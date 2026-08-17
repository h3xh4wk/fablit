"""Web/route tests for the learner experience (SPEC-012 journey, SPEC-013 presentation).

SPEC-013 preserves the SPEC-012 end-to-end journey while adding SPEC-013
presentation coverage: dashboard and activity-card rendering, responsive
layout, accessible form controls, conversational feedback, quiet completion,
and keyboard-navigation support.
"""

from __future__ import annotations

import re
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _activity_hrefs(dashboard_html: str) -> list[str]:
    return re.findall(r'href="(/activities/[0-9a-f-]+)"', dashboard_html)


def _submit_first_activity(client: TestClient) -> None:
    """Submit a response to the first dashboard activity (the composition activity)."""
    dashboard = client.get("/")
    href = _activity_hrefs(dashboard.text)[0]
    client.post(
        href + "/submit",
        data={
            "response": (
                "The contrast between the subject and the dark background stands out."
            )
        },
    )


def _visible_text(html: str) -> str:
    """Strip tags so only visible text remains (hrefs carry ids legitimately)."""
    return re.sub(r"<[^>]+>", " ", html)


# --- Dashboard (SPEC-013 §11–13) --------------------------------------------


def test_dashboard_renders_three_to_five_activities() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert 3 <= len(_activity_hrefs(response.text)) <= 5
    assert "Try it" in response.text


def test_dashboard_displays_skill_names() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert "Visual Analysis" in response.text
    assert "Written Communication" in response.text


def test_activity_cards_show_invitation_hierarchy() -> None:
    """Cards present title → invitation → relevant Skill → action (SPEC-013 §12)."""
    with TestClient(app) as client:
        response = client.get("/")

    html = response.text
    assert "What would you like to explore?" in html
    assert "Visual Analysis — Composition" in html
    assert "Analyse the composition of this photograph." in html
    assert "Try it" in html
    assert len(_activity_hrefs(html)) >= 3


def test_activity_cards_expose_no_internal_identifiers() -> None:
    """No internal identifiers or technical metadata in visible card text (§12)."""
    with TestClient(app) as client:
        response = client.get("/")

    visible = _visible_text(response.text)
    assert re.search(r"\bposition\b", visible.lower()) is None
    assert re.search(r"\bactivity[_-]?id\b", visible.lower()) is None
    for activity_id in re.findall(r"/activities/([0-9a-f-]+)", response.text):
        assert activity_id not in visible


# --- Practice (SPEC-013 §14–16) ----------------------------------------------


def test_practice_page_emphasises_prompt_with_accessible_response_field() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        response = client.get(href)

    assert response.status_code == 200
    assert "Visual Analysis — Composition" in response.text
    assert "Look at the photograph provided" in response.text
    assert "Visual Analysis" in response.text
    assert 'name="response"' in response.text
    assert 'id="response"' in response.text
    assert 'for="response"' in response.text
    assert "Submit response" in response.text


# --- Visual stimulus presentation (SPEC-015 §24–26) ---------------------------


def test_practice_page_displays_the_visual_stimulus() -> None:
    """The resolved image is presented before the observation prompt (§24)."""
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        response = client.get(href)

    assert response.status_code == 200
    assert 'src="/static/images/stimulus-composition.svg"' in response.text
    assert "Fablit demo stimulus" in response.text
    assert "Source" in response.text


def test_practice_page_stimulus_has_meaningful_alt_text() -> None:
    """The image carries meaningful alternative text (§26)."""
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        response = client.get(href)

    assert 'alt="A photograph-style composition for visual analysis."' in response.text


def test_non_stimulus_activity_practice_page_has_no_image() -> None:
    """Activities that do not depend on a stimulus present no image (§6)."""
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[1]
        response = client.get(href)

    assert response.status_code == 200
    assert "Written Communication" in response.text
    assert "<img" not in response.text


def test_practice_page_is_quieter_than_the_dashboard() -> None:
    """The practice page carries no activity cards and no dashboard actions."""
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        response = client.get(href)

    assert _activity_hrefs(response.text) == []
    assert "Try it" not in response.text


