"""API route: GET /health

Health check endpoint — verifies rclone is available and the service is running.
"""

import shutil
from fastapi import APIRouter

from src.core.config import Config
from ..core.schemas import APIResponse, HealthResponseData

router = APIRouter(tags=["health"])


@router.get("/health", response_model=APIResponse[HealthResponseData])
async def health_check() -> APIResponse[HealthResponseData]:
    """Check service health status.

    Verifies:
    - Application is running
    - Configuration is loaded
    - rclone executable is accessible (on PATH or at configured path)
    """
    cfg = Config.get()
    env = cfg.env

    # Check rclone availability
    rclone_available = _check_rclone(cfg)

    data = HealthResponseData(
        status="healthy" if rclone_available else "degraded",
        version="1.0.0",
        env=env,
        rclone_available=rclone_available,
    )
    return APIResponse.ok(data=data)


def _check_rclone(cfg: Config) -> bool:
    """Check if rclone is available at the configured path or on PATH."""
    try:
        rclone_path = cfg.rclone_path
        if rclone_path:
            return shutil.which(rclone_path) is not None
        # Fall back to PATH
        return shutil.which("rclone") is not None
    except Exception:
        return False
