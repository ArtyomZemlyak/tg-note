"""
Logging Configuration with Loguru
Centralized logging setup for the application
"""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(
    log_level: str = "INFO", log_file: Path | None = None, enable_debug_trace: bool = False
):
    """
    Setup loguru logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        enable_debug_trace: Enable detailed DEBUG tracing for agents
    """
    # Remove default handler
    logger.remove()

    # Add console handler with formatting
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Console output
    logger.add(
        sys.stdout, format=log_format, level=log_level, colorize=True, backtrace=True, diagnose=True
    )

    # File output if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Regular log file
        logger.add(
            log_file,
            format=log_format,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            backtrace=True,
            diagnose=True,
        )

        # If debug tracing is enabled, create a separate debug log
        if enable_debug_trace or log_level == "DEBUG":
            debug_log_file = log_file.parent / f"{log_file.stem}_debug{log_file.suffix}"
            logger.add(
                debug_log_file,
                format=log_format,
                level="DEBUG",
                rotation="50 MB",
                retention="3 days",
                compression="zip",
                backtrace=True,
                diagnose=True,
                filter=lambda record: record["level"].name == "DEBUG",
            )

    logger.info(
        f"Logging configured: level={log_level}, file={log_file}, debug_trace={enable_debug_trace}"
    )


def get_logger(name: str):
    """
    Get a logger instance with the given name

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logger.bind(name=name)
