from __future__ import annotations

import logging
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

_CORRELATION_CONTEXT: ContextVar[dict[str, str | None] | None] = ContextVar(
    "fablit_correlation_context",
    default=None,
)


class CorrelationContext:
    """Context manager that stores request-scoped correlation values."""

    def __init__(
        self,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        self.request_id = request_id
        self.trace_id = trace_id
        self.token: Any | None = None

    def __enter__(self) -> CorrelationContext:
        self.token = _CORRELATION_CONTEXT.set(
            {
                "request_id": self.request_id,
                "trace_id": self.trace_id,
            }
        )
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.token is not None:
            _CORRELATION_CONTEXT.reset(self.token)


@contextmanager
def correlation_context(
    request_id: str | None = None,
    trace_id: str | None = None,
) -> Iterator[None]:
    with CorrelationContext(request_id=request_id, trace_id=trace_id):
        yield


def set_correlation_id(key: str, value: str | None) -> None:
    context = dict(_CORRELATION_CONTEXT.get() or {})
    context[key] = value
    _CORRELATION_CONTEXT.set(context)


def get_correlation_id(key: str) -> str | None:
    return (_CORRELATION_CONTEXT.get() or {}).get(key)


class StructuredLogger(logging.LoggerAdapter[logging.Logger]):
    """A small adapter that enriches log records with correlation IDs."""

    def process(
        self,
        msg: str,
        kwargs: MutableMapping[str, Any],
    ) -> tuple[str, MutableMapping[str, Any]]:
        kwargs.setdefault("extra", {})
        kwargs["extra"].setdefault("request_id", get_correlation_id("request_id"))
        kwargs["extra"].setdefault("trace_id", get_correlation_id("trace_id"))
        return msg, kwargs
