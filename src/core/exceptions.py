"""CloudDriveError hierarchy — plain string error codes.

Error codes follow contracts/sync-job-api.md.
"""

from __future__ import annotations

from typing import Any, Optional


class CloudDriveError(Exception):
    """Base exception for all service errors.

    Error codes follow SC-003: plain string format (e.g., CONFIG_KEY_NOT_FOUND).
    """

    CODE: str = "INTERNAL_ERROR"
    MESSAGE: str = "An internal error occurred."

    def __init__(self, message: Optional[str] = None, detail: Optional[str] = None):
        self.message = message or self.MESSAGE
        self.detail = detail
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        d = {"code": self.CODE, "message": self.message}
        if self.detail:
            d["detail"] = self.detail
        return d


# ── Config errors ──────────────────────────────────────────────────────────────


class ConfigError(CloudDriveError):
    CODE = "CONFIG_ERROR"
    MESSAGE = "Configuration error."


class ConfigKeyNotFoundError(ConfigError):
    CODE = "CONFIG_KEY_NOT_FOUND"
    MESSAGE = "A required configuration key was not found."


class ConfigFileNotFoundError(ConfigError):
    CODE = "CONFIG_FILE_NOT_FOUND"
    MESSAGE = "Configuration file not found."


class ConfigParseError(ConfigError):
    CODE = "CONFIG_PARSE_ERROR"
    MESSAGE = "Configuration file is malformed."


# ── Cloud drive errors ─────────────────────────────────────────────────────────


class CloudDriveError2(CloudDriveError):
    CODE = "CLOUD_DRIVE_ERROR"
    MESSAGE = "A cloud drive operation failed."


class RcloneNotFoundError(CloudDriveError2):
    CODE = "RCLONE_NOT_FOUND"
    MESSAGE = "rclone executable not found at the configured path."


class RcloneExecutionError(CloudDriveError2):
    CODE = "RCLONE_EXECUTION_ERROR"
    MESSAGE = "rclone command execution failed."


class RcloneTimeoutError(CloudDriveError2):
    CODE = "RCLONE_TIMEOUT"
    MESSAGE = "rclone command timed out."


class CloudDriveAuthError(CloudDriveError2):
    CODE = "CLOUD_DRIVE_AUTH_ERROR"
    MESSAGE = "Cloud drive authentication failed."


class CloudDriveNotFoundError(CloudDriveError2):
    CODE = "CLOUD_DRIVE_NOT_FOUND"
    MESSAGE = "Cloud drive not found or not configured."


class FileNotFoundError(CloudDriveError2):
    CODE = "FILE_NOT_FOUND"
    MESSAGE = "The specified file was not found."


class DirectoryNotFoundError(CloudDriveError2):
    CODE = "DIRECTORY_NOT_FOUND"
    MESSAGE = "The specified directory was not found."


class PathAlreadyExistsError(CloudDriveError2):
    CODE = "PATH_ALREADY_EXISTS"
    MESSAGE = "The target path already exists."


class InvalidPathError(CloudDriveError2):
    CODE = "INVALID_PATH"
    MESSAGE = "The provided path is invalid."


# ── API errors ─────────────────────────────────────────────────────────────────


class APIError(CloudDriveError):
    CODE = "API_ERROR"
    MESSAGE = "API request error."


class ValidationError(APIError):
    CODE = "VALIDATION_ERROR"
    MESSAGE = "Request validation failed."


class UnsupportedDriveTypeError(APIError):
    CODE = "UNSUPPORTED_DRIVE_TYPE"
    MESSAGE = "The specified cloud drive type is not supported."


# ── Service errors ─────────────────────────────────────────────────────────────


class ServiceError(CloudDriveError):
    CODE = "SERVICE_ERROR"
    MESSAGE = "A service operation failed."


class SyncError(ServiceError):
    CODE = "SYNC_ERROR"
    MESSAGE = "Cloud sync operation failed."


class OfflineDownloadError(ServiceError):
    CODE = "OFFLINE_DOWNLOAD_ERROR"
    MESSAGE = "Offline download task creation failed."


class OfflineDownloadTimeoutError(OfflineDownloadError):
    CODE = "OFFLINE_DOWNLOAD_TIMEOUT"
    MESSAGE = "Offline download timed out."


# ── Sync job errors ────────────────────────────────────────────────────────────


class JobNotFoundError(ServiceError):
    CODE = "JOB_NOT_FOUND"
    MESSAGE = "Sync job not found."


class InvalidJobStateError(ServiceError):
    CODE = "INVALID_JOB_STATE"
    MESSAGE = "The sync job is not in a valid state for this operation."


class OperationQueueFullError(ServiceError):
    CODE = "OPERATION_QUEUE_FULL"
    MESSAGE = "Too many concurrent sync tasks. Please wait and retry."


class CloudDriveFileInUseError(CloudDriveError2):
    """Raised when attempting to delete or move a file that is currently being synced."""
    CODE = "FILE_IN_USE"
    MESSAGE = "The file is currently being used by another operation."