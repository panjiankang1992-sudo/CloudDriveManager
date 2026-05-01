"""PikPak-specific service layer — implements offline download via pikpak_api.py.

This module bridges the CloudDriveService interface with the PikPak HTTP API.
All methods here are async (sync wrapper is handled by the API layer).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from src.core.logger import get_logger

if TYPE_CHECKING:
    from src.services.pikpak_api import PikPakClient

logger = get_logger("pikpak_service")


def _get_pikpak_client() -> "PikPakClient":  # type: ignore[reportMissingImports]
    """Deferred import to avoid circular dependency."""
    from src.services import pikpak_api as _api_module

    return _api_module.get_pikpak_client()  # type: ignore[reportAttributeAccessIssue]


def _run_async(coro) -> str:
    """Run an async coroutine in a synchronous context.

    Creates a new event loop per call (not thread-safe for high concurrency,
    but suitable for the PikPak offline download use case).
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new loop in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists
        return asyncio.run(coro)


def cloud_download_add(urls: list[str], folder: str = "/My Pack") -> str:
    """Create an offline download task on PikPak (synchronous entry point).

    Args:
        urls: List of HTTP/magnet URLs to download.
        folder: Destination folder on PikPak.

    Returns:
        Task ID as string.

    Raises:
        OfflineDownloadError: on failure
        OfflineDownloadTimeoutError: on rate limit timeout
    """
    client = _get_pikpak_client()
    return _run_async(client.create_offline_download(urls, folder))
