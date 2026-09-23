"""Application-layer tests for SPEC-022 — Optional Practice Modes & Learner Choice.

Covers the application/learner-experience boundary only: the available
modes, explicit mode selection, curated activity resolution, Short Drill
and Full Practice entry into the unchanged journey, empty eligibility
configuration, history compatibility, and the absence of hidden
history-based mode selection (SPEC-022 §18 "Application Tests").
"""

from __future__ import annotations

from pathlib import Path

import pytest

import fablit.application.practice_modes as practice_modes_module
from fablit.application import (
    DEMO_LEARNER_ID,
    PRACTICE_MODE_CHOICE_QUESTION,
    SHORT_DRILL_ACTIVITY_TITLES,
    CompletionView,
    DemoEvaluator,
    FeedbackView,
    LearnerJourneyStore,
    PracticeActivityView,
    PracticeApplication,
    PracticeDashboardView,
    PracticeMode,
    PracticeModeActivitiesView,
    PracticeModeChoiceView,
    UnknownPracticeModeError,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
    build_practice_mode_definitions,
    build_stimulus_provider,
)
from fablit.application.repositories import InMemoryPracticeHistoryRepository

PRACTICE_MODES_SOURCE = Path(practice_modes_module.__file__)


def make_application(
    *, history_repository: InMemoryPracticeHistoryRepository | None = None
) -> PracticeApplication:
    """Build a practice application over the seeded demo content."""
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


# --- Available practice modes (AC-022-01) -------------------------------------


def test_both_practice_modes_are_presented() -> None:
    application = make_application()

    view = application.get_practice_modes()

    assert isinstance(view, PracticeModeChoiceView)
    assert view.question == PRACTICE_MODE_CHOICE_QUESTION
    assert [mode.mode_id for mode in view.modes] == [
        "short-drill",
        "full-practice",
    ]


def test_each_mode_has_label_description_and_effort_guidance() -> None:
    application = make_application()

    view = application.get_practice_modes()

    for mode in view.modes:
        assert mode.label
        assert mode.description
        assert mode.effort_guidance
    assert view.modes[0].label == "A short drill"
    assert view.modes[1].label == "A full practice"


def test_mode_set_is_deliberately_small() -> None:
    assert {mode.value for mode in PracticeMode} == {
        "short-drill",
        "full-practice",
    }


def test_short_drill_effort_guidance_is_an_indication_not_a_limit() -> None:
    """§10: effort guidance is a guide — no countdown or enforced window."""
    application = make_application()

    view = application.get_practice_modes()

    lowered = view.modes[0].effort_guidance.lower()
    for forbidden in ("countdown", "time limit", "deadline", "must finish"):
        assert forbidden not in lowered


# --- Explicit choice, no recommendation (AC-022-10) ----------------------------


def test_no_mode_is_preselected_or_ranked() -> None:
    application = make_application()

    view = application.get_practice_modes()

    # The chooser view carries only neutral presentation data: no default,
    # no ranking, no recommendation signal of any kind.
    assert "recommended" not in vars(view)
    assert "default" not in vars(view)
    assert "ranking" not in vars(view)


def test_mode_choice_is_unchanged_after_practice_history_accumulates() -> None:
    """No hidden personalization: history never alters the presented modes."""
    application = make_application()
    before = application.get_practice_modes()

    drills = application.get_practice_mode_activities(PracticeMode.SHORT_DRILL)
    application.submit_response(drills.activities[0].id, "A quick noticing response.")
    application.submit_reflection("I will look for one more detail next time.")
    after = application.get_practice_modes()

    assert after == before


# --- Eligible activity resolution (AC-022-03, AC-022-04, AC-022-07) ------------


