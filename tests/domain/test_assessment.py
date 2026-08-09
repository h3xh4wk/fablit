"""Unit tests for the Assessment domain model (SPEC-005)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from uuid import UUID, uuid4

import pytest

from fablit.domain import (
    AssessmentStatus,
    InvalidAssessmentError,
)

from .helpers import make_activity, make_assessment


def test_create_assessment_with_valid_data() -> None:
    assessment = make_assessment(
        title="Weekly Challenge",
        description="A weekly skill challenge.",
        status=AssessmentStatus.PUBLISHED,
    )

    assert assessment.title == "Weekly Challenge"
    assert assessment.description == "A weekly skill challenge."
    assert assessment.status is AssessmentStatus.PUBLISHED
    assert isinstance(assessment.id, UUID)
    assert len(assessment.activities) == 2


def test_create_assessment_with_minimal_required_fields() -> None:
    assessment = make_assessment(
        title="Mock Test",
        description="A timed mock test.",
        status=AssessmentStatus.DRAFT,
        activities=(make_activity(position=0),),
    )

    assert assessment.title == "Mock Test"
    assert len(assessment.activities) == 1


def test_reject_assessment_without_identity() -> None:
    with pytest.raises(InvalidAssessmentError, match="identity"):
        make_assessment(id=None)


def test_reject_assessment_without_title() -> None:
    with pytest.raises(InvalidAssessmentError, match="title"):
        make_assessment(title="")


def test_reject_assessment_with_blank_title() -> None:
    with pytest.raises(InvalidAssessmentError, match="title"):
        make_assessment(title="   ")


def test_reject_assessment_without_description() -> None:
    with pytest.raises(InvalidAssessmentError, match="description"):
        make_assessment(description="")


def test_reject_assessment_with_blank_description() -> None:
    with pytest.raises(InvalidAssessmentError, match="description"):
        make_assessment(description="   ")


def test_reject_assessment_without_status() -> None:
    with pytest.raises(InvalidAssessmentError, match="status"):
        make_assessment(status=None)


def test_reject_assessment_with_invalid_status() -> None:
    with pytest.raises(InvalidAssessmentError, match="status"):
        make_assessment(status="archived")


def test_reject_assessment_without_activities() -> None:
    with pytest.raises(InvalidAssessmentError, match="activity"):
        make_assessment(activities=())


def test_reject_assessment_with_non_activity_items() -> None:
    with pytest.raises(InvalidAssessmentError, match="AssessmentActivity"):
        make_assessment(activities=("not-an-activity",))


def test_assessment_identity_is_unique_across_instances() -> None:
    first = make_assessment()
    second = make_assessment()

    assert first.id != second.id


def test_assessment_identity_remains_stable() -> None:
    assessment = make_assessment()
    original_id = assessment.id

    assert assessment.id == original_id
    with pytest.raises(FrozenInstanceError):
        assessment.id = uuid4()  # type: ignore[misc]


def test_assessment_metadata_retrieval() -> None:
    assessment = make_assessment(
        title="Portfolio Review",
        description="A review of the learner's portfolio.",
        status=AssessmentStatus.PUBLISHED,
    )

    assert assessment.title == "Portfolio Review"
    assert assessment.description == "A review of the learner's portfolio."
    assert assessment.status is AssessmentStatus.PUBLISHED


def test_assessment_status_transition_via_replace() -> None:
    assessment = make_assessment(status=AssessmentStatus.DRAFT)

    published = replace(assessment, status=AssessmentStatus.PUBLISHED)

    assert assessment.status is AssessmentStatus.DRAFT
    assert published.status is AssessmentStatus.PUBLISHED
    assert published.id == assessment.id
