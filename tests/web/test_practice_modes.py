"""Web/route tests for SPEC-022 — Optional Practice Modes & Learner Choice.

Covers the learner-facing chooser surface only: mode-choice rendering,
accessible labels and keyboard-reachable links, Short Drill and Full
Practice entry, the return path to the normal activity library,
responsive/accessible presentation, and the absence of countdown or
scoring language (SPEC-022 §18 "Web/UI Tests"). The existing journey
regression suites (SPEC-020/021) continue to cover the practice flow
itself; the journey assertions here confirm both chosen paths still
complete it.
"""

from __future__ import annotations

import re
from html import unescape

from fastapi.testclient import TestClient

from app.main import app, create_app
from fablit.config import load_config


def _mode_choice(client: TestClient) -> str:
    return client.get("/practice").text


def _activity_hrefs(html: str) -> list[str]:
    """Activity hrefs on a page. Card actions lead to the SPEC-026 intention
    prompt (`/activities/<id>/intention`); the journeys here drive the
    activity itself, so only the activity path prefix is returned."""
    return re.findall(r'href="(/activities/[0-9a-f-]+)', html)


# --- Mode chooser rendering (AC-022-01) ----------------------------------------


def test_practice_choice_page_renders_both_modes() -> None:
    with TestClient(app) as client:
        response = client.get("/practice")

    assert response.status_code == 200
    html = response.text
    assert "What kind of practice feels right today?" in html
    assert "A short drill" in html
    assert "A full practice" in html


def test_mode_options_explain_the_difference_and_link_to_entry() -> None:
    with TestClient(app) as client:
        html = _mode_choice(client)

    # Each mode briefly explains itself and indicates the effort involved.
    assert "A few minutes to notice, write, or reset your attention." in html
    assert "A longer focused activity with the complete practice journey." in html
    assert "About 5–10 minutes" in html
    # Options navigate to the mode's activity list.
    assert 'href="/practice/short-drill"' in html
    assert 'href="/practice/full-practice"' in html


def test_mode_chooser_carries_no_countdown_or_scoring_language() -> None:
    """§10/§3: no timers, scores, streaks, or urgency framing (AC-022-06)."""
    with TestClient(app) as client:
        html = _mode_choice(client)

    lowered = html.lower()
    for forbidden in ("countdown", "timer", "score", "streak", "points", "badges"):
        assert forbidden not in lowered


# --- Accessibility (AC-022-11) ---------------------------------------------------


def test_mode_options_are_accessible_links_with_clear_names() -> None:
    """Semantic interactive controls with accessible names (§16)."""
    with TestClient(app) as client:
        html = _mode_choice(client)

    # The whole option is a real link (keyboard reachable, announced by name).
    links = re.findall(r'<a class="mode-choice__option" href="[^"]+">', html)
    assert len(links) == 2
    assert html.count("<h1") == 1
    # Effort guidance is real text, never conveyed by styling alone.
    assert "About 5–10 minutes, whenever suits you." in html
    assert "Take as long as you like" in html


def test_mode_chooser_is_listed_in_the_region_structure() -> None:
    with TestClient(app) as client:
        html = _mode_choice(client)

    assert 'class="mode-choice"' in html
    assert 'class="mode-choice__list"' in html


# --- Short Drill entry (AC-022-03) -----------------------------------------------


def test_short_drill_entry_lists_only_curated_activities() -> None:
    with TestClient(app) as client:
        response = client.get("/practice/short-drill")

    assert response.status_code == 200
    visible = unescape(response.text)
    assert "A short drill" in visible
    assert "Memory Drawing Prep — Object & Proportion Detection" in visible
    assert "Creative Writing — Concept Explanations for Poster Designs" in visible
    # Not the whole library: the reflection and colour activities stay out.
    assert "Situation Test Prep" not in visible
    assert "Color Theory" not in visible


def test_short_drill_activity_starts_the_normal_practice_page() -> None:
    with TestClient(app) as client:
        mode_page = client.get("/practice/short-drill")
        href = _activity_hrefs(mode_page.text)[0]
        practice = client.get(href)

    assert practice.status_code == 200
    assert 'id="submission-area"' in practice.text
    assert 'name="response"' in practice.text


def test_full_practice_entry_lists_the_whole_library() -> None:
    with TestClient(app) as client:
        mode_page = client.get("/practice/full-practice")
        dashboard = client.get("/")

    assert mode_page.status_code == 200
    assert len(_activity_hrefs(mode_page.text)) == len(_activity_hrefs(dashboard.text))


# --- Return path / chooser is not a gate (AC-022-02) ------------------------------


def test_chooser_offers_a_direct_path_to_the_normal_activity_library() -> None:
    with TestClient(app) as client:
        html = _mode_choice(client)

    assert 'href="/" ' in html or 'href="/">Skip this' in html
    assert "Skip this and go to explore" in html


def test_mode_pages_offer_the_way_back_to_the_choice() -> None:
    with TestClient(app) as client:
        html = client.get("/practice/short-drill").text

    assert 'href="/practice"' in html
    assert "Change practice choice" in html


def test_dashboard_keeps_the_activity_library_without_requiring_mode_selection() -> (
    None
):
    """The Explore surface remains the primary, ungated path (§9)."""
    with TestClient(app) as client:
        dashboard = client.get("/")

    assert dashboard.status_code == 200
    assert len(_activity_hrefs(dashboard.text)) >= 3
    # The chooser is a quiet invitation, not a gate.
    assert 'href="/practice"' in dashboard.text


# --- Unknown modes ----------------------------------------------------------------


def test_unknown_mode_returns_friendly_not_found() -> None:
    with TestClient(app) as client:
        response = client.get("/practice/marathon-mode")

    assert response.status_code == 404
    assert "Practice mode not found." in response.text


# --- Journey regression through both chosen paths (AC-022-05, AC-022-09) ----------


def test_short_drill_completes_the_existing_journey_and_history() -> None:
    """A completed drill is simply completed practice (SPEC-021 compatible)."""
    test_config = load_config(overrides={"practice_history_repository": "memory"})
    test_app = create_app(test_config)
    with TestClient(test_app) as client:
        mode_page = client.get("/practice/short-drill")
        href = _activity_hrefs(mode_page.text)[0]
        submitted = client.post(
            href + "/submit", data={"response": "A short noticing response."}
        )
        assert "Something you noticed" in submitted.text
        client.post("/reflect", data={"content": "I will look for one more detail."})
        completion = client.get("/complete")
        history = client.get("/history")

    assert "That's one done." in completion.text
    assert "Memory Drawing Prep" in history.text


def test_full_practice_completes_the_existing_journey() -> None:
    with TestClient(app) as client:
        mode_page = client.get("/practice/full-practice")
        href = _activity_hrefs(mode_page.text)[0]
        submitted = client.post(
            href + "/submit", data={"response": "A considered reading."}
        )
        assert "Something you noticed" in submitted.text
        client.post("/reflect", data={"content": "I will compare two elements."})
        completion = client.get("/complete")

    assert "That's one done." in completion.text


# --- Responsive and shared design system (AC-022-12) -------------------------------


def test_mode_surfaces_respect_responsive_and_motion_guidance() -> None:
    with TestClient(app) as client:
        choice = client.get("/practice")
        css = client.get("/static/css/fablit.css")

    assert 'name="viewport"' in choice.text
    assert ".mode-choice__list" in css.text
    assert "prefers-reduced-motion" in css.text
    assert ":focus-visible" in css.text
