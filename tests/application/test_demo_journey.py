"""Application-layer journey tests for the expanded library (SPEC-023).

New activities are content, not new workflow: every added activity must run
the unchanged SPEC-012 learner journey (Submission → Evaluation → Feedback →
Reflection → Completion) and produce the same durable SPEC-021 practice
history as the original five (AC-023-07, AC-023-08, AC-023-10, AC-023-11).
These tests walk representative new activities — stimulus and text-first,
across the capability lens — through that journey and confirm the expanded
library is exposed through the existing surfaces (AC-023-05, §19).
"""

from __future__ import annotations

from uuid import UUID

from fablit.application import (
    DEMO_LEARNER_ID,
    CompletionView,
    DemoEvaluator,
    FeedbackView,
    PracticeActivityView,
    PracticeApplication,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
    build_stimulus_provider,
)
from fablit.application.repositories import InMemoryPracticeHistoryRepository
from fablit.application.store import LearnerJourneyStore

# Titles of activities added by SPEC-023 (one per primary capability where
# possible, mixing stimulus-dependent and text-first activities).
NEW_ACTIVITY_TITLES = (
    "Observation Drill — Everyday Object Study",
    "Visual Interpretation — Reading a Street Scene",
    "Short Ideation Sprint — Alternative Uses",
    "Design Ideation — Transform the Object",
    "Composition Detective — What Holds This Together?",
    "Design Articulation — Explain a Poster Concept",
    "Reflection Prompt — What Did Practice Ask of You?",
)


def make_application(
    *,
    history_repository: InMemoryPracticeHistoryRepository | None = None,
) -> PracticeApplication:
    """Build a practice application over the expanded demo content."""
    activities = build_demo_activities()
    return PracticeApplication(
        store=LearnerJourneyStore(
            learner_id=DEMO_LEARNER_ID,
            activities=activities,
            skills=build_demo_skills(),
        ),
        evaluator=DemoEvaluator(build_demo_activity_map(activities)),
        stimulus_provider=build_stimulus_provider(activities, provider_name="builtin"),
        history_repository=history_repository,
    )


def _activity_id(application: PracticeApplication, title: str) -> UUID:
    for summary in application.get_dashboard().activities:
        if summary.title == title:
            return summary.id
    raise AssertionError(f"activity not found in the library: {title}")


# --------------------------------------------------------------------------- #
# The expanded library is exposed (§19)
# --------------------------------------------------------------------------- #


def test_expanded_library_is_exposed_on_the_dashboard() -> None:
    """All seeded activities, new ones included, appear on Explore."""
    application = make_application()
    titles = {summary.title for summary in application.get_dashboard().activities}

    assert set(NEW_ACTIVITY_TITLES) <= titles


def test_new_activities_are_reachable_in_deterministic_library_order() -> None:
    """The expanded library keeps one deterministic ordering (SPEC-012)."""
    titles = [
        summary.title for summary in make_application().get_dashboard().activities
    ]

    assert titles == list(dict.fromkeys(titles))
    assert len(titles) == 12


def test_new_stimulus_activities_resolve_a_bundled_stimulus() -> None:
    """New image-dependent activities get a deterministic bundled stimulus."""
    application = make_application()

    view = application.start_practice(
        _activity_id(application, "Observation Drill — Everyday Object Study")
    )

    assert isinstance(view, PracticeActivityView)
    assert view.stimulus is not None
    assert view.stimulus.image_url.startswith("/static/images/")


def test_new_text_first_activities_have_no_stimulus() -> None:
    """Text-first new activities stay text-first (SPEC-019 §12)."""
    application = make_application()

    view = application.start_practice(
        _activity_id(application, "Short Ideation Sprint — Alternative Uses")
    )

    assert isinstance(view, PracticeActivityView)
    assert view.stimulus is None


# --------------------------------------------------------------------------- #
# Representative journeys (AC-023-07, AC-023-08, §19)
# --------------------------------------------------------------------------- #


def _run_journey(application: PracticeApplication, title: str, response: str) -> None:
    """Drive the unchanged journey for one activity."""
    activity_id = _activity_id(application, title)
    activity = application.start_practice(activity_id)
    assert isinstance(activity, PracticeActivityView)

    feedback = application.submit_response(activity_id, response)
    assert isinstance(feedback, FeedbackView)
    assert feedback.activity_title == title

    reflection = application.get_reflection()
    assert reflection.prompt

    completion = application.submit_reflection("A specific next-attempt note.")
    assert isinstance(completion, CompletionView)


