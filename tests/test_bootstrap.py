"""Bootstrap platform API tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_homepage_returns_welcome_message() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.text == "Welcome to Fablit"


def test_health_returns_healthy_status() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_metrics_endpoint_exposes_registry_output() -> None:
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "requests_total" in response.text


def test_openapi_documentation_routes_are_available() -> None:
    with TestClient(app) as client:
        docs_response = client.get("/docs")
        redoc_response = client.get("/redoc")
        openapi_response = client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert redoc_response.status_code == 200
    assert openapi_response.status_code == 200


def test_application_lifespan_sets_ready_state() -> None:
    with TestClient(app):
        assert app.state.ready is True

    assert app.state.ready is False
