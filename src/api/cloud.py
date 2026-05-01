"""FastAPI router factory for cloud drive API endpoints."""

from typing import Optional, Dict, Type

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    CloudDriveError,
    UnsupportedDriveTypeError,
    ValidationError,
    CloudDriveNotFoundError,
)
from src.core.logger import get_logger
from src.core.schemas import (
    APIResponse,
    FileListResponseData,
    SyncRequestData,
    SyncResponseData,
    MoveRequestData,
    MoveResponseData,
    OfflineDownloadRequestData,
    OfflineDownloadResponseData,
)
from src.services.base import CloudDriveService
from src.services.pikpak import PikPakCloudDrive
from src.services.jianguoyun import JianguoyunCloudDrive
from src.services.baidu import BaiduCloudDrive
from src.services.aliyun import AliyunCloudDrive
from src.services.quark import QuarkCloudDrive

logger = get_logger("cloud_api")

SUPPORTED_DRIVES = {"pikpak", "jianguoyun", "baidu", "aliyun", "quark"}

# Service class registry — maps drive_type to CloudDriveService subclass
_DRIVE_SERVICE_REGISTRY: Dict[str, Type[CloudDriveService]] = {
    "pikpak": PikPakCloudDrive,
    "jianguoyun": JianguoyunCloudDrive,
    "baidu": BaiduCloudDrive,
    "aliyun": AliyunCloudDrive,
    "quark": QuarkCloudDrive,
}


def get_drive_service(
    drive_type: str,
    rclone_path: str,
    remote_name: str,
    timeout: int = 300,
) -> CloudDriveService:
    """Factory: create a CloudDriveService instance for the given drive type."""
    drive_type_lower = drive_type.lower()
    if drive_type_lower not in SUPPORTED_DRIVES:
        raise UnsupportedDriveTypeError(
            message=f"Unsupported cloud drive type: {drive_type}",
            detail=f"Supported types: {', '.join(sorted(SUPPORTED_DRIVES))}",
        )

    service_class = _DRIVE_SERVICE_REGISTRY[drive_type_lower]
    return service_class(rclone_path=rclone_path, remote_name=remote_name, timeout=timeout)


def create_cloud_router(
    drive_type: str,
    rclone_path: str,
    remote_name: str,
    timeout: int = 300,
) -> APIRouter:
    """Create a FastAPI router for a specific cloud drive.

    Args:
        drive_type: The cloud drive type (e.g. "pikpak").
        rclone_path: Path to rclone executable.
        remote_name: Name of the rclone remote.
        timeout: Default timeout in seconds.

    Returns:
        An APIRouter with all cloud operation endpoints registered.
    """
    service = get_drive_service(drive_type, rclone_path, remote_name, timeout)
    router = APIRouter(prefix=f"/cloud/{drive_type}", tags=[drive_type])

    # ── GET /cloud/{drive_type}/list ─────────────────────────────────────────

    @router.get("/list", response_model=APIResponse[FileListResponseData])
    async def list_files(path: str = Query(default="/", description="Remote path")):
        """List files at the given path (lightweight, no full metadata)."""
        try:
            items = service.list_files(path)
            data = FileListResponseData(path=path, items=items)
            return APIResponse.ok(data=data)
        except CloudDriveError as e:
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )

    # ── GET /cloud/{drive_type}/detail ─────────────────────────────────────────

    @router.get("/detail", response_model=APIResponse[FileListResponseData])
    async def detail_files(path: str = Query(default="/", description="Remote path")):
        """List files at the given path with full metadata (ModTime, Hash, MimeType)."""
        try:
            items = service.list_detail(path)
            data = FileListResponseData(path=path, items=items)
            return APIResponse.ok(data=data)
        except CloudDriveError as e:
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )

    # ── GET /cloud/{drive_type}/download ───────────────────────────────────────

    @router.get("/download", response_model=APIResponse[MoveResponseData])
    async def download_file(
        path: str = Query(..., description="Remote file path"),
        local_path: str = Query(..., description="Local destination path"),
    ):
        """Download a file from the cloud drive to a local path."""
        try:
            service.download(path, local_path)
            data = MoveResponseData(source_path=path, destination_path=local_path, success=True)
            return APIResponse.ok(data=data)
        except CloudDriveError as e:
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )

    # ── DELETE /cloud/{drive_type}/delete ─────────────────────────────────────

    @router.delete("/delete", response_model=APIResponse[MoveResponseData])
    async def delete_file(path: str = Query(..., description="Remote path to delete")):
        """Delete a file or directory from the cloud drive."""
        try:
            service.delete(path)
            data = MoveResponseData(source_path=path, destination_path="", success=True)
            return APIResponse.ok(data=data)
        except CloudDriveError as e:
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )

    # ── POST /cloud/{drive_type}/move ─────────────────────────────────────────

    @router.post("/move", response_model=APIResponse[MoveResponseData])
    async def move_file(body: MoveRequestData):
        """Move/rename a file or directory within the cloud drive."""
        try:
            service.move(body.source_path, body.destination_path)
            data = MoveResponseData(
                source_path=body.source_path,
                destination_path=body.destination_path,
                success=True,
            )
            return APIResponse.ok(data=data)
        except CloudDriveError as e:
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )

    # ── POST /cloud/{drive_type}/offline-download (PikPak only) ───────────────

    @router.post("/offline-download", response_model=APIResponse[OfflineDownloadResponseData])
    async def offline_download(body: OfflineDownloadRequestData):
        """Add an offline download task (PikPak only)."""
        try:
            task_id = service.cloud_download_add(body.urls, body.folder)
            data = OfflineDownloadResponseData(
                task_id=task_id,
                status="pending",
                urls_count=len(body.urls),
            )
            return APIResponse.ok(data=data)
        except NotImplementedError:
            return JSONResponse(
                status_code=501,
                content=APIResponse.error(
                    code=1,
                    message="Offline download not supported for this cloud drive type.",
                    detail=None,
                ).model_dump(),
            )
        except CloudDriveError as e:
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )

    return router
