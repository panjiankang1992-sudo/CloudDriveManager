"""Structured logging using Python's standard logging module.

Log format: 2026-04-26 22:35:00 | DEBUG    | module                    | message
Config source: Config (already initialized)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config.config import Config


def setup_logger() -> logging.Logger:
    """Configure and return the application logger.

    Reads log configuration from Config (must be initialized before calling).
    Creates log directory if it does not exist.
    """
    cfg = Config.get()
    log_cfg = cfg.log

    # Ensure log directory exists
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)

    log_level = getattr(logging, log_cfg.get("level", "INFO").upper())
    max_bytes: int = log_cfg.get("max_bytes", 10 * 1024 * 1024)
    backup_count: int = log_cfg.get("backup_count", 5)
    retention_days: int = log_cfg.get("retention_days", 7)

    # Console handler — always attached
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    # File handler — RotatingFileHandler
    file_handler = RotatingFileHandler(
        filename=str(log_dir / "app.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger("cloud_drive_manager")
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    root_logger.info(
        "Logger initialized | level=%s | max_bytes=%d | backup_count=%d | retention_days=%d",
        log_cfg.get("level", "INFO"),
        max_bytes,
        backup_count,
        retention_days,
    )

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a named logger under the cloud_drive_manager hierarchy."""
    return logging.getLogger(f"cloud_drive_manager.{name}")
