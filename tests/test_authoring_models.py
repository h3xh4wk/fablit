"""Tests for typed internal practice-authoring models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.authoring import (
    AuthoringBrief,
    AuthoringCandidateStore,
    CandidateReviewOutcome,
    InvalidAuthoringBriefError,
    PracticeCandidate,
)
from fablit.application.practice_modes import PracticeMode


def _brief_values(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "practice_area": "Visual analysis",
        "learner_context": "A learner practising close observation.",
        "purpose": "Distinguish visible evidence from interpretation.",
        "intended_mode": "short-drill",
        "response_form": "A short written observation.",
        "evaluation_intent": "Look for specific observable details.",
        "feedback_intent": "Identify useful evidence and one next step.",
        "reflection_intent": "Notice which observation strategy was useful.",
    }
    values.update(overrides)
    return values


def test_authoring_brief_parses_required_and_optional_fields() -> None:
    brief = AuthoringBrief.from_mapping(
        _brief_values(
            examination_context="Design entrance practice",
            primary_creative_thinking_lens="Observe",
            constraints="Use one paragraph.",
            stimulus_requirements="Use a photograph.",
            continuation_intent="Extend the same observation with a new image.",
        )
    )

    assert brief.intended_mode is PracticeMode.SHORT_DRILL
    assert brief.primary_creative_thinking_lens == "Observe"
    assert brief.continuation_intent == (
        "Extend the same observation with a new image."
    )


def test_authoring_brief_allows_omitted_optional_fields() -> None:
    brief = AuthoringBrief.from_mapping(_brief_values())

    assert brief.examination_context is None
    assert brief.primary_creative_thinking_lens is None
    assert brief.constraints is None
    assert brief.stimulus_requirements is None
    assert brief.continuation_intent is None


@pytest.mark.parametrize(
    "values",
    [
        _brief_values(purpose=" "),
        _brief_values(intended_mode="unsupported-mode"),
        _brief_values(primary_creative_thinking_lens="Unsupported"),
        _brief_values(unrecognized_field="value"),
        _brief_values(learner_context=5),
    ],
)
def test_authoring_brief_rejects_invalid_fields(
    values: dict[str, object],
) -> None:
    with pytest.raises(InvalidAuthoringBriefError):
        AuthoringBrief.from_mapping(values)


def test_practice_candidate_preserves_brief_untrusted_data_and_provenance() -> None:
    brief = AuthoringBrief.from_mapping(_brief_values())
    generated_at = datetime(2026, 10, 11, 9, tzinfo=UTC)
    candidate = PracticeCandidate(
        brief=brief,
        candidate_data={"title": "Draft", "unexpected": {"raw": True}},
        provider="provider-neutral-name",
        model="model-v1",
        generated_at=generated_at,
    )

    assert candidate.brief is brief
    assert candidate.candidate_data["unexpected"] == {"raw": True}
    assert candidate.provider == "provider-neutral-name"
    assert candidate.model == "model-v1"
    assert candidate.generated_at == generated_at
    assert candidate.review_outcome is None
    assert candidate.status == "candidate"


def test_candidate_requires_timezone_aware_utc_provenance() -> None:
    brief = AuthoringBrief.from_mapping(_brief_values())
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        PracticeCandidate(
            brief=brief,
            candidate_data={},
            provider="provider",
            model="model",
            generated_at=datetime(2026, 10, 11, 9),
        )
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        PracticeCandidate(
            brief=brief,
            candidate_data={},
            provider="provider",
            model="model",
            generated_at=datetime(
                2026,
                10,
                11,
                9,
                tzinfo=timezone(timedelta(hours=1)),
            ),
        )


def test_candidate_store_lists_and_retrieves_actual_candidates() -> None:
    brief = AuthoringBrief.from_mapping(_brief_values())
    candidate = PracticeCandidate(
        id=uuid4(),
        brief=brief,
        candidate_data={"title": "Draft"},
        provider="provider",
        model="model",
        generated_at=datetime.now(UTC),
        review_outcome=CandidateReviewOutcome.REJECTED,
    )
    store = AuthoringCandidateStore()

    store.add(candidate)

    assert store.get(candidate.id) is candidate
    assert store.list() == (candidate,)
    assert candidate.status == "rejected"
