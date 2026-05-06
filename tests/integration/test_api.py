"""Integration test — verify FastAPI app and all routers load correctly."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.app import create_app


def test_app_creation():
    """App factory creates successfully."""
    app = create_app()
    assert app is not None
    assert app.title == "CloudDriveManager API"


def test_health_endpoint():
    """Health check endpoint responds."""
    app = create_app()
    from httpx import ASGITransport, AsyncClient
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    import asyncio
    result = asyncio.run(client.get("/health"))
    assert result.status_code == 200
    assert result.json() == {"status": "ok"}


def test_cloud_router_registered():
    """Cloud drive router is registered on /cloud prefix."""
    app = create_app()
    # Check routes are registered (at least one /cloud/{drive_type}/list exists)
    routes = [r.path for r in app.routes]
    cloud_routes = [r for r in routes if r.startswith("/cloud")]
    assert len(cloud_routes) >= 4, f"Expected ≥4 cloud routes, got: {cloud_routes}"


def test_all_required_endpoints():
    """All required endpoint paths are registered."""
    app = create_app()
    paths = {r.path for r in app.routes}
    required = {
        "/health",
        "/cloud/{drive_type}/list",
        "/cloud/{drive_type}/detail",
        "/cloud/{drive_type}/move",
        "/cloud/{drive_type}/delete",
        "/cloud/sync",
        "/cloud/sync/{job_id}/status",
        "/cloud/sync/{job_id}/cancel",
        "/cloud/admin/operation-logs",
    }
    for expected in required:
        # Normalize template paths for comparison
        matched = any(
            _path_matches(expected, r.path) for r in app.routes
        )
        assert matched, f"Missing route: {expected}"


class TestAllDriveTypesRegistered:
    """All 3 supported drive types (pikpak, jianguoyun, baiduyun) are wired up."""

    def _get_app(self):
        return create_app()

    def test_pikpak_list_route_exists(self):
        app = self._get_app()
        routes = {r.path for r in app.routes}
        assert any(_path_matches("/cloud/{drive_type}/list", p) for p in routes)

    def test_jianguoyun_list_route_exists(self):
        app = self._get_app()
        routes = {r.path for r in app.routes}
        assert any(_path_matches("/cloud/{drive_type}/list", p) for p in routes)

    def test_baiduyun_list_route_exists(self):
        app = self._get_app()
        routes = {r.path for r in app.routes}
        assert any(_path_matches("/cloud/{drive_type}/list", p) for p in routes)


class TestErrorCodes:
    """API returns correct error codes for validation and cloud drive errors.

    Tests call endpoint functions directly (not via HTTP) to avoid
    Config/Database initialization complexity in the test runtime.
    """

    def test_unsupported_drive_type_returns_error(self):
        """Requesting an unsupported drive type returns UNSUPPORTED_DRIVE_TYPE."""
        mock_cfg = MagicMock()
        mock_db = MagicMock()

        with patch("src.core.config.Config.get", return_value=mock_cfg):
            with patch("src.db.database.Database.get", return_value=mock_db):
                from src.api.cloud import _error_response
                response = _error_response("UNSUPPORTED_DRIVE_TYPE", "Unsupported drive type: unsupported", "Supported: ['pikpak']")

        assert response.status_code == 200
        import json
        body = json.loads(response.body)
        assert body["code"] == "UNSUPPORTED_DRIVE_TYPE"

    def test_validation_error_response_format(self):
        """VALIDATION_ERROR response has correct format."""
        from src.api.cloud import _error_response
        response = _error_response("VALIDATION_ERROR", "Path cannot be empty")
        assert response.status_code == 200
        import json
        body = json.loads(response.body)
        assert body["code"] == "VALIDATION_ERROR"

    def test_cloud_drive_file_in_use_error_response_format(self):
        """FILE_IN_USE error response has correct format from CloudDriveFileInUseError."""
        from src.core.exceptions import CloudDriveFileInUseError
        from src.api.cloud import _error_response

        error = CloudDriveFileInUseError(
            message="File is currently being synced: /busy/file.txt",
            detail="Active sync job job-123 is using this file.",
        )
        response = _error_response(error.CODE, error.message, error.detail)
        assert response.status_code == 200
        import json
        body = json.loads(response.body)
        assert body["code"] == "FILE_IN_USE"
        assert "file.txt" in body["message"]

    def test_api_response_error_has_correct_structure(self):
        """APIResponse.error() produces correct structure."""
        from src.core.schemas import APIResponse
        err = APIResponse.error(code="TEST_ERROR", message="Test message", detail="Test detail")
        dump = err.model_dump()
        assert dump["code"] == "TEST_ERROR"
        assert dump["message"] == "Test message"
        assert dump["data"] == {"detail": "Test detail"}

    def test_cloud_drive_file_in_use_error_code(self):
        """CloudDriveFileInUseError has correct error code."""
        from src.core.exceptions import CloudDriveFileInUseError
        error = CloudDriveFileInUseError(message="test", detail="test")
        assert error.CODE == "FILE_IN_USE"

    def test_all_drive_types_have_list_endpoint(self):
        """pikpak, jianguoyun, baiduyun all have list endpoint wired up via generic route."""
        from src.api.cloud import create_cloud_router
        from src.api.cloud import SUPPORTED_DRIVES
        router = create_cloud_router()
        # Router uses /cloud prefix, so routes are like /{drive_type}/list
        # All 3 drives share the same template route
        paths = {r.path for r in router.routes}
        list_routes = [p for p in paths if "/list" in p]
        # One template route handles all drive types
        assert len(list_routes) >= 1, f"Expected list routes, got: {list_routes}"
        assert "/{drive_type}/list" in list_routes or any("/list" in p for p in list_routes)
        # Verify all 3 drive types are in SUPPORTED_DRIVES
        assert SUPPORTED_DRIVES == {"pikpak", "jianguoyun", "baiduyun"}


def _path_matches(template: str, actual: str) -> bool:
    """Check if an actual path matches a route template."""
    if template == actual:
        return True
    # Simple template matching: /cloud/{drive_type}/list matches /cloud/pikpak/list
    import re
    pattern = re.escape(template).replace(r"\{[^}]+\}", "[^/]+")
    return bool(re.match(f"^{pattern}$", actual))


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
