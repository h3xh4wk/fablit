"""Managed task dispatch for durable news curation (SPEC-042 §7).

The application persists a job, then this adapter hands only the job identity
to Cloud Tasks. Cloud Tasks delivers an authenticated HTTP request to the
application's own protected task handler, so accepted work does not depend on
the author's browser, an in-process thread, or a particular App Engine
instance.

The adapter follows the same shape as the other platform adapters: the network
call lives behind an injectable transport, the OAuth token for the Cloud Tasks
API comes from an injectable provider (Application Default Credentials by
default), and every failure becomes a safe application-level
:class:`~fablit.application.errors.NewsCurationDispatchError`.
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any, Final
from uuid import UUID

from fablit.application.errors import NewsCurationDispatchError

logger = logging.getLogger("fablit.news.tasks")

#: Cloud Tasks REST endpoint for creating a task in a queue.
CLOUD_TASKS_API_BASE: Final[str] = "https://cloudtasks.googleapis.com/v2"

#: Cloud Tasks accepts a dispatch deadline of at most ten minutes.
DEFAULT_DISPATCH_DEADLINE: Final[str] = "540s"

#: OAuth scope needed to enqueue a Cloud Tasks task.
CLOUD_TASKS_SCOPE: Final[str] = "https://www.googleapis.com/auth/cloud-platform"

#: Transport signature: ``(url, body, headers) -> (status, response_body)``.
DispatchTransport = Callable[[str, bytes, Mapping[str, str]], tuple[int, bytes]]

#: Token signature: ``() -> access token`` for the Cloud Tasks API.
AccessTokenProvider = Callable[[], str]


class CloudTasksNewsCurationDispatcher:
    """Dispatch curation jobs through a Cloud Tasks queue (SPEC-042 §7)."""

    def __init__(
        self,
        *,
        queue_path: str,
        handler_url: str,
        service_account_email: str,
        audience: str | None = None,
        dispatch_deadline: str = DEFAULT_DISPATCH_DEADLINE,
        timeout: float = 10.0,
        transport: DispatchTransport | None = None,
        access_token: AccessTokenProvider | None = None,
    ) -> None:
        if not isinstance(queue_path, str) or not queue_path.startswith("projects/"):
            raise NewsCurationDispatchError(
                "the Cloud Tasks queue path must be a full "
                "'projects/…/locations/…/queues/…' resource name"
            )
        if not isinstance(handler_url, str) or not handler_url.startswith("https://"):
            raise NewsCurationDispatchError(
                "the curation task handler URL must be an absolute HTTPS URL"
            )
        if not isinstance(service_account_email, str) or (
            not service_account_email.strip()
        ):
            raise NewsCurationDispatchError(
                "the curation task handler requires a service account email"
            )
        self._queue_path = queue_path.rstrip("/")
        self._handler_url = handler_url
        self._service_account_email = service_account_email.strip()
        self._audience = (audience or handler_url).strip()
        self._dispatch_deadline = dispatch_deadline
        self._timeout = timeout
        self._transport = transport or self._default_transport
        self._access_token = access_token or _default_access_token

    def dispatch(self, job_id: UUID) -> None:
        """Enqueue one authenticated task for ``job_id``."""
        if not isinstance(job_id, UUID):
            raise NewsCurationDispatchError("a curation task requires a job identity")
        body = json.dumps({"job_id": str(job_id)}).encode("utf-8")
        payload = {
            "task": {
                "http_request": {
                    "url": self._handler_url,
                    "http_method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": base64.b64encode(body).decode("ascii"),
                    "oidc_token": {
                        "service_account_email": self._service_account_email,
                        "audience": self._audience,
                    },
                    "dispatch_deadline": self._dispatch_deadline,
                }
            }
        }
        url = f"{CLOUD_TASKS_API_BASE}/{self._queue_path}/tasks"
        headers = {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json",
        }
        try:
            status, response_body = self._transport(
                url, json.dumps(payload).encode("utf-8"), headers
            )
        except urllib.error.HTTPError as exc:
            logger.error(
                "news curation task dispatch failed",
                extra={"job_id": str(job_id), "status": exc.code},
            )
            raise NewsCurationDispatchError(
                f"task dispatch failed (status {exc.code})"
            ) from exc
        except Exception as exc:
            logger.error(
                "news curation task dispatch failed",
                extra={"job_id": str(job_id), "error_type": type(exc).__name__},
            )
            raise NewsCurationDispatchError("task dispatch failed") from exc
        if not 200 <= status < 300:
            logger.error(
                "news curation task dispatch was refused",
                extra={"job_id": str(job_id), "status": status},
            )
            raise NewsCurationDispatchError(f"task dispatch failed (status {status})")
        logger.info(
            "news curation task dispatched",
            extra={"job_id": str(job_id), "queue": self._queue_path},
        )

    def _default_transport(
        self, url: str, body: bytes, headers: Mapping[str, str]
    ) -> tuple[int, bytes]:
        request = urllib.request.Request(
            url,
            data=body,
            headers=dict(headers),
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            return response.status, response.read()


def _default_access_token() -> str:
    """Return an OAuth token for the Cloud Tasks API from ADC."""
    try:
        import google.auth
        from google.auth.transport.requests import Request
    except ImportError as exc:  # pragma: no cover - production dependency
        raise NewsCurationDispatchError(
            "google-auth is required to dispatch curation tasks"
        ) from exc

    credentials, _ = google.auth.default(scopes=[CLOUD_TASKS_SCOPE])
    credentials.refresh(Request())
    token: Any = credentials.token
    if not isinstance(token, str) or not token.strip():
        raise NewsCurationDispatchError(
            "could not obtain credentials to dispatch curation tasks"
        )
    return token
