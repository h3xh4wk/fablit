"""Web workflow tests for AI-assisted practice authoring (SPEC-032).

These exercise the authoring workflow through the SEC-001-protected routes:
structured brief generation, validation gating, the explicit human approval
gate, editing/rejection, and the separation of approved content from pending
candidates. Generation works with no AI provider configured, so AI
availability never gates content creation.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient

from app.main import create_app
from fablit.application import FakeAuthoringProvider, PracticeMode
from fablit.config import AppConfig, load_config
from fablit.platform.authoring_auth import AUTHORING_COOKIE_NAME

SECRET = "spec-032-authoring-secret-7"

#: A complete, SPEC-029-compatible provider output for the fake provider.
_PROVIDER_OUTPUT: dict[str, Any] = {
    "title": "Reading Composition — Observe Practice",
    "description": "A generated practice on reading composition.",
    "contract": {
        "purpose": "Practise reading structure in a composition.",
        "task": "Describe the dominant structure you notice.",
        "expected_thinking": "Move from observation to a reasoned claim.",
        "response_contract": "A short evidence-based paragraph.",
        "evaluation_intent": "Look for evidence tied to the composition.",
        "feedback_intent": "Name one strength, why it matters, one next move.",
        "reflection_intent": "Notice how you approached the reading.",
        "continuation_intent": "Try a related practice on the same move.",
    },
}

_BRIEF_FORM: dict[str, str] = {
    "practice_area": "Visual Analysis",
    "practice_purpose": "Practise reading structure in a composition.",
    "task": "Describe the dominant structure you notice.",
    "response_form": "A short evidence-based paragraph.",
    "primary_capability": "Observe",
    "practice_mode": PracticeMode.FULL_PRACTICE.value,
    "learner_context": "Design aspirants preparing a portfolio.",
    "evaluation_intent": "Look for evidence tied to the composition.",
    "feedback_intent": "Name one strength, why it matters, and one next move.",
    "reflection_intent": "Notice how you approached the reading.",
    "continuation_intent": "Try a related practice on the same thinking move.",
}


def _client(*, provider: FakeAuthoringProvider | None = None) -> TestClient:
    config: AppConfig = load_config(
        overrides={
            "environment": "development",
            "authoring_secret": SECRET,
        }
    )
    app = create_app(config)
    if provider is not None:
        app.state.authoring_ai_provider = provider
    client = TestClient(
        app, base_url="https://testserver", raise_server_exceptions=False
    )
    client.cookies.set(AUTHORING_COOKIE_NAME, SECRET)
    return client


def _generate(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/authoring/generate",
        json=_BRIEF_FORM,
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


# --- Workspace rendering ------------------------------------------------------


def test_workspace_renders_candidate_and_approved_sections() -> None:
    client = _client()
    response = client.get("/authoring")
    assert response.status_code == 200
    assert "Candidate Queue" in response.text
    assert "Approved for Curated Library" in response.text


def test_html_generation_shows_the_structured_contract_and_validation() -> None:
    client = _client()
    response = client.post(
        "/authoring/generate",
        data=_BRIEF_FORM,
        headers={"Accept": "text/html"},
    )
    assert response.status_code == 200
    assert "SPEC-029 Practice Content Contract" in response.text
    assert "Describe the dominant structure you notice." in response.text
    assert "passed the structural and feedback validation gate" in response.text


# --- Provider-free generation -------------------------------------------------


def test_generation_without_a_provider_still_produces_an_approvable_candidate() -> None:
    client = _client()
    candidate = _generate(client)

    assert candidate["status"] == "candidate"
    assert candidate["validation"]["is_approvable"] is True
    assert (
        candidate["contract"]["task"] == "Describe the dominant structure you notice."
    )


def test_generated_candidate_is_not_automatically_approved() -> None:
    client = _client()
    candidate = _generate(client)
    assert candidate["is_approved"] is False

    approved = client.get(
        "/authoring/candidates", headers={"Accept": "application/json"}
    ).json()["approved"]
    assert approved == []


# --- Human approval gate ------------------------------------------------------


def test_approved_content_becomes_distinguishable_from_pending_candidates() -> None:
    client = _client()
    first = _generate(client)
    second = _generate(client)
    assert first["id"] != second["id"]

    approve = client.post(
        f"/authoring/candidates/{first['id']}/approve",
        headers={"Accept": "application/json", "X-Author-Name": "reviewer@fablit"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"
    assert approve.json()["is_approved"] is True

    listing = client.get(
        "/authoring/candidates", headers={"Accept": "application/json"}
    ).json()
    assert [item["id"] for item in listing["approved"]] == [first["id"]]
    assert second["id"] not in [item["id"] for item in listing["approved"]]


def test_rejected_candidate_never_enters_the_library() -> None:
    client = _client()
    candidate = _generate(client)

    reject = client.post(
        f"/authoring/candidates/{candidate['id']}/reject",
        headers={"Accept": "application/json"},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    listing = client.get(
        "/authoring/candidates", headers={"Accept": "application/json"}
    ).json()
    assert listing["approved"] == []
    statuses = {item["id"]: item["status"] for item in listing["candidates"]}
    assert statuses[candidate["id"]] == "rejected"


def test_malformed_provider_output_cannot_be_approved() -> None:
    provider = FakeAuthoringProvider(
        {
            "status": "candidate",
            "activity": {"title": "Loosely shaped", "instructions": "Do something."},
        }
    )
    client = _client(provider=provider)

    candidate = _generate(client)
    assert candidate["validation"]["is_approvable"] is False

    approve = client.post(
        f"/authoring/candidates/{candidate['id']}/approve",
        headers={"Accept": "application/json"},
    )
    assert approve.status_code == 422

    listing = client.get(
        "/authoring/candidates", headers={"Accept": "application/json"}
    ).json()
    assert listing["approved"] == []


def test_approving_an_unknown_candidate_is_a_404() -> None:
    client = _client()
    response = client.post(
        "/authoring/candidates/not-a-uuid/approve",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 404


# --- Provider-backed generation (ARCH-001) ------------------------------------


def test_provider_backed_generation_records_provider_provenance() -> None:
    provider = FakeAuthoringProvider(
        _PROVIDER_OUTPUT, provider="test-gemini", model="test-gemini-1"
    )
    client = _client(provider=provider)

    candidate = _generate(client)

    assert candidate["validation"]["is_approvable"] is True
    assert candidate["provenance"]["provider"] == "test-gemini"
    assert candidate["provenance"]["model"] == "test-gemini-1"
    assert len(provider.calls) == 1


def test_provider_failure_creates_no_learner_facing_candidate() -> None:
    from fablit.application import AuthoringProviderError

    provider = FakeAuthoringProvider(error=AuthoringProviderError("unavailable"))
    client = _client(provider=provider)

    response = client.post(
        "/authoring/generate",
        json=_BRIEF_FORM,
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 502

    listing = client.get(
        "/authoring/candidates", headers={"Accept": "application/json"}
    ).json()
    assert listing["candidates"] == []


# --- Brief validation ---------------------------------------------------------


def test_generate_rejects_an_incomplete_brief() -> None:
    client = _client()
    response = client.post(
        "/authoring/generate",
        json={"practice_area": "Visual Analysis"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 422


def test_generate_rejects_an_unsupported_practice_mode() -> None:
    client = _client()
    payload = dict(_BRIEF_FORM, practice_mode="essay")
    response = client.post(
        "/authoring/generate",
        json=payload,
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 422


# --- Editing ------------------------------------------------------------------


def test_editing_a_candidate_creates_a_new_revision() -> None:
    client = _client()
    candidate = _generate(client)

    edit = client.post(
        f"/authoring/candidates/{candidate['id']}/edit",
        json={"title": "Authored Title", "description": "Authored description."},
        headers={"Accept": "application/json"},
    )
    assert edit.status_code == 200
    assert edit.json()["revision"] == 2
    assert edit.json()["title"] == "Authored Title"
    assert edit.json()["status"] == "under_review"


def test_editing_with_forbidden_feedback_language_blocks_approval() -> None:
    client = _client()
    candidate = _generate(client)

    edit = client.post(
        f"/authoring/candidates/{candidate['id']}/edit",
        json={
            "contract": {
                "purpose": "Practise reading structure.",
                "task": "Describe the structure you notice.",
                "expected_thinking": "Move from observation to a claim.",
                "response_contract": "A short paragraph.",
                "evaluation_intent": "Look for evidence.",
                "feedback_intent": "Give a mastery score for the response.",
                "reflection_intent": "Notice your approach.",
                "continuation_intent": "Try a related practice.",
            }
        },
        headers={"Accept": "application/json"},
    )
    assert edit.status_code == 200
    assert edit.json()["validation"]["is_approvable"] is False

    approve = client.post(
        f"/authoring/candidates/{candidate['id']}/approve",
        headers={"Accept": "application/json"},
    )
    assert approve.status_code == 422


# --- Learner boundary ---------------------------------------------------------


def test_learner_routes_are_unaffected_by_the_authoring_workflow() -> None:
    client = _client()
    _generate(client)

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "Internal Authoring" not in dashboard.text
    practice = client.get("/practice")
    assert practice.status_code == 200
