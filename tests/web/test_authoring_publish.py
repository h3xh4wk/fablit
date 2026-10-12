"""Web tests for publishing approved candidates to the learner library (SPEC-035).

The tests drive the real HTTP surface an author uses (generate → approve →
publish → withdraw) and then verify the learner side through the ordinary
practice routes, so the approval/publication distinction is proven end to end
rather than against internal helpers.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from fablit.application.persistence import PersistenceError
from fablit.application.publishing import (
    PublishedPractice,
    PublishedPracticeStore,
)
from fablit.config import load_config

SECRET = "authoring-publish-secret"
HEADERS = {"Authorization": f"Bearer {SECRET}"}
HTML_HEADERS = {**HEADERS, "Accept": "text/html"}
JSON_HEADERS = {**HEADERS, "Accept": "application/json"}

TITLE = "Evidence-based observation practice"
DESCRIPTION = "Practise separating what is visible from what is inferred."

BRIEF = {
    "practice_area": "Visual analysis",
    "learner_context": "A learner practising close observation.",
    "purpose": "Distinguish visible evidence from interpretation.",
    "intended_mode": "full-practice",
    "response_form": "A short written observation.",
    "evaluation_intent": "Look for specific observable details.",
    "feedback_intent": "Identify useful evidence and one next step.",
    "reflection_intent": "Notice which observation strategy was useful.",
}


def _complete_contract() -> dict[str, str]:
    return {
        "purpose": (
            "Distinguish visible evidence from interpretation in Visual analysis."
        ),
        "task": "Identify three visible details in the provided stimulus.",
        "expected_thinking": "Connect visible details directly to interpretations.",
        "response_contract": "Three concise bullet points citing evidence.",
        "evaluation_intent": "Check for concrete descriptive language.",
        "feedback_intent": (
            "Highlight the most specific observation and suggest next step."
        ),
        "reflection_intent": "Notice which visual feature guided your analysis.",
        "continuation_intent": "Apply the observation method to a contrasting scene.",
    }


def _client(
    *,
    contract: dict[str, str] | None = None,
    title: str = TITLE,
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
    provider = Mock()
    provider.generate.return_value = SimpleNamespace(
        candidate_data={
            "title": title,
            "description": DESCRIPTION,
            "contract": dict(contract)
            if contract is not None
            else _complete_contract(),
        },
        provider="test-provider",
        model="test-model",
        generated_at=datetime(2026, 10, 11, 9, tzinfo=UTC),
    )
    app.state.authoring_ai_provider = provider
    return TestClient(app), app


def _generate(client: TestClient, **brief: object) -> str:
    response = client.post(
        "/authoring/generate",
        headers=JSON_HEADERS,
        json={**BRIEF, **brief},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["id"])


def _approve(client: TestClient, candidate_id: str) -> None:
    response = client.post(
        f"/authoring/candidates/{candidate_id}/approve", headers=HEADERS
    )
    assert response.status_code == 200, response.text


def _publish(
    client: TestClient, candidate_id: str, *, revision: int = 1
) -> dict[str, object]:
    response = client.post(
        f"/authoring/candidates/{candidate_id}/publish", headers=JSON_HEADERS
    )
    assert response.status_code == 200, response.text
    payload: dict[str, object] = response.json()
    assert payload["status"] == "published"
    assert payload["candidate_id"] == candidate_id
    assert payload["revision"] == revision
    return payload


def _activity_hrefs(page: str) -> list[str]:
    return re.findall(r'href="(/activities/[0-9a-f-]+)', page)


def _card_href(page: str, title: str) -> str:
    """Find the dashboard card for a title and return its activity href."""
    for card in re.findall(r'<li class="card">.*?</li>', page, re.DOTALL):
        if title in card:
            match = re.search(r'href="(/activities/[0-9a-f-]+)', card)
            assert match is not None, card
            return match.group(1)
    raise AssertionError(f"no dashboard card for {title!r}")


def _complete_practice(client: TestClient, href: str, title: str) -> str:
    """Run the ordinary learner journey for one activity and return history link."""
    client.post(href + "/intention", data={"intention": ""})
    practice = client.get(href)
    assert practice.status_code == 200
    submitted = client.post(
        href + "/submit",
        data={"response": "The window, the shadow, and the frame stand out."},
    )
    assert submitted.status_code == 200
    feedback = client.get("/feedback")
    assert title in feedback.text
    reflection = client.post("/reflect", data={"content": "I will slow down first."})
    assert reflection.status_code == 200
    complete = client.get("/complete")
    assert complete.status_code == 200
    history = client.get("/history")
    assert title in history.text
    return _history_href(history.text, title)


def _history_href(page: str, title: str) -> str:
    for row in re.findall(r'<li class="history__item">.*?</li>', page, re.DOTALL):
        if title in row:
            match = re.search(r'href="(/history/[0-9a-f-]+)"', row)
            if match is not None:
                return match.group(1)
    raise AssertionError(f"no history entry for {title!r}")


# --- Publication rules over HTTP (SPEC-035 §5, §10) --------------------------


def test_publish_requires_authoring_authentication() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)

    response = client.post(f"/authoring/candidates/{candidate_id}/publish")

    assert response.status_code == 401


def test_generated_candidate_cannot_be_published() -> None:
    client, _ = _client()
    candidate_id = _generate(client)

    response = client.post(
        f"/authoring/candidates/{candidate_id}/publish", headers=JSON_HEADERS
    )

    assert response.status_code == 409
    assert "not approved" in response.json()["detail"]
    assert TITLE not in client.get("/").text


def test_browser_publish_failure_is_explained_in_the_workspace() -> None:
    client, _ = _client()
    candidate_id = _generate(client)

    response = client.post(
        f"/authoring/candidates/{candidate_id}/publish", headers=HTML_HEADERS
    )

    assert response.status_code == 409
    assert "not approved" in response.text
    assert 'role="alert"' in response.text
    assert TITLE not in client.get("/").text


def test_candidate_with_validation_errors_cannot_be_published() -> None:
    client, _ = _client(contract={"task": "Only a partial contract."})
    candidate_id = _generate(client)

    response = client.post(
        f"/authoring/candidates/{candidate_id}/publish", headers=JSON_HEADERS
    )

    assert response.status_code == 422
    assert "validation errors" in response.json()["detail"]
    assert TITLE not in client.get("/").text


def test_rejected_candidate_cannot_be_published() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    client.post(f"/authoring/candidates/{candidate_id}/reject", headers=HEADERS)

    response = client.post(
        f"/authoring/candidates/{candidate_id}/publish", headers=JSON_HEADERS
    )

    assert response.status_code == 409
    assert TITLE not in client.get("/").text


def test_approved_candidate_stays_invisible_until_published() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)

    dashboard = client.get("/")
    modes = client.get("/practice/full-practice")

    assert dashboard.status_code == 200
    assert TITLE not in dashboard.text
    assert TITLE not in modes.text


def test_authorised_author_can_publish_and_learner_discovers_it() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)
    # The learner application exists before publication, so this also proves
    # an existing learner picks the publication up on the next request.
    assert TITLE not in client.get("/").text

    payload = _publish(client, candidate_id)

    dashboard = client.get("/")
    modes = client.get("/practice/full-practice")
    assert TITLE in dashboard.text
    assert DESCRIPTION in dashboard.text
    assert TITLE in modes.text
    assert dashboard.text.count(TITLE) == 1
    assert str(payload["activity_id"]) in dashboard.text


def test_hand_authored_practices_are_unchanged_by_publication() -> None:
    client, _ = _client()
    seeded = _activity_hrefs(client.get("/").text)
    candidate_id = _generate(client)
    _approve(client, candidate_id)
    _publish(client, candidate_id)

    after = _activity_hrefs(client.get("/").text)

    assert after[: len(seeded)] == seeded
    assert len(after) == len(seeded) + 1


def test_publish_without_a_candidate_fails_visibly() -> None:
    client, _ = _client()

    missing = client.post(
        "/authoring/candidates/00000000-0000-0000-0000-000000000000/publish",
        headers=JSON_HEADERS,
    )

    assert missing.status_code == 404


# --- Learner journey (SPEC-035 §7) -------------------------------------------


def test_learner_completes_a_published_practice_end_to_end() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)
    _publish(client, candidate_id)

    href = _card_href(client.get("/").text, TITLE)
    review_href = _complete_practice(client, href, TITLE)

    review = client.get(review_href)
    assert review.status_code == 200
    assert TITLE in review.text
    # Internal authoring provenance never reaches learner-facing pages.
    assert "test-provider" not in review.text
    assert candidate_id not in review.text


def test_learner_pages_expose_no_authoring_metadata() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)
    _publish(client, candidate_id)
    href = _card_href(client.get("/").text, TITLE)

    pages = [
        client.get("/").text,
        client.get(href).text,
        client.get("/practice/full-practice").text,
    ]

    for page in pages:
        assert SECRET not in page
        assert "test-provider" not in page
        assert "candidate" not in page.lower()
        assert candidate_id not in page


def test_practice_modes_keep_curated_short_drill_untouched() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)
    _publish(client, candidate_id)

    short_drill = client.get("/practice/short-drill")

    assert short_drill.status_code == 200
    assert TITLE not in short_drill.text


# --- Idempotency, replacement, withdrawal (SPEC-035 §8, §9) ------------------


def test_repeated_publish_is_idempotent_and_never_duplicates() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)

    first = _publish(client, candidate_id)
    second = _publish(client, candidate_id)

    assert first["activity_id"] == second["activity_id"]
    dashboard = client.get("/")
    assert dashboard.text.count(TITLE) == 1
    listed = client.get("/authoring/candidates", headers=JSON_HEADERS).json()
    publications = [
        item["publication"]
        for item in listed["candidates"]
        if item["publication"] is not None
    ]
    assert len(publications) == 1
    assert publications[0]["activity_id"] == first["activity_id"]
    assert publications[0]["published_revision"] == 1
    assert publications[0]["is_withdrawn"] is False


def test_edit_after_approval_blocks_publish_and_keeps_published_content() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)
    first = _publish(client, candidate_id)

    edited = client.post(
        f"/authoring/candidates/{candidate_id}/edit",
        headers=JSON_HEADERS,
        json={"title": "Edited after publication"},
    )
    assert edited.status_code == 200
    assert edited.json()["revision"] == 2

    blocked = client.post(
        f"/authoring/candidates/{candidate_id}/publish", headers=JSON_HEADERS
    )
    assert blocked.status_code == 409
    dashboard = client.get("/")
    assert TITLE in dashboard.text
    assert "Edited after publication" not in dashboard.text

    # Re-approval makes the new revision publishable, replacing in place.
    _approve(client, candidate_id)
    replacement = _publish(client, candidate_id, revision=2)
    assert replacement["activity_id"] == first["activity_id"]

    dashboard = client.get("/")
    assert "Edited after publication" in dashboard.text
    assert dashboard.text.count("Edited after publication") == 1
    assert TITLE not in dashboard.text


def test_withdrawal_removes_discovery_but_preserves_completed_history() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)
    payload = _publish(client, candidate_id)
    href = _card_href(client.get("/").text, TITLE)
    review_href = _complete_practice(client, href, TITLE)

    withdrawn = client.post(
        f"/authoring/candidates/{candidate_id}/withdraw", headers=JSON_HEADERS
    )

    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"
    assert TITLE not in client.get("/").text
    assert TITLE not in client.get("/practice/full-practice").text

    # Completed learner history stays readable, and the withdrawal policy is
    # discovery-only: a learner already in the practice still reaches it.
    assert TITLE in client.get("/history").text
    assert TITLE in client.get(review_href).text
    assert client.get(f"/activities/{payload['activity_id']}").status_code == 200


def test_withdrawal_is_idempotent_and_requires_a_publication() -> None:
    client, _ = _client()
    candidate_id = _generate(client)

    never_published = client.post(
        f"/authoring/candidates/{candidate_id}/withdraw", headers=JSON_HEADERS
    )
    assert never_published.status_code == 409

    _approve(client, candidate_id)
    _publish(client, candidate_id)
    first = client.post(
        f"/authoring/candidates/{candidate_id}/withdraw", headers=JSON_HEADERS
    )
    second = client.post(
        f"/authoring/candidates/{candidate_id}/withdraw", headers=JSON_HEADERS
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["activity_id"] == second.json()["activity_id"]


def test_republish_after_withdrawal_restores_the_same_practice() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)
    first = _publish(client, candidate_id)
    client.post(f"/authoring/candidates/{candidate_id}/withdraw", headers=HEADERS)

    restored = _publish(client, candidate_id)

    assert restored["activity_id"] == first["activity_id"]
    dashboard = client.get("/")
    assert dashboard.text.count(TITLE) == 1


# --- Failure handling (SPEC-035 §9) ------------------------------------------


class _FailingPublishedStore(PublishedPracticeStore):
    def save(self, record: PublishedPractice) -> PublishedPractice:
        raise PersistenceError("simulated publication outage")

    def get(self, activity_id: UUID) -> PublishedPractice | None:
        raise PersistenceError("simulated publication outage")

    def find_by_candidate(self, candidate_id: UUID) -> PublishedPractice | None:
        return None

    def list_records(self) -> tuple[PublishedPractice, ...]:
        raise PersistenceError("simulated publication outage")


def test_storage_failure_is_reported_and_learners_see_nothing() -> None:
    client, app = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)
    healthy_store = app.state.published_practice_store

    app.state.published_practice_store = _FailingPublishedStore()
    failed = client.post(
        f"/authoring/candidates/{candidate_id}/publish", headers=JSON_HEADERS
    )

    assert failed.status_code == 503
    assert "temporarily unavailable" in failed.json()["detail"]

    # No misleading partial state: the learner catalogue shows nothing.
    assert TITLE not in client.get("/").text

    # Once storage is back, the same explicit publish succeeds.
    app.state.published_practice_store = healthy_store
    _publish(client, candidate_id)
    assert TITLE in client.get("/").text


# --- Authoring workspace feedback (SPEC-035 implementation checklist) --------


def test_workspace_shows_publication_state_and_controls() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)

    approved_page = client.get(
        f"/authoring/candidates/{candidate_id}", headers=HTML_HEADERS
    )
    assert "Publish to Learner Library" in approved_page.text
    assert "Not published" in approved_page.text

    _publish(client, candidate_id)
    published_page = client.get(
        f"/authoring/candidates/{candidate_id}", headers=HTML_HEADERS
    )
    assert "Published to Learner Library" in published_page.text
    assert "Withdraw from Library" in published_page.text
    assert "Publish to Learner Library" not in published_page.text

    client.post(f"/authoring/candidates/{candidate_id}/withdraw", headers=HEADERS)
    withdrawn_page = client.get(
        f"/authoring/candidates/{candidate_id}", headers=HTML_HEADERS
    )
    assert "Withdrawn" in withdrawn_page.text
    assert "Publish to Learner Library" in withdrawn_page.text


def test_candidate_payload_carries_publication_provenance_for_authors() -> None:
    client, _ = _client()
    candidate_id = _generate(client)
    _approve(client, candidate_id)
    payload = _publish(client, candidate_id)

    listed = client.get("/authoring/candidates", headers=JSON_HEADERS).json()
    candidate = next(
        item for item in listed["candidates"] if item["id"] == candidate_id
    )

    publication = candidate["publication"]
    assert publication["activity_id"] == payload["activity_id"]
    assert publication["published_revision"] == 1
    assert publication["is_withdrawn"] is False
    assert publication["withdrawn_at"] is None
