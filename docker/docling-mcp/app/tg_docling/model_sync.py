from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from huggingface_hub import snapshot_download

try:
    from modelscope.hub.snapshot_download import snapshot_download as ms_snapshot_download
except Exception:  # pragma: no cover - optional dependency
    ms_snapshot_download = None

from tg_docling.config import (
    ContainerConfig,
    ModelDownloadConfig,
    ensure_config_file,
    load_config,
)
from tg_docling.converter import install_converter

logger = logging.getLogger(__name__)

# AICODE-NOTE: Callback for sending progress notifications (e.g., to Telegram)
# Can be set externally to receive sync progress updates
_sync_progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None


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
        return {"status": "skipped", "repo_id": download.repo_id, "path": str(target_dir)}

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
        return {"status": "skipped", "repo_id": download.repo_id, "path": str(target_dir)}

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
    }


def sync_models(config: ContainerConfig, force: bool = False) -> Dict[str, Any]:
    """
    Ensure all configured model artefacts are available on disk.

    Returns a structured dictionary describing performed operations.
    """
    results: List[Dict[str, Any]] = []
    base_dir = config.model_cache.base_dir
    base_dir.mkdir(parents=True, exist_ok=True)

    total_items = len(config.model_cache.downloads)
    logger.info("Synchronising Docling model artefacts (force=%s)", force)
    _notify_progress(
        f"🔄 Starting model synchronization ({total_items} items)...",
        {"total": total_items, "force": force, "status": "started"},
    )

    for idx, item in enumerate(config.model_cache.downloads, 1):
        target_dir = _resolve_target_dir(base_dir, item)
        logger.info(
            "Processing model download '%s' (type=%s) into %s",
            item.name,
            item.type,
            target_dir,
        )

        _notify_progress(
            f"📦 Processing {idx}/{total_items}: {item.name}",
            {"current": idx, "total": total_items, "name": item.name, "type": item.type},
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
                    {"name": item.name, "status": "error", "error": error_msg},
                )
                raise RuntimeError(error_msg)

            result["name"] = item.name
            results.append(result)
        except Exception as exc:
            logger.exception("Failed to sync model %s", item.name)
            _notify_progress(
                f"❌ Failed to sync {item.name}: {str(exc)}",
                {"name": item.name, "status": "error", "error": str(exc)},
            )
            results.append(
                {
                    "name": item.name,
                    "status": "error",
                    "error": str(exc),
                }
            )

    successful = sum(1 for r in results if r.get("status") in ("downloaded", "skipped"))
    failed = sum(1 for r in results if r.get("status") == "error")

    logger.info("Model synchronisation completed (successful=%d, failed=%d)", successful, failed)
    _notify_progress(
        f"✅ Model synchronization completed: {successful} successful, {failed} failed",
        {"successful": successful, "failed": failed, "total": total_items, "status": "completed"},
    )

    return {
        "items": results,
        "summary": {"successful": successful, "failed": failed, "total": total_items},
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
