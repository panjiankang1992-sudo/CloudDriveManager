"""Rclone CLI adapter — wraps rclone commands for cloud drive operations.

Supports: list, list_detail, delete, moveto, copy, mkdir
Progress parsing for rclone copy --progress: "Transferred: 1.234 GiB / 10.382 GiB, 13%, ..."
"""

from __future__ import annotations

import json
import posixpath
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

from src.core.config import Config
from src.core.exceptions import (
    RcloneExecutionError,
    RcloneNotFoundError,
    RcloneTimeoutError,
)
from src.core.logger import get_logger
from src.core.schemas import FileInfoSchema

logger = get_logger("rclone_adapter")

# Progress line regex from rclone copy --progress
PROGRESS_RE = re.compile(
    r"Transferred:\s+([\d.]+ [KMGT]iB)\s+/\s+([\d.]+ [KMGT]iB),\s+(\d+)%"
)


def _parse_size(size_str: str) -> int:
    """Parse rclone size string like '1.234 GiB' into bytes."""
    size_str = size_str.strip()
    try:
        number, unit = size_str.split()
        number = float(number)
        multipliers = {
            "B": 1,
            "KB": 1024,
            "MB": 1024**2,
            "GB": 1024**3,
            "TB": 1024**4,
            "KiB": 1024,
            "MiB": 1024**2,
            "GiB": 1024**3,
            "TiB": 1024**4,
        }
        return int(number * multipliers.get(unit, 1))
    except (ValueError, KeyError):
        return 0


