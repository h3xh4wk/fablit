"""Web tests for durable curation jobs and the protected task handler.

SPEC-042 §7, §11: accepted work is persisted before it is acknowledged, job
status is behind SEC-001, and task execution is authenticated independently of
the author session. No test calls Gemini or Google Cloud.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from fablit.application.news import InMemoryNewsRepository, NewsCurator
from fablit.application.news_curation import FakeNewsCurationProvider
from fablit.application.news_jobs import (
    InlineNewsCurationTaskDispatcher,
    InMemoryNewsCurationJobRepository,
    NewsCurationJobService,
    NewsCurationJobStatus,
)
from fablit.application.news_sources import (
    FakeNewsSourceFetcher,
    NewsSource,
    NewsSourceItem,
)

SECRET = "news-authoring-secret"
HEADERS = {"Authorization": f"Bearer {SECRET}"}
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
AUDIENCE = "https://fablit.test/tasks/news-curation"
SERVICE_ACCOUNT = "news-tasks@fablit.iam.gserviceaccount.com"
TASK_HEADERS = {"Authorization": "Bearer task-token"}
SOURCE = NewsSource(
    name="The Daily Weave",
    feed_url="https://news.example.com/feed.xml",
    site_url="https://news.example.com",
)


class RecordingDispatcher:
    """A task dispatcher that records jobs instead of delivering them."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.dispatched: list[UUID] = []
        self._error = error

    def dispatch(self, job_id: UUID) -> None:
        self.dispatched.append(job_id)
        if self._error is not None:
            raise self._error


def _app() -> FastAPI:
    from fablit.config import load_config

    app = create_app(
        load_config(
            overrides={
                "environment": "testing",
                "authoring_secret": SECRET,
                "news_repository": "memory",
                "news_sources": [
                    {
                        "name": SOURCE.name,
                        "feed_url": SOURCE.feed_url,
                        "site_url": SOURCE.site_url,
                    }
                ],
                "news_task_audience": AUDIENCE,
                "news_task_service_account": SERVICE_ACCOUNT,
            }
        )
    )
    app.state.news_task_verifier = _verifier
    return app


def _verifier(token: str, audience: str) -> dict[str, Any]:
    """Stand in for Google's OIDC verification in tests."""
    assert token == "task-token"
    assert audience == AUDIENCE
    return {
        "email": SERVICE_ACCOUNT,
        "email_verified": True,
        "iss": "https://accounts.google.com",
        "aud": AUDIENCE,
    }


def make_item(**overrides: object) -> NewsSourceItem:
    values: dict[str, object] = {
        "source_name": SOURCE.name,
        "title": "Handloom revival connects weavers with new markets",
        "url": "https://news.example.com/story/1",
        "published_at": NOW - timedelta(days=1),
        "excerpt": "A collective is helping handloom weavers reach new buyers.",
    }
    values.update(overrides)
    return NewsSourceItem(**values)  # type: ignore[arg-type]


def install_job_workflow(
    app: FastAPI,
    *,
    dispatcher: RecordingDispatcher | InlineNewsCurationTaskDispatcher | None = None,
    provider: FakeNewsCurationProvider | None = None,
    job_repository: InMemoryNewsCurationJobRepository | None = None,
) -> NewsCurationJobService:
    repository = app.state.news_repository
    assert isinstance(repository, InMemoryNewsRepository)
    curator = NewsCurator(
        repository=repository,
        fetcher=FakeNewsSourceFetcher(default=(make_item(),)),
        provider=provider or FakeNewsCurationProvider(),
        sources=(SOURCE,),
        clock=lambda: NOW,
    )
    jobs = job_repository or InMemoryNewsCurationJobRepository()
    task_dispatcher = dispatcher or InlineNewsCurationTaskDispatcher()
    service = NewsCurationJobService(
        repository=jobs,
        curator=curator,
        dispatcher=task_dispatcher,
        clock=lambda: NOW + timedelta(minutes=1),
    )
    if isinstance(task_dispatcher, InlineNewsCurationTaskDispatcher):
        task_dispatcher.bind(service.run_locally)
    app.state.news_curator = curator
    app.state.news_job_repository = jobs
    app.state.news_job_dispatcher = task_dispatcher
    app.state.news_job_service = service
    return service


