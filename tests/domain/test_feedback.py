"""Unit tests for the Feedback domain model (SPEC-008)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import fablit.domain.feedback
from fablit.domain import (
    Evaluation,
    Feedback,
    InvalidFeedbackError,
)

from .helpers import make_evaluation, make_feedback

FEEDBACK_SOURCE = Path(fablit.domain.feedback.__file__).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Creation and identity (FR-001 / DR-001)
# ---------------------------------------------------------------------------


def test_create_feedback_with_valid_data() -> None:
    evaluation = make_evaluation()

    feedback = make_feedback(evaluation_id=evaluation.id)

    assert isinstance(feedback.id, UUID)
    assert feedback.evaluation_id == evaluation.id
    assert feedback.content
    assert feedback.created_at is not None


def test_create_feedback_with_generated_identity() -> None:
    feedback = make_feedback()

    assert isinstance(feedback.id, UUID)


def test_feedback_identity_is_unique_across_instances() -> None:
    first = make_feedback()
    second = make_feedback()

    assert first.id != second.id


def test_feedback_identity_remains_stable() -> None:
    feedback = make_feedback()
    original_id = feedback.id

    assert feedback.id == original_id
    with pytest.raises(FrozenInstanceError):
        feedback.id = uuid4()  # type: ignore[misc]


def test_feedback_with_explicit_identity() -> None:
    feedback_id = uuid4()

    feedback = make_feedback(id=feedback_id)

    assert feedback.id == feedback_id


def test_reject_feedback_without_identity() -> None:
    with pytest.raises(InvalidFeedbackError, match="identity"):
        make_feedback(id=None)


def test_reject_feedback_with_invalid_identity() -> None:
    with pytest.raises(InvalidFeedbackError, match="identity"):
        make_feedback(id="not-a-uuid")


# ---------------------------------------------------------------------------
# Evaluation association (FR-002 / DR-002)
# ---------------------------------------------------------------------------


def test_feedback_references_evaluation_by_identity() -> None:
    evaluation = make_evaluation()

    feedback = make_feedback(evaluation_id=evaluation.id)

    assert feedback.evaluation_id == evaluation.id
    # The evaluation is referenced by identity only; it is not duplicated.
    assert not hasattr(feedback, "evaluation")


def test_reject_feedback_without_evaluation() -> None:
    with pytest.raises(InvalidFeedbackError, match="evaluation"):
        make_feedback(evaluation_id=None)


def test_reject_feedback_with_invalid_evaluation() -> None:
    with pytest.raises(InvalidFeedbackError, match="evaluation"):
        make_feedback(evaluation_id="evaluation-1")


# ---------------------------------------------------------------------------
# Content validity (FR-003 / FR-004 / DR-003 / DR-004)
# ---------------------------------------------------------------------------


def test_create_feedback_with_meaningful_content() -> None:
    content = "Your response shows a strength; try one more example."
    feedback = make_feedback(content=content)

    assert feedback.content == content


def test_reject_feedback_without_content() -> None:
    with pytest.raises(InvalidFeedbackError, match="guidance"):
        make_feedback(content=None)


def test_reject_feedback_with_empty_content() -> None:
    with pytest.raises(InvalidFeedbackError, match="guidance"):
        make_feedback(content="")


def test_reject_feedback_with_whitespace_only_content() -> None:
    with pytest.raises(InvalidFeedbackError, match="guidance"):
        make_feedback(content="   \n\t ")


def test_reject_feedback_with_non_string_content() -> None:
    with pytest.raises(InvalidFeedbackError, match="guidance"):
        make_feedback(content=42)


# ---------------------------------------------------------------------------
# Creation timestamp (FR-005 / DR-005)
# ---------------------------------------------------------------------------


def test_feedback_records_creation_timestamp() -> None:
    created_at = datetime.now(UTC) - timedelta(minutes=5)

    feedback = make_feedback(created_at=created_at)

    assert feedback.created_at == created_at


def test_feedback_timestamp_is_timezone_aware() -> None:
    feedback = make_feedback()

    assert feedback.created_at is not None
    assert feedback.created_at.tzinfo is not None


def test_reject_feedback_without_timestamp() -> None:
    with pytest.raises(InvalidFeedbackError, match="when it was created"):
        make_feedback(created_at=None)


def test_reject_feedback_with_naive_timestamp() -> None:
    with pytest.raises(InvalidFeedbackError, match="timezone-aware"):
        make_feedback(created_at=datetime(2026, 8, 11, 12, 0, 0))


# ---------------------------------------------------------------------------
# Immutability (FR-006 / DR-006)
# ---------------------------------------------------------------------------


def test_feedback_cannot_be_silently_modified() -> None:
    feedback = make_feedback()

    with pytest.raises(FrozenInstanceError):
        feedback.evaluation_id = uuid4()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        feedback.content = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        feedback.created_at = datetime.now(UTC)  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        feedback.id = uuid4()  # type: ignore[misc]


def test_replace_cannot_create_invalid_feedback() -> None:
    feedback = make_feedback()

    with pytest.raises(InvalidFeedbackError, match="guidance"):
        replace(feedback, content="")


# ---------------------------------------------------------------------------
# Evaluation preservation (FR-007 / DR-007)
# ---------------------------------------------------------------------------


def test_creating_feedback_does_not_modify_evaluation() -> None:
    evaluation = make_evaluation()
    original_findings = evaluation.findings
    original_evaluated_at = evaluation.evaluated_at

    make_feedback(evaluation_id=evaluation.id)

    assert evaluation.findings == original_findings
    assert evaluation.evaluated_at == original_evaluated_at
    assert isinstance(evaluation, Evaluation)


# ---------------------------------------------------------------------------
# No mandatory score (FR-008 / DR-008)
# ---------------------------------------------------------------------------


def test_feedback_does_not_require_a_score() -> None:
    feedback = make_feedback()

    assert not hasattr(feedback, "score")
    # A feedback without a score is valid.
    assert isinstance(feedback, Feedback)


# ---------------------------------------------------------------------------
# Domain boundaries (DR-009 / DR-010 / DR-011 / DR-012)
# ---------------------------------------------------------------------------


def test_feedback_has_no_reflection_or_provider_concerns() -> None:
    feedback = make_feedback()

    assert not hasattr(feedback, "reflection")
    assert not hasattr(feedback, "provider")
    assert not hasattr(feedback, "model")
    assert not hasattr(feedback, "prompt")
    assert not hasattr(feedback, "score")


def test_feedback_source_has_no_persistence_dependencies() -> None:
    for module in ("sqlalchemy", "psycopg", "redis", "sqlite3", "motor"):
        assert f"import {module}" not in FEEDBACK_SOURCE
        assert f"from {module}" not in FEEDBACK_SOURCE


def test_feedback_source_has_no_framework_dependencies() -> None:
    for module in ("fastapi", "pydantic", "uvicorn"):
        assert f"import {module}" not in FEEDBACK_SOURCE
        assert f"from {module}" not in FEEDBACK_SOURCE


@pytest.mark.parametrize("forbidden", ["NIFT", "NID", "CEED"])
def test_feedback_source_has_no_examination_specific_terminology(
    forbidden: str,
) -> None:
    assert forbidden.lower() not in FEEDBACK_SOURCE.lower()


def test_feedback_is_usable_in_memory_without_infrastructure() -> None:
    feedback = make_feedback()

    assert isinstance(feedback, Feedback)
    assert feedback.evaluation_id is not None
