"""AI-assisted brief drafting in the authoring workspace (SPEC-040).

The workspace must let an author start from partial notes, review an editable
draft whose provenance is visible, regenerate one field without losing the
rest, and keep all their work when the provider fails. Every test drives the
real HTML an author sees and uses a deterministic provider: no live call is
made in the ordinary suite.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from fastapi.testclient import TestClient

from app.main import create_app
from fablit.application import AuthoringProviderError, FakeAuthoringProvider
from fablit.config import load_config

SECRET = "authoring-brief-draft-secret"
HEADERS = {"Authorization": f"Bearer {SECRET}"}
HTML_HEADERS = {**HEADERS, "Accept": "text/html"}

NOTES = (
    "Year 10 group, photos from the bulletin board: they compared two posters "
    "and argued about which was more persuasive, but stayed on the colours."
)

DRAFT_OUTPUT: dict[str, Any] = {
    "fields": {
        "practice_area": {"value": "Visual analysis", "source": "notes"},
        "learner_context": {
            "value": "Learners comparing two posters.",
            "source": "notes",
        },
        "purpose": {
            "value": "Distinguish visible evidence from interpretation.",
            "source": "suggested",
        },
        "intended_mode": {"value": "short-drill", "source": "suggested"},
        "response_form": {
            "value": "A short written comparison.",
            "source": "suggested",
        },
        "evaluation_intent": {
            "value": "Look for claims tied to visible detail.",
            "source": "suggested",
        },
        "feedback_intent": {
            "value": "Name one specific piece of evidence and one next step.",
            "source": "suggested",
        },
        "reflection_intent": {
            "value": "Notice which comparison strategy helped.",
            "source": "suggested",
        },
        "examination_context": {
            "value": "A timed written response.",
            "source": "notes",
        },
    },
    "assumptions": ["The two posters are comparable in style."],
}

CURRENT_BRIEF = {
    "practice_area": "My typed area",
    "learner_context": "My typed learners.",
    "purpose": "My typed purpose.",
    "intended_mode": "full-practice",
    "response_form": "My typed response.",
    "evaluation_intent": "My typed evaluation.",
    "feedback_intent": "My typed feedback.",
    "reflection_intent": "My typed reflection.",
}


def _client(
    *,
    brief_output: Mapping[str, Any] | None = None,
    brief_error: Exception | None = None,
) -> tuple[TestClient, Any, FakeAuthoringProvider]:
    app = create_app(
        load_config(
            overrides={
                "environment": "testing",
                "authoring_secret": SECRET,
                "practice_history_repository": "memory",
            }
        )
    )
    provider = FakeAuthoringProvider(
        candidate_data={
            "title": "Drafted practice",
            "description": "Describe one visible detail.",
            "contract": {
                "purpose": "Distinguish visible evidence from interpretation.",
                "task": "Describe one visible detail.",
                "expected_thinking": "Connect detail to a claim.",
                "response_contract": "A short written comparison.",
                "evaluation_intent": "Look for claims tied to visible detail.",
                "feedback_intent": "Name one specific piece of evidence.",
                "reflection_intent": "Notice which strategy helped.",
            },
        },
        brief_output=DRAFT_OUTPUT if brief_output is None else brief_output,
        brief_error=brief_error,
    )
    app.state.authoring_ai_provider = provider
    # Brief drafting and candidate generation never need image search.
    app.state.authoring_image_search = None
    return TestClient(app), app, provider


def _workspace(client: TestClient, **params: str) -> str:
    response = client.get("/authoring", headers=HTML_HEADERS, params=params)
    assert response.status_code == 200, response.text
    return response.text


def _field_value(html: str, name: str) -> str | None:
    """Read a submitted field back out of the rendered form."""
    textarea = re.search(
        rf'<textarea[^>]*name="{name}"[^>]*>(?P<value>.*?)</textarea>',
        html,
        re.DOTALL,
    )
    if textarea:
        return textarea.group("value")
    field = re.search(rf'<(?:input)[^>]*name="{name}"[^>]*>', html)
    if field:
        value = re.search(r'value="([^"]*)"', field.group(0))
        return value.group(1) if value else None
    return None


def _selected_option(html: str, name: str) -> str | None:
    select = re.search(
        rf'<select[^>]*name="{name}"[^>]*>(?P<body>.*?)</select>', html, re.DOTALL
    )
    assert select, f"select {name} is missing"
    selected = re.search(r'<option value="([^"]*)"\s+selected', select.group("body"))
    return selected.group(1) if selected else None


def _draft(client: TestClient, data: Mapping[str, str]) -> Any:
    return client.post("/authoring/brief/draft", headers=HTML_HEADERS, data=data)


# --- Entry point --------------------------------------------------------------


def test_workspace_offers_the_help_me_write_the_brief_action() -> None:
    client, _, _ = _client()

    html = _workspace(client)

    assert "Help me write the brief" in html
    assert 'name="notes"' in html
    assert 'formaction="/authoring/brief/draft"' in html
    assert "Draft the brief" in html
    # The reviewed brief still continues through the existing action only.
    assert 'action="/authoring/generate"' in html
    # A second click is dropped while the draft is in flight.
    assert 'hx-sync="closest form:drop"' in html


# --- Successful drafting ------------------------------------------------------


def test_partial_notes_produce_an_editable_draft_with_visible_provenance() -> None:
    client, app, provider = _client()

    response = _draft(client, {"notes": NOTES})

    assert response.status_code == 200, response.text
    html = response.text
    assert _field_value(html, "practice_area") == "Visual analysis"
    assert _field_value(html, "learner_context") == "Learners comparing two posters."
    assert _field_value(html, "evaluation_intent") == (
        "Look for claims tied to visible detail."
    )
    assert _selected_option(html, "intended_mode") == "short-drill"

    # The author can tell facts, suggestions, and assumptions apart.
    assert "From your notes" in html
    assert "AI suggestion" in html
    assert "Assumption to confirm" in html
    assert "The two posters are comparable in style." in html
    # Generated examination detail is never presented as fact.
    assert (
        "Fablit cannot confirm official examination or institutional requirements."
        in (html)
    )

    # The notes are still there, and every value stays editable.
    assert NOTES in html
    assert 'name="practice_area"' in html
    practice_area = re.search(r'<input[^>]*name="practice_area"[^>]*>', html)
    assert practice_area, "practice_area was rendered as an editable input"
    assert "required" in practice_area.group(0)

    assert provider.brief_calls[0].notes == NOTES
    assert provider.brief_calls[0].target_field is None
    # Drafting created no candidate and made no candidate-generation call.
    assert provider.calls == []
    assert app.state.authoring_candidate_store.list() == ()


def test_a_short_topic_is_a_valid_starting_point() -> None:
    client, _, provider = _client()

    response = _draft(client, {"notes": "still life drawing"})

    assert response.status_code == 200, response.text
    assert provider.brief_calls[0].notes == "still life drawing"


# --- Rejected input -----------------------------------------------------------


def test_empty_notes_are_rejected_without_calling_the_provider() -> None:
    client, _, provider = _client()

    response = _draft(client, {"notes": "   ", "practice_area": "Existing area"})

    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert "Add some notes" in response.text
    assert "Existing area" in response.text
    assert provider.brief_calls == []


def test_oversized_notes_are_rejected_without_calling_the_provider() -> None:
    client, _, provider = _client()

    response = _draft(client, {"notes": "x" * 8001})

    assert response.status_code == 422
    assert "longer than the supported 8000 characters" in response.text
    assert provider.brief_calls == []


# --- Failure recovery ---------------------------------------------------------


def test_provider_failure_keeps_notes_and_current_values_for_retry() -> None:
    client, app, provider = _client(brief_error=AuthoringProviderError("provider down"))

    response = _draft(client, {"notes": NOTES, "practice_area": "Typed by the author"})

    assert response.status_code == 502
    assert 'role="alert"' in response.text
    assert "temporarily unavailable" in response.text
    assert "try again" in response.text
    assert NOTES in response.text
    assert "Typed by the author" in response.text
    assert "Draft the brief" in response.text

    # The author can retry and get the draft without retyping anything.
    app.state.authoring_ai_provider = FakeAuthoringProvider(brief_output=DRAFT_OUTPUT)
    retry = _draft(
        client,
        {"notes": NOTES, "practice_area": "Typed by the author", "replace": "1"},
    )
    assert retry.status_code == 200
    assert _field_value(retry.text, "practice_area") == "Visual analysis"
    assert NOTES in retry.text


def test_unconfigured_drafting_preserves_the_notes() -> None:
    client, app, _ = _client()
    app.state.authoring_ai_provider = None

    response = _draft(client, {"notes": NOTES})

    assert response.status_code == 503
    assert "not configured" in response.text
    assert NOTES in response.text


def test_malformed_provider_output_changes_nothing() -> None:
    client, app, provider = _client(brief_output={"fields": "not-a-mapping"})

    response = _draft(client, {"notes": NOTES, "practice_area": "Typed by the author"})

    assert response.status_code == 502
    assert "could not be used" in response.text
    assert NOTES in response.text
    assert "Typed by the author" in response.text
    assert app.state.authoring_candidate_store.list() == ()
    assert provider.calls == []


def test_provider_details_are_never_exposed_on_failure() -> None:
    client, _, _ = _client(
        brief_error=RuntimeError("Sensitive provider response: api-key-leak-attempt")
    )

    response = _draft(client, {"notes": NOTES})

    assert response.status_code == 502
    assert "api-key-leak-attempt" not in response.text
    assert "RuntimeError" not in response.text


# --- Regeneration -------------------------------------------------------------


def test_single_field_regeneration_preserves_every_other_value_and_edit() -> None:
    client, _, provider = _client(
        brief_output={
            "fields": {
                "feedback_intent": {
                    "value": "Ask what the evidence shows and what to try next.",
                    "source": "suggested",
                },
                "practice_area": {"value": "Should not be used", "source": "suggested"},
            }
        }
    )

    response = _draft(
        client,
        {**CURRENT_BRIEF, "notes": NOTES, "field": "feedback_intent"},
    )

    assert response.status_code == 200, response.text
    html = response.text
    assert _field_value(html, "feedback_intent") == (
        "Ask what the evidence shows and what to try next."
    )
    assert _field_value(html, "practice_area") == "My typed area"
    assert _field_value(html, "purpose") == "My typed purpose."
    assert _selected_option(html, "intended_mode") == "full-practice"
    assert "Your other fields are unchanged." in html

    call = provider.brief_calls[0]
    assert call.target_field == "feedback_intent"
    assert call.current_values["practice_area"] == "My typed area"
    assert call.current_values["feedback_intent"] == "My typed feedback."


def test_whole_brief_draft_keeps_existing_values_until_replacement_is_chosen() -> None:
    client, _, _ = _client()

    kept = _draft(client, {**CURRENT_BRIEF, "notes": NOTES})

    assert kept.status_code == 200
    assert "Kept your existing values" in kept.text
    assert "Replace my current field values" in kept.text
    assert _field_value(kept.text, "practice_area") == "My typed area"
    assert _field_value(kept.text, "purpose") == "My typed purpose."
    assert NOTES in kept.text

    replaced = _draft(client, {**CURRENT_BRIEF, "notes": NOTES, "replace": "1"})

    assert replaced.status_code == 200
    assert "Kept your existing values" not in replaced.text
    assert _field_value(replaced.text, "practice_area") == "Visual analysis"
    assert _field_value(replaced.text, "purpose") == (
        "Distinguish visible evidence from interpretation."
    )
    # Notes survive replacement, so the original source is never discarded.
    assert NOTES in replaced.text


def test_unsupported_controlled_value_keeps_the_existing_option() -> None:
    client, _, _ = _client(
        brief_output={
            "fields": {
                "practice_area": {"value": "Visual analysis", "source": "notes"},
                "intended_mode": {"value": "lecture", "source": "suggested"},
            }
        }
    )

    response = _draft(client, {**CURRENT_BRIEF, "notes": NOTES, "replace": "1"})

    assert response.status_code == 200
    # The out-of-range suggestion is refused; the existing option stays put.
    assert _selected_option(response.text, "intended_mode") == "full-practice"
    assert _field_value(response.text, "practice_area") == "Visual analysis"
    assert "not one of the existing options" in response.text


# --- Authorisation, JSON, and the unchanged lifecycle ------------------------


def test_unauthorised_request_never_calls_the_drafting_provider() -> None:
    client, _, provider = _client()

    response = client.post("/authoring/brief/draft", data={"notes": NOTES})

    assert response.status_code == 401
    assert provider.brief_calls == []

    api_response = client.post(
        "/authoring/brief/draft",
        headers={"Accept": "application/json"},
        json={"notes": NOTES},
    )
    assert api_response.status_code == 401
    assert api_response.json()["error"] == "Unauthorized"
    assert provider.brief_calls == []


def test_json_clients_receive_the_structured_draft() -> None:
    client, _, _ = _client()

    response = client.post(
        "/authoring/brief/draft",
        headers={**HEADERS, "Accept": "application/json"},
        json={"notes": NOTES, "practice_area": ""},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["notes"] == NOTES
    assert body["fields"]["practice_area"] == "Visual analysis"
    assert body["sources"]["practice_area"] == "notes"
    assert body["sources"]["purpose"] == "suggested"
    assert body["assumptions"] == ["The two posters are comparable in style."]
    assert "practice_area" in body["applied"]


def test_reviewed_draft_continues_through_the_existing_generation_flow() -> None:
    client, app, provider = _client()

    drafted = _draft(client, {"notes": NOTES})
    assert drafted.status_code == 200
    assert provider.calls == []
    assert app.state.authoring_candidate_store.list() == ()

    values = {
        name: _field_value(drafted.text, name) or ""
        for name in (
            "practice_area",
            "learner_context",
            "purpose",
            "response_form",
            "evaluation_intent",
            "feedback_intent",
            "reflection_intent",
        )
    }
    generated = client.post(
        "/authoring/generate",
        headers={**HEADERS, "Accept": "application/json"},
        json={**values, "intended_mode": "short-drill", "notes": NOTES},
    )

    assert generated.status_code == 200, generated.text
    assert generated.json()["title"] == "Drafted practice"
    assert len(provider.calls) == 1
    assert len(app.state.authoring_candidate_store.list()) == 1
