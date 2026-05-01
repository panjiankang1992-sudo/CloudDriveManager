"""CloudDrive MCP Server — exposes cloud drive operations as MCP tools.

All tools call the same FastAPI HTTP endpoints running at the configured base URL.
The MCP server acts as a thin proxy so that other AI agents can interact with
the cloud drive manager without needing to manage HTTP requests manually.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

# Ensure src/ is on the path (same pattern as main.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastmcp import FastMCP

from src.config.config import Config
from src.core import encryption
from src.core.logger import get_logger, setup_logger

logger = get_logger("mcp.server")

# ── MCP server instance ─────────────────────────────────────────────────────────

mcp = FastMCP("CloudDriveManager")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_base_url() -> str:
    """Return the base URL for HTTP API calls (read from config)."""
    cfg = Config.get()
    host = cfg.server.get("host", "0.0.0.0")
    port = cfg.server.get("port", 8000)
    return f"http://{host}:{port}"


def _http_call(method: str, path: str, json_data: Optional[dict] = None) -> dict:
    """Make an HTTP call to the local FastAPI server and return parsed JSON."""
    import httpx

    base = _get_base_url()
    url = f"{base}{path}"
    timeout = 60.0

    with httpx.Client(timeout=timeout) as client:
        if method == "GET":
            resp = client.get(url)
        elif method == "POST":
            resp = client.post(url, json=json_data)
        elif method == "DELETE":
            resp = client.request("DELETE", url)
        elif method == "PUT":
            resp = client.request("PUT", url, json=json_data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        resp.raise_for_status()
        return resp.json()


# ── Cloud drive tools — PikPak ─────────────────────────────────────────────────

@mcp.tool(name="pikpak_list")
def pikpak_list(path: str = "/") -> dict:
    """List files on PikPak (lightweight).

    Args:
        path: Remote path to list (default: /).
    """
    return _http_call("GET", f"/cloud/pikpak/list?path={path}")


@mcp.tool(name="pikpak_detail")
def pikpak_detail(path: str = "/") -> dict:
    """List files on PikPak with full metadata.

    Args:
        path: Remote path to list (default: /).
    """
    return _http_call("GET", f"/cloud/pikpak/detail?path={path}")


@mcp.tool(name="pikpak_delete")
def pikpak_delete(path: str) -> dict:
    """Delete a file or directory from PikPak.

    Args:
        path: Absolute path of the file or directory to delete.
    """
    return _http_call("DELETE", f"/cloud/pikpak/delete?path={path}")


@mcp.tool(name="pikpak_move")
def pikpak_move(source_path: str, destination_path: str) -> dict:
    """Move or rename a file within PikPak.

    Args:
        source_path: Source file absolute path.
        destination_path: Destination file absolute path.
    """
    body = {"source_path": source_path, "destination_path": destination_path}
    return _http_call("POST", "/cloud/pikpak/move", json_data=body)


# ── Cloud drive tools — JianGuoYun ─────────────────────────────────────────────

@mcp.tool(name="jianguoyun_list")
def jianguoyun_list(path: str = "/") -> dict:
    """List files on JianGuoYun (lightweight).

    Args:
        path: Remote path to list (default: /).
    """
    return _http_call("GET", f"/cloud/jianguoyun/list?path={path}")


@mcp.tool(name="jianguoyun_detail")
def jianguoyun_detail(path: str = "/") -> dict:
    """List files on JianGuoYun with full metadata.

    Args:
        path: Remote path to list (default: /).
    """
    return _http_call("GET", f"/cloud/jianguoyun/detail?path={path}")


@mcp.tool(name="jianguoyun_delete")
def jianguoyun_delete(path: str) -> dict:
    """Delete a file or directory from JianGuoYun.

    Args:
        path: Absolute path of the file or directory to delete.
    """
    return _http_call("DELETE", f"/cloud/jianguoyun/delete?path={path}")


@mcp.tool(name="jianguoyun_move")
def jianguoyun_move(source_path: str, destination_path: str) -> dict:
    """Move or rename a file within JianGuoYun.

    Args:
        source_path: Source file absolute path.
        destination_path: Destination file absolute path.
    """
    body = {"source_path": source_path, "destination_path": destination_path}
    return _http_call("POST", "/cloud/jianguoyun/move", json_data=body)


# ── Cloud drive tools — Baidu ──────────────────────────────────────────────────

@mcp.tool(name="baidu_list")
def baidu_list(path: str = "/") -> dict:
    """List files on Baidu (lightweight).

    Args:
        path: Remote path to list (default: /).
    """
    return _http_call("GET", f"/cloud/baidu/list?path={path}")


@mcp.tool(name="baidu_detail")
def baidu_detail(path: str = "/") -> dict:
    """List files on Baidu with full metadata.

    Args:
        path: Remote path to list (default: /).
    """
    return _http_call("GET", f"/cloud/baidu/detail?path={path}")


@mcp.tool(name="baidu_delete")
def baidu_delete(path: str) -> dict:
    """Delete a file or directory from Baidu.

    Args:
        path: Absolute path of the file or directory to delete.
    """
    return _http_call("DELETE", f"/cloud/baidu/delete?path={path}")


@mcp.tool(name="baidu_move")
def baidu_move(source_path: str, destination_path: str) -> dict:
    """Move or rename a file within Baidu.

    Args:
        source_path: Source file absolute path.
        destination_path: Destination file absolute path.
    """
    body = {"source_path": source_path, "destination_path": destination_path}
    return _http_call("POST", "/cloud/baidu/move", json_data=body)


# ── Cloud drive tools — Aliyun ──────────────────────────────────────────────────

@mcp.tool(name="aliyun_list")
def aliyun_list(path: str = "/") -> dict:
    """List files on Aliyun (lightweight).

    Args:
        path: Remote path to list (default: /).
    """
    return _http_call("GET", f"/cloud/aliyun/list?path={path}")


@mcp.tool(name="aliyun_detail")
def aliyun_detail(path: str = "/") -> dict:
    """List files on Aliyun with full metadata.

    Args:
        path: Remote path to list (default: /).
    """
    return _http_call("GET", f"/cloud/aliyun/detail?path={path}")


@mcp.tool(name="aliyun_delete")
def aliyun_delete(path: str) -> dict:
    """Delete a file or directory from Aliyun.

    Args:
        path: Absolute path of the file or directory to delete.
    """
    return _http_call("DELETE", f"/cloud/aliyun/delete?path={path}")


@mcp.tool(name="aliyun_move")
def aliyun_move(source_path: str, destination_path: str) -> dict:
    """Move or rename a file within Aliyun.

    Args:
        source_path: Source file absolute path.
        destination_path: Destination file absolute path.
    """
    body = {"source_path": source_path, "destination_path": destination_path}
    return _http_call("POST", "/cloud/aliyun/move", json_data=body)


# ── Cloud drive tools — Quark ───────────────────────────────────────────────────

@mcp.tool(name="quark_list")
def quark_list(path: str = "/") -> dict:
    """List files on Quark (lightweight).

    Args:
        path: Remote path to list (default: /).
    """
    return _http_call("GET", f"/cloud/quark/list?path={path}")


@mcp.tool(name="quark_detail")
def quark_detail(path: str = "/") -> dict:
    """List files on Quark with full metadata.

    Args:
        path: Remote path to list (default: /).
    """
    return _http_call("GET", f"/cloud/quark/detail?path={path}")


@mcp.tool(name="quark_delete")
def quark_delete(path: str) -> dict:
    """Delete a file or directory from Quark.

    Args:
        path: Absolute path of the file or directory to delete.
    """
    return _http_call("DELETE", f"/cloud/quark/delete?path={path}")


@mcp.tool(name="quark_move")
def quark_move(source_path: str, destination_path: str) -> dict:
    """Move or rename a file within Quark.

    Args:
        source_path: Source file absolute path.
        destination_path: Destination file absolute path.
    """
    body = {"source_path": source_path, "destination_path": destination_path}
    return _http_call("POST", "/cloud/quark/move", json_data=body)


# ── PikPak offline download ────────────────────────────────────────────────────

@mcp.tool(name="pikpak_offline_download")
def pikpak_offline_download(urls: List[str], folder: str = "/downloads") -> dict:
    """Add offline download tasks to PikPak.

    Args:
        urls: List of HTTP URLs or magnet links to download.
        folder: Destination folder on PikPak (default: /downloads).
    """
    body = {"urls": urls, "folder": folder}
    return _http_call("POST", "/cloud/pikpak/offline-download", json_data=body)


# ── Admin tools ────────────────────────────────────────────────────────────────

@mcp.tool(name="admin_list_configs")
def admin_list_configs() -> dict:
    """List all cloud drive configurations from the database."""
    return _http_call("GET", "/admin/cloud-configs")


@mcp.tool(name="admin_get_config")
def admin_get_config(drive_type: str) -> dict:
    """Get cloud drive configuration by drive type.

    Args:
        drive_type: Cloud drive type (pikpak, jianguoyun, baidu, aliyun, quark).
    """
    return _http_call("GET", f"/admin/cloud-configs/{drive_type}")


@mcp.tool(name="admin_create_config")
def admin_create_config(
    drive_type: str,
    remote_name: str,
    username: str,
    password: str,
    host_endpoint: Optional[str] = None,
    is_enabled: bool = True,
) -> dict:
    """Create a new cloud drive configuration.

    Args:
        drive_type: Cloud drive type (pikpak, jianguoyun, baidu, aliyun, quark).
        remote_name: rclone remote name.
        username: Cloud drive username.
        password: Cloud drive password (stored encrypted).
        host_endpoint: Custom API endpoint (optional).
        is_enabled: Whether this config is active (default: True).
    """
    body = {
        "drive_type": drive_type,
        "remote_name": remote_name,
        "username": username,
        "password": password,
        "host_endpoint": host_endpoint,
        "is_enabled": is_enabled,
    }
    return _http_call("POST", "/admin/cloud-configs", json_data=body)


@mcp.tool(name="admin_update_config")
def admin_update_config(
    drive_type: str,
    remote_name: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    host_endpoint: Optional[str] = None,
    is_enabled: Optional[bool] = None,
) -> dict:
    """Update an existing cloud drive configuration.

    Args:
        drive_type: Cloud drive type (pikpak, jianguoyun, baidu, aliyun, quark).
        remote_name: rclone remote name (optional).
        username: Cloud drive username (optional).
        password: New password if changing (optional).
        host_endpoint: Custom API endpoint (optional).
        is_enabled: Whether this config is active (optional).
    """
    body = {
        "remote_name": remote_name,
        "username": username,
        "password": password,
        "host_endpoint": host_endpoint,
        "is_enabled": is_enabled,
    }
    body = {k: v for k, v in body.items() if v is not None}
    return _http_call("PUT", f"/admin/cloud-configs/{drive_type}", json_data=body)


@mcp.tool(name="admin_delete_config")
def admin_delete_config(drive_type: str) -> dict:
    """Delete a cloud drive configuration.

    Args:
        drive_type: Cloud drive type (pikpak, jianguoyun, baidu, aliyun, quark).
    """
    return _http_call("DELETE", f"/admin/cloud-configs/{drive_type}")


@mcp.tool(name="admin_apply_config")
def admin_apply_config(drive_type: str) -> dict:
    """Apply (activate) a cloud drive configuration — triggers rclone config.

    Args:
        drive_type: Cloud drive type (pikpak, jianguoyun, baidu, aliyun, quark).
    """
    return _http_call("POST", f"/admin/cloud-configs/{drive_type}/apply")


@mcp.tool(name="health_check")
def health_check() -> dict:
    """Check the health status of the CloudDriveManager service."""
    return _http_call("GET", "/health")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    """Run the MCP server on port 29313."""
    env = os.environ.get("ENV", "prod")
    Config.load(env)
    setup_logger()

    salt = Config.get().encryption.get("salt", "").strip()
    if salt:
        encryption.configure(salt)

    logger.info("Starting CloudDrive MCP server on port 29313 | env=%s", env)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=29313, stateless_http=True)


if __name__ == "__main__":
    main()
