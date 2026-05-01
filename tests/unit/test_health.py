"""Unit tests for src/api/health.py"""

import pytest
from unittest.mock import patch, MagicMock

from src.config.config import Config, _AppConfig
from src.core.schemas import APIResponse


class TestHealthCheck:
    """Tests for GET /health endpoint."""

    def setup_method(self):
        Config._instance = None
        Config._env = None

    def teardown_method(self):
        Config._instance = None
        Config._env = None

    @pytest.mark.asyncio
    @patch("src.api.health._check_rclone")
    async def test_health_check_healthy(self, mock_check):
        mock_check.return_value = True

        # Load real config (config_dev.yaml exists)
        cfg = Config.load("dev")

        from src.api.health import health_check

        resp = await health_check()

        assert resp.code == 0
        assert resp.data is not None
        assert resp.data.status in ("healthy", "degraded")
        assert resp.data.version == "1.0.0"
        assert resp.data.env == "dev"

    @pytest.mark.asyncio
    @patch("src.api.health._check_rclone")
    async def test_health_check_degraded_when_rclone_missing(self, mock_check):
        mock_check.return_value = False

        cfg = Config.load("dev")

        from src.api.health import health_check

        resp = await health_check()

        assert resp.code == 0
        assert resp.data.status == "degraded"
        assert resp.data.rclone_available is False


class TestCheckRclone:
    """Tests for the _check_rclone helper."""

    def setup_method(self):
        Config._instance = None
        Config._env = None

    def teardown_method(self):
        Config._instance = None
        Config._env = None

    @patch("shutil.which")
    def test_check_rclone_finds_on_path(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"

        cfg = Config.load("dev")
        from src.api.health import _check_rclone

        result = _check_rclone(cfg)
        assert result is True

    @patch("shutil.which")
    def test_check_rclone_not_found(self, mock_which):
        mock_which.return_value = None

        cfg = Config.load("dev")
        from src.api.health import _check_rclone

        result = _check_rclone(cfg)
        assert result is False
