from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

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
from huggingface_hub import snapshot_download

try:
    from modelscope.hub.snapshot_download import snapshot_download as ms_snapshot_download
except Exception:  # pragma: no cover - optional dependency
    ms_snapshot_download = None

from tg_docling.config import (
    ContainerConfig,
    ModelDownloadConfig,
    ModelGroupConfig,
    ensure_config_file,
    load_config,
)
from tg_docling.converter import install_converter

logger = logging.getLogger(__name__)

# AICODE-NOTE: Callback for sending progress notifications (e.g., to Telegram)
# Can be set externally to receive sync progress updates
_sync_progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None

SUPPORTED_RAPIDOCR_BACKENDS = tuple(sorted(RapidOcrModel._default_models.keys()))


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


def _resolve_target_dir(base_dir: Path, download: ModelDownloadConfig) -> Path:
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


def _download_model_group(base_dir: Path, group: ModelGroupConfig, force: bool) -> Dict[str, Any]:
    """Download a predefined Docling model group."""
    result: Dict[str, Any] = {"name": group.name, "kind": "group"}

    if not group.enabled:
        result.update({"status": "skipped", "reason": "disabled"})
        return result

    try:
        if group.name == "layout":
            local_dir = base_dir / LayoutOptions().model_spec.model_repo_folder
            _prepare_download_dir(local_dir, force)
            LayoutModel.download_models(local_dir=local_dir, force=force, progress=False)
            result.update({"status": "downloaded", "path": str(local_dir)})
        elif group.name == "tableformer":
            local_dir = base_dir / TableStructureModel._model_repo_folder  # type: ignore[attr-defined]
            _prepare_download_dir(local_dir, force)
            TableStructureModel.download_models(local_dir=local_dir, force=force, progress=False)
            result.update({"status": "downloaded", "path": str(local_dir)})
        elif group.name == "code_formula":
            local_dir = base_dir / CodeFormulaModel._model_repo_folder  # type: ignore[attr-defined]
            _prepare_download_dir(local_dir, force)
            CodeFormulaModel.download_models(local_dir=local_dir, force=force, progress=False)
            result.update({"status": "downloaded", "path": str(local_dir)})
        elif group.name == "picture_classifier":
            local_dir = base_dir / DocumentPictureClassifier._model_repo_folder  # type: ignore[attr-defined]
            _prepare_download_dir(local_dir, force)
            DocumentPictureClassifier.download_models(
                local_dir=local_dir,
                force=force,
                progress=False,
            )
            result.update({"status": "downloaded", "path": str(local_dir)})
        elif group.name == "rapidocr":
            requested_backends = list(group.backends) or list(SUPPORTED_RAPIDOCR_BACKENDS)
            backend_results: List[Dict[str, Any]] = []
            success = False
            base_path = base_dir / RapidOcrModel._model_repo_folder  # type: ignore[attr-defined]
            _prepare_download_dir(base_path, force)
            for backend in requested_backends:
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
            if not backend_results:
                result.update({"status": "skipped", "reason": "no backends requested"})
            else:
                result.update(
                    {
                        "status": "downloaded" if success else "skipped",
                        "backends": backend_results,
                    }
                )
        elif group.name == "easyocr":
            local_dir = base_dir / EasyOcrModel._model_repo_folder  # type: ignore[attr-defined]
            _prepare_download_dir(local_dir, force)
            EasyOcrModel.download_models(local_dir=local_dir, force=force, progress=False)
            result.update({"status": "downloaded", "path": str(local_dir)})
        elif group.name == "smolvlm":
            cache_dir = base_dir / smolvlm_picture_description.repo_cache_folder
            _prepare_download_dir(cache_dir, force)
            local_dir = download_hf_model(
                repo_id=smolvlm_picture_description.repo_id,
                local_dir=cache_dir,
                force=force,
                progress=False,
            )
            result.update({"status": "downloaded", "path": str(local_dir)})
        elif group.name == "granitedocling":
            cache_dir = base_dir / GRANITEDOCLING_TRANSFORMERS.repo_cache_folder
            _prepare_download_dir(cache_dir, force)
            local_dir = download_hf_model(
                repo_id=GRANITEDOCLING_TRANSFORMERS.repo_id,
                local_dir=cache_dir,
                force=force,
                progress=False,
            )
            result.update({"status": "downloaded", "path": str(local_dir)})
        elif group.name == "granitedocling_mlx":
            cache_dir = base_dir / GRANITEDOCLING_MLX.repo_cache_folder
            _prepare_download_dir(cache_dir, force)
            local_dir = download_hf_model(
                repo_id=GRANITEDOCLING_MLX.repo_id,
                local_dir=cache_dir,
                force=force,
                progress=False,
            )
            result.update({"status": "downloaded", "path": str(local_dir)})
        elif group.name == "smoldocling":
            cache_dir = base_dir / SMOLDOCLING_TRANSFORMERS.repo_cache_folder
            _prepare_download_dir(cache_dir, force)
            local_dir = download_hf_model(
                repo_id=SMOLDOCLING_TRANSFORMERS.repo_id,
                local_dir=cache_dir,
                force=force,
                progress=False,
            )
            result.update({"status": "downloaded", "path": str(local_dir)})
        elif group.name == "smoldocling_mlx":
            cache_dir = base_dir / SMOLDOCLING_MLX.repo_cache_folder
            _prepare_download_dir(cache_dir, force)
            local_dir = download_hf_model(
                repo_id=SMOLDOCLING_MLX.repo_id,
                local_dir=cache_dir,
                force=force,
                progress=False,
            )
            result.update({"status": "downloaded", "path": str(local_dir)})
        elif group.name == "granite_vision":
            cache_dir = base_dir / granite_picture_description.repo_cache_folder
            _prepare_download_dir(cache_dir, force)
            local_dir = download_hf_model(
                repo_id=granite_picture_description.repo_id,
                local_dir=cache_dir,
                force=force,
                progress=False,
            )
            result.update({"status": "downloaded", "path": str(local_dir)})
        else:
            result.update({"status": "skipped", "reason": f"unsupported group '{group.name}'"})
    except Exception as exc:
        logger.exception("Failed to download model group %s", group.name)
        result.update({"status": "error", "error": str(exc)})

    return result


