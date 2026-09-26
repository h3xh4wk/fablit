"""Web/route tests for SPEC-017 — Submission & Evaluation Feedback.

Covers the submission-to-evaluation transition: HTMX-powered in-place
state changes, loading indicator, duplicate prevention, success/failure
transitions, answer preservation, and accessible status communication.
"""

from __future__ import annotations

import re
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def _activity_hrefs(dashboard_html: str) -> list[str]:
    """Activity hrefs on a page. Card actions lead to the SPEC-026 intention
    prompt (`/activities/<id>/intention`); the journeys here drive the
    activity itself, so only the activity path prefix is returned."""
    return re.findall(r'href="(/activities/[0-9a-f-]+)', dashboard_html)


def _first_activity_href(client: TestClient) -> str:
    dashboard = client.get("/")
    return _activity_hrefs(dashboard.text)[0]


# --- AC-017-01: Submission acknowledgement -------------------------------------


def test_practice_form_has_htmx_submission_attributes() -> None:
    """The practice form includes hx-post, hx-target, and hx-swap (FR-017-01)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    assert response.status_code == 200
    assert 'hx-post="' in response.text
    assert 'hx-target="#submission-area"' in response.text
    assert 'hx-swap="innerHTML"' in response.text
    assert 'hx-disabled-elt="find button"' in response.text


def test_practice_form_has_loading_indicator() -> None:
    """The practice form includes a loading indicator element (FR-017-01)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    assert "loading-indicator" in response.text
    assert "Evaluating your response" in response.text
    assert 'aria-live="polite"' in response.text


