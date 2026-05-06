"""FastAPI application entry point.

HTTPServer (port 29312, config driven).
MCP server (port 29313) via cloud-drive-mcp package.
"""

from __future__ import annotations

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.core.config import Config
from src.core.logger import get_logger, setup_logger
from src.core.exceptions import CloudDriveError
from src.api.cloud import create_cloud_router
from src.api.sync import router as sync_router, set_sync_manager
from src.api.operation_log import router as operation_log_router

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # ── Startup ────────────────────────────────────────────────────────────
    cfg: Any = Config.get()  # type: ignore[reportCallIssue]
    setup_logger("app", log_file=cfg.log_file, level=cfg.log_level)  # type: ignore[reportCallIssue]

    logger.info(
        f"Starting CloudDriveManager on {cfg.app_host}:{cfg.app_port} "
        f"(env={cfg.env})"
    )

    # Initialize sync manager (lazy, but prime it now)
    try:
        from src.services.sync_manager import get_sync_manager
        set_sync_manager(get_sync_manager())
        logger.info("Sync manager initialized")
    except Exception as e:
        logger.warning(f"Sync manager init skipped: {e}")

    # ── Shutdown ──────────────────────────────────────────────────────────
    yield
    logger.info("Shutting down CloudDriveManager")
    try:
        from src.db.database import Database
        Database.get().close()
    except Exception:
        pass


def create_app() -> FastAPI:
    """Factory: build and configure the FastAPI application."""
    cfg: Any = Config.get()  # type: ignore[reportCallIssue]

    app = FastAPI(
        title="CloudDriveManager API",
        description="Universal cloud drive file manager (list/detail/move/delete/sync)",
        version="0.1.0",
        docs_url="/docs" if cfg.env == "dev" else None,
        redoc_url="/redoc" if cfg.env == "dev" else None,
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ────────────────────────────────────────────────────────────
    app.include_router(create_cloud_router())
    app.include_router(sync_router)
    app.include_router(operation_log_router)

    # ── Health check ───────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    # ── Global exception handler ─────────────────────────────────────────
    @app.exception_handler(CloudDriveError)
    async def cloud_drive_error_handler(request, exc: CloudDriveError):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"code": exc.CODE, "message": exc.message, "detail": exc.detail},
        )

    return app


# ── Application instance ──────────────────────────────────────────────────────

app = create_app()


if __name__ == "__main__":
    import uvicorn

    cfg: Any = Config.get()  # type: ignore[reportCallIssue]
    uvicorn.run(
        "src.app:app",
        host=cfg.app_host,
        port=cfg.app_port,
        reload=(cfg.env == "dev"),
    )
