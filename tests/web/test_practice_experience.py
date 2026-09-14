"""Web/route tests for SPEC-020 — Visual Practice Experience Foundation.

SPEC-020 refines the presentation of the existing Practice Activity screen so
it reads as a focused design-practice workspace (stimulus → task → response →
submit) while preserving the SPEC-015 stimulus lifecycle, the SPEC-017
submission acknowledgement and duplicate-submission protection, and the
SPEC-018 completion semantics.

These tests cover the learner-facing structure only: they do not assert
evaluation, feedback, reflection, or completion behaviour beyond confirming
that the existing journey is unchanged.
"""

from __future__ import annotations

import re
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def _activity_hrefs(dashboard_html: str) -> list[str]:
    return re.findall(r'href="(/activities/[0-9a-f-]+)"', dashboard_html)


def _first_activity_href(client: TestClient) -> str:
    """The composition activity, which has a bundled visual stimulus."""
    return _activity_hrefs(client.get("/").text)[0]


def _text_first_activity_href(client: TestClient) -> str:
    """The writing activity, which has no stimulus context."""
    return _activity_hrefs(client.get("/").text)[1]


# --- AC-020-01 / AC-020-04: focused practice identity and hierarchy ------------


def test_practice_page_presents_the_practice_hierarchy_in_order() -> None:
    """Stimulus → task → response are distinct, ordered, labelled regions."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    assert response.status_code == 200
    html = response.text
    assert 'class="practice__header"' in html
    assert 'class="practice__observe"' in html
    assert 'class="practice__task"' in html
    assert 'class="practice__response"' in html
    # The labelled relationship is legible to sighted and assistive-technology
    # learners alike, and appears in the intended order.
    assert html.index("Observe") < html.index("Your task") < html.index("Your response")


def test_practice_page_keeps_a_single_labelled_response_target() -> None:
    """The response area is a single targetable region (SPEC-017 preservation)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    assert response.text.count('id="submission-area"') == 1


# --- AC-020-02: stimulus presentation -----------------------------------------


def test_stimulus_is_presented_inside_the_observe_region() -> None:
    """The resolved stimulus renders within the observe region with alt text."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    html = response.text
    observe = html[html.index('class="practice__observe"') : html.index("Your task")]
    assert 'class="stimulus__image"' in observe
    assert 'src="/static/images/stimulus-composition.svg"' in observe
    assert 'alt="A photograph-style composition for visual analysis."' in observe


def test_stimulus_images_are_local_and_never_external() -> None:
    """No new live external image-provider dependency (AC-020-12)."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        practice = client.get(href)
        css = client.get("/static/css/fablit.css")

    assert 'src="/static/images/' in practice.text
    assert not re.search(r'src="https?://', practice.text)
    assert "url(http" not in css.text


# --- AC-020-03: text-first activities -----------------------------------------


def test_text_first_activity_has_no_fabricated_imagery() -> None:
    """Activities without a suitable stimulus stay clean and fully usable."""
    with TestClient(app) as client:
        href = _text_first_activity_href(client)
        response = client.get(href)

    html = response.text
    assert response.status_code == 200
    assert "<img" not in html
    assert 'class="practice__observe"' not in html
    # The task and response hierarchy is intact without imagery.
    assert 'class="practice__task"' in html
    assert 'class="practice__response"' in html
    assert "Write a short response" in html
    assert 'name="response"' in html


# --- AC-020-05: response space -------------------------------------------------


def test_response_area_is_comfortable_and_accessible() -> None:
    """The response field is spacious, visually identifiable, and described."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    html = response.text
    assert 'class="form-control"' in html
    assert 'id="response"' in html
    assert 'for="response"' in html
    assert 'aria-describedby="response-hint"' in html
    assert "There isn't a right answer" in html
    rows = re.search(r'rows="(\d+)"', html)
    assert rows is not None
    assert int(rows.group(1)) >= 10


def test_practice_stylesheet_offers_a_comfortable_response_surface() -> None:
    with TestClient(app) as client:
        css = client.get("/static/css/fablit.css")

    assert css.status_code == 200
    assert ".practice__step" in css.text
    assert ".practice__response" in css.text
    # A minimum response height, not just the textarea's rows attribute.
    assert re.search(r"min-height:\s*1[0-9]rem", css.text)
    # Attribution metadata wraps instead of overflowing narrow viewports.
    assert "flex-wrap: wrap" in css.text


# --- AC-020-06: response preservation -----------------------------------------


def test_evaluation_failure_preserves_the_learners_response() -> None:
    """A failed evaluation keeps the learner's work in the response area."""
    answer = (
        "The dominant element is the figure, and the negative space around her "
        "directs attention back to the composition as a whole."
    )
    with TestClient(app) as client:
        href = _first_activity_href(client)
        with patch(
            "fablit.application.demo_evaluator.DemoEvaluator.evaluate",
            side_effect=Exception("boom"),
        ):
            response = client.post(
                href + "/submit",
                data={"response": answer},
                headers={"HX-Request": "true"},
            )

    assert response.status_code == 200
    assert answer in response.text
    assert 'name="response"' in response.text


def test_non_htmx_evaluation_failure_preserves_response_on_the_page() -> None:
    answer = "A considered reading of the composition."
    with TestClient(app) as client:
        href = _first_activity_href(client)
        with patch(
            "fablit.application.demo_evaluator.DemoEvaluator.evaluate",
            side_effect=Exception("boom"),
        ):
            response = client.post(href + "/submit", data={"response": answer})

    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text
    assert answer in response.text
    assert 'id="submission-area"' in response.text


# --- AC-020-07 / AC-020-08: submission and evaluation continuity ---------------


def test_submission_acknowledgement_and_duplicate_protection_remain() -> None:
    """SPEC-017 in-flight acknowledgement and duplicate protection are intact."""
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.get(href)

    text = response.text
    assert 'hx-post="' in text
    assert 'hx-target="#submission-area"' in text
    assert 'hx-swap="innerHTML"' in text
    assert 'hx-disabled-elt="find button"' in text
    assert 'aria-live="polite"' in text
    assert "Evaluating your response" in text


def test_successful_submission_still_moves_to_feedback() -> None:
    with TestClient(app) as client:
        href = _first_activity_href(client)
        response = client.post(
            href + "/submit",
            data={"response": "The contrast between light and dark is striking."},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    assert "What you noticed" in response.text
    assert "Try this next" in response.text
    assert 'id="submission-area"' not in response.text


# --- AC-020-09: completion continuity ------------------------------------------


def test_full_journey_remains_unchanged() -> None:
    with TestClient(app) as client:
        href = _first_activity_href(client)
        submitted = client.post(
            href + "/submit",
            data={"response": "The composition is led by its central subject."},
        )
        assert "Something you noticed" in submitted.text

        reflection = client.post(
            "/reflect",
            data={"content": "I will explain how two elements interact."},
        )
        assert "That's one done." in reflection.text

        complete = client.get("/complete")
        assert "You found something." in complete.text


# --- AC-020-10 / AC-020-11: responsive and accessible --------------------------


def test_practice_presentation_respects_motion_and_focus_guidance() -> None:
    with TestClient(app) as client:
        href = _first_activity_href(client)
        practice = client.get(href)
        css = client.get("/static/css/fablit.css")

    assert 'name="viewport"' in practice.text
    assert ":focus-visible" in css.text
    assert "@media (prefers-reduced-motion: reduce)" in css.text
    # Images never force horizontal overflow.
    assert "max-width: 100%" in css.text
