"""Unit tests for the Assessment Activity domain model (SPEC-005)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from fablit.domain import (
    ActivityStatus,
    ActivityType,
    AssessmentActivity,
    InvalidActivityError,
)

from .helpers import make_activity, make_assessment


def test_create_activity_with_valid_data() -> None:
    activity = make_activity(
        activity_type=ActivityType.MULTIPLE_CHOICE,
        instructions="Select the best option.",
        position=2,
        status=ActivityStatus.INACTIVE,
    )

    assert activity.activity_type is ActivityType.MULTIPLE_CHOICE
    assert activity.instructions == "Select the best option."
    assert activity.position == 2
    assert activity.status is ActivityStatus.INACTIVE
    assert isinstance(activity.id, UUID)


def test_create_activity_with_minimal_required_fields() -> None:
    activity = AssessmentActivity(
        activity_type=ActivityType.REFLECTION,
        instructions="Reflect on your approach.",
        position=0,
    )

    assert activity.activity_type is ActivityType.REFLECTION
    assert activity.position == 0
    assert isinstance(activity.id, UUID)
    assert activity.status is ActivityStatus.ACTIVE


def test_reject_activity_without_identity() -> None:
    with pytest.raises(InvalidActivityError, match="identity"):
        make_activity(id=None)


def test_reject_activity_with_invalid_identity() -> None:
    with pytest.raises(InvalidActivityError, match="identity"):
        make_activity(id="not-a-uuid")


def test_reject_activity_without_type() -> None:
    with pytest.raises(InvalidActivityError, match="activity type"):
        make_activity(activity_type=None)


def test_reject_activity_with_invalid_type() -> None:
    with pytest.raises(InvalidActivityError, match="activity type"):
        make_activity(activity_type="essay")


def test_reject_activity_without_instructions() -> None:
    with pytest.raises(InvalidActivityError, match="instructions"):
        make_activity(instructions="")


def test_reject_activity_with_blank_instructions() -> None:
    with pytest.raises(InvalidActivityError, match="instructions"):
        make_activity(instructions="   ")


def test_reject_activity_without_position() -> None:
    with pytest.raises(InvalidActivityError, match="position"):
        make_activity(position=None)


def test_reject_activity_with_negative_position() -> None:
    with pytest.raises(InvalidActivityError, match="position"):
        make_activity(position=-1)


def test_reject_activity_with_non_integer_position() -> None:
    with pytest.raises(InvalidActivityError, match="position"):
        make_activity(position=1.5)


def test_reject_activity_with_boolean_position() -> None:
    with pytest.raises(InvalidActivityError, match="position"):
        make_activity(position=True)


def test_reject_activity_with_invalid_status() -> None:
    with pytest.raises(InvalidActivityError, match="status"):
        make_activity(status="retired")


def test_every_activity_type_is_supported() -> None:
    for activity_type in ActivityType:
        activity = make_activity(activity_type=activity_type)
        assert activity.activity_type is activity_type


def test_activity_identity_is_unique_across_instances() -> None:
    first = make_activity()
    second = make_activity()

    assert first.id != second.id


def test_activity_identity_remains_stable() -> None:
    activity = make_activity()
    original_id = activity.id

    assert activity.id == original_id
    with pytest.raises(FrozenInstanceError):
        activity.id = uuid4()  # type: ignore[misc]


def test_activity_parent_reference_to_assessment() -> None:
    activity = make_activity(position=1)
    assessment = make_assessment(
        title="Interview Practice",
        activities=(make_activity(position=0), activity),
    )

    assert assessment.ordered_activities()[1] is activity
    assert activity in assessment.activities


def test_activity_type_validation_message_lists_valid_types() -> None:
    with pytest.raises(InvalidActivityError, match="multiple_choice"):
        make_activity(activity_type="essay")
