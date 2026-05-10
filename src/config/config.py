"""Application configuration loaded from YAML files.

Two environments:
  - config_dev.yaml   → mode=dev
  - config_prod.yaml  → mode=prod

Usage:
    cfg = Config.get()                 # raises if not loaded
    host = cfg.server["host"]
    pikpak_cfg = cfg.pikpak            # CloudDriveConfig
"""

from pathlib import Path
from typing import Any, Dict, Optional

import sys
from pathlib import Path
import yaml

from src.core.exceptions import (
    ConfigFileNotFoundError,
    ConfigKeyNotFoundError,
    ConfigParseError,
    ConfigValueError,
)


class _AppConfig:
    """Holds all application configuration sections."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        # Top-level sections
        self.app: Dict[str, Any] = data.get("app", {})
        self.server: Dict[str, Any] = data.get("server", {})
        self.log: Dict[str, Any] = data.get("log", {})
        self.encryption: Dict[str, Any] = data.get("encryption", {})
        self.database: Dict[str, Any] = data.get("database", {})

        # Cloud drive sections — each returns a CloudDriveConfig dict
        self.pikpak: Dict[str, Any] = data.get("pikpak", {})
        self.jianguoyun: Dict[str, Any] = data.get("jianguoyun", {})
        self.baidu: Dict[str, Any] = data.get("baidu", {})
        self.aliyun: Dict[str, Any] = data.get("aliyun", {})
        self.quark: Dict[str, Any] = data.get("quark", {})

    def get_raw(self, *keys: str, default: Any = None) -> Any:
        """Navigate nested dict by keys, raise ConfigKeyNotFoundError if missing."""
        val = self._data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                raise ConfigKeyNotFoundError(
                    message=f"Config key not found: {'.'.join(keys)}",
                    detail=f"Missing key '{k}' in config path {'.'.join(keys)}.",
                )
        return val


class Config:
    """Singleton configuration loader.

    Call Config.load(env) once at startup, then Config.get() everywhere.
    Raises on missing file or invalid YAML.
    """

    _instance: Optional[_AppConfig] = None
    _env: Optional[str] = None

    @classmethod
    def load(cls, env: str = "dev") -> _AppConfig:
        """Load configuration from config_{env}.yaml.

        Args:
            env: 'dev' or 'prod'.

        Returns:
            The loaded _AppConfig instance.
        """
        if env not in ("dev", "prod"):
            raise ConfigValueError(
                message=f"Invalid environment: {env}",
                detail="env must be 'dev' or 'prod'.",
            )

        # Resolve config path: in dev it's relative to this file, in PyInstaller bundle it's sys._MEIPASS
        if getattr(sys, "frozen", False):
            # Running as PyInstaller onefile bundle
            bundle_root = Path(sys._MEIPASS)
            config_file = bundle_root / "config" / f"config_{env}.yaml"
        else:
            # Running as normal Python script
            config_file = Path(__file__).parent.parent.parent / "config" / f"config_{env}.yaml"
        if not config_file.exists():
            raise ConfigFileNotFoundError(
                message=f"Configuration file not found: {config_file}",
                detail=f"Ensure config/config_{env}.yaml exists.",
            )

        try:
            with open(config_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigParseError(
                message=f"Failed to parse YAML: {e}",
                detail="Check your config file for syntax errors.",
            )

        cls._instance = _AppConfig(data)
        cls._env = env
        return cls._instance

    @classmethod
    def get(cls) -> _AppConfig:
        """Return the loaded configuration.

        Raises:
            ConfigError: If load() has not been called.
        """
        if cls._instance is None:
            raise ConfigKeyNotFoundError(
                message="Configuration not loaded.",
                detail="Call Config.load('dev') or Config.load('prod') at startup.",
            )
        return cls._instance

    @classmethod
    def env(cls) -> str:
        """Return the active environment name ('dev' or 'prod')."""
        if cls._env is None:
            return "dev"
        return cls._env
