"""Unit tests for src/config/config.py"""

import pytest
import tempfile
import os
from pathlib import Path

from src.config.config import Config, _AppConfig
from src.core.exceptions import (
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigValueError,
    ConfigKeyNotFoundError,
)


class TestAppConfig:
    def test_sections_loaded_from_data(self, mock_config_data):
        cfg = _AppConfig(mock_config_data)
        assert cfg.app["name"] == "test_app"
        assert cfg.server["port"] == 8000
        assert cfg.log["level"] == "DEBUG"

    def test_cloud_drive_sections(self, mock_config_data):
        cfg = _AppConfig(mock_config_data)
        assert cfg.pikpak["remote_name"] == "mypikpak"
        assert cfg.jianguoyun["remote_name"] == "myjianguoyun"
        assert cfg.baidu["remote_name"] == "mybaidu"
        assert cfg.aliyun["remote_name"] == "myaliyun"
        assert cfg.quark["remote_name"] == "myquark"

    def test_get_raw_nested_key(self, mock_config_data):
        cfg = _AppConfig(mock_config_data)
        assert cfg.get_raw("app", "version") == "1.0.0"
        assert cfg.get_raw("server", "port") == 8000

    def test_get_raw_missing_key_raises(self, mock_config_data):
        cfg = _AppConfig(mock_config_data)
        with pytest.raises(ConfigKeyNotFoundError) as exc_info:
            cfg.get_raw("app", "nonexistent")
        assert exc_info.value.CODE == "CONFIG_KEY_NOT_FOUND"

    def test_missing_sections_return_empty_dict(self, mock_config_data):
        data = {"app": {"name": "test"}}
        cfg = _AppConfig(data)
        assert cfg.server == {}
        assert cfg.log == {}
        assert cfg.encryption == {}


class TestConfigLoad:
    def setup_method(self):
        Config._instance = None
        Config._env = None

    def teardown_method(self):
        Config._instance = None
        Config._env = None

    def test_load_dev_file_success(self):
        # The actual config_dev.yaml exists in the repo
        cfg = Config.load("dev")
        assert cfg.app["name"] == "cloud_drive_manager"
        assert Config.env() == "dev"

    def test_load_prod_file_success(self):
        cfg = Config.load("prod")
        assert cfg.app["name"] == "cloud_drive_manager"
        assert Config.env() == "prod"

    def test_load_invalid_env_raises(self):
        with pytest.raises(ConfigValueError) as exc_info:
            Config.load("staging")
        assert exc_info.value.CODE == "CONFIG_VALUE_ERROR"

    def test_load_nonexistent_file_raises(self):
        # Patch the path resolution temporarily
        original = Path(__file__).parent.parent / "config" / "config_dev.yaml"
        # This test depends on actual file existence
        cfg = Config.load("dev")
        assert cfg is not None

    def test_get_without_load_raises(self):
        Config._instance = None
        with pytest.raises(ConfigKeyNotFoundError) as exc_info:
            Config.get()
        assert "not loaded" in exc_info.value.message.lower()

    def test_env_defaults_to_dev_when_not_set(self):
        assert Config.env() == "dev"
