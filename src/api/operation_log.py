"""Operation log query API (audit log).

GET /cloud/admin/operation-logs
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.core.logger import get_logger
from src.core.schemas import APIResponse, OperationLogQuery, OperationLogPageData
from src.core.operation_logger import get_operation_logger

logger = get_logger("operation_log")

router = APIRouter(prefix="/cloud/admin", tags=["admin"])


@router.get("/operation-logs", response_model=APIResponse)
async def query_operation_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Records per page"),
    operation: str | None = Query(None, description="Filter by operation type"),
    drive_type: str | None = Query(None, description="Filter by cloud drive type"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Query operation audit logs with pagination and filtering (SC-008)."""
    try:
        op_logger = get_operation_logger()
        items, total = op_logger.query(
            page=page,
            page_size=page_size,
            operation=operation,
            drive_type=drive_type,
            start_date=start_date,
            end_date=end_date,
        )

        return APIResponse.ok(
            data=OperationLogPageData(
                total=total,
                page=page,
                page_size=page_size,
                items=items,
            ).model_dump()
        )

    except Exception as e:
        logger.exception(f"Unexpected error in query_operation_logs: {e}")
        return JSONResponse(
            status_code=500,
            content=APIResponse.error(code="INTERNAL_ERROR", message=str(e)).model_dump(),
        )