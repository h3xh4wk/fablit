"""Web/route tests for the learner practice flow (SPEC-012)."""

from __future__ import annotations

import re
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _activity_hrefs(dashboard_html: str) -> list[str]:
    return re.findall(r'href="(/activities/[0-9a-f-]+)"', dashboard_html)


def test_dashboard_renders_three_to_five_activities() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert 3 <= len(_activity_hrefs(response.text)) <= 5
    assert "Start Practice" in response.text


def test_dashboard_displays_skill_names() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert "Visual Analysis" in response.text
    assert "Written Communication" in response.text


def test_practice_page_shows_prompt_skills_and_response_field() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        response = client.get(href)

    assert response.status_code == 200
    assert "What am I being asked to do?" in response.text
    assert "Visual Analysis" in response.text
    assert 'name="response"' in response.text
    assert "Submit Response" in response.text


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


def test_feedback_page_shows_structured_feedback() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        client.post(href + "/submit", data={"response": "A thoughtful analysis."})
        response = client.get("/feedback")

    assert response.status_code == 200
    assert "What you did well" in response.text
    assert "Where you can improve" in response.text
    assert "Try this next" in response.text
    assert "You identified the dominant visual elements" in response.text


def test_reflection_page_shows_prompt_and_context() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        client.post(href + "/submit", data={"response": "A thoughtful analysis."})
        response = client.get("/reflect")

    assert response.status_code == 200
    assert (
        "What will you try differently the next time you practise this skill?"
        in response.text
    )
    assert "Your feedback" in response.text
    assert 'name="content"' in response.text


def test_submit_reflection_redirects_to_completion() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        client.post(href + "/submit", data={"response": "A thoughtful analysis."})
        response = client.post(
            "/reflect",
            data={"content": "I will compare two elements."},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/complete"


def test_empty_reflection_shows_validation_message() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        client.post(href + "/submit", data={"response": "A thoughtful analysis."})
        response = client.post(
            "/reflect",
            data={"content": ""},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "Please enter a reflection before saving." in response.text


def test_completion_page_confirms_completion_and_navigates_home() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        href = _activity_hrefs(dashboard.text)[0]
        client.post(href + "/submit", data={"response": "A thoughtful analysis."})
        client.post("/reflect", data={"content": "I will compare two elements."})
        response = client.get("/complete")

    assert response.status_code == 200
    assert "Reflection saved" in response.text
    assert "You have completed this practice." in response.text
    assert 'href="/"' in response.text


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
    """Walk the complete SPEC-012 §33 learner journey over HTTP."""
    with TestClient(app) as client:
        dashboard = client.get("/")
        assert dashboard.status_code == 200
        href = _activity_hrefs(dashboard.text)[0]

        practice = client.get(href)
        assert practice.status_code == 200
        assert "What am I being asked to do?" in practice.text

        submitted = client.post(
            href + "/submit",
            data={"response": "The composition is dominated by the central subject."},
        )
        assert "What you did well" in submitted.text

        feedback = client.get("/feedback")
        assert "Try this next" in feedback.text

        reflection = client.get("/reflect")
        assert "What will you try differently" in reflection.text

        saved = client.post(
            "/reflect",
            data={"content": "I will explain how the elements interact."},
        )
        assert "Reflection saved" in saved.text

        complete = client.get("/complete")
        assert "You have completed this practice." in complete.text

        back_home = client.get("/")
        assert "Start Practice" in back_home.text
