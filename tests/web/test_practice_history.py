"""Web/route tests for SPEC-021 — Persistent Practice History & Learner Review.

Covers history reachability from the learner experience, the empty-history
state, chronological ordering, opening the correct review, evidence display,
repeated practices remaining distinct, and the existing practice journey
still completing successfully (SPEC-021 §19 "Web/UI Tests").
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from fablit.application.persistence import PersistenceError
from fablit.config import load_config


def _history_client() -> TestClient:
    """A TestClient running the app with the in-memory history repository."""
    test_config = load_config(overrides={"practice_history_repository": "memory"})
    test_app = create_app(test_config)
    return TestClient(test_app)


def _first_activity_href(dashboard_html: str) -> str:
    """Extract the first activity href from the dashboard page."""
    return "/activities/" + dashboard_html.split('href="/activities/')[1].split('"')[0]


def _complete_first_practice(client: TestClient, response: str) -> str:
    """Complete one practice journey through the web layer; return its review href."""
    dashboard = client.get("/")
    href = _first_activity_href(dashboard.text)
    client.post(href + "/submit", data={"response": response})
    client.post("/reflect", data={"content": "I will look for balance next time."})
    history = client.get("/history")
    for line in history.text.splitlines():
        if 'href="/history/' in line:
            return line.split('href="')[1].split('"')[0]
    raise AssertionError("no history entry link found after completion")


# --- Reachability (AC-021-08 groundwork, SPEC-021 §8) ---------------------------


def test_history_is_reachable_from_the_header_navigation() -> None:
    with _history_client() as client:
        dashboard = client.get("/")

    assert dashboard.status_code == 200
    assert 'href="/history"' in dashboard.text


def test_history_route_renders_without_repository() -> None:
    """History degrades gracefully when persistence is not configured."""
    test_config = load_config(overrides={"practice_history_repository": ""})
    test_app = create_app(test_config)
    with TestClient(test_app) as client:
        response = client.get("/history")

    assert response.status_code == 200
    assert "Nothing here yet" in response.text


# --- Empty history (AC-021-08) ---------------------------------------------------


def test_empty_history_renders_clear_empty_state() -> None:
    with _history_client() as client:
        response = client.get("/history")

    assert response.status_code == 200
    assert "Nothing here yet" in response.text
    assert (
        "completed a practice" in response.text
        or "complete a practice" in response.text
    )
    assert 'href="/"' in response.text  # natural path back to Explore


# --- History content (SPEC-021 §8, §19) ------------------------------------------


def test_completed_practice_appears_in_history() -> None:
    with _history_client() as client:
        _complete_first_practice(client, "The contrast is striking.")
        history = client.get("/history")

    assert history.status_code == 200
    assert "CAT Practice" in history.text
    assert "The contrast is striking." in history.text
    assert "Review this practice" in history.text


def test_completed_practices_appear_in_chronological_order() -> None:
    with _history_client() as client:
        _complete_first_practice(client, "First attempt response.")
        _complete_first_practice(client, "Second attempt response.")
        history = client.get("/history")

    first_position = history.text.find("First attempt response.")
    second_position = history.text.find("Second attempt response.")

    assert first_position != -1
    assert second_position != -1
    # Recent completed practice appears first (§8).
    assert second_position < first_position


def test_history_does_not_introduce_progress_or_scores() -> None:
    """AC-021-12: no mastery, scores, percentages, streaks, or recommendations."""
    with _history_client() as client:
        _complete_first_practice(client, "A response.")
        history = client.get("/history")

    lowered = history.text.lower()
    for forbidden in ("mastery", "score", "percent", "streak", "level up", "rank"):
        assert forbidden not in lowered


# --- Review (SPEC-021 §9, §19) ----------------------------------------------------


def test_selecting_a_history_item_opens_the_correct_review() -> None:
    with _history_client() as client:
        review_href = _complete_first_practice(
            client, "The contrast between light and dark stands out."
        )
        review = client.get(review_href)

    assert review.status_code == 200
    assert "CAT Practice" in review.text
    assert "The contrast between light and dark stands out." in review.text


def test_review_displays_feedback_and_reflection() -> None:
    with _history_client() as client:
        review_href = _complete_first_practice(client, "A thoughtful response.")
        review = client.get(review_href)

    assert "What you noticed" in review.text
    assert "Your reflection" in review.text
    assert "I will look for balance next time." in review.text


def test_review_displays_completion_timestamp() -> None:
    with _history_client() as client:
        review_href = _complete_first_practice(client, "A response.")
        review = client.get(review_href)

    assert "Completed" in review.text


def test_review_displays_the_preserved_stimulus() -> None:
    """AC-021-07: the review shows the original stimulus, not a new one."""
    with _history_client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        practice_page = client.get(href)
        assert "/static/images/" in practice_page.text  # stimulus was resolved

        client.post(href + "/submit", data={"response": "A response."})
        client.post("/reflect", data={"content": "A reflection."})
        history = client.get("/history")
        review_href = next(
            line.split('href="')[1].split('"')[0]
            for line in history.text.splitlines()
            if 'href="/history/' in line
        )
        review = client.get(review_href)

    assert review.status_code == 200
    assert "/static/images/" in review.text


def test_repeated_practices_remain_distinct_in_review() -> None:
    """AC-021-06: each completion opens its own review."""
    with _history_client() as client:
        first_href = _complete_first_practice(client, "First attempt response.")
        second_href = _complete_first_practice(client, "Second attempt response.")

        first_review = client.get(first_href)
        second_review = client.get(second_href)

    assert first_href != second_href
    assert "First attempt response." in first_review.text
    assert "Second attempt response." not in first_review.text
    assert "Second attempt response." in second_review.text
    assert "First attempt response." not in second_review.text


def test_review_of_unknown_completion_shows_not_found_error() -> None:
    with _history_client() as client:
        response = client.get(f"/history/{uuid4()}")

    assert response.status_code == 404
    assert "Practice record not found" in response.text


def test_review_of_invalid_completion_id_shows_not_found_error() -> None:
    with _history_client() as client:
        response = client.get("/history/not-a-uuid")

    assert response.status_code == 404
    assert "Practice record not found" in response.text


# --- Failure states (AC-021-09, SPEC-021 §14) -------------------------------------


def _sabotage_repositories(client: TestClient, failing: Any) -> list[Any]:
    """Swap the repository on every built learner application; return originals."""
    registry = client.app.state.learner_applications  # type: ignore[attr-defined]
    originals: list[Any] = []
    for application in registry._applications.values():
        originals.append(application._history_repository)
        application._history_repository = failing
    return originals


def _restore_repositories(client: TestClient, originals: list[Any]) -> None:
    """Restore the original repositories on every built learner application."""
    registry = client.app.state.learner_applications  # type: ignore[attr-defined]
    built = list(registry._applications.values())
    for application, original in zip(built, originals, strict=False):
        application._history_repository = original


def test_history_load_failure_shows_recoverable_error() -> None:
    """A retrieval failure renders an explicit learner-safe error, not silence."""
    test_config = load_config(overrides={"practice_history_repository": "memory"})
    test_app = create_app(test_config)
    with TestClient(test_app) as client:
        client.get("/")  # build this learner's application

        class Failing:
            def list_completions(self, learner_id: Any) -> Any:
                raise PersistenceError("Failed to load practice history.")

            def has_completed_activity(self, learner_id: Any, activity_id: Any) -> bool:
                return False

        originals = _sabotage_repositories(client, Failing())
        try:
            response = client.get("/history")
        finally:
            _restore_repositories(client, originals)

    assert response.status_code == 500
    # The learner-facing message is explicit and recoverable, without leaking
    # internal error details (SPEC-021 §14). The apostrophe may be HTML-escaped.
    assert "couldn" in response.text and "load your practice history" in response.text
    assert 'href="/"' in response.text


def test_review_load_failure_shows_recoverable_error() -> None:
    test_config = load_config(overrides={"practice_history_repository": "memory"})
    test_app = create_app(test_config)
    with TestClient(test_app) as client:
        client.get("/")  # build this learner's application

        class Failing:
            def get_completion(self, learner_id: Any, completion_id: Any) -> Any:
                raise PersistenceError("Failed to retrieve completed practice.")

        originals = _sabotage_repositories(client, Failing())
        try:
            response = client.get(f"/history/{uuid4()}")
        finally:
            _restore_repositories(client, originals)

    assert response.status_code == 500
    assert "couldn" in response.text and "load the practice record" in response.text
    assert 'href="/"' in response.text


def test_reflection_persistence_failure_does_not_report_completion() -> None:
    """AC-021-09: a failed write must not falsely record durable completion."""
    test_config = load_config(overrides={"practice_history_repository": "memory"})
    test_app = create_app(test_config)
    with TestClient(test_app) as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        client.post(href + "/submit", data={"response": "A response."})

        class Failing:
            def save_completion(self, **kwargs: Any) -> Any:
                raise PersistenceError("Failed to save completed practice.")

            def has_completed_activity(self, learner_id: Any, activity_id: Any) -> bool:
                return False

        originals = _sabotage_repositories(client, Failing())
        try:
            response = client.post(
                "/reflect", data={"content": "A reflection."}, follow_redirects=False
            )
        finally:
            _restore_repositories(client, originals)

    # The learner is not redirected to the completion confirmation.
    assert response.status_code == 500
    # The reflection page is re-presented with an explicit error.
    assert (
        "Failed to save completed practice" in response.text
        or "couldn" in response.text
    )


# --- Existing journey preservation (AC-021-13) -------------------------------------


def test_existing_practice_journey_still_completes() -> None:
    with _history_client() as client:
        dashboard = client.get("/")
        assert dashboard.status_code == 200
        href = _first_activity_href(dashboard.text)
        practice_page = client.get(href)
        assert practice_page.status_code == 200

        submit = client.post(
            href + "/submit", data={"response": "A considered response."}
        )
        assert submit.status_code == 200

        reflect_page = client.get("/reflect")
        assert reflect_page.status_code == 200

        reflect = client.post(
            "/reflect", data={"content": "I will look for balance next time."}
        )
        assert reflect.status_code == 200

        completion = client.get("/complete")
        assert completion.status_code == 200
        assert (
            "completed this practice" in completion.text
            or "That's one done" in completion.text
        )


def test_history_link_offers_path_from_completion() -> None:
    """SPEC-021 §8: the natural flow continues from completion to history."""
    with _history_client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        client.post(href + "/submit", data={"response": "A response."})
        client.post("/reflect", data={"content": "A reflection."})
        completion = client.get("/complete")

    assert 'href="/history"' in completion.text


@pytest.mark.parametrize(
    ("route", "fragment"),
    [("/history", "Your practice"), ("/history", "practised")],
)
def test_history_pages_use_the_shared_design_system(route: str, fragment: str) -> None:
    """SPEC-021 §16: history/review preserve the editorial visual direction."""
    with _history_client() as client:
        response = client.get(route)

    assert response.status_code == 200
    assert fragment in response.text
    # The shared stylesheet is used, not per-template inline styles.
    assert "/static/css/fablit.css" in response.text
    assert "<style scoped>" not in response.text
