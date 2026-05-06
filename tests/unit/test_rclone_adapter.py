"""Unit tests for src.adapters.rclone_adapter — verify rclone command building and output parsing."""

from __future__ import annotations

import json

import pytest

from src.adapters.rclone_adapter import RcloneAdapter, _parse_size, PROGRESS_RE


class TestParseSize:
    def test_bytes(self):
        assert _parse_size("123 B") == 123

    def test_kibibytes(self):
        assert _parse_size("4.5 KiB") == int(4.5 * 1024)

    def test_mebibytes(self):
        assert _parse_size("2.5 MiB") == int(2.5 * 1024 * 1024)

    def test_gibibytes(self):
        assert _parse_size("1.234 GiB") == int(1.234 * 1024 * 1024 * 1024)

    def test_tebibytes(self):
        val = _parse_size("1 TiB")
        assert val == 1024 ** 4


class TestProgressRegex:
    def test_matches_progress_line(self):
        line = "Transferred:   1.234 GiB / 10.382 GiB, 13%, 12.5 MiB/s, ETA 15m30s"
        m = PROGRESS_RE.search(line)
        assert m is not None
        assert m.group(1) == "1.234 GiB"
        assert m.group(2) == "10.382 GiB"
        assert m.group(3) == "13"

    def test_matches_zero_percent(self):
        # rclone with KiB unit for zero progress
        line = "Transferred:   0.000 KiB / 100 MiB, 0%"
        m = PROGRESS_RE.search(line)
        assert m is not None
        assert m.group(3) == "0"

    def test_matches_100_percent(self):
        line = "Transferred:   5.0 GiB / 5.0 GiB, 100%"
        m = PROGRESS_RE.search(line)
        assert m is not None
        assert m.group(3) == "100"

    def test_no_match_on_non_progress_line(self):
        assert PROGRESS_RE.search("2025/01/15 10:30:45 INFO  : Notifying endpoint") is None
        assert PROGRESS_RE.search("Transfer queue exceeded 100 outstanding requests") is None


class TestRcloneAdapterInit:
    def test_adapter_stores_rclone_path(self, monkeypatch):
        """Verify adapter is created with correct params (mock rclone version call)."""
        import subprocess

        def mock_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout=b"rclone v1.65.0\n")

        monkeypatch.setattr("subprocess.run", mock_run)
        adapter = RcloneAdapter(rclone_path="/usr/bin/rclone", remote_name="pikpak:", timeout=30)
        assert adapter.rclone_path == "/usr/bin/rclone"
        assert adapter.remote_name == "pikpak:"
        assert adapter.timeout == 30

    def test_adapter_defaults(self, monkeypatch):
        import subprocess

        def mock_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout=b"rclone v1.65.0\n")

        monkeypatch.setattr("subprocess.run", mock_run)
        adapter = RcloneAdapter()
        assert adapter.rclone_path == "rclone"
        assert adapter.timeout == 300


class TestRcloneAdapterRemote:
    def test_remote_prefix(self, monkeypatch):
        import subprocess

        def mock_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout=b"rclone v1.65.0\n")

        monkeypatch.setattr("subprocess.run", mock_run)
        adapter = RcloneAdapter(remote_name="pikpak:")
        assert adapter._remote("/docs/file.txt") == "pikpak:/docs/file.txt"

    def test_remote_root(self, monkeypatch):
        import subprocess

        def mock_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout=b"rclone v1.65.0\n")

        monkeypatch.setattr("subprocess.run", mock_run)
        adapter = RcloneAdapter(remote_name="baidu:")
        assert adapter._remote("/") == "baidu:/"