def test_new_observation_activity_completes_the_existing_journey() -> None:
    """A stimulus-dependent new activity runs the unchanged journey."""
    application = make_application()

    _run_journey(
        application,
        "Observation Drill — Everyday Object Study",
        "The wooden handle is worn smooth and the metal carries fine scratches.",
    )


def test_new_ideation_activity_completes_the_existing_journey() -> None:
    """A text-first new activity runs the unchanged journey."""
    application = make_application()

    _run_journey(
        application,
        "Short Ideation Sprint — Alternative Uses",
        "A ladle could be a plant marker, a doorstop, or a tiny mirror stand.",
    )


def test_new_reflection_activity_completes_the_existing_journey() -> None:
    """The new reflection activity runs the unchanged journey."""
    application = make_application()

    _run_journey(
        application,
        "Reflection Prompt — What Did Practice Ask of You?",
        "The last activity asked me to slow down and name details precisely.",
    )


def test_new_activity_evaluation_is_concrete_and_actionable() -> None:
    """Feedback stays finding → improvement → next step (AC-023-09, §12)."""
    application = make_application()
    activity_id = _activity_id(
        application, "Visual Interpretation — Reading a Street Scene"
    )
    application.start_practice(activity_id)
    feedback = application.submit_response(
        activity_id,
        "Two people walk past a shopfront in warm evening light; the long "
        "shadows give the street a calm end-of-day mood.",
    )

    assert feedback.strengths
    assert feedback.improvements
    assert feedback.next_steps


def test_different_responses_to_a_new_stimulus_activity_change_findings() -> None:
    """Response-aware evaluation semantics carry over (SPEC-015 §69)."""
    application = make_application()
    activity_id = _activity_id(application, "Observation Drill — Everyday Object Study")

    first = application.submit_response(
        activity_id,
        "I notice the wear on the handle where hands have held it.",
    )
    second = application.submit_response(
        activity_id,
        "I notice the scratches across the metal surface catching the light.",
    )

    assert first.strengths != second.strengths


# --------------------------------------------------------------------------- #
# History compatibility (AC-023-10)
# --------------------------------------------------------------------------- #


def test_new_activity_completion_is_recorded_and_reviewable() -> None:
    """A new activity produces ordinary SPEC-021 history and review."""
    application = make_application(
        history_repository=InMemoryPracticeHistoryRepository()
    )
    title = "Design Ideation — Transform the Object"
    activity_id = _activity_id(application, title)
    application.start_practice(activity_id)
    application.submit_response(
        activity_id,
        "I would transform the kettle's curling form into a watering can.",
    )
    application.submit_reflection("Next time I will keep one original feature.")

    history = application.get_practice_history()

    assert not history.is_empty
    entry = next(item for item in history.entries if item.activity_title == title)
    review = application.get_practice_review(entry.completion_id)

    assert review.activity_id == activity_id
    assert "watering can" in review.learner_response
    assert review.reflection == "Next time I will keep one original feature."


def test_repeated_practice_of_a_new_activity_remains_valid() -> None:
    """Repeated attempts remain possible and distinct (§15)."""
    application = make_application(
        history_repository=InMemoryPracticeHistoryRepository()
    )
    activity_id = _activity_id(application, "Short Ideation Sprint — Alternative Uses")
    for response in (
        "First attempt: paperweight, phone stand.",
        "Second attempt: bookmark, hook, scoop.",
    ):
        application.start_practice(activity_id)
        application.submit_response(activity_id, response)
        application.submit_reflection("I will push one idea further.")

    history = application.get_practice_history()

    assert len(history.entries) == 2


# --------------------------------------------------------------------------- #
# No special-casing (AC-023-11)
# --------------------------------------------------------------------------- #


def test_new_activities_need_no_activity_specific_application_branches() -> None:
    """The application layer has no per-activity special cases for expansion."""
    from pathlib import Path

    import fablit.application.use_cases as use_cases_module

    source = Path(use_cases_module.__file__).read_text(encoding="utf-8")
    for new_title in NEW_ACTIVITY_TITLES:
        assert new_title.split(" — ")[0] not in source
