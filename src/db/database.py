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

    # ── Unified Jobs ─────────────────────────────────────────────────────────

    def job_insert(
        self,
        job_id: str,
        job_type: str,
        drive_type: str,
        source: str,
        destination: str,
        status: str = "pending",
        phase: str = "downloading",
    ) -> int:
        """Insert a new job (sync or cloud_download). Returns the inserted row id."""
        return self.execute_last_id(
            """
            INSERT INTO jobs (job_id, type, drive_type, source, destination, status, phase)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (job_id, job_type, drive_type, source, destination, status, phase),
        )

    def job_update(
        self,
        job_id: str,
        status: str,
        phase: str | None = None,
        progress_bytes: int = 0,
        total_bytes: int = 0,
        error_message: str | None = None,
        finished_at=None,
    ) -> int:
        """Update job status/progress. Returns rows affected."""
        if phase is not None:
            return self.execute(
                """
                UPDATE jobs
                SET status = %s, phase = %s, progress_bytes = %s, total_bytes = %s,
                    error_message = %s, finished_at = %s, updated_at = NOW()
                WHERE job_id = %s
                """,
                (status, phase, progress_bytes, total_bytes, error_message, finished_at, job_id),
            )
        else:
            return self.execute(
                """
                UPDATE jobs
                SET status = %s, progress_bytes = %s, total_bytes = %s,
                    error_message = %s, finished_at = %s, updated_at = NOW()
                WHERE job_id = %s
                """,
                (status, progress_bytes, total_bytes, error_message, finished_at, job_id),
            )

    def job_get(self, job_id: str) -> dict[str, Any] | None:
        """Get a job by job_id."""
        return self.fetch_one(
            "SELECT * FROM jobs WHERE job_id = %s",
            (job_id,),
        )

    def job_get_pending(self, job_type: str | None = None) -> list[dict[str, Any]]:
        """Get all pending/running jobs, optionally filtered by type."""
        if job_type:
            return self.fetch_all(
                "SELECT * FROM jobs WHERE status IN ('pending', 'running') AND type = %s",
                (job_type,),
            )
        return self.fetch_all(
            "SELECT * FROM jobs WHERE status IN ('pending', 'running')",
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