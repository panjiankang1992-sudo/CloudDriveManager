"""Pydantic schemas for cloud drive database models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CloudDriveConfigCreate(BaseModel):
    """Request body for creating a new cloud drive config."""

    drive_type: str = Field(..., description="Cloud drive type: pikpak/jianguoyun/baidu/aliyun/quark")
    remote_name: str = Field(..., description="rclone remote name")
    drive_type_variant: str = Field(..., description="rclone remote type: pikpak/jianGuoYun/baidu/AliyunDrive/quark")
    host_endpoint: Optional[str] = Field(None, description="Custom API endpoint (optional)")
    username: Optional[str] = Field(None, description="Login username or email")
    password: Optional[str] = Field(None, description="Plaintext password (will be encrypted)")


class CloudDriveConfigUpdate(BaseModel):
    """Request body for updating a cloud drive config."""

    remote_name: Optional[str] = None
    drive_type_variant: Optional[str] = None
    host_endpoint: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = Field(None, description="Leave empty to keep existing password")
    is_enabled: Optional[bool] = None


class CloudDriveConfigResponse(BaseModel):
    """API response for a cloud drive config (never exposes plaintext password)."""

    drive_type: str
    remote_name: str
    drive_type_variant: str
    host_endpoint: Optional[str] = None
    username: Optional[str] = None
    password_set: bool = Field(..., description="True if a password is stored (value is never returned)")
    is_enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CloudDriveConfigApplyResponse(BaseModel):
    """Response for /admin/cloud-configs/{drive_type}/apply."""

    drive_type: str
    remote_name: str
    action: str = Field(..., description="Action taken: 'created' | 'updated' | 'unchanged'")
    detail: Optional[str] = None
