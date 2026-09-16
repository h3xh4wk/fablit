"""Application-layer tests for durable practice history (SPEC-021).

Covers the in-memory repository test double (SPEC-021 §13), the completion
boundary after successful reflection (§7), history ordering (§8), review
reconstruction with preserved stimulus context (§9–10), idempotent completion
persistence (§14), and explicit persistence failure behaviour (§14).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from fablit.application import (
    DEMO_LEARNER_ID,
    CompletionNotFoundError,
    DemoActivity,
    DemoEvaluator,
    InvalidReflectionResponseError,
    LearnerJourneyStore,
    PracticeApplication,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
    build_stimulus_provider,
)
from fablit.application.persistence import (
    PersistenceError,
    PracticeHistoryRepository,
    PracticeHistorySummary,
    StoredPracticeCompletion,
)
from fablit.application.repositories import InMemoryPracticeHistoryRepository
from fablit.domain import (
    Evaluation,
    EvaluationFinding,
    Feedback,
    Reflection,
    StimulusInstance,
    Submission,
)

LEARNER = DEMO_LEARNER_ID


def make_history_application(
    *,
    repository: PracticeHistoryRepository | None = None,
    clock: Callable[[], datetime] | None = None,
    activities: tuple[DemoActivity, ...] | None = None,
) -> PracticeApplication:
    """Build a practice application wired to the given history repository."""
    activities = activities if activities is not None else build_demo_activities()
    store = LearnerJourneyStore(
        learner_id=LEARNER,
        activities=activities,
        skills=build_demo_skills(),
    )
    return PracticeApplication(
        store=store,
        evaluator=DemoEvaluator(build_demo_activity_map(activities)),
        stimulus_provider=build_stimulus_provider(activities, provider_name="builtin"),
        history_repository=repository,
        clock=clock,
    )


def complete_first_practice(
    application: PracticeApplication, response: str = "The contrast is striking."
) -> None:
    """Drive one full journey: submit, then reflect, for the first activity."""
    activity_id = application.get_dashboard().activities[0].id
    application.submit_response(activity_id, response)
    application.submit_reflection("I will look for balance next time.")


def make_submission(
    *, learner_id: UUID | None = None, activity_id: UUID | None = None
) -> Submission:
    """Build a domain Submission with sensible defaults for repository tests."""
    return Submission(
        learner_id=learner_id or LEARNER,
        activity_id=activity_id or uuid4(),
        response="A considered response about composition.",
    ).submit(submitted_at=datetime.now(UTC))


def make_evaluation(submission: Submission) -> Evaluation:
    return Evaluation(
        submission_id=submission.id,
        findings=(EvaluationFinding(observation="You noticed the contrast."),),
        evaluated_at=datetime.now(UTC),
    )


def make_feedback(evaluation: Evaluation) -> Feedback:
    return Feedback(
        evaluation_id=evaluation.id,
        content="Strengths: You noticed the contrast.",
        created_at=datetime.now(UTC),
    )


def make_reflection(feedback: Feedback) -> Reflection:
    return Reflection(
        feedback_id=feedback.id,
        content="I will look for balance next time.",
        created_at=datetime.now(UTC),
    )


def make_stimulus(activity_id: UUID | None = None) -> StimulusInstance:
    return StimulusInstance(
        activity_id=activity_id or uuid4(),
        provider="fablit",
        image_url="/static/images/composition.svg",
        source_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
        retrieved_at=datetime.now(UTC),
        attribution="Example Author",
        alt_text="An example composition.",
    )


# --- In-memory repository behaviour (SPEC-021 §13) ----------------------------


def test_in_memory_repository_round_trips_a_completion() -> None:
    repository = InMemoryPracticeHistoryRepository()
    submission = make_submission()
    evaluation = make_evaluation(submission)
    feedback = make_feedback(evaluation)
    reflection = make_reflection(feedback)
    stimulus = make_stimulus()

    stored = repository.save_completion(
        learner_id=LEARNER,
        activity_id=submission.activity_id,
        activity_title="CAT Practice — 2D & 3D Composition Analysis",
        submission=submission,
        evaluation=evaluation,
        feedback=feedback,
        reflection=reflection,
        stimulus=stimulus,
    )
    retrieved = repository.get_completion(LEARNER, stored.completion_id)

    assert retrieved is not None
    assert retrieved.completion_id == reflection.id
    assert retrieved.activity_title == "CAT Practice — 2D & 3D Composition Analysis"
    assert retrieved.submission.response == submission.response
    assert retrieved.evaluation.id == evaluation.id
    assert retrieved.feedback.content == feedback.content
    assert retrieved.reflection.content == reflection.content
    assert retrieved.stimulus is not None
    assert retrieved.stimulus.image_url == stimulus.image_url
    assert retrieved.completed_at == reflection.created_at


def test_in_memory_repository_supports_no_stimulus() -> None:
    repository = InMemoryPracticeHistoryRepository()
    submission = make_submission()
    evaluation = make_evaluation(submission)
    feedback = make_feedback(evaluation)
    reflection = make_reflection(feedback)

    stored = repository.save_completion(
        learner_id=LEARNER,
        activity_id=submission.activity_id,
        activity_title="Text-only activity",
        submission=submission,
        evaluation=evaluation,
        feedback=feedback,
        reflection=reflection,
        stimulus=None,
    )
    retrieved = repository.get_completion(LEARNER, stored.completion_id)

    assert retrieved is not None
    assert retrieved.stimulus is None


def test_in_memory_repository_get_unknown_completion_returns_none() -> None:
    repository = InMemoryPracticeHistoryRepository()

    assert repository.get_completion(LEARNER, uuid4()) is None


def test_in_memory_repository_scopes_completions_to_the_learner() -> None:
    repository = InMemoryPracticeHistoryRepository()
    submission = make_submission()
    evaluation = make_evaluation(submission)
    feedback = make_feedback(evaluation)
    reflection = make_reflection(feedback)
    repository.save_completion(
        learner_id=LEARNER,
        activity_id=submission.activity_id,
        activity_title="A practice",
        submission=submission,
        evaluation=evaluation,
        feedback=feedback,
        reflection=reflection,
        stimulus=None,
    )

    other_learner = uuid4()
    assert repository.get_completion(other_learner, reflection.id) is None
    assert repository.list_completions(other_learner) == ()
    assert not repository.has_completed_activity(other_learner, submission.activity_id)


def test_in_memory_repository_orders_history_newest_first() -> None:
    repository = InMemoryPracticeHistoryRepository()

    def save_with_offset(seconds: int) -> StoredPracticeCompletion:
        submission = make_submission()
        evaluation = make_evaluation(submission)
        feedback = make_feedback(evaluation)
        created_at = datetime.now(UTC) - timedelta(seconds=seconds)
        reflection = Reflection(
            feedback_id=feedback.id,
            content=f"Reflection {seconds}",
            created_at=created_at,
        )
        return repository.save_completion(
            learner_id=LEARNER,
            activity_id=submission.activity_id,
            activity_title=f"Practice {seconds}",
            submission=submission,
            evaluation=evaluation,
            feedback=feedback,
            reflection=reflection,
            stimulus=None,
        )

    oldest = save_with_offset(200)
    middle = save_with_offset(100)
    newest = save_with_offset(0)

    summaries = repository.list_completions(LEARNER)

    assert [s.completion_id for s in summaries] == [
        newest.completion_id,
        middle.completion_id,
        oldest.completion_id,
    ]


def test_in_memory_repository_lists_empty_history() -> None:
    repository = InMemoryPracticeHistoryRepository()

    assert repository.list_completions(LEARNER) == ()


def test_in_memory_repository_summaries_carry_review_context() -> None:
    repository = InMemoryPracticeHistoryRepository()
    submission = make_submission()
    submission = Submission(
        learner_id=submission.learner_id,
        activity_id=submission.activity_id,
        response="The contrast between light and dark stands out immediately.",
    ).submit(submitted_at=datetime.now(UTC))
    evaluation = make_evaluation(submission)
    feedback = make_feedback(evaluation)
    reflection = make_reflection(feedback)
    repository.save_completion(
        learner_id=LEARNER,
        activity_id=submission.activity_id,
        activity_title="CAT Practice",
        submission=submission,
        evaluation=evaluation,
        feedback=feedback,
        reflection=reflection,
        stimulus=None,
    )

    summaries = repository.list_completions(LEARNER)

    assert len(summaries) == 1
    summary = summaries[0]
    assert isinstance(summary, PracticeHistorySummary)
    assert summary.activity_title == "CAT Practice"
    assert summary.completed_at == reflection.created_at
    assert summary.submission_preview.startswith("The contrast between")
    assert summary.completion_id == reflection.id


def test_in_memory_repository_truncates_long_previews() -> None:
    repository = InMemoryPracticeHistoryRepository()
    long_response = "x" * 200
    submission = Submission(
        learner_id=LEARNER,
        activity_id=uuid4(),
        response=long_response,
    ).submit(submitted_at=datetime.now(UTC))
    evaluation = make_evaluation(submission)
    feedback = make_feedback(evaluation)
    reflection = make_reflection(feedback)
    repository.save_completion(
        learner_id=LEARNER,
        activity_id=submission.activity_id,
        activity_title="Long response practice",
        submission=submission,
        evaluation=evaluation,
        feedback=feedback,
        reflection=reflection,
        stimulus=None,
    )

    summaries = repository.list_completions(LEARNER)

    preview = summaries[0].submission_preview
    assert len(preview) < len(long_response)
    assert preview.endswith("…")


def test_in_memory_repository_tracks_activity_completion() -> None:
    repository = InMemoryPracticeHistoryRepository()
    activity_id = uuid4()
    submission = make_submission(activity_id=activity_id)
    evaluation = make_evaluation(submission)
    feedback = make_feedback(evaluation)
    reflection = make_reflection(feedback)

    assert not repository.has_completed_activity(LEARNER, activity_id)
    repository.save_completion(
        learner_id=LEARNER,
        activity_id=activity_id,
        activity_title="Repeated practice",
        submission=submission,
        evaluation=evaluation,
        feedback=feedback,
        reflection=reflection,
        stimulus=None,
    )

    assert repository.has_completed_activity(LEARNER, activity_id)


# --- SPEC-021 §7: completion boundary -----------------------------------------


def test_completion_persisted_only_after_successful_reflection() -> None:
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    # Submission and evaluation alone must not create durable history (§7).
    application.submit_response(activity_id, "A response.")
    assert repository.list_completions(LEARNER) == ()

    application.submit_reflection("I will look for balance next time.")

    assert len(repository.list_completions(LEARNER)) == 1


def test_no_completion_persisted_when_reflection_is_rejected() -> None:
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    application.submit_response(activity_id, "A response.")
    with pytest.raises(InvalidReflectionResponseError):
        application.submit_reflection("   ")

    assert repository.list_completions(LEARNER) == ()


# --- SPEC-021 §8/§9: history and review through the application ---------------


def test_history_without_repository_is_empty() -> None:
    application = make_history_application(repository=None)

    view = application.get_practice_history()

    assert view.is_empty
    assert view.entries == ()


def test_history_lists_completed_practice_newest_first() -> None:
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    application.submit_response(activity_id, "First attempt response.")
    application.submit_reflection("First reflection.")
    application.submit_response(activity_id, "Second attempt response.")
    application.submit_reflection("Second reflection.")

    view = application.get_practice_history()

    assert not view.is_empty
    assert len(view.entries) == 2
    assert view.entries[0].submission_preview == "Second attempt response."
    assert view.entries[1].submission_preview == "First attempt response."


def test_review_returns_the_full_practice_evidence() -> None:
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    application.start_practice(activity_id)  # resolve the stimulus
    application.submit_response(activity_id, "The contrast is striking.")
    application.submit_reflection("I will look for balance next time.")
    completion_id = application.get_practice_history().entries[0].completion_id

    review = application.get_practice_review(completion_id)

    assert review.activity_id == activity_id
    assert review.learner_response == "The contrast is striking."
    assert review.strengths
    assert review.feedback
    assert review.reflection == "I will look for balance next time."
    assert review.completed_at is not None


def test_review_preserves_the_original_stimulus() -> None:
    """A review must not silently resolve a new stimulus (SPEC-021 §10, AC-021-07)."""
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    started = application.start_practice(activity_id)
    assert started.stimulus is not None
    original_image_url = started.stimulus.image_url
    application.submit_response(activity_id, "The contrast is striking.")
    application.submit_reflection("I will look for balance next time.")
    completion_id = application.get_practice_history().entries[0].completion_id

    review = application.get_practice_review(completion_id)

    assert review.stimulus is not None
    assert review.stimulus.image_url == original_image_url


def test_review_of_unknown_completion_raises() -> None:
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)

    with pytest.raises(CompletionNotFoundError):
        application.get_practice_review(uuid4())


def test_review_without_repository_raises() -> None:
    application = make_history_application(repository=None)

    with pytest.raises(CompletionNotFoundError):
        application.get_practice_review(uuid4())


# --- SPEC-021 §14: idempotency and failure behaviour --------------------------


def test_retrying_the_same_completion_does_not_duplicate_history() -> None:
    """AC-021-10: a retried completion write must not create a second record."""
    repository = InMemoryPracticeHistoryRepository()
    submission = make_submission()
    evaluation = make_evaluation(submission)
    feedback = make_feedback(evaluation)
    reflection = make_reflection(feedback)

    first = repository.save_completion(
        learner_id=LEARNER,
        activity_id=submission.activity_id,
        activity_title="Idempotent practice",
        submission=submission,
        evaluation=evaluation,
        feedback=feedback,
        reflection=reflection,
        stimulus=None,
    )
    second = repository.save_completion(
        learner_id=LEARNER,
        activity_id=submission.activity_id,
        activity_title="Idempotent practice",
        submission=submission,
        evaluation=evaluation,
        feedback=feedback,
        reflection=reflection,
        stimulus=None,
    )

    assert first.completion_id == second.completion_id == reflection.id
    assert len(repository.list_completions(LEARNER)) == 1


def test_repeated_practice_remains_distinguishable() -> None:
    """AC-021-06: each completion of the same activity is its own record."""
    repository = InMemoryPracticeHistoryRepository()
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    application.submit_response(activity_id, "First attempt.")
    application.submit_reflection("First reflection.")
    application.submit_response(activity_id, "Second attempt.")
    application.submit_reflection("Second reflection.")

    view = application.get_practice_history()
    assert len(view.entries) == 2
    assert view.entries[0].completion_id != view.entries[1].completion_id


class FailingRepository(InMemoryPracticeHistoryRepository):
    """A repository whose writes fail, to exercise SPEC-021 §14."""

    def __init__(self) -> None:
        super().__init__()
        self.fail_next_save = False

    def save_completion(
        self,
        learner_id: UUID,
        activity_id: UUID,
        activity_title: str,
        submission: Submission,
        evaluation: Evaluation,
        feedback: Feedback,
        reflection: Reflection,
        stimulus: StimulusInstance | None,
    ) -> StoredPracticeCompletion:
        if self.fail_next_save:
            raise PersistenceError("Failed to save completed practice.")
        return super().save_completion(
            learner_id=learner_id,
            activity_id=activity_id,
            activity_title=activity_title,
            submission=submission,
            evaluation=evaluation,
            feedback=feedback,
            reflection=reflection,
            stimulus=stimulus,
        )


def test_persistence_failure_is_explicit_not_silent() -> None:
    """AC-021-09: a failed write must not report durable completion."""
    repository = FailingRepository()
    repository.fail_next_save = True
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    application.submit_response(activity_id, "A response.")
    with pytest.raises(PersistenceError):
        application.submit_reflection("I will look for balance next time.")

    # The failure must be observable: nothing is reported as durably recorded.
    assert repository.list_completions(LEARNER) == ()


def test_persistence_failure_can_be_retried_successfully() -> None:
    repository = FailingRepository()
    repository.fail_next_save = True
    application = make_history_application(repository=repository)
    activity_id = application.get_dashboard().activities[0].id

    application.submit_response(activity_id, "A response.")
    with pytest.raises(PersistenceError):
        application.submit_reflection("I will look for balance next time.")

    # Retry the reflection after the failure is resolved.
    repository.fail_next_save = False
    view = application.submit_reflection("I will look for balance next time.")

    assert "completed this practice" in view.message
    assert len(repository.list_completions(LEARNER)) == 1


# --- Dashboard continuity across durable history -------------------------------


def test_dashboard_reports_practice_from_durable_history() -> None:
    """AC-021-04: a completion stays visible after session state is gone."""
    repository = InMemoryPracticeHistoryRepository()
    # Demo activity identities are generated per call, so both applications
    # must share the same seeded activities for the dashboard check to align.
    activities = build_demo_activities()
    application = make_history_application(repository=repository, activities=activities)

    complete_first_practice(application)

    # A fresh application (no session state) sharing the same repository still
    # sees the completed practice through durable history.
    fresh_application = make_history_application(
        repository=repository, activities=activities
    )
    summary = fresh_application.get_dashboard().activities[0]
    assert summary.has_completed_practice


def test_dashboard_without_repository_uses_session_only() -> None:
    application = make_history_application(repository=None)

    complete_first_practice(application)

    assert application.get_dashboard().activities[0].has_completed_practice


# --- Application layer remains persistence-agnostic ----------------------------


def test_application_layer_never_imports_datastore() -> None:
    """SPEC-021 §4: the application layer must not depend on Datastore APIs."""
    from pathlib import Path

    import fablit.application as application_package

    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path(application_package.__file__).parent.glob("*.py")
    )
    assert "google.cloud" not in source
    assert "datastore" not in source.replace("history_repository", "").replace(
        "PracticeHistoryRepository", ""
    )
