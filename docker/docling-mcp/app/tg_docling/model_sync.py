from __future__ import annotations

import logging
import shutil
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

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
        return {"status": "skipped", "repo_id": download.repo_id, "path": str(target_dir)}

    if force and target_dir.exists():
        shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

    allow_patterns = download.allow_patterns or download.files
    ignore_patterns = download.ignore_patterns

    local_dir = snapshot_download(
        repo_id=download.repo_id,
        revision=download.revision,
        local_dir=target_dir,
        local_dir_use_symlinks=False,
        allow_patterns=allow_patterns,
        ignore_patterns=ignore_patterns,
    )

    logger.info("Downloaded HuggingFace repo %s to %s", download.repo_id, local_dir)
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
        raise RuntimeError("modelscope is not installed; cannot download models.")

    target_dir.mkdir(parents=True, exist_ok=True)

    if any(target_dir.iterdir()) and not force:
        logger.info("Skipping ModelScope repo %s (already cached)", download.repo_id)
        return {"status": "skipped", "repo_id": download.repo_id, "path": str(target_dir)}

    if force and target_dir.exists():
        shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

    local_dir = ms_snapshot_download(
        download.repo_id,
        revision=download.revision,
        cache_dir=target_dir,
        allow_file_pattern=download.allow_patterns or download.files,
    )

    logger.info("Downloaded ModelScope repo %s to %s", download.repo_id, local_dir)
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

    logger.info("Synchronising Docling model artefacts (force=%s)", force)

    for item in config.model_cache.downloads:
        target_dir = _resolve_target_dir(base_dir, item)
        logger.info(
            "Processing model download '%s' (type=%s) into %s",
            item.name,
            item.type,
            target_dir,
        )

        if item.type == "huggingface":
            result = _sync_huggingface(target_dir, item, force=force)
        elif item.type == "modelscope":
            result = _sync_modelscope(target_dir, item, force=force)
        else:
            raise RuntimeError(f"Unsupported model download type: {item.type}")

        result["name"] = item.name
        results.append(result)

    logger.info("Model synchronisation completed")
    return {"items": results}


def main(argv: List[str] | None = None) -> None:
    args = argv or sys.argv[1:]
    force = "--force" in args
    config_path = Path(os.getenv("DOCLING_CONFIG_PATH", "/opt/docling-mcp/config/docling-config.json"))
    config = load_config(ensure_config_file(config_path))
    install_converter(config)
    result = sync_models(config, force=force)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
