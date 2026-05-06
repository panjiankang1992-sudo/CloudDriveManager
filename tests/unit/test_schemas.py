"""Unit tests for src.core.schemas — verify Pydantic models parse correctly."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.schemas import (
    APIResponse,
    FileInfoSchema,
    CloudDriveListRequest,
    CloudDriveDetailRequest,
    CloudDriveMoveRequest,
    CloudDriveDeleteRequest,
    SyncJobSchema,
    SyncRequestData,
    SyncStatus,
    SyncPhase,
    OperationResult,
    DriveType,
    OfflineDownloadRequest,
    OfflineDownloadResponseData,
)


class TestAPIResponse:
    def test_ok_with_data(self):
        r = APIResponse.ok(data={"foo": "bar"})
        assert r.code == 0
        assert r.message == "success"
        assert r.data == {"foo": "bar"}

    def test_ok_without_data(self):
        r = APIResponse.ok()
        assert r.code == 0
        assert r.data is None

    def test_error_with_code_and_message(self):
        r = APIResponse.error(code="FILE_NOT_FOUND", message="File not found", detail="path=/a")
        assert r.code == "FILE_NOT_FOUND"
        assert r.message == "File not found"
        assert r.data == {"detail": "path=/a"}

    def test_error_without_detail(self):
        r = APIResponse.error(code="VALIDATION_ERROR", message="bad input")
        assert r.code == "VALIDATION_ERROR"
        assert r.data is None

    def test_model_dump(self):
        r = APIResponse.ok(data={"x": 1})
        d = r.model_dump()
        assert d["code"] == 0
        assert d["data"]["x"] == 1


class TestFileInfoSchema:
    def test_file(self):
        f = FileInfoSchema(
            name="report.pdf",
            path="/docs/report.pdf",
            size=4096,
            is_dir=False,
            modified=datetime.now(timezone.utc),
        )
        assert f.name == "report.pdf"
        assert f.size == 4096
        assert f.is_dir is False

    def test_directory(self):
        f = FileInfoSchema(
            name="docs",
            path="/docs",
            size=0,
            is_dir=True,
            modified=datetime.now(timezone.utc),
        )
        assert f.is_dir is True
        assert f.size == 0


class TestCloudDriveListRequest:
    def test_default_path_is_root(self):
        req = CloudDriveListRequest()
        assert req.path == "/"

    def test_custom_path(self):
        req = CloudDriveListRequest(path="/documents")
        assert req.path == "/documents"


class TestCloudDriveDetailRequest:
    def test_requires_path(self):
        req = CloudDriveDetailRequest(path="/docs/report.pdf")
        assert req.path == "/docs/report.pdf"


class TestCloudDriveMoveRequest:
    def test_requires_src_and_dst(self):
        req = CloudDriveMoveRequest(src="/a.txt", dst="/b.txt")
        assert req.src == "/a.txt"
        assert req.dst == "/b.txt"


class TestCloudDriveDeleteRequest:
    def test_requires_path(self):
        req = CloudDriveDeleteRequest(path="/to_delete.txt")
        assert req.path == "/to_delete.txt"


class TestSyncJobSchema:
    def test_pending_job(self):
        now = datetime.now(timezone.utc)
        job = SyncJobSchema(
            job_id="abc-123",
            drive_type=DriveType.PIKPAK,
            source_path="/data.zip",
            local_path="/downloads/data.zip",
            status=SyncStatus.PENDING,
            phase=SyncPhase.DOWNLOADING,
            progress_bytes=0,
            total_bytes=0,
            progress_percent=0.0,
            retry_count=0,
            created_at=now,
            updated_at=now,
        )
        assert job.job_id == "abc-123"
        assert job.status == SyncStatus.PENDING
        assert job.phase == SyncPhase.DOWNLOADING

    def test_completed_job(self):
        now = datetime.now(timezone.utc)
        job = SyncJobSchema(
            job_id="abc-123",
            drive_type=DriveType.PIKPAK,
            source_path="/data.zip",
            local_path="/downloads/data.zip",
            status=SyncStatus.COMPLETED,
            phase=SyncPhase.COMPLETED,
            progress_bytes=1024,
            total_bytes=1024,
            progress_percent=100.0,
            retry_count=0,
            created_at=now,
            updated_at=now,
            finished_at=now,
        )
        assert job.status == SyncStatus.COMPLETED
        assert job.finished_at is not None

    def test_failed_job_with_error(self):
        now = datetime.now(timezone.utc)
        job = SyncJobSchema(
            job_id="abc-123",
            drive_type=DriveType.BAIDUYUN,
            source_path="/large.zip",
            local_path="/downloads/large.zip",
            status=SyncStatus.FAILED,
            phase=SyncPhase.DOWNLOADING,
            progress_bytes=512,
            total_bytes=1024,
            progress_percent=50.0,
            retry_count=3,
            error_message="Connection reset",
            created_at=now,
            updated_at=now,
        )
        assert job.status == SyncStatus.FAILED
        assert job.retry_count == 3
        assert "Connection reset" in job.error_message


class TestSyncRequestData:
    def test_drive_type_validation(self):
        req = SyncRequestData(drive_type=DriveType.JIANGUOYUN, source_path="/a.zip", local_path="/dl/")
        assert req.drive_type == DriveType.JIANGUOYUN


class TestOperationResult:
    def test_success_value(self):
        assert OperationResult.SUCCESS == "success"

    def test_failed_value(self):
        assert OperationResult.FAILED == "failed"


class TestDriveType:
    def test_all_drive_types_exist(self):
        assert DriveType.PIKPAK == "pikpak"
        assert DriveType.JIANGUOYUN == "jianguoyun"
        assert DriveType.BAIDUYUN == "baiduyun"


class TestOfflineDownloadRequest:
    def test_multiple_urls(self):
        req = OfflineDownloadRequest(
            urls=["https://example.com/file.zip", "magnet:?xt=urn:btih:abc"],
            folder="/My Pack",
        )
        assert len(req.urls) == 2
        assert req.folder == "/My Pack"

    def test_default_folder(self):
        req = OfflineDownloadRequest(urls=["https://example.com/file.zip"])
        assert req.folder == "/My Pack"


class TestOfflineDownloadResponseData:
    def test_response_data(self):
        now = datetime.now(timezone.utc)
        data = OfflineDownloadResponseData(
            task_id="task-001",
            urls_count=3,
            destination_folder="/My Pack",
            created_at=now,
        )
        assert data.task_id == "task-001"
        assert data.urls_count == 3