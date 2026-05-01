"""RcloneAdapter — base class for all cloud drive operations via rclone subprocess."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List

from src.core.exceptions import (
    RcloneNotFoundError,
    RcloneExecutionError,
    RcloneTimeoutError,
    FileNotFoundError,
    InvalidPathError,
)
from src.core.logger import get_logger
from src.core.schemas import FileInfoSchema

logger = get_logger("rclone_adapter")


class RcloneAdapter:
    """Wraps rclone CLI calls for a specific remote cloud drive.

    Subclass for each cloud drive (PikPakAdapter, JianGuoYunAdapter, etc.)
    to inherit the base operations: list, detail, delete, move, download.
    """

    def __init__(
        self,
        rclone_path: str,
        remote_name: str,
        timeout: int = 300,
    ):
        """Initialize the adapter.

        Args:
            rclone_path: Path to rclone executable.
            remote_name: Name of the rclone remote (e.g. "mypikpak").
            timeout: Default timeout in seconds for rclone commands.
        """
        self.rclone_path = rclone_path
        self.remote_name = remote_name
        self.timeout = timeout

        # Verify rclone exists
        if not shutil.which(self.rclone_path):
            raise RcloneNotFoundError(
                message=f"rclone executable not found: {self.rclone_path}",
                detail=f"Check 'rclone_path' in the config for '{remote_name}'.",
            )

    # ── Core rclone runner ────────────────────────────────────────────────────

    def run_rclone(
        self,
        args: List[str],
        timeout: Optional[int] = None,
    ) -> str:
        """Run a rclone command and return stdout.

        Args:
            args: rclone command arguments (e.g. ["lsjson", "mypikpak:/"])
            timeout: Override timeout in seconds (default: self.timeout).

        Returns:
            stdout text from rclone.

        Raises:
            RcloneNotFoundError: If rclone executable not found.
            RcloneTimeoutError: If command times out.
            RcloneExecutionError: If rclone exits with non-zero code.
        """
        cmd = [self.rclone_path] + args
        effective_timeout = timeout if timeout is not None else self.timeout

        logger.debug("Running rclone: %s (timeout=%ds)", " ".join(cmd), effective_timeout)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=effective_timeout,
                check=False,
            )
        except FileNotFoundError:
            raise RcloneNotFoundError(
                message=f"rclone executable not found: {self.rclone_path}",
            )
        except subprocess.TimeoutExpired:
            raise RcloneTimeoutError(
                message=f"rclone command timed out after {effective_timeout}s.",
                detail=f"Command: {' '.join(cmd)}",
            )

        if result.returncode != 0:
            logger.warning("rclone error: %s | %s", result.stderr, result.stdout)
            raise RcloneExecutionError(
                message=f"rclone command failed with code {result.returncode}.",
                detail=result.stderr.strip() if result.stderr else None,
            )

        return result.stdout

    # ── File operations ──────────────────────────────────────────────────────

    def list_remote(self, path: str = "/") -> List[FileInfoSchema]:
        """List files at the given path on the remote.

        Args:
            path: Absolute path on the remote (e.g. "/" or "/folder").

        Returns:
            List of FileInfoSchema entries.
        """
        self._validate_path(path)
        remote_path = self._remote_path(path)
        output = self.run_rclone(["lsjson", "--stat", remote_path])
        return self._parse_lsjson(output)

    def list_detail(self, path: str = "/") -> List[FileInfoSchema]:
        """List files with full metadata (ModTime, Hash, MimeType).

        Uses rclone lsjson without --stat flag for full metadata.
        """
        self._validate_path(path)
        remote_path = self._remote_path(path)
        output = self.run_rclone(["lsjson", remote_path])
        return self._parse_lsjson(output)

    def delete(self, path: str) -> bool:
        """Delete a file or directory at the given path.

        Args:
            path: Absolute path on the remote.

        Returns:
            True if deletion succeeded.

        Raises:
            FileNotFoundError: If the path does not exist.
            InvalidPathError: If attempting to delete root "/".
        """
        self._validate_path(path)

        # Guard: forbid deleting root
        if path == "/":
            raise InvalidPathError(
                message="Cannot delete root directory.",
                detail="Deleting '/' is forbidden.",
            )
        remote_path = self._remote_path(path)

        # First check if it exists
        try:
            self.run_rclone(["lsjson", "--max-depth", "1", remote_path], timeout=30)
        except RcloneExecutionError:
            raise FileNotFoundError(
                message=f"Path not found: {path}",
                detail=f"Cannot delete non-existent path on {self.remote_name}.",
            )

        self.run_rclone(["purge", remote_path])
        logger.info("Deleted %s on %s", path, self.remote_name)
        return True

    def move(self, src: str, dst: str) -> bool:
        """Move/rename a file or directory.

        Args:
            src: Source absolute path on the remote.
            dst: Destination absolute path on the remote.

        Returns:
            True if move succeeded.
        """
        self._validate_path(src)
        self._validate_path(dst)
        remote_src = self._remote_path(src)
        remote_dst = self._remote_path(dst)

        self.run_rclone(["moveto", remote_src, remote_dst])
        logger.info("Moved %s -> %s on %s", src, dst, self.remote_name)
        return True

    def download(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the remote to a local path.

        Args:
            remote_path: Source path on the remote.
            local_path: Destination path on the local filesystem.

        Returns:
            True if download succeeded.
        """
        self._validate_path(remote_path)

        # Ensure local directory exists
        local_dest = Path(local_path)
        local_dest.parent.mkdir(parents=True, exist_ok=True)

        remote_src = self._remote_path(remote_path)
        self.run_rclone(["copyto", remote_src, str(local_dest)])
        logger.info("Downloaded %s -> %s", remote_path, local_path)
        return True

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _remote_path(self, path: str) -> str:
        """Build the rclone remote:path string."""
        return f"{self.remote_name}:{path}"

    def _validate_path(self, path: str) -> None:
        """Validate that path is an absolute path starting with /."""
        if not path.startswith("/"):
            raise InvalidPathError(
                message=f"Path must be absolute (start with /): {path}",
                detail=f"Paths on {self.remote_name} must be absolute.",
            )

    def _parse_lsjson(self, output: str) -> List[FileInfoSchema]:
        """Parse rclone lsjson stdout into FileInfoSchema objects.

        Each line is a separate JSON object:
        {"Path":"file.txt","Size":1024,"IsDir":false,...}
        """
        if not output:
            return []

        results: List[FileInfoSchema] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Failed to parse lsjson line: %s", line)
                continue

            results.append(
                FileInfoSchema(
                    name=Path(obj.get("Path", "")).name,
                    path="/" + obj.get("Path", "").lstrip("/"),
                    size=obj.get("Size", 0),
                    is_dir=obj.get("IsDir", False),
                    modified=obj.get("ModTime"),
                    hash=obj.get("Hashes", {}).get("MD5") if isinstance(obj.get("Hashes"), dict) else None,
                    mime_type=obj.get("MimeType"),
                )
            )
        return results
