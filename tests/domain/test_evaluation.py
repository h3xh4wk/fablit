"""Unit tests for the Evaluation domain model (SPEC-007)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import fablit.domain.evaluation
from fablit.domain import (
    Evaluation,
    EvaluationFinding,
    InvalidEvaluationError,
    InvalidEvaluationFindingError,
)

from .helpers import (
    make_evaluation,
    make_finding,
    make_submitted_submission,
)

EVALUATION_SOURCE = Path(fablit.domain.evaluation.__file__).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Creation and identity (FR-001 / DR-001)
# ---------------------------------------------------------------------------


def test_create_evaluation_with_valid_data() -> None:
    submission = make_submitted_submission()
    finding = make_finding()

    evaluation = make_evaluation(submission_id=submission.id, findings=(finding,))

    assert isinstance(evaluation.id, UUID)
    assert evaluation.submission_id == submission.id
    assert evaluation.findings == (finding,)
    assert evaluation.evaluated_at is not None


def test_create_evaluation_with_generated_identity() -> None:
    evaluation = make_evaluation()

    assert isinstance(evaluation.id, UUID)


def test_evaluation_identity_is_unique_across_instances() -> None:
    first = make_evaluation()
    second = make_evaluation()

    assert first.id != second.id


def test_evaluation_identity_remains_stable() -> None:
    evaluation = make_evaluation()
    original_id = evaluation.id

    assert evaluation.id == original_id
    with pytest.raises(FrozenInstanceError):
        evaluation.id = uuid4()  # type: ignore[misc]


def test_evaluation_with_explicit_identity() -> None:
    evaluation_id = uuid4()

    evaluation = make_evaluation(id=evaluation_id)

    assert evaluation.id == evaluation_id


def test_reject_evaluation_without_identity() -> None:
    with pytest.raises(InvalidEvaluationError, match="identity"):
        make_evaluation(id=None)


def test_reject_evaluation_with_invalid_identity() -> None:
    with pytest.raises(InvalidEvaluationError, match="identity"):
        make_evaluation(id="not-a-uuid")


# ---------------------------------------------------------------------------
# Submission association (FR-002 / DR-002)
# ---------------------------------------------------------------------------


def test_evaluation_references_submission_by_identity() -> None:
    submission = make_submitted_submission()

    evaluation = make_evaluation(submission_id=submission.id)

    assert evaluation.submission_id == submission.id
    # The submission is referenced by identity only; it is not duplicated.
    assert not hasattr(evaluation, "submission")


def test_reject_evaluation_without_submission() -> None:
    with pytest.raises(InvalidEvaluationError, match="submission"):
        make_evaluation(submission_id=None)


def test_reject_evaluation_with_invalid_submission() -> None:
    with pytest.raises(InvalidEvaluationError, match="submission"):
        make_evaluation(submission_id="submission-1")


# ---------------------------------------------------------------------------
# Findings (FR-003 / FR-011 / DR-003)
# ---------------------------------------------------------------------------


def test_evaluation_requires_at_least_one_finding() -> None:
    with pytest.raises(InvalidEvaluationError, match="at least one finding"):
        make_evaluation(findings=())


def test_evaluation_rejects_non_finding_items() -> None:
    with pytest.raises(InvalidEvaluationError, match="EvaluationFinding"):
        make_evaluation(findings=("not-a-finding",))


def test_evaluation_preserves_finding_identity() -> None:
    finding = make_finding()
    evaluation = make_evaluation(findings=(finding,))

    assert evaluation.findings[0] == finding
    assert evaluation.findings[0].id == finding.id


def test_evaluation_with_multiple_findings() -> None:
    first = make_finding(observation="A clear strength in the response.")
    second = make_finding(observation="An area that needs improvement.")

    evaluation = make_evaluation(findings=(first, second))

    assert len(evaluation.findings) == 2
    assert evaluation.findings[0] == first
    assert evaluation.findings[1] == second


# ---------------------------------------------------------------------------
# Finding identity (FR-004)
# ---------------------------------------------------------------------------


def test_finding_identity_is_unique_across_instances() -> None:
    first = make_finding()
    second = make_finding()

    assert first.id != second.id


def test_finding_identity_remains_stable() -> None:
    finding = make_finding()
    original_id = finding.id

    assert finding.id == original_id
    with pytest.raises(FrozenInstanceError):
        finding.id = uuid4()  # type: ignore[misc]


def test_finding_with_explicit_identity() -> None:
    finding_id = uuid4()

    finding = make_finding(id=finding_id)

    assert finding.id == finding_id


def test_findings_are_referenceable_by_identity_without_position() -> None:
    target = make_finding(observation="A specific observation.")
    other = make_finding(observation="Another observation.")
    evaluation = make_evaluation(findings=(other, target))

    by_identity = next(
        finding for finding in evaluation.findings if finding.id == target.id
    )

    assert by_identity.observation == "A specific observation."


def test_reject_finding_without_identity() -> None:
    with pytest.raises(InvalidEvaluationFindingError, match="identity"):
        make_finding(id=None)


def test_reject_finding_with_invalid_identity() -> None:
    with pytest.raises(InvalidEvaluationFindingError, match="identity"):
        make_finding(id="not-a-uuid")


# ---------------------------------------------------------------------------
# Finding validity (FR-005 / DR-004)
# ---------------------------------------------------------------------------


def test_create_finding_with_valid_observation() -> None:
    finding = make_finding(observation="The response addresses the core prompt.")

    assert finding.observation == "The response addresses the core prompt."


def test_reject_finding_without_observation() -> None:
    with pytest.raises(InvalidEvaluationFindingError, match="observation"):
        make_finding(observation=None)


def test_reject_finding_with_empty_observation() -> None:
    with pytest.raises(InvalidEvaluationFindingError, match="observation"):
        make_finding(observation="")


def test_reject_finding_with_blank_observation() -> None:
    with pytest.raises(InvalidEvaluationFindingError, match="observation"):
        make_finding(observation="   ")


def test_evaluation_rejects_invalid_finding() -> None:
    # An invalid finding is rejected at construction by the Finding model;
    # InvalidEvaluationFindingError is a subclass of InvalidEvaluationError.
    with pytest.raises(InvalidEvaluationError, match="observation"):
        make_finding(observation="")


def test_evaluation_rejects_non_tuple_findings() -> None:
    with pytest.raises(InvalidEvaluationError, match="tuple"):
        make_evaluation(findings=[make_finding()])


# ---------------------------------------------------------------------------
# Evaluation timestamp (FR-006 / DR-005)
# ---------------------------------------------------------------------------


def test_evaluation_records_evaluation_timestamp() -> None:
    evaluated_at = datetime.now(UTC) - timedelta(minutes=5)

    evaluation = make_evaluation(evaluated_at=evaluated_at)

    assert evaluation.evaluated_at == evaluated_at


def test_evaluation_timestamp_is_timezone_aware() -> None:
    evaluation = make_evaluation()

    assert evaluation.evaluated_at is not None
    assert evaluation.evaluated_at.tzinfo is not None


def test_reject_evaluation_without_timestamp() -> None:
    with pytest.raises(InvalidEvaluationError, match="when it occurred"):
        make_evaluation(evaluated_at=None)


def test_reject_evaluation_with_naive_timestamp() -> None:
    with pytest.raises(InvalidEvaluationError, match="timezone-aware"):
        make_evaluation(evaluated_at=datetime(2026, 8, 9, 12, 0, 0))


# ---------------------------------------------------------------------------
# Immutability (FR-007 / DR-006)
# ---------------------------------------------------------------------------


def test_evaluation_cannot_be_silently_modified() -> None:
    evaluation = make_evaluation()

    with pytest.raises(FrozenInstanceError):
        evaluation.submission_id = uuid4()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        evaluation.findings = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        evaluation.evaluated_at = datetime.now(UTC)  # type: ignore[misc]


def test_replace_cannot_create_invalid_evaluation() -> None:
    evaluation = make_evaluation()

    with pytest.raises(InvalidEvaluationError, match="at least one finding"):
        replace(evaluation, findings=())


def test_finding_cannot_be_silently_modified() -> None:
    finding = make_finding()

    with pytest.raises(FrozenInstanceError):
        finding.observation = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Submission preservation (FR-008 / DR-007)
# ---------------------------------------------------------------------------


def test_creating_evaluation_does_not_modify_submission() -> None:
    submission = make_submitted_submission()
    original_response = submission.response
    original_status = submission.status

    make_evaluation(submission_id=submission.id)

    assert submission.response == original_response
    assert submission.status is original_status
    assert submission.submitted_at is not None


# ---------------------------------------------------------------------------
# No mandatory score (FR-009 / DR-008)
# ---------------------------------------------------------------------------


def test_evaluation_does_not_require_a_score() -> None:
    evaluation = make_evaluation()

    assert not hasattr(evaluation, "score")
    # An evaluation without a score is valid.
    assert isinstance(evaluation, Evaluation)


# ---------------------------------------------------------------------------
# Domain boundaries (DR-009 / DR-010 / DR-011 / DR-012)
# ---------------------------------------------------------------------------


def test_evaluation_has_no_feedback_or_provider_concerns() -> None:
    evaluation = make_evaluation()

    assert not hasattr(evaluation, "feedback")
    assert not hasattr(evaluation, "provider")
    assert not hasattr(evaluation, "model")
    assert not hasattr(evaluation, "prompt")
    assert not hasattr(evaluation, "score")


def test_evaluation_source_has_no_persistence_dependencies() -> None:
    for module in ("sqlalchemy", "psycopg", "redis", "sqlite3", "motor"):
        assert f"import {module}" not in EVALUATION_SOURCE
        assert f"from {module}" not in EVALUATION_SOURCE


def test_evaluation_source_has_no_framework_dependencies() -> None:
    for module in ("fastapi", "pydantic", "uvicorn"):
        assert f"import {module}" not in EVALUATION_SOURCE
        assert f"from {module}" not in EVALUATION_SOURCE


@pytest.mark.parametrize("forbidden", ["NIFT", "NID", "CEED"])
def test_evaluation_source_has_no_examination_specific_terminology(
    forbidden: str,
) -> None:
    assert forbidden.lower() not in EVALUATION_SOURCE.lower()


def test_evaluation_is_usable_in_memory_without_infrastructure() -> None:
    evaluation = make_evaluation()

    assert isinstance(evaluation, Evaluation)
    assert isinstance(evaluation.findings[0], EvaluationFinding)
