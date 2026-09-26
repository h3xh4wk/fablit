"""Web/route tests for SPEC-026 — Metacognitive Practice & Reflection.

Covers the optional pre-practice intention surface (§2.1): reachability,
capture, the skip path, blank-field acceptance, and that direct entry into
practice is never blocked. Covers the post-evaluation reflection panel
(§2.2): structured prompts immediately after the evaluation rendering,
Save/Skip controls, and that skipping never blocks completion. Covers the
history review extension (§2.3): the session's whole artifact — intention,
response, evaluation feedback, reflection — in chronological order.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from fablit.config import load_config


def _client() -> TestClient:
    test_config = load_config(overrides={"practice_history_repository": "memory"})
    test_app = create_app(test_config)
    return TestClient(test_app)


def _first_activity_href(dashboard_html: str) -> str:
    href = "/activities/" + dashboard_html.split('href="/activities/')[1].split('"')[0]
    # Card actions lead through the SPEC-026 intention prompt; the journeys
    # here drive the practice activity itself, so drop the intention suffix.
    return href.removesuffix("/intention")


def _card_action_href(page_html: str) -> str:
    """The first card's action href — leads through the intention prompt."""
    return "/activities/" + page_html.split('href="/activities/')[1].split('"')[0]


def _submit_first_activity(client: TestClient) -> str:
    """Start from the dashboard and submit a response; return the activity href."""
    dashboard = client.get("/")
    href = _first_activity_href(dashboard.text)
    client.post(href + "/submit", data={"response": "The contrast is striking."})
    return href


# --- §2.1: The pre-practice intention surface (AC 1) -----------------------------


def test_intention_page_renders_with_save_and_skip_controls() -> None:
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        response = client.get(href + "/intention")

    assert response.status_code == 200
    assert "Set an intention" in response.text
    assert "specific focus" in response.text
    assert "Continue with intention" in response.text
    assert "Skip" in response.text
    # The optional field is labelled for accessibility.
    assert 'for="intention"' in response.text


def test_stated_intention_is_echoed_in_the_active_workspace() -> None:
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        client.post(
            href + "/intention",
            data={"intention": "Focus on how two elements interact."},
        )
        practice = client.get(href)

    assert practice.status_code == 200
    assert "Focus on how two elements interact." in practice.text


def test_skip_intention_goes_straight_to_practice() -> None:
    """The skip path never blocks practice (AC 1, AC 5)."""
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        response = client.post(
            href + "/intention", data={"intention": ""}, follow_redirects=False
        )
        practice = client.get(href)

    assert response.status_code == 303
    assert response.headers["location"] == href
    assert practice.status_code == 200
    assert "Your task" in practice.text
    # No intention is rendered when none was stated.
    assert "practice__intention" not in practice.text


def test_blank_intention_is_accepted_gracefully() -> None:
    """Whitespace-only input behaves like skipping (§2.1)."""
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        response = client.post(
            href + "/intention", data={"intention": "   "}, follow_redirects=False
        )
        practice = client.get(href)

    assert response.status_code == 303
    assert practice.status_code == 200
    assert "practice__intention" not in practice.text


def test_direct_entry_into_practice_is_never_blocked() -> None:
    """Selecting an activity still opens practice directly (§2.1)."""
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        practice = client.get(href)

    assert practice.status_code == 200
    assert "Your task" in practice.text


def test_intention_for_unknown_activity_shows_not_found() -> None:
    with _client() as client:
        response = client.get("/activities/not-a-uuid/intention")

    assert response.status_code == 404
    assert "Activity not found" in response.text


# --- §2.2: The post-evaluation reflection panel (AC 3) ---------------------------


def test_feedback_page_shows_structured_reflection_prompts_after_evaluation() -> None:
    with _client() as client:
        _submit_first_activity(client)
        feedback = client.get("/feedback")

    assert feedback.status_code == 200
    # The panel follows the evaluation rendering, in the same page.
    assert "What you noticed" in feedback.text
    assert "A moment to reflect" in feedback.text
    assert (
        "What strategy or mental model did you use to complete this activity?"
        in feedback.text
    )
    assert "What was the primary friction point or misconception you encountered?" in (
        feedback.text
    )
    assert "Save reflection" in feedback.text
    assert "Skip reflection" in feedback.text


def test_reflection_page_carries_the_structured_prompts() -> None:
    with _client() as client:
        _submit_first_activity(client)
        reflection = client.get("/reflect")

    assert reflection.status_code == 200
    assert "What strategy or mental model did you use" in reflection.text
    assert "friction point or misconception" in reflection.text


def test_skipping_reflection_reaches_completion() -> None:
    """Skip never blocks completion (AC 5)."""
    with _client() as client:
        _submit_first_activity(client)
        response = client.post("/reflect", data={"content": ""}, follow_redirects=False)
        completion = client.get("/complete")

    assert response.status_code == 303
    assert completion.status_code == 200
    assert "completed this practice" in completion.text
    # The acknowledgement does not claim a reflection was recorded.
    assert "reflection has been recorded" not in completion.text


def test_saving_a_reflection_still_reports_it_recorded() -> None:
    with _client() as client:
        _submit_first_activity(client)
        client.post("/reflect", data={"content": "I will slow down next time."})
        completion = client.get("/complete")

    assert completion.status_code == 200
    assert "reflection has been recorded" in completion.text


def test_stated_intention_is_echoed_while_reflecting() -> None:
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        client.post(
            href + "/intention", data={"intention": "Watch the negative space."}
        )
        _submit_first_activity(client)
        reflection = client.get("/reflect")

    assert "Watch the negative space." in reflection.text


