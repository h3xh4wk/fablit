"""Web/route tests for the SPEC-014 learner pilot deployment boundary.

SPEC-014 establishes an operational boundary around the existing application:

- unexpected errors must render a learner-friendly page with no stack traces,
  file paths, or internal detail (§20);
- development-only interfaces (API documentation, OpenAPI schema) must not be
  exposed to learners in the pilot environment (§19, §43);
- the learner journey and health check remain available in production.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from fablit.config import AppConfig, load_config


def _app(environment: str) -> AppConfig:
    return load_config(overrides={"environment": environment})


def _production_client() -> TestClient:
    return TestClient(
        create_app(_app("production")),
        raise_server_exceptions=False,
    )


# --- Learner-facing error page (SPEC-014 §20) ---------------------------------


def test_unhandled_error_renders_learner_friendly_page() -> None:
    app = create_app(_app("production"))

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("internal detail must never reach the learner")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert "Something went wrong." in response.text
    # The apostrophe is HTML-escaped (&#39;) by the template engine.
    assert "We couldn&#39;t complete that action." in response.text
    assert "Please try again." in response.text
    assert "Back to practice" in response.text
    assert 'href="/"' in response.text


def test_error_page_leaks_no_internals() -> None:
    app = create_app(_app("production"))

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret-internal-detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    lowered = response.text.lower()
    for leaked in (
        "traceback",
        "secret-internal-detail",
        "runtimeerror",
        "/app/main.py",
        "file ",
        "environment",
        "exception",
    ):
        assert leaked not in lowered


def test_error_page_offers_route_back_to_practice() -> None:
    app = create_app(_app("production"))

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert "Back to practice" in response.text
    assert 'href="/"' in response.text


# --- Static assets served scheme-agnostically (mixed-content safety) ----------


def test_static_assets_use_root_relative_urls() -> None:
    """Static asset URLs must never embed the request scheme.

    PythonAnywhere terminates HTTPS at its proxy and forwards plain HTTP to
    uvicorn, so scheme-absolute URLs (``http://...``) generated from the
    request would be blocked by the browser as mixed content. Root-relative
    paths resolve correctly under any scheme.
    """
    with _production_client() as client:
        body = client.get("/").text

    for asset in (
        "/static/css/fablit.css",
        "/static/htmx.min.js",
        "/static/favicon.svg",
    ):
        assert asset in body
    assert "http://" not in body


# --- Development-only interfaces hidden in production (SPEC-014 §19/§43) -------


def test_production_app_hides_api_documentation() -> None:
    with _production_client() as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_production_app_keeps_learner_journey_and_health() -> None:
    with _production_client() as client:
        health = client.get("/health")
        dashboard = client.get("/")

    assert health.status_code == 200
    assert health.json() == {"status": "healthy"}
    assert dashboard.status_code == 200
    assert "What would you like to explore?" in dashboard.text
    assert "Try it" in dashboard.text


def test_development_app_still_exposes_api_documentation() -> None:
    with TestClient(create_app(_app("development"))) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").status_code == 200
