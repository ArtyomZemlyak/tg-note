from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional

from docling.datamodel.pipeline_options import (
    LayoutOptions,
    granite_picture_description,
    smolvlm_picture_description,
)
from docling.datamodel.vlm_model_specs import (
    GRANITEDOCLING_MLX,
    GRANITEDOCLING_TRANSFORMERS,
    SMOLDOCLING_MLX,
    SMOLDOCLING_TRANSFORMERS,
)
from docling.models.code_formula_model import CodeFormulaModel
from docling.models.document_picture_classifier import DocumentPictureClassifier
from docling.models.easyocr_model import EasyOcrModel
from docling.models.layout_model import LayoutModel
from docling.models.rapid_ocr_model import RapidOcrModel
from docling.models.table_structure_model import TableStructureModel
from docling.models.utils.hf_model_download import download_hf_model
from docling.utils.model_downloader import download_models as download_model_bundles
from huggingface_hub import snapshot_download

try:
    from modelscope.hub.snapshot_download import snapshot_download as ms_snapshot_download
except Exception:  # pragma: no cover - optional dependency
    ms_snapshot_download = None

from tg_docling.config import DEFAULT_SETTINGS_PATH, load_docling_settings
from tg_docling.converter import install_converter

from config.settings import DoclingModelDownloadSettings, DoclingSettings

if TYPE_CHECKING:
    from config.settings import DoclingBuiltinModelCacheSettings

logger = logging.getLogger(__name__)

# AICODE-NOTE: Callback for sending progress notifications (e.g., to Telegram)
# Can be set externally to receive sync progress updates
_sync_progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None

SUPPORTED_RAPIDOCR_BACKENDS = tuple(sorted(RapidOcrModel._default_models.keys()))

_DOC_MODEL_FLAG_MAP: Dict[str, str] = {
    "layout": "with_layout",
    "tableformer": "with_tableformer",
    "code_formula": "with_code_formula",
    "picture_classifier": "with_picture_classifier",
    "smolvlm": "with_smolvlm",
    "granitedocling": "with_granitedocling",
    "granitedocling_mlx": "with_granitedocling_mlx",
    "smoldocling": "with_smoldocling",
    "smoldocling_mlx": "with_smoldocling_mlx",
    "granite_vision": "with_granite_vision",
    "rapidocr": "with_rapidocr",
    "easyocr": "with_easyocr",
}

_DOC_MODEL_PATH_MAP: Dict[str, Callable[[Path], Path]] = {
    "layout": lambda base: base / LayoutOptions().model_spec.model_repo_folder,
    "tableformer": lambda base: base / TableStructureModel._model_repo_folder,  # type: ignore[attr-defined]
    "code_formula": lambda base: base / CodeFormulaModel._model_repo_folder,  # type: ignore[attr-defined]
    "picture_classifier": lambda base: base
    / DocumentPictureClassifier._model_repo_folder,  # type: ignore[attr-defined]
    "rapidocr": lambda base: base / RapidOcrModel._model_repo_folder,  # type: ignore[attr-defined]
    "easyocr": lambda base: base / EasyOcrModel._model_repo_folder,  # type: ignore[attr-defined]
    "smolvlm": lambda base: base / smolvlm_picture_description.repo_cache_folder,
    "granitedocling": lambda base: base / GRANITEDOCLING_TRANSFORMERS.repo_cache_folder,
    "granitedocling_mlx": lambda base: base / GRANITEDOCLING_MLX.repo_cache_folder,
    "smoldocling": lambda base: base / SMOLDOCLING_TRANSFORMERS.repo_cache_folder,
    "smoldocling_mlx": lambda base: base / SMOLDOCLING_MLX.repo_cache_folder,
    "granite_vision": lambda base: base / granite_picture_description.repo_cache_folder,
}

_HF_TRANSFER_FAST_DOWNLOAD_AVAILABLE: Optional[bool] = None


