"""Pydantic schemas for API request/response validation.

All schemas follow SC-004: Unified JSON response envelope.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, model_validator


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


# ── File info ──────────────────────────────────────────────────────────────────


class FileInfoSchema(BaseModel):
    """Schema for a single file or directory entry."""

    name: str = Field(..., description="File or directory name")
    path: str = Field(..., description="Full path on the cloud drive")
    size: int = Field(default=0, description="Size in bytes (0 for directories)")
    is_dir: bool = Field(default=False, description="True if this is a directory")
    modified: Optional[str] = Field(None, description="ISO 8601 modification time")
    hash: Optional[str] = Field(None, description="MD5 hash if available")
    mime_type: Optional[str] = Field(None, description="MIME type if known")


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


# ── Sync ───────────────────────────────────────────────────────────────────────


class SyncRequestData(BaseModel):
    """Request payload for /cloud/sync."""

    source_drive: str = Field(..., description="Source cloud drive type (e.g. pikpak)")
    source_path: str = Field(default="/", description="Source directory path")
    destination_drive: str = Field(..., description="Destination cloud drive type")
    destination_path: str = Field(..., description="Destination directory path")
    direction: str = Field(default="cloud-to-local", description="Sync direction")


class SyncResponseData(BaseModel):
    job_id: str = Field(..., description="Unique sync job identifier")
    status: str = Field(..., description="Current job status")
    message: Optional[str] = Field(None, description="Status message or error")


# ── Offline download (PikPak) ───────────────────────────────────────────────────


class OfflineDownloadRequestData(BaseModel):
    """Request payload for /cloud/pikpak/offline-download."""

    urls: List[str] = Field(..., description="List of URLs to download")
    folder: str = Field(default="/downloads", description="Destination folder on PikPak")


class OfflineDownloadResponseData(BaseModel):
    task_id: str = Field(..., description="Offline download task ID")
    status: str = Field(..., description="Current task status")
    urls_count: int = Field(..., description="Number of URLs in this task")


# ── Move ──────────────────────────────────────────────────────────────────────


class MoveRequestData(BaseModel):
    """Request payload for /cloud/{drive_type}/move."""

    source_path: str = Field(..., description="Source file or directory path")
    destination_path: str = Field(..., description="Destination path")


class MoveResponseData(BaseModel):
    """Response payload for /cloud/{drive_type}/move."""

    source_path: str
    destination_path: str
    success: bool = True


# ── Error detail ───────────────────────────────────────────────────────────────


class ErrorDetailSchema(BaseModel):
    """Structured error detail included in API error responses."""

    code: str = Field(..., description="Plain string error code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional context")
