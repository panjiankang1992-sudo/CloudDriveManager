"""MySQL database connection management.

Uses PyMySQL for synchronous MySQL connections.
Falls back gracefully if MySQL is unavailable.
"""

import sys
from pathlib import Path
from typing import Optional

import pymysql
from pymysql.cursors import DictCursor

from src.core.logger import get_logger
from src.core.exceptions import CloudDriveError

logger = get_logger("db.connection")

# Re-export common exceptions for convenience
from src.core.exceptions import (
    ConfigKeyNotFoundError,
    ConfigFileNotFoundError,
)


class DatabaseConnectionError(CloudDriveError):
    """Raised when database connection fails."""
    CODE = "DATABASE_CONNECTION_ERROR"
    MESSAGE = "Failed to connect to the database."


class DatabaseConfig:
    """Holds MySQL connection configuration from config.yaml."""

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

    @classmethod
    def from_yaml(cls, cfg) -> Optional["DatabaseConfig"]:
        """Load from _AppConfig object (config_dev.yaml / config_prod.yaml).

        The password in YAML should already be encrypted with the same Fernet key
        stored in encryption.salt. It is decrypted here so that PyMySQL receives
        the plaintext password for authentication.
        """
        db_cfg = getattr(cfg, "database", {})
        if not db_cfg:
            return None
        host = db_cfg.get("host")
        if not host:
            return None

        from src.core import encryption

        encrypted_pw = db_cfg.get("password", "")
        try:
            # Decrypt if encryption has been configured and password looks encrypted
            if encrypted_pw and encryption._fernet is not None:
                password = encryption.decrypt(encrypted_pw)
            else:
                password = encrypted_pw
        except Exception:
            # Fallback: treat as plaintext (e.g. dev without encryption)
            password = encrypted_pw

        return cls(
            host=host,
            port=int(db_cfg.get("port", 3306)),
            user=db_cfg.get("user", "root"),
            password=password,
            database=db_cfg.get("database", "cloud_drive_manager"),
        )


class ConnectionManager:
    """Context-manager for MySQL connections.

    Usage:
        with ConnectionManager() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                print(cur.fetchone())
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._conn: Optional[pymysql.Connection] = None

    def __enter__(self) -> "ConnectionManager":
        try:
            self._conn = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset="utf8mb4",
                cursorclass=DictCursor,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30,
            )
            logger.debug("MySQL connected: %s:%d/%s", self.config.host, self.config.port, self.config.database)
            return self
        except pymysql.Error as e:
            logger.error("MySQL connection failed: %s", e)
            raise DatabaseConnectionError(
                message=f"Failed to connect to MySQL: {e}",
                detail=f"Check 'database' config section in config yaml.",
            )

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            self._conn.close()
            logger.debug("MySQL connection closed")

    def cursor(self):
        """Return a new cursor.

        Connects lazily if ConnectionManager was created but not entered.
        Usage (option A — context manager):
            with conn_mgr as c:
                with c.cursor() as cur:
                    cur.execute("SELECT 1")
        Usage (option B — raw cursor, auto-connects):
            cur = conn_mgr.cursor()
            cur.execute("SELECT 1")
        """
        if self._conn is None:
            # Lazy connect: user called cursor() without entering context first
            try:
                self._conn = pymysql.connect(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.user,
                    password=self.config.password,
                    database=self.config.database,
                    charset="utf8mb4",
                    cursorclass=DictCursor,
                    connect_timeout=10,
                    read_timeout=30,
                    write_timeout=30,
                )
            except pymysql.Error as e:
                raise DatabaseConnectionError(
                    message=f"Failed to connect to MySQL: {e}",
                    detail=f"Check 'database' config section in config yaml.",
                )
        return _Cursor(self._conn)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


class _Cursor:
    """Thin wrapper to make pymysql cursor usable as `with cursor()`."""

    def __init__(self, conn):
        self._cur = conn.cursor()

    def __enter__(self):
        return self._cur

    def __exit__(self, *args):
        self._cur.close()


def get_connection(cfg) -> Optional[ConnectionManager]:
    """Create a ConnectionManager from the app config object.

    Returns None if database config is not present in YAML.
    Raises DatabaseConnectionError if connection attempt fails.
    """
    db_cfg = DatabaseConfig.from_yaml(cfg)
    if not db_cfg:
        logger.info("No database configuration found — skipping DB layer")
        return None
    return ConnectionManager(db_cfg)
