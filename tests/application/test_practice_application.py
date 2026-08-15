"""Application-layer tests for the learner practice flow (SPEC-012)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import fablit.application
from fablit.application import (
    DEMO_LEARNER_ID,
    REFLECTION_PROMPT,
    ActivityNotFoundError,
    CompletionNotFoundError,
    CompletionView,
    DemoEvaluator,
    FeedbackNotFoundError,
    FeedbackView,
    InvalidPracticeResponseError,
    InvalidReflectionResponseError,
    LearnerJourneyStore,
    PracticeActivityView,
    PracticeApplication,
    PracticeDashboardView,
    ReflectionView,
    build_demo_activities,
    build_demo_findings,
    build_demo_skills,
)
from fablit.domain import SubmissionStatus

APPLICATION_SOURCE = list(Path(fablit.application.__file__).parent.glob("*.py"))


def _application_source_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in APPLICATION_SOURCE)


def _fixed_clock() -> datetime:
    return datetime(2026, 8, 15, 12, 0, tzinfo=UTC)


def make_application(
    *,
    clock: Callable[[], datetime] | None = None,
) -> tuple[PracticeApplication, LearnerJourneyStore]:
    """Build a practice application together with its in-memory store."""
    activities = build_demo_activities()
    store = LearnerJourneyStore(
        learner_id=DEMO_LEARNER_ID,
        activities=activities,
        skills=build_demo_skills(),
    )
    application = PracticeApplication(
        store=store,
        evaluator=DemoEvaluator(build_demo_findings(activities)),
        clock=clock,
    )
    return application, store


def first_activity_id(application: PracticeApplication) -> UUID:
    return application.get_dashboard().activities[0].id


def test_dashboard_lists_three_to_five_activities() -> None:
    application, _ = make_application()

    view = application.get_dashboard()

    assert isinstance(view, PracticeDashboardView)
    assert 3 <= len(view.activities) <= 5


def test_dashboard_summaries_include_skills() -> None:
    application, _ = make_application()

    view = application.get_dashboard()
    summary = view.activities[0]

    assert summary.title
    assert summary.description
    assert summary.skills
    assert "Visual Analysis" in summary.skills


def test_start_practice_presents_activity() -> None:
    application, _ = make_application()

    view = application.start_practice(first_activity_id(application))

    assert isinstance(view, PracticeActivityView)
    assert view.title == "Visual Analysis — Composition"
    assert "composition" in view.prompt.lower()
    assert "Visual Analysis" in view.skills


def test_start_practice_unknown_activity_raises() -> None:
    application, _ = make_application()

    with pytest.raises(ActivityNotFoundError):
        application.start_practice(uuid4())


def test_submit_response_creates_journey_records() -> None:
    application, store = make_application(clock=_fixed_clock)

    view = application.submit_response(first_activity_id(application), "A response.")

    assert isinstance(view, FeedbackView)
    submissions = store.recorded_submissions()
    assert len(submissions) == 1
    assert submissions[0].status is SubmissionStatus.SUBMITTED
    assert submissions[0].response == "A response."
    evaluations = store.recorded_evaluations()
    assert len(evaluations) == 1
    assert len(evaluations[0].findings) >= 1
    feedback = store.recorded_feedback()
    assert len(feedback) == 1
    assert store.current_feedback().id == feedback[0].id


def test_submission_references_activity_and_learner_by_identity() -> None:
    application, store = make_application()
    activity_id = first_activity_id(application)

    application.submit_response(activity_id, "A response.")

    submission = store.recorded_submissions()[0]
    assert submission.activity_id == activity_id
    assert submission.learner_id == DEMO_LEARNER_ID


def test_submit_response_prepares_structured_feedback_view() -> None:
    application, _ = make_application()

    view = application.submit_response(first_activity_id(application), "A response.")

    assert view.strengths
    assert view.improvements
    assert view.next_steps
    assert view.activity_title == "Visual Analysis — Composition"
    assert view.reflection_prompt == REFLECTION_PROMPT


def test_submit_response_is_deterministic() -> None:
    application, _ = make_application(clock=_fixed_clock)

    first = application.submit_response(
        first_activity_id(application), "Same response."
    )
    second = application.submit_response(
        first_activity_id(application), "Same response."
    )

    assert first.strengths == second.strengths
    assert first.improvements == second.improvements
    assert first.next_steps == second.next_steps


@pytest.mark.parametrize("response", ["", "   ", "\n\t"])
def test_submit_response_rejects_blank_response(response: str) -> None:
    application, store = make_application()

    with pytest.raises(InvalidPracticeResponseError):
        application.submit_response(first_activity_id(application), response)

    assert store.recorded_submissions() == ()


def test_submit_response_unknown_activity_raises() -> None:
    application, store = make_application()

    with pytest.raises(ActivityNotFoundError):
        application.submit_response(uuid4(), "A response.")

    assert store.recorded_submissions() == ()


def test_get_feedback_returns_the_current_feedback_view() -> None:
    application, _ = make_application()

    submitted = application.submit_response(
        first_activity_id(application), "A response."
    )
    presented = application.get_feedback()

    assert presented.strengths == submitted.strengths
    assert presented.activity_title == "Visual Analysis — Composition"


def test_get_feedback_without_submission_raises() -> None:
    application, _ = make_application()

    with pytest.raises(FeedbackNotFoundError):
        application.get_feedback()


def test_get_reflection_presents_prompt_with_feedback_context() -> None:
    application, _ = make_application()

    application.submit_response(first_activity_id(application), "A response.")
    view = application.get_reflection()

    assert isinstance(view, ReflectionView)
    assert view.prompt == REFLECTION_PROMPT
    assert view.activity_title == "Visual Analysis — Composition"
    assert "Strengths" in view.context


def test_submit_reflection_creates_reflection_and_completion() -> None:
    application, store = make_application(clock=_fixed_clock)

    application.submit_response(first_activity_id(application), "A response.")
    view = application.submit_reflection("I will compare two elements next time.")

    assert isinstance(view, CompletionView)
    assert "completed this practice" in view.message
    reflections = store.recorded_reflections()
    assert len(reflections) == 1
    assert reflections[0].content == "I will compare two elements next time."
    assert reflections[0].created_at == _fixed_clock()
    assert store.last_reflection() is not None


@pytest.mark.parametrize("content", ["", "   ", "\n"])
def test_submit_reflection_rejects_blank_content(content: str) -> None:
    application, store = make_application()

    application.submit_response(first_activity_id(application), "A response.")
    with pytest.raises(InvalidReflectionResponseError):
        application.submit_reflection(content)

    assert store.recorded_reflections() == ()


def test_get_completion_requires_a_saved_reflection() -> None:
    application, _ = make_application()

    with pytest.raises(CompletionNotFoundError):
        application.get_completion()

    application.submit_response(first_activity_id(application), "A response.")
    with pytest.raises(CompletionNotFoundError):
        application.get_completion()

    application.submit_reflection("Next time I will slow down.")
    assert "completed this practice" in application.get_completion().message


def test_journey_records_use_timezone_aware_timestamps() -> None:
    application, store = make_application()

    application.submit_response(first_activity_id(application), "A response.")
    application.submit_reflection("Next time I will slow down.")

    for submission in store.recorded_submissions():
        assert submission.submitted_at is not None
        assert submission.submitted_at.tzinfo is not None
    for evaluation in store.recorded_evaluations():
        assert evaluation.evaluated_at.tzinfo is not None
    for feedback in store.recorded_feedback():
        assert feedback.created_at.tzinfo is not None
    for reflection in store.recorded_reflections():
        assert reflection.created_at.tzinfo is not None


@pytest.mark.parametrize("forbidden", ["NIFT", "NID", "CEED"])
def test_application_layer_has_no_examination_specific_terminology(
    forbidden: str,
) -> None:
    assert forbidden.lower() not in _application_source_text().lower()


def test_application_layer_has_no_framework_or_persistence_dependencies() -> None:
    source = _application_source_text()
    for module in (
        "fastapi",
        "pydantic",
        "uvicorn",
        "sqlalchemy",
        "psycopg",
        "redis",
        "sqlite3",
        "motor",
    ):
        assert f"import {module}" not in source
        assert f"from {module}" not in source


def test_application_layer_contains_no_html_markup() -> None:
    source = _application_source_text()
    assert "<html" not in source
    assert "<form" not in source
    assert "</" not in source