def _sync_huggingface(
    target_dir: Path,
    download: ModelDownloadConfig,
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

    local_dir = snapshot_download(
        repo_id=download.repo_id,
        revision=download.revision,
        local_dir=target_dir,
        local_dir_use_symlinks=False,
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
    download: ModelDownloadConfig,
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


def sync_models(config: ContainerConfig, force: bool = False) -> Dict[str, Any]:
    """
    Ensure all configured model artefacts are available on disk.

    Returns a structured dictionary describing performed operations.
    """
    results: List[Dict[str, Any]] = []
    group_results: List[Dict[str, Any]] = []
    download_results: List[Dict[str, Any]] = []

    base_dir = config.model_cache.base_dir
    base_dir.mkdir(parents=True, exist_ok=True)

    total_items = len(config.model_cache.groups) + len(config.model_cache.downloads)
    logger.info("Synchronising Docling model artefacts (force=%s)", force)
    _notify_progress(
        f"🔄 Starting model synchronization ({total_items} items)...",
        {"total": total_items, "force": force, "status": "started"},
    )

    progress_index = 0
    total_for_progress = max(total_items, 1)

    for group in config.model_cache.groups:
        progress_index += 1
        _notify_progress(
            f"📦 Processing {progress_index}/{total_for_progress}: group {group.name}",
            {
                "current": progress_index,
                "total": total_for_progress,
                "name": group.name,
                "kind": "group",
            },
        )

        result = _download_model_group(base_dir, group, force=force)
        group_results.append(result)
        results.append(result)

        status = result.get("status")
        if status == "downloaded":
            _notify_progress(
                f"✅ Downloaded group {group.name}",
                {"name": group.name, "status": status, "kind": "group"},
            )
        elif status == "skipped":
            _notify_progress(
                f"⏭️ Skipped group {group.name}",
                {
                    "name": group.name,
                    "status": status,
                    "kind": "group",
                    "reason": result.get("reason"),
                },
            )
        elif status == "error":
            _notify_progress(
                f"❌ Failed to download group {group.name}: {result.get('error')}",
                {
                    "name": group.name,
                    "status": status,
                    "kind": "group",
                    "error": result.get("error"),
                },
            )

    for item in config.model_cache.downloads:
        progress_index += 1
        target_dir = _resolve_target_dir(base_dir, item)
        logger.info(
            "Processing model download '%s' (type=%s) into %s",
            item.name,
            item.type,
            target_dir,
        )

        _notify_progress(
            f"📦 Processing {progress_index}/{total_for_progress}: {item.name}",
            {
                "current": progress_index,
                "total": total_for_progress,
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
        "groups": group_results,
        "downloads": download_results,
        "items": results,
        "summary": summary,
    }


def main(argv: List[str] | None = None) -> None:
    args = argv or sys.argv[1:]
    force = "--force" in args
    config_path = Path(
        os.getenv("DOCLING_CONFIG_PATH", "/opt/docling-mcp/config/docling-config.json")
    )
    config = load_config(ensure_config_file(config_path))
    install_converter(config)
    result = sync_models(config, force=force)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
