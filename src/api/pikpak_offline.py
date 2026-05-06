"""PikPak offline download API — HTTP/magnet links downloaded to PikPak cloud.

Endpoints:
- POST /cloud/pikpak/offline-download — submit offline download task
- GET  /cloud/pikpak/offline-download/{task_id} — query task status
"""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.core.exceptions import UnsupportedDriveTypeError
from src.core.logger import get_logger
from src.core.schemas import (
    APIResponse,
    OfflineDownloadRequest,
    OfflineDownloadResponseData,
    OperationResult,
)
from src.core.operation_logger import get_operation_logger

logger = get_logger("pikpak_offline")

router = APIRouter(prefix="/cloud/pikpak", tags=["pikpak"])


def _error_response(code: str, message: str, detail: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=APIResponse.error(code=code, message=message, detail=detail).model_dump(),
    )


# ── POST /cloud/pikpak/offline-download ─────────────────────────────────

@router.post("/offline-download", response_model=APIResponse)
async def create_offline_download(body: OfflineDownloadRequest):
    """Submit an offline download task to PikPak (HTTP/magnet -> PikPak cloud)."""
    try:
        if not body.urls:
            return _error_response("VALIDATION_ERROR", "URLs cannot be empty")

        folder = body.folder.strip() if body.folder else "/My Pack"
        if not folder:
            folder = "/My Pack"

        from src.services.base import get_drive_service
        service = get_drive_service("pikpak")
        task_id = service.cloud_download_add(body.urls, folder)

        try:
            op_logger = get_operation_logger()
            op_logger.log(
                operation="offline_download",
                result=OperationResult.SUCCESS,
                drive_type="pikpak",
                path=folder,
                extra={"task_id": task_id, "urls_count": len(body.urls)},
            )
        except Exception as e:
            logger.warning(f"Failed to log offline_download: {e}")

        return APIResponse.ok(
            data=OfflineDownloadResponseData(
                task_id=task_id,
                urls_count=len(body.urls),
                destination_folder=folder,
                created_at=datetime.now(timezone.utc),
            ).model_dump()
        )

    except UnsupportedDriveTypeError as e:
        return _error_response(e.CODE, e.message, e.detail)
    except NotImplementedError as e:
        return _error_response("OFFLINE_DOWNLOAD_ERROR", "PikPak offline download not supported", str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in create_offline_download: {e}")
        return _error_response("OFFLINE_DOWNLOAD_ERROR", str(e))
