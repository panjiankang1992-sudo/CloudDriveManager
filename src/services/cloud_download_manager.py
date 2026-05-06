"""Cloud download job manager — tracks PikPak offline download tasks.

Manages the lifecycle of cloud download jobs:
  PENDING → RUNNING → COMPLETED / FAILED / TIMEOUT

The watchdog thread runs every 60 seconds and marks any job that has been
in PENDING or RUNNING state for more than 2 hours as TIMEOUT.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.core.logger import get_logger
from src.db.database import Database

logger = get_logger("cloud_download_mgr")

WATCHDOG_INTERVAL_SECS = 60
JOB_TIMEOUT_SECS = 2 * 60 * 60  # 2 hours


class _CloudDownloadState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class CloudDownloadJob:
    """In-memory representation of a cloud download job."""
    task_id: str
    urls: list[str]
    folder: str
    status: _CloudDownloadState = _CloudDownloadState.PENDING
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None


class CloudDownloadJobManager:
    """Manages cloud download jobs with a background watchdog thread.

    Uses a watchdog thread that wakes every 60 seconds and marks any
    job older than 2 hours as TIMEOUT.
    """

    def __init__(self):
        self._db = Database.get()
        self._jobs: dict[str, CloudDownloadJob] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._watchdog_thread: threading.Thread | None = None
        self._started = False

    # ── Public API ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the watchdog background thread (idempotent)."""
        if self._started:
            return
        self._stop_event.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            name="cloud_download_watchdog",
            daemon=True,
        )
        self._watchdog_thread.start()
        self._started = True
        logger.info("CloudDownloadJobManager watchdog started")

    def stop(self) -> None:
        """Stop the watchdog thread."""
        if not self._started:
            return
        self._stop_event.set()
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=5)
        self._started = False
        logger.info("CloudDownloadJobManager watchdog stopped")

    def create_job(self, urls: list[str], folder: str = "/My Pack") -> CloudDownloadJob:
        """Create and persist a new cloud download job.

        Args:
            urls: List of HTTP/magnet URLs to download.
            folder: Destination folder on PikPak.

        Returns:
            The created CloudDownloadJob.
        """
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        job = CloudDownloadJob(
            task_id=task_id,
            urls=urls,
            folder=folder,
            status=_CloudDownloadState.PENDING,
            created_at=now,
            updated_at=now,
        )

        # Persist to DB
        urls_json = json.dumps(urls)
        db_id = self._db.cloud_download_job_insert(task_id, urls_json, folder, "pending")
        job.id = db_id  # type: ignore[reportAttributeAccessIssue]

        with self._lock:
            self._jobs[task_id] = job

        logger.info(f"Cloud download job created: {task_id} ({len(urls)} URLs -> {folder})")
        return job

    def update_status(
        self,
        task_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update job status in memory and DB.

        Valid statuses: pending, running, completed, failed, timeout
        """
        with self._lock:
            job = self._jobs.get(task_id)
            if job is None:
                logger.warning(f"update_status: job not found {task_id}")
                return

            job.status = _CloudDownloadState(status)
            job.error_message = error_message
            job.updated_at = datetime.now(timezone.utc)
            if status in ("completed", "failed", "timeout"):
                job.finished_at = datetime.now(timezone.utc)

        # Persist to DB
        self._db.cloud_download_job_update_status(
            task_id,
            status,
            error_message,
            job.finished_at,
        )

        logger.info(f"Cloud download job {task_id} status -> {status}")

    def get_job(self, task_id: str) -> CloudDownloadJob | None:
        """Get a job by task_id (in-memory only)."""
        return self._jobs.get(task_id)

    def load_pending_from_db(self) -> None:
        """Reload pending/running jobs from DB into memory on startup."""
        rows = self._db.cloud_download_job_get_pending()
        with self._lock:
            for row in rows:
                task_id = row["task_id"]
                urls = json.loads(row["urls"])
                job = CloudDownloadJob(
                    task_id=task_id,
                    urls=urls,
                    folder=row["folder"],
                    status=_CloudDownloadState(row["status"]),
                    error_message=row.get("error_message"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    finished_at=row.get("finished_at"),
                )
                self._jobs[task_id] = job
        logger.info(f"Loaded {len(rows)} pending/running jobs from DB")

    # ── Watchdog ────────────────────────────────────────────────────────────

    def _watchdog_loop(self) -> None:
        """Background loop: check job age every WATCHDOG_INTERVAL_SECS."""
        while not self._stop_event.wait(WATCHDOG_INTERVAL_SECS):
            self._check_timeouts()

    def _check_timeouts(self) -> None:
        """Mark any job older than JOB_TIMEOUT_SECS as TIMEOUT."""
        now = datetime.now(timezone.utc)
        aged_task_ids: list[str] = []

        with self._lock:
            for task_id, job in self._jobs.items():
                if job.status in (_CloudDownloadState.PENDING, _CloudDownloadState.RUNNING):
                    age_secs = (now - job.created_at).total_seconds()
                    if age_secs > JOB_TIMEOUT_SECS:
                        aged_task_ids.append(task_id)

        for task_id in aged_task_ids:
            logger.warning(f"Cloud download job {task_id} timed out after {JOB_TIMEOUT_SECS}s")
            self.update_status(task_id, "timeout", "Task exceeded 2 hour timeout")


# ── Module-level singleton ────────────────────────────────────────────────────

_manager: CloudDownloadJobManager | None = None
_manager_lock = threading.Lock()


def get_cloud_download_manager() -> CloudDownloadJobManager:
    """Get or create the CloudDownloadJobManager singleton."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = CloudDownloadJobManager()
                _manager.start()
                _manager.load_pending_from_db()
    return _manager
