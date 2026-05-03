"""Unit tests for FILE_IN_USE guard in CloudDriveService.delete() and .move().

Verifies that FR-015 is correctly implemented: attempting to delete or move a file
that is currently being synced raises CloudDriveFileInUseError.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.exceptions import CloudDriveFileInUseError
from src.services.base import (
    CloudDriveService,
    JianguoyunCloudDrive,
    PikPakCloudDrive,
)
from src.adapters.rclone_adapter import RcloneAdapter


class MockSyncJob:
    """Simulates a running sync job for testing."""

    def __init__(self, job_id: str, source_path: str, status: str):
        self.job_id = job_id
        self.source_path = source_path
        self.status = MagicMock()
        self.status.value = status


class TestFileInUseGuard:
    """Test CloudDriveFileInUseError is raised when file is being synced."""

    def _make_service(self, cls=JianguoyunCloudDrive):
        adapter = RcloneAdapter(rclone_path="echo", remote_name="jianguoyun:", timeout=10)
        return cls(adapter)

    def test_delete_free_file_succeeds(self):
        """When no active sync job targets the file, delete proceeds normally."""
        service = self._make_service()

        with patch.object(service._adapter, "delete", return_value=True) as mock_delete:
            with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
                mock_sm_instance = MagicMock()
                mock_sm_instance._jobs = {}
                mock_sm.return_value = mock_sm_instance

                result = service.delete("/path/to/file.txt")
                assert result is True
                mock_delete.assert_called_once_with("/path/to/file.txt")

    def test_delete_file_in_use_raises_error(self):
        """When an active sync job targets the file, delete raises CloudDriveFileInUseError."""
        service = self._make_service()

        with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
            mock_job = MockSyncJob("job-123", "/path/to/file.txt", "running")
            mock_sm_instance = MagicMock()
            mock_sm_instance._jobs = {"job-123": mock_job}
            mock_sm.return_value = mock_sm_instance

            with pytest.raises(CloudDriveFileInUseError) as exc_info:
                service.delete("/path/to/file.txt")

            assert exc_info.value.CODE == "FILE_IN_USE"
            assert "/path/to/file.txt" in exc_info.value.message

    def test_delete_pending_job_also_blocks(self):
        """A pending (not yet running) sync job also blocks delete."""
        service = self._make_service()

        with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
            mock_job = MockSyncJob("job-456", "/data/doc.pdf", "pending")
            mock_sm_instance = MagicMock()
            mock_sm_instance._jobs = {"job-456": mock_job}
            mock_sm.return_value = mock_sm_instance

            with pytest.raises(CloudDriveFileInUseError) as exc_info:
                service.delete("/data/doc.pdf")

            assert exc_info.value.CODE == "FILE_IN_USE"

    def test_delete_completed_job_allows_delete(self):
        """A completed sync job does NOT block delete."""
        service = self._make_service()

        with patch.object(service._adapter, "delete", return_value=True) as mock_delete:
            with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
                mock_job = MockSyncJob("job-789", "/old/file.zip", "completed")
                mock_sm_instance = MagicMock()
                mock_sm_instance._jobs = {"job-789": mock_job}
                mock_sm.return_value = mock_sm_instance

                result = service.delete("/old/file.zip")
                assert result is True
                mock_delete.assert_called_once()

    def test_move_free_file_succeeds(self):
        """When no active sync job targets the source file, move proceeds normally."""
        service = self._make_service()

        with patch.object(service._adapter, "move_with_mkdir", return_value=True) as mock_move:
            with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
                mock_sm_instance = MagicMock()
                mock_sm_instance._jobs = {}
                mock_sm.return_value = mock_sm_instance

                result = service.move("/src/file.txt", "/dst/file.txt")
                assert result is True
                mock_move.assert_called_once()

    def test_move_file_in_use_raises_error(self):
        """When an active sync job targets the source file, move raises CloudDriveFileInUseError."""
        service = self._make_service()

        with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
            mock_job = MockSyncJob("job-abc", "/busy/data.csv", "running")
            mock_sm_instance = MagicMock()
            mock_sm_instance._jobs = {"job-abc": mock_job}
            mock_sm.return_value = mock_sm_instance

            with pytest.raises(CloudDriveFileInUseError) as exc_info:
                service.move("/busy/data.csv", "/archive/data.csv")

            assert exc_info.value.CODE == "FILE_IN_USE"

    def test_pikpak_delete_file_in_use(self):
        """PikPakCloudDrive also raises FILE_IN_USE when file is being synced."""
        adapter = RcloneAdapter(rclone_path="echo", remote_name="pikpak:", timeout=10)
        service = PikPakCloudDrive(adapter)

        with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
            mock_job = MockSyncJob("job-pikpak-1", "/pikpak/file.zip", "running")
            mock_sm_instance = MagicMock()
            mock_sm_instance._jobs = {"job-pikpak-1": mock_job}
            mock_sm.return_value = mock_sm_instance

            with pytest.raises(CloudDriveFileInUseError):
                service.delete("/pikpak/file.zip")

    def test_pikpak_move_file_in_use(self):
        """PikPakCloudDrive also raises FILE_IN_USE when source file is being synced."""
        adapter = RcloneAdapter(rclone_path="echo", remote_name="pikpak:", timeout=10)
        service = PikPakCloudDrive(adapter)

        with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
            mock_job = MockSyncJob("job-pikpak-2", "/pikpak/src.docx", "pending")
            mock_sm_instance = MagicMock()
            mock_sm_instance._jobs = {"job-pikpak-2": mock_job}
            mock_sm.return_value = mock_sm_instance

            with pytest.raises(CloudDriveFileInUseError):
                service.move("/pikpak/src.docx", "/pikpak/dst.docx")
