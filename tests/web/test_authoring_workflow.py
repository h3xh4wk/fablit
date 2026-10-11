"""Authoring brief validation and candidate provenance workflow tests."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.authoring import AuthoringBrief
from app.main import create_app
from fablit.config import load_config

SECRET = "authoring-workflow-secret"
HEADERS = {"Authorization": f"Bearer {SECRET}"}
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


def _client(*, configured_provider: bool = True) -> tuple[TestClient, Mock]:
    app = create_app(
        load_config(
            overrides={
                "environment": "testing",
                "authoring_secret": SECRET,
            }
        )
    )
    provider = Mock()
    provider.generate.return_value = SimpleNamespace(
        candidate_data={
            "title": "Evidence-based observation",
            "description": "Describe one detail.",
            "contract": {"task": "Describe what is visible."},
        },
        provider="test-provider",
        model="test-model",
        generated_at=datetime(2026, 10, 11, 9, tzinfo=UTC),
    )
    if configured_provider:
        app.state.authoring_ai_provider = provider
    return TestClient(app), provider


def test_authoring_form_captures_complete_brief_and_renders_candidate() -> None:
    client, provider = _client()
    response = client.post(
        "/authoring/generate",
        headers={**HEADERS, "Accept": "text/html"},
        data={
            **BRIEF,
            "examination_context": "",
            "primary_creative_thinking_lens": "Observe",
            "constraints": "Use one paragraph.",
            "stimulus_requirements": "Use an image of a public place.",
            "continuation_intent": "",
        },
    )

    assert response.status_code == 200
    assert "Evidence-based observation" in response.text
    assert "test-provider" in response.text
    assert "test-model" in response.text
    assert "A learner practising close observation." in response.text
    assert "Use one paragraph." in response.text
    assert "Use an image of a public place." in response.text
    assert "Identify useful evidence and one next step." in response.text
    assert "Extend the same observation" not in response.text
    provider.generate.assert_called_once()
    brief = provider.generate.call_args.args[0]
    assert isinstance(brief, AuthoringBrief)
    assert brief.primary_creative_thinking_lens == "Observe"
    assert brief.continuation_intent is None


def test_invalid_brief_is_rejected_before_provider_invocation() -> None:
    client, provider = _client()
    response = client.post(
        "/authoring/generate",
        headers=HEADERS,
        json={**BRIEF, "intended_mode": "unsupported"},
    )

    assert response.status_code == 422
    provider.generate.assert_not_called()


def test_missing_required_brief_field_is_rejected() -> None:
    client, provider = _client()
    brief = {key: value for key, value in BRIEF.items() if key != "purpose"}
    response = client.post(
        "/authoring/generate",
        headers=HEADERS,
        json=brief,
    )

    assert response.status_code == 422
    provider.generate.assert_not_called()


def test_generation_without_provider_does_not_create_fallback_candidate() -> None:
    client, _ = _client(configured_provider=False)
    response = client.post(
        "/authoring/generate",
        headers=HEADERS,
        json=BRIEF,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == ("The AI generation service is not configured.")
    assert client.get("/authoring/candidates", headers=HEADERS).json() == {
        "candidates": []
    }


def test_candidate_list_exposes_brief_and_safe_provenance() -> None:
    client, _ = _client()
    generated = client.post(
        "/authoring/generate",
        headers=HEADERS,
        json=BRIEF,
    )
    listed = client.get("/authoring/candidates", headers=HEADERS)

    assert generated.status_code == 200
    assert listed.status_code == 200
    candidate = listed.json()["candidates"][0]
    assert candidate["brief"]["practice_area"] == "Visual analysis"
    assert candidate["candidate_data"]["title"] == "Evidence-based observation"
    assert candidate["provider"] == "test-provider"
    assert candidate["model"] == "test-model"
    assert candidate["generated_at"] == "2026-10-11T09:00:00+00:00"
    assert SECRET not in listed.text
    assert "api_key" not in listed.text


def test_untrusted_non_mapping_contract_renders_without_becoming_validated() -> None:
    client, provider = _client()
    provider.generate.return_value.candidate_data["contract"] = "untrusted raw value"
    response = client.post(
        "/authoring/generate",
        headers={**HEADERS, "Accept": "text/html"},
        data=BRIEF,
    )

    assert response.status_code == 200
    assert "untrusted raw value" in response.text


def test_gemini_provider_adapter_integration_with_authoring_endpoint() -> None:
    import json
    from unittest.mock import MagicMock

    from fablit.platform.gemini_authoring_provider import (
        DEFAULT_GEMINI_MODEL,
        GEMINI_PROVIDER_ID,
        GeminiAuthoringProvider,
    )

    fake_fetch = MagicMock()
    fake_fetch.return_value = json.dumps(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "title": "Integrated Test Title",
                                        "description": "Integrated desc",
                                        "contract": {
                                            "task": "Write an integrated response."
                                        },
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }
    ).encode("utf-8")
    provider = GeminiAuthoringProvider(
        api_key="integration-key",
        fetch=fake_fetch,
    )
    app = create_app(
        load_config(
            overrides={
                "environment": "testing",
                "authoring_secret": SECRET,
                "ai_provider_api_key": "integration-key",
            }
        )
    )
    app.state.authoring_ai_provider = provider
    client = TestClient(app)

    response = client.post(
        "/authoring/generate",
        headers=HEADERS,
        json=BRIEF,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == GEMINI_PROVIDER_ID
    assert data["model"] == DEFAULT_GEMINI_MODEL
    assert data["candidate_data"]["title"] == "Integrated Test Title"
    assert (
        data["brief"]["purpose"] == "Distinguish visible evidence from interpretation."
    )


def _complete_contract() -> dict[str, str]:
    return {
        "purpose": (
            "Distinguish visible evidence from interpretation in Visual analysis."
        ),
        "task": "Identify three visible details in the provided stimulus.",
        "expected_thinking": "Connect visible details directly to interpretations.",
        "response_contract": "Three concise bullet points citing evidence.",
        "evaluation_intent": "Check for concrete descriptive language.",
        "feedback_intent": (
            "Highlight the most specific observation and suggest next step."
        ),
        "reflection_intent": "Notice which visual feature guided your analysis.",
        "continuation_intent": "Apply the observation method to a contrasting scene.",
    }


def test_candidate_detail_and_approval_workflow() -> None:
    client, provider = _client()
    provider.generate.return_value = SimpleNamespace(
        candidate_data={
            "title": "Evidence-based observation",
            "description": "Describe one detail.",
            "contract": _complete_contract(),
        },
        provider="test-provider",
        model="test-model",
        generated_at=datetime(2026, 10, 11, 9, tzinfo=UTC),
    )

    gen_resp = client.post("/authoring/generate", headers=HEADERS, json=BRIEF)
    assert gen_resp.status_code == 200
    candidate_id = gen_resp.json()["id"]

    # Detail JSON
    detail_resp = client.get(f"/authoring/candidates/{candidate_id}", headers=HEADERS)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["id"] == candidate_id
    assert detail_data["validation"]["is_approvable"] is True

    # Detail HTML
    html_resp = client.get(
        f"/authoring/candidates/{candidate_id}",
        headers={**HEADERS, "Accept": "text/html"},
    )
    assert html_resp.status_code == 200
    assert "Generated Candidate Practice" in html_resp.text
    assert "Evidence-based observation" in html_resp.text

    # Approve valid candidate
    app_resp = client.post(
        f"/authoring/candidates/{candidate_id}/approve", headers=HEADERS
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "approved"

    # Conflicting state transitions
    dup_app = client.post(
        f"/authoring/candidates/{candidate_id}/approve", headers=HEADERS
    )
    assert dup_app.status_code == 409
    assert "already approved" in dup_app.json()["detail"]

    dup_rej = client.post(
        f"/authoring/candidates/{candidate_id}/reject", headers=HEADERS
    )
    assert dup_rej.status_code == 409
    assert "cannot be rejected" in dup_rej.json()["detail"]


def test_candidate_approval_gate_blocks_invalid_candidate() -> None:
    client, provider = _client()
    # Contract missing required fields
    provider.generate.return_value = SimpleNamespace(
        candidate_data={
            "title": "Invalid Incomplete Practice",
            "description": "Incomplete practice without full contract.",
            "contract": {"task": "Just a task."},
        },
        provider="test-provider",
        model="test-model",
        generated_at=datetime(2026, 10, 11, 9, tzinfo=UTC),
    )

    gen_resp = client.post("/authoring/generate", headers=HEADERS, json=BRIEF)
    assert gen_resp.status_code == 200
    candidate_id = gen_resp.json()["id"]
    assert gen_resp.json()["validation"]["is_approvable"] is False

    # Attempt to approve
    app_resp = client.post(
        f"/authoring/candidates/{candidate_id}/approve", headers=HEADERS
    )
    assert app_resp.status_code == 422
    assert "validation errors and cannot be approved" in app_resp.json()["detail"]


def test_candidate_edit_and_revalidation_flow() -> None:
    client, provider = _client()
    # Candidate with forbidden evaluative language in feedback intent
    invalid_contract = _complete_contract()
    invalid_contract["feedback_intent"] = "Assign a score and assess mastery."
    provider.generate.return_value = SimpleNamespace(
        candidate_data={
            "title": "Evaluative Draft",
            "description": "Close observation.",
            "contract": invalid_contract,
        },
        provider="test-provider",
        model="test-model",
        generated_at=datetime(2026, 10, 11, 9, tzinfo=UTC),
    )

    gen_resp = client.post("/authoring/generate", headers=HEADERS, json=BRIEF)
    assert gen_resp.status_code == 200
    cand_id = gen_resp.json()["id"]
    assert gen_resp.json()["validation"]["is_approvable"] is False

    # Approval blocked
    assert (
        client.post(
            f"/authoring/candidates/{cand_id}/approve", headers=HEADERS
        ).status_code
        == 422
    )

    # Edit via API to fix feedback intent
    edit_resp = client.post(
        f"/authoring/candidates/{cand_id}/edit",
        headers=HEADERS,
        json={
            "feedback_intent": (
                "Identify specific concrete evidence and suggest one next step."
            )
        },
    )
    assert edit_resp.status_code == 200
    edited_data = edit_resp.json()
    assert edited_data["revision"] == 2
    assert edited_data["validation"]["is_approvable"] is True
    assert len(edited_data["history"]) == 1

    # Edit HTML flow works
    edit_html = client.post(
        f"/authoring/candidates/{cand_id}/edit",
        headers={**HEADERS, "Accept": "text/html"},
        data={"title": "Updated Observation Title"},
    )
    assert edit_html.status_code == 200
    assert "revision 3" in edit_html.text

    # Now approvable
    final_app = client.post(f"/authoring/candidates/{cand_id}/approve", headers=HEADERS)
    assert final_app.status_code == 200
    assert final_app.json()["status"] == "approved"


def test_authoring_candidates_are_isolated_from_learner_library() -> None:
    client, provider = _client()
    provider.generate.return_value = SimpleNamespace(
        candidate_data={
            "title": "Secret Internal Authoring Activity",
            "description": "Internal activity not yet published.",
            "contract": _complete_contract(),
        },
        provider="test-provider",
        model="test-model",
        generated_at=datetime(2026, 10, 11, 9, tzinfo=UTC),
    )

    gen_resp = client.post("/authoring/generate", headers=HEADERS, json=BRIEF)
    cand_id = gen_resp.json()["id"]
    client.post(f"/authoring/candidates/{cand_id}/approve", headers=HEADERS)

    # Learner activities list on dashboard and practice pages
    dashboard_resp = client.get("/")
    assert dashboard_resp.status_code == 200
    assert "Secret Internal Authoring Activity" not in dashboard_resp.text

    practice_resp = client.get("/practice")
    assert practice_resp.status_code == 200
    assert "Secret Internal Authoring Activity" not in practice_resp.text
