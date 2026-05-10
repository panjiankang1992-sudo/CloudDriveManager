"""Async sync job manager — coordinates background file sync from cloud to local (FR-006 to FR-012).

Uses an in-memory dict + ThreadPoolExecutor (max 5 concurrent) for a personal-tool
scale implementation. No Redis/Celery required.
"""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, Future as FutureBase
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from src.core.config import Config
from src.core.logger import get_logger
from src.core.exceptions import JobNotFoundError, InvalidJobStateError, OperationQueueFullError
from src.core.schemas import DriveType, SyncJobSchema, SyncStatus, SyncPhase
from src.db.database import Database

logger = get_logger("sync_manager")

MAX_CONCURRENT_JOBS = 5


class _JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class _SyncJob:
    """In-memory sync job representation."""
    job_id: str
    drive_type: str
    source_path: str
    local_path: str
    status: _JobState = _JobState.PENDING
    phase: SyncPhase = SyncPhase.DOWNLOADING
    progress_bytes: int = 0
    total_bytes: int = 0
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def to_schema(self) -> SyncJobSchema:
        return SyncJobSchema(
            job_id=self.job_id,
            status=SyncStatus(self.status.value),
            drive_type=DriveType(self.drive_type),
            source_path=self.source_path,
            local_path=self.local_path,
            phase=self.phase,
            progress_bytes=self.progress_bytes,
            total_bytes=self.total_bytes,
            progress_percent=(
                round(self.progress_bytes / self.total_bytes * 100, 1)
                if self.total_bytes > 0 else 0.0
            ),
            error_message=self.error_message,
            created_at=self.created_at,
            updated_at=self.updated_at,
            finished_at=self.finished_at,
            retry_count=0,
        )


