"""Unit tests for src/db/repository.py"""

import pytest
from unittest.mock import MagicMock, patch

from src.db.schemas import CloudDriveConfigCreate, CloudDriveConfigUpdate
from src.db.repository import CloudDriveConfigRepository


class TestCloudDriveConfigRepository:
    """Tests for CloudDriveConfigRepository CRUD operations."""

    def _make_conn_mgr(self, rows=None):
        """Build a mock connection manager."""
        mock_conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = rows or []
        cursor.fetchone.return_value = rows[0] if rows else None
        cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.commit = MagicMock()
        mock_conn.rollback = MagicMock()

        class FakeConnMgr:
            def __init__(self, c):
                self._conn = c
            def cursor(self):
                return self._conn.cursor()
            def commit(self):
                self._conn.commit()
            def rollback(self):
                self._conn.rollback()

        return FakeConnMgr(mock_conn)

    def _make_repo(self, rows=None):
        return CloudDriveConfigRepository(self._make_conn_mgr(rows))

    @patch("src.db.repository.enc")
    def test_list_all_returns_responses(self, mock_enc):
        rows = [
            {
                "drive_type": "pikpak",
                "remote_name": "mypikpak",
                "drive_type_variant": "pikpak",
                "host_endpoint": None,
                "username": "user@test.com",
                "encrypted_password": "encrypted_value",
                "is_enabled": True,
                "created_at": None,
                "updated_at": None,
            }
        ]
        repo = self._make_repo(rows)
        results = repo.list_all()
        assert len(results) == 1
        assert results[0].drive_type == "pikpak"
        assert results[0].password_set is True

    @patch("src.db.repository.enc")
    def test_get_by_drive_type_returns_config(self, mock_enc):
        rows = [
            {
                "drive_type": "pikpak",
                "remote_name": "mypikpak",
                "drive_type_variant": "pikpak",
                "host_endpoint": None,
                "username": "user@test.com",
                "encrypted_password": None,
                "is_enabled": True,
                "created_at": None,
                "updated_at": None,
            }
        ]
        repo = self._make_repo(rows)
        result = repo.get_by_drive_type("pikpak")
        assert result is not None
        assert result.drive_type == "pikpak"
        assert result.password_set is False

    @patch("src.db.repository.enc")
    def test_get_by_drive_type_not_found(self, mock_enc):
        repo = self._make_repo([])
        result = repo.get_by_drive_type("nonexistent")
        assert result is None

    @patch("src.db.repository.enc")
    def test_delete_returns_true_when_deleted(self, mock_enc):
        repo = self._make_repo([])
        deleted = repo.delete("pikpak")
        assert deleted is True

    @patch("src.db.repository.enc")
    def test_row_to_response_never_exposes_password(self, mock_enc):
        row = {
            "drive_type": "pikpak",
            "remote_name": "mypikpak",
            "drive_type_variant": "pikpak",
            "host_endpoint": "https://api.pikpak.com",
            "username": "user@test.com",
            "encrypted_password": "something_encrypted",
            "is_enabled": True,
            "created_at": None,
            "updated_at": None,
        }
        repo = self._make_repo([row])
        response = repo._row_to_response(row)
        assert not hasattr(response, "password") or getattr(response, "password", "NOTFOUND") == "NOTFOUND"
        assert response.password_set is True
