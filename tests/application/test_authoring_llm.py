"""Provider-neutral LLM boundary behaviour (ARCH-001).

These tests protect the boundary SPEC-032 depends on: a structured request,
a structured generation result carrying provider/model metadata and timestamp,
and a deterministic fake provider that makes the workflow testable without any
real external API call.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fablit.application import (
    AuthoringGenerationRequest,
    AuthoringLlmProvider,
    AuthoringProviderError,
    BriefDraftingRequest,
    FakeAuthoringProvider,
    LlmGenerationResult,
    PracticeAuthoringBrief,
    PracticeMode,
    candidate_from_provider_output,
    draft_candidate_from_brief,
)


def _brief(**overrides: object) -> PracticeAuthoringBrief:
    values: dict[str, object] = {
        "practice_area": "Visual Analysis",
        "practice_purpose": "Practise reading structure in a composition.",
        "task": "Describe the dominant structure you notice.",
        "response_form": "A short evidence-based paragraph.",
        "primary_capability": "Observe",
        "practice_mode": PracticeMode.FULL_PRACTICE,
    }
    values.update(overrides)
    return PracticeAuthoringBrief(**values)  # type: ignore[arg-type]


def _output() -> dict[str, object]:
    return {
        "title": "Reading Composition — Observe Practice",
        "description": "A generated practice on reading composition.",
        "contract": {
            "purpose": "Practise reading structure in a composition.",
            "task": "Describe the dominant structure you notice.",
            "expected_thinking": "Move from observation to a reasoned claim.",
            "response_contract": "A short evidence-based paragraph.",
            "evaluation_intent": "Look for evidence tied to the composition.",
            "feedback_intent": "Name one strength, why it matters, next move.",
            "reflection_intent": "Notice how you approached the reading.",
            "continuation_intent": "Try a related practice on the same move.",
        },
    }


# --- Port shape (ARCH-001) ----------------------------------------------------


def test_fake_provider_satisfies_the_authoring_provider_port() -> None:
    provider = FakeAuthoringProvider(_output())
    assert isinstance(provider, AuthoringLlmProvider)


def test_request_carries_the_structured_brief() -> None:
    request = AuthoringGenerationRequest(brief=_brief())
    payload = request.as_payload()
    assert payload["practice_area"] == "Visual Analysis"
    assert payload["practice_mode"] == PracticeMode.FULL_PRACTICE.value


# --- Structured generation result (ARCH-001) ----------------------------------


def test_fake_provider_returns_a_structured_result_with_metadata() -> None:
    provider = FakeAuthoringProvider(_output(), provider="acme", model="acme-1")

    result = provider.generate(_brief())

    assert isinstance(result, LlmGenerationResult)
    assert result.provider == "acme"
    assert result.model == "acme-1"
    assert result.candidate_data["title"] == "Reading Composition — Observe Practice"
    assert result.output["title"] == "Reading Composition — Observe Practice"
    assert isinstance(result.generated_at, datetime)
    assert result.generated_at.tzinfo is not None


def test_fake_provider_records_requests_without_network_io() -> None:
    provider = FakeAuthoringProvider(_output())
    brief = _brief()

    provider.generate(brief)

    assert provider.calls == [brief]


def test_fake_provider_generate_candidate_compatibility() -> None:
    provider = FakeAuthoringProvider(_output())
    request = AuthoringGenerationRequest(brief=_brief())

    result = provider.generate_candidate(request)

    assert isinstance(result, LlmGenerationResult)
    assert provider.calls == [request]


def test_generation_result_requires_provider_and_model_metadata() -> None:
    with pytest.raises(AuthoringProviderError, match="provider"):
        LlmGenerationResult(output={}, provider="", model="m")
    with pytest.raises(AuthoringProviderError, match="model"):
        LlmGenerationResult(output={}, provider="p", model="  ")


def test_generation_result_requires_timezone_aware_generated_at() -> None:
    naive_dt = datetime(2026, 1, 1, 12, 0, 0)
    with pytest.raises(AuthoringProviderError, match="timezone-aware"):
        LlmGenerationResult(
            candidate_data=_output(),
            provider="p",
            model="m",
            generated_at=naive_dt,
        )

    aware_dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    result = LlmGenerationResult(
        candidate_data=_output(),
        provider="p",
        model="m",
        generated_at=aware_dt,
    )
    assert result.generated_at == aware_dt


def test_fake_provider_can_surface_a_provider_failure() -> None:
    provider = FakeAuthoringProvider(error=AuthoringProviderError("boom"))

    with pytest.raises(AuthoringProviderError, match="boom"):
        provider.generate(_brief())


def test_fake_provider_output_flows_into_spec_032_validation() -> None:
    """The port's result feeds SPEC-032's existing validation unchanged."""
    provider = FakeAuthoringProvider(_output())
    result = provider.generate(_brief())

    candidate = candidate_from_provider_output(
        result.candidate_data, _brief(), provider=result.provider, model=result.model
    )

    assert candidate.validation.is_approvable is True
    assert candidate.provenance.provider == "fake-authoring"


def test_provider_free_path_still_works_alongside_the_port() -> None:
    """AI availability never gates authoring (SPEC-032 §17)."""
    candidate = draft_candidate_from_brief(_brief())
    assert candidate.validation.is_approvable is True


# --- Brief drafting (SPEC-040) ------------------------------------------------


def test_brief_drafting_request_carries_notes_and_current_brief() -> None:
    request = BriefDraftingRequest(
        notes="Year 10 group compared two posters.",
        current_values={"practice_area": "Visual analysis"},
        target_field="evaluation_intent",
    )

    payload = request.as_payload()

    assert payload == {
        "notes": "Year 10 group compared two posters.",
        "current_values": {"practice_area": "Visual analysis"},
        "target_field": "evaluation_intent",
    }


def test_brief_drafting_request_requires_source_notes() -> None:
    with pytest.raises(AuthoringProviderError, match="source notes"):
        BriefDraftingRequest(notes="   ")


def test_fake_provider_returns_a_configured_brief_draft() -> None:
    output = {"fields": {"practice_area": {"value": "Visual analysis"}}}
    provider = FakeAuthoringProvider(brief_output=output)
    request = BriefDraftingRequest(
        notes="A short topic",
        current_values={"purpose": "Notice evidence"},
    )

    assert provider.draft_brief(request) == output
    assert provider.brief_calls == [request]
    # Drafting is separate from candidate generation (SPEC-040 §5).
    assert provider.calls == []


def test_fake_provider_can_surface_a_brief_drafting_failure() -> None:
    provider = FakeAuthoringProvider(
        brief_error=AuthoringProviderError("provider down")
    )

    with pytest.raises(AuthoringProviderError, match="provider down"):
        provider.draft_brief(BriefDraftingRequest(notes="A short topic"))
