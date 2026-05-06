"""Integration contract tests — verify identical behavior across 3 drive types.

Tests that list_files, list_detail, move, and delete work the same way
for PikPak, JianGuoYun, and BaiduYun using parameterized drive types.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.base import (
    CloudDriveService,
    PikPakCloudDrive,
    JianguoyunCloudDrive,
    BaiduCloudDrive,
)
from src.adapters.rclone_adapter import RcloneAdapter
from src.core.schemas import FileInfoSchema
from src.core.exceptions import ValidationError, FileNotFoundError


DRIVE_TEST_CASES = [
    ("pikpak", PikPakCloudDrive),
    ("jianguoyun", JianguoyunCloudDrive),
    ("baiduyun", BaiduCloudDrive),
]


def _make_adapter():
    return RcloneAdapter(rclone_path="echo", remote_name="test:", timeout=10)


class TestCloudDriveListFiles:
    """list_files contract: same interface across all 3 drive types."""

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_list_files_returns_list_of_file_info_schema(self, drive_name, drive_cls):
        """list_files returns List[FileInfoSchema] regardless of drive type."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        mock_files = [
            FileInfoSchema(name="a.txt", path="/a.txt", size=100, is_dir=False, modified=datetime.now(timezone.utc)),
            FileInfoSchema(name="dir", path="/dir", size=0, is_dir=True, modified=datetime.now(timezone.utc)),
        ]
        with patch.object(adapter, "list_remote", return_value=mock_files):
            result = service.list_files("/")
            assert isinstance(result, list)
            assert all(isinstance(f, FileInfoSchema) for f in result)
            assert len(result) == 2

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_list_files_default_path_is_root(self, drive_name, drive_cls):
        """list_files() defaults to root '/' when no path given."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        with patch.object(adapter, "list_remote", return_value=[]) as mock_list:
            service.list_files()
            mock_list.assert_called_once_with("/")

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_list_files_custom_path(self, drive_name, drive_cls):
        """list_files('/docs') passes '/docs' to the adapter."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        with patch.object(adapter, "list_remote", return_value=[]) as mock_list:
            service.list_files("/docs")
            mock_list.assert_called_once_with("/docs")


class TestCloudDriveListDetail:
    """list_detail contract: same interface across all 3 drive types."""

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_list_detail_returns_list_of_file_info_schema(self, drive_name, drive_cls):
        """list_detail returns List[FileInfoSchema] with full metadata."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        mock_files = [
            FileInfoSchema(name="b.pdf", path="/b.pdf", size=2048, is_dir=False, modified=datetime.now(timezone.utc)),
        ]
        with patch.object(adapter, "list_detail", return_value=mock_files):
            result = service.list_detail("/")
            assert isinstance(result, list)
            assert all(isinstance(f, FileInfoSchema) for f in result)

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_list_detail_rejects_empty_path(self, drive_name, drive_cls):
        """list_detail('') raises ValidationError."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        with pytest.raises(ValidationError):
            service.list_detail("")


