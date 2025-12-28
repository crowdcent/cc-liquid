"""Logging configuration utilities using loguru.

This module provides logging configuration for the cc-flow application.
"""

from __future__ import annotations

import sys

from loguru import logger


def configure_logging(
    level: str = "INFO",
    log_file: str | None = None,
    rotation: str = "100 MB",
    retention: str = "1 week"
):
    """Configure loguru logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        rotation: When to rotate logs
        retention: How long to keep old logs

    Returns:
        Configured logger instance
    """
    # Remove default handler
    logger.remove()

    # Add console handler with nice formatting
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # Add file handler if specified
    if log_file:
        logger.add(
            log_file,
            level=level,
            rotation=rotation,
            retention=retention,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )

    return logger


# Default logger instance
log = configure_logging()
