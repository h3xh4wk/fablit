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
from fablit.application.errors import (
    CandidateNotApprovableError,
    CandidateNotFoundError,
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


def _valid_candidate_data(
    title: str = "Test Observation", **contract_overrides: str
) -> dict[str, object]:
    contract = {
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
    contract.update(contract_overrides)
    return {
        "title": title,
        "description": "Practice close visual observation without grading.",
        "contract": contract,
    }


def test_candidate_validation_evaluates_contract_and_feedback_quality() -> None:
    brief = AuthoringBrief.from_mapping(_brief_values())
    valid_candidate = PracticeCandidate(
        brief=brief,
        candidate_data=_valid_candidate_data(),
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    assert valid_candidate.validation.is_approvable is True
    assert len(valid_candidate.validation.structural_errors) == 0
    assert len(valid_candidate.validation.feedback_errors) == 0

    # Missing contract field
    invalid_data = _valid_candidate_data()
    assert isinstance(invalid_data["contract"], dict)
    del invalid_data["contract"]["continuation_intent"]
    invalid_candidate = PracticeCandidate(
        brief=brief,
        candidate_data=invalid_data,
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    assert invalid_candidate.validation.is_approvable is False
    assert any(
        "continuation_intent" in err
        for err in invalid_candidate.validation.structural_errors
    )

    # Evaluative term in feedback_intent (SPEC-030)
    eval_candidate = PracticeCandidate(
        brief=brief,
        candidate_data=_valid_candidate_data(
            feedback_intent="Assign a score and assess learner mastery."
        ),
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    assert eval_candidate.validation.is_approvable is False
    assert any("mastery" in err for err in eval_candidate.validation.feedback_errors)
    assert any("score" in err for err in eval_candidate.validation.feedback_errors)


def test_candidate_store_lifecycle_and_transition_guards() -> None:
    brief = AuthoringBrief.from_mapping(_brief_values())
    store = AuthoringCandidateStore()

    candidate = PracticeCandidate(
        brief=brief,
        candidate_data=_valid_candidate_data("Candidate Alpha"),
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    store.add(candidate)

    # Retrieve valid candidate
    retrieved = store.get(str(candidate.id))
    assert retrieved.id == candidate.id

    # Unknown candidate returns CandidateNotFoundError
    with pytest.raises(CandidateNotFoundError):
        store.get(uuid4())
    with pytest.raises(CandidateNotFoundError):
        store.get("not-a-uuid")

    # Approve candidate
    approved = store.approve(candidate.id, reviewer="reviewer-jane")
    assert approved.status == "approved"
    assert approved.is_approved is True
    assert approved.reviewer == "reviewer-jane"
    assert approved.decided_at is not None
    assert store.approved_practices() == (approved,)

    # Conflict: cannot approve already approved candidate
    with pytest.raises(CandidateNotApprovableError, match="already approved"):
        store.approve(candidate.id)

    # Conflict: cannot reject already approved candidate
    with pytest.raises(CandidateNotApprovableError, match="cannot be rejected"):
        store.reject(candidate.id)

    # Rejection lifecycle
    cand_beta = PracticeCandidate(
        brief=brief,
        candidate_data=_valid_candidate_data("Candidate Beta"),
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    store.add(cand_beta)
    rejected = store.reject(cand_beta.id, reviewer="reviewer-bob")
    assert rejected.status == "rejected"
    assert rejected.reviewer == "reviewer-bob"

    # Conflict: cannot reject already rejected candidate
    with pytest.raises(CandidateNotApprovableError, match="already rejected"):
        store.reject(cand_beta.id)

    # Conflict: cannot approve rejected candidate
    with pytest.raises(CandidateNotApprovableError, match="cannot be approved"):
        store.approve(cand_beta.id)


def test_candidate_store_blocks_approval_of_invalid_candidate() -> None:
    brief = AuthoringBrief.from_mapping(_brief_values())
    store = AuthoringCandidateStore()

    invalid_candidate = PracticeCandidate(
        brief=brief,
        candidate_data=_valid_candidate_data(
            feedback_intent="Grade learner performance on a 1-5 scale."
        ),
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    store.add(invalid_candidate)

    with pytest.raises(CandidateNotApprovableError, match="validation errors"):
        store.approve(invalid_candidate.id)


def test_candidate_store_detects_duplicate_titles() -> None:
    brief = AuthoringBrief.from_mapping(_brief_values())
    store = AuthoringCandidateStore()

    cand1 = PracticeCandidate(
        brief=brief,
        candidate_data=_valid_candidate_data("Unique Practice Name"),
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    cand2 = PracticeCandidate(
        brief=brief,
        candidate_data=_valid_candidate_data("unique practice name"),
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    store.add(cand1)
    added2 = store.add(cand2)
    assert any("possible duplicate" in w for w in added2.validation.content_warnings)


def test_candidate_store_edit_revalidates_and_archives_history() -> None:
    brief = AuthoringBrief.from_mapping(_brief_values())
    store = AuthoringCandidateStore()

    invalid_candidate = PracticeCandidate(
        brief=brief,
        candidate_data=_valid_candidate_data(
            feedback_intent="Grade learner output against peers."
        ),
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    store.add(invalid_candidate)
    assert invalid_candidate.validation.is_approvable is False

    # Edit candidate to fix forbidden feedback language
    updated = store.edit(
        invalid_candidate.id,
        updates={
            "feedback_intent": (
                "Highlight descriptive detail and offer a constructive next step."
            )
        },
        editor="author-editor",
    )
    assert updated.revision == 2
    assert updated.validation.is_approvable is True
    assert len(updated.history) == 1
    assert updated.history[0].version == 1
    assert updated.history[0].editor == "author-editor"

    # Now that it's validated, it can be approved
    approved = store.approve(updated.id, reviewer="final-reviewer")
    assert approved.status == "approved"
