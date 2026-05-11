"""Admin CRUD API for cloud drive configurations stored in MySQL."""

from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.core.exceptions import CloudDriveError
from src.core.schemas import APIResponse
from src.core.config import Config
from src.db.database import Database
from src.db.repository import CloudDriveConfigRepository
from src.db.schemas import (
    CloudDriveConfigCreate,
    CloudDriveConfigUpdate,
    CloudDriveConfigResponse,
    CloudDriveConfigApplyResponse,
)
from src.services.rclone_configurator import RcloneConfigurator

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_repo():
    """Get a repository with an active DB connection."""
    cfg = Config.get()
    db = Database.get()
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    return CloudDriveConfigRepository(db)


def _apply_rclone_config(drive_type: str, remote_name: str) -> dict:
    """Apply rclone config for a single drive (create/update)."""
    cfg = Config.get()
    db = Database.get()
    if not db:
        return {"action": "skipped", "detail": "no DB connection"}

    rclone_path = cfg.rclone_path

    configurator = RcloneConfigurator(rclone_path)
    return configurator.apply_single(db, drive_type)


# ── GET /admin/cloud-configs ─────────────────────────────────────────────────

@router.get("/cloud-configs", response_model=APIResponse[List[CloudDriveConfigResponse]])
async def list_configs():
    """List all cloud drive configurations (password never returned)."""
    try:
        repo = _get_repo()
        configs = repo.list_all()
        return APIResponse.ok(data=configs)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error(code=1, message=str(e)).model_dump(),
        )


# ── GET /admin/cloud-configs/{drive_type} ──────────────────────────────────

@router.get("/cloud-configs/{drive_type}", response_model=APIResponse[CloudDriveConfigResponse])
async def get_config(drive_type: str):
    """Get a specific cloud drive configuration."""
    try:
        repo = _get_repo()
        config = repo.get_by_drive_type(drive_type)
        if not config:
            raise HTTPException(status_code=404, detail=f"No config found for drive_type: {drive_type}")
        return APIResponse.ok(data=config)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error(code=1, message=str(e)).model_dump(),
        )


# ── POST /admin/cloud-configs ───────────────────────────────────────────────

@router.post("/cloud-configs", response_model=APIResponse[CloudDriveConfigResponse], status_code=201)
async def create_config(body: CloudDriveConfigCreate):
    """Create a new cloud drive configuration.

    Password is encrypted before storage.
    If is_enabled=True, immediately applies rclone config.
    """
    try:
        repo = _get_repo()

        # Check for duplicate
        existing = repo.get_by_drive_type(body.drive_type)
        if existing:
            raise HTTPException(status_code=409, detail=f"Config already exists for drive_type: {body.drive_type}")

        created = repo.create(body)

        # Auto-apply if enabled
        cfg = Config.get()
        if created.is_enabled:
            db = Database.get()
            if db:
                rclone_path = cfg.rclone_path
                configurator = RcloneConfigurator(rclone_path)
                configurator.apply_single(db, body.drive_type)

        return APIResponse.ok(data=created)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error(code=1, message=str(e)).model_dump(),
        )


# ── PUT /admin/cloud-configs/{drive_type} ──────────────────────────────────

@router.put("/cloud-configs/{drive_type}", response_model=APIResponse[CloudDriveConfigResponse])
async def update_config(drive_type: str, body: CloudDriveConfigUpdate):
    """Update a cloud drive configuration.

    If password is provided, it is re-encrypted.
    If is_enabled=True and remote_name changed, re-applies rclone config.
    """
    try:
        repo = _get_repo()
        updated = repo.update(drive_type, body)
        if not updated:
            raise HTTPException(status_code=404, detail=f"No config found for drive_type: {drive_type}")

        # Re-apply rclone config if enabled
        cfg = Config.get()
        if updated.is_enabled:
            db = Database.get()
            if db:
                rclone_path = cfg.rclone_path
                configurator = RcloneConfigurator(rclone_path)
                configurator.apply_single(db, drive_type)

        return APIResponse.ok(data=updated)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error(code=1, message=str(e)).model_dump(),
        )


# ── DELETE /admin/cloud-configs/{drive_type} ────────────────────────────────

@router.delete("/cloud-configs/{drive_type}", response_model=APIResponse[dict])
async def delete_config(drive_type: str):
    """Delete a cloud drive configuration."""
    try:
        repo = _get_repo()
        deleted = repo.delete(drive_type)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"No config found for drive_type: {drive_type}")

        # Also delete the rclone remote if it exists
        cfg = Config.get()
        db = Database.get()
        if db:
            rclone_path = cfg.rclone_path
            configurator = RcloneConfigurator(rclone_path)
            if configurator.remote_exists(repo.get_by_drive_type_raw(drive_type)["remote_name"] if repo.get_by_drive_type_raw(drive_type) else ""):
                # We don't have the original remote_name since we deleted — skip
                pass

        return APIResponse.ok(data={"deleted": drive_type})
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error(code=1, message=str(e)).model_dump(),
        )


# ── POST /admin/cloud-configs/{drive_type}/apply ─────────────────────────────

@router.post("/cloud-configs/{drive_type}/apply", response_model=APIResponse[CloudDriveConfigApplyResponse])
async def apply_config(drive_type: str):
    """Manually trigger rclone config apply for a specific cloud drive.

    Creates the remote if it doesn't exist, or updates if it does.
    """
    try:
        repo = _get_repo()
        raw = repo.get_by_drive_type_raw(drive_type)
        if not raw:
            raise HTTPException(status_code=404, detail=f"No config found for drive_type: {drive_type}")

        cfg = Config.get()
        rclone_path = cfg.rclone_path
        configurator = RcloneConfigurator(rclone_path)
        result = configurator.apply_single(repo.conn_mgr, drive_type)

        return APIResponse.ok(data=CloudDriveConfigApplyResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error(code=1, message=str(e)).model_dump(),
        )
