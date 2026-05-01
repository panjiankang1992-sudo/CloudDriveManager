"""Pydantic schemas for all API request/response models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class DriveType(str, Enum):
    PIKPAK = "pikpak"
    JIANGUOYUN = "jianguoyun"
    BAIDU = "baidu"
    ALIYUN = "aliyun"
    QUARK = "quark"


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


# ── FileInfo ─────────────────────────────────────────────────────────────────

class FileInfoSchema(BaseModel):
    """Cloud drive file/folder metadata."""

    name: str = Field(..., description="File name (without path)")
    path: str = Field(..., description="Full absolute path")
    size: int = Field(..., ge=0, description="Size in bytes (0 for directory)")
    is_dir: bool = Field(..., description="True if directory")
    modified: datetime = Field(..., description="Last modified time (ISO 8601)")
    mime_type: str | None = Field(None, description="MIME type (null for directory)")

    class Config:
        from_attributes = True


# ── Cloud Drive Requests ──────────────────────────────────────────────────────

class CloudDriveListRequest(BaseModel):
    path: str = Field("/", description="Absolute path on the remote; empty returns root")


class CloudDriveDetailRequest(BaseModel):
    path: str = Field(..., min_length=1, description="Absolute path; cannot be empty")


class CloudDriveMoveRequest(BaseModel):
    src: str = Field(..., min_length=1, description="Source absolute path")
    dst: str = Field(..., min_length=1, description="Destination absolute path")


class CloudDriveDeleteRequest(BaseModel):
    path: str = Field(..., min_length=1, description="Path to delete (cannot be /)")


# ── Sync Job ─────────────────────────────────────────────────────────────────

class SyncJobSchema(BaseModel):
    job_id: str = Field(..., description="UUID of the sync job")
    drive_type: DriveType
    source_path: str = Field(..., description="Cloud source path")
    local_path: str = Field(..., description="Local destination path")
    status: SyncStatus = Field(SyncStatus.PENDING)
    phase: SyncPhase = Field(SyncPhase.DOWNLOADING)
    progress_bytes: int = Field(0, ge=0)
    total_bytes: int = Field(0, ge=0)
    progress_percent: float = Field(0.0, ge=0.0, le=100.0)
    retry_count: int = Field(0, ge=0)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None

    class Config:
        from_attributes = True


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


# ── Offline Download ─────────────────────────────────────────────────────────

class OfflineDownloadRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, description="URLs or magnet links to download")
    folder: str = Field("/My Pack", description="Destination folder on PikPak")


class OfflineDownloadResponseData(BaseModel):
    task_id: str
    drive_type: DriveType = DriveType.PIKPAK
    urls_count: int
    destination_folder: str
    status: str = "pending"
    created_at: datetime


# ── API Response Wrapper ──────────────────────────────────────────────────────

class APIResponse(BaseModel):
    code: int | str = Field(0, description="0 = success, error code otherwise (int or str)")
    message: str = Field("success")
    data: Any = Field(None)

    @classmethod
    def ok(cls, data: Any = None, message: str = "success") -> APIResponse:
        return cls(code=0, message=message, data=data)

    @classmethod
    def error(cls, code: str = "UNKNOWN", message: str = "error", detail: str | None = None) -> APIResponse:
        return cls(code=code, message=message, data={"detail": detail} if detail else None)


# ── Operation Log ────────────────────────────────────────────────────────────

class OperationLogSchema(BaseModel):
    id: int
    op_user: str = "admin"
    drive_type: str | None = None
    operation: str  # list, detail, move, delete, offline_download, sync_start, sync_cancel
    path: str | None = None
    result: OperationResult
    error_code: str | None = None
    error_message: str | None = None
    extra: str | None = None  # JSON string
    ip_address: str = "localhost"
    created_at: datetime


class OperationLogQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    operation: str | None = None
    drive_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class OperationLogPageData(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[OperationLogSchema]


# ── Move Response ────────────────────────────────────────────────────────────

class MoveResponseData(BaseModel):
    src: str
    dst: str
    moved: bool


# ── Delete Response ──────────────────────────────────────────────────────────

class DeleteResponseData(BaseModel):
    deleted: bool
    path: str


# ── List Response ────────────────────────────────────────────────────────────

class FileListData(BaseModel):
    path: str
    files: list[FileInfoSchema]