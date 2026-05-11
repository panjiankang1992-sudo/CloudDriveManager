"""FastAPI application entry point.

Loads config, sets up logging and encryption, then starts uvicorn.
"""

import sys
from pathlib import Path

# Ensure src/ is on the path for absolute imports
# In dev:   __file__ = D:\MyCode\CloudDriveManager\main.py  → parent = project root
# In bundle: __file__ = <_MEIPASS>/main.py                  → parent = bundle root (= _MEIPASS)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.config import Config
from src.core.exceptions import CloudDriveError
from src.core.logger import get_logger, setup_logger
from src.core import encryption as enc
from src.core.schemas import APIResponse
from src.api import health
from src.api.cloud import create_cloud_router, SUPPORTED_DRIVES, get_drive_service
from src.api.sync import router as sync_router
from src.api.admin import router as admin_router
from src.db.database import Database
from src.services.rclone_configurator import run_autoconfig

logger = get_logger("main")

# ── App factory ────────────────────────────────────────────────────────────────


def create_app(env: str = "dev") -> FastAPI:
    """Create and configure the FastAPI application."""
    # 1. Load configuration
    cfg = Config.get(env=env)

    # 2. Set up logging
    setup_logger("main")

    # 3. Configure encryption (Fernet key from config)
    salt = cfg.encryption_salt.strip()
    if salt:
        enc.configure(salt)

    # 3b. Auto-configure rclone remotes from database (non-blocking)
    try:
        db = Database.get()
        if db:
            results = run_autoconfig(db, rclone_path=cfg.rclone_path)
            for r in results:
                if r["action"] == "failed":
                    logger.error("Auto-config failed for %s: %s", r["drive_type"], r.get("detail"))
                else:
                    logger.info("Auto-config %s for %s", r["action"], r["drive_type"])
    except Exception as e:
        logger.warning("Database auto-config skipped: %s", e)

    # 4. Create FastAPI app
    app = FastAPI(
        title="cloud_drive_manager",
        version="1.0.0",
        description="Cloud Drive Manager — multi-cloud-drive HTTP service via rclone",
    )

    # 5. Register exception handler
    @app.exception_handler(CloudDriveError)
    async def cloud_drive_error_handler(request: Request, exc: CloudDriveError) -> JSONResponse:
        logger.warning("CloudDriveError: %s | %s | %s", exc.CODE, exc.message, exc.detail)
        return JSONResponse(
            status_code=500,
            content=APIResponse.error(
                code=1,  # non-zero → client error indicator
                message=exc.message,
                detail=exc.detail,
            ).model_dump(),
        )

    # 6. Include routers
    app.include_router(health.router)
    app.include_router(sync_router)
    app.include_router(admin_router)

    # 7. Register cloud drive routers
    cfg = Config.get()
    for drive_type in SUPPORTED_DRIVES:
        drive_cfg = getattr(cfg, drive_type, {})
        rclone_path = drive_cfg.get("rclone_path", "rclone")
        remote_name = drive_cfg.get("remote_name", "")
        timeout = drive_cfg.get("timeout", 300)

        if not remote_name:
            logger.warning("Skipping %s: no remote_name configured", drive_type)
            continue

        try:
            service = get_drive_service(drive_type, rclone_path, remote_name, timeout)
            app.include_router(create_cloud_router(drive_type, rclone_path, remote_name, timeout))
            logger.info("Registered router for %s (remote=%s)", drive_type, remote_name)
        except Exception as e:
            logger.warning("Failed to register %s: %s", drive_type, e)

    logger.info("Application created | env=%s | version=1.0.0", env)
    return app


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    """Run the application with uvicorn."""
    import uvicorn

    env = "prod" if "--prod" in sys.argv else "dev"
    app = create_app(env)

    cfg = Config.get()
    uvicorn.run(
        app,
        host=cfg.app_host,
        port=cfg.app_port,
        log_level="debug" if env == "dev" else "info",
    )


if __name__ == "__main__":
    main()
