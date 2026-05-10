"""Application configuration — loads YAML and supports environment variable overrides.

Priority: environment variable > YAML config file > built-in default

Environment variables:
    CLOUD_DB_HOST          — database host (default: localhost)
    CLOUD_DB_PORT          — database port (default: 3306)
    CLOUD_DB_USER          — database username (default: root)
    CLOUD_DB_PASSWORD      — database password (default: empty)
    CLOUD_DB_NAME          — database name (default: cloud_drive_manager)
    CLOUD_APP_HOST         — HTTP server bind host (default: 127.0.0.1)
    CLOUD_APP_PORT         — HTTP server port (default: 29312)
    CLOUD_MCP_PORT         — MCP server port (default: 29313)
    CLOUD_ENCRYPTION_SALT  — Fernet key salt (auto-generated if unset)
    CLOUD_RCLONE_PATH      — path to rclone binary (default: rclone)
    CLOUD_ENV              — environment name dev/prod (default: dev)
    CLOUD_CONFIG_FILE      — explicit path to YAML config (overrides env-based lookup)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from cryptography.fernet import Fernet

from src.core.logger import get_logger

logger = get_logger("config")


def _env_str(key: str, default: str = "") -> str:
    """Read a string environment variable, falling back to default."""
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    """Read an integer environment variable, falling back to default."""
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        logger.warning(f"Invalid integer for {key}: {val}, using default {default}")
        return default


class Config:
    """Application configuration singleton.

    Loads from config/config_{ENV}.yaml where ENV comes from:
      1. CLOUD_ENV environment variable
      2. Constructor argument
      3. Default: 'dev'

    Every property supports override via environment variable (CLOUD_* prefix),
    so callers never need to provide a YAML file for basic operation.
    """

    _instance: Config | None = None

    def __init__(self, data: dict[str, Any]):
        self._data = data
        self._fernet: Fernet | None = None
        self._fernet_key: bytes | None = None

    @classmethod
    def get(cls, env: str | None = None) -> "Config":
        """Get or create the singleton Config instance.

        On first call, loads YAML from config/config_{env}.yaml.
        If the file is missing, proceeds with an empty dict (all defaults + env vars).
        """
        if cls._instance is None:
            env = env or _env_str("CLOUD_ENV", "dev")
            config_path = cls._find_config(env)
            if config_path:
                logger.info(f"Loading config from {config_path}")
                data = cls._load_yaml(config_path)
            else:
                logger.info(
                    f"No config file found for env={env}, using defaults + environment variables. "
                    f"Set CLOUD_CONFIG_FILE to an explicit path if needed."
                )
                data = {}
            cls._instance = cls(data)
        return cls._instance

    @classmethod
    def _find_config(cls, env: str) -> Path | None:
        """Locate config file. Returns None if not found (caller uses defaults)."""
        explicit = os.getenv("CLOUD_CONFIG_FILE")
        if explicit:
            p = Path(explicit)
            if p.exists():
                return p
            logger.warning(f"CLOUD_CONFIG_FILE={explicit} not found, falling back")

        repo_root = Path(__file__).parent.parent.parent
        candidates = [
            Path.cwd() / "config" / f"config_{env}.yaml",
            repo_root / "config" / f"config_{env}.yaml",
            Path(f"config/config_{env}.yaml"),
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    @classmethod
    def _load_yaml(cls, path: Path) -> dict[str, Any]:
        """Load and parse YAML config file."""
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

    def reload(self) -> None:
        """Force reload from disk."""
        env = _env_str("CLOUD_ENV", "dev")
        path = self._find_config(env)
        self._data = self._load_yaml(path) if path else {}
        self._fernet = None
        self._fernet_key = None
        logger.info("Config reloaded")

    # ── Internal helper ──────────────────────────────────────────────────────

    def _val(self, yaml_path: str, default: Any, env_var: str | None = None) -> Any:
        """Resolve a config value: env var > YAML > default.

        Args:
            yaml_path: Dot-separated path into YAML (e.g. "database.host")
            default: Fallback value if nothing is configured
            env_var: Optional environment variable name (auto-derived from yaml_path if None)
        """
        if env_var is None:
            # Auto-derive: "database.host" → "CLOUD_DB_HOST"
            parts = yaml_path.replace(".", "_").upper()
            env_var = f"CLOUD_{parts}"

        # 1. Environment variable (highest priority)
        env_val = os.getenv(env_var)
        if env_val is not None:
            return env_val

        # 2. YAML config
        keys = yaml_path.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict):
                node = node.get(k)
            else:
                return default
            if node is None:
                return default

        # 3. YAML value found
        return node

    # ── Database ─────────────────────────────────────────────────────────────

    @property
    def database_host(self) -> str:
        return str(self._val("database.host", "localhost", "CLOUD_DB_HOST"))

    @property
    def database_port(self) -> int:
        raw = self._val("database.port", 3306, "CLOUD_DB_PORT")
        return int(raw) if raw is not None else 3306

    @property
    def database_username(self) -> str:
        return str(self._val("database.username", "root", "CLOUD_DB_USER"))

    @property
    def database_password(self) -> str:
        return str(self._val("database.password", "", "CLOUD_DB_PASSWORD"))

    @property
    def database_name(self) -> str:
        return str(self._val("database.name", "cloud_drive_manager", "CLOUD_DB_NAME"))

    # ── App ──────────────────────────────────────────────────────────────────

    @property
    def app_host(self) -> str:
        return str(self._val("app.host", "127.0.0.1", "CLOUD_APP_HOST"))

    @property
    def app_port(self) -> int:
        raw = self._val("app.port", 29312, "CLOUD_APP_PORT")
        return int(raw) if raw is not None else 29312

    @property
    def mcp_port(self) -> int:
        return _env_int("CLOUD_MCP_PORT", 29313)

    @property
    def app_debug(self) -> bool:
        raw = self._val("app.debug", False)
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("true", "1", "yes")

    @property
    def env(self) -> str:
        return _env_str("CLOUD_ENV", "dev")

    # ── Encryption ───────────────────────────────────────────────────────────

    @property
    def encryption_salt(self) -> str:
        return str(self._val("encryption.salt", "", "CLOUD_ENCRYPTION_SALT"))

    @property
    def fernet_key(self) -> bytes:
        """Return Fernet key as bytes, auto-generating one if not configured."""
        salt = self.encryption_salt
        if salt:
            return salt.encode("utf-8")
        # Auto-generate a deterministic key for this session (NOT for production)
        key = Fernet.generate_key()
        logger.warning("No encryption.salt configured — using auto-generated key. "
                       "Set CLOUD_ENCRYPTION_SALT for persistence across restarts.")
        return key

    def get_fernet(self) -> Fernet:
        """Get a Fernet cipher instance (lazy init)."""
        if self._fernet is None:
            key = self.fernet_key
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
        return str(self._val("cloud_drives.rclone_path", "rclone", "CLOUD_RCLONE_PATH"))

    @property
    def cloud_timeout(self) -> int:
        raw = self._val("cloud_drives.timeout", 300)
        return int(raw) if raw is not None else 300

    @property
    def max_concurrent_syncs(self) -> int:
        raw = self._val("cloud_drives.max_concurrent_syncs", 5)
        return int(raw) if raw is not None else 5

    @property
    def max_retry(self) -> int:
        raw = self._val("cloud_drives.max_retry", 10)
        return int(raw) if raw is not None else 10

    # ── Logging ──────────────────────────────────────────────────────────────

    @property
    def log_level(self) -> int:
        raw = str(self._val("logging.level", "INFO")).upper()
        return getattr(logging, raw, logging.INFO)

    @property
    def log_file(self) -> str | None:
        val = self._val("logging.file", None)
        return str(val) if val else None

    @property
    def log_format(self) -> str:
        return str(self._val("logging.format", "json"))

    # ── Generic access ───────────────────────────────────────────────────────

    def get_value(self, key: str, default: Any = None) -> Any:
        """Access any config value by dot-notation key (e.g., 'database.host')."""
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
        return self.get_value(key)
