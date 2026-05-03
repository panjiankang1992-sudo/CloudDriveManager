"""Unit tests for src.core.logger — verify JSON logging output."""

from __future__ import annotations

import json
import logging
import io
import sys

import pytest

from src.core.logger import JSONFormatter, setup_logger


class TestJSONFormatter:
    def test_format_produces_valid_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        d = json.loads(output)
        assert d["level"] == "INFO"
        assert d["logger"] == "test_logger"
        assert d["message"] == "hello world"
        assert "timestamp" in d

    def test_format_includes_extra(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="x", lineno=1,
            msg="msg", args=(), exc_info=None,
        )
        record.extra = {"job_id": "abc", "count": 42}
        d = json.loads(formatter.format(record))
        assert d["extra"]["job_id"] == "abc"
        assert d["extra"]["count"] == 42

    def test_format_timestamp_is_iso(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="t", level=logging.WARNING, pathname="x", lineno=1,
            msg="warn", args=(), exc_info=None,
        )
        d = json.loads(formatter.format(record))
        assert "T" in d["timestamp"]  # ISO format has T


class TestSetupLogger:
    def test_setup_logger_returns_logger(self):
        logger = setup_logger("test-smoke", level=logging.DEBUG)
        assert logger.name == "test-smoke"
        assert logger.level == logging.DEBUG

    def test_console_handler_added(self):
        logger = setup_logger("test-console", level=logging.INFO)
        handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(handlers) >= 1

    def test_logger_produces_output(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))

        logger = logging.getLogger("test-output")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        logger.addHandler(handler)

        logger.info("hello from logger")
        output = stream.getvalue()
        assert "hello from logger" in output


class TestGetLogger:
    def test_get_logger_returns_logger(self):
        logger = logging.getLogger("test-get")
        # get_logger just wraps logging.getLogger
        import src.core.logger as ml
        result = ml.get_logger("test-get")
        assert result.name == "test-get"