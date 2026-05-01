"""Unit tests for src/core/exceptions.py"""

import pytest
from src.core.exceptions import (
    CloudDriveError,
    ConfigKeyNotFoundError,
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigValueError,
    EncryptionKeyNotSetError,
    EncryptionDecryptError,
    EncryptionEncryptError,
    RcloneNotFoundError,
    RcloneExecutionError,
    CloudDriveAuthError,
    CloudDriveNotFoundError,
    FileNotFoundError,
    ValidationError,
    UnsupportedDriveTypeError,
    SyncError,
    OfflineDownloadError,
)


class TestCloudDriveError:
    def test_default_code_and_message(self):
        err = CloudDriveError()
        assert err.CODE == "INTERNAL_ERROR"
        assert err.message == "An internal error occurred."
        assert err.detail is None

    def test_custom_message(self):
        err = CloudDriveError(message="Custom message")
        assert err.message == "Custom message"

    def test_custom_detail(self):
        err = CloudDriveError(message="Error", detail="More info")
        assert err.detail == "More info"

    def test_to_dict_basic(self):
        err = CloudDriveError(message="Test error")
        d = err.to_dict()
        assert d["code"] == "INTERNAL_ERROR"
        assert d["message"] == "Test error"
        assert "detail" not in d

    def test_to_dict_with_detail(self):
        err = CloudDriveError(message="Test", detail="Extra")
        d = err.to_dict()
        assert d["detail"] == "Extra"

    def test_is_instance_of_exception(self):
        err = CloudDriveError()
        assert isinstance(err, Exception)


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