def _is_hf_transfer_missing_error(exc: Exception) -> bool:
    if not isinstance(exc, ValueError):
        return False
    message = str(exc)
    return (
        "Fast download using 'hf_transfer'" in message
        and "'hf_transfer' package is not available" in message
    )


@contextmanager
def _temporarily_disable_hf_transfer_env() -> Iterator[None]:
    """Temporarily disable HF transfer fast downloads by forcing env flag to 0."""
    original = os.environ.get("HF_HUB_ENABLE_HF_TRANSFER")
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("HF_HUB_ENABLE_HF_TRANSFER", None)
        else:
            os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = original


def _snapshot_download_with_hf_transfer_fallback(
    *,
    repo_id: Optional[str],
    revision: Optional[str],
    target_dir: Path,
    allow_patterns: Optional[List[str]],
    ignore_patterns: Optional[List[str]],
) -> str:
    """Download snapshot while gracefully handling missing hf_transfer dependency."""
    global _HF_TRANSFER_FAST_DOWNLOAD_AVAILABLE

    kwargs = {
        "repo_id": repo_id,
        "revision": revision,
        "local_dir": target_dir,
        "local_dir_use_symlinks": False,
        "allow_patterns": allow_patterns,
        "ignore_patterns": ignore_patterns,
    }

    def _call_snapshot() -> str:
        return snapshot_download(**kwargs)

    if _HF_TRANSFER_FAST_DOWNLOAD_AVAILABLE is False:
        with _temporarily_disable_hf_transfer_env():
            return _call_snapshot()

    try:
        return _call_snapshot()
    except Exception as exc:
        if not _is_hf_transfer_missing_error(exc):
            raise

        # AICODE-NOTE: Falling back to standard download when hf_transfer fast-path is unavailable.
        if _HF_TRANSFER_FAST_DOWNLOAD_AVAILABLE is not False:
            _HF_TRANSFER_FAST_DOWNLOAD_AVAILABLE = False
            logger.warning(
                "hf_transfer fast download requested but package is unavailable; retrying with "
                "standard HuggingFace download."
            )
            _notify_progress(
                "⚠️ hf_transfer package missing, falling back to standard download.",
                {"status": "warning", "reason": "hf_transfer_unavailable"},
            )

        with _temporarily_disable_hf_transfer_env():
            return _call_snapshot()


