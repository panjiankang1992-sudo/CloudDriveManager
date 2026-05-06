"""Unit tests for src.core.exceptions — verify error hierarchy and codes."""

from __future__ import annotations

import pytest

from src.core.exceptions import (
    CloudDriveError,
    ConfigError,
    RcloneNotFoundError,
    RcloneExecutionError,
    ValidationError,
    UnsupportedDriveTypeError,
    FileNotFoundError,
    SyncError,
    JobNotFoundError,
    InvalidJobStateError,
    OperationQueueFullError,
)


class TestCloudDriveError:
    def test_default_message(self):
        e = CloudDriveError()
        assert e.message == "An internal error occurred."
        assert e.CODE == "INTERNAL_ERROR"

    def test_custom_message(self):
        e = CloudDriveError(message="custom error")
        assert e.message == "custom error"

    def test_custom_message_and_detail(self):
        e = CloudDriveError(message="failed", detail="file not found")
        d = e.to_dict()
        assert d["code"] == "INTERNAL_ERROR"
        assert d["message"] == "failed"
        assert d["detail"] == "file not found"

    def test_to_dict(self):
        e = CloudDriveError(message="oops")
        d = e.to_dict()
        assert d["code"] == "INTERNAL_ERROR"
        assert d["message"] == "oops"


class TestConfigError:
    def test_code(self):
        e = ConfigError()
        assert e.CODE == "CONFIG_ERROR"


class TestRcloneNotFoundError:
    def test_code(self):
        e = RcloneNotFoundError()
        assert e.CODE == "RCLONE_NOT_FOUND"
        assert "rclone" in e.message


class TestRcloneExecutionError:
    def test_code(self):
        e = RcloneExecutionError(message="exit code 1")
        assert e.CODE == "RCLONE_EXECUTION_ERROR"


class TestValidationError:
    def test_code(self):
        e = ValidationError(message="path is required")
        assert e.CODE == "VALIDATION_ERROR"
        d = e.to_dict()
        assert d["code"] == "VALIDATION_ERROR"
        assert d["message"] == "path is required"


class TestUnsupportedDriveTypeError:
    def test_code(self):
        e = UnsupportedDriveTypeError(message="unknown drive")
        assert e.CODE == "UNSUPPORTED_DRIVE_TYPE"


class TestFileNotFoundError:
    def test_code(self):
        e = FileNotFoundError(message="/a/b.txt not found")
        assert e.CODE == "FILE_NOT_FOUND"


class TestSyncError:
    def test_code(self):
        e = SyncError(message="sync failed")
        assert e.CODE == "SYNC_ERROR"


class TestJobNotFoundError:
    def test_code(self):
        e = JobNotFoundError(message="job abc not found")
        assert e.CODE == "JOB_NOT_FOUND"


class TestInvalidJobStateError:
    def test_code(self):
        e = InvalidJobStateError(message="cannot cancel completed job")
        assert e.CODE == "INVALID_JOB_STATE"
        d = e.to_dict()
        assert "cannot cancel" in d["message"]


class TestOperationQueueFullError:
    def test_code(self):
        e = OperationQueueFullError(message="too many jobs")
        assert e.CODE == "OPERATION_QUEUE_FULL"