"""Web tests for Learning Guides (SPEC-045).

The authoring workflow and the learner journey are exercised through the real
HTML: only complete, safely attributed guides publish, only published guides
appear beside their practices, and reading a guide never runs an image search
or an LLM call.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from fablit.application.image_search import ImageCandidate, ImageSearchError
from fablit.config import load_config

SECRET = "learning-guide-secret"
HEADERS = {"Authorization": f"Bearer {SECRET}"}
HTML_HEADERS = {**HEADERS, "Accept": "text/html"}
HTMX_HEADERS = {**HTML_HEADERS, "HX-Request": "true"}

TITLE = "Finding stories in everyday surroundings"
SUMMARY = "A guided way into observation and photography."
PRACTICE_AREA = "Observation and photography"
SECTION_HEADING = "Look beyond what is immediately visible"
SECTION_BODY = "Notice who prepares the space before others arrive."

IMAGE = ImageCandidate(
    photo_id="photo-1",
    image_url="https://cdn.example/large.jpg",
    thumbnail_url="https://cdn.example/thumb.jpg",
    alt_text="A hand sorting produce at a market stall",
    description="A market stall at dawn.",
    photographer="A. Photographer",
    photographer_url="https://example/photographers/a",
    source="Pixabay",
    source_url="https://example/photos/market",
    attribution="Photo by A. Photographer on Pixabay",
    width=4000,
    height=3000,
    orientation="landscape",
    license_type="free",
)

UNATTRIBUTED = ImageCandidate(
    photo_id="unattributed-1",
    image_url="https://cdn.example/unattributed.jpg",
    thumbnail_url="https://cdn.example/unattributed-thumb.jpg",
    alt_text="A market stall",
    description="A market stall.",
    photographer="",
    photographer_url="",
    source="Pixabay",
    source_url="https://example/photos/unattributed",
    attribution="",
    width=3000,
    height=2000,
    orientation="landscape",
    license_type="free",
)

_SECTION_ID = re.compile(r'id="section-([0-9a-f-]{36})"')


class FakeImageSearch:
    def __init__(
        self,
        *,
        error: bool = False,
        candidate: ImageCandidate = IMAGE,
    ) -> None:
        self.queries: list[str] = []
        self._error = error
        self._candidate = candidate

    def search(
        self, query: str, *, limit: int | None = None
    ) -> tuple[ImageCandidate, ...]:
        self.queries.append(query)
        if self._error:
            raise ImageSearchError("image search is unavailable")
        return (self._candidate,)


def _client(
    *, image_search: FakeImageSearch | None = None
) -> tuple[TestClient, FastAPI]:
    app = create_app(
        load_config(
            overrides={
                "environment": "testing",
                "authoring_secret": SECRET,
                "practice_history_repository": "memory",
            }
        )
    )
    app.state.authoring_ai_provider = Mock()
    app.state.authoring_image_search = image_search
    return TestClient(app), app


def _practice(app: FastAPI) -> tuple[UUID, str]:
    activity = app.state.demo_content.activities[0]
    return activity.activity.id, activity.title


def _new_guide(client: TestClient) -> str:
    response = client.post(
        "/authoring/guides",
        headers=HTML_HEADERS,
        data={"title": TITLE, "practice_area": PRACTICE_AREA},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    return response.headers["location"].rsplit("/", 1)[-1]


def _save_details(client: TestClient, guide_id: str, practice_id: UUID) -> str:
    response = client.post(
        f"/authoring/guides/{guide_id}/details",
        headers=HTML_HEADERS,
        data={
            "title": TITLE,
            "summary": SUMMARY,
            "practice_area": PRACTICE_AREA,
            "intended_learner_context": "A learner starting an open-ended prompt.",
            "associated_practice_ids": str(practice_id),
        },
    )
    assert response.status_code == 200, response.text
    return response.text


def _add_section(
    client: TestClient,
    guide_id: str,
    *,
    stage: str = "observe",
    heading: str = SECTION_HEADING,
    body: str = SECTION_BODY,
) -> str:
    response = client.post(
        f"/authoring/guides/{guide_id}/sections",
        headers=HTML_HEADERS,
        data={"stage": stage, "heading": heading, "body": body},
    )
    assert response.status_code == 200, response.text
    return response.text


def _section_ids(html: str) -> list[str]:
    return _SECTION_ID.findall(html)


def _prepare(client: TestClient, app: FastAPI) -> tuple[str, UUID, str]:
    """Create, detail, and add one section — but do not publish."""
    guide_id = _new_guide(client)
    practice_id, _ = _practice(app)
    _save_details(client, guide_id, practice_id)
    page = _add_section(client, guide_id)
    return guide_id, practice_id, _section_ids(page)[0]


def _search(
    client: TestClient,
    guide_id: str,
    section_id: str,
    query: str = "hands at work in a market",
) -> Any:
    return client.post(
        f"/authoring/guides/{guide_id}/sections/{section_id}/images/search",
        headers=HTMX_HEADERS,
        data={"query": query},
    )


def _select(
    client: TestClient,
    guide_id: str,
    section_id: str,
    *,
    photo_id: str = "photo-1",
    alt_text: str = "Hands sorting produce",
    caption: str = "",
) -> Any:
    return client.post(
        f"/authoring/guides/{guide_id}/sections/{section_id}/images",
        headers=HTML_HEADERS,
        data={"photo_id": photo_id, "alt_text": alt_text, "caption": caption},
    )


def _publish(client: TestClient, guide_id: str) -> Any:
    return client.post(f"/authoring/guides/{guide_id}/publish", headers=HTML_HEADERS)


# ---------------------------------------------------------------------------
# Authoring and authorisation
# ---------------------------------------------------------------------------


def test_guide_authoring_requires_author_access() -> None:
    client, _ = _client()

    assert client.get("/authoring/guides").status_code == 401
    assert client.post("/authoring/guides", data={"title": TITLE}).status_code == 401


def test_author_can_create_a_draft_guide_without_a_practice() -> None:
    client, _ = _client()

    guide_id = _new_guide(client)

    page = client.get(f"/authoring/guides/{guide_id}", headers=HTML_HEADERS)
    assert page.status_code == 200
    assert TITLE in page.text
    assert "Draft" in page.text
    # A draft never becomes learner-visible, even by direct URL.
    assert client.get(f"/guides/{guide_id}").status_code == 404


def test_author_can_add_reorder_and_remove_sections() -> None:
    client, _ = _client()
    guide_id = _new_guide(client)
    _add_section(client, guide_id, stage="observe", heading="Look closely")
    page = _add_section(client, guide_id, stage="think", heading="Ask why")
    section_ids = _section_ids(page)
    assert len(section_ids) == 2
    assert page.index("Look closely") < page.index("Ask why")

    moved = client.post(
        f"/authoring/guides/{guide_id}/sections/{section_ids[1]}/move",
        headers=HTML_HEADERS,
        data={"direction": "up"},
    )
    assert moved.status_code == 200
    assert moved.text.index("Ask why") < moved.text.index("Look closely")

    removed = client.post(
        f"/authoring/guides/{guide_id}/sections/{section_ids[0]}/remove",
        headers=HTML_HEADERS,
    )
    assert removed.status_code == 200
    assert "Look closely" not in removed.text
    assert "Ask why" in removed.text


def test_preview_shows_a_draft_with_a_preview_banner() -> None:
    client, app = _client()
    guide_id, _, _ = _prepare(client, app)

    preview = client.get(f"/authoring/guides/{guide_id}/preview", headers=HTML_HEADERS)

    assert preview.status_code == 200
    assert "Draft preview" in preview.text
    assert SECTION_HEADING in preview.text


# ---------------------------------------------------------------------------
# Image search, provenance, and text-only fallback
# ---------------------------------------------------------------------------


def test_section_image_search_reuses_the_existing_provider() -> None:
    search = FakeImageSearch()
    client, app = _client(image_search=search)
    guide_id, _, section_id = _prepare(client, app)

    partial = _search(client, guide_id, section_id)

    assert partial.status_code == 200
    assert search.queries == ["hands at work in a market"]
    assert "Use this image" in partial.text
    assert "A. Photographer" in partial.text
    assert "https://cdn.example/thumb.jpg" in partial.text

    selected = _select(client, guide_id, section_id)

    assert selected.status_code == 200
    assert "https://cdn.example/thumb.jpg" in selected.text
    assert "Hands sorting produce" in selected.text
    assert "Photo by A. Photographer on Pixabay" in selected.text


def test_image_search_failure_allows_a_text_only_section() -> None:
    client, app = _client(image_search=FakeImageSearch(error=True))
    guide_id, _, section_id = _prepare(client, app)

    partial = _search(client, guide_id, section_id)

    assert partial.status_code == 200
    assert "text-only" in partial.text

    published = _publish(client, guide_id)
    assert published.status_code == 200
    assert "Guide published" in published.text


def test_inadequately_attributed_image_blocks_publication() -> None:
    client, app = _client(image_search=FakeImageSearch(candidate=UNATTRIBUTED))
    guide_id, _, section_id = _prepare(client, app)
    _search(client, guide_id, section_id)
    _select(client, guide_id, section_id, photo_id="unattributed-1")

    refused = _publish(client, guide_id)

    assert refused.status_code == 422
    assert "creator, source, or attribution" in refused.text
    assert client.get(f"/guides/{guide_id}").status_code == 404

    client.post(
        f"/authoring/guides/{guide_id}/sections/{section_id}/images/remove",
        headers=HTML_HEADERS,
        data={"asset_id": "unattributed-1"},
    )
    published = _publish(client, guide_id)
    assert published.status_code == 200


# ---------------------------------------------------------------------------
# Learner journey
# ---------------------------------------------------------------------------


def test_published_guide_opens_from_its_practice_and_returns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="fablit.guides")
    client, app = _client(image_search=FakeImageSearch())
    guide_id, practice_id, section_id = _prepare(client, app)
    _search(client, guide_id, section_id)
    _select(client, guide_id, section_id)
    assert _publish(client, guide_id).status_code == 200

    practice_page = client.get(f"/activities/{practice_id}")

    assert practice_page.status_code == 200
    assert "Explore a Learning Guide" in practice_page.text
    assert f"/guides/{guide_id}?practice_id={practice_id}" in practice_page.text

    guide_page = client.get(f"/guides/{guide_id}")

    assert guide_page.status_code == 200
    assert SECTION_HEADING in guide_page.text
    assert "Illustrative stock image" in guide_page.text
    assert "Photo by A. Photographer on Pixabay" in guide_page.text

    returned = client.get(
        f"/guides/{guide_id}/return-to-practice?practice_id={practice_id}",
        follow_redirects=False,
    )

    assert returned.status_code == 303
    assert returned.headers["location"] == f"/activities/{practice_id}"
    messages = [
        record.message for record in caplog.records if record.name == "fablit.guides"
    ]
    assert "learning_guide_opened" in messages
    assert "learning_guide_returned_to_practice" in messages


def test_draft_and_archived_guides_are_not_learner_visible() -> None:
    client, app = _client()
    guide_id, practice_id, _ = _prepare(client, app)

    assert client.get(f"/guides/{guide_id}").status_code == 404
    assert (
        "Explore a Learning Guide" not in client.get(f"/activities/{practice_id}").text
    )

    assert _publish(client, guide_id).status_code == 200
    assert client.get(f"/guides/{guide_id}").status_code == 200

    archived = client.post(
        f"/authoring/guides/{guide_id}/archive", headers=HTML_HEADERS
    )
    assert archived.status_code == 200
    assert "Guide archived" in archived.text
    assert client.get(f"/guides/{guide_id}").status_code == 404
    assert (
        "Explore a Learning Guide" not in client.get(f"/activities/{practice_id}").text
    )


def test_reading_a_guide_never_searches_or_calls_the_llm() -> None:
    search = FakeImageSearch()
    client, app = _client(image_search=search)
    guide_id, _, section_id = _prepare(client, app)
    _search(client, guide_id, section_id)
    _select(client, guide_id, section_id)
    assert _publish(client, guide_id).status_code == 200
    search.queries.clear()
    provider = app.state.authoring_ai_provider

    response = client.get(f"/guides/{guide_id}")

    assert response.status_code == 200
    assert search.queries == []
    provider.generate.assert_not_called()