def test_submit_response_redirects_to_feedback() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        response = client.post(
            href + "/submit",
            data={"response": "A thoughtful analysis."},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/feedback"


def test_invalid_response_shows_validation_message() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        response = client.post(
            href + "/submit",
            data={"response": "   "},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "Please enter a response before submitting." in response.text


# --- Feedback (SPEC-013 §17–19) ----------------------------------------------


def test_feedback_presents_conversational_sections() -> None:
    with TestClient(app) as client:
        _submit_first_activity(client)
        response = client.get("/feedback")

    assert response.status_code == 200
    assert "A little feedback" in response.text
    assert "What you noticed" in response.text
    assert "What to think about" in response.text
    assert "Try this next" in response.text
    assert "Reflect" in response.text
    assert "You noticed the contrast in the image" in response.text


def test_feedback_is_response_aware() -> None:
    """Feedback reflects what the learner wrote, not predefined text (§35, §61)."""
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        client.post(
            href + "/submit",
            data={
                "response": (
                    "The model stands out because she is surrounded "
                    "by a lot of empty space."
                )
            },
        )
        response = client.get("/feedback")

    assert response.status_code == 200
    assert "empty space" in response.text


def test_different_responses_produce_different_feedback() -> None:
    """Different learner responses result in different findings (SPEC-015 §69)."""
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        client.post(
            href + "/submit",
            data={
                "response": (
                    "The contrast between the subject and the dark "
                    "background stands out."
                )
            },
        )
        contrast_feedback = client.get("/feedback").text

        client.post(
            href + "/submit",
            data={
                "response": (
                    "The leading lines carry my eye from the foreground to the model."
                )
            },
        )
        lines_feedback = client.get("/feedback").text

    assert "You noticed the contrast in the image" in contrast_feedback
    assert "You noticed the contrast in the image" not in lines_feedback
    assert "lines" in lines_feedback


def test_feedback_avoids_score_and_grade_language() -> None:
    """Learner-facing feedback never uses score/grade/pass/fail language (§18, §34)."""
    with TestClient(app) as client:
        _submit_first_activity(client)
        response = client.get("/feedback")

    lowered = response.text.lower()
    forbidden = ("score", "grade", "penalty", "passed", "failed", "incorrect", "%")
    for word in forbidden:
        assert word not in lowered


# --- Reflection (SPEC-013 §20) -----------------------------------------------


def test_reflection_page_shows_purposeful_prompt_and_accessible_field() -> None:
    with TestClient(app) as client:
        _submit_first_activity(client)
        response = client.get("/reflect")

    assert response.status_code == 200
    assert (
        "What will you try differently the next time you practise this skill?"
        in response.text
    )
    assert 'id="content"' in response.text
    assert 'for="content"' in response.text
    assert 'name="content"' in response.text
    assert "Save reflection" in response.text


def test_submit_reflection_redirects_to_completion() -> None:
    with TestClient(app) as client:
        _submit_first_activity(client)
        response = client.post(
            "/reflect",
            data={"content": "I will compare two elements."},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/complete"


def test_empty_reflection_shows_validation_message() -> None:
    with TestClient(app) as client:
        _submit_first_activity(client)
        response = client.post(
            "/reflect",
            data={"content": ""},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "Please enter a reflection before saving." in response.text


# --- Completion (SPEC-013 §21) -----------------------------------------------


def test_completion_is_quiet_and_offers_route_back_to_practice() -> None:
    with TestClient(app) as client:
        _submit_first_activity(client)
        client.post("/reflect", data={"content": "I will compare two elements."})
        response = client.get("/complete")

    assert response.status_code == 200
    assert "That's one done." in response.text
    assert "You have completed this practice." in response.text
    assert "Back to practice" in response.text
    assert 'href="/"' in response.text


# --- Journey guards -----------------------------------------------------------


def test_unknown_activity_returns_friendly_not_found() -> None:
    with TestClient(app) as client:
        invalid = client.get("/activities/not-a-uuid")
        missing = client.get(f"/activities/{uuid4()}")

    assert invalid.status_code == 404
    assert "Activity not found." in invalid.text
    assert missing.status_code == 404
    assert "Activity not found." in missing.text


def test_feedback_page_without_submission_redirects_to_dashboard() -> None:
    with TestClient(app) as client:
        response = client.get("/feedback", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_completion_page_without_journey_redirects_to_dashboard() -> None:
    with TestClient(app) as client:
        response = client.get("/complete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_full_learner_journey_end_to_end() -> None:
    """Walk the complete SPEC-012 §33 learner journey over HTTP (SPEC-013 §40)."""
    with TestClient(app) as client:
        dashboard = client.get("/")
        assert dashboard.status_code == 200
        href = _activity_hrefs(dashboard.text)[0]

        practice = client.get(href)
        assert practice.status_code == 200
        assert "Look at the photograph provided" in practice.text

        submitted = client.post(
            href + "/submit",
            data={"response": "The composition is dominated by the central subject."},
        )
        assert "A little feedback" in submitted.text

        feedback = client.get("/feedback")
        assert "Try this next" in feedback.text

        reflection = client.get("/reflect")
        assert "What will you try differently" in reflection.text

        saved = client.post(
            "/reflect",
            data={"content": "I will explain how the elements interact."},
        )
        assert "That's one done." in saved.text

        complete = client.get("/complete")
        assert "You have completed this practice." in complete.text

        back_home = client.get("/")
        assert "Try it" in back_home.text


# --- Responsive behaviour (SPEC-013 §25–26) -----------------------------------


def test_responsive_layout_has_viewport_meta_and_css_breakpoints() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        css = client.get("/static/css/fablit.css")

    assert 'name="viewport"' in dashboard.text
    assert css.status_code == 200
    assert "@media" in css.text
    assert "grid-template-columns" in css.text
    assert "repeat(auto-fit" in css.text


def test_design_tokens_are_centralized_in_css() -> None:
    """Visual values live in centralized tokens (SPEC-013 §29)."""
    with TestClient(app) as client:
        css = client.get("/static/css/fablit.css")

    for token in ("--font-", "--space-", "--color-", "--radius-", "--container-"):
        assert token in css.text


# --- Accessibility (SPEC-013 §27) ---------------------------------------------


def test_each_page_has_a_single_h1_document_hierarchy() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        practice = client.get(href)
        _submit_first_activity(client)
        feedback = client.get("/feedback")
        reflection = client.get("/reflect")
        client.post("/reflect", data={"content": "I will compare two elements."})
        completion = client.get("/complete")

    for page in (dashboard, practice, feedback, reflection, completion):
        assert len(re.findall(r"<h1", page.text)) == 1


def test_keyboard_navigation_support_is_defined() -> None:
    """Skip link, keyboard reachability, and visible focus styles are present (§27)."""
    with TestClient(app) as client:
        dashboard = client.get("/")
        css = client.get("/static/css/fablit.css")

    assert "Skip to content" in dashboard.text
    assert 'href="#main"' in dashboard.text
    assert ":focus-visible" in css.text
    assert "prefers-reduced-motion" in css.text
