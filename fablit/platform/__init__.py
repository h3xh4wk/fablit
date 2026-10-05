"""Shared platform services for Fablit."""

from .auth import AuthContext, IntrospectionClient, parse_bearer_token
from .authoring_auth import (
    AUTHORING_COOKIE_NAME,
    clear_authoring_cookie,
    extract_authoring_credential,
    set_authoring_cookie,
    verify_authoring_secret,
)
from .config import ConfigLoader, RemoteOverride
from .health import (
    HealthChecker,
    HealthCheckResult,
    create_health_checker,
    readiness_check,
)
from .logging import CorrelationContext, get_correlation_id, set_correlation_id
from .metrics import Counter, MetricsRegistry
from .resilience import CircuitBreaker, retry

__all__ = [
    "AUTHORING_COOKIE_NAME",
    "AuthContext",
    "CircuitBreaker",
    "ConfigLoader",
    "CorrelationContext",
    "Counter",
    "HealthCheckResult",
    "HealthChecker",
    "IntrospectionClient",
    "MetricsRegistry",
    "RemoteOverride",
    "clear_authoring_cookie",
    "create_health_checker",
    "extract_authoring_credential",
    "get_correlation_id",
    "parse_bearer_token",
    "readiness_check",
    "retry",
    "set_authoring_cookie",
    "set_correlation_id",
    "verify_authoring_secret",
]
