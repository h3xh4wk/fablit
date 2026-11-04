"""Web tests for shared HTMX focus, status roles, and authoring nav (SPEC-046 Slice 1).

Covers:
- Explicit ``aria-current="page"`` on the active authoring navigation link
  across ``/authoring``, ``/authoring/candidates/{id}``, ``/authoring/guides``,
  ``/authoring/guides/{id}``, ``/authoring/pulse``, and authoring error pages,
  without prefix collisions.
- Shared ``/static/js/htmx-focus.js`` script loaded from ``base.html``.
- Status roles on live/caution panels (F-17 brief draft caution panel,
  candidate content warnings panel, and practice loading indicator).
- Explicit ``[data-focus-target]`` markers on error and outcome panels.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from fablit.config import load_config

SECRET = "ux-nav-focus-secret"
HEADERS = {"Authorization": f"Bearer {SECRET}"}
HTML_HEADERS = {**HEADERS, "Accept": "text/html"}

BRIEF = {
    "practice_area": "Visual analysis",
    "learner_context": "A learner practising close observation.",
    "purpose": "Distinguish visible evidence from interpretation.",
    "intended_mode": "short-drill",
    "response_form": "A short written observation.",
    "evaluation_intent": "Look for specific observable details.",
    "feedback_intent": "Identify useful evidence and one next step.",
    "reflection_intent": "Notice which observation strategy was useful.",
}

_AUTHORING_NAV_PATTERN = re.compile(
    r'<nav class="subnav" aria-label="Authoring navigation">(?P<body>.*?)</nav>',
    re.DOTALL,
)
_NAV_LINK_PATTERN = re.compile(
    r'<a href="(?P<href>[^"]+)"(?P<attrs>[^>]*)>(?P<label>[^<]+)</a>'
)


def _client() -> tuple[TestClient, FastAPI, Mock]:
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
    app.state.authoring_ai_provider = provider
    return TestClient(app), app, provider


def _authoring_nav_current_hrefs(html: str) -> list[str]:
    nav_match = _AUTHORING_NAV_PATTERN.search(html)
    assert nav_match is not None, "Authoring navigation block is missing"
    current: list[str] = []
    for link in _NAV_LINK_PATTERN.finditer(nav_match.group("body")):
        if 'aria-current="page"' in link.group("attrs"):
            current.append(link.group("href"))
    return current


def _create_candidate(
    client: TestClient, provider: Mock, *, include_warning: bool = False
) -> str:
    # Omit optional continuation_intent when include_warning=True so structural
    # validation produces a non-blocking warning while staying approvable.
    contract = {
        "purpose": "Distinguish visible evidence from interpretation.",
        "task": "Identify three visible details in the provided stimulus.",
        "expected_thinking": "Connect visible details directly to interpretations.",
        "response_contract": "Three concise bullet points citing evidence.",
        "evaluation_intent": "Check for concrete descriptive language.",
        "feedback_intent": "Highlight the most specific observation.",
        "reflection_intent": "Notice which visual feature guided your analysis.",
    }
    if not include_warning:
        contract["continuation_intent"] = (
            "Apply the observation method to a contrasting scene."
        )
    provider.generate.return_value = SimpleNamespace(
        candidate_data={
            "title": "Candidate for nav check",
            "description": "Describe one detail.",
            "contract": contract,
        },
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    response = client.post(
        "/authoring/generate",
        headers={**HEADERS, "Accept": "application/json"},
        json=BRIEF,
    )
    assert response.status_code == 200, response.text
    candidate_id: object = response.json()["id"]
    assert isinstance(candidate_id, str)
    return candidate_id


def test_authoring_navigation_marks_only_the_active_section_current() -> None:
    """SPEC-046 §6.4: exact active state across workspace, guides, and pulse."""
    client, _, provider = _client()

    # 1. Candidate workspace (/authoring)
    workspace = client.get("/authoring", headers=HTML_HEADERS)
    assert workspace.status_code == 200
    assert _authoring_nav_current_hrefs(workspace.text) == ["/authoring"]

    # 2. Candidate detail (/authoring/candidates/{id}) stays in workspace section
    candidate_id = _create_candidate(client, provider)
    candidate_page = client.get(
        f"/authoring/candidates/{candidate_id}", headers=HTML_HEADERS
    )
    assert candidate_page.status_code == 200
    assert _authoring_nav_current_hrefs(candidate_page.text) == ["/authoring"]

    # 3. Learning Guides list (/authoring/guides) — /authoring must NOT match
    guides_list = client.get("/authoring/guides", headers=HTML_HEADERS)
    assert guides_list.status_code == 200
    assert _authoring_nav_current_hrefs(guides_list.text) == ["/authoring/guides"]

    # 4. Learning Guide editor (/authoring/guides/{id})
    created_guide = client.post(
        "/authoring/guides",
        headers=HTML_HEADERS,
        data={
            "title": "Nav check guide",
            "summary": "Short summary.",
            "practice_area": "Visual analysis",
        },
        follow_redirects=True,
    )
    assert created_guide.status_code == 200
    assert _authoring_nav_current_hrefs(created_guide.text) == ["/authoring/guides"]

    # 5. Fashion & Design Pulse (/authoring/pulse) — /authoring must NOT match
    pulse_page = client.get("/authoring/pulse", headers=HTML_HEADERS)
    assert pulse_page.status_code == 200
    assert _authoring_nav_current_hrefs(pulse_page.text) == ["/authoring/pulse"]


def test_authoring_error_pages_preserve_section_aria_current_and_focus_target() -> None:
    """Authoring 404 responses keep section nav current and set data-focus-target."""
    client, _, _ = _client()

    missing_candidate = client.get(
        "/authoring/candidates/00000000-0000-0000-0000-000000000000",
        headers=HTML_HEADERS,
    )
    assert missing_candidate.status_code == 404
    assert _authoring_nav_current_hrefs(missing_candidate.text) == ["/authoring"]
    assert '<h1 class="display" data-focus-target>' in missing_candidate.text

    missing_guide = client.get(
        "/authoring/guides/00000000-0000-0000-0000-000000000000",
        headers=HTML_HEADERS,
    )
    assert missing_guide.status_code == 404
    assert _authoring_nav_current_hrefs(missing_guide.text) == ["/authoring/guides"]
    assert '<h1 class="display" data-focus-target>' in missing_guide.text


def test_shared_htmx_focus_script_and_learner_error_focus_target_are_rendered() -> None:
    """base.html loads htmx-focus.js and learner error pages set data-focus-target."""
    client, _, _ = _client()

    home = client.get("/")
    assert home.status_code == 200
    assert '<script src="/static/js/htmx-focus.js" defer></script>' in home.text

    script = client.get("/static/js/htmx-focus.js")
    assert script.status_code == 200
    assert "htmx:afterSettle" in script.text
    assert "preventScroll: true" in script.text

    missing_page = client.get("/activities/non-existent-activity-id")
    assert missing_page.status_code == 404
    assert '<h1 class="display" data-focus-target>' in missing_page.text


def test_candidate_warnings_and_practice_loading_indicator_carry_status_role() -> None:
    """SPEC-046 §6.5: caution panels and loading indicator expose role="status"."""
    client, _, provider = _client()

    candidate_id = _create_candidate(client, provider, include_warning=True)
    candidate_page = client.get(
        f"/authoring/candidates/{candidate_id}", headers=HTML_HEADERS
    )
    assert candidate_page.status_code == 200
    assert (
        '<div class="validation-panel validation-panel--caution" role="status">'
        in candidate_page.text
    )

    # Check the practice page loading indicator has role="status" and aria-live.
    home = client.get("/")
    href_match = re.search(r'href="(/activities/[^"]+/intention)"', home.text)
    assert href_match is not None
    activity_path = href_match.group(1).removesuffix("/intention")
    practice_page = client.get(activity_path)
    assert practice_page.status_code == 200
    assert (
        'class="htmx-indicator loading-indicator" role="status" aria-live="polite"'
        in practice_page.text
    )
