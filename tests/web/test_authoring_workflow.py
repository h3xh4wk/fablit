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