class TestCloudDriveDelete:
    """delete contract: same interface across all 3 drive types."""

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_delete_rejects_empty_path(self, drive_name, drive_cls):
        """delete('') raises ValidationError."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        with pytest.raises(ValidationError):
            service.delete("")

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_delete_rejects_root(self, drive_name, drive_cls):
        """delete('/') raises ValidationError."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        with pytest.raises(ValidationError):
            service.delete("/")

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_delete_calls_adapter_delete(self, drive_name, drive_cls):
        """delete('/path') delegates to adapter.delete()."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        with patch.object(adapter, "delete", return_value=True) as mock_del:
            with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
                mock_sm_instance = MagicMock()
                mock_sm_instance._jobs = {}
                mock_sm.return_value = mock_sm_instance

                result = service.delete("/path/to/file.txt")
                assert result is True
                mock_del.assert_called_once_with("/path/to/file.txt")

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_delete_raises_file_not_in_use(self, drive_name, drive_cls):
        """delete raises CloudDriveFileInUseError when file is being synced."""
        from src.core.exceptions import CloudDriveFileInUseError

        adapter = _make_adapter()
        service = drive_cls(adapter)

        mock_job = MagicMock()
        mock_job.source_path = "/busy/file.txt"
        mock_job.job_id = "job-123"
        mock_job.status.value = "running"

        with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
            mock_sm_instance = MagicMock()
            mock_sm_instance._jobs = {"job-123": mock_job}
            mock_sm.return_value = mock_sm_instance

            with pytest.raises(CloudDriveFileInUseError) as exc:
                service.delete("/busy/file.txt")
            assert exc.value.CODE == "FILE_IN_USE"


class TestCloudDriveMove:
    """move contract: same interface across all 3 drive types."""

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_move_rejects_empty_src(self, drive_name, drive_cls):
        """move('', 'dst') raises ValidationError."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        with pytest.raises(ValidationError):
            service.move("", "/dst/file.txt")

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_move_rejects_empty_dst(self, drive_name, drive_cls):
        """move('src', '') raises ValidationError."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        with pytest.raises(ValidationError):
            service.move("/src/file.txt", "")

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_move_calls_adapter_move_with_mkdir(self, drive_name, drive_cls):
        """move delegates to adapter.move_with_mkdir()."""
        adapter = _make_adapter()
        service = drive_cls(adapter)

        with patch.object(adapter, "move_with_mkdir", return_value=True) as mock_move:
            with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
                mock_sm_instance = MagicMock()
                mock_sm_instance._jobs = {}
                mock_sm.return_value = mock_sm_instance

                result = service.move("/src.txt", "/dst.txt")
                assert result is True
                mock_move.assert_called_once_with("/src.txt", "/dst.txt")

    @pytest.mark.parametrize("drive_name,drive_cls", DRIVE_TEST_CASES)
    def test_move_raises_file_not_in_use(self, drive_name, drive_cls):
        """move raises CloudDriveFileInUseError when source is being synced."""
        from src.core.exceptions import CloudDriveFileInUseError

        adapter = _make_adapter()
        service = drive_cls(adapter)

        mock_job = MagicMock()
        mock_job.source_path = "/busy/src.txt"
        mock_job.job_id = "job-456"
        mock_job.status.value = "pending"

        with patch("src.services.sync_manager.get_sync_manager") as mock_sm:
            mock_sm_instance = MagicMock()
            mock_sm_instance._jobs = {"job-456": mock_job}
            mock_sm.return_value = mock_sm_instance

            with pytest.raises(CloudDriveFileInUseError) as exc:
                service.move("/busy/src.txt", "/dst.txt")
            assert exc.value.CODE == "FILE_IN_USE"


class TestCloudDriveCloudDownloadAdd:
    """cloud_download_add contract: PikPak supports it, others raise NotImplementedError."""

    def test_pikpak_supports_cloud_download_add(self):
        """PikPakCloudDrive.cloud_download_add uses rclone backend addurl."""
        mock_job = MagicMock()
        mock_job.task_id = "task-123"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            with patch("src.services.cloud_download_manager.get_cloud_download_manager") as mock_mgr:
                mock_mgr.return_value.create_job.return_value = mock_job
                adapter = _make_adapter()
                service = PikPakCloudDrive(adapter)

                result = service.cloud_download_add(["http://x.com/f.zip"], "/My Pack")

                assert result == "task-123"
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert "backend" in call_args
                assert "addurl" in call_args
                assert any("pikpak" in str(a) for a in call_args)
                assert "http://x.com/f.zip" in call_args

    def test_pikpak_cloud_download_with_folder(self):
        """PikPakCloudDrive.cloud_download_add includes folder in remote path."""
        mock_job = MagicMock()
        mock_job.task_id = "task-456"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            with patch("src.services.cloud_download_manager.get_cloud_download_manager") as mock_mgr:
                mock_mgr.return_value.create_job.return_value = mock_job
                adapter = _make_adapter()
                service = PikPakCloudDrive(adapter)

                result = service.cloud_download_add(["magnet:?xt=urn:btih:abc"], "/movies/2026")

                assert result == "task-456"
                call_args = mock_run.call_args[0][0]
                assert "pikpak:movies/2026" in call_args

    def test_jianguoyun_raises_not_implemented(self):
        """JianguoyunCloudDrive.cloud_download_add raises NotImplementedError."""
        adapter = _make_adapter()
        service = JianguoyunCloudDrive(adapter)

        with pytest.raises(NotImplementedError):
            service.cloud_download_add(["http://x.com/f.zip"], "/My Pack")

    def test_baiduyun_raises_not_implemented(self):
        """BaiduCloudDrive.cloud_download_add raises NotImplementedError."""
        adapter = _make_adapter()
        service = BaiduCloudDrive(adapter)

        with pytest.raises(NotImplementedError):
            service.cloud_download_add(["http://x.com/f.zip"], "/My Pack")