def set_sync_progress_callback(callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> None:
    """
    Set a callback function to receive model sync progress updates.

    Args:
        callback: Function that accepts (message: str, data: Dict[str, Any])
                  or None to disable notifications
    """
    global _sync_progress_callback
    _sync_progress_callback = callback


def _notify_progress(message: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Send progress notification if callback is configured."""
    if _sync_progress_callback is not None:
        try:
            _sync_progress_callback(message, data or {})
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to send progress notification: %s", exc)


def _resolve_target_dir(base_dir: Path, download: DoclingModelDownloadSettings) -> Path:
    """Resolve the local directory where the artefact should be stored."""
    if download.local_dir:
        return base_dir / download.local_dir
    if download.repo_id:
        sanitized = download.repo_id.replace("/", "__")
        return base_dir / sanitized
    return base_dir / download.name


def _prepare_download_dir(path: Path, force: bool) -> None:
    """Ensure target directory exists and optionally reset previous contents."""
    if force and path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _download_rapidocr_backends(base_dir: Path, backends: List[str], force: bool) -> Dict[str, Any]:
    backend_results: List[Dict[str, Any]] = []
    success = False
    base_path = base_dir / RapidOcrModel._model_repo_folder  # type: ignore[attr-defined]
    _prepare_download_dir(base_path, force)
    for backend in backends:
        entry = {"backend": backend}
        if backend not in SUPPORTED_RAPIDOCR_BACKENDS:
            entry.update({"status": "skipped", "reason": "unsupported backend"})
            backend_results.append(entry)
            continue
        local_dir = RapidOcrModel.download_models(
            backend=backend,
            local_dir=base_path,
            force=force,
            progress=False,
        )
        entry.update({"status": "downloaded", "path": str(local_dir)})
        backend_results.append(entry)
        success = True

    status = "downloaded" if success else "skipped"
    if not backend_results:
        status = "skipped"
    return {"status": status, "backends": backend_results, "path": str(base_path)}


def _doc_model_flag_kwargs(target_flag: str) -> Dict[str, bool]:
    """Build argument dictionary for docling download helper."""
    kwargs = {flag_name: False for flag_name in _DOC_MODEL_FLAG_MAP.values()}
    kwargs[target_flag] = True
    return kwargs


def _download_docling_bundle(base_dir: Path, target_flag: str, force: bool) -> None:
    """Invoke Docling's managed downloader for a specific model bundle."""
    kwargs = _doc_model_flag_kwargs(target_flag)
    download_model_bundles(output_dir=base_dir, force=force, progress=False, **kwargs)


def _resolve_model_path(base_dir: Path, model_name: str) -> str:
    """Resolve canonical model path for a Docling bundle."""
    path_factory = _DOC_MODEL_PATH_MAP.get(model_name)
    target_path = path_factory(base_dir) if path_factory else base_dir
    return str(target_path)


def _sync_builtin_model(
    base_dir: Path,
    model_name: str,
    builtin_settings: "DoclingBuiltinModelCacheSettings",
    force: bool,
) -> Dict[str, Any]:
    """Ensure a single Docling-managed bundle is present according to configuration."""
    result: Dict[str, Any] = {"name": model_name, "kind": "builtin"}

    flag_name = _DOC_MODEL_FLAG_MAP.get(model_name)
    if flag_name is None:
        result.update({"status": "error", "error": f"unsupported builtin model '{model_name}'"})
        return result

    if model_name == "rapidocr":
        rapidocr_cfg = builtin_settings.rapidocr
        if not rapidocr_cfg.enabled:
            result.update({"status": "skipped", "reason": "disabled"})
            return result

        if rapidocr_cfg.wants_builtin_download():
            logger.info("Downloading RapidOCR bundle using Docling defaults")
            _download_docling_bundle(base_dir, flag_name, force)
            result.update(
                {"status": "downloaded", "path": _resolve_model_path(base_dir, model_name)}
            )
            return result

        requested_backends = rapidocr_cfg.backends or list(SUPPORTED_RAPIDOCR_BACKENDS)
        logger.info(
            "Downloading RapidOCR bundle using custom backends: %s",
            ", ".join(requested_backends),
        )
        backend_result = _download_rapidocr_backends(base_dir, requested_backends, force)
        backend_result["name"] = model_name
        backend_result["kind"] = "builtin"
        return backend_result

    logger.info("Downloading Docling bundle '%s'", model_name)
    _download_docling_bundle(base_dir, flag_name, force)
    result.update({"status": "downloaded", "path": _resolve_model_path(base_dir, model_name)})
    return result


def _sync_huggingface(
    target_dir: Path,
    download: DoclingModelDownloadSettings,
    force: bool,
) -> Dict[str, Any]:
    """Synchronise models from Hugging Face Hub."""
    target_dir.mkdir(parents=True, exist_ok=True)

    if any(target_dir.iterdir()) and not force:
        logger.info("Skipping HuggingFace repo %s (already cached)", download.repo_id)
        _notify_progress(
            f"⏭️ Skipping {download.name}: already cached",
            {"name": download.name, "repo_id": download.repo_id, "status": "skipped"},
        )
        return {
            "status": "skipped",
            "repo_id": download.repo_id,
            "path": str(target_dir),
            "kind": "download",
        }

    if force and target_dir.exists():
        _notify_progress(
            f"🗑️ Cleaning old {download.name} cache",
            {"name": download.name, "repo_id": download.repo_id},
        )
        shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

    allow_patterns = download.allow_patterns or download.files
    ignore_patterns = download.ignore_patterns

    _notify_progress(
        f"📥 Downloading {download.name} from HuggingFace...",
        {"name": download.name, "repo_id": download.repo_id, "status": "downloading"},
    )

    local_dir = _snapshot_download_with_hf_transfer_fallback(
        repo_id=download.repo_id,
        revision=download.revision,
        target_dir=target_dir,
        allow_patterns=allow_patterns,
        ignore_patterns=ignore_patterns,
    )

    logger.info("Downloaded HuggingFace repo %s to %s", download.repo_id, local_dir)
    _notify_progress(
        f"✅ Successfully downloaded {download.name}",
        {
            "name": download.name,
            "repo_id": download.repo_id,
            "path": str(local_dir),
            "status": "completed",
        },
    )
    return {
        "status": "downloaded",
        "repo_id": download.repo_id,
        "path": str(target_dir),
        "revision": download.revision,
        "kind": "download",
    }


def _sync_modelscope(
    target_dir: Path,
    download: DoclingModelDownloadSettings,
    force: bool,
) -> Dict[str, Any]:
    """Synchronise models from ModelScope."""
    if ms_snapshot_download is None:
        error_msg = "modelscope is not installed; cannot download models."
        _notify_progress(
            f"❌ Error: {error_msg}", {"name": download.name, "status": "error", "error": error_msg}
        )
        raise RuntimeError(error_msg)

    target_dir.mkdir(parents=True, exist_ok=True)

    if any(target_dir.iterdir()) and not force:
        logger.info("Skipping ModelScope repo %s (already cached)", download.repo_id)
        _notify_progress(
            f"⏭️ Skipping {download.name}: already cached",
            {"name": download.name, "repo_id": download.repo_id, "status": "skipped"},
        )
        return {
            "status": "skipped",
            "repo_id": download.repo_id,
            "path": str(target_dir),
            "kind": "download",
        }

    if force and target_dir.exists():
        _notify_progress(
            f"🗑️ Cleaning old {download.name} cache",
            {"name": download.name, "repo_id": download.repo_id},
        )
        shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

    _notify_progress(
        f"📥 Downloading {download.name} from ModelScope...",
        {"name": download.name, "repo_id": download.repo_id, "status": "downloading"},
    )

    local_dir = ms_snapshot_download(
        download.repo_id,
        revision=download.revision,
        cache_dir=target_dir,
        allow_file_pattern=download.allow_patterns or download.files,
    )

    logger.info("Downloaded ModelScope repo %s to %s", download.repo_id, local_dir)
    _notify_progress(
        f"✅ Successfully downloaded {download.name}",
        {
            "name": download.name,
            "repo_id": download.repo_id,
            "path": str(local_dir),
            "status": "completed",
        },
    )
    return {
        "status": "downloaded",
        "repo_id": download.repo_id,
        "path": str(target_dir),
        "revision": download.revision,
        "kind": "download",
    }


def sync_models(settings: DoclingSettings, force: bool = False) -> Dict[str, Any]:
    """
    Ensure all configured model artefacts are available on disk.

    Returns a structured dictionary describing performed operations.
    """
    results: List[Dict[str, Any]] = []
    builtin_results: List[Dict[str, Any]] = []
    download_results: List[Dict[str, Any]] = []

    base_dir = Path(settings.model_cache.base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    builtin_settings = settings.model_cache.builtin_models
    enabled_map = builtin_settings.enabled_model_map()
    enabled_builtin = [name for name in _DOC_MODEL_FLAG_MAP.keys() if enabled_map.get(name)]
    extra_downloads = list(settings.model_cache.downloads)
    total_items = len(enabled_builtin) + len(extra_downloads)
    logger.info("Synchronising Docling model artefacts (force=%s)", force)
    _notify_progress(
        f"🔄 Starting model synchronization ({total_items} items)...",
        {"total": total_items, "force": force, "status": "started"},
    )

    if total_items == 0:
        _notify_progress("✅ No Docling model downloads requested.", {"status": "completed"})
        return {
            "builtin": builtin_results,
            "downloads": download_results,
            "items": results,
            "summary": {"successful": 0, "failed": 0, "total": 0},
        }

    progress_index = 0

    for model_name in enabled_builtin:
        progress_index += 1
        _notify_progress(
            f"📦 Processing {progress_index}/{total_items}: bundle {model_name}",
            {
                "current": progress_index,
                "total": total_items,
                "name": model_name,
                "kind": "builtin",
            },
        )

        try:
            result = _sync_builtin_model(base_dir, model_name, builtin_settings, force=force)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Failed to download builtin model %s", model_name)
            result = {
                "name": model_name,
                "status": "error",
                "error": str(exc),
                "kind": "builtin",
            }

        builtin_results.append(result)
        results.append(result)

        status = result.get("status")
        if status == "downloaded":
            _notify_progress(
                f"✅ Downloaded bundle {model_name}",
                {"name": model_name, "status": status, "kind": "builtin"},
            )
        elif status == "skipped":
            _notify_progress(
                f"⏭️ Skipped bundle {model_name}",
                {
                    "name": model_name,
                    "status": status,
                    "kind": "builtin",
                    "reason": result.get("reason"),
                },
            )
        elif status == "error":
            _notify_progress(
                f"❌ Failed to download bundle {model_name}: {result.get('error')}",
                {
                    "name": model_name,
                    "status": status,
                    "kind": "builtin",
                    "error": result.get("error"),
                },
            )

    for item in extra_downloads:
        progress_index += 1
        target_dir = _resolve_target_dir(base_dir, item)
        logger.info(
            "Processing model download '%s' (type=%s) into %s",
            item.name,
            item.type,
            target_dir,
        )

        _notify_progress(
            f"📦 Processing {progress_index}/{total_items}: {item.name}",
            {
                "current": progress_index,
                "total": total_items,
                "name": item.name,
                "type": item.type,
                "kind": "download",
            },
        )

        try:
            if item.type == "huggingface":
                result = _sync_huggingface(target_dir, item, force=force)
            elif item.type == "modelscope":
                result = _sync_modelscope(target_dir, item, force=force)
            else:
                error_msg = f"Unsupported model download type: {item.type}"
                _notify_progress(
                    f"❌ Error processing {item.name}: {error_msg}",
                    {
                        "name": item.name,
                        "status": "error",
                        "error": error_msg,
                        "kind": "download",
                    },
                )
                raise RuntimeError(error_msg)

            result.update({"name": item.name, "kind": "download"})
            download_results.append(result)
            results.append(result)
        except Exception as exc:
            logger.exception("Failed to sync model %s", item.name)
            err_result = {
                "name": item.name,
                "status": "error",
                "error": str(exc),
                "kind": "download",
            }
            _notify_progress(
                f"❌ Failed to sync {item.name}: {str(exc)}",
                err_result.copy(),
            )
            download_results.append(err_result)
            results.append(err_result)

    successful = sum(1 for r in results if r.get("status") in ("downloaded", "skipped"))
    failed = sum(1 for r in results if r.get("status") == "error")

    logger.info("Model synchronisation completed (successful=%d, failed=%d)", successful, failed)
    _notify_progress(
        f"✅ Model synchronization completed: {successful} successful, {failed} failed",
        {
            "successful": successful,
            "failed": failed,
            "total": total_items,
            "status": "completed",
        },
    )

    summary = {"successful": successful, "failed": failed, "total": total_items}
    return {
        "builtin": builtin_results,
        "downloads": download_results,
        "items": results,
        "summary": summary,
    }


def main(argv: List[str] | None = None) -> None:
    args = argv or sys.argv[1:]
    force = "--force" in args
    settings_path = Path(os.getenv("DOCLING_SETTINGS_PATH", str(DEFAULT_SETTINGS_PATH)))
    docling_settings, _ = load_docling_settings(settings_path)
    install_converter(docling_settings)
    result = sync_models(docling_settings, force=force)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
