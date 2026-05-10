"""Jianguoyun (坚果云) cloud drive implementation."""

from typing import List

from src.adapters.rclone_adapter import RcloneAdapter
from src.core.schemas import FileInfoSchema
from src.services.base import CloudDriveService


class JianguoyunCloudDrive(CloudDriveService):
    """Jianguoyun cloud drive implementation using rclone."""

    def __init__(
        self,
        rclone_path: str,
        remote_name: str,
        timeout: int = 300,
    ):
        self._adapter = RcloneAdapter(
            rclone_path=rclone_path,
            remote_name=remote_name,
            timeout=timeout,
        )

    def list_files(self, path: str = "/") -> List[FileInfoSchema]:
        return self._adapter.list_remote(path)

    def list_detail(self, path: str = "/") -> List[FileInfoSchema]:
        return self._adapter.list_detail(path)

    def delete(self, path: str) -> bool:
        return self._adapter.delete(path)

    def move(self, src: str, dst: str) -> bool:
        return self._adapter.move(src, dst)

    def download(self, remote_path: str, local_path: str) -> bool:
        return self._adapter.download(remote_path, local_path)

    def cloud_download_add(self, urls: List[str], folder: str = "/downloads") -> str:
        raise NotImplementedError("Jianguoyun does not support offline download.")
