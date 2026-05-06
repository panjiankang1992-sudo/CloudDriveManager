"""PikPak HTTP API client — direct httpx implementation for offline download.

Features:
- Sign in with username/password
- Create offline download tasks
- Rate limiting with exponential backoff (1s → 2s → 4s … 60s max)

Required config:
    pikpak.username, pikpak.password (in config.yaml)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from src.core.config import Config
from src.core.logger import get_logger
from src.core.exceptions import OfflineDownloadError, OfflineDownloadTimeoutError

logger = get_logger("pikpak_client")

# Rate limit constants
_INITIAL_DELAY = 1.0
_MAX_DELAY = 60.0
_MULTIPLIER = 2.0

# PikPak API endpoints
_PIKPAK_API_BASE = "https://api.pikpak.com"
_AUTH_URL = f"{_PIKPAK_API_BASE}/v1/auth/authentication"
_OFFLINE_DOWNLOAD_URL = f"{_PIKPAK_API_BASE}/v1/offline/download"
_OFFLINE_LIST_URL = f"{_PIKPAK_API_BASE}/v1/offline/list"


class PikPakClient:
    """Async PikPak API client with rate limiting and retry logic."""

    def __init__(self, username: str | None = None, password: str | None = None):
        cfg = Config.get()
        self._username = username or cfg.get_value("pikpak.username", "")
        self._password = password or cfg.get_value("pikpak.password", "")
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        return self._client

    async def _ensure_auth(self) -> str:
        """Ensure we have a valid access token, refreshing if needed."""
        if self._access_token:
            return self._access_token

        await self._do_login()
        return self._access_token or ""

    async def _do_login(self) -> None:
        """Perform login to get access/refresh tokens."""
        client = await self._get_client()

        payload = {
            "username": self._username,
            "password": self._password,
        }

        try:
            response = await client.post(_AUTH_URL, json=payload)
            response.raise_for_status()
            data = response.json()

            self._access_token = data.get("access_token", "")
            self._refresh_token = data.get("refresh_token", "")
            logger.info("PikPak client signed in successfully")
        except httpx.HTTPError as e:
            raise OfflineDownloadError(
                message=f"PikPak login failed: {e}",
            ) from e

    async def _retry_with_backoff(
        self,
        coro,
        operation: str = "operation",
        max_retries: int = 5,
    ) -> Any:
        """Execute an async coroutine with exponential backoff rate limiting."""
        delay = _INITIAL_DELAY
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                return await coro
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if any(kw in error_str for kw in ["rate", "limit", "429", "too many", "throttle"]):
                    logger.warning(
                        f"PikPak rate limited ({operation}), attempt {attempt + 1}/{max_retries}, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * _MULTIPLIER, _MAX_DELAY)
                    continue
                else:
                    raise OfflineDownloadError(
                        message=f"PikPak {operation} failed: {e}",
                    ) from e

        raise OfflineDownloadTimeoutError(
            message=f"PikPak {operation} failed after {max_retries} retries",
            detail=str(last_error) if last_error else None,
        )

    async def signin(self) -> tuple[str, str]:
        """Sign in to PikPak and return (access_token, refresh_token)."""
        await self._ensure_auth()
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
        access_token = await self._ensure_auth()
        client = await self._get_client()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async def _create() -> Any:
            payload = {
                "url": urls[0],
            }
            response = await client.post(
                _OFFLINE_DOWNLOAD_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

        result = await self._retry_with_backoff(_create(), "offline_download")
        task_id = self._extract_task_id(result)
        logger.info(f"Offline download task created: {task_id} ({len(urls)} URLs -> {folder})")
        return task_id

    async def get_offline_task_status(self, task_id: str) -> dict[str, Any]:
        """Get status of an offline download task."""
        access_token = await self._ensure_auth()
        client = await self._get_client()

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        async def _list() -> Any:
            response = await client.get(
                _OFFLINE_LIST_URL,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

        result = await self._retry_with_backoff(_list(), "offline_list")
        tasks = result.get("tasks", [])
        for task in tasks:
            if task.get("id") == task_id or task.get("task_id") == task_id:
                return task
        return {"id": task_id, "status": "unknown", "error": "Task not found"}

    def _extract_task_id(self, result: Any) -> str:
        """Extract task ID from PikPak API response."""
        if isinstance(result, dict):
            return str(result.get("task_id", result.get("id", "")))
        if isinstance(result, str):
            return result
        return str(result)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# ── Module-level singleton ────────────────────────────────────────────────────

_client: PikPakClient | None = None


def get_pikpak_client() -> PikPakClient:
    """Get or create the PikPak client singleton."""
    global _client
    if _client is None:
        _client = PikPakClient()
    return _client
