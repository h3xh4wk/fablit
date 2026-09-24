"""Web tests for SPEC-024 — Learner Identity & Private Practice History.

Covers the identity boundary at the web layer (SPEC-024 §8):

- two fresh clients receive different learner identities and do not share
  journey state;
- one client keeps the same identity across requests (cookie persistence);
- practice submissions are attributed to the current learner;
- each learner's ``/history`` lists only their own completions, and opening
  the other learner's completion ID behaves exactly like an unknown record
  (not-found), so URL manipulation cannot cross the ownership boundary;
- repeated practices remain separate within the same learner;
- invalid completion IDs and persistence failures behave as before;
- the identity resolution mechanism is tested independently from practice
  history so failures identify whether the problem is in identity creation,
  request resolution, or persistence scoping (§8).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from fablit.config import load_config

FIRST_RESPONSE = "The contrast between the subject and the dark background stands out."
SECOND_RESPONSE = "The leading lines carry my eye from the foreground to the model."
FIRST_REFLECTION = "Learner A's private reflection."
SECOND_REFLECTION = "Learner B's private reflection."


def _app_client() -> TestClient:
    """A client running the app with the in-memory history repository."""
    test_config = load_config(overrides={"practice_history_repository": "memory"})
    test_app = create_app(test_config)
    return TestClient(test_app)


def _first_activity_href(dashboard_html: str) -> str:
    return "/activities/" + dashboard_html.split('href="/activities/')[1].split('"')[0]


def _complete_practice(client: TestClient, response: str, reflection: str) -> str:
    """Complete one practice journey; return the review href of the completion."""
    dashboard = client.get("/")
    href = _first_activity_href(dashboard.text)
    client.post(href + "/submit", data={"response": response})
    client.post("/reflect", data={"content": reflection})
    history = client.get("/history")
    for line in history.text.splitlines():
        if 'href="/history/' in line:
            return line.split('href="')[1].split('"')[0]
    raise AssertionError("no history entry link found after completion")


# --- Identity creation and persistence (§5, §8) ---------------------------------


def test_two_fresh_clients_receive_different_learner_identities() -> None:
    """Two anonymous learners never share an identity (AC-024-03)."""
    with _app_client() as client_a, _app_client() as client_b:
        a_1 = client_a.get("/")
        b_1 = client_b.get("/")

    a_cookie = a_1.headers.get("set-cookie", "")
    b_cookie = b_1.headers.get("set-cookie", "")

    assert "fablit_learner_id=" in a_cookie
    assert "fablit_learner_id=" in b_cookie
    a_id = a_cookie.split("fablit_learner_id=")[1].split(";")[0]
    b_id = b_cookie.split("fablit_learner_id=")[1].split(";")[0]
    assert a_id != b_id
    # Both identities are opaque UUIDs; nothing personal is encoded (§5.1).
    UUID(a_id)
    UUID(b_id)


def test_same_client_retains_the_same_learner_identity_across_requests() -> None:
    """The identity cookie persists and stays stable (AC-024-02)."""
    with _app_client() as client:
        first = client.get("/")
        second = client.get("/history")

    # The cookie is issued once and the browser (TestClient cookie jar) then
    # sends it back; no new identity cookie is issued on later requests.
    assert "fablit_learner_id=" in first.headers.get("set-cookie", "")
    assert second.headers.get("set-cookie") is None


def test_learner_identity_cookie_has_secure_attributes() -> None:
    """The identity cookie is HttpOnly, SameSite, path-scoped, long-lived (§5.2)."""
    with _app_client() as client:
        response = client.get("/")

    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie.replace("Lax", "lax")
    assert "Path=/" in cookie
    assert "Max-Age=31536000" in cookie


def test_identity_cookie_is_secure_in_production() -> None:
    """Production deployment sets the Secure attribute on the identity cookie."""
    test_config = load_config(
        overrides={"environment": "production", "practice_history_repository": "memory"}
    )
    test_app = create_app(test_config)
    with TestClient(test_app) as client:
        response = client.get("/")

    assert "Secure" in response.headers["set-cookie"]


def test_invalid_identity_cookie_starts_a_fresh_learner() -> None:
    """A corrupt identity value is treated as absent: a new learner starts (§5.2)."""
    with _app_client() as client:
        client.get("/")  # receive a valid identity first
        client.cookies.set("fablit_learner_id", "not-a-uuid")
        response = client.get("/")

    assert "fablit_learner_id=" in response.headers.get("set-cookie", "")


def test_identity_resolution_is_independent_of_history_scoping() -> None:
    """Identity creation is testable separately from practice history (§8)."""
    with _app_client() as client_a, _app_client() as client_b:
        a_1 = client_a.get("/")
        a_2 = client_a.get("/")
        b_1 = client_b.get("/")

    a_cookie = a_1.headers.get("set-cookie", "")
    a_id = a_cookie.split("fablit_learner_id=")[1].split(";")[0]
    # The same browser keeps the same identity; the other browser has its own.
    assert a_2.headers.get("set-cookie") is None
    assert f"fablit_learner_id={a_id}" in a_2.request.headers.get("cookie", "")
    assert a_id not in b_1.headers.get("set-cookie", "")


# --- Two-learner isolation matrix (SPEC-024 §8, AC-024-05/06/07/09) --------------


def test_two_learners_have_completely_separate_histories() -> None:
    """Learner A sees X, Learner B sees Y — and only their own (§8 matrix)."""
    with _app_client() as client_a, _app_client() as client_b:
        review_x = _complete_practice(client_a, FIRST_RESPONSE, FIRST_REFLECTION)
        review_y = _complete_practice(client_b, SECOND_RESPONSE, SECOND_REFLECTION)

        history_a = client_a.get("/history")
        history_b = client_b.get("/history")

        review_of_y_by_a = client_a.get(review_y)
        review_of_x_by_b = client_b.get(review_x)

    assert history_a.status_code == 200
    assert history_b.status_code == 200

    # Learner A → /history sees X, does not see Y.
    assert "CAT Practice" in history_a.text
    assert FIRST_RESPONSE[:20] in history_a.text
    assert SECOND_RESPONSE[:20] not in history_a.text

    # Learner B → /history sees Y, does not see X.
    assert "CAT Practice" in history_b.text
    assert SECOND_RESPONSE[:20] in history_b.text
    assert FIRST_RESPONSE[:20] not in history_b.text

    # Cross-learner review access is indistinguishable from an unknown record.
    for response in (review_of_y_by_a, review_of_x_by_b):
        assert response.status_code == 404
        assert "Practice record not found" in response.text


def test_cross_learner_completion_ids_look_like_unknown_records() -> None:
    """Reviewing the other learner's completion is not-found, no existence leak."""
    with _app_client() as client_a, _app_client() as client_b:
        review_x = _complete_practice(client_a, FIRST_RESPONSE, FIRST_REFLECTION)
        _complete_practice(client_b, SECOND_RESPONSE, SECOND_REFLECTION)

        known_to_a = client_a.get(review_x)  # owner: full review
        foreign = client_b.get(review_x)  # non-owner: not found
        unknown = client_b.get(f"/history/{uuid4()}")  # truly unknown: not found

    assert known_to_a.status_code == 200
    assert foreign.status_code == 404
    assert unknown.status_code == 404
    # Same learner-facing message: no information about existence elsewhere.
    assert "Practice record not found" in foreign.text
    assert "Practice record not found" in unknown.text


