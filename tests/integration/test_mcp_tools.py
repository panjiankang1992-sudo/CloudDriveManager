"""Integration contract tests — verify MCP tools produce identical schemas to HTTP API endpoints.

T020: Verifies MCP tools mirror the HTTP API response schemas for pikpak_list_files
and pikpak_offline_download.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.schemas import FileInfoSchema


class TestMCPListFilesContract:
    """MCP pikpak_list_files response schema must match HTTP /cloud/pikpak/list."""

    def test_mcp_returns_same_fields_as_file_info_schema_list(self):
        """MCP pikpak_list_files returns {path, files: [FileInfoSchema fields]}."""
        mock_files = [
            FileInfoSchema(
                name="report.pdf",
                path="/docs/report.pdf",
                size=4096,
                is_dir=False,
                modified=datetime.now(timezone.utc),
                mime_type="application/pdf",
                hash="abc123",
            ),
        ]

        with patch("src.services.base.get_drive_service") as mock_drive:
            mock_service = MagicMock()
            mock_service.list_files.return_value = mock_files
            mock_drive.return_value = mock_service

            # Force reimport to pick up patch
            import importlib
            import src.mcp.server
            importlib.reload(src.mcp.server)
            from src.mcp.server import pikpak_list_files

            result = pikpak_list_files("/docs")

            assert "path" in result
            assert "files" in result
            assert result["path"] == "/docs"
            assert len(result["files"]) == 1

            f = result["files"][0]
            assert f["name"] == "report.pdf"
            assert f["path"] == "/docs/report.pdf"
            assert f["size"] == 4096
            assert f["is_dir"] is False
            assert "modified" in f
            assert f["mime_type"] == "application/pdf"
            assert f["hash"] == "abc123"

    def test_mcp_list_files_default_path(self):
        """MCP pikpak_list_files() defaults to '/' when no path given."""
        mock_service = MagicMock()
        mock_service.list_files.return_value = []

        with patch("src.services.base.get_drive_service", return_value=mock_service):
            import importlib
            import src.mcp.server
            importlib.reload(src.mcp.server)
            from src.mcp.server import pikpak_list_files

            result = pikpak_list_files()

            mock_service.list_files.assert_called_once_with("/")
            assert result["path"] == "/"


class TestMCPOfflineDownloadContract:
    """MCP pikpak_offline_download response schema must match OfflineDownloadResponseData."""

    def test_mcp_offline_download_returns_task_id_urls_count_folder(self):
        """MCP pikpak_offline_download returns {task_id, urls_count, destination_folder}."""
        mock_job = MagicMock()
        mock_job.task_id = "local-uuid-123"

        mock_mgr = MagicMock()
        mock_mgr.create_job.return_value = mock_job

        with patch("src.services.cloud_download_manager.get_cloud_download_manager", return_value=mock_mgr):
            with patch("src.services.pikpak.cloud_download_add", return_value="pikpak-task-456"):
                import importlib
                import src.mcp.server
                importlib.reload(src.mcp.server)
                from src.mcp.server import pikpak_offline_download

                result = pikpak_offline_download(
                    urls=["https://example.com/file.zip", "magnet:?xt=urn:btih:xyz"],
                    folder="/My Pack",
                )

                assert "task_id" in result
                assert "urls_count" in result
                assert "destination_folder" in result
                assert result["task_id"] == "pikpak-task-456"
                assert result["urls_count"] == 2
                assert result["destination_folder"] == "/My Pack"


class TestMCPOtherDrives:
    """MCP jianguoyun_list_files and baidu_list_files return same shape as pikpak."""

    def test_jianguoyun_list_files_returns_same_structure(self):
        """jianguoyun_list_files returns {path, files: [...]} same as pikpak."""
        mock_files = [
            FileInfoSchema(
                name="data.csv",
                path="/data.csv",
                size=1024,
                is_dir=False,
                modified=datetime.now(timezone.utc),
            ),
        ]

        mock_service = MagicMock()
        mock_service.list_files.return_value = mock_files

        with patch("src.services.base.get_drive_service", return_value=mock_service):
            import importlib
            import src.mcp.server
            importlib.reload(src.mcp.server)
            from src.mcp.server import jianguoyun_list_files

            result = jianguoyun_list_files("/")

            assert "path" in result
            assert "files" in result
            assert len(result["files"]) == 1
            assert result["files"][0]["name"] == "data.csv"

    def test_baidu_list_files_returns_same_structure(self):
        """baidu_list_files returns {path, files: [...]} same as pikpak."""
        mock_files: list = []

        mock_service = MagicMock()
        mock_service.list_files.return_value = mock_files

        with patch("src.services.base.get_drive_service", return_value=mock_service):
            import importlib
            import src.mcp.server
            importlib.reload(src.mcp.server)
            from src.mcp.server import baidu_list_files

            result = baidu_list_files("/storage")

            assert "path" in result
            assert "files" in result
            assert result["path"] == "/storage"
