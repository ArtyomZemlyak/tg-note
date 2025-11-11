from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from loguru import logger

from config.logging_config import setup_logging


class _LoguruInterceptHandler(logging.Handler):
    """Route standard logging records through Loguru so formatting stays consistent."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _install_loguru_bridge(log_level: int) -> None:
    """Replace root handlers with Loguru interceptors."""
    logging.root.handlers = []
    logging.root.setLevel(log_level)
    handler = _LoguruInterceptHandler()
    logging.basicConfig(handlers=[handler], level=log_level, force=True)

    # Silence overly verbose third-party libraries by default
    for noisy in ("urllib3", "httpx", "PIL", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.captureWarnings(True)


def configure_logging(level: str = "INFO", log_dir: Optional[str] = None) -> None:
    """
    Configure Loguru logging for the Docling MCP container so that output matches the bot style.
    """

    log_level = getattr(logging, level.upper(), logging.INFO)
    log_file = Path(log_dir) / "docling-mcp.log" if log_dir else None

    setup_logging(log_level=level.upper(), log_file=log_file)
    _install_loguru_bridge(log_level)

    logger.info("Docling logging initialised (level=%s, log_dir=%s)", level.upper(), log_dir)
