"""Operation logger — writes API audit records to MySQL (SC-008: ≤500ms write)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from src.core.schemas import OperationLogSchema, OperationResult
from src.core.logger import get_logger

logger = get_logger("operation_logger")


class OperationLogger:
    """Thread-safe synchronous operation logger (SC-008 compliant).

    Writes operation audit records directly to MySQL — no queue, no async,
    to guarantee ≤500ms write latency.
    """

    def __init__(self):
        self._db = self._get_db()

    @staticmethod
    def _get_db():
        from src.db.database import Database
        return Database.get()

    def log(
        self,
        operation: str,
        result: OperationResult,
        drive_type: Optional[str] = None,
        path: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
        ip_address: str = "localhost",
    ) -> None:
        """Synchronously write an operation log record to MySQL.

        Args:
            operation: Operation type (list/detail/move/delete/sync_start/sync_cancel/offline_download/admin_*)
            result: SUCCESS or FAILED
            drive_type: Cloud drive type (e.g., "pikpak", "baidu")
            path: File/folder path on cloud drive
            error_code: Error code string (if result is FAILED)
            error_message: Error message (if result is FAILED)
            extra: Additional JSON-serializable data (e.g., {"job_id": "abc123"})
            ip_address: Caller IP address
        """
        from src.core.schemas import OperationLogSchema

        now = datetime.now(timezone.utc)
        extra_json = json.dumps(extra, ensure_ascii=False) if extra else None

        sql = """
        INSERT INTO operation_logs
            (op_user, drive_type, operation, path, result, error_code, error_message, extra, ip_address, created_at)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            "admin",
            drive_type,
            operation,
            path,
            result.value,
            error_code,
            error_message,
            extra_json,
            ip_address,
            now,
        )

        try:
            self._db.execute(sql, params)
            logger.debug(
                f"Operation logged: {operation} {result.value} path={path}",
                extra={"extra": extra},
            )
        except Exception as e:
            # SC-008: Log errors but never crash the request
            logger.error(f"Failed to write operation log: {e}")

    def query(
        self,
        page: int = 1,
        page_size: int = 20,
        operation: Optional[str] = None,
        drive_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> tuple[list[OperationLogSchema], int]:
        """Query operation logs with pagination and filters.

        Returns:
            (items, total_count)
        """
        conditions = ["1=1"]
        params: list[Any] = []

        if operation:
            conditions.append("operation = %s")
            params.append(operation)
        if drive_type:
            conditions.append("drive_type = %s")
            params.append(drive_type)
        if start_date:
            conditions.append("created_at >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("created_at <= %s")
            params.append(end_date)

        where = " AND ".join(conditions)

        # Count total
        count_sql = f"SELECT COUNT(*) as cnt FROM operation_logs WHERE {where}"
        row = self._db.fetch_one(count_sql, tuple(params))
        total = int(row["cnt"]) if row else 0

        # Fetch page
        offset = (page - 1) * page_size
        select_sql = (
            f"SELECT * FROM operation_logs WHERE {where} "
            f"ORDER BY created_at DESC LIMIT %s OFFSET %s"
        )
        rows = self._db.fetch_all(select_sql, tuple(params + [page_size, offset]))

        items = []
        for row in rows:
            items.append(
                OperationLogSchema(
                    id=row["id"],
                    op_user=row["op_user"],
                    drive_type=row["drive_type"],
                    operation=row["operation"],
                    path=row["path"],
                    result=OperationResult(row["result"]),
                    error_code=row["error_code"],
                    error_message=row["error_message"],
                    extra=row["extra"],
                    ip_address=row["ip_address"],
                    created_at=row["created_at"],
                )
            )
        return items, total


# Singleton instance
_operation_logger: OperationLogger | None = None


def get_operation_logger() -> OperationLogger:
    global _operation_logger
    if _operation_logger is None:
        _operation_logger = OperationLogger()
    return _operation_logger