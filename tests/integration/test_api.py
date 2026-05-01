"""Integration smoke tests for CloudDriveManager API."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient

from src.config.config import Config
from main import create_app


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app."""
    Config._instance = None
    Config._env = None
    app = create_app("dev")
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "success"
        assert "data" in data
        assert data["data"]["status"] in ("healthy", "degraded")

    def test_health_has_required_fields(self, client):
        response = client.get("/health")
        data = response.json()["data"]
        assert "status" in data
        assert "version" in data
        assert "env" in data
        assert "rclone_available" in data


class TestCloudDriveEndpoints:
    """Test that all cloud drive endpoints are registered."""

    DRIVES = ["pikpak", "jianguoyun", "baidu", "aliyun", "quark"]

    @pytest.mark.parametrize("drive", DRIVES)
    def test_list_endpoint_registered(self, client, drive):
        response = client.get(f"/cloud/{drive}/list?path=/")
        # Either 200 (success) or 500 (rclone not available) is acceptable
        assert response.status_code in (200, 500)
        # Response should always have code field
        data = response.json()
        assert "code" in data
        assert "message" in data

    @pytest.mark.parametrize("drive", DRIVES)
    def test_detail_endpoint_registered(self, client, drive):
        response = client.get(f"/cloud/{drive}/detail?path=/")
        assert response.status_code in (200, 500)
        data = response.json()
        assert "code" in data

    @pytest.mark.parametrize("drive", DRIVES)
    def test_delete_endpoint_registered(self, client, drive):
        # Without a valid path, expect 422 (validation error) or 500 (rclone error)
        response = client.delete(f"/cloud/{drive}/delete?path=/nonexistent")
        assert response.status_code in (200, 422, 500)
        data = response.json()
        assert "code" in data

    @pytest.mark.parametrize("drive", DRIVES)
    def test_move_endpoint_registered(self, client, drive):
        response = client.post(
            f"/cloud/{drive}/move",
            json={"source_path": "/a", "destination_path": "/b"},
        )
        # Expect 200 (success) or 500 (rclone error)
        assert response.status_code in (200, 500)
        data = response.json()
        assert "code" in data


class TestSyncEndpoint:
    def test_sync_endpoint_registered(self, client):
        response = client.post(
            "/cloud/sync",
            json={
                "source_drive": "pikpak",
                "source_path": "/",
                "destination_drive": "jianguoyun",
                "destination_path": "/",
                "direction": "cloud-to-local",
            },
        )
        # Expect 200 or 500 (rclone not configured or error)
        assert response.status_code in (200, 500)


class TestPikPakOfflineDownload:
    def test_offline_download_returns_501_or_success(self, client):
        response = client.post(
            "/cloud/pikpak/offline-download",
            json={"urls": ["https://example.com/file.zip"], "folder": "/downloads"},
        )
        # 501 = NotImplementedError, 200 = actual implementation
        assert response.status_code in (200, 501)


class TestResponseFormat:
    """Verify all endpoints return consistent APIResponse envelope."""

    def test_error_response_has_code_and_message(self, client):
        """Request with missing required params should return proper error."""
        # Missing required path query param → FastAPI returns 422
        response = client.delete("/cloud/pikpak/delete")
        data = response.json()
        assert response.status_code == 422
        assert "detail" in data