def client_for(
    app: FastAPI | None = None,
) -> tuple[TestClient, FastAPI]:
    application = app or _app()
    return TestClient(application), application


# --- Start and status (SEC-001) ---------------------------------------------


def test_starting_curation_requires_author_access() -> None:
    client, app = client_for()
    dispatcher = RecordingDispatcher()
    install_job_workflow(app, dispatcher=dispatcher)

    response = client.post("/authoring/pulse/curate")

    assert response.status_code == 401
    assert dispatcher.dispatched == []
    assert app.state.news_job_repository.latest() is None


def test_starting_curation_returns_a_durable_job_identity() -> None:
    client, app = client_for()
    dispatcher = RecordingDispatcher()
    install_job_workflow(app, dispatcher=dispatcher)

    response = client.post(
        "/authoring/pulse/curate", headers={**HEADERS, "Accept": "application/json"}
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["stage"] == "queued"
    assert payload["report"] is None
    assert payload["counters"]["items_published"] == 0
    assert dispatcher.dispatched == [UUID(payload["job_id"])]
    stored = app.state.news_job_repository.get(UUID(payload["job_id"]))
    assert stored is not None
    assert stored.status is NewsCurationJobStatus.QUEUED


def test_job_status_is_protected_and_reports_persisted_state() -> None:
    client, app = client_for()
    service = install_job_workflow(app, dispatcher=InlineNewsCurationTaskDispatcher())
    job = service.start()

    unauthorized = client.get(f"/authoring/pulse/jobs/{job.job_id}")
    latest_unauthorized = client.get("/authoring/pulse/jobs/latest")
    latest = client.get("/authoring/pulse/jobs/latest", headers=HEADERS)
    status = client.get(f"/authoring/pulse/jobs/{job.job_id}", headers=HEADERS)

    assert unauthorized.status_code == 401
    assert latest_unauthorized.status_code == 401
    assert latest.status_code == 200
    assert latest.json()["job_id"] == str(job.job_id)
    assert status.status_code == 200
    assert status.json()["status"] == "succeeded"
    assert status.json()["report"]["published"] == 1


def test_unknown_and_malformed_job_identities_are_404() -> None:
    client, app = client_for()
    install_job_workflow(app)

    missing = client.get(f"/authoring/pulse/jobs/{uuid4()}", headers=HEADERS)
    malformed = client.get("/authoring/pulse/jobs/not-a-uuid", headers=HEADERS)
    latest = client.get("/authoring/pulse/jobs/latest", headers=HEADERS)

    assert missing.status_code == 404
    assert malformed.status_code == 404
    assert latest.status_code == 404


def test_a_dispatch_failure_is_reported_without_a_queued_job() -> None:
    client, app = client_for()
    install_job_workflow(
        app, dispatcher=RecordingDispatcher(error=RuntimeError("queue unavailable"))
    )

    response = client.post("/authoring/pulse/curate", headers=HEADERS)

    assert response.status_code == 502
    assert "could not be queued" in response.text
    assert "no work was accepted" in response.text
    assert app.state.news_job_repository.find_active() is None


def test_curation_without_a_provider_reports_configuration() -> None:
    client, app = client_for()

    response = client.post("/authoring/pulse/curate", headers=HEADERS)

    assert response.status_code == 503
    assert "not configured" in response.text


def test_accepted_job_is_visible_after_a_fresh_application_view() -> None:
    first_client, first_app = client_for()
    shared_jobs = InMemoryNewsCurationJobRepository()
    service = install_job_workflow(
        first_app,
        dispatcher=RecordingDispatcher(),
        job_repository=shared_jobs,
    )
    accepted = service.start()

    second_app = _app()
    install_job_workflow(second_app, job_repository=shared_jobs)
    second_client, _ = client_for(second_app)

    page = second_client.get("/authoring/pulse", headers=HEADERS)
    status = second_client.get(
        f"/authoring/pulse/jobs/{accepted.job_id}", headers=HEADERS
    )

    assert page.status_code == 200
    assert "Queued" in page.text
    assert status.status_code == 200
    assert status.json()["job_id"] == str(accepted.job_id)


# --- Task handler (independent authentication) ------------------------------


def test_task_handler_refuses_unauthenticated_requests() -> None:
    client, app = client_for()
    dispatcher = RecordingDispatcher()
    service = install_job_workflow(app, dispatcher=dispatcher)
    job = service.start()

    response = client.post("/tasks/news-curation", json={"job_id": str(job.job_id)})

    assert response.status_code == 401
    stored = app.state.news_job_repository.get(job.job_id)
    assert stored is not None
    assert stored.status is NewsCurationJobStatus.QUEUED


def test_task_handler_refuses_an_identity_for_another_audience() -> None:
    client, app = client_for()
    service = install_job_workflow(app, dispatcher=RecordingDispatcher())
    job = service.start()
    app.state.news_task_verifier = lambda token, audience: {
        "email": SERVICE_ACCOUNT,
        "email_verified": True,
        "iss": "https://accounts.google.com",
        "aud": "https://elsewhere.example.com",
    }

    response = client.post(
        "/tasks/news-curation",
        json={"job_id": str(job.job_id)},
        headers=TASK_HEADERS,
    )

    assert response.status_code == 401


def test_task_handler_runs_the_job_and_is_idempotent_under_redelivery() -> None:
    client, app = client_for()
    provider = FakeNewsCurationProvider()
    service = install_job_workflow(
        app, dispatcher=RecordingDispatcher(), provider=provider
    )
    job = service.start()

    first = client.post(
        "/tasks/news-curation",
        json={"job_id": str(job.job_id)},
        headers={**TASK_HEADERS, "X-CloudTasks-TaskName": "task-1"},
    )
    duplicate = client.post(
        "/tasks/news-curation",
        json={"job_id": str(job.job_id)},
        headers={**TASK_HEADERS, "X-CloudTasks-TaskName": "task-1"},
    )

    assert first.status_code == 200
    assert first.json()["status"] == "succeeded"
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "succeeded"
    assert len(provider.requests) == 1
    stories = app.state.news_repository.list_stories()
    assert len(stories) == 1


def test_task_handler_refuses_a_malformed_body_and_unknown_job() -> None:
    client, app = client_for()
    install_job_workflow(app, dispatcher=RecordingDispatcher())

    malformed = client.post(
        "/tasks/news-curation", json={"job": "missing"}, headers=TASK_HEADERS
    )
    unknown = client.post(
        "/tasks/news-curation",
        json={"job_id": str(uuid4())},
        headers=TASK_HEADERS,
    )

    assert malformed.status_code == 400
    assert unknown.status_code == 404


def test_task_handler_reports_a_failed_continuation_for_retry() -> None:
    client, app = client_for()
    second_source = NewsSource(
        name="Atelier Notes",
        feed_url="https://atelier.example.com/feed.xml",
        site_url="https://atelier.example.com",
    )
    second_item = make_item(
        source_name=second_source.name,
        title="Handloom weavers rethink repair at a studio fair",
        url="https://atelier.example.com/story/1",
        excerpt="Handloom weavers are keeping garments in use for longer.",
    )

    class ContinuationFailingDispatcher(RecordingDispatcher):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def dispatch(self, job_id: UUID) -> None:
            self.calls += 1
            if self.calls == 1:
                super().dispatch(job_id)
                return
            raise RuntimeError("queue unavailable")

    dispatcher = ContinuationFailingDispatcher()
    stories = app.state.news_repository
    assert isinstance(stories, InMemoryNewsRepository)
    repository = InMemoryNewsCurationJobRepository()
    curator = NewsCurator(
        repository=stories,
        fetcher=FakeNewsSourceFetcher(
            items={
                SOURCE.feed_url: (make_item(),),
                second_source.feed_url: (second_item,),
            }
        ),
        provider=FakeNewsCurationProvider(),
        sources=(SOURCE, second_source),
        clock=lambda: NOW,
    )
    service = NewsCurationJobService(
        repository=repository,
        curator=curator,
        dispatcher=dispatcher,
        max_sources_per_task=1,
        clock=lambda: NOW + timedelta(minutes=1),
    )
    app.state.news_curator = curator
    app.state.news_job_repository = repository
    app.state.news_job_service = service
    app.state.news_job_dispatcher = dispatcher
    job = service.start()

    response = client.post(
        "/tasks/news-curation",
        json={"job_id": str(job.job_id)},
        headers=TASK_HEADERS,
    )

    assert response.status_code == 503
    checkpoint = repository.get(job.job_id)
    assert checkpoint is not None
    assert checkpoint.status is NewsCurationJobStatus.QUEUED
    assert checkpoint.next_source_index == 1
    assert checkpoint.report is not None
    assert checkpoint.report.published == 1


def test_a_temporary_status_failure_does_not_change_the_job() -> None:
    client, app = client_for()
    service = install_job_workflow(app, dispatcher=RecordingDispatcher())
    job = service.start()

    class UnavailableRepository(InMemoryNewsCurationJobRepository):
        def get(self, job_id: UUID) -> Any:
            from fablit.application.persistence import PersistenceError

            raise PersistenceError("simulated job store outage")

    app.state.news_job_repository = UnavailableRepository()
    app.state.news_job_service = NewsCurationJobService(
        repository=app.state.news_job_repository,
        curator=app.state.news_curator,
        dispatcher=app.state.news_job_dispatcher,
        clock=lambda: NOW,
    )

    response = client.get(f"/authoring/pulse/jobs/{job.job_id}", headers=HEADERS)

    assert response.status_code == 503
    assert service.get(job.job_id) == job


def test_page_shows_the_latest_terminal_job_and_report() -> None:
    client, app = client_for()
    install_job_workflow(app, dispatcher=InlineNewsCurationTaskDispatcher())

    accepted = client.post("/authoring/pulse/curate", headers=HEADERS)
    page = client.get("/authoring/pulse", headers=HEADERS)

    assert accepted.status_code == 202
    assert "Completed" in page.text
    assert "1 fetched, 0 duplicates, 1 published, 0 rejected, 0 failed" in page.text


def test_cloud_tasks_dispatch_requires_complete_configuration() -> None:
    from fablit.config import load_config

    with pytest.raises(RuntimeError, match="FABLIT_NEWS_TASK_QUEUE"):
        create_app(
            load_config(
                overrides={
                    "environment": "testing",
                    "news_task_dispatch": "cloud_tasks",
                }
            )
        )


def test_cloud_tasks_dispatch_is_built_from_configuration() -> None:
    from fablit.config import load_config
    from fablit.platform.cloud_tasks_dispatcher import (
        CloudTasksNewsCurationDispatcher,
    )

    app = create_app(
        load_config(
            overrides={
                "environment": "testing",
                "news_task_dispatch": "cloud_tasks",
                "news_task_queue": "projects/fablit/locations/eu/queues/news-curation",
                "news_task_handler_url": AUDIENCE,
                "news_task_service_account": SERVICE_ACCOUNT,
            }
        )
    )

    assert isinstance(app.state.news_job_dispatcher, CloudTasksNewsCurationDispatcher)


@pytest.mark.parametrize("route", ["/authoring/pulse", "/authoring/pulse/jobs/latest"])
def test_learners_cannot_read_job_status(route: str) -> None:
    client, app = client_for()
    install_job_workflow(app)

    assert client.get(route).status_code == 401
