"""AI-assisted practice authoring workflow behaviour (SPEC-032).

These tests protect the boundaries that make the workflow safe to use: a
structured brief, provider-agnostic generation, structural + feedback
validation that keeps malformed output out of the approval path, an explicit
human approval gate, editing/rejection, and provenance.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fablit.application import (
    DETERMINISTIC_PROVIDER,
    AuthoringCandidateStore,
    AuthoringProvenance,
    CandidateNotApprovableError,
    CandidateNotFoundError,
    CandidateStatus,
    InvalidAuthoringBriefError,
    PracticeAuthoringBrief,
    PracticeCandidate,
    PracticeContentContract,
    PracticeMode,
    candidate_from_provider_output,
    draft_candidate_from_brief,
    serialize_candidate,
    validate_candidate,
    with_validation,
)


def _brief(**overrides: object) -> PracticeAuthoringBrief:
    values: dict[str, object] = {
        "practice_area": "Visual Analysis",
        "practice_purpose": "Practise reading structure in a composition.",
        "task": "Describe the dominant structure you notice.",
        "response_form": "A short evidence-based paragraph.",
        "primary_capability": "Observe",
        "practice_mode": PracticeMode.FULL_PRACTICE,
        "learner_context": "Design aspirants preparing a portfolio.",
        "evaluation_intent": "Look for evidence tied to the composition.",
        "feedback_intent": "Name one strength, why it matters, and one next move.",
        "reflection_intent": "Notice how you approached the reading.",
        "continuation_intent": "Try a related practice on the same thinking move.",
    }
    values.update(overrides)
    return PracticeAuthoringBrief(**values)  # type: ignore[arg-type]


def _provider_output(**overrides: object) -> dict[str, object]:
    contract: dict[str, str] = {
        "purpose": "Practise reading structure in a composition.",
        "task": "Describe the dominant structure you notice.",
        "expected_thinking": "Move from observation to a reasoned claim.",
        "response_contract": "A short evidence-based paragraph.",
        "evaluation_intent": "Look for evidence tied to the composition.",
        "feedback_intent": "Name one strength, why it matters, and one next move.",
        "reflection_intent": "Notice how you approached the reading.",
        "continuation_intent": "Try a related practice on the same thinking move.",
    }
    values: dict[str, object] = {
        "title": "Reading Composition — Observe Practice",
        "description": "A generated practice on reading composition.",
        "contract": contract,
    }
    values.update(overrides)
    return values


# --- Authoring brief (SPEC-032 §4) -------------------------------------------


def test_brief_accepts_a_complete_structured_description() -> None:
    brief = _brief()

    assert brief.practice_mode is PracticeMode.FULL_PRACTICE
    assert brief.primary_capability == "Observe"
    assert brief.as_dict()["practice_area"] == "Visual Analysis"


@pytest.mark.parametrize(
    "field",
    ["practice_area", "practice_purpose", "task", "response_form"],
)
def test_brief_rejects_blank_required_intent_fields(field: str) -> None:
    with pytest.raises(InvalidAuthoringBriefError, match=field):
        _brief(**{field: "   "})


def test_brief_rejects_an_unsupported_practice_mode() -> None:
    with pytest.raises(InvalidAuthoringBriefError, match="practice mode"):
        _brief(practice_mode="essay")


def test_brief_rejects_an_unsupported_thinking_lens() -> None:
    with pytest.raises(InvalidAuthoringBriefError, match="capability"):
        _brief(primary_capability="Memorise")


def test_brief_rejects_a_secondary_lens_equal_to_the_primary() -> None:
    with pytest.raises(InvalidAuthoringBriefError, match="differ"):
        _brief(secondary_capability="Observe")


def test_brief_rejects_blank_constraints() -> None:
    with pytest.raises(InvalidAuthoringBriefError, match="constraints"):
        _brief(constraints=("   ",))


def test_exam_name_alone_cannot_form_a_brief() -> None:
    """AA-006: a brief describes intent, not just an examination label."""
    with pytest.raises(InvalidAuthoringBriefError):
        PracticeAuthoringBrief(
            practice_area="",
            practice_purpose="",
            task="",
            response_form="",
            primary_capability="Observe",
            practice_mode=PracticeMode.FULL_PRACTICE,
            examination_context="Design Aptitude Test",
        )


# --- Provider-free generation (SPEC-032 §17) ---------------------------------


def test_draft_from_brief_is_valid_and_approvable_without_ai() -> None:
    candidate = draft_candidate_from_brief(_brief())

    assert candidate.provenance.provider == DETERMINISTIC_PROVIDER
    assert candidate.contract is not None
    assert candidate.validation.is_approvable is True
    assert candidate.status is CandidateStatus.GENERATED


def test_draft_derives_a_full_contract_even_when_intent_is_sparse() -> None:
    brief = _brief(
        evaluation_intent="",
        feedback_intent="",
        reflection_intent="",
        continuation_intent="",
    )
    candidate = draft_candidate_from_brief(brief)

    assert candidate.contract is not None
    assert candidate.contract.feedback_intent
    assert candidate.contract.continuation_intent
    assert candidate.validation.is_approvable is True


# --- Provider output parsing (SPEC-032 §5, §17) ------------------------------


def test_complete_provider_output_becomes_an_approvable_candidate() -> None:
    candidate = candidate_from_provider_output(
        _provider_output(), _brief(), provider="test-provider", model="test-model"
    )

    assert candidate.validation.is_approvable is True
    assert candidate.contract is not None
    assert candidate.contract.task == "Describe the dominant structure you notice."


def test_malformed_provider_output_is_not_approvable() -> None:
    candidate = candidate_from_provider_output(
        {}, _brief(), provider="test-provider", model="test-model"
    )

    assert candidate.contract is None
    assert candidate.validation.is_approvable is False
    assert any("title" in err for err in candidate.validation.structural_errors)


def test_incomplete_contract_is_not_silently_accepted() -> None:
    output = _provider_output(contract={"purpose": "Only a purpose."})
    candidate = candidate_from_provider_output(
        output, _brief(), provider="test-provider", model="test-model"
    )

    assert candidate.contract is None
    assert candidate.validation.is_approvable is False


def test_unrecognised_activity_shape_is_preserved_as_an_invalid_draft() -> None:
    """The SEC-001 stub shape no longer enters the approval path."""
    candidate = candidate_from_provider_output(
        {"status": "candidate", "activity": {"title": "T", "instructions": "I"}},
        _brief(),
        provider="test-provider",
        model="test-model",
    )

    assert candidate.title == "T"
    assert candidate.contract is None
    assert candidate.validation.is_approvable is False


# --- Validation against SPEC-030 (SPEC-032 §6, §7) ---------------------------


def test_feedback_with_grading_language_blocks_approval() -> None:
    candidate = draft_candidate_from_brief(
        _brief(feedback_intent="Grade the learner's response.")
    )

    assert candidate.validation.is_approvable is False
    assert any("grade" in err for err in candidate.validation.feedback_errors)


@pytest.mark.parametrize(
    "phrase",
    [
        "Assign a mastery score.",
        "Compare the learner's ranking.",
        "Infer the learner's ability.",
        "Judge the learner's motivation.",
    ],
)
def test_feedback_language_violations_are_detected(phrase: str) -> None:
    candidate = draft_candidate_from_brief(_brief(feedback_intent=phrase))

    assert candidate.validation.is_approvable is False


def test_feedback_language_matching_is_whole_word() -> None:
    """A word containing a forbidden term is not itself a violation."""
    candidate = draft_candidate_from_brief(
        _brief(feedback_intent="Point to an upgrade in clarity.")
    )

    assert candidate.validation.feedback_errors == ()
    assert candidate.validation.is_approvable is True


def test_exam_name_alone_is_flagged_as_a_review_warning() -> None:
    brief = _brief(
        examination_context="Design Aptitude Test",
        practice_purpose="Design Aptitude Test",
    )
    candidate = with_validation(
        PracticeCandidate(
            brief=brief,
            provenance=_provenance(brief),
            title="Design Aptitude Test — Observe Practice",
            description="Design aspirants.",
            contract=_contract(purpose="Design Aptitude Test"),
        )
    )

    assert any(
        "exam name alone" in note for note in candidate.validation.content_warnings
    )
    assert candidate.validation.is_approvable is True


def test_candidate_not_referencing_the_practice_area_is_flagged() -> None:
    candidate = draft_candidate_from_brief(_brief(practice_area="Typography"))
    assert candidate.validation.content_warnings == ()

    candidate = with_validation(
        PracticeCandidate(
            brief=_brief(practice_area="Typography"),
            provenance=_provenance(_brief()),
            title="Something Else",
            description="Unrelated.",
            contract=_contract(),
        )
    )
    assert any(
        "practice area" in note for note in candidate.validation.content_warnings
    )


def test_validate_candidate_returns_structural_errors_for_a_blank_candidate() -> None:
    candidate = PracticeCandidate(
        brief=_brief(),
        provenance=_provenance(_brief()),
        title="",
        description="",
        contract=None,
    )

    result = validate_candidate(candidate)

    assert result.is_approvable is False
    assert len(result.structural_errors) >= 2


# --- Approval gate & store (SPEC-032 §8, §9) ---------------------------------


def test_store_keeps_multiple_candidates_and_finds_them_by_id() -> None:
    store = AuthoringCandidateStore()
    first = store.add(draft_candidate_from_brief(_brief()))
    second = store.add(draft_candidate_from_brief(_brief(practice_area="Typography")))

    assert store.get(first.id).id == first.id
    assert [item.id for item in store.list_candidates()] == [first.id, second.id]
    assert store.get(second.id).title.startswith("Typography")


def test_store_raises_for_an_unknown_candidate() -> None:
    store = AuthoringCandidateStore()
    with pytest.raises(CandidateNotFoundError):
        store.get(uuid4())


def test_store_flags_a_possible_duplicate_title() -> None:
    store = AuthoringCandidateStore()
    store.add(draft_candidate_from_brief(_brief()))
    duplicate = store.add(draft_candidate_from_brief(_brief()))

    assert any("duplicate" in note for note in duplicate.validation.content_warnings)


def test_approval_is_refused_for_a_malformed_candidate() -> None:
    store = AuthoringCandidateStore()
    invalid = store.add(
        candidate_from_provider_output({}, _brief(), provider="p", model="m")
    )

    with pytest.raises(CandidateNotApprovableError):
        store.approve(invalid.id, reviewer="author@fablit")


def test_approval_marks_content_approved_and_retains_provenance() -> None:
    store = AuthoringCandidateStore()
    candidate = store.add(draft_candidate_from_brief(_brief()))

    approved = store.approve(candidate.id, reviewer="author@fablit")

    assert approved.status is CandidateStatus.APPROVED
    assert approved.is_approved is True
    assert approved.reviewer == "author@fablit"
    assert approved.decided_at is not None
    assert approved.provenance.reviewer == "author@fablit"
    assert store.approved_practices() == (approved,)


def test_approving_twice_is_refused() -> None:
    store = AuthoringCandidateStore()
    candidate = store.add(draft_candidate_from_brief(_brief()))
    store.approve(candidate.id, reviewer="author@fablit")

    with pytest.raises(CandidateNotApprovableError, match="already approved"):
        store.approve(candidate.id, reviewer="author@fablit")


def test_rejection_is_distinguishable_from_approval() -> None:
    store = AuthoringCandidateStore()
    candidate = store.add(draft_candidate_from_brief(_brief()))

    rejected = store.reject(candidate.id, reviewer="author@fablit")

    assert rejected.status is CandidateStatus.REJECTED
    assert rejected.is_approved is False
    assert store.approved_practices() == ()


def test_only_approved_candidates_enter_the_library() -> None:
    store = AuthoringCandidateStore()
    pending = store.add(draft_candidate_from_brief(_brief()))
    approved = store.add(draft_candidate_from_brief(_brief(practice_area="Typography")))
    store.approve(approved.id, reviewer="author@fablit")

    assert [item.id for item in store.approved_practices()] == [approved.id]
    assert pending.id not in [item.id for item in store.approved_practices()]


# --- Editing (SPEC-032 §10, §11) ---------------------------------------------


def test_editing_a_candidate_creates_a_new_revision_and_keeps_history() -> None:
    store = AuthoringCandidateStore()
    candidate = store.add(draft_candidate_from_brief(_brief()))

    edited = store.edit(
        candidate.id,
        editor="author@fablit",
        title="Authored Title",
        description="Authored description.",
    )

    assert edited.revision == 2
    assert edited.title == "Authored Title"
    assert edited.status is CandidateStatus.UNDER_REVIEW
    assert len(edited.history) == 1
    assert edited.history[0].title == candidate.title
    assert edited.history[0].version == 1


def test_editing_can_replace_the_contract() -> None:
    store = AuthoringCandidateStore()
    candidate = store.add(draft_candidate_from_brief(_brief()))
    new_contract = _contract(task="A rewritten task.")

    edited = store.edit(candidate.id, editor="author@fablit", contract=new_contract)

    assert edited.contract is new_contract


def test_editing_revalidates_the_candidate() -> None:
    store = AuthoringCandidateStore()
    candidate = store.add(draft_candidate_from_brief(_brief()))

    edited = store.edit(
        candidate.id,
        editor="author@fablit",
        contract=_contract(feedback_intent="Give a mastery score."),
    )

    assert edited.validation.is_approvable is False
    with pytest.raises(CandidateNotApprovableError):
        store.approve(edited.id, reviewer="author@fablit")


# --- Serialization & provenance (SPEC-032 §10, §16) --------------------------


def test_serialized_candidate_carries_validation_and_provenance() -> None:
    candidate = draft_candidate_from_brief(_brief())
    view = serialize_candidate(candidate)

    assert view["status"] == "candidate"
    assert view["validation"]["is_approvable"] is True
    assert view["contract"]["task"] == "Describe the dominant structure you notice."
    assert view["provenance"]["brief"]["practice_area"] == "Visual Analysis"
    assert view["provenance"]["provider"] == DETERMINISTIC_PROVIDER


def test_serialized_candidate_never_carries_learner_identity() -> None:
    candidate = draft_candidate_from_brief(_brief())
    view = serialize_candidate(candidate)

    assert "learner_id" not in view
    assert "learner_id" not in view["provenance"]
    assert "learner_id" not in view["provenance"]["brief"]


# --- Helpers -----------------------------------------------------------------


def _contract(**overrides: str) -> PracticeContentContract:
    values: dict[str, str] = {
        "purpose": "Practise reading structure in a composition.",
        "task": "Describe the dominant structure you notice.",
        "expected_thinking": "Move from observation to a reasoned claim.",
        "response_contract": "A short evidence-based paragraph.",
        "evaluation_intent": "Look for evidence tied to the composition.",
        "feedback_intent": "Name one strength, why it matters, and one next move.",
        "reflection_intent": "Notice how you approached the reading.",
        "continuation_intent": "Try a related practice on the same thinking move.",
    }
    values.update(overrides)
    return PracticeContentContract(**values)


def _provenance(brief: PracticeAuthoringBrief) -> AuthoringProvenance:
    return AuthoringProvenance(
        brief=brief,
        generated_at=datetime.now(UTC),
        provider="test-provider",
        model="test-model",
    )
