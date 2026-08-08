from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")


def retry(
    *,
    max_attempts: int = 3,
    delay_seconds: float = 0.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    if attempt >= max_attempts:
                        raise
                    if delay_seconds > 0:
                        time.sleep(delay_seconds)
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


class CircuitBreaker:
    """A very small circuit breaker with closed/open transitions."""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        recovery_timeout_seconds: int = 30,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._failure_count = 0
        self._opened_at: float | None = None
        self.state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self.state = "open"
            self._opened_at = time.time()

    def record_success(self) -> None:
        self._failure_count = 0
        self.state = "closed"
        self._opened_at = None

    def call(self, func: Callable[[], T]) -> T:
        if self.state == "open":
            raise RuntimeError("circuit breaker is open")
        try:
            result = func()
        except Exception:
            self.record_failure()
            raise
        else:
            self.record_success()
            return result
