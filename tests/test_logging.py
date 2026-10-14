from __future__ import annotations

import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import request_logging_middleware
from fablit.config import AppConfig
from fablit.logging import (
    StructuredLogFormatter,
    get_request_context,
    init_logging,
    reset_request_context,
    set_request_context,
)


def _config() -> AppConfig:
    return AppConfig.model_validate(
        {
            "service_name": "fablit-test",
            "environment": "testing",
            "log_level": "INFO",
            "log_format": "json",
        }
    )


def _log_payloads(captured: str) -> list[dict[str, object]]:
    """Parse the structured JSON log lines out of captured output."""
    return [
        json.loads(line)
        for line in captured.splitlines()
        if line.strip().startswith("{")
    ]


def test_request_context_is_set_and_reset() -> None:
    token = set_request_context(request_id="req-1", trace_id="trace-1")
    assert get_request_context()["request_id"] == "req-1"
    assert get_request_context()["trace_id"] == "trace-1"

    reset_request_context(token)
    assert get_request_context()["request_id"] is None
    assert get_request_context()["trace_id"] is None


def test_structured_log_formatter_outputs_json() -> None:
    formatter = StructuredLogFormatter("fablit", "testing", "json")
    record = logging.LogRecord(
        name="fablit.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello world",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    payload = json.loads(output)

    assert payload["service"] == "fablit"
    assert payload["environment"] == "testing"
    assert payload["level"] == "INFO"
    assert payload["message"] == "hello world"


def test_init_logging_sets_root_logger_level_and_handlers() -> None:
    config = AppConfig.model_validate(
        {
            "service_name": "fablit-test",
            "environment": "testing",
            "log_level": "DEBUG",
            "log_format": "json",
        }
    )

    init_logging(config)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert any(
        isinstance(handler.formatter, StructuredLogFormatter)
        for handler in root_logger.handlers
    )


def test_logging_handler_emits_structured_records(
    capfd: pytest.CaptureFixture[str],
) -> None:
    init_logging(_config())
    logger = logging.getLogger("fablit.test")

    logger.info("startup complete")
    captured = capfd.readouterr()

    assert "startup complete" in captured.err


def test_application_logger_records_carry_request_correlation(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """SPEC-003 FR-010: completed-request logs carry request correlation.

    The correlation filter must apply to records propagated from child
    loggers (the application logger is not the root logger), otherwise every
    emitted record reports ``request_id``/``trace_id`` as null.
    """
    init_logging(_config())
    token = set_request_context(request_id="req-1", trace_id="trace-1")
    try:
        logging.getLogger("fablit.app").info(
            "request completed",
            extra={"method": "GET", "path": "/activities/1", "status_code": 200},
        )
        captured = capfd.readouterr()
    finally:
        reset_request_context(token)

    payloads = _log_payloads(captured.err)
    assert len(payloads) == 1
    assert payloads[0]["logger"] == "fablit.app"
    assert payloads[0]["request_id"] == "req-1"
    assert payloads[0]["trace_id"] == "trace-1"


def test_request_logging_middleware_correlates_with_platform_trace(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """A real request logs a generated request id plus the platform trace id."""
    init_logging(_config())
    app = FastAPI()
    app.middleware("http")(request_logging_middleware)

    @app.get("/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get(
            "/ping",
            headers={"X-Cloud-Trace-Context": "abc123/456;o=1"},
        )
    captured = capfd.readouterr()

    assert response.status_code == 200
    payload = next(
        item
        for item in _log_payloads(captured.err)
        if item["message"] == "request completed"
    )
    assert payload["path"] == "/ping"
    assert payload["status_code"] == 200
    assert isinstance(payload["request_id"], str)
    assert payload["request_id"]
    assert payload["trace_id"] == "abc123"


def test_request_logging_middleware_prefers_explicit_trace_header(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """An explicit caller-supplied trace id wins over the platform header."""
    init_logging(_config())
    app = FastAPI()
    app.middleware("http")(request_logging_middleware)

    @app.get("/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        client.get(
            "/ping",
            headers={"X-Request-ID": "req-9", "X-Trace-ID": "trace-9"},
        )
    captured = capfd.readouterr()

    payload = next(
        item
        for item in _log_payloads(captured.err)
        if item["message"] == "request completed"
    )
    assert payload["request_id"] == "req-9"
    assert payload["trace_id"] == "trace-9"
