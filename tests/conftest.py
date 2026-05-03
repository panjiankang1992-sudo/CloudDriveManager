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