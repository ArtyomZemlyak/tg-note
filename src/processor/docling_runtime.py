"""
Docling runtime helpers for container orchestration.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional

from loguru import logger

from src.processor.file_processor import FileProcessor


@lru_cache()
def get_file_processor() -> FileProcessor:
    """Lazily instantiate a shared FileProcessor instance."""
    return FileProcessor()


async def sync_models(force: bool = False) -> Optional[Dict[str, Any]]:
    """
    Trigger Docling model synchronisation via MCP.

    Args:
        force: Whether to redownload existing artefacts.
    """
    processor = get_file_processor()
    if not processor.docling_config.use_mcp():
        logger.warning("[DoclingRuntime] Docling MCP backend disabled; skipping sync.")
        return None
    return await processor.sync_docling_models(force=force)
