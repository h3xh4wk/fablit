from __future__ import annotations

import json
import logging

import pytest
from fablit.config import AppConfig
from fablit.logging import (
    StructuredLogFormatter,
    get_request_context,
    init_logging,
    reset_request_context,
    set_request_context,
)


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
    config = AppConfig.model_validate(
        {
            "service_name": "fablit-test",
            "environment": "testing",
            "log_level": "INFO",
            "log_format": "json",
        }
    )

    init_logging(config)
    logger = logging.getLogger("fablit.test")

    logger.info("startup complete")
    captured = capfd.readouterr()

    assert "startup complete" in captured.err
