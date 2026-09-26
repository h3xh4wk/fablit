"""Web/route tests for SPEC-025 — Curated Practice Continuity.

Covers the quiet continuation surface on the completion page (§3.1, §6),
its determinism and learner independence across two anonymous browsers
(AC 10), the unchanged journey when the learner follows the continuation
(AC 5, AC 6), and the learner's freedom to ignore it (AC 7).

``TestClient`` follows redirects and keeps one cookie jar per client, so a
second anonymous learner is simulated by clearing cookies against the same
app instance — same content identities, a fresh learner identity.
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


def _activity_href_by_title(dashboard_html: str, title_fragment: str) -> str:
    """Extract one card's activity href by a fragment of its title.

    Card markup places each title inside its card, ahead of that card's
    action link, so the dashboard is split on card boundaries first.
    """
    for chunk in dashboard_html.split('class="card"'):
        if title_fragment in chunk:
            href = "/activities/" + chunk.split('href="/activities/')[1].split('"')[0]
            return href.removesuffix("/intention")
    raise AssertionError(f"no dashboard card found for: {title_fragment}")


def _submit_and_reflect(client: TestClient, href: str, response: str) -> None:
    client.post(href + "/submit", data={"response": response})
    client.post("/reflect", data={"content": "I will look for balance next time."})


def _complete_first_practice(client: TestClient, response: str) -> str:
    """Complete one journey through the web layer; return the completion page."""
    dashboard = client.get("/")
    href = _first_activity_href(dashboard.text)
    _submit_and_reflect(client, href, response)
    completion = client.get("/complete")
    assert completion.status_code == 200
    return completion.text


def _continuation_href(completion_html: str) -> str:
    """Extract the continuation's activity href from the completion page.

    The continuation action leads through the SPEC-026 intention prompt;
    return the bare activity href so journeys can drive either surface.
    """
    section = completion_html.split('class="continuation"')[1]
    for line in section.splitlines():
        if 'href="/activities/' in line:
            href = line.split('href="')[1].split('"')[0]
            return href.removesuffix("/intention")
    raise AssertionError("no continuation link found on the completion page")


# --- The continuation surface (AC 1, §3.1, §6) ----------------------------------


def test_completion_shows_the_curated_continuation_for_an_authored_activity() -> None:
    with _client() as client:
        html = _complete_first_practice(
            client, "The contrast between the subject and the background stands out."
        )

    assert "Continue the practice" in html
    assert "Try the next practice" in html
    assert "You just analysed how a composition works." in html
    assert "Visual Interpretation — Reading a Street Scene" in html


def test_completion_without_an_authored_transition_shows_no_continuation() -> None:
    with _client() as client:
        # Complete the library's one unauthored activity (SPEC-025 §4).
        dashboard = client.get("/")
        href = _activity_href_by_title(dashboard.text, "Situation Test Prep")
        _submit_and_reflect(client, href, "The hardest part was the time pressure.")
        html = client.get("/complete").text

    assert "Continue the practice" not in html
    assert "That's one done." in html


def test_continuation_copy_makes_no_recommendation_claims() -> None:
    with _client() as client:
        html = _complete_first_practice(
            client, "The contrast between the subject and the background stands out."
        )

    lowered = html.lower()
    for forbidden in ("recommended", "best for you", "personalized", "streak"):
        assert forbidden not in lowered, forbidden


# --- Determinism and learner independence (AC 2, AC 10) --------------------------


def test_a_second_browser_receives_the_same_content_transition() -> None:
    """AC 10: another learner gets the same transition with no shared state."""
    with _client() as client:
        first_html = _complete_first_practice(
            client, "The contrast between the subject and the background stands out."
        )
        first_href = _continuation_href(first_html)

        # A cleared cookie jar is a brand-new anonymous learner on the same
        # content: no shared journey state, no shared history.
        client.cookies.clear()
        second_html = _complete_first_practice(
            client, "A completely different response about the same image."
        )
        second_href = _continuation_href(second_html)

        history = client.get("/history").text

    assert first_href == second_href
    assert "Visual Interpretation — Reading a Street Scene" in second_html
    # The second learner's history holds only their own single completion.
    assert history.count('href="/history/') == 1


def test_the_same_activity_yields_the_same_transition_on_repeat_practice() -> None:
    """AC 2: deterministic for the same source activity and configuration."""
    with _client() as client:
        dashboard = client.get("/")
        href = _first_activity_href(dashboard.text)
        _submit_and_reflect(client, href, "First considered response.")
        first_href = _continuation_href(client.get("/complete").text)

        _submit_and_reflect(client, href, "Second considered response.")
        second_html = client.get("/complete").text

    assert "Continue the practice" in second_html
    assert _continuation_href(second_html) == first_href


# --- Following the continuation (AC 5, AC 6) -------------------------------------


def test_following_the_continuation_opens_the_existing_practice_journey() -> None:
    with _client() as client:
        html = _complete_first_practice(
            client, "The contrast between the subject and the background stands out."
        )
        href = _continuation_href(html)

        practice_page = client.get(href)
        client.post(
            href + "/submit",
            data={"response": "The crowd's movement suggests a morning rush."},
        )
        client.post("/reflect", data={"content": "I will tie claims to details."})
        completion = client.get("/complete").text
        history = client.get("/history").text

    assert practice_page.status_code == 200
    assert "Reading a Street Scene" in practice_page.text
    assert "That's one done." in completion
    # Both the original practice and the followed continuation are recorded.
    # (Raw HTML escapes "&", so title fragments avoid it.)
    assert "Composition Analysis" in history
    assert "Reading a Street Scene" in history


# --- The learner can ignore the continuation (AC 7) ------------------------------


def test_existing_navigation_remains_available_alongside_the_continuation() -> None:
    with _client() as client:
        html = _complete_first_practice(
            client, "The contrast between the subject and the background stands out."
        )

    assert 'href="/history"' in html
    assert 'href="/"' in html
    assert "Back to explore" in html


def test_the_continuation_is_a_single_quiet_invitation() -> None:
    with _client() as client:
        html = _complete_first_practice(
            client, "The contrast between the subject and the background stands out."
        )

    # The continuation is an invitation, not a forced step: the completion
    # page renders fully whether or not the learner acts on it.
    assert html.count("Try the next practice") == 1
    assert "That's one done." in html
