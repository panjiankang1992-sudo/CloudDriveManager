"""Pydantic schemas for all API request/response models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Generic envelope ───────────────────────────────────────────────────────────

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Unified API response wrapper.

    All API endpoints return this envelope:
      {"code": 0, "message": "success", "data": <payload>}

    code: 0 = success, non-zero = error (maps to CloudDriveError.CODE)
    """

    code: int = 0
    message: str = "success"
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: T = None, message: str = "success") -> "APIResponse[T]":
        return cls(code=0, message=message, data=data)

    @classmethod
    def error(cls, code: int, message: str, detail: Optional[str] = None) -> "APIResponse[None]":
        return cls(code=code, message=message, data=None)


# ── Enums ────────────────────────────────────────────────────────────────────

class DriveType(str, Enum):
    PIKPAK = "pikpak"
    JIANGUOYUN = "jianguoyun"
    BAIDUYUN = "baiduyun"


class SyncStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncPhase(str, Enum):
    DOWNLOADING = "downloading"
    MOVING_TO_BACKUP = "moving-to-backup"
    COMPLETED = "completed"


class OperationResult(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class CloudDownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# ── FileInfo ──────────────────────────────────────────────────────────────────

class FileInfoSchema(BaseModel):
    """Schema for a single file or directory entry."""

    name: str = Field(..., description="File or directory name")
    path: str = Field(..., description="Full path on the cloud drive")
    size: int = Field(default=0, description="Size in bytes (0 for directories)")
    is_dir: bool = Field(default=False, description="True if this is a directory")
    modified: Optional[str] = Field(None, description="ISO 8601 modification time")
    hash: Optional[str] = Field(None, description="MD5 hash if available")
    mime_type: Optional[str] = Field(None, description="MIME type if known")

    model_config = ConfigDict(from_attributes=True)


class FileListData(BaseModel):
    path: str
    files: list[FileInfoSchema]


class FileListResponseData(BaseModel):
    """Response payload for /cloud/{drive_type}/list/detail."""

    path: str
    items: List[FileInfoSchema] = Field(default_factory=list)
    total: int = Field(default=0, description="Total number of items")

    @model_validator(mode="after")
    def compute_total(self) -> "FileListResponseData":
        self.total = len(self.items)
        return self


# ── Health ─────────────────────────────────────────────────────────────────────


class HealthResponseData(BaseModel):
    status: str = Field(..., description="Overall service status")
    version: str = Field(..., description="Application version")
    env: str = Field(..., description="Active environment (dev/prod)")
    rclone_available: bool = Field(default=False, description="rclone executable found")


class HealthCheckResponse(APIResponse[HealthResponseData]):
    pass


# ── Cloud Drive Requests ─────────────────────────────────────────────────────

class CloudDriveListRequest(BaseModel):
    path: str = Field("/", description="Directory path to list (empty defaults to /)")


class CloudDriveDetailRequest(BaseModel):
    path: str = Field(..., description="Full path of file or directory")


class CloudDriveMoveRequest(BaseModel):
    src: str = Field(..., description="Source path")
    dst: str = Field(..., description="Destination path (including filename)")


class CloudDriveDeleteRequest(BaseModel):
    path: str = Field(..., description="Path of file or directory to delete")


class MoveResponseData(BaseModel):
    """Response payload for /cloud/{drive_type}/move."""

    source_path: str
    destination_path: str
    success: bool = True


class DeleteResponseData(BaseModel):
    deleted: bool
    path: str


# ── Sync Job ──────────────────────────────────────────────────────────────────

class SyncJobSchema(BaseModel):
    job_id: str = Field(..., description="UUID of the sync job")
    status: SyncStatus = Field(SyncStatus.PENDING)
    drive_type: DriveType
    source_path: str = Field(..., description="Cloud source path")
    local_path: str = Field(..., description="Local destination path")
    phase: SyncPhase = Field(SyncPhase.DOWNLOADING)
    progress_bytes: int = Field(0, ge=0)
    total_bytes: int = Field(0, ge=0)
    progress_percent: float = Field(0.0, ge=0.0, le=100.0)
    retry_count: int = Field(0, ge=0)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SyncRequestData(BaseModel):
    drive_type: DriveType
    source_path: str = Field(..., description="Cloud path to sync")
    local_path: str = Field(..., description="Local destination path")


class SyncResponseData(BaseModel):
    job_id: str
    status: SyncStatus
    source_path: str
    local_path: str
    phase: SyncPhase
    progress_bytes: int
    total_bytes: int
    progress_percent: float
    created_at: datetime


# ── Offline download (PikPak) ───────────────────────────────────────────────────


class OfflineDownloadRequestData(BaseModel):
    """Request payload for /cloud/pikpak/offline-download."""

    urls: List[str] = Field(..., description="List of URLs to download")
    folder: str = Field(default="/downloads", description="Destination folder on PikPak")


class OfflineDownloadResponseData(BaseModel):
    task_id: str = Field(..., description="Offline download task ID")
    status: str = Field(..., description="Current task status")
    urls_count: int = Field(..., description="Number of URLs in this task")


# ── Offline Download ──────────────────────────────────────────────────────────

class OfflineDownloadRequest(BaseModel):
    urls: list[str] = Field(..., description="List of HTTP or magnet URLs")
    folder: str = Field("/My Pack", description="Destination folder on PikPak")


class OfflineDownloadStatusData(BaseModel):
    task_id: str
    urls: list[str]
    folder: str
    status: str  # pending, running, completed, failed, timeout
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None


# ── Operation Log ─────────────────────────────────────────────────────────────

class OperationLogSchema(BaseModel):
    id: int
    op_user: str = "admin"
    drive_type: str | None = None
    operation: str  # list, detail, move, delete, offline_download, sync_start, sync_cancel
    path: str | None = None
    result: OperationResult
    error_code: str | None = None
    error_message: str | None = None
    extra: dict[str, Any] | None = None
    ip_address: str = "localhost"
    created_at: datetime


class OperationLogQuery(BaseModel):
    page: int = 1
    page_size: int = 20
    operation: str | None = None
    drive_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class OperationLogPageData(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[OperationLogSchema]


class CloudDownloadJobSchema(BaseModel):
    id: int
    task_id: str
    urls: list[str]
    folder: str
    status: CloudDownloadStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Error detail ───────────────────────────────────────────────────────────────


class ErrorDetailSchema(BaseModel):
    """Structured error detail included in API error responses."""

    code: str = Field(..., description="Plain string error code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional context")
