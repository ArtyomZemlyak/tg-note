from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from loguru import logger

from config.logging_config import setup_logging


def _truncate_base64_in_message(message: str, max_length: int = 50) -> str:
    """
    Truncate base64-encoded strings in log messages to prevent log bloat.

    Args:
        message: The log message that may contain base64 content
        max_length: Maximum length for base64 strings (default: 50)

    Returns:
        Message with truncated base64 strings
    """
    # Pattern 1: Match base64 in common key-value patterns like 'content': '...', "content": "..."
    # Also handles cases like content='...', content="...", 'content'='...', etc.
    base64_pattern = r"(['\"]?(?:content|data|payload|base64|b64|value|arg)['\"]?\s*[:=]\s*['\"]?)([A-Za-z0-9+/=]{50,})(['\"]?)"

    def truncate_match(match):
        prefix = match.group(1)
        base64_content = match.group(2)
        suffix = match.group(3) or ""
        truncated = base64_content[:max_length] + "...[truncated]"
        return f"{prefix}{truncated}{suffix}"

    # Apply truncation for key-value patterns
    result = re.sub(base64_pattern, truncate_match, message, flags=re.IGNORECASE)

    # Pattern 2: Handle standalone long base64-like strings (100+ chars)
    # This catches cases where base64 is passed as a direct argument or in complex structures
    standalone_pattern = r"([A-Za-z0-9+/=]{100,})"

    def truncate_standalone(match):
        content = match.group(1)
        # Only truncate if it looks like base64 (has enough variety of chars and typical base64 chars)
        # Base64 typically has a diverse character set and may include padding (=)
        char_variety = len(set(content[:100]))
        has_base64_chars = bool(re.search(r"[+/=]", content[:100]))

        # Truncate if it has good variety (likely base64) or contains base64-specific chars
        if char_variety > 10 or (has_base64_chars and len(content) > 200):
            truncated = content[:max_length] + "...[truncated]"
            return truncated
        return content

    result = re.sub(standalone_pattern, truncate_standalone, result)

    return result


class _LoguruInterceptHandler(logging.Handler):
    """Route standard logging records through Loguru so formatting stays consistent."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Truncate base64 content in the message
        message = record.getMessage()
        truncated_message = _truncate_base64_in_message(message)

        # Patch loguru record to use the actual source location from LogRecord
        # This ensures we show the correct file/function/line instead of logging internals
        def patch_record(log_record):
            log_record["name"] = record.name
            log_record["file"] = record.pathname
            log_record["function"] = record.funcName or "<unknown>"
            log_record["line"] = record.lineno

        logger.patch(patch_record).opt(exception=record.exc_info).log(level, truncated_message)


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
