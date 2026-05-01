"""PikPak HTTP API client — wraps pikpakapi library for offline download.

Features:
- Sign in with username/password
- Create offline download tasks
- Rate limiting with exponential backoff (1s → 2s → 4s … 60s max)

Required env / config:
    PIKPAK_USERNAME, PIKPAK_PASSWORD (or in config.yaml)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pikpakapi import PikPakApi

from src.core.config import Config
from src.core.logger import get_logger
from src.core.exceptions import OfflineDownloadError, OfflineDownloadTimeoutError

logger = get_logger("pikpak_api")

# Rate limit constants
_INITIAL_DELAY = 1.0  # seconds
_MAX_DELAY = 60.0  # seconds
_MULTIPLIER = 2.0


class PikPakClient:
    """Async PikPak API client with rate limiting and retry logic."""

    def __init__(self, username: str | None = None, password: str | None = None):
        cfg = Config.get()
        self._username = username or cfg.get("pikpak.username", "")
        self._password = password or cfg.get("pikpak.password", "")
        self._client: PikPakApi | None = None
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    async def _ensure_client(self) -> PikPakApi:
        """Lazily create and sign in the PikPakApi client."""
        if self._client is None:
            self._client = PikPakApi(
                username=self._username,
                password=self._password,
            )
            await self._client.login()  # type: ignore[reportOptionalMemberAccess]
            self._access_token = getattr(self._client, "access_token", None)  # type: ignore[reportOptionalMemberAccess]
            self._refresh_token = getattr(self._client, "refresh_token", None)  # type: ignore[reportOptionalMemberAccess]
            logger.info("PikPak client signed in successfully")
        return self._client  # type: ignore[return-value]

    async def _retry_with_backoff(
        self,
        coro,
        operation: str = "operation",
        max_retries: int = 5,
    ) -> Any:
        """Execute an async coroutine with exponential backoff rate limiting.

        Args:
            coro: coroutine to execute
            operation: name for log messages
            max_retries: maximum retry attempts

        Returns:
            Result of the coroutine

        Raises:
            OfflineDownloadError: after all retries exhausted
            OfflineDownloadTimeoutError: if pikpak rate limits permanently
        """
        delay = _INITIAL_DELAY
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                return await coro
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if rate limited (common indicators)
                if any(kw in error_str for kw in ["rate", "limit", "429", "too many", "throttle"]):
                    logger.warning(
                        f"PikPak rate limited ({operation}), attempt {attempt + 1}/{max_retries}, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * _MULTIPLIER, _MAX_DELAY)
                    continue
                else:
                    # Non-rate-limit error, don't retry
                    raise OfflineDownloadError(
                        message=f"PikPak {operation} failed: {e}",
                    ) from e

        raise OfflineDownloadTimeoutError(
            message=f"PikPak {operation} failed after {max_retries} retries",
            detail=str(last_error) if last_error else None,
        )

    async def signin(self) -> tuple[str, str]:
        """Sign in to PikPak and return (access_token, refresh_token).

        Returns:
            Tuple of (access_token, refresh_token)
        """
        client = await self._ensure_client()
        return self._access_token or "", self._refresh_token or ""

    async def create_offline_download(
        self,
        urls: list[str],
        folder: str = "/My Pack",
    ) -> str:
        """Create an offline download task.

        Args:
            urls: List of HTTP or magnet URLs to download.
            folder: Destination folder on PikPak (default: /My Pack).

        Returns:
            Task ID as string.

        Raises:
            OfflineDownloadError: if task creation fails
            OfflineDownloadTimeoutError: if permanently rate limited
        """
        client = await self._ensure_client()

        async def _create() -> Any:
            return await client.offline_download(
                urls=urls,
                folder=folder,
            )

        result = await self._retry_with_backoff(_create(), "offline_download")

        # Extract task ID from result
        task_id = self._extract_task_id(result)
        logger.info(f"Offline download task created: {task_id} ({len(urls)} URLs -> {folder})")
        return task_id

    async def get_offline_task_status(self, task_id: str) -> dict[str, Any]:
        """Get status of an offline download task.

        Args:
            task_id: The task ID returned from create_offline_download.

        Returns:
            Dict with task status information.
        """
        client = await self._ensure_client()

        async def _list() -> Any:
            return await client.offline_list()

        all_tasks = await self._retry_with_backoff(_list(), "offline_list")
        for task in all_tasks:
            if task.get("id") == task_id or task.get("task_id") == task_id:
                return task
        return {"id": task_id, "status": "unknown", "error": "Task not found"}

    # ── Internal ───────────────────────────────────────────────────────────

    def _extract_task_id(self, result: Any) -> str:
        """Extract task ID from pikpakapi response."""
        if isinstance(result, dict):
            return str(result.get("task_id", result.get("id", "")))
        if isinstance(result, str):
            return result
        if hasattr(result, "task_id"):
            return str(result.task_id)
        if hasattr(result, "id"):
            return str(result.id)
        return str(result)


# ── Module-level singleton ────────────────────────────────────────────────────

_client: PikPakClient | None = None


def get_pikpak_client() -> PikPakClient:
    """Get or create the PikPak client singleton."""
    global _client
    if _client is None:
        _client = PikPakClient()
    return _client
