"""MySQL database connection management."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator, cast

import pymysql
from pymysql.cursors import DictCursor

from src.core.config import Config
from src.core.logger import get_logger

logger = get_logger("database")


class Database:
    """MySQL database connection manager (lazy singleton)."""

    _instance: Database | None = None

    def __init__(self):
        self._cfg: Config = Config.get()
        self._pool: dict[str, pymysql.Connection] = {}

    @classmethod
    def get(cls) -> Database:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def connection(self, database: str | None = None) -> pymysql.Connection:
        """Get a MySQL connection (thread-safe per database)."""
        db = database or self._cfg.database_name
        if db not in self._pool or not self._pool[db].open:
            logger.info(f"Connecting to MySQL {db} at {self._cfg.database_host}:{self._cfg.database_port}")
            self._pool[db] = pymysql.connect(
                host=self._cfg.database_host,
                port=self._cfg.database_port,
                user=self._cfg.database_username,
                password=self._cfg.database_password,
                database=db,
                charset="utf8mb4",
                cursorclass=DictCursor,
                autocommit=True,
            )
        return self._pool[db]

    @contextmanager
    def cursor(self, database: str | None = None) -> Generator[DictCursor, None, None]:
        """Context manager for executing queries.

        Usage:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM sync_jobs")
                rows = cur.fetchall()
        """
        conn = self.connection(database)
        try:
            with conn.cursor(DictCursor) as cur:
                yield cur
        except pymysql.Error as e:
            logger.error(f"MySQL error: {e}")
            raise

    def execute(self, sql: str, params: tuple[Any, ...] | None = None, database: str | None = None) -> int:
        """Execute INSERT/UPDATE/DELETE and return rows affected."""
        with self.cursor(database) as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def execute_last_id(self, sql: str, params: tuple[Any, ...] | None = None, database: str | None = None) -> int:
        """Execute INSERT and return the last inserted id."""
        with self.cursor(database) as cur:
            cur.execute(sql, params)
            return cur.lastrowid

    def fetch_one(self, sql: str, params: tuple[Any, ...] | None = None, database: str | None = None) -> dict[str, Any] | None:
        """Execute SELECT and return first row."""
        with self.cursor(database) as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def fetch_all(self, sql: str, params: tuple[Any, ...] | None = None, database: str | None = None) -> list[dict[str, Any]]:
        """Execute SELECT and return all rows."""
        with self.cursor(database) as cur:
            cur.execute(sql, params)
            return cast("list[dict[str, Any]]", cast(object, cur.fetchall()))

    # ── Cloud Download Jobs ─────────────────────────────────────────────────────

    def cloud_download_job_insert(
        self,
        task_id: str,
        urls: str,
        folder: str,
        status: str = "pending",
    ) -> int:
        """Insert a new cloud download job. Returns the inserted row id."""
        return self.execute_last_id(
            """
            INSERT INTO cloud_download_jobs (task_id, urls, folder, status)
            VALUES (%s, %s, %s, %s)
            """,
            (task_id, urls, folder, status),
        )

    def cloud_download_job_update_status(
        self,
        task_id: str,
        status: str,
        error_message: str | None = None,
        finished_at: datetime | None = None,
    ) -> int:
        """Update cloud download job status. Returns rows affected."""
        return self.execute(
            """
            UPDATE cloud_download_jobs
            SET status = %s, error_message = %s, finished_at = %s
            WHERE task_id = %s
            """,
            (status, error_message, finished_at, task_id),
        )

    def cloud_download_job_get(self, task_id: str) -> dict[str, Any] | None:
        """Get a cloud download job by task_id."""
        return self.fetch_one(
            "SELECT * FROM cloud_download_jobs WHERE task_id = %s",
            (task_id,),
        )

    def cloud_download_job_get_pending(self) -> list[dict[str, Any]]:
        """Get all pending/downloading cloud download jobs for watchdog tracking."""
        return self.fetch_all(
            "SELECT * FROM cloud_download_jobs WHERE status IN ('pending', 'downloading')",
        )

    def cloud_download_job_mark_timeout(self, task_id: str) -> int:
        """Mark a job as TIMEOUT and set finished_at."""
        return self.cloud_download_job_update_status(
            task_id, "timeout", "Task exceeded 30 minute timeout", datetime.now(timezone.utc)
        )

    def close(self, database: str | None = None) -> None:
        """Close connection(s)."""
        if database:
            if database in self._pool:
                self._pool[database].close()
                del self._pool[database]
        else:
            for conn in self._pool.values():
                conn.close()
            self._pool.clear()