def test_short_drill_resolves_the_curated_configuration() -> None:
    application = make_application()

    view = application.get_practice_mode_activities(PracticeMode.SHORT_DRILL)

    assert isinstance(view, PracticeModeActivitiesView)
    assert view.mode_id == "short-drill"
    assert not view.is_empty
    assert [activity.title for activity in view.activities] == [
        "Memory Drawing Prep — Object & Proportion Detection",
        "Creative Writing — Concept Explanations for Poster Designs",
        "Observation Drill — Everyday Object Study",
        "Short Ideation Sprint — Alternative Uses",
        "Design Articulation — Explain a Poster Concept",
        "Reflection Prompt — What Did Practice Ask of You?",
    ]


def test_short_drill_activities_come_from_configuration_not_title_inference() -> None:
    """Eligibility resolves the curated list to stable identities (AC-022-07)."""
    activities = build_demo_activities()

    short_drill = build_practice_mode_definitions(activities)[0]

    eligible_ids = short_drill.eligible_activity_ids
    all_ids = {item.activity.id for item in activities}
    assert set(eligible_ids) <= all_ids
    assert len(eligible_ids) == len(SHORT_DRILL_ACTIVITY_TITLES)


def test_full_practice_resolves_the_whole_existing_library() -> None:
    application = make_application()

    view = application.get_practice_mode_activities(PracticeMode.FULL_PRACTICE)
    dashboard = application.get_dashboard()

    assert view.mode_id == "full-practice"
    assert not view.is_empty
    assert [activity.id for activity in view.activities] == [
        activity.id for activity in dashboard.activities
    ]


def test_full_practice_entries_reuse_dashboard_summaries() -> None:
    """The mode view reuses the ordinary activity library, not a parallel one."""
    application = make_application()

    dashboard = application.get_dashboard()
    view = application.get_practice_mode_activities(PracticeMode.FULL_PRACTICE)

    assert isinstance(dashboard, PracticeDashboardView)
    assert view.activities[0].title == dashboard.activities[0].title
    assert view.activities[0].description == dashboard.activities[0].description
    assert view.activities[0].skills == dashboard.activities[0].skills


def test_short_drill_is_a_subset_of_the_existing_library() -> None:
    application = make_application()

    drills = application.get_practice_mode_activities(PracticeMode.SHORT_DRILL)
    full = application.get_practice_mode_activities(PracticeMode.FULL_PRACTICE)

    full_ids = {activity.id for activity in full.activities}
    for drill in drills.activities:
        assert drill.id in full_ids


# --- Empty/unsupported eligibility configuration --------------------------------


def test_empty_short_drill_configuration_yields_an_empty_mode_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activities = build_demo_activities()
    monkeypatch.setattr(practice_modes_module, "SHORT_DRILL_ACTIVITY_TITLES", ())
    definitions = build_practice_mode_definitions(activities)

    assert definitions[0].eligible_activity_ids == ()

    application = make_application()
    monkeypatch.setattr(application, "_practice_modes", definitions)
    view = application.get_practice_mode_activities(PracticeMode.SHORT_DRILL)

    assert view.is_empty
    assert view.activities == ()