class RcloneAdapter:
    """Thread-safe rclone CLI wrapper for a single remote."""

    def __init__(
        self,
        rclone_path: str = "rclone",
        remote_name: str = "",
        timeout: int = 300,
    ):
        self.rclone_path = rclone_path
        self.remote_name = remote_name  # e.g. "pikpak:"
        self.timeout = timeout

    def _remote(self, path: str = "") -> str:
        """Build full remote:path string."""
        return f"{self.remote_name}{path}"

    def _run(
        self,
        *args: str,
        check: bool = True,
        capture_stdout: bool = True,
        timeout: int | None = None,
    ) -> str:
        """Execute rclone command and return stdout.

        Args:
            *args: rclone subcommand and arguments (e.g., "lsjson", "/")
            check: Raise on non-zero exit
            capture_stdout: Return stdout text
            timeout: Override default timeout

        Returns:
            stdout text (empty if not capturing)

        Raises:
            RcloneNotFoundError: rclone not in PATH
            RcloneExecutionError: command failed
            RcloneTimeoutError: timed out
        """
        cmd = [self.rclone_path, *args]
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_stdout,
                text=True,
                timeout=timeout or self.timeout,
                check=False,
            )
        except FileNotFoundError:
            raise RcloneNotFoundError(f"rclone not found at: {self.rclone_path}")
        except subprocess.TimeoutExpired:
            raise RcloneTimeoutError(f"rclone command timed out after {timeout or self.timeout}s")

        if check and result.returncode != 0:
            logger.error(f"rclone failed: {result.stderr}")
            raise RcloneExecutionError(
                message=f"rclone {args[0]} failed with code {result.returncode}",
                detail=result.stderr.strip()[:200],
            )

        return result.stdout if capture_stdout else ""

    # ── File listing ──────────────────────────────────────────────────────────

    def list_remote(self, path: str = "/") -> list[FileInfoSchema]:
        """List files at path (lightweight, no metadata).

        Returns:
            List of FileInfoSchema (IsDir, Remote, Name, EncryptedFileMetadata only)
        """
        output = self._run("lsjson", self._remote(path))
        if not output.strip():
            return []

        items = json.loads(output)
        return [
            FileInfoSchema(
                name=item["Name"],
                path=f"/{item['Name']}" if path == "/" else f"{path}/{item['Name']}",
                size=item.get("Size", 0),
                is_dir=item["IsDir"],
                modified=item.get("ModTime", "1970-01-01T00:00:00Z"),
                mime_type=None,
            )
            for item in items
        ]

    def list_detail(self, path: str = "/") -> list[FileInfoSchema]:
        """List files with full metadata (hash, mime-type)."""
        output = self._run("lsjson", "--full", self._remote(path))
        if not output.strip():
            return []

        items = json.loads(output)
        return [
            FileInfoSchema(
                name=item["Name"],
                path=f"/{item['Name']}" if path == "/" else f"{path}/{item['Name']}",
                size=item.get("Size", 0),
                is_dir=item["IsDir"],
                modified=item.get("ModTime", "1970-01-01T00:00:00Z"),
                mime_type=item.get("MimeType"),
            )
            for item in items
        ]

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, path: str) -> bool:
        """Delete file or directory at path."""
        self._run("purge", self._remote(path))
        return True

    # ── Move (with auto-mkdir) ───────────────────────────────────────────────

    def moveto(self, src: str, dst: str) -> bool:
        """Move/rename file or directory.

        Creates destination parent directory if it doesn't exist (FR-003).
        """
        # Parse destination parent directory
        dst_dir = posixpath.dirname(dst)
        dst_name = posixpath.basename(dst)

        # Ensure destination parent exists
        if dst_dir and dst_dir != "/":
            self.mkdir(self._remote(dst_dir))

        self._run("moveto", self._remote(src), self._remote(dst))
        return True

    def mkdir(self, remote_path: str) -> bool:
        """Create directory on remote (no-op if already exists)."""
        self._run("mkdir", remote_path, check=False)
        return True

    def move_with_mkdir(self, src: str, dst: str) -> bool:
        """Move with automatic destination parent directory creation.

        This is the FR-003 implementation: moveto won't create parent dirs,
        so we do it first.
        """
        # Parse destination parent directory
        dst_dir = posixpath.dirname(dst)
        # dst_name = posixpath.basename(dst)  # not needed directly

        # Ensure destination parent exists
        if dst_dir and dst_dir != "/":
            self.mkdir(self._remote(dst_dir))

        self._run("moveto", self._remote(src), self._remote(dst))
        return True

    # ── Copy / Download ──────────────────────────────────────────────────────

    def copy(self, remote_path: str, local_path: str) -> bool:
        """Copy remote file to local path (synchronous)."""
        local_path = str(Path(local_path).expanduser().resolve())
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        self._run("copyto", self._remote(remote_path), local_path)
        return True

    def copy_with_progress(
        self,
        remote_path: str,
        local_path: str,
        cancel_event: threading.Event | None = None,
        progress_callback: Callable[[int, int, int], None] | None = None,
    ) -> bool:
        """Copy remote file to local with progress tracking.

        Args:
            remote_path: Source path on remote
            local_path: Destination local path
            cancel_event: Threading event to signal cancellation
            progress_callback: Called with (bytes_done, total_bytes, percent) on each progress update

        Returns:
            True if completed, False if cancelled
        """
        local_path = str(Path(local_path).expanduser().resolve())
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        cmd = [self.rclone_path, "copy", "--progress", self._remote(remote_path), local_path]
        logger.info(f"Starting copy: {' '.join(cmd)}")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        total_bytes = 0
        bytes_done = 0

        def read_stdout():
            nonlocal bytes_done, total_bytes
            for line in iter(proc.stdout or []):
                if cancel_event and cancel_event.is_set():
                    proc.terminate()
                    time.sleep(2)
                    if proc.poll() is None:
                        proc.kill()
                    logger.warning("Copy cancelled by user")
                    return

                m = PROGRESS_RE.search(line)
                if m:
                    bytes_done = _parse_size(m.group(1))
                    total_bytes = _parse_size(m.group(2))
                    percent = int(m.group(3))
                    if progress_callback:
                        progress_callback(bytes_done, total_bytes, percent)

        t = threading.Thread(target=read_stdout, daemon=True)
        t.start()
        proc.wait()
        t.join(timeout=5)

        if proc.returncode != 0:
            raise RcloneExecutionError(f"rclone copy failed with code {proc.returncode}")

        return True

    # ── Utility ──────────────────────────────────────────────────────────────

    def remote_exists(self, path: str) -> bool:
        """Check if a remote path exists."""
        try:
            self._run("lsjson", "--files-only", "--max-depth", "1", self._remote(path), check=False)
            return True
        except RcloneExecutionError:
            return False

    def close(self) -> None:
        """Close adapter (no-op for subprocess-based adapter)."""
        pass


# ── Progress parser ────────────────────────────────────────────────────────────

def parse_progress_line(line: str) -> tuple[int, int, int] | None:
    """Parse rclone progress output line.

    Returns:
        (bytes_done, total_bytes, percent) or None if not a progress line
    """
    m = PROGRESS_RE.search(line)
    if not m:
        return None
    return _parse_size(m.group(1)), _parse_size(m.group(2)), int(m.group(3))