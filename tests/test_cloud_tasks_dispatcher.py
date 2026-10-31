"""Deterministic tests for the SPEC-042 Cloud Tasks dispatcher.

The transport and the API access token are injected, so no test reaches
Google Cloud or needs credentials.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from uuid import uuid4

import pytest

from fablit.application.errors import NewsCurationDispatchError
from fablit.platform.cloud_tasks_dispatcher import (
    CLOUD_TASKS_API_BASE,
    CloudTasksNewsCurationDispatcher,
)

QUEUE = "projects/fablit/locations/europe-west1/queues/news-curation"
HANDLER = "https://fablit.appspot.com/tasks/news-curation"
SERVICE_ACCOUNT = "news-tasks@fablit.iam.gserviceaccount.com"


class RecordingTransport:
    """A dispatcher transport that records the request and returns a status."""

    def __init__(self, *, status: int = 200, error: Exception | None = None) -> None:
        self.status = status
        self.error = error
        self.requests: list[tuple[str, bytes, Mapping[str, str]]] = []

    def __call__(
        self, url: str, body: bytes, headers: Mapping[str, str]
    ) -> tuple[int, bytes]:
        self.requests.append((url, body, headers))
        if self.error is not None:
            raise self.error
        return self.status, b"{}"


def make_dispatcher(
    transport: RecordingTransport,
) -> CloudTasksNewsCurationDispatcher:
    return CloudTasksNewsCurationDispatcher(
        queue_path=QUEUE,
        handler_url=HANDLER,
        service_account_email=SERVICE_ACCOUNT,
        transport=transport,
        access_token=lambda: "api-token",
    )


def test_dispatch_enqueues_an_authenticated_task() -> None:
    transport = RecordingTransport()
    dispatcher = make_dispatcher(transport)
    job_id = uuid4()

    dispatcher.dispatch(job_id)

    assert len(transport.requests) == 1
    url, body, headers = transport.requests[0]
    assert url == f"{CLOUD_TASKS_API_BASE}/{QUEUE}/tasks"
    assert headers["Authorization"] == "Bearer api-token"
    assert headers["Content-Type"] == "application/json"
    payload = json.loads(body.decode("utf-8"))
    task = payload["task"]
    http_request = task["http_request"]
    assert http_request["url"] == HANDLER
    assert http_request["http_method"] == "POST"
    assert http_request["headers"] == {"Content-Type": "application/json"}
    assert json.loads(base64.b64decode(http_request["body"])) == {"job_id": str(job_id)}
    assert http_request["oidc_token"] == {
        "service_account_email": SERVICE_ACCOUNT,
        "audience": HANDLER,
    }
    # The deadline is a field of the task, not of the HTTP request.
    assert task["dispatch_deadline"] == "540s"
    assert "dispatch_deadline" not in http_request


def test_dispatch_uses_an_explicit_audience_when_configured() -> None:
    transport = RecordingTransport()
    dispatcher = CloudTasksNewsCurationDispatcher(
        queue_path=QUEUE,
        handler_url=HANDLER,
        service_account_email=SERVICE_ACCOUNT,
        audience="fablit-tasks",
        transport=transport,
        access_token=lambda: "api-token",
    )

    dispatcher.dispatch(uuid4())

    payload = json.loads(transport.requests[0][1].decode("utf-8"))
    assert payload["task"]["http_request"]["oidc_token"]["audience"] == "fablit-tasks"


def test_dispatch_reports_a_refused_request_safely() -> None:
    transport = RecordingTransport(status=403)
    dispatcher = make_dispatcher(transport)

    with pytest.raises(NewsCurationDispatchError, match="status 403"):
        dispatcher.dispatch(uuid4())


def test_dispatch_translates_transport_failures() -> None:
    transport = RecordingTransport(error=RuntimeError("secret socket detail"))
    dispatcher = make_dispatcher(transport)

    with pytest.raises(NewsCurationDispatchError) as raised:
        dispatcher.dispatch(uuid4())

    assert "secret socket detail" not in str(raised.value)


def test_dispatch_refuses_a_non_job_identity() -> None:
    dispatcher = make_dispatcher(RecordingTransport())

    with pytest.raises(NewsCurationDispatchError):
        dispatcher.dispatch("not-a-uuid")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "overrides",
    [
        {"queue_path": "news-curation"},
        {"handler_url": "http://fablit.appspot.com/tasks/news-curation"},
        {"service_account_email": " "},
    ],
)
def test_configuration_is_validated(overrides: dict[str, str]) -> None:
    values: dict[str, str] = {
        "queue_path": QUEUE,
        "handler_url": HANDLER,
        "service_account_email": SERVICE_ACCOUNT,
    }
    values.update(overrides)

    with pytest.raises(NewsCurationDispatchError):
        CloudTasksNewsCurationDispatcher(
            queue_path=values["queue_path"],
            handler_url=values["handler_url"],
            service_account_email=values["service_account_email"],
            transport=RecordingTransport(),
            access_token=lambda: "api-token",
        )
