"""Cloud sync API endpoint — syncs files between two cloud drives or cloud to local."""

import uuid
from typing import Optional

from fastapi import APIRouter, Query

from src.core.exceptions import CloudDriveError, SyncError
from src.core.logger import get_logger
from src.core.schemas import APIResponse, SyncRequestData, SyncResponseData
from src.services.base import CloudDriveService
from src.api.cloud import get_drive_service, SUPPORTED_DRIVES

logger = get_logger("sync_api")

router = APIRouter(prefix="/cloud", tags=["sync"])


@router.post("/sync", response_model=APIResponse[SyncResponseData])
async def sync_files(body: SyncRequestData):
    """Sync files between two cloud drives or between cloud and local.

    Currently supports:
    - cloud-to-local: download from cloud to local filesystem
    - local-to-cloud: upload from local to cloud (future)
    - cloud-to-cloud: copy between two cloud remotes (future)
    """
    try:
        job_id = str(uuid.uuid4())[:8]

        # cloud-to-local: use download
        if body.direction == "cloud-to-local":
            source_service = get_drive_service(
                body.source_drive,
                rclone_path="",  # will be loaded from config
                remote_name="",
                timeout=300,
            )
            # Load config inline to get rclone_path
            from src.config.config import Config
            cfg = Config.get()
            drive_cfg = getattr(cfg, body.source_drive, {})
            rclone_path = drive_cfg.get("rclone_path", "rclone")
            remote_name = drive_cfg.get("remote_name", "")
            source_service = get_drive_service(body.source_drive, rclone_path, remote_name, 300)

            source_service.download(body.source_path, body.destination_path)
            data = SyncResponseData(
                job_id=job_id,
                status="completed",
                message=f"Synced {body.source_path} -> {body.destination_path}",
            )
            return APIResponse.ok(data=data)

        raise SyncError(
            message=f"Unsupported sync direction: {body.direction}",
            detail="Supported: cloud-to-local",
        )

    except CloudDriveError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content=APIResponse.error(code=1, message=e.message, detail=e.detail).model_dump(),
        )
