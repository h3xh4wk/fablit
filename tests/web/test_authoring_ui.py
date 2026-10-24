"""Web tests for the authoring workspace UI (SPEC-032 §8–9, SPEC-035 §5).

The workspace and the candidate page have one job each: the workspace takes a
brief and shows the queue of candidates, and a candidate page shows where that
candidate stands and which single action moves it forward. These tests drive
the real HTML an author sees, so a regression in the split — the brief form
reappearing on a candidate page, counts drifting from the rows, or the queue
no longer being scannable at scale — fails here rather than in review.
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

SECRET = "authoring-ui-secret"
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

REQUIRED_FIELDS = (
    "practice_area",
    "learner_context",
    "purpose",
    "intended_mode",
    "response_form",
    "evaluation_intent",
    "feedback_intent",
    "reflection_intent",
)

OPTIONAL_FIELDS = (
    "examination_context",
    "primary_creative_thinking_lens",
    "constraints",
    "stimulus_requirements",
    "continuation_intent",
)

FILTER_LABELS = (
    "All",
    "Awaiting decision",
    "Ready to publish",
    "In the learner library",
    "Withdrawn",
    "Rejected",
)

_FIELD_TAG = '<(?:input|textarea|select)\\b[^>]*name="{name}"[^>]*>'
_FILTER_ROW = re.compile(
    r'<a class="filter-tabs__link" href="(?P<url>[^"]+)"[^>]*>\s*'
    r"(?P<label>[^<]+?)\s*"
    r'<span class="filter-tabs__count">(?P<count>\d+)</span>',
)


def _complete_contract() -> dict[str, str]:
    return {
        "purpose": "Distinguish visible evidence from interpretation.",
        "task": "Identify three visible details in the provided stimulus.",
        "expected_thinking": "Connect visible details directly to interpretations.",
        "response_contract": "Three concise bullet points citing evidence.",
        "evaluation_intent": "Check for concrete descriptive language.",
        "feedback_intent": "Highlight the most specific observation.",
        "reflection_intent": "Notice which visual feature guided your analysis.",
        "continuation_intent": "Apply the observation method to a contrasting scene.",
    }


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


def _set_provider_result(
    provider: Mock,
    *,
    title: str,
    generated_at: datetime | None = None,
    contract: dict[str, str] | None = None,
) -> None:
    provider.generate.return_value = SimpleNamespace(
        candidate_data={
            "title": title,
            "description": "Describe one detail.",
            "contract": _complete_contract() if contract is None else contract,
        },
        provider="test-provider",
        model="test-model",
        generated_at=generated_at or datetime(2026, 10, 11, 9, tzinfo=UTC),
    )


def _generate(client: TestClient, provider: Mock, title: str, **brief: object) -> str:
    _set_provider_result(provider, title=title)
    response = client.post(
        "/authoring/generate",
        headers={**HEADERS, "Accept": "application/json"},
        json={**BRIEF, **brief},
    )
    assert response.status_code == 200, response.text
    candidate_id: object = response.json()["id"]
    assert isinstance(candidate_id, str)
    return candidate_id


def _workspace(client: TestClient, **params: str) -> str:
    response = client.get("/authoring", headers=HTML_HEADERS, params=params)
    assert response.status_code == 200, response.text
    return response.text


def _candidate_page(client: TestClient, candidate_id: str) -> str:
    response = client.get(f"/authoring/candidates/{candidate_id}", headers=HTML_HEADERS)
    assert response.status_code == 200, response.text
    return response.text


def _filter_counts(html: str) -> dict[str, int]:
    return {
        match.group("label"): int(match.group("count"))
        for match in _FILTER_ROW.finditer(html)
    }


def _active_filter_url(html: str) -> str:
    match = re.search(
        r'<a class="filter-tabs__link" href="(?P<url>[^"]+)"\s+aria-current="true"',
        html,
    )
    assert match, "no filter tab is marked as current"
    url: str = match.group("url")
    return url


# --- Brief form: grouped, and honest about what is required ------------------


def test_workspace_groups_the_brief_into_three_steps_plus_optionals() -> None:
    client, _, _ = _client()
    html = _workspace(client)

    assert "1. What the practice is for" in html
    assert "2. How the learner will work" in html
    assert "3. How the work will be reviewed with the learner" in html
    assert "Optional context and constraints" in html
    assert html.count('class="form-section"') == 3


def test_required_fields_are_marked_and_optional_fields_are_collapsed() -> None:
    client, _, _ = _client()
    html = _workspace(client)

    for name in REQUIRED_FIELDS:
        tag = re.search(_FIELD_TAG.format(name=name), html)
        assert tag, f"required field {name} is missing"
        assert "required" in tag.group(0), f"{name} should be marked required"

    optional_block = re.search(
        r'<details class="form-optional-group"(?P<attrs>[^>]*)>(?P<body>.*?)</details>',
        html,
        re.DOTALL,
    )
    assert optional_block, "the optional brief fields are not in a disclosure group"
    # Collapsed by default, and with no brief values to preserve.
    assert "open" not in optional_block.group("attrs")

    for name in OPTIONAL_FIELDS:
        tag = re.search(_FIELD_TAG.format(name=name), html)
        assert tag, f"optional field {name} is missing"
        assert "required" not in tag.group(0), f"{name} must not be required"
        assert name in optional_block.group("body"), f"{name} should be collapsed"


def test_required_markers_match_the_number_of_required_fields() -> None:
    client, _, _ = _client()
    html = _workspace(client)

    assert html.count('class="form-required"') == len(REQUIRED_FIELDS)


def test_invalid_brief_returns_the_form_with_the_answers_preserved() -> None:
    client, _, _ = _client()
    response = client.post(
        "/authoring/generate",
        headers=HTML_HEADERS,
        data={**BRIEF, "purpose": ""},
    )

    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert 'value="Visual analysis"' in response.text
    assert "Distinguish visible evidence from interpretation." not in response.text


def test_provider_failure_returns_the_brief_with_every_answer_preserved() -> None:
    """FIX-9: a failed generation must not cost the author their brief."""
    client, _, provider = _client()
    provider.generate.side_effect = RuntimeError(
        "Sensitive provider response: api-key-leak-attempt"
    )
    optional_values = {
        "examination_context": "A timed examination response.",
        "primary_creative_thinking_lens": "Observe",
        "constraints": "Use one paragraph.",
        "stimulus_requirements": "Use an image of a public place.",
        "continuation_intent": "Extend the same observation.",
    }

    response = client.post(
        "/authoring/generate",
        headers=HTML_HEADERS,
        data={**BRIEF, **optional_values},
    )

    assert response.status_code == 502
    assert 'role="alert"' in response.text
    assert "temporarily unavailable" in response.text
    assert "try again" in response.text

    # Required and optional answers are all still in the form.
    for name, value in BRIEF.items():
        if name == "intended_mode":
            continue
        assert value in response.text, f"submitted value {value!r} was lost"
    for value in optional_values.values():
        assert value in response.text, f"submitted value {value!r} was lost"
    assert '<option value="short-drill" selected>' in response.text
    assert '<option value="Observe" selected>' in response.text

    # Optional context is expanded, because it holds values to preserve.
    optional_block = re.search(
        r'<details class="form-optional-group"(?P<attrs>[^>]*)>',
        response.text,
    )
    assert optional_block, "the optional brief fields are not in a disclosure group"
    assert "open" in optional_block.group("attrs")

    # The retry is offered without leaking the provider's own message.
    assert "Generate candidate practice" in response.text
    assert "api-key-leak-attempt" not in response.text
    assert "RuntimeError" not in response.text


def test_unconfigured_generation_keeps_the_brief_in_the_browser() -> None:
    """FIX-9: a configuration failure is explained without losing answers."""
    client, app, _ = _client()
    app.state.authoring_ai_provider = None

    response = client.post(
        "/authoring/generate",
        headers=HTML_HEADERS,
        data=BRIEF,
    )

    assert response.status_code == 503
    assert 'role="alert"' in response.text
    assert "not configured" in response.text
    assert 'value="Visual analysis"' in response.text
    assert "Distinguish visible evidence from interpretation." in response.text


def test_authoring_pages_carry_no_inline_styles() -> None:
    """Styling lives in the stylesheet, not in markup attributes."""
    client, _, provider = _client()
    candidate_id = _generate(client, provider, "Inline style guard")

    login = client.get("/authoring/login")
    assert login.status_code == 200, login.text
    assert 'style="' not in login.text
    assert 'style="' not in _workspace(client)
    assert 'style="' not in _candidate_page(client, candidate_id)


# --- Queue: filterable, counted, newest first -------------------------------


def test_queue_counts_and_filters_cover_every_candidate_exactly_once() -> None:
    client, _, provider = _client()
    _generate(client, provider, "Awaiting practice")
    approved = _generate(client, provider, "Approved practice")
    rejected = _generate(client, provider, "Rejected practice")
    client.post(f"/authoring/candidates/{approved}/approve", headers=HEADERS)
    client.post(f"/authoring/candidates/{rejected}/reject", headers=HEADERS)

    html = _workspace(client)
    counts = _filter_counts(html)

    assert list(counts) == list(FILTER_LABELS)
    assert counts["All"] == 3
    assert counts["Awaiting decision"] == 1
    assert counts["Ready to publish"] == 1
    assert counts["Rejected"] == 1
    assert counts["In the learner library"] == 0
    assert counts["Withdrawn"] == 0
    assert sum(counts[key] for key in counts if key != "All") == counts["All"]

    for title in ("Awaiting practice", "Approved practice", "Rejected practice"):
        assert title in html

    assert _active_filter_url(html) == "/authoring"

    filtered = _workspace(client, stage="awaiting")
    assert "Awaiting practice" in filtered
    assert "Approved practice" not in filtered
    assert "Rejected practice" not in filtered
    assert _active_filter_url(filtered) == "/authoring?stage=awaiting"


def test_queue_lists_newest_first() -> None:
    client, _, provider = _client()
    for title, generated_at in (
        ("Oldest practice", datetime(2026, 10, 1, 9, tzinfo=UTC)),
        ("Middle practice", datetime(2026, 10, 5, 9, tzinfo=UTC)),
        ("Newest practice", datetime(2026, 10, 9, 9, tzinfo=UTC)),
    ):
        _set_provider_result(provider, title=title, generated_at=generated_at)
        response = client.post("/authoring/generate", headers=HEADERS, json=BRIEF)
        assert response.status_code == 200, response.text

    html = _workspace(client)

    assert html.index("Newest practice") < html.index("Middle practice")
    assert html.index("Middle practice") < html.index("Oldest practice")


def test_queue_rows_link_to_their_candidate_pages() -> None:
    client, _, provider = _client()
    candidate_id = _generate(client, provider, "Linked practice")

    html = _workspace(client)

    assert f'href="/authoring/candidates/{candidate_id}"' in html


def test_empty_filter_and_unknown_filter_are_handled() -> None:
    client, _, provider = _client()
    _generate(client, provider, "Only practice")

    empty = _workspace(client, stage="withdrawn")
    assert "No candidates match this stage." in empty
    assert 'href="/authoring"' in empty
    assert "Only practice" not in empty

    unknown = _workspace(client, stage="not-a-stage")
    assert "Only practice" in unknown


def test_workspace_without_candidates_shows_an_empty_state() -> None:
    client, _, _ = _client()

    html = _workspace(client)

    assert "Nothing generated yet" in html
    assert 'class="filter-tabs"' not in html


# --- Candidate page: one candidate, one next step ---------------------------


def test_candidate_page_shows_the_stage_and_only_the_available_action() -> None:
    client, _, provider = _client()
    candidate_id = _generate(client, provider, "Staged practice")

    awaiting = _candidate_page(client, candidate_id)
    assert "Where this candidate stands" in awaiting
    assert "Human decision" in awaiting
    assert "Approve for Library" in awaiting
    assert "Reject Candidate" in awaiting
    assert "Not published" in awaiting
    assert "Publish to Learner Library" not in awaiting

    client.post(f"/authoring/candidates/{candidate_id}/approve", headers=HEADERS)
    approved = _candidate_page(client, candidate_id)
    assert "Publish to Learner Library" in approved
    assert "Approve for Library" not in approved
    assert "Reject Candidate" not in approved

    client.post(f"/authoring/candidates/{candidate_id}/publish", headers=HEADERS)
    published = _candidate_page(client, candidate_id)
    assert "Published to Learner Library" in published
    assert "Withdraw from Library" in published
    assert "Publish to Learner Library" not in published

    client.post(f"/authoring/candidates/{candidate_id}/withdraw", headers=HEADERS)
    withdrawn = _candidate_page(client, candidate_id)
    assert "Withdrawn from the learner library" in withdrawn
    assert "Publish to Learner Library" in withdrawn


def test_candidate_page_keeps_the_brief_and_the_edit_form_separate() -> None:
    client, _, provider = _client()
    candidate_id = _generate(client, provider, "Separated practice")

    html = _candidate_page(client, candidate_id)

    # The brief is read back here; the brief *form* belongs to the workspace.
    assert "Authoring brief" in html
    assert "A learner practising close observation." in html
    assert 'name="practice_area"' not in html
    assert 'action="/authoring/generate"' not in html
    # Editing the draft is available, labelled as its own step.
    assert 'action="/authoring/candidates/' in html
    assert 'name="description"' in html
    assert 'href="/authoring"' in html


def test_generate_renders_the_candidate_page_rather_than_the_workspace() -> None:
    client, _, provider = _client()
    _set_provider_result(provider, title="Split practice")

    response = client.post("/authoring/generate", headers=HTML_HEADERS, data=BRIEF)

    assert response.status_code == 200, response.text
    assert "Split practice" in response.text
    assert "Where this candidate stands" in response.text
    assert 'name="practice_area"' not in response.text


def test_publication_failure_is_explained_on_the_candidate_page() -> None:
    client, _, provider = _client()
    candidate_id = _generate(client, provider, "Unapproved practice")

    response = client.post(
        f"/authoring/candidates/{candidate_id}/publish", headers=HTML_HEADERS
    )

    assert response.status_code == 409
    assert "not approved" in response.text
    assert 'role="alert"' in response.text
    # The author stays where the action was, not back at the queue.
    assert "Where this candidate stands" in response.text
    assert 'name="practice_area"' not in response.text


def test_conflicting_review_transition_explains_itself_on_the_candidate_page() -> None:
    """A refused review transition stays on the page the author was using."""
    client, _, provider = _client()
    candidate_id = _generate(client, provider, "Twice approved practice")
    client.post(f"/authoring/candidates/{candidate_id}/approve", headers=HEADERS)

    response = client.post(
        f"/authoring/candidates/{candidate_id}/approve", headers=HTML_HEADERS
    )

    assert response.status_code == 409
    assert "already approved" in response.text
    assert "Where this candidate stands" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_conflicting_review_transition_stays_json_for_api_clients() -> None:
    """The explicit JSON contract is unchanged."""
    client, _, provider = _client()
    candidate_id = _generate(client, provider, "API approved practice")
    client.post(f"/authoring/candidates/{candidate_id}/approve", headers=HEADERS)

    response = client.post(
        f"/authoring/candidates/{candidate_id}/approve",
        headers={**HEADERS, "Accept": "application/json"},
    )

    assert response.status_code == 409
    assert "already approved" in response.json()["detail"]