# --- §2.3: History renders the whole artifact (AC 7) ------------------------------


def test_review_shows_intention_response_and_reflection_in_order() -> None:
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        client.post(href + "/intention", data={"intention": "Name the dominant forms."})
        client.post(href + "/submit", data={"response": "The contrast is striking."})
        client.post("/reflect", data={"content": "I will describe interactions."})
        history = client.get("/history")
        review_href = next(
            line.split('href="')[1].split('"')[0]
            for line in history.text.splitlines()
            if 'href="/history/' in line
        )
        review = client.get(review_href)

    assert review.status_code == 200
    assert "Your intention" in review.text
    assert "Name the dominant forms." in review.text
    assert "Your response" in review.text
    assert "The contrast is striking." in review.text
    assert "Feedback you received" in review.text
    assert "Your reflection" in review.text
    assert "I will describe interactions." in review.text

    # Chronological order (§2.3): intention → response → feedback → reflection.
    intention_pos = review.text.find("Your intention")
    response_pos = review.text.find("Your response")
    feedback_pos = review.text.find("Feedback you received")
    reflection_pos = review.text.find("Your reflection")
    assert intention_pos < response_pos < feedback_pos < reflection_pos


def test_review_without_an_intention_has_no_intention_section() -> None:
    with _client() as client:
        _submit_first_activity(client)
        client.post("/reflect", data={"content": "A reflection."})
        history = client.get("/history")
        review_href = next(
            line.split('href="')[1].split('"')[0]
            for line in history.text.splitlines()
            if 'href="/history/' in line
        )
        review = client.get(review_href)

    assert review.status_code == 200
    assert "Your intention" not in review.text
    assert "Your response" in review.text


# --- §4: No scoring or analytics on metacognitive content -------------------------


def test_no_scores_or_evaluation_language_on_metacognitive_surfaces() -> None:
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        intention = client.get(href + "/intention")
        _submit_first_activity(client)
        feedback = client.get("/feedback")

    for lowered in (intention.text.lower(), feedback.text.lower()):
        assert "score" not in lowered
        assert "points" not in lowered
        assert "mastery" not in lowered


# --- Journey wiring (#92): selecting an activity leads through the prompt ---------


def test_dashboard_activity_cards_lead_to_the_intention_prompt() -> None:
    """AC 1: selecting an activity from Explore shows the intention prompt."""
    with _client() as client:
        dashboard = client.get("/")
        card_href = _card_action_href(dashboard.text)
        intention = client.get(card_href)

    assert card_href.endswith("/intention")
    assert intention.status_code == 200
    assert "Set an intention" in intention.text
    assert "Continue with intention" in intention.text
    assert "Skip" in intention.text


def test_practice_mode_activity_cards_lead_to_the_intention_prompt() -> None:
    """AC 1: the SPEC-022 entry shows the intention prompt before practice."""
    with _client() as client:
        mode_page = client.get("/practice/short-drill")
        card_href = _card_action_href(mode_page.text)
        intention = client.get(card_href)

    assert card_href.endswith("/intention")
    assert intention.status_code == 200
    assert "Set an intention" in intention.text


def test_completion_continuation_leads_to_the_intention_prompt() -> None:
    """AC 1: the SPEC-025 continuation enters practice through the prompt."""
    with _client() as client:
        _submit_first_activity(client)
        client.post("/reflect", data={"content": "I will look for balance."})
        completion = client.get("/complete")
        section = completion.text.split('class="continuation"')[1]
        continuation_href = next(
            line.split('href="')[1].split('"')[0]
            for line in section.splitlines()
            if 'href="/activities/' in line
        )
        intention = client.get(continuation_href)

    assert continuation_href.endswith("/intention")
    assert intention.status_code == 200
    assert "Set an intention" in intention.text


def test_clicking_a_card_then_skipping_reaches_practice_without_an_intention() -> None:
    """AC 2 + AC 5: the card path reaches practice; skipping is never a gate."""
    with _client() as client:
        dashboard = client.get("/")
        card_href = _card_action_href(dashboard.text)
        activity_href = card_href.removesuffix("/intention")
        response = client.post(
            card_href, data={"intention": ""}, follow_redirects=False
        )
        practice = client.get(activity_href)

    assert response.status_code == 303
    assert response.headers["location"] == activity_href
    assert practice.status_code == 200
    assert "Your task" in practice.text
    assert "practice__intention" not in practice.text


# --- Journey wiring (#92): the HTMX feedback path carries the full panel ----------


def test_htmx_feedback_shows_structured_reflection_prompts_and_controls() -> None:
    """AC 3: the default (HTMX) flow shows the panel, as the full page does."""
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        response = client.post(
            href + "/submit",
            data={"response": "The contrast is striking."},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    assert "A moment to reflect" in response.text
    assert (
        "What strategy or mental model did you use to complete this activity?"
        in response.text
    )
    assert "What was the primary friction point or misconception you encountered?" in (
        response.text
    )
    assert "Save reflection" in response.text
    assert "Skip reflection" in response.text


def test_htmx_feedback_echoes_a_stated_intention() -> None:
    """AC 4: the intention echo appears in the swapped-in feedback panel."""
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        client.post(
            href + "/intention", data={"intention": "Watch the negative space."}
        )
        response = client.post(
            href + "/submit",
            data={"response": "The contrast is striking."},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    assert "Watch the negative space." in response.text
    assert "Your intention for this practice" in response.text
