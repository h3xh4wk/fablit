"""Application-layer tests for metacognitive practice integration (SPEC-026).

Covers the optional pre-practice intention lifecycle (§2.1): capture, echo
in the active workspace, attachment to the session payload at submission,
and retry behaviour after evaluation failure (§64 semantics preserved).
Covers the optional post-evaluation reflection (§2.2): skip paths, empty-
field acceptance, and that skipping never blocks completion or history
persistence for a *saved* reflection. Covers the chronological review
extension (§2.3): intention and reflection rendered alongside evaluation
results. No scoring, analytics, or automated feedback is derived from
intentions or reflections (§4).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from fablit.application import (
    EvaluationFailedError,
    IntentionView,
    InvalidReflectionResponseError,
    ReflectionView,
)
from fablit.application.persistence import PracticeHistoryRepository
from fablit.application.repositories import InMemoryPracticeHistoryRepository

from .test_practice_application import (
    first_activity_id,
    make_application,
    second_activity_id,
)
from .test_practice_history import (
    LEARNER,
    complete_first_practice,
    make_history_application,
)

# --- SPEC-026 §2.1: Pre-Practice Intention -------------------------------------


def test_get_intention_prepares_the_optional_prompt() -> None:
    application, _ = make_application()
    activity_id = first_activity_id(application)

    view = application.get_intention(activity_id)

    assert isinstance(view, IntentionView)
    assert view.activity_id == activity_id
    assert view.activity_title == "CAT Practice — 2D & 3D Composition Analysis"
    assert "specific focus" in view.prompt
    assert view.action_label == "Continue with intention"
    assert view.skip_label.startswith("Skip")


def test_set_intention_captures_a_stated_focus() -> None:
    application, store = make_application()
    activity_id = first_activity_id(application)

    application.set_intention(activity_id, "Focus on explicit variable naming.")

    assert store.pending_intention(activity_id) == "Focus on explicit variable naming."


def test_blank_intention_is_accepted_and_leaves_nothing_behind() -> None:
    """Submission with empty fields is accepted gracefully (§2.1)."""
    application, store = make_application()
    activity_id = first_activity_id(application)

    application.set_intention(activity_id, "   ")
    application.set_intention(activity_id, None)

    assert store.pending_intention(activity_id) is None


def test_intention_is_not_attached_to_a_different_activity() -> None:
    application, _ = make_application()
    first = first_activity_id(application)
    second = second_activity_id(application)

    application.set_intention(first, "Focus on composition.")

    assert second is not first
    assert application.start_practice(second).intention is None


def test_captured_intention_is_echoed_in_the_active_workspace() -> None:
    application, _ = make_application()
    activity_id = first_activity_id(application)

    application.set_intention(activity_id, "Verify boundary cases first.")
    view = application.start_practice(activity_id)

    assert view.intention == "Verify boundary cases first."


def test_intention_attaches_to_the_session_payload_at_submission() -> None:
    application, store = make_application()

    activity_id = first_activity_id(application)
    application.set_intention(activity_id, "Explain how two elements interact.")
    application.submit_response(activity_id, "The contrast is striking.")

    submission = store.recorded_submissions()[-1]
    assert submission.activity_id == activity_id
    assert submission.pre_practice_intention == ("Explain how two elements interact.")


def test_submission_without_intention_leaves_the_field_empty() -> None:
    application, store = make_application()

    application.submit_response(first_activity_id(application), "A response.")

    assert store.recorded_submissions()[-1].pre_practice_intention is None


def test_intention_survives_an_evaluation_failure_retry() -> None:
    """§64: a failed evaluation must not lose the learner's context."""

    class FailingEvaluator:
        def evaluate(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("evaluator failure")

    application, store = make_application(evaluator=FailingEvaluator())
    activity_id = first_activity_id(application)

    application.set_intention(activity_id, "Focus on the negative space.")
    with pytest.raises(EvaluationFailedError):
        application.submit_response(activity_id, "A response.")

    # The intention is still pending, so the learner's retry keeps it.
    assert store.pending_intention(activity_id) == "Focus on the negative space."


def test_get_reflection_shows_the_structured_prompts_and_intention() -> None:
    application, _ = make_application()

    activity_id = first_activity_id(application)
    application.set_intention(activity_id, "Watch for leading lines.")
    application.submit_response(activity_id, "The contrast is striking.")

    view = application.get_reflection()

    assert isinstance(view, ReflectionView)
    assert view.prompts == (
        "What strategy or mental model did you use to complete this activity?",
        "What was the primary friction point or misconception you encountered?",
    )
    assert view.intention == "Watch for leading lines."


# --- SPEC-026 §2.2: Skipping never blocks ---------------------------------------


def test_skipped_reflection_completes_the_practice() -> None:
    application, store = make_application()

    application.submit_response(first_activity_id(application), "A response.")
    view = application.submit_reflection(None)

    assert "completed this practice" in view.message
    assert "reflection has been recorded" not in view.message
    completions = store.recorded_completions()
    assert len(completions) == 1
    assert completions[0].reflection_id is None


def test_skipped_reflection_still_reaches_completion_confirmation() -> None:
    application, _ = make_application()

    application.submit_response(first_activity_id(application), "A response.")
    application.submit_reflection(None)

    # get_completion() no longer requires a saved Reflection.
    assert "completed this practice" in application.get_completion().message


def test_saved_reflection_still_persists_to_durable_history() -> None:
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)

    complete_first_practice(application)

    summaries = repository.list_completions(LEARNER)
    assert len(summaries) == 1


