"""Unit tests for edge cases: root delete, rclone not found, path validation."""

import pytest
from unittest.mock import patch, MagicMock

from src.adapters.rclone_adapter import RcloneAdapter
from src.core.exceptions import (
    InvalidPathError,
    RcloneNotFoundError,
    RcloneExecutionError,
    RcloneTimeoutError,
)


class TestRcloneAdapterRootDelete:
    """Edge case: cannot delete root directory '/'

    Per spec SC-003 edge case: root delete forbidden.
    """

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_delete_root_raises_invalid_path_error(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"
        adapter = RcloneAdapter(rclone_path="rclone", remote_name="test", timeout=300)

        with pytest.raises(InvalidPathError) as exc_info:
            adapter.delete("/")
        assert exc_info.value.CODE == "INVALID_PATH"
        assert "root" in exc_info.value.message.lower() or "/" in exc_info.value.message

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_delete_nested_path_succeeds(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"
        adapter = RcloneAdapter(rclone_path="rclone", remote_name="test", timeout=300)

        # Path validation should pass for non-root
        adapter._validate_path("/folder/file.txt")  # should not raise

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_delete_relative_path_raises(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"
        adapter = RcloneAdapter(rclone_path="rclone", remote_name="test", timeout=300)

        with pytest.raises(InvalidPathError):
            adapter.delete("relative/path")


class TestRcloneNotFoundFastFail:
    """Edge case: rclone not found fast-fails at adapter construction.

    Per quickstart.md: log dir unwritable fallback.
    """

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_rclone_not_found_raises_at_construction(self, mock_which):
        mock_which.return_value = None

        with pytest.raises(RcloneNotFoundError) as exc_info:
            RcloneAdapter(rclone_path="/nonexistent/rclone", remote_name="test", timeout=300)
        assert exc_info.value.CODE == "RCLONE_NOT_FOUND"


class TestRcloneTimeout:
    """Edge case: rclone command timeout handling."""

    @patch("src.adapters.rclone_adapter.shutil.which")
    @patch("src.adapters.rclone_adapter.subprocess.run")
    def test_rclone_timeout_raises(self, mock_run, mock_which):
        import subprocess

        mock_which.return_value = "/usr/bin/rclone"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="rclone", timeout=5)

        adapter = RcloneAdapter(rclone_path="rclone", remote_name="test", timeout=300)

        with pytest.raises(RcloneTimeoutError) as exc_info:
            adapter.run_rclone(["lsjson", "test:/"])
        assert exc_info.value.CODE == "RCLONE_TIMEOUT"


class TestMovePathValidation:
    """Edge case: move with invalid paths."""

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_move_with_relative_source_raises(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"
        adapter = RcloneAdapter(rclone_path="rclone", remote_name="test", timeout=300)

        with pytest.raises(InvalidPathError):
            adapter.move("relative", "/dest")

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_move_with_relative_dest_raises(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"
        adapter = RcloneAdapter(rclone_path="rclone", remote_name="test", timeout=300)

        with pytest.raises(InvalidPathError):
            adapter.move("/src", "relative")


class TestCloudAPIRouterEdgeCases:
    """Edge cases for the cloud API router."""

    def test_unsupported_drive_type_error_has_correct_code(self):
        from src.api.cloud import get_drive_service
        from src.core.exceptions import UnsupportedDriveTypeError

        with pytest.raises(UnsupportedDriveTypeError) as exc_info:
            get_drive_service("unknown", "rclone", "remote", 300)
        assert exc_info.value.CODE == "UNSUPPORTED_DRIVE_TYPE"
