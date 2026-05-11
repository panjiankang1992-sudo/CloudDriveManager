"""Unit tests for src/core/config.py"""

import pytest
import os

from src.core.config import Config


class TestConfigGet:
    def setup_method(self):
        Config._instance = None

    def teardown_method(self):
        Config._instance = None

    def test_get_returns_singleton(self):
        cfg1 = Config.get()
        cfg2 = Config.get()
        assert cfg1 is cfg2

    def test_env_defaults_to_dev(self):
        cfg = Config.get()
        assert cfg.env == "dev"

    def test_database_defaults(self):
        cfg = Config.get()
        assert cfg.database_host == "localhost"
        assert cfg.database_port == 3306
        assert cfg.database_username == "root"
        assert cfg.database_name == "cloud_drive_manager"

    def test_app_defaults(self):
        cfg = Config.get()
        assert cfg.app_host == "127.0.0.1"
        assert cfg.app_port == 29312

    def test_rclone_path_defaults(self):
        cfg = Config.get()
        assert cfg.rclone_path == "rclone"

    def test_cloud_timeout_defaults(self):
        cfg = Config.get()
        assert cfg.cloud_timeout == 300

    def test_max_concurrent_syncs_defaults(self):
        cfg = Config.get()
        assert cfg.max_concurrent_syncs == 5

    def test_max_retry_defaults(self):
        cfg = Config.get()
        assert cfg.max_retry == 10

    def test_encryption_salt_empty_by_default(self):
        cfg = Config.get()
        assert cfg.encryption_salt == ""

    def test_fernet_key_generated(self):
        cfg = Config.get()
        key = cfg.fernet_key
        assert key is not None
        assert len(key) > 0

    def test_encrypt_decrypt_password(self):
        cfg = Config.get()
        original = "my_secret_password"
        encrypted = cfg.encrypt_password(original)
        decrypted = cfg.decrypt_password(encrypted)
        assert decrypted == original
        assert encrypted != original

    def test_get_value_with_dot_notation(self):
        cfg = Config.get()
        # These use defaults since no YAML is loaded in test
        host = cfg.get_value("database.host")
        assert host is not None

    def test_get_value_returns_default_for_missing(self):
        cfg = Config.get()
        value = cfg.get_value("nonexistent.key", "default_value")
        assert value == "default_value"


class TestConfigEnvOverride:
    def setup_method(self):
        Config._instance = None

    def teardown_method(self):
        Config._instance = None
        # Clean up env vars
        for key in ["CLOUD_DB_HOST", "CLOUD_APP_PORT", "CLOUD_RCLONE_PATH"]:
            if key in os.environ:
                del os.environ[key]

    def test_env_var_overrides_yaml(self):
        os.environ["CLOUD_DB_HOST"] = "testhost"
        Config._instance = None
        cfg = Config.get()
        assert cfg.database_host == "testhost"

    def test_env_var_overrides_defaults(self):
        os.environ["CLOUD_APP_PORT"] = "9999"
        Config._instance = None
        cfg = Config.get()
        assert cfg.app_port == 9999

    def test_rclone_path_from_env(self):
        os.environ["CLOUD_RCLONE_PATH"] = "/custom/rclone"
        Config._instance = None
        cfg = Config.get()
        assert cfg.rclone_path == "/custom/rclone"
