"""FastMCP server — exposes CloudDriveManager tools via MCP (port 29313).

Stateless HTTP MCP server.
Tools mirror the HTTP API endpoints for cloud drive operations.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from src.core.config import Config
from src.core.logger import get_logger
from src.core.schemas import (
    DriveType,
    SyncRequestData,
)
from src.services.base import get_drive_service
from src.services.sync_manager import get_sync_manager
from typing import Any

logger = get_logger("mcp_server")

# ── FastMCP instance ─────────────────────────────────────────────────────────

mcp = FastMCP(
    "CloudDriveManager",
    instructions="Universal cloud drive file operations (list/detail/move/delete/sync/offline-download)",
)


# ── Helper ───────────────────────────────────────────────────────────────────

def _cfg() -> Any:
    return Config.get()  # type: ignore[reportCallIssue]


# ── List files ───────────────────────────────────────────────────────────────

@mcp.tool()
def pikpak_list_files(path: str = "/") -> dict[str, Any]:
    """List files in a PikPak directory.

    Args:
        path: Remote path (default: root /)
    Returns:
        {"files": [...], "path": str}
    """
    service = get_drive_service("pikpak")
    files = service.list_files(path)
    return {"path": path, "files": [f.model_dump() for f in files]}


@mcp.tool()
def jianguoyun_list_files(path: str = "/") -> dict[str, Any]:
    """List files in a JianGuoYun directory."""
    service = get_drive_service("jianguoyun")
    files = service.list_files(path)
    return {"path": path, "files": [f.model_dump() for f in files]}


@mcp.tool()
def baidu_list_files(path: str = "/") -> dict[str, Any]:
    """List files in a Baidu cloud directory."""
    service = get_drive_service("baidu")
    files = service.list_files(path)
    return {"path": path, "files": [f.model_dump() for f in files]}


@mcp.tool()
def aliyun_list_files(path: str = "/") -> dict[str, Any]:
    """List files in an Aliyun directory."""
    service = get_drive_service("aliyun")
    files = service.list_files(path)
    return {"path": path, "files": [f.model_dump() for f in files]}


@mcp.tool()
def quark_list_files(path: str = "/") -> dict[str, Any]:
    """List files in a Quark directory."""
    service = get_drive_service("quark")
    files = service.list_files(path)
    return {"path": path, "files": [f.model_dump() for f in files]}


# ── Detail ───────────────────────────────────────────────────────────────────

@mcp.tool()
def pikpak_get_file_detail(path: str) -> dict[str, Any]:
    """Get file/folder metadata on PikPak.

    Args:
        path: Full path to the file
    Returns:
        FileInfo dict
    Raises:
        FileNotFoundError: if path does not exist
    """
    service = get_drive_service("pikpak")
    files = service.list_detail(path)
    if not files:
        raise FileNotFoundError(f"File not found: {path}")
    # list_detail returns all items in the directory, find the target
    target = next(
        (f for f in files if f.path.rstrip("/") == path.rstrip("/") or f.name == path.lstrip("/")),
        files[0],
    )
    return target.model_dump()


# ── Move ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def pikpak_move_file(src: str, dst: str) -> dict[str, Any]:
    """Move/rename a file or folder on PikPak.

    Args:
        src: Source path
        dst: Destination path (including filename)
    Returns:
        {"src": str, "dst": str, "moved": bool}
    """
    service = get_drive_service("pikpak")
    service.move(src, dst)
    return {"src": src, "dst": dst, "moved": True}


# ── Delete ───────────────────────────────────────────────────────────────────

@mcp.tool()
def pikpak_delete_file(path: str) -> dict[str, Any]:
    """Delete a file or folder on PikPak.

    Args:
        path: Path to delete (must not be root /)
    Returns:
        {"deleted": bool, "path": str}
    Raises:
        ValidationError: if path is empty or root
    """
    service = get_drive_service("pikpak")
    service.delete(path)
    return {"deleted": True, "path": path}


# ── Sync ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def pikpak_sync_to_local(source_path: str, local_path: str) -> dict[str, Any]:
    """Start an async sync job: download cloud file to local path.

    Args:
        source_path: Remote cloud path
        local_path: Local destination directory
    Returns:
        {"job_id": str, "status": str, "source_path": str, "local_path": str}
    """
    sm = get_sync_manager()
    job = sm.submit(
        drive_type="pikpak",
        source_path=source_path,
        local_path=local_path,
    )
    return job.to_schema().model_dump()


@mcp.tool()
def pikpak_get_sync_status(job_id: str) -> dict[str, Any]:
    """Query sync job progress.

    Args:
        job_id: UUID of the sync job
    Returns:
        SyncJobSchema dict
    Raises:
        JobNotFoundError: if job_id not found
    """
    sm = get_sync_manager()
    return sm.get_status(job_id).model_dump()


@mcp.tool()
def pikpak_cancel_sync(job_id: str) -> dict[str, Any]:
    """Cancel a running or pending sync job.

    Args:
        job_id: UUID of the sync job
    Returns:
        SyncJobSchema dict
    Raises:
        JobNotFoundError: if job_id not found
        InvalidJobStateError: if job is not cancellable
    """
    sm = get_sync_manager()
    return sm.cancel(job_id).to_schema().model_dump()


# ── Entry point ─────────────────────────────────────────────────────────────

def run(port: int | None = None) -> None:
    """Start the MCP server."""
    cfg = _cfg()
    listen_port = port or 29313
    logger.info(f"Starting MCP server on port {listen_port}")
    mcp.run(transport="http", host="0.0.0.0", port=listen_port)


if __name__ == "__main__":
    run()