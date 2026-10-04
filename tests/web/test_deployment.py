"""Web/route tests for the SPEC-014 learner pilot deployment boundary.

SPEC-014 establishes an operational boundary around the existing application:

- unexpected errors must render a learner-friendly page with no stack traces,
  file paths, or internal detail (§20);
- development-only interfaces (API documentation, OpenAPI schema) must not be
  exposed to learners in the pilot environment (§19, §43);
- the learner journey and health check remain available in production.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import _build_artifact_storage, create_app
from fablit.application.artifact_storage import FileArtifactStorage
from fablit.config import AppConfig, load_config
from fablit.platform.gcs_artifact_storage import GCSArtifactStorage


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
    assert "Explore" in dashboard.text


def test_development_app_still_exposes_api_documentation() -> None:
    with TestClient(create_app(_app("development"))) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").status_code == 200


# --- Artifact storage backend assembly (SPEC-034) -----------------------------


def test_build_artifact_storage_file_backend_defaults() -> None:
    config = AppConfig.model_validate({"artifact_storage_backend": "file"})
    storage = _build_artifact_storage(config)

    assert isinstance(storage, FileArtifactStorage)


def test_build_artifact_storage_gcs_backend_instantiates_adapter() -> None:
    config = AppConfig.model_validate(
        {
            "artifact_storage_backend": "gcs",
            "artifact_storage_bucket": "my-artifacts-bucket",
        }
    )

    google_cloud = MagicMock()
    fake_storage = MagicMock()
    google_cloud.storage = fake_storage
    fake_client = MagicMock()
    fake_client.project = "test-project"
    fake_storage.Client.return_value = fake_client

    with patch.dict(
        "sys.modules",
        {
            "google": MagicMock(cloud=google_cloud),
            "google.cloud": google_cloud,
            "google.cloud.storage": fake_storage,
        },
    ):
        storage = _build_artifact_storage(config)

    assert isinstance(storage, GCSArtifactStorage)
    assert storage.bucket_name == "my-artifacts-bucket"
    assert storage.client is fake_client


def test_build_artifact_storage_gcs_backend_fails_on_client_init_error() -> None:
    config = AppConfig.model_validate(
        {
            "artifact_storage_backend": "gcs",
            "artifact_storage_bucket": "my-artifacts-bucket",
        }
    )

    google_cloud = MagicMock()
    fake_storage = MagicMock()
    google_cloud.storage = fake_storage
    fake_storage.Client.side_effect = RuntimeError("GCP auth failed")

    with (
        patch.dict(
            "sys.modules",
            {
                "google": MagicMock(cloud=google_cloud),
                "google.cloud": google_cloud,
                "google.cloud.storage": fake_storage,
            },
        ),
        pytest.raises(
            RuntimeError,
            match="Could not initialize Google Cloud Storage",
        ),
    ):
        _build_artifact_storage(config)


def test_gcs_artifact_storage_web_roundtrip() -> None:
    """AC-034-08/09/10: Full web journey persists to GCS and serves privately."""
    from tests.persistence.test_gcs_artifact_storage import FakeStorageClient

    fake_client = FakeStorageClient()
    fake_storage = MagicMock()
    fake_storage.Client.return_value = fake_client

    google_cloud = MagicMock()
    google_cloud.storage = fake_storage

    config = load_config(
        overrides={
            "environment": "production",
            "practice_history_repository": "memory",
            "artifact_storage_backend": "gcs",
            "artifact_storage_bucket": "prod-sketch-bucket",
        }
    )

    with (
        patch.dict(
            "sys.modules",
            {
                "google": MagicMock(cloud=google_cloud),
                "google.cloud": google_cloud,
                "google.cloud.storage": fake_storage,
            },
        ),
        TestClient(create_app(config), base_url="https://testserver") as client,
    ):
        dashboard = client.get("/")
        hrefs = [
            "/activities/" + chunk.split('"')[0]
            for chunk in dashboard.text.split('href="/activities/')[1:]
        ]
        reflection_href = None
        for href in hrefs:
            clean_href = href.removesuffix("/intention")
            if 'name="artifact"' in client.get(clean_href).text:
                reflection_href = clean_href
                break
        assert reflection_href is not None

        png_bytes = b"\x89PNG\r\n\x1a\n" + b"gcs-web-test"
        client.post(
            reflection_href + "/submit",
            data={"response": "Sketch response persisted to GCS"},
            files={"artifact": ("my-sketch.png", png_bytes, "image/png")},
        )
        client.post("/reflect", data={"content": "Reflection with GCS artifact."})

        history = client.get("/history")
        review_href = next(
            line.split('href="')[1].split('"')[0]
            for line in history.text.splitlines()
            if 'href="/history/' in line
        )

        review = client.get(review_href)
        assert review.status_code == 200
        assert review_href + "/artifact" in review.text

        artifact_resp = client.get(review_href + "/artifact")
        assert artifact_resp.status_code == 200
        assert artifact_resp.content == png_bytes
        assert artifact_resp.headers["content-type"] == "image/png"
        assert artifact_resp.headers["cache-control"] == "private, no-store"

        # Verify underlying GCS bucket stored the blob
        bucket = fake_client.bucket("prod-sketch-bucket")
        assert len(bucket._blobs) == 1

        # When blob is deleted (e.g. absent/legacy object), route 404s and review
        # renders normally without crashing (AC-034-10)
        bucket._blobs.clear()
        artifact_missing = client.get(review_href + "/artifact")
        assert artifact_missing.status_code == 404
        review_after_deletion = client.get(review_href)
        assert review_after_deletion.status_code == 200
