from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from logging import LogRecord
from typing import Any

from .config import AppConfig

_LOG_CONTEXT: ContextVar[dict[str, str | None] | None] = ContextVar(
    "fablit_log_context",
    default=None,
)


class RequestContextFilter(logging.Filter):
    def __init__(self, service_name: str, environment: str) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def filter(self, record: LogRecord) -> bool:
        context = _LOG_CONTEXT.get()
        record.service = self.service_name
        record.environment = self.environment
        record.request_id = context.get("request_id")
        record.trace_id = context.get("trace_id")
        return True


class StructuredLogFormatter(logging.Formatter):
    def __init__(
        self,
        service_name: str,
        environment: str,
        log_format: str = "json",
    ) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment
        self.log_format = log_format.lower()

    def format(self, record: LogRecord) -> str:
        record_dict: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": getattr(record, "service", self.service_name),
            "environment": getattr(record, "environment", self.environment),
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "trace_id": getattr(record, "trace_id", None),
        }

        if hasattr(record, "status_code"):
            record_dict["status_code"] = record.status_code
        if hasattr(record, "method"):
            record_dict["method"] = record.method
        if hasattr(record, "path"):
            record_dict["path"] = record.path
        if hasattr(record, "client"):
            record_dict["client"] = record.client

        if record.exc_info:
            record_dict["exception"] = self.formatException(record.exc_info)

        if self.log_format == "text":
            pieces = [
                f"{key}={value}"
                for key, value in record_dict.items()
                if value is not None
            ]
            return " ".join(pieces)

        return json.dumps(record_dict, default=str, separators=(",", ":"))


class StructuredLogHandler(logging.StreamHandler):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.setFormatter(
            StructuredLogFormatter(
                service_name=config.service_name,
                environment=config.environment,
                log_format=config.log_format,
            )
        )


def get_request_context() -> dict[str, str | None]:
    context = _LOG_CONTEXT.get()
    if context is None:
        return {"request_id": None, "trace_id": None}
    return context.copy()


def set_request_context(
    request_id: str | None = None,
    trace_id: str | None = None,
) -> Any:
    return _LOG_CONTEXT.set({"request_id": request_id, "trace_id": trace_id})


def reset_request_context(token: Any) -> None:
    _LOG_CONTEXT.reset(token)


def _configure_library_loggers(config: AppConfig) -> None:
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "starlette"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True


def init_logging(config: AppConfig) -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(config.log_level)
    root_logger.addHandler(StructuredLogHandler(config))
    root_logger.addFilter(RequestContextFilter(config.service_name, config.environment))
    _configure_library_loggers(config)
    logging.captureWarnings(True)