class SyncJobManager:
    """Manages async sync jobs with a thread pool executor (max 5 concurrent)."""

    def __init__(self):
        self._cfg: Any = Config.get()  # type: ignore[reportCallIssue]
        self._db = Database.get()
        self._jobs: dict[str, _SyncJob] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT_JOBS,
            thread_name_prefix="sync_worker",
        )
        self._futures: dict[str, FutureBase[Any]] = {}
        self._lock = threading.Lock()
        logger.info(f"SyncJobManager initialized (max_concurrent={MAX_CONCURRENT_JOBS})")

    # ── Public API ──────────────────────────────────────────────────────────

    def submit(
        self,
        drive_type: str,
        source_path: str,
        local_path: str,
    ) -> _SyncJob:
        """Submit a new sync job (FR-006).

        Raises:
            OperationQueueFullError: if 5 jobs already running
            SyncError: on unexpected error
        """
        # Count running jobs
        running = sum(
            1 for j in self._jobs.values()
            if j.status in (_JobState.PENDING, _JobState.RUNNING)
        )
        if running >= MAX_CONCURRENT_JOBS:
            raise OperationQueueFullError(
                message="Sync operation queue is full",
                detail=f"Maximum {MAX_CONCURRENT_JOBS} concurrent sync jobs allowed.",
            )

        job = _SyncJob(
            job_id=str(uuid.uuid4()),
            drive_type=drive_type,
            source_path=source_path,
            local_path=local_path,
        )

        with self._lock:
            self._jobs[job.job_id] = job

        # Persist to DB
        self._persist_job(job, insert=True)

        # Submit to executor
        future = self._executor.submit(self._run_job, job)
        self._futures[job.job_id] = future

        logger.info(
            f"Sync job submitted: {job.job_id} "
            f"({drive_type}:{source_path} -> {local_path})"
        )
        return job

    def get_status(self, job_id: str) -> SyncJobSchema:
        """Get job status (FR-008)."""
        job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(message=f"Job not found: {job_id}")
        return job.to_schema()

    def cancel(self, job_id: str) -> SyncJobSchema:
        """Cancel a running or pending job (FR-009)."""
        job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(message=f"Job not found: {job_id}")

        if job.status not in (_JobState.PENDING, _JobState.RUNNING):
            raise InvalidJobStateError(
                message=f"Cannot cancel job in '{job.status.value}' state",
                detail="Only pending or running jobs can be cancelled.",
            )

        job.cancel_event.set()  # Signal cancellation

        with job._lock:
            job.status = _JobState.CANCELLED
            job.finished_at = datetime.now(timezone.utc)
            job.updated_at = datetime.now(timezone.utc)

        self._persist_job(job, insert=False)
        logger.info(f"Sync job cancelled: {job_id}")
        return job.to_schema()

    # ── Internal ───────────────────────────────────────────────────────────

    def _run_job(self, job: _SyncJob) -> None:
        """Execute the sync: download files and update progress."""
        try:
            with job._lock:
                job.status = _JobState.RUNNING
                job.updated_at = datetime.now(timezone.utc)
            self._persist_job(job, insert=False)

            self._do_sync(job)

            with job._lock:
                if job.cancel_event.is_set():
                    job.status = _JobState.CANCELLED
                else:
                    job.status = _JobState.COMPLETED
                    job.phase = SyncPhase.COMPLETED
                job.finished_at = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)
            self._persist_job(job, insert=False)
            logger.info(f"Sync job finished: {job.job_id} ({job.status.value})")

        except Exception as e:
            logger.exception(f"Sync job failed: {job.job_id}")
            with job._lock:
                job.status = _JobState.FAILED
                job.error_message = str(e)
                job.finished_at = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)
            self._persist_job(job, insert=False)

        finally:
            # Clean up future reference
            with self._lock:
                self._futures.pop(job.job_id, None)

    def _do_sync(self, job: _SyncJob) -> None:
        """Perform the actual file sync (FR-007).

        Uses rclone copy --progress with a cancel_event for interruption.
        Progress is updated via callback into the job state.
        """
        from src.services.base import get_drive_service

        service = get_drive_service(job.drive_type)

        # Use the adapter's copy_to_local for progress tracking
        def progress_callback(done: int, total: int, percent: int) -> None:
            if job.cancel_event.is_set():
                return
            with job._lock:
                job.progress_bytes = done
                job.total_bytes = total
                job.phase = SyncPhase.DOWNLOADING
                job.updated_at = datetime.now(timezone.utc)

        try:
            service.copy_to_local(
                remote_path=job.source_path,
                local_path=job.local_path,
                cancel_event=job.cancel_event,
                progress_callback=progress_callback,
            )
        except Exception as e:
            if job.cancel_event.is_set():
                logger.info(f"Sync cancelled: {job.job_id}")
                raise
            raise

    def _persist_job(self, job: _SyncJob, insert: bool = True) -> None:
        """Write job state to MySQL unified jobs table.

        Database failures are logged but do NOT crash the sync operation —
        the in-memory state is authoritative; DB is a best-effort mirror.
        """
        import json
        status_map = {
            _JobState.PENDING: "pending",
            _JobState.RUNNING: "running",
            _JobState.COMPLETED: "completed",
            _JobState.FAILED: "failed",
            _JobState.CANCELLED: "cancelled",
        }
        phase_map = {
            SyncPhase.DOWNLOADING: "downloading",
            SyncPhase.MOVING_TO_BACKUP: "moving-to-backup",
            SyncPhase.COMPLETED: "completed",
        }

        source_json = json.dumps({"source_path": job.source_path})
        try:
            if insert:
                self._db.job_insert(
                    job_id=job.job_id,
                    job_type="sync",
                    drive_type=job.drive_type,
                    source=source_json,
                    destination=job.local_path,
                    status=status_map[job.status],
                    phase=phase_map.get(job.phase, "downloading"),
                )
            else:
                self._db.job_update(
                    job_id=job.job_id,
                    status=status_map[job.status],
                    phase=phase_map.get(job.phase, "downloading"),
                    progress_bytes=job.progress_bytes,
                    total_bytes=job.total_bytes,
                    error_message=job.error_message,
                    finished_at=job.finished_at,
                )
        except Exception as e:
            logger.warning(f"Failed to persist job {job.job_id} to DB: {e}")


# ── Module-level singleton ────────────────────────────────────────────────────

_manager: SyncJobManager | None = None
_manager_lock = threading.Lock()


def get_sync_manager() -> SyncJobManager:
    """Get or create the SyncJobManager singleton."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = SyncJobManager()
    return _manager
