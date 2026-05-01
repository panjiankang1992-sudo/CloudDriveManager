"""Unit tests for src/core/schemas.py"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.core.schemas import (
    APIResponse,
    FileInfoSchema,
    FileListResponseData,
    HealthResponseData,
    SyncRequestData,
    SyncResponseData,
    OfflineDownloadRequestData,
    OfflineDownloadResponseData,
    MoveRequestData,
    MoveResponseData,
    ErrorDetailSchema,
)


class TestAPIResponse:
    def test_ok_with_data(self):
        data = {"name": "test"}
        resp = APIResponse.ok(data=data)
        assert resp.code == 0
        assert resp.message == "success"
        assert resp.data == data

    def test_ok_without_data(self):
        resp = APIResponse.ok()
        assert resp.code == 0
        assert resp.data is None

    def test_ok_with_custom_message(self):
        resp = APIResponse.ok(message="done")
        assert resp.message == "done"

    def test_error(self):
        resp = APIResponse.error(code=1, message="Something went wrong", detail="Extra info")
        assert resp.code == 1
        assert resp.message == "Something went wrong"
        assert resp.data is None


class TestFileInfoSchema:
    def test_valid_file(self):
        f = FileInfoSchema(name="test.txt", path="/test.txt", size=1024)
        assert f.name == "test.txt"
        assert f.size == 1024
        assert f.is_dir is False

    def test_valid_directory(self):
        d = FileInfoSchema(name="folder", path="/folder", is_dir=True)
        assert d.is_dir is True
        assert d.size == 0  # default

    def test_missing_required_field_raises(self):
        with pytest.raises(PydanticValidationError):
            FileInfoSchema(name="test.txt")  # missing path


class TestFileListResponseData:
    def test_valid(self):
        data = FileListResponseData(
            path="/",
            items=[
                FileInfoSchema(name="a.txt", path="/a.txt", size=100),
                FileInfoSchema(name="b.txt", path="/b.txt", size=200),
            ],
        )
        assert data.total == 2

    def test_empty_list(self):
        data = FileListResponseData(path="/downloads")
        assert data.items == []
        assert data.total == 0


class TestHealthResponseData:
    def test_healthy_status(self):
        h = HealthResponseData(
            status="healthy",
            version="1.0.0",
            env="dev",
            rclone_available=True,
        )
        assert h.status == "healthy"
        assert h.rclone_available is True


class TestSyncRequestData:
    def test_valid_sync_request(self):
        req = SyncRequestData(
            source_drive="pikpak",
            source_path="/src",
            destination_drive="jianguoyun",
            destination_path="/dest",
        )
        assert req.direction == "cloud-to-local"  # default

    def test_custom_direction(self):
        req = SyncRequestData(
            source_drive="pikpak",
            source_path="/",
            destination_drive="baidu",
            destination_path="/",
            direction="local-to-cloud",
        )
        assert req.direction == "local-to-cloud"


class TestOfflineDownloadRequestData:
    def test_valid_request(self):
        req = OfflineDownloadRequestData(
            urls=["https://example.com/file1.zip", "https://example.com/file2.zip"],
            folder="/downloads",
        )
        assert len(req.urls) == 2
        assert req.folder == "/downloads"

    def test_default_folder(self):
        req = OfflineDownloadRequestData(urls=["https://example.com/file.zip"])
        assert req.folder == "/downloads"


class TestMoveRequestData:
    def test_valid_move(self):
        req = MoveRequestData(
            source_path="/old/name.txt",
            destination_path="/new/name.txt",
        )
        assert req.source_path == "/old/name.txt"


class TestMoveResponseData:
    def test_default_success(self):
        resp = MoveResponseData(source_path="/a", destination_path="/b")
        assert resp.success is True
