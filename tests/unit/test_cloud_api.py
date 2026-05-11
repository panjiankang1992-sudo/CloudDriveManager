"""Unit tests for src/api/cloud.py"""

import pytest
from unittest.mock import patch, MagicMock

from src.core.exceptions import (
    UnsupportedDriveTypeError,
    InvalidPathError,
    RcloneNotFoundError,
    FileNotFoundError,
)
from src.api.cloud import SUPPORTED_DRIVES
from src.services.base import (
    PikPakCloudDrive,
    JianguoyunCloudDrive,
    BaiduCloudDrive,
    AliyunCloudDrive,
    QuarkCloudDrive,
    get_drive_service,
)


class TestGetDriveService:
    """Tests for the get_drive_service factory."""

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_pikpak_service_created(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"
        service = get_drive_service("pikpak", "rclone", "mypikpak", 300)
        assert isinstance(service, PikPakCloudDrive)

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_jianguoyun_service_created(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"
        service = get_drive_service("jianguoyun", "rclone", "myjianguoyun", 300)
        assert isinstance(service, JianguoyunCloudDrive)

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_baiduyun_service_created(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"
        service = get_drive_service("baiduyun", "rclone", "mybaiduyun", 300)
        assert isinstance(service, BaiduCloudDrive)

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_aliyun_service_created(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"
        service = get_drive_service("aliyun", "rclone", "myaliyun", 300)
        assert isinstance(service, AliyunCloudDrive)

    @patch("src.adapters.rclone_adapter.shutil.which")
    def test_quark_service_created(self, mock_which):
        mock_which.return_value = "/usr/bin/rclone"
        service = get_drive_service("quark", "rclone", "myquark", 300)
        assert isinstance(service, QuarkCloudDrive)

    def test_unsupported_drive_type_raises(self):
        with pytest.raises(UnsupportedDriveTypeError) as exc_info:
            get_drive_service("unsupported", "rclone", "remote", 300)
        assert exc_info.value.CODE == "UNSUPPORTED_DRIVE_TYPE"

    def test_case_insensitive(self):
        with pytest.raises(UnsupportedDriveTypeError):
            get_drive_service("PIKKAK", "rclone", "remote", 300)


class TestSupportedDrives:
    def test_all_five_drives_supported(self):
        expected = {"pikpak", "jianguoyun", "baiduyun", "aliyun", "quark"}
        assert SUPPORTED_DRIVES == expected
