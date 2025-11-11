from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from config.logging_config import setup_logging


def limit_content_for_log(data: Any, max_length: int = 50) -> Any:
    """
    Limit content length in data for logging to avoid flooding logs with large payloads.

    Args:
        data: Data to limit (dict, list, str, or other)
        max_length: Maximum length for string values (default: 50 chars)

    Returns:
        Data with limited content length
    """
    if isinstance(data, dict):
        limited = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value) > max_length:
                limited[key] = f"{value[:max_length]}... (truncated, total: {len(value)} chars)"
            elif isinstance(value, (dict, list)):
                limited[key] = limit_content_for_log(value, max_length)
            else:
                limited[key] = value
        return limited
    elif isinstance(data, list):
        return [limit_content_for_log(item, max_length) for item in data]
    elif isinstance(data, str) and len(data) > max_length:
        return f"{data[:max_length]}... (truncated, total: {len(data)} chars)"
    else:
        return data


class _LoguruInterceptHandler(logging.Handler):
    """Route standard logging records through Loguru so formatting stays consistent."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Apply content limiting to arguments before formatting the message
        # This prevents large base64 strings and other large data from flooding logs
        message = None
        if record.args:
            try:
                # Limit content in each argument
                limited_args = tuple(limit_content_for_log(arg) for arg in record.args)
                # Format message with limited args
                # Handle both %-style formatting and {} style formatting
                if isinstance(record.msg, str):
                    try:
                        # Try %-style formatting first (most common in logging)
                        message = record.msg % limited_args
                    except (TypeError, ValueError):
                        # Fallback to .format() if % fails
                        try:
                            message = record.msg.format(*limited_args)
                        except (IndexError, KeyError, ValueError):
                            # If both fail, just use the msg with args as string representation
                            message = f"{record.msg} {limited_args}"
                else:
                    # If msg is not a string, convert to string representation
                    message = str(record.msg) + " " + str(limited_args)
            except Exception:
                # Fallback: if something goes wrong, use original message and limit it
                message = record.getMessage()
                # Try to parse as JSON and limit if possible
                try:
                    parsed = json.loads(message)
                    limited = limit_content_for_log(parsed)
                    message = json.dumps(limited, default=str)
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, just limit as string if too long
                    if len(message) > 500:
                        message = limit_content_for_log(message, max_length=200)
        else:
            # No args, work with the message directly
            message = record.getMessage()
            # Try to parse as JSON and limit if possible
            try:
                parsed = json.loads(message)
                limited = limit_content_for_log(parsed)
                message = json.dumps(limited, default=str)
            except (json.JSONDecodeError, TypeError):
                # Not JSON, just limit as string if too long
                if len(message) > 500:
                    message = limit_content_for_log(message, max_length=200)

        # Patch loguru record to use the actual source location from LogRecord
        # This ensures we show the correct file/function/line instead of logging internals
        def patch_record(log_record):
            log_record["name"] = record.name
            log_record["file"] = record.pathname
            log_record["function"] = record.funcName or "<unknown>"
            log_record["line"] = record.lineno

        logger.patch(patch_record).opt(exception=record.exc_info).log(level, message)


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
