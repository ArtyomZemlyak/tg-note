from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

from loguru import logger

# AICODE-NOTE: Known tessdata locations shipped with common Tesseract packages.
DEFAULT_TESSDATA_CANDIDATES: tuple[Path, ...] = (
    Path("/usr/share/tesseract-ocr/5/tessdata"),
    Path("/usr/share/tesseract-ocr/4.00/tessdata"),
    Path("/usr/share/tesseract-ocr/tessdata"),
    Path("/usr/share/tessdata"),
)


def _iter_candidates(
    models_base: Path, configured_path: Optional[str], env_prefix: Optional[str]
) -> Iterable[Path]:
    if configured_path:
        candidate = Path(configured_path)
        if not candidate.is_absolute():
            candidate = (models_base / candidate).resolve()
        yield candidate

    if env_prefix:
        yield Path(env_prefix)

    yield from DEFAULT_TESSDATA_CANDIDATES


def resolve_tessdata_path(models_base: Path, configured_path: Optional[str]) -> Optional[str]:
    """
    Resolve the tessdata directory for the Tesseract backend.

    Priority order:
        1. Explicit path set in MEDIA_PROCESSING_DOCLING.ocr_config.tesseract.tessdata_prefix
        2. TESSDATA_PREFIX environment variable
        3. Known system locations (DEFAULT_TESSDATA_CANDIDATES)
    """

    env_prefix = os.getenv("TESSDATA_PREFIX")

    for candidate in _iter_candidates(models_base, configured_path, env_prefix):
        if candidate and candidate.is_dir():
            resolved = str(candidate)
            if configured_path and candidate != Path(configured_path):
                logger.debug("Resolved relative tessdata path %s to %s", configured_path, resolved)
            return resolved

    if configured_path:
        logger.warning(
            "Configured Tesseract tessdata directory does not exist: %s",
            configured_path,
        )
    elif env_prefix:
        logger.warning(
            "Environment variable TESSDATA_PREFIX points to a non-existent directory: %s",
            env_prefix,
        )
    else:
        logger.warning(
            "Unable to locate Tesseract tessdata directory automatically. "
            "Set MEDIA_PROCESSING_DOCLING.ocr_config.tesseract.tessdata_prefix "
            "or export TESSDATA_PREFIX."
        )

    return None