def test_submission_is_attributed_to_the_current_learner() -> None:
    """Journey records and durable completions carry the current identity."""
    with _app_client() as client_a, _app_client() as client_b:
        review_x = _complete_practice(client_a, FIRST_RESPONSE, FIRST_REFLECTION)
        review_y = _complete_practice(client_b, SECOND_RESPONSE, SECOND_REFLECTION)

        completion_x = UUID(review_x.rsplit("/", 1)[1])
        completion_y = UUID(review_y.rsplit("/", 1)[1])

        registry = client_a.app.state.learner_applications  # type: ignore[attr-defined]
        app_a: dict[Any, Any] = registry._applications
        app_b_registry = client_b.app.state.learner_applications  # type: ignore[attr-defined]
        app_b: dict[Any, Any] = app_b_registry._applications

        # Distinct learners hold distinct applications; each store's learner_id
        # matches the identity its browser was issued, and history is separated.
        assert len(app_a) == 1 and len(app_b) == 1
        learner_a = next(iter(app_a))
        learner_b = next(iter(app_b))
        assert learner_a != learner_b
        assert app_a[learner_a]._store.learner_id == learner_a
        assert app_b[learner_b]._store.learner_id == learner_b

        # Durable records: completion X belongs only to learner A's namespace
        # in learner A's repository; completion Y belongs only to learner B's
        # namespace in learner B's repository.
        repo_a = app_a[learner_a]._history_repository
        repo_b = app_b[learner_b]._history_repository
        assert repo_a._completions[(learner_a, completion_x)] is not None
        assert (learner_b, completion_x) not in repo_a._completions
        assert (learner_a, completion_y) not in repo_a._completions
        assert repo_b._completions[(learner_b, completion_y)] is not None
        assert (learner_a, completion_y) not in repo_b._completions
        assert (learner_b, completion_x) not in repo_b._completions


