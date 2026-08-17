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
from tests.domain.helpers import make_stimulus


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


# --- Stimulus records (SPEC-015 §16, §18, §19) --------------------------------


def test_no_current_stimulus_before_resolution() -> None:
    store = make_store()
    activity_id = store.list_activities()[0].activity.id

    assert store.current_stimulus(activity_id) is None
    assert store.recorded_stimuli() == ()


def test_set_and_retrieve_current_stimulus() -> None:
    store = make_store()
    activity_id = store.list_activities()[0].activity.id
    stimulus = make_stimulus(activity_id=activity_id)

    store.set_current_stimulus(stimulus)

    assert store.current_stimulus(activity_id) == stimulus
    assert store.recorded_stimuli() == (stimulus,)


def test_current_stimulus_is_scoped_to_its_activity() -> None:
    store = make_store()
    first, second = store.list_activities()[:2]
    stimulus = make_stimulus(activity_id=first.activity.id)
    store.set_current_stimulus(stimulus)

    assert store.current_stimulus(first.activity.id) == stimulus
    assert store.current_stimulus(second.activity.id) is None


def test_setting_a_new_stimulus_replaces_the_current_one() -> None:
    store = make_store()
    activity_id = store.list_activities()[0].activity.id
    first = make_stimulus(activity_id=activity_id)
    second = make_stimulus(activity_id=activity_id)

    store.set_current_stimulus(first)
    store.set_current_stimulus(second)

    assert store.current_stimulus(activity_id) == second
    # Both remain recorded so the historical stimulus is never lost (§18).
    assert len(store.recorded_stimuli()) == 2


def test_save_and_get_stimulus_by_identity() -> None:
    store = make_store()
    stimulus = make_stimulus()

    store.save_stimulus(stimulus)

    assert store.get_stimulus(stimulus.id) == stimulus


def test_missing_stimulus_raises_journey_error() -> None:
    store = make_store()

    with pytest.raises(JourneyStateError):
        store.get_stimulus(uuid4())
