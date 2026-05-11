"""FastAPI router factory for cloud drive API endpoints.

Exposes: POST /cloud/{drive_type}/list, /detail, /move, /delete
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    CloudDriveError,
    ValidationError,
    CloudDriveNotFoundError,
)
from src.core.logger import get_logger
from src.core.schemas import (
    APIResponse,
    CloudDriveListRequest,
    CloudDriveDetailRequest,
    CloudDriveMoveRequest,
    CloudDriveDeleteRequest,
    FileListData,
    MoveResponseData,
    DeleteResponseData,
    OperationResult,
    FileListResponseData,
    SyncRequestData,
    SyncResponseData,
    OfflineDownloadRequestData,
    OfflineDownloadResponseData,
)
from src.services.base import CloudDriveService, get_drive_service
from src.core.operation_logger import get_operation_logger

logger = get_logger("cloud_api")

SUPPORTED_DRIVES = {"pikpak", "jianguoyun", "baiduyun", "aliyun", "quark"}


def _error_response(code: str, message: str, detail: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=APIResponse.error(code=code, message=message, detail=detail).model_dump(),
    )


def _log_operation(operation: str, drive_type: str, path: str | None, result: OperationResult, error_code: str | None = None, error_message: str | None = None, extra: dict[str, Any] | None = None, request: Request | None = None):
    """Log an operation to the operation log."""
    try:
        ip = request.client.host if request and request.client else "localhost"
        op_logger = get_operation_logger()
        op_logger.log(
            operation=operation,
            result=result,
            drive_type=drive_type,
            path=path,
            error_code=error_code,
            error_message=error_message,
            extra=extra,
            ip_address=ip,
        )
    except Exception as e:
        logger.warning(f"Failed to log operation: {e}")


def _get_request(request: Request) -> Request:
    """FastAPI dependency to inject the current Request object."""
    return request


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
    async def list_files(
        path: str = Query(default="/", description="Remote path"),
        request: Request = None,
    ):
        """List files at the given path (lightweight, no full metadata)."""
        try:
            items = service.list_files(path)
            data = FileListResponseData(path=path, items=items)

            _log_operation("list", drive_type, path, OperationResult.SUCCESS, request=request)

            return APIResponse.ok(data=data)
        except CloudDriveError as e:
            _log_operation("list", drive_type, path, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )
        except Exception as e:
            logger.exception(f"Unexpected error in list_files: {e}")
            _log_operation("list", drive_type, path, OperationResult.FAILED, error_message=str(e), request=request)
            return _error_response("INTERNAL_ERROR", "An unexpected error occurred", str(e))

    # ── GET /cloud/{drive_type}/detail ─────────────────────────────────────────

    @router.get("/detail", response_model=APIResponse[FileListResponseData])
    async def detail_files(
        path: str = Query(default="/", description="Remote path"),
        request: Request = None,
    ):
        """List files at the given path with full metadata (ModTime, Hash, MimeType)."""
        try:
            items = service.list_detail(path)
            data = FileListResponseData(path=path, items=items)

            _log_operation("detail", drive_type, path, OperationResult.SUCCESS, request=request)

            return APIResponse.ok(data=data)
        except CloudDriveError as e:
            _log_operation("detail", drive_type, path, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )
        except Exception as e:
            logger.exception(f"Unexpected error in detail_files: {e}")
            _log_operation("detail", drive_type, path, OperationResult.FAILED, error_message=str(e), request=request)
            return _error_response("INTERNAL_ERROR", "An unexpected error occurred", str(e))

    # ── GET /cloud/{drive_type}/download ───────────────────────────────────────

    @router.get("/download", response_model=APIResponse[MoveResponseData])
    async def download_file(
        path: str = Query(..., description="Remote file path"),
        local_path: str = Query(..., description="Local destination path"),
        request: Request = None,
    ):
        """Download a file from the cloud drive to a local path."""
        try:
            service.download(path, local_path)
            data = MoveResponseData(source_path=path, destination_path=local_path, success=True)

            _log_operation("download", drive_type, path, OperationResult.SUCCESS, extra={"local_path": local_path}, request=request)

            return APIResponse.ok(data=data)
        except CloudDriveError as e:
            _log_operation("download", drive_type, path, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )
        except Exception as e:
            logger.exception(f"Unexpected error in download_file: {e}")
            _log_operation("download", drive_type, path, OperationResult.FAILED, error_message=str(e), request=request)
            return _error_response("INTERNAL_ERROR", "An unexpected error occurred", str(e))

    # ── DELETE /cloud/{drive_type}/delete ─────────────────────────────────────

    @router.delete("/delete", response_model=APIResponse[MoveResponseData])
    async def delete_file(
        path: str = Query(..., description="Remote path to delete"),
        request: Request = None,
    ):
        """Delete a file or directory from the cloud drive."""
        try:
            service.delete(path)
            data = MoveResponseData(source_path=path, destination_path="", success=True)

            _log_operation("delete", drive_type, path, OperationResult.SUCCESS, request=request)

            return APIResponse.ok(data=data)
        except CloudDriveError as e:
            _log_operation("delete", drive_type, path, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )
        except Exception as e:
            logger.exception(f"Unexpected error in delete_file: {e}")
            _log_operation("delete", drive_type, path, OperationResult.FAILED, error_message=str(e), request=request)
            return _error_response("INTERNAL_ERROR", "An unexpected error occurred", str(e))

    # ── POST /cloud/{drive_type}/move ─────────────────────────────────────────

    @router.post("/move", response_model=APIResponse[MoveResponseData])
    async def move_file(
        body: CloudDriveMoveRequest,
        request: Request = None,
    ):
        """Move/rename a file or directory within the cloud drive."""
        try:
            service.move(body.source_path, body.destination_path)
            data = MoveResponseData(
                source_path=body.source_path,
                destination_path=body.destination_path,
                success=True,
            )

            _log_operation("move", drive_type, body.source_path, OperationResult.SUCCESS, extra={"dst": body.destination_path}, request=request)

            return APIResponse.ok(data=data)
        except CloudDriveError as e:
            _log_operation("move", drive_type, body.source_path, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )
        except Exception as e:
            logger.exception(f"Unexpected error in move_file: {e}")
            _log_operation("move", drive_type, body.source_path, OperationResult.FAILED, error_message=str(e), request=request)
            return _error_response("INTERNAL_ERROR", "An unexpected error occurred", str(e))

    # ── POST /cloud/{drive_type}/offline-download (PikPak only) ───────────────

    @router.post("/offline-download", response_model=APIResponse[OfflineDownloadResponseData])
    async def offline_download(
        body: OfflineDownloadRequestData,
        request: Request = None,
    ):
        """Add an offline download task (PikPak only)."""
        try:
            task_id = service.cloud_download_add(body.urls, body.folder)
            data = OfflineDownloadResponseData(
                task_id=task_id,
                status="pending",
                urls_count=len(body.urls),
            )

            _log_operation("offline-download", drive_type, body.folder, OperationResult.SUCCESS, extra={"urls_count": len(body.urls)}, request=request)

            return APIResponse.ok(data=data)
        except NotImplementedError:
            _log_operation("offline-download", drive_type, body.folder, OperationResult.FAILED, error_code="NOT_SUPPORTED", error_message="Offline download not supported for this cloud drive type.", request=request)
            return JSONResponse(
                status_code=501,
                content=APIResponse.error(
                    code=1,
                    message="Offline download not supported for this cloud drive type.",
                    detail=None,
                ).model_dump(),
            )
        except CloudDriveError as e:
            _log_operation("offline-download", drive_type, body.folder, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return JSONResponse(
                status_code=500,
                content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
            )

    return router
