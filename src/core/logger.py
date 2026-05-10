"""Structured JSON logger — SC-008 compliant.

Each log entry contains: timestamp, level, logger, message, extra.
"""

import logging
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Format log records as JSON with timestamp/level/logger/message/extra."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "extra": getattr(record, "extra", {}),
        }
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logger(name: str, log_file: str | None = None, level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger with JSON output to file and console.

    Args:
        name: Logger name (e.g., "sync_api", "pikpak_api")
        log_file: Path to log file (json lines). If None, only console output.
        level: Logging level (default INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    # JSON file handler (buffered, flush ≤ 5s)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(JSONFormatter())
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    # Console handler (human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get an existing logger or a minimal fallback.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
