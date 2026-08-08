from fablit.platform.auth import IntrospectionClient, parse_bearer_token
from fablit.platform.config import ConfigLoader, RemoteOverride
from fablit.platform.health import create_health_checker
from fablit.platform.logging import CorrelationContext
from fablit.platform.metrics import MetricsRegistry
from fablit.platform.resilience import CircuitBreaker, retry

if __name__ == "__main__":
    registry = MetricsRegistry()
    registry.counter("requests_total").inc()

    loader = ConfigLoader([RemoteOverride(values={"port": 9000})])
    loader.load()

    with CorrelationContext(request_id="demo", trace_id="trace-demo"):
        token = parse_bearer_token("Bearer demo-token")
        client = IntrospectionClient(lambda _: {"active": True, "sub": "demo-user"})
        client.introspect(token)

    @retry(max_attempts=2, delay_seconds=0)
    def flaky() -> str:
        return "ok"

    breaker = CircuitBreaker(failure_threshold=2)
    breaker.call(flaky)

    checker = create_health_checker(readiness=lambda: True, liveness=lambda: True)
    checker.check()