def test_skip_and_save_are_independent_completions() -> None:
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    application.submit_response(activity_id, "First attempt.")
    application.submit_reflection(None)  # skip: in-memory completion only
    application.submit_response(activity_id, "Second attempt.")
    application.submit_reflection("I will slow down next time.")  # saved

    summaries = repository.list_completions(LEARNER)
    assert len(summaries) == 1  # only the saved reflection made history


def test_skip_does_not_block_a_later_saved_reflection() -> None:
    repository: PracticeHistoryRepository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    application.submit_response(activity_id, "A response.")
    application.submit_reflection(None)
    application.submit_response(activity_id, "A better response.")
    application.submit_reflection("Next time I will describe interactions.")

    summaries = repository.list_completions(LEARNER)
    assert len(summaries) == 1
    view = application.get_practice_review(summaries[0].completion_id)
    assert view.reflection == "Next time I will describe interactions."


def test_invalid_non_string_reflection_is_still_rejected() -> None:
    application, store = make_application()

    application.submit_response(first_activity_id(application), "A response.")
    try:
        application.submit_reflection(123)  # type: ignore[arg-type]
    except InvalidReflectionResponseError:
        pass
    else:  # pragma: no cover - assertion guard
        raise AssertionError("non-string reflection must be rejected")

    assert store.recorded_completions() == ()


# --- SPEC-026 §2.3: History renders the whole artifact --------------------------


def test_review_renders_the_session_intention() -> None:
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    application.set_intention(activity_id, "Name the dominant visual elements.")
    application.submit_response(activity_id, "The contrast is striking.")
    application.submit_reflection("I will describe interactions next time.")

    summaries = repository.list_completions(LEARNER)
    view = application.get_practice_review(summaries[0].completion_id)

    assert view.pre_practice_intention == "Name the dominant visual elements."
    assert view.learner_response == "The contrast is striking."
    assert view.reflection == "I will describe interactions next time."


def test_review_without_an_intention_renders_none() -> None:
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)

    complete_first_practice(application)

    summaries = repository.list_completions(LEARNER)
    view = application.get_practice_review(summaries[0].completion_id)

    assert view.pre_practice_intention is None
    assert isinstance(view.activity_id, UUID)


def test_completion_message_reflects_the_current_completion_only() -> None:
    """A previously saved reflection must not leak into a later skipped one."""
    application, _ = make_application()
    activity_id = first_activity_id(application)

    # First journey: reflection saved.
    application.submit_response(activity_id, "First attempt.")
    application.submit_reflection("I will slow down next time.")
    assert "reflection has been recorded" in application.get_completion().message

    # Second journey: reflection skipped — the message must not claim it.
    application.start_practice(activity_id)
    application.submit_response(activity_id, "Second attempt.")
    view = application.submit_reflection(None)

    assert "reflection has been recorded" not in view.message
    assert "completed this practice" in view.message
