"""CloudDriveError hierarchy — plain string error codes."""

from typing import Optional


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

    def to_dict(self) -> dict[str, object]:
        d = {"code": self.CODE, "message": self.message}
        if self.detail:
            d["detail"] = self.detail
        return d


# ── Config errors ──────────────────────────────────────────────────────────────


class ConfigError(CloudDriveError):
    """Base class for configuration errors."""
    CODE = "CONFIG_ERROR"
    MESSAGE = "Configuration error."


class ConfigKeyNotFoundError(ConfigError):
    """Raised when a required config key is missing."""
    CODE = "CONFIG_KEY_NOT_FOUND"
    MESSAGE = "A required configuration key was not found."


class ConfigFileNotFoundError(ConfigError):
    """Raised when the config file itself cannot be found."""
    CODE = "CONFIG_FILE_NOT_FOUND"
    MESSAGE = "Configuration file not found."


class ConfigParseError(ConfigError):
    """Raised when the config file is malformed YAML."""
    CODE = "CONFIG_PARSE_ERROR"
    MESSAGE = "Configuration file is malformed."


class ConfigValueError(ConfigError):
    """Raised when a config value is invalid (wrong type, out of range, etc.)."""
    CODE = "CONFIG_VALUE_ERROR"
    MESSAGE = "Configuration value is invalid."


# ── Encryption errors ───────────────────────────────────────────────────────────


class EncryptionError(CloudDriveError):
    """Base class for encryption / decryption errors."""
    CODE = "ENCRYPTION_ERROR"
    MESSAGE = "Encryption operation failed."


class EncryptionKeyNotSetError(EncryptionError):
    CODE = "ENCRYPTION_KEY_NOT_SET"
    MESSAGE = "Encryption key is not configured."


class EncryptionDecryptError(EncryptionError):
    CODE = "ENCRYPTION_DECRYPT_ERROR"
    MESSAGE = "Failed to decrypt the provided ciphertext."


class EncryptionEncryptError(EncryptionError):
    CODE = "ENCRYPTION_ENCRYPT_ERROR"
    MESSAGE = "Failed to encrypt the provided plaintext."


# ── Cloud drive errors ─────────────────────────────────────────────────────────


class CloudDriveError2(CloudDriveError):
    """Base class for cloud drive operation errors (rclone, network, auth, etc.)."""
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
    """Base class for API-layer errors (request validation, etc.)."""
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
    """Base class for service-layer errors (sync, offline-download, etc.)."""
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
