"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Disable config file loading during tests to avoid real MySQL/rclone calls
os.environ["CONFIG_ENV"] = "dev"
os.environ["RCLONE_PATH"] = "echo"  # dummy rclone for smoke tests

import pytest


@pytest.fixture
def mock_config_data():
    """Minimal valid config data for testing."""
    return {
        "app": {"name": "test_app", "version": "1.0.0"},
        "server": {"host": "0.0.0.0", "port": 8000},
        "log": {
            "level": "DEBUG",
            "max_bytes": 10485760,
            "backup_count": 3,
            "retention_days": 7,
        },
        "encryption": {"salt": ""},
        "pikpak": {"remote_name": "mypikpak", "rclone_path": "rclone"},
        "jianguoyun": {"remote_name": "myjianguoyun", "rclone_path": "rclone"},
        "baidu": {"remote_name": "mybaidu", "rclone_path": "rclone"},
        "aliyun": {"remote_name": "myaliyun", "rclone_path": "rclone"},
        "quark": {"remote_name": "myquark", "rclone_path": "rclone"},
    }


@pytest.fixture
def valid_fernet_key():
    """A valid Fernet key for testing encryption."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()
