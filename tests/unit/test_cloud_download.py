"""Unit tests for CloudDownloadJobManager — verifies 30-minute watchdog timeout logic."""

from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.cloud_download_manager import (
    CloudDownloadJobManager,
    CloudDownloadJob,
    _CloudDownloadState,
    get_cloud_download_manager,
    JOB_TIMEOUT_SECS,
    WATCHDOG_INTERVAL_SECS,
)


class TestCloudDownloadJob:
    """Test CloudDownloadJob dataclass."""

    def test_default_status_is_pending(self):
        job = CloudDownloadJob(task_id="t1", urls=["http://x.com/f.zip"], folder="/dl")
        assert job.status == _CloudDownloadState.PENDING
        assert job.error_message is None
        assert job.finished_at is None

    def test_finished_job_has_timestamp(self):
        now = datetime.now(timezone.utc)
        job = CloudDownloadJob(
            task_id="t2",
            urls=["magnet:?xt=urn:btih:abc"],
            folder="/pack",
            status=_CloudDownloadState.COMPLETED,
            finished_at=now,
        )
        assert job.status == _CloudDownloadState.COMPLETED
        assert job.finished_at == now


class TestCloudDownloadJobManager:
    """Test CloudDownloadJobManager lifecycle and watchdog."""

    def _make_manager(self) -> CloudDownloadJobManager:
        mock_db = MagicMock()
        with patch("src.services.cloud_download_manager.Database") as MockDbCls:
            MockDbCls.get.return_value = mock_db
            mgr = CloudDownloadJobManager()
            mgr._db = mock_db
        return mgr

    def test_create_job_returns_job_with_pending_status(self):
        mgr = self._make_manager()
        mgr._db.cloud_download_job_insert.return_value = 1

        job = mgr.create_job(["http://example.com/file.zip"], "/My Pack")

        assert job.task_id is not None
        assert job.status == _CloudDownloadState.PENDING
        assert job.folder == "/My Pack"
        assert job.urls == ["http://example.com/file.zip"]
        mgr._db.cloud_download_job_insert.assert_called_once()
        call_args = mgr._db.cloud_download_job_insert.call_args
        assert call_args[0][0] == job.task_id  # task_id
        assert json.loads(call_args[0][1]) == ["http://example.com/file.zip"]  # urls
        assert call_args[0][2] == "/My Pack"  # folder
        assert call_args[0][3] == "pending"

    def test_create_job_persists_to_db(self):
        mgr = self._make_manager()
        mgr._db.cloud_download_job_insert.return_value = 42

        job = mgr.create_job(["https://x.com/a.tar"], "/ Videos")

        assert job.id == 42

    def test_update_status_to_downloading(self):
        mgr = self._make_manager()
        mgr._db.cloud_download_job_insert.return_value = 1
        job = mgr.create_job(["http://x.com/f.zip"], "/dl")

        mgr.update_status(job.task_id, "downloading")

        assert mgr._jobs[job.task_id].status == _CloudDownloadState.DOWNLOADING
        mgr._db.cloud_download_job_update_status.assert_called_once()
        call_args = mgr._db.cloud_download_job_update_status.call_args[0]
        assert call_args[0] == job.task_id
        assert call_args[1] == "downloading"

    def test_update_status_to_completed_sets_finished_at(self):
        mgr = self._make_manager()
        mgr._db.cloud_download_job_insert.return_value = 1
        job = mgr.create_job(["http://x.com/f.zip"], "/dl")

        mgr.update_status(job.task_id, "completed")

        assert mgr._jobs[job.task_id].status == _CloudDownloadState.COMPLETED
        assert mgr._jobs[job.task_id].finished_at is not None
        call_args = mgr._db.cloud_download_job_update_status.call_args[0]
        assert call_args[1] == "completed"
        assert call_args[2] is None  # no error message
        assert call_args[3] is not None  # finished_at set

    def test_update_status_to_failed_with_error(self):
        mgr = self._make_manager()
        mgr._db.cloud_download_job_insert.return_value = 1
        job = mgr.create_job(["http://x.com/f.zip"], "/dl")

        mgr.update_status(job.task_id, "failed", "Connection reset")

        assert mgr._jobs[job.task_id].status == _CloudDownloadState.FAILED
        assert mgr._jobs[job.task_id].error_message == "Connection reset"
        call_args = mgr._db.cloud_download_job_update_status.call_args[0]
        assert call_args[1] == "failed"
        assert call_args[2] == "Connection reset"

    def test_get_job_returns_job(self):
        mgr = self._make_manager()
        mgr._db.cloud_download_job_insert.return_value = 1
        created = mgr.create_job(["http://x.com/f.zip"], "/dl")

        retrieved = mgr.get_job(created.task_id)

        assert retrieved is created

    def test_get_job_returns_none_for_unknown(self):
        mgr = self._make_manager()
        assert mgr.get_job("nonexistent") is None

    def test_load_pending_from_db(self):
        mgr = self._make_manager()
        mgr._db.cloud_download_job_get_pending.return_value = [
            {
                "task_id": "db-task-1",
                "urls": json.dumps(["http://a.com/f1.zip"]),
                "folder": "/pack1",
                "status": "downloading",
                "error_message": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "finished_at": None,
            },
            {
                "task_id": "db-task-2",
                "urls": json.dumps(["http://b.com/f2.tar"]),
                "folder": "/pack2",
                "status": "pending",
                "error_message": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "finished_at": None,
            },
        ]

        mgr.load_pending_from_db()

        assert "db-task-1" in mgr._jobs
        assert "db-task-2" in mgr._jobs
        assert mgr._jobs["db-task-1"].status == _CloudDownloadState.DOWNLOADING
        assert mgr._jobs["db-task-2"].status == _CloudDownloadState.PENDING

    def test_watchdog_marks_aged_job_as_timeout(self):
        """A job created more than JOB_TIMEOUT_SECS ago is marked TIMEOUT."""
        mgr = self._make_manager()
        mgr._db.cloud_download_job_insert.return_value = 1
        mgr._db.cloud_download_job_get_pending.return_value = []

        # Create a job with a past created_at (simulate aged job)
        job = mgr.create_job(["http://x.com/f.zip"], "/dl")
        # Manually age the job
        old_time = datetime.now(timezone.utc).timestamp() - (JOB_TIMEOUT_SECS + 10)
        mgr._jobs[job.task_id].created_at = datetime.fromtimestamp(old_time, tz=timezone.utc)

        mgr._check_timeouts()

        assert mgr._jobs[job.task_id].status == _CloudDownloadState.TIMEOUT
        mgr._db.cloud_download_job_update_status.assert_called()
        call_args = mgr._db.cloud_download_job_update_status.call_args[0]
        assert call_args[0] == job.task_id
        assert call_args[1] == "timeout"

    def test_watchdog_does_not_timeout_recent_job(self):
        """A job created recently is NOT marked as timeout."""
        mgr = self._make_manager()
        mgr._db.cloud_download_job_insert.return_value = 1
        mgr._db.cloud_download_job_get_pending.return_value = []

        job = mgr.create_job(["http://x.com/f.zip"], "/dl")

        mgr._check_timeouts()

        assert mgr._jobs[job.task_id].status == _CloudDownloadState.PENDING
        # No update_status call for timeout
        for call in mgr._db.cloud_download_job_update_status.call_args_list:
            assert call[0][1] != "timeout"

    def test_watchdog_does_not_timeout_completed_job(self):
        """A completed/failed job is never marked timeout."""
        mgr = self._make_manager()
        mgr._db.cloud_download_job_insert.return_value = 1
        mgr._db.cloud_download_job_get_pending.return_value = []

        job = mgr.create_job(["http://x.com/f.zip"], "/dl")
        mgr.update_status(job.task_id, "completed")

        # Age the job
        old_ts = datetime.now(timezone.utc).timestamp() - (JOB_TIMEOUT_SECS + 10)
        mgr._jobs[job.task_id].created_at = datetime.fromtimestamp(old_ts, tz=timezone.utc)

        mgr._check_timeouts()

        # Status should still be completed (not changed to timeout)
        assert mgr._jobs[job.task_id].status == _CloudDownloadState.COMPLETED

    def test_manager_is_singleton(self):
        """get_cloud_download_manager returns the same instance."""
        mock_db = MagicMock()
        with patch("src.services.cloud_download_manager._manager", None):
            with patch("src.services.cloud_download_manager._manager_lock", threading.Lock()):
                with patch("src.services.cloud_download_manager.Database") as MockDbCls:
                    MockDbCls.get.return_value = mock_db
                    mgr1 = get_cloud_download_manager()
                    mgr2 = get_cloud_download_manager()
                    assert mgr1 is mgr2
