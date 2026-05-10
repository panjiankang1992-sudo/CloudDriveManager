"""Sync job API — async file sync from cloud to local (FR-006 to FR-012).

Endpoints:
- POST /cloud/sync            — create sync job
- GET  /cloud/sync/{job_id}/status — query progress
- POST /cloud/sync/{job_id}/cancel — cancel running job
"""

from __future__ import annotations

from fastapi import APIRouter, Path
from fastapi.responses import JSONResponse
from typing import TYPE_CHECKING

from src.core.exceptions import (
    JobNotFoundError,
    InvalidJobStateError,
    OperationQueueFullError,
    SyncError,
    CloudDriveError,
)
from src.core.logger import get_logger
from src.core.schemas import (
    APIResponse,
    SyncRequestData,
    SyncResponseData,
    SyncStatus,
    SyncPhase,
    OperationResult,
)
from src.core.operation_logger import get_operation_logger

if TYPE_CHECKING:
    from src.services.sync_manager import SyncJobManager  # type: ignore[reportMissingImports]

logger = get_logger("sync_api")

router = APIRouter(prefix="/cloud", tags=["sync"])


# ── Deferred imports (SyncJobManager initialized at startup) ──────────────────

_sync_manager: SyncJobManager | None = None


def set_sync_manager(manager: SyncJobManager) -> None:
    global _sync_manager
    _sync_manager = manager


def _sm() -> SyncJobManager:
    if _sync_manager is None:
        from src.services.sync_manager import get_sync_manager  # type: ignore[reportMissingImports]
        set_sync_manager(get_sync_manager())  # type: ignore[reportArgType]
    return _sync_manager  # type: ignore[return-value]


# ── POST /cloud/sync ──────────────────────────────────────────────────────

@router.post("/sync", response_model=APIResponse)
async def create_sync_job(body: SyncRequestData):
    """Create an async sync job (FR-006).

    Returns job_id immediately (202 Accepted). Use GET /cloud/sync/{job_id}/status to poll.
    """
    try:
        sm = _sm()
        job = sm.submit(
            drive_type=body.drive_type.value,
            source_path=body.source_path,
            local_path=body.local_path,
        )

        # Log operation
        try:
            op_logger = get_operation_logger()
            op_logger.log(
                operation="sync_start",
                result=OperationResult.SUCCESS,
                drive_type=body.drive_type.value,
                path=body.source_path,
                extra={"job_id": job.job_id},
            )
        except Exception as e:
            logger.warning(f"Failed to log sync_start: {e}")

        return JSONResponse(
            status_code=202,
            content=APIResponse.ok(
                data=SyncResponseData(
                    job_id=job.job_id,
                    status=SyncStatus.PENDING,
                    source_path=job.source_path,
                    local_path=job.local_path,
                    phase=SyncPhase.DOWNLOADING,
                    progress_bytes=0,
                    total_bytes=0,
                    progress_percent=0.0,
                    created_at=job.created_at,
                ).model_dump()
            ).model_dump(),
        )

    except OperationQueueFullError as e:
        return _error_response(e.CODE, e.message)
    except SyncError as e:
        return _error_response(e.CODE, e.message, e.detail)
    except Exception as e:
        logger.exception(f"Unexpected error in create_sync_job: {e}")
        return _error_response("SYNC_ERROR", str(e))


# ── GET /cloud/sync/{job_id}/status ───────────────────────────────────

@router.get("/sync/{job_id}/status", response_model=APIResponse)
async def get_sync_status(job_id: str = Path(...)):
    """Get sync job progress and status (FR-008)."""
    try:
        sm = _sm()
        job = sm.get_status(job_id)
        return APIResponse.ok(data=job.model_dump())

    except JobNotFoundError as e:
        return _error_response(e.CODE, e.message)
    except Exception as e:
        logger.exception(f"Unexpected error in get_sync_status: {e}")
        return _error_response("SYNC_ERROR", str(e))


# ── POST /cloud/sync/{job_id}/cancel ───────────────────────────────────

@router.post("/sync/{job_id}/cancel", response_model=APIResponse)
async def cancel_sync_job(job_id: str = Path(...)):
    """Cancel a running sync job (FR-009).

    Sends cancel signal, interrupts download, cleans up temp files.
    """
    try:
        sm = _sm()
        job = sm.cancel(job_id)

        # Log operation
        try:
            op_logger = get_operation_logger()
            op_logger.log(
                operation="sync_cancel",
                result=OperationResult.SUCCESS,
                drive_type=job.drive_type,
                path=job.source_path,
                extra={"job_id": job.job_id, "status": job.status.value},
            )
        except Exception as e:
            logger.warning(f"Failed to log sync_cancel: {e}")

        return APIResponse.ok(data=job.model_dump())

    except JobNotFoundError as e:
        return _error_response(e.CODE, e.message)
    except InvalidJobStateError as e:
        return _error_response(e.CODE, e.message, e.detail)
    except Exception as e:
        logger.exception(f"Unexpected error in cancel_sync_job: {e}")
        return _error_response("SYNC_ERROR", str(e))


def _error_response(code: str, message: str, detail: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=APIResponse.error(code=code, message=message, detail=detail).model_dump(),
    )