def test_history_remains_scoped_after_navigation() -> None:
    """Scoping survives navigation across the journey and back (§8)."""
    with _app_client() as client_a, _app_client() as client_b:
        _complete_practice(client_a, FIRST_RESPONSE, FIRST_REFLECTION)
        _complete_practice(client_b, SECOND_RESPONSE, SECOND_REFLECTION)

        # Learner A navigates elsewhere then returns to history.
        client_a.get("/practice")
        client_a.get("/")
        history_after_navigation = client_a.get("/history")

    assert FIRST_RESPONSE[:20] in history_after_navigation.text
    assert SECOND_RESPONSE[:20] not in history_after_navigation.text


def test_repeated_practices_remain_separate_within_one_learner() -> None:
    """Repeating a practice keeps distinct records for the same learner (§8)."""
    with _app_client() as client:
        first_href = _complete_practice(client, FIRST_RESPONSE, FIRST_REFLECTION)
        second_href = _complete_practice(client, SECOND_RESPONSE, SECOND_REFLECTION)

        history = client.get("/history")
        first_review = client.get(first_href)
        second_review = client.get(second_href)

    assert first_href != second_href
    assert history.text.count("CAT Practice") >= 2
    assert FIRST_RESPONSE[:20] in first_review.text
    assert SECOND_RESPONSE[:20] not in first_review.text
    assert SECOND_RESPONSE[:20] in second_review.text
    assert FIRST_RESPONSE[:20] not in second_review.text


def test_invalid_completion_id_still_behaves_correctly() -> None:
    """Invalid completion IDs keep the established not-found behaviour (§8)."""
    with _app_client() as client:
        response = client.get("/history/not-a-uuid")

    assert response.status_code == 404
    assert "Practice record not found" in response.text


def test_persistence_failure_is_handled_as_before() -> None:
    """A failing history repository still renders the recoverable error (§8)."""
    test_config = load_config(overrides={"practice_history_repository": "memory"})
    test_app = create_app(test_config)
    with TestClient(test_app) as client:
        # Build this learner's application with a normal first request.
        client.get("/")

        from fablit.application.persistence import PersistenceError

        class Failing:
            def list_completions(self, learner_id: Any) -> Any:
                raise PersistenceError("Failed to load practice history.")

            def has_completed_activity(self, learner_id: Any, activity_id: Any) -> bool:
                return False

        # Sabotage the repository on every learner application built so far.
        registry = client.app.state.learner_applications  # type: ignore[attr-defined]
        built = list(registry._applications.values())
        assert built  # the learner's application exists
        for application in built:
            application._history_repository = Failing()
        response = client.get("/history")

    assert response.status_code == 500
    assert "couldn" in response.text and "load your practice history" in response.text


def test_in_flight_journey_state_does_not_leak_between_learners() -> None:
    """Feedback state is per learner, not shared via the old demo identity (§7.4)."""
    with _app_client() as client_a, _app_client() as client_b:
        dashboard_a = client_a.get("/")
        href_a = _first_activity_href(dashboard_a.text)
        client_a.post(href_a + "/submit", data={"response": FIRST_RESPONSE})

        # Learner B, with no submission at all, has no feedback state — and
        # none of learner A's journey content appears on B's surfaces.
        feedback_b = client_b.get("/feedback", follow_redirects=False)
        dashboard_b = client_b.get("/")

        feedback_a = client_a.get("/feedback")

    assert feedback_b.status_code == 303  # redirected to the dashboard
    assert feedback_a.status_code == 200
    assert "You noticed the contrast" in feedback_a.text
    assert "You noticed the contrast" not in dashboard_b.text


def test_fresh_client_has_no_prior_history() -> None:
    """A new anonymous learner starts with an empty history (§7.4)."""
    with _app_client() as client_a, _app_client() as client_b:
        _complete_practice(client_a, FIRST_RESPONSE, FIRST_REFLECTION)
        fresh_history = client_b.get("/history")

    assert fresh_history.status_code == 200
    assert "Nothing here yet" in fresh_history.text
    assert "CAT Practice" not in fresh_history.text
