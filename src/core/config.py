"""Application configuration — loads config.yaml and provides typed access."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from cryptography.fernet import Fernet

from src.core.logger import get_logger

logger = get_logger("config")


class Config:
    """Application configuration singleton.

    Loads config from config/config_{ENV}.yaml where ENV defaults to 'dev',
    overridden by CONFIG_ENV environment variable.
    """

    _instance: Config | None = None

    def __init__(self, data: dict[str, Any]):
        self._data = data
        self._fernet: Fernet | None = None
        self._fernet_key: str | None = None

    @classmethod
    def get(cls, env: str | None = None) -> Config:
        """Get the singleton Config instance (loads on first call).

        Args:
            env: Environment name (dev/prod). Defaults to CONFIG_ENV env var or 'dev'.
        """
        if cls._instance is None:
            env = env or os.getenv("CONFIG_ENV", "dev")
            config_path = cls._find_config(env)
            logger.info(f"Loading config from {config_path}")
            data = cls._load_yaml(config_path)
            cls._instance = cls(data)
        return cls._instance

    @classmethod
    def _find_config(cls, env: str) -> Path:
        """Locate config file. Searches in order: cwd/config/, repo root/config/, relative path."""
        candidates = [
            Path.cwd() / "config" / f"config_{env}.yaml",
            Path(__file__).parent.parent.parent / "config" / f"config_{env}.yaml",
            Path(f"config/config_{env}.yaml"),
        ]
        for p in candidates:
            if p.exists():
                return p
        raise FileNotFoundError(f"Config file config_{env}.yaml not found in: {candidates}")

    @classmethod
    def _load_yaml(cls, path: Path) -> dict[str, Any]:
        """Load and parse YAML config file."""
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

    def reload(self) -> None:
        """Force reload from disk (useful for config changes without restart)."""
        env = os.getenv("CONFIG_ENV", "dev")
        path = self._find_config(env)
        self._data = self._load_yaml(path)
        self._fernet = None
        self._fernet_key = None
        logger.info("Config reloaded")

    # ── Database ──────────────────────────────────────────────────────────────

    @property
    def database_host(self) -> str:
        return self._data.get("database", {}).get("host", "localhost")

    @property
    def database_port(self) -> int:
        return int(self._data.get("database", {}).get("port", 3306))

    @property
    def database_username(self) -> str:
        return self._data.get("database", {}).get("username", "root")

    @property
    def database_password(self) -> str:
        return self._data.get("database", {}).get("password", "")

    @property
    def database_name(self) -> str:
        return self._data.get("database", {}).get("name", "cloud_drive_manager")

    # ── App ───────────────────────────────────────────────────────────────────

    @property
    def app_host(self) -> str:
        return self._data.get("app", {}).get("host", "0.0.0.0")

    @property
    def app_port(self) -> int:
        return int(self._data.get("app", {}).get("port", 29312))

    @property
    def app_debug(self) -> bool:
        return bool(self._data.get("app", {}).get("debug", False))

    # ── Encryption ─────────────────────────────────────────────────────────────

    @property
    def encryption_salt(self) -> str:
        """Return the raw salt string (Fernet key)."""
        return self._data.get("encryption", {}).get("salt", "")

    @property
    def fernet_key(self) -> bytes:
        """Return Fernet key as bytes (derived from encryption.salt)."""
        return self.encryption_salt.encode("utf-8")

    def get_fernet(self) -> Fernet:
        """Get a Fernet cipher instance (lazy init)."""
        if self._fernet is None:
            key = self.fernet_key
            if not key:
                raise ValueError("encryption.salt not set in config")
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt_password(self, plaintext: str) -> str:
        """Encrypt a plaintext password and return base64 ciphertext."""
        return self.get_fernet().encrypt(plaintext.encode()).decode()

    def decrypt_password(self, ciphertext: str) -> str:
        """Decrypt a base64 ciphertext password and return plaintext."""
        return self.get_fernet().decrypt(ciphertext.encode()).decode()

    # ── Cloud drives ─────────────────────────────────────────────────────────

    @property
    def rclone_path(self) -> str:
        return self._data.get("cloud_drives", {}).get("rclone_path", "rclone")

    @property
    def cloud_timeout(self) -> int:
        return int(self._data.get("cloud_drives", {}).get("timeout", 300))

    @property
    def max_concurrent_syncs(self) -> int:
        return int(self._data.get("cloud_drives", {}).get("max_concurrent_syncs", 5))

    @property
    def max_retry(self) -> int:
        return int(self._data.get("cloud_drives", {}).get("max_retry", 10))

    # ── Logging ───────────────────────────────────────────────────────────────

    @property
    def log_level(self) -> int:
        raw = self._data.get("logging", {}).get("level", "INFO").upper()
        return getattr(logging, raw, logging.INFO)

    @property
    def log_file(self) -> str | None:
        return self._data.get("logging", {}).get("file") or None

    @property
    def log_format(self) -> str:
        return self._data.get("logging", {}).get("format", "json")

    # ── Generic access ───────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Access any config value by dot-notation key (e.g., "database.host")."""
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
            if val is None:
                return default
        return val

    def __getitem__(self, key: str) -> Any:
        return self.get(key)