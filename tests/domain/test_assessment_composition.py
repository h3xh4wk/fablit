"""Integration tests for Assessment composition and ordering (SPEC-005)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fablit.domain import (
    DuplicateActivityPositionError,
    InvalidAssessmentError,
)

from .helpers import make_activity, make_assessment


def test_assessment_with_single_activity() -> None:
    assessment = make_assessment(
        activities=(make_activity(position=0),),
    )

    assert len(assessment.activities) == 1
    assert assessment.ordered_activities()[0].position == 0


def test_assessment_with_multiple_activities() -> None:
    activities = tuple(make_activity(position=position) for position in range(5))
    assessment = make_assessment(activities=activities)

    assert len(assessment.activities) == 5
    assert assessment.ordered_activities() == activities


def test_activities_maintain_deterministic_order() -> None:
    assessment = make_assessment(
        activities=(
            make_activity(instructions="first", position=0),
            make_activity(instructions="second", position=1),
            make_activity(instructions="third", position=2),
        ),
    )

    ordered = assessment.ordered_activities()
    assert [activity.instructions for activity in ordered] == [
        "first",
        "second",
        "third",
    ]
    assert [activity.position for activity in ordered] == [0, 1, 2]


def test_reject_assessment_with_duplicate_activity_positions() -> None:
    with pytest.raises(DuplicateActivityPositionError, match="share positions"):
        make_assessment(
            activities=(
                make_activity(position=0),
                make_activity(position=0),
            ),
        )


def test_reject_assessment_with_duplicate_non_zero_positions() -> None:
    with pytest.raises(DuplicateActivityPositionError, match="share positions"):
        make_assessment(
            activities=(
                make_activity(position=1),
                make_activity(position=1),
            ),
        )


def test_reject_assessment_with_non_sequential_positions() -> None:
    with pytest.raises(InvalidAssessmentError, match="sequential"):
        make_assessment(
            activities=(
                make_activity(position=0),
                make_activity(position=2),
            ),
        )


def test_reject_assessment_with_missing_first_position() -> None:
    with pytest.raises(InvalidAssessmentError, match="sequential"):
        make_assessment(
            activities=(
                make_activity(position=1),
                make_activity(position=2),
            ),
        )


def test_reject_assessment_with_out_of_order_positions() -> None:
    with pytest.raises(InvalidAssessmentError, match="sequential"):
        make_assessment(
            activities=(
                make_activity(position=1),
                make_activity(position=0),
            ),
        )


def test_retrieve_activities_in_correct_order_from_assessment() -> None:
    assessment = make_assessment(
        activities=(
            make_activity(instructions="a", position=0),
            make_activity(instructions="b", position=1),
            make_activity(instructions="c", position=2),
        ),
    )

    assert [activity.instructions for activity in assessment.ordered_activities()] == [
        "a",
        "b",
        "c",
    ]


def test_modify_assessment_while_preserving_order_integrity() -> None:
    assessment = make_assessment(
        activities=(
            make_activity(position=0),
            make_activity(position=1),
        ),
    )

    renamed = replace(assessment, title="Renamed Practice")

    assert renamed.title == "Renamed Practice"
    assert renamed.id == assessment.id
    assert [a.position for a in renamed.activities] == [0, 1]

    with pytest.raises(InvalidAssessmentError, match="sequential"):
        replace(
            assessment,
            activities=(
                make_activity(position=0),
                make_activity(position=5),
            ),
        )


def test_activity_count_matches_expected() -> None:
    assessment = make_assessment(
        activities=(
            make_activity(position=0),
            make_activity(position=1),
            make_activity(position=2),
        ),
    )

    assert len(assessment.activities) == 3