def test_stale_titles_in_configuration_are_skipped_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configuration may drift from seeded content without breaking resolution."""
    activities = build_demo_activities()
    monkeypatch.setattr(
        practice_modes_module,
        "SHORT_DRILL_ACTIVITY_TITLES",
        ("Retired Activity Title",),
    )

    short_drill = build_practice_mode_definitions(activities)[0]

    assert short_drill.eligible_activity_ids == ()


def test_unknown_mode_is_rejected_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application = make_application()
    monkeypatch.setattr(application, "_practice_modes", ())

    with pytest.raises(UnknownPracticeModeError):
        application.get_practice_mode_activities(PracticeMode.SHORT_DRILL)


# --- Entry into the unchanged journey (AC-022-05) -------------------------------


def test_short_drill_entry_uses_the_normal_practice_journey() -> None:
    application = make_application()

    drills = application.get_practice_mode_activities(PracticeMode.SHORT_DRILL)
    activity_id = drills.activities[0].id

    activity = application.start_practice(activity_id)
    assert isinstance(activity, PracticeActivityView)
    assert activity.id == activity_id

    feedback = application.submit_response(activity_id, "A short noticing response.")
    assert isinstance(feedback, FeedbackView)

    completion = application.submit_reflection(
        "I will look for one more detail next time."
    )
    assert isinstance(completion, CompletionView)


def test_full_practice_entry_uses_the_normal_practice_journey() -> None:
    application = make_application()

    full = application.get_practice_mode_activities(PracticeMode.FULL_PRACTICE)
    activity_id = full.activities[0].id

    activity = application.start_practice(activity_id)
    assert isinstance(activity, PracticeActivityView)

    feedback = application.submit_response(activity_id, "A considered response.")
    assert isinstance(feedback, FeedbackView)

    completion = application.submit_reflection("I will compare two elements next time.")
    assert isinstance(completion, CompletionView)


# --- History compatibility (AC-022-09) ------------------------------------------


def test_completed_short_drill_is_recorded_in_practice_history() -> None:
    """A completed drill is simply completed practice."""
    application = make_application(
        history_repository=InMemoryPracticeHistoryRepository()
    )

    drills = application.get_practice_mode_activities(PracticeMode.SHORT_DRILL)
    activity_id = drills.activities[0].id
    application.submit_response(activity_id, "A short noticing response.")
    application.submit_reflection("I will look for one more detail next time.")

    history = application.get_practice_history()

    assert not history.is_empty
    assert history.entries[0].activity_id == activity_id
    assert history.entries[0].activity_title == (
        "Memory Drawing Prep — Object & Proportion Detection"
    )


def test_completed_short_drill_is_reviewable() -> None:
    application = make_application(
        history_repository=InMemoryPracticeHistoryRepository()
    )

    drills = application.get_practice_mode_activities(PracticeMode.SHORT_DRILL)
    activity_id = drills.activities[0].id
    application.submit_response(activity_id, "A short noticing response.")
    application.submit_reflection("I will look for one more detail next time.")
    completion_id = application.get_practice_history().entries[0].completion_id

    review = application.get_practice_review(completion_id)

    assert review.activity_id == activity_id
    assert review.learner_response == "A short noticing response."
    assert review.reflection == "I will look for one more detail next time."


def test_repeated_drills_create_separate_history_entries() -> None:
    application = make_application(
        history_repository=InMemoryPracticeHistoryRepository()
    )

    drills = application.get_practice_mode_activities(PracticeMode.SHORT_DRILL)
    activity_id = drills.activities[0].id
    application.submit_response(activity_id, "First drill response.")
    application.submit_reflection("First drill reflection.")
    application.submit_response(activity_id, "Second drill response.")
    application.submit_reflection("Second drill reflection.")

    history = application.get_practice_history()

    assert len(history.entries) == 2


# --- No hidden selection machinery (§12) -----------------------------------------


def test_mode_layer_carries_no_gamification_or_timer_machinery() -> None:
    """No timers, gamification, or history-based inference in the mode layer."""
    source = PRACTICE_MODES_SOURCE.read_text(encoding="utf-8").lower()

    for forbidden in ("countdown", "timer", "streak", "badge", "leaderboard"):
        assert forbidden not in source


def test_mode_layer_never_touches_history_or_persistence() -> None:
    """§12: mode selection cannot infer from history — the module cannot see it."""
    source = PRACTICE_MODES_SOURCE.read_text(encoding="utf-8")

    assert "persistence" not in source
    assert "history_repository" not in source
    assert "PracticeHistoryRepository" not in source


def test_mode_identifiers_are_stable_url_safe_slugs() -> None:
    for mode in PracticeMode:
        assert mode.value == mode.value.lower()
        assert " " not in mode.value


def test_eligibility_check_rejects_activities_outside_the_mode() -> None:
    """A mode's eligibility check excludes activities it does not curate."""
    activities = build_demo_activities()

    short_drill = build_practice_mode_definitions(activities)[0]
    full = build_practice_mode_definitions(activities)[1]
    uncurated = next(
        item.activity.id
        for item in activities
        if not short_drill.is_eligible(item.activity.id)
    )

    assert not short_drill.is_eligible(uncurated)
    assert full.is_eligible(uncurated)
