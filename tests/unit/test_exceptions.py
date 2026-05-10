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
    ConfigKeyNotFoundError,
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigValueError,
    EncryptionKeyNotSetError,
    EncryptionDecryptError,
    EncryptionEncryptError,
    CloudDriveAuthError,
    CloudDriveNotFoundError,
    OfflineDownloadError,
    CloudDriveFileInUseError,
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


class TestConfigErrors:
    def test_config_key_not_found(self):
        err = ConfigKeyNotFoundError()
        assert err.CODE == "CONFIG_KEY_NOT_FOUND"

    def test_config_file_not_found(self):
        err = ConfigFileNotFoundError()
        assert err.CODE == "CONFIG_FILE_NOT_FOUND"

    def test_config_parse_error(self):
        err = ConfigParseError()
        assert err.CODE == "CONFIG_PARSE_ERROR"

    def test_config_value_error(self):
        err = ConfigValueError()
        assert err.CODE == "CONFIG_VALUE_ERROR"

    def test_all_inherit_from_cloud_drive_error(self):
        assert issubclass(ConfigKeyNotFoundError, CloudDriveError)
        assert issubclass(ConfigFileNotFoundError, CloudDriveError)
        assert issubclass(ConfigParseError, CloudDriveError)
        assert issubclass(ConfigValueError, CloudDriveError)


class TestEncryptionErrors:
    def test_encryption_key_not_set(self):
        err = EncryptionKeyNotSetError()
        assert err.CODE == "ENCRYPTION_KEY_NOT_SET"

    def test_encryption_decrypt_error(self):
        err = EncryptionDecryptError()
        assert err.CODE == "ENCRYPTION_DECRYPT_ERROR"

    def test_encryption_encrypt_error(self):
        err = EncryptionEncryptError()
        assert err.CODE == "ENCRYPTION_ENCRYPT_ERROR"


class TestCloudDriveOperationErrors:
    def test_rclone_not_found(self):
        err = RcloneNotFoundError()
        assert err.CODE == "RCLONE_NOT_FOUND"

    def test_rclone_execution_error(self):
        err = RcloneExecutionError()
        assert err.CODE == "RCLONE_EXECUTION_ERROR"

    def test_cloud_drive_auth_error(self):
        err = CloudDriveAuthError()
        assert err.CODE == "CLOUD_DRIVE_AUTH_ERROR"

    def test_cloud_drive_not_found_error(self):
        err = CloudDriveNotFoundError()
        assert err.CODE == "CLOUD_DRIVE_NOT_FOUND"

    def test_file_not_found(self):
        err = FileNotFoundError()
        assert err.CODE == "FILE_NOT_FOUND"


class TestAPIAndServiceErrors:
    def test_validation_error(self):
        err = ValidationError()
        assert err.CODE == "VALIDATION_ERROR"

    def test_unsupported_drive_type_error(self):
        err = UnsupportedDriveTypeError()
        assert err.CODE == "UNSUPPORTED_DRIVE_TYPE"

    def test_sync_error(self):
        err = SyncError()
        assert err.CODE == "SYNC_ERROR"

    def test_offline_download_error(self):
        err = OfflineDownloadError()
        assert err.CODE == "OFFLINE_DOWNLOAD_ERROR"

    def test_cloud_drive_file_in_use_error(self):
        err = CloudDriveFileInUseError()
        assert err.CODE == "FILE_IN_USE"
