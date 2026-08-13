"""Unit tests for the Reflection domain model (SPEC-009)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import fablit.domain.reflection
from fablit.domain import (
    Feedback,
    InvalidReflectionError,
    Reflection,
)

from .helpers import make_feedback, make_reflection

REFLECTION_SOURCE = Path(fablit.domain.reflection.__file__).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Creation and identity (FR-001 / DR-001)
# ---------------------------------------------------------------------------


def test_create_reflection_with_valid_data() -> None:
    feedback = make_feedback()

    reflection = make_reflection(feedback_id=feedback.id)

    assert isinstance(reflection.id, UUID)
    assert reflection.feedback_id == feedback.id
    assert reflection.content
    assert reflection.created_at is not None


def test_create_reflection_with_generated_identity() -> None:
    reflection = make_reflection()

    assert isinstance(reflection.id, UUID)


def test_reflection_identity_is_unique_across_instances() -> None:
    first = make_reflection()
    second = make_reflection()

    assert first.id != second.id


def test_reflection_identity_remains_stable() -> None:
    reflection = make_reflection()
    original_id = reflection.id

    assert reflection.id == original_id
    with pytest.raises(FrozenInstanceError):
        reflection.id = uuid4()  # type: ignore[misc]


def test_reflection_with_explicit_identity() -> None:
    reflection_id = uuid4()

    reflection = make_reflection(id=reflection_id)

    assert reflection.id == reflection_id


def test_reject_reflection_without_identity() -> None:
    with pytest.raises(InvalidReflectionError, match="identity"):
        make_reflection(id=None)


def test_reject_reflection_with_invalid_identity() -> None:
    with pytest.raises(InvalidReflectionError, match="identity"):
        make_reflection(id="not-a-uuid")


# ---------------------------------------------------------------------------
# Feedback association (FR-002 / DR-002)
# ---------------------------------------------------------------------------


def test_reflection_references_feedback_by_identity() -> None:
    feedback = make_feedback()

    reflection = make_reflection(feedback_id=feedback.id)

    assert reflection.feedback_id == feedback.id
    # The feedback is referenced by identity only; it is not duplicated.
    assert not hasattr(reflection, "feedback")


def test_reject_reflection_without_feedback() -> None:
    with pytest.raises(InvalidReflectionError, match="feedback"):
        make_reflection(feedback_id=None)


def test_reject_reflection_with_invalid_feedback() -> None:
    with pytest.raises(InvalidReflectionError, match="feedback"):
        make_reflection(feedback_id="feedback-1")


# ---------------------------------------------------------------------------
# Content validity (FR-003 / FR-004 / DR-003 / DR-004)
# ---------------------------------------------------------------------------


def test_create_reflection_with_meaningful_content() -> None:
    content = "I understand my mistake now and will practise it again tomorrow."
    reflection = make_reflection(content=content)

    assert reflection.content == content


def test_reject_reflection_without_content() -> None:
    with pytest.raises(InvalidReflectionError, match="content"):
        make_reflection(content=None)


def test_reject_reflection_with_empty_content() -> None:
    with pytest.raises(InvalidReflectionError, match="content"):
        make_reflection(content="")


def test_reject_reflection_with_whitespace_only_content() -> None:
    with pytest.raises(InvalidReflectionError, match="content"):
        make_reflection(content="   \n\t ")


def test_reject_reflection_with_non_string_content() -> None:
    with pytest.raises(InvalidReflectionError, match="content"):
        make_reflection(content=42)


# ---------------------------------------------------------------------------
# Creation timestamp (FR-006 / DR-005)
# ---------------------------------------------------------------------------


def test_reflection_records_creation_timestamp() -> None:
    created_at = datetime.now(UTC) - timedelta(minutes=5)

    reflection = make_reflection(created_at=created_at)

    assert reflection.created_at == created_at


def test_reflection_timestamp_is_timezone_aware() -> None:
    reflection = make_reflection()

    assert reflection.created_at is not None
    assert reflection.created_at.tzinfo is not None


def test_reject_reflection_without_timestamp() -> None:
    with pytest.raises(InvalidReflectionError, match="when it was created"):
        make_reflection(created_at=None)


def test_reject_reflection_with_naive_timestamp() -> None:
    with pytest.raises(InvalidReflectionError, match="timezone-aware"):
        make_reflection(created_at=datetime(2026, 8, 11, 12, 0, 0))


# ---------------------------------------------------------------------------
# Immutability (FR-007 / DR-006)
# ---------------------------------------------------------------------------


def test_reflection_cannot_be_silently_modified() -> None:
    reflection = make_reflection()

    with pytest.raises(FrozenInstanceError):
        reflection.feedback_id = uuid4()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        reflection.content = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        reflection.created_at = datetime.now(UTC)  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        reflection.id = uuid4()  # type: ignore[misc]


def test_replace_cannot_create_invalid_reflection() -> None:
    reflection = make_reflection()

    with pytest.raises(InvalidReflectionError, match="content"):
        replace(reflection, content="")


# ---------------------------------------------------------------------------
# Feedback preservation (FR-008 / DR-007)
# ---------------------------------------------------------------------------


def test_creating_reflection_does_not_modify_feedback() -> None:
    feedback = make_feedback()
    original_evaluation_id = feedback.evaluation_id
    original_content = feedback.content
    original_created_at = feedback.created_at

    make_reflection(feedback_id=feedback.id)

    assert feedback.evaluation_id == original_evaluation_id
    assert feedback.content == original_content
    assert feedback.created_at == original_created_at
    assert isinstance(feedback, Feedback)


# ---------------------------------------------------------------------------
# No mandatory confidence score (FR-009 / DR-008)
# ---------------------------------------------------------------------------


def test_reflection_does_not_require_a_confidence_score() -> None:
    reflection = make_reflection()

    assert not hasattr(reflection, "confidence")
    assert not hasattr(reflection, "score")
    # A reflection without a confidence score is valid.
    assert isinstance(reflection, Reflection)


# ---------------------------------------------------------------------------
# No mandatory improvement goal (FR-010 / DR-009)
# ---------------------------------------------------------------------------


def test_reflection_does_not_require_an_improvement_goal() -> None:
    reflection = make_reflection()

    assert not hasattr(reflection, "goal")
    assert not hasattr(reflection, "action_plan")
    # A reflection without a separate goal or action plan is valid.
    assert isinstance(reflection, Reflection)


# ---------------------------------------------------------------------------
# Domain boundaries (DR-010 / DR-011 / DR-012)
# ---------------------------------------------------------------------------


def test_reflection_has_no_generation_or_scoring_concerns() -> None:
    reflection = make_reflection()

    assert not hasattr(reflection, "provider")
    assert not hasattr(reflection, "model")
    assert not hasattr(reflection, "prompt")
    assert not hasattr(reflection, "score")
    assert not hasattr(reflection, "progress")


def test_reflection_source_has_no_persistence_dependencies() -> None:
    for module in ("sqlalchemy", "psycopg", "redis", "sqlite3", "motor"):
        assert f"import {module}" not in REFLECTION_SOURCE
        assert f"from {module}" not in REFLECTION_SOURCE


def test_reflection_source_has_no_framework_dependencies() -> None:
    for module in ("fastapi", "pydantic", "uvicorn"):
        assert f"import {module}" not in REFLECTION_SOURCE
        assert f"from {module}" not in REFLECTION_SOURCE


@pytest.mark.parametrize("forbidden", ["NIFT", "NID", "CEED"])
def test_reflection_source_has_no_examination_specific_terminology(
    forbidden: str,
) -> None:
    assert forbidden.lower() not in REFLECTION_SOURCE.lower()


def test_reflection_is_usable_in_memory_without_infrastructure() -> None:
    reflection = make_reflection()

    assert isinstance(reflection, Reflection)
    assert reflection.feedback_id is not None
