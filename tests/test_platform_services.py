from __future__ import annotations

from pathlib import Path

import pytest

from fablit.platform.auth import IntrospectionClient, parse_bearer_token
from fablit.platform.config import ConfigLoader, RemoteOverride
from fablit.platform.health import (
    HealthCheckResult,
    create_health_checker,
    readiness_check,
)
from fablit.platform.logging import CorrelationContext, get_correlation_id
from fablit.platform.metrics import MetricsRegistry
from fablit.platform.resilience import CircuitBreaker, retry


def test_correlation_context_tracks_request_ids() -> None:
    with CorrelationContext(request_id="req-1", trace_id="trace-1"):
        assert get_correlation_id("request_id") == "req-1"
        assert get_correlation_id("trace_id") == "trace-1"

    assert get_correlation_id("request_id") is None
    assert get_correlation_id("trace_id") is None


def test_metrics_registry_tracks_counts_and_rendering() -> None:
    registry = MetricsRegistry()
    registry.counter("requests_total").inc()
    registry.counter("requests_total").inc(2)

    payload = registry.render()

    assert "requests_total 3.0" in payload


def test_config_loader_merges_env_and_remote_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text('{"service_name": "from-file"}', encoding="utf-8")

    monkeypatch.setenv("FABLIT_SERVICE_NAME", "from-env")

    remote_override = RemoteOverride(path=str(config_file), values={"port": 9000})
    loader = ConfigLoader([remote_override])

    config = loader.load()

    assert config.service_name == "from-env"
    assert config.port == 9000
    assert config.config_file == config_file


def test_bearer_token_parsing_and_introspection() -> None:
    token = parse_bearer_token("Bearer abc123")
    assert token == "abc123"

    client = IntrospectionClient(lambda _: {"active": True, "sub": "user-1"})
    auth_context = client.introspect("abc123")
    assert auth_context.principal == "user-1"
    assert auth_context.scopes == []


def test_retry_decorator_retries_until_success() -> None:
    attempts = {"count": 0}

    @retry(max_attempts=3, delay_seconds=0)
    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("still failing")
        return "ok"

    assert flaky() == "ok"
    assert attempts["count"] == 3


def test_circuit_breaker_opens_after_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60)

    assert breaker.state == "closed"
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == "open"

    with pytest.raises(RuntimeError):
        breaker.call(lambda: "should not run")


def test_health_checker_reports_ready_and_unhealthy() -> None:
    checker = create_health_checker(
        readiness=lambda: True,
        liveness=lambda: True,
    )

    result = checker.check()
    assert result.status == "ready"
    assert result.readiness is True
    assert result.liveness is True

    failing = create_health_checker(readiness=lambda: False, liveness=lambda: True)
    failing_result = failing.check()
    assert failing_result.status == "not_ready"
    assert isinstance(failing_result, HealthCheckResult)

    assert readiness_check(lambda: True) is True
