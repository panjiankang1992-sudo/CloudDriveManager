"""FastAPI router factory for cloud drive API endpoints.

Exposes: POST /cloud/{drive_type}/list, /detail, /move, /delete
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    CloudDriveError,
    ValidationError,
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
)
from src.services.base import get_drive_service
from src.core.operation_logger import get_operation_logger

logger = get_logger("cloud_api")

SUPPORTED_DRIVES = {"pikpak", "jianguoyun", "baiduyun"}


def _error_response(code: str, message: str, detail: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=200,
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


def create_cloud_router() -> APIRouter:
    """Factory: build and return a cloud drive API router with all endpoints."""
    router = APIRouter(prefix="/cloud", tags=["cloud"])

    # ── POST /cloud/{drive_type}/list ──────────────────────────────────────

    @router.post("/{drive_type}/list", response_model=APIResponse)
    async def list_files(
        body: CloudDriveListRequest,
        drive_type: Annotated[str, Path(description="Cloud drive type")],
        request: Annotated[Request, Depends(_get_request)],
    ):
        """List files at the given path (FR-001).

        Path defaults to root `/` if empty.
        """
        if drive_type.lower() not in SUPPORTED_DRIVES:
            return _error_response(
                "UNSUPPORTED_DRIVE_TYPE",
                f"Unsupported drive type: {drive_type}",
                detail=f"Supported: {sorted(SUPPORTED_DRIVES)}",
            )

        try:
            service = get_drive_service(drive_type)
            path = body.path or "/"
            files = service.list_files(path)

            _log_operation("list", drive_type, path, OperationResult.SUCCESS, request=request)

            return APIResponse.ok(
                data=FileListData(path=path, files=files).model_dump()
            )

        except CloudDriveError as e:
            _log_operation("list", drive_type, body.path, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return _error_response(e.CODE, e.message, e.detail)
        except Exception as e:
            logger.exception(f"Unexpected error in list_files: {e}")
            _log_operation("list", drive_type, body.path, OperationResult.FAILED, error_message=str(e), request=request)
            return _error_response("INTERNAL_ERROR", "An unexpected error occurred", str(e))

    # ── POST /cloud/{drive_type}/detail ──────────────────────────────────

    @router.post("/{drive_type}/detail", response_model=APIResponse)
    async def get_detail(
        body: CloudDriveDetailRequest,
        drive_type: Annotated[str, Path(description="Cloud drive type")],
        request: Annotated[Request, Depends(_get_request)],
    ):
        """Get file/folder metadata (FR-002)."""
        if drive_type.lower() not in SUPPORTED_DRIVES:
            return _error_response(
                "UNSUPPORTED_DRIVE_TYPE",
                f"Unsupported drive type: {drive_type}",
            )

        try:
            if not body.path or not body.path.strip():
                return _error_response("VALIDATION_ERROR", "Path cannot be empty")

            service = get_drive_service(drive_type)
            files = service.list_detail(body.path)

            if not files:
                _log_operation("detail", drive_type, body.path, OperationResult.FAILED, error_code="FILE_NOT_FOUND", error_message="File not found", request=request)
                return _error_response("FILE_NOT_FOUND", f"File not found: {body.path}")

            # list_detail returns list; find our target (exact path match)
            target = next((f for f in files if f.path.rstrip("/") == body.path.rstrip("/") or f.name == body.path.lstrip("/")), None)
            if target is None:
                # Fallback: if path itself is returned as a directory
                target = files[0] if files else None

            _log_operation("detail", drive_type, body.path, OperationResult.SUCCESS, request=request)
            if target is None:
                return _error_response("FILE_NOT_FOUND", f"File not found: {body.path}")
            return APIResponse.ok(data=target.model_dump())

        except ValidationError as e:
            _log_operation("detail", drive_type, body.path, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return _error_response(e.CODE, e.message, e.detail)
        except CloudDriveError as e:
            _log_operation("detail", drive_type, body.path, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return _error_response(e.CODE, e.message, e.detail)
        except Exception as e:
            logger.exception(f"Unexpected error in get_detail: {e}")
            _log_operation("detail", drive_type, body.path, OperationResult.FAILED, error_message=str(e), request=request)
            return _error_response("INTERNAL_ERROR", "An unexpected error occurred", str(e))

    # ── POST /cloud/{drive_type}/move ────────────────────────────────────

    @router.post("/{drive_type}/move", response_model=APIResponse)
    async def move_file(
        body: CloudDriveMoveRequest,
        drive_type: Annotated[str, Path(description="Cloud drive type")],
        request: Annotated[Request, Depends(_get_request)],
    ):
        """Move a file or folder (FR-003). Auto-creates destination parent dir."""
        if drive_type.lower() not in SUPPORTED_DRIVES:
            return _error_response("UNSUPPORTED_DRIVE_TYPE", f"Unsupported drive type: {drive_type}")

        try:
            if not body.src or not body.src.strip():
                return _error_response("VALIDATION_ERROR", "Source path cannot be empty")

            service = get_drive_service(drive_type)
            service.move(body.src, body.dst)

            _log_operation("move", drive_type, body.src, OperationResult.SUCCESS, extra={"dst": body.dst}, request=request)
            return APIResponse.ok(data=MoveResponseData(src=body.src, dst=body.dst, moved=True).model_dump())

        except ValidationError as e:
            _log_operation("move", drive_type, body.src, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return _error_response(e.CODE, e.message, e.detail)
        except CloudDriveError as e:
            _log_operation("move", drive_type, body.src, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return _error_response(e.CODE, e.message, e.detail)
        except Exception as e:
            logger.exception(f"Unexpected error in move_file: {e}")
            _log_operation("move", drive_type, body.src, OperationResult.FAILED, error_message=str(e), request=request)
            return _error_response("INTERNAL_ERROR", "An unexpected error occurred", str(e))

    # ── POST /cloud/{drive_type}/delete ──────────────────────────────────

    @router.post("/{drive_type}/delete", response_model=APIResponse)
    async def delete_file(
        body: CloudDriveDeleteRequest,
        drive_type: Annotated[str, Path(description="Cloud drive type")],
        request: Annotated[Request, Depends(_get_request)],
    ):
        """Delete a file or folder (FR-004). Cannot delete root `/`."""
        if drive_type.lower() not in SUPPORTED_DRIVES:
            return _error_response("UNSUPPORTED_DRIVE_TYPE", f"Unsupported drive type: {drive_type}")

        try:
            if not body.path or not body.path.strip():
                return _error_response("VALIDATION_ERROR", "Path cannot be empty")
            if body.path == "/":
                return _error_response("VALIDATION_ERROR", "Cannot delete root directory")

            service = get_drive_service(drive_type)
            service.delete(body.path)

            _log_operation("delete", drive_type, body.path, OperationResult.SUCCESS, request=request)
            return APIResponse.ok(data=DeleteResponseData(deleted=True, path=body.path).model_dump())

        except ValidationError as e:
            _log_operation("delete", drive_type, body.path, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return _error_response(e.CODE, e.message, e.detail)
        except CloudDriveError as e:
            _log_operation("delete", drive_type, body.path, OperationResult.FAILED, error_code=e.CODE, error_message=e.message, request=request)
            return _error_response(e.CODE, e.message, e.detail)
        except Exception as e:
            logger.exception(f"Unexpected error in delete_file: {e}")
            _log_operation("delete", drive_type, body.path, OperationResult.FAILED, error_message=str(e), request=request)
            return _error_response("INTERNAL_ERROR", "An unexpected error occurred", str(e))

    return router