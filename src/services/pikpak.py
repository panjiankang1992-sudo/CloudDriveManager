"""PikPak-specific service layer — offline download via rclone backend addurl.

This module bridges the CloudDriveService interface with rclone's pikpak: backend.
"""

from __future__ import annotations

from src.core.logger import get_logger
from src.core.config import Config

logger = get_logger("pikpak_service")


def cloud_download_add(urls: list[str], folder: str = "/My Pack") -> str:
    """Create an offline download task on PikPak using rclone backend addurl.

    Args:
        urls: List of HTTP/magnet URLs to download.
        folder: Destination folder on PikPak (e.g. /My Pack or /movies/2026).

    Returns:
        Task ID as string (from rclone output).
    """
    cfg = Config.get()
    adapter = __import__("src.adapters.rclone_adapter", fromlist=["RcloneAdapter"]).RcloneAdapter(
        rclone_path=cfg.rclone_path,
        remote_name="pikpak:",
    )
    return adapter.backend_addurl(folder, urls[0])