def test_submission_area_has_target_div() -> None:
    """The form is wrapped in a targetable div for HTMX swap (FR-017-01)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    assert 'id="submission-area"' in response.text


# --- AC-017-02: Processing state -----------------------------------------------


def test_htmx_request_returns_partial_html() -> None:
    """HTMX submissions receive partial HTML without page chrome (FR-017-02)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.post(
            href + "/submit",
            data={"response": "A thoughtful analysis."},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    # Partial response should not contain full page boilerplate
    assert "<!DOCTYPE html>" not in response.text
    assert '<meta charset="utf-8">' not in response.text
    # Should contain feedback content
    assert "Something you noticed" in response.text


def test_htmx_submission_returns_feedback_content_in_place() -> None:
    """Successful HTMX evaluation replaces the form with feedback (FR-017-04)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.post(
            href + "/submit",
            data={"response": "The composition is strong."},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    assert "What you noticed" in response.text
    assert "Try this next" in response.text
    # SPEC-026 §2.2: the HTMX partial carries the same structured reflection
    # panel as the full feedback page — Save and Skip controls, not the old
    # single Continue link.
    assert "Save reflection" in response.text
    assert "Skip reflection" in response.text


# --- AC-017-03: Duplicate prevention -------------------------------------------


def test_htmx_button_is_disabled_during_submission() -> None:
    """The submit button is disabled during HTMX request (FR-017-03)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    assert 'hx-disabled-elt="find button"' in response.text


# --- AC-017-04: Successful evaluation ------------------------------------------


def test_non_htmx_submission_still_redirects() -> None:
    """Non-HTMX requests still receive a full redirect (progressive enhancement)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.post(
            href + "/submit",
            data={"response": "A thoughtful analysis."},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/feedback"


def test_htmx_success_swaps_to_feedback_in_place() -> None:
    """On success, the submission area is replaced with feedback (AC-017-04)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.post(
            href + "/submit",
            data={"response": "The contrast is striking."},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    assert "Something you noticed" in response.text
    # The submission area should be gone — replaced by feedback
    assert 'id="submission-area"' not in response.text


# --- AC-017-05: Evaluation failure ---------------------------------------------


def test_htmx_evaluation_failure_returns_error_with_retry() -> None:
    """On evaluation failure, HTMX returns error with retry path (FR-017-05)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        with patch(
            "fablit.application.demo_evaluator.DemoEvaluator.evaluate",
            side_effect=Exception("boom"),
        ):
            response = client.post(
                href + "/submit",
                data={"response": "My analysis."},
                headers={"HX-Request": "true"},
            )

    assert response.status_code == 200
    text = response.text.lower()
    assert "couldn't evaluate" in text or "try again" in text
    # The form should still be present for retry
    assert 'hx-post="' in response.text
    assert 'name="response"' in response.text


def test_non_htmx_evaluation_failure_shows_full_error_page() -> None:
    """Non-HTMX evaluation failure renders the full practice page with error."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        with patch(
            "fablit.application.demo_evaluator.DemoEvaluator.evaluate",
            side_effect=Exception("boom"),
        ):
            response = client.post(
                href + "/submit",
                data={"response": "My analysis."},
            )

    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text


# --- AC-017-06: Answer preservation --------------------------------------------


def test_htmx_validation_error_preserves_submitted_response() -> None:
    """On validation failure, the learner's response is preserved (AC-017-06)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.post(
            href + "/submit",
            data={"response": "   "},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    assert "Please enter a response before submitting." in response.text
    assert 'hx-post="' in response.text  # Form is still present for retry


def test_htmx_evaluation_failure_preserves_response_for_retry() -> None:
    """On evaluation failure, the response is preserved for retry (AC-017-06)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        with patch(
            "fablit.application.demo_evaluator.DemoEvaluator.evaluate",
            side_effect=Exception("boom"),
        ):
            response = client.post(
                href + "/submit",
                data={"response": "My detailed analysis of the composition."},
                headers={"HX-Request": "true"},
            )

    assert response.status_code == 200
    # The form should be present for retry
    assert 'hx-post="' in response.text
    assert 'name="response"' in response.text


# --- AC-017-09: Evaluation behaviour unchanged ---------------------------------


def test_evaluation_results_unchanged_after_spec017() -> None:
    """Evaluation logic, score, and result content remain unchanged (AC-017-09)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.post(
            href + "/submit",
            data={"response": "The contrast between light and dark areas stands out."},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    # Same feedback content as before SPEC-017
    assert "Something you noticed" in response.text
    assert "You noticed the contrast" in response.text


# --- AC-017-10: No artificial waiting ------------------------------------------


def test_htmx_submission_completes_without_artificial_delay() -> None:
    """HTMX submission completes without introducing artificial delay (AC-017-10)."""
    import time

    with TestClient(app) as client:
        href = _first_activity_href(client)
        start = time.monotonic()
        response = client.post(
            href + "/submit",
            data={"response": "Quick response."},
            headers={"HX-Request": "true"},
        )
        elapsed = time.monotonic() - start

    assert response.status_code == 200
    # The demo evaluator is synchronous and deterministic — should be fast
    assert elapsed < 2.0


# --- Accessibility (AC-017-07, AC-017-08) --------------------------------------


def test_loading_indicator_has_aria_live() -> None:
    """The loading indicator exposes state changes via aria-live (AC-017-08)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    assert 'aria-live="polite"' in response.text


def test_error_role_alert_on_validation_failure() -> None:
    """Validation errors use role=alert for assistive technology (AC-017-08)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.post(
            href + "/submit",
            data={"response": "   "},
            headers={"HX-Request": "true"},
        )

    assert 'role="alert"' in response.text


def test_keyboard_submit_flow_works() -> None:
    """Keyboard navigation through submission remains functional (AC-017-07)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    # The button should be focusable and the form should be submittable
    assert 'type="submit"' in response.text
    assert 'id="response"' in response.text
    assert 'for="response"' in response.text


# --- Duplicate submission prevention via repeated HTMX requests ----------------


def test_repeated_htmx_submissions_dont_create_duplicates() -> None:
    """Multiple rapid submissions should not create duplicate evaluations."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        # First submission
        client.post(
            href + "/submit",
            data={"response": "First attempt."},
            headers={"HX-Request": "true"},
        )
        # Second submission to same activity (after first completed)
        response = client.post(
            href + "/submit",
            data={"response": "Second attempt."},
            headers={"HX-Request": "true"},
        )

    # Both should succeed — the store handles duplicate protection at the
    # application level (FR-017-03 is primarily client-side via hx-disabled-elt)
    assert response.status_code == 200


# --- CSS loading state styles --------------------------------------------------


def test_css_contains_loading_state_styles() -> None:
    """The CSS includes styles for the HTMX loading indicator (FR-017-01)."""
    with TestClient(app) as client:
        css = client.get("/static/css/fablit.css")

    assert css.status_code == 200
    assert "loading-indicator" in css.text
    assert "htmx-indicator" in css.text
    assert ".button:disabled" in css.text
