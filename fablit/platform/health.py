from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(slots=True)
class HealthCheckResult:
    status: str
    readiness: bool
    liveness: bool
    details: dict[str, bool] | None = None


class HealthChecker:
    """Small health checker for readiness and liveness probes."""

    def __init__(
        self,
        *,
        readiness: Callable[[], bool] | None = None,
        liveness: Callable[[], bool] | None = None,
    ) -> None:
        self._readiness = readiness or (lambda: True)
        self._liveness = liveness or (lambda: True)

    def check(self) -> HealthCheckResult:
        readiness = self._readiness()
        liveness = self._liveness()
        status = "ready" if readiness and liveness else "not_ready"
        return HealthCheckResult(
            status=status,
            readiness=readiness,
            liveness=liveness,
            details={"readiness": readiness, "liveness": liveness},
        )


def create_health_checker(
    *,
    readiness: Callable[[], bool] | None = None,
    liveness: Callable[[], bool] | None = None,
) -> HealthChecker:
    return HealthChecker(readiness=readiness, liveness=liveness)


def readiness_check(check: Callable[[], bool]) -> bool:
    return check()
