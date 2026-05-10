"""CloudDriveService abstract base class + concrete implementations per drive type.

Each cloud drive (PikPak, JianGuoYun, Baidu, Aliyun, Quark) implements this interface.
rclone handles the underlying operations uniformly.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, Generator, List, Optional

from src.core.schemas import FileInfoSchema
from src.adapters.rclone_adapter import RcloneAdapter
from src.core.config import Config
from src.core.exceptions import (
    CloudDriveFileInUseError,
    CloudDriveNotFoundError,
    FileNotFoundError,
    InvalidPathError,
    ValidationError,
)
from src.core.logger import get_logger
from src.core.operation_logger import get_operation_logger

logger = get_logger("cloud_drive_service")


class CloudDriveService(ABC):
    """Abstract base class defining the cloud drive operations interface.

    All cloud drive implementations inherit from this class and implement
    each method. The interface is intentionally minimal — rclone handles
    most operations uniformly, so implementations mostly delegate to RcloneAdapter.
    """

    def __init__(self, adapter: RcloneAdapter):
        self._adapter = adapter

    def _check_file_not_in_use(self, path: str) -> None:
        """Raise CloudDriveFileInUseError if path is being synced by an active job."""
        from src.services.sync_manager import get_sync_manager

        sm = get_sync_manager()
        for job in sm._jobs.values():
            if job.status.value in ("pending", "running") and job.source_path == path:
                raise CloudDriveFileInUseError(
                    message=f"File is currently being synced: {path}",
                    detail=f"Active sync job {job.job_id} is using this file.",
                )

    @abstractmethod
    def list_files(self, path: str = "/") -> List[FileInfoSchema]:
        """List files at the given path (lightweight).

        Args:
            path: Absolute path on the remote; empty defaults to root `/`

        Returns:
            List of FileInfoSchema entries.
        """
        ...

    @abstractmethod
    def list_detail(self, path: str = "/") -> List[FileInfoSchema]:
        """List files at the given path with full metadata.

        Args:
            path: Absolute path on the remote; empty returns error

        Returns:
            List of FileInfoSchema entries with ModTime, Hash, MimeType.
        """
        ...

    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete a file or directory.

        Args:
            path: Absolute path on the remote.

        Returns:
            True if deletion succeeded.

        Raises:
            ValidationError: path is empty or root
            FileNotFoundError: path does not exist
        """
        ...

    @abstractmethod
    def move(self, src: str, dst: str) -> bool:
        """Move/rename a file or directory.

        Destination parent directory is automatically created (FR-003).

        Args:
            src: Source absolute path.
            dst: Destination absolute path (including filename).

        Returns:
            True if move succeeded.

        Raises:
            ValidationError: src is empty
            FileNotFoundError: src does not exist
        """
        ...

    @abstractmethod
    def download(self, remote_path: str, local_path: str) -> bool:
        """Download a file from cloud to local filesystem.

        Args:
            remote_path: Source path on the remote.
            local_path: Destination path on local filesystem.

        Returns:
            True if download succeeded.
        """
        ...

    @abstractmethod
    def copy_to_local(
        self,
        remote_path: str,
        local_path: str,
        cancel_event: threading.Event | None = None,
        progress_callback: Callable[[int, int, int], None] | None = None,
    ) -> bool:
        """Download with real-time progress tracking and cancellation support.

        Args:
            remote_path: Source path on the remote.
            local_path: Destination path on local filesystem.
            cancel_event: Threading Event to signal cancellation.
            progress_callback: Called with (bytes_done, total_bytes, percent).

        Returns:
            True if download succeeded.
        """
        ...

    @abstractmethod
    def cloud_download_add(self, urls: List[str], folder: str = "/My Pack") -> str:
        """Add an offline download task (PikPak only; others raise NotImplementedError).

        Args:
            urls: List of HTTP/magnet URLs to download.
            folder: Destination folder on the cloud drive.

        Returns:
            Task ID as string.

        Raises:
            NotImplementedError: If the cloud drive does not support offline download.
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support offline download.")


# ── Concrete implementations ────────────────────────────────────────────────────


class _RcloneCloudDrive(CloudDriveService):
    """Base mixin for all rclone-backed drives (Jianguoyun, Baidu, Aliyun, Quark).

    Provides concrete implementations for all CloudDriveService methods except
    cloud_download_add, which raises NotImplementedError for rclone-backed drives.
    """

    def cloud_download_add(self, urls: List[str], folder: str = "/My Pack") -> str:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support offline download."
        )

    def list_files(self, path: str = "/") -> List[FileInfoSchema]:
        path = path or "/"
        return self._adapter.list_remote(path)

    def list_detail(self, path: str = "/") -> List[FileInfoSchema]:
        if not path or not path.strip():
            raise ValidationError(message="Directory path cannot be empty")
        return self._adapter.list_detail(path)

    def delete(self, path: str) -> bool:
        if not path or not path.strip():
            raise ValidationError(message="Path cannot be empty")
        if path == "/":
            raise ValidationError(message="Cannot delete root directory")
        self._check_file_not_in_use(path)
        self._adapter.delete(path)
        return True

    def move(self, src: str, dst: str) -> bool:
        if not src or not src.strip():
            raise ValidationError(message="Source path cannot be empty")
        if not dst or not dst.strip():
            raise ValidationError(message="Destination path cannot be empty")
        self._check_file_not_in_use(src)
        return self._adapter.move_with_mkdir(src, dst)

    def download(self, remote_path: str, local_path: str) -> bool:
        return self._adapter.copy(remote_path, local_path)

    def copy_to_local(
        self,
        remote_path: str,
        local_path: str,
        cancel_event: threading.Event | None = None,
        progress_callback: Callable[[int, int, int], None] | None = None,
    ) -> bool:
        return self._adapter.copy_with_progress(
            remote_path, local_path, cancel_event, progress_callback
        )


class JianguoyunCloudDrive(_RcloneCloudDrive):
    """JianGuoYun (坚果云) cloud drive via rclone."""


class BaiduCloudDrive(_RcloneCloudDrive):
    """Baidu cloud drive via rclone (via Alist WebDAV)."""


class AliyunCloudDrive(_RcloneCloudDrive):
    """Aliyun cloud drive via rclone (WebDAV)."""


class QuarkCloudDrive(_RcloneCloudDrive):
    """Quark cloud drive via rclone (WebDAV)."""


class PikPakCloudDrive(_RcloneCloudDrive):
    """PikPak cloud drive — all operations via rclone, plus offline download."""

    def cloud_download_add(self, urls: List[str], folder: str = "/My Pack") -> str:
        from src.services.pikpak import cloud_download_add as _add
        return _add(urls, folder)


# ── Service factory ─────────────────────────────────────────────────────────────

_DRIVE_SERVICE_MAP = {
    "pikpak": PikPakCloudDrive,
    "jianguoyun": JianguoyunCloudDrive,
    "baiduyun": BaiduCloudDrive,
    "aliyun": AliyunCloudDrive,
    "quark": QuarkCloudDrive,
}


def get_drive_service(
    drive_type: str,
    rclone_path: str | None = None,
    remote_name: str | None = None,
    timeout: int | None = None,
) -> CloudDriveService:
    """Factory: create a CloudDriveService for the given drive type.

    Only `drive_type` is required. All other parameters fall back to
    environment variables or YAML config automatically — callers never
    need to pass credentials or infrastructure details.

    Args:
        drive_type: One of pikpak, jianguoyun, baiduyun
        rclone_path: Path to rclone binary (default: from config/env)
        remote_name: rclone remote name (default: "{drive_type}:")
        timeout: Command timeout in seconds (default: from config/env)

    Returns:
        Configured CloudDriveService subclass instance

    Raises:
        UnsupportedDriveTypeError: Unknown drive type
    """
    from src.core.exceptions import UnsupportedDriveTypeError

    cls = _DRIVE_SERVICE_MAP.get(drive_type.lower())
    if cls is None:
        raise UnsupportedDriveTypeError(
            message=f"Unsupported drive type: {drive_type}",
            detail=f"Supported: {list(_DRIVE_SERVICE_MAP.keys())}",
        )

    cfg: Config = Config.get()  # type: ignore[reportCallIssue]
    adapter = RcloneAdapter(
        rclone_path=rclone_path or cfg.rclone_path,
        remote_name=remote_name or f"{drive_type}:",
        timeout=timeout if timeout is not None else cfg.cloud_timeout,
    )
    return cls(adapter)
