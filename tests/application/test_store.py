"""Unit tests for the in-memory learner journey store (SPEC-012)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from fablit.application import (
    DEMO_LEARNER_ID,
    ActivityNotFoundError,
    FeedbackNotFoundError,
    JourneyStateError,
    LearnerJourneyStore,
    build_demo_activities,
    build_demo_skills,
)


def make_store() -> LearnerJourneyStore:
    """Build a store seeded with the demo content."""
    return LearnerJourneyStore(
        learner_id=DEMO_LEARNER_ID,
        activities=build_demo_activities(),
        skills=build_demo_skills(),
    )


def test_unknown_activity_raises() -> None:
    store = make_store()

    with pytest.raises(ActivityNotFoundError):
        store.get_activity(uuid4())


def test_unknown_skill_raises_journey_error() -> None:
    store = make_store()

    with pytest.raises(JourneyStateError):
        store.get_skill(uuid4())


def test_missing_submission_raises_journey_error() -> None:
    store = make_store()

    with pytest.raises(JourneyStateError):
        store.get_submission(uuid4())


def test_missing_evaluation_raises_journey_error() -> None:
    store = make_store()

    with pytest.raises(JourneyStateError):
        store.get_evaluation(uuid4())


def test_current_feedback_requires_a_recorded_feedback() -> None:
    store = make_store()

    with pytest.raises(FeedbackNotFoundError):
        store.current_feedback()

    store.set_current_feedback(uuid4())
    with pytest.raises(FeedbackNotFoundError):
        store.current_feedback()


def test_list_activities_returns_deterministic_order() -> None:
    store = make_store()

    positions = [item.activity.position for item in store.list_activities()]

    assert positions == sorted(positions)
    assert len(positions) == 5
