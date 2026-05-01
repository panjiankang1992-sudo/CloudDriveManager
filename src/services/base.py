"""CloudDriveService — abstract base class for all cloud drive operations.

Each cloud drive (PikPak, JianGuoYun, Baidu, Aliyun, Quark) implements this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.schemas import FileInfoSchema


class CloudDriveService(ABC):
    """Abstract base class defining the cloud drive operations interface.

    All cloud drive implementations must inherit from this class and implement
    each method. The interface is intentionally minimal to allow rclone to
    handle most operations uniformly.
    """

    @abstractmethod
    def list_files(self, path: str = "/") -> List[FileInfoSchema]:
        """List files at the given path (lightweight).

        Args:
            path: Absolute path on the remote.

        Returns:
            List of FileInfoSchema entries.
        """
        ...

    @abstractmethod
    def list_detail(self, path: str = "/") -> List[FileInfoSchema]:
        """List files at the given path with full metadata.

        Args:
            path: Absolute path on the remote.

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
        """
        ...

    @abstractmethod
    def move(self, src: str, dst: str) -> bool:
        """Move/rename a file or directory.

        Args:
            src: Source absolute path.
            dst: Destination absolute path.

        Returns:
            True if move succeeded.
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
    def cloud_download_add(self, urls: List[str], folder: str = "/downloads") -> str:
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
