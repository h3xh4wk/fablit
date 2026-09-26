"""Application-layer tests for SPEC-025 — Curated Practice Continuity.

Covers the authored transition configuration and its resolution (§3.2, §4,
§7), the deterministic continuation surfaced on completion (§3.1, AC 1–4),
learner independence — a second learner receives the same content transition
without sharing any history or state (AC 10) — the unchanged journey and
history boundaries when following a continuation (§3.4, AC 5, AC 6, AC 9),
and the absence of recommendation or personalization machinery (AC 8, §10
"Connect practices, not learners").

Activity identities are minted fresh on every ``build_demo_activities()``
call, so every helper resolves identities against the tuple it is given —
never across builds.
"""

from __future__ import annotations

import dataclasses
from dataclasses import replace
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import fablit.application.practice_continuity as practice_continuity_module
from fablit.application import (
    CONTINUATION_ACTION_LABEL,
    CONTINUATION_HEADING,
    DEMO_LEARNER_ID,
    CompletionView,
    ContinuationView,
    DemoActivity,
    DemoEvaluator,
    LearnerJourneyStore,
    PracticeApplication,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
    build_practice_transition_map,
    build_practice_transitions,
    build_stimulus_provider,
)
from fablit.application.repositories import InMemoryPracticeHistoryRepository

PRACTICE_CONTINUITY_SOURCE = Path(practice_continuity_module.__file__)

EXPECTED_TRANSITION_PAIRS: tuple[tuple[str, str], ...] = (
    (
        "Observation Drill — Everyday Object Study",
        "Design Ideation — Transform the Object",
    ),
    (
        "Memory Drawing Prep — Object & Proportion Detection",
        "Short Ideation Sprint — Alternative Uses",
    ),
    (
        "CAT Practice — 2D & 3D Composition Analysis",
        "Visual Interpretation — Reading a Street Scene",
    ),
    (
        "Color Theory — Mood & Atmosphere Interpretation",
        "Design Articulation — Explain a Poster Concept",
    ),
    (
        "Short Ideation Sprint — Alternative Uses",
        "Design Articulation — Explain a Poster Concept",
    ),
    (
        "Design Ideation — Transform the Object",
        "Design Articulation — Explain a Poster Concept",
    ),
    (
        "Reflection Prompt — What Did Practice Ask of You?",
        "Observation Drill — Everyday Object Study",
    ),
)

#: The one library activity with no authored continuation (SPEC-025 §4).
UNAUTHORED_TITLE = "Situation Test Prep — Material & Design Process Reflection"


def make_application(
    *,
    learner_id: UUID = DEMO_LEARNER_ID,
    history_repository: InMemoryPracticeHistoryRepository | None = None,
    activities: tuple[DemoActivity, ...] | None = None,
) -> PracticeApplication:
    """Build a practice application over the seeded demo content."""
    activities = activities if activities is not None else build_demo_activities()
    return PracticeApplication(
        store=LearnerJourneyStore(
            learner_id=learner_id,
            activities=activities,
            skills=build_demo_skills(),
        ),
        evaluator=DemoEvaluator(build_demo_activity_map(activities)),
        stimulus_provider=build_stimulus_provider(activities, provider_name="builtin"),
        history_repository=history_repository,
    )


def complete_activity(
    application: PracticeApplication, activity_id: UUID
) -> CompletionView:
    """Drive one full journey for the given activity: submit, then reflect."""
    application.submit_response(activity_id, "A considered response about the object.")
    return application.submit_reflection("I will look for one more detail next time.")


def activity_id_by_title(
    source: tuple[DemoActivity, ...] | PracticeApplication, title: str
) -> UUID:
    """Resolve an activity identity by title within one build or application."""
    if isinstance(source, PracticeApplication):
        pairs = {
            summary.title: summary.id for summary in source.get_dashboard().activities
        }
    else:
        pairs = {item.title: item.activity.id for item in source}
    if title not in pairs:
        raise AssertionError(f"seeded activity not found: {title}")
    return pairs[title]


# --- Authored transitions resolve to the existing library (AC 1, AC 3) ---------


def test_every_authored_transition_resolves_to_seeded_activities() -> None:
    activities = build_demo_activities()
    valid_ids = {item.activity.id for item in activities}

    transitions = build_practice_transitions(activities)

    assert len(transitions) == len(EXPECTED_TRANSITION_PAIRS)
    for transition in transitions:
        assert transition.source_activity_id in valid_ids
        assert transition.target_activity_id in valid_ids
        assert transition.transition_copy.strip()


def test_transition_pairs_match_the_authored_configuration() -> None:
    activities = build_demo_activities()
    by_id = {item.activity.id: item for item in activities}

    transitions = build_practice_transitions(activities)

    pairs = tuple(
        (by_id[t.source_activity_id].title, by_id[t.target_activity_id].title)
        for t in transitions
    )
    assert pairs == EXPECTED_TRANSITION_PAIRS


def test_one_source_points_to_at_most_one_target() -> None:
    """§3.2: one completed activity may point to one curated next activity."""
    transitions = build_practice_transitions(build_demo_activities())
    sources = [t.source_activity_id for t in transitions]

    assert len(sources) == len(set(sources))


def test_transition_targets_are_distinct_from_their_sources() -> None:
    transitions = build_practice_transitions(build_demo_activities())

    for transition in transitions:
        assert transition.source_activity_id != transition.target_activity_id


def test_stale_configuration_titles_are_skipped_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configuration may drift from seeded content without breaking resolution."""
    activities = build_demo_activities()
    monkeypatch.setattr(
        practice_continuity_module,
        "_AUTHORED_TRANSITIONS",
        (("Retired Activity Title", "Design Ideation — Transform the Object", "x"),),
    )

    resolved = build_practice_transitions(activities)

    assert resolved == ()


def test_one_library_activity_has_no_authored_transition() -> None:
    activities = build_demo_activities()
    titles = {item.title for item in activities}
    by_id = {item.activity.id: item for item in activities}

    source_titles = {
        by_id[t.source_activity_id].title
        for t in build_practice_transitions(activities)
    }

    assert len(source_titles) == len(EXPECTED_TRANSITION_PAIRS)
    assert source_titles <= titles


# --- Deterministic continuation on completion (AC 1, AC 2, AC 4) ---------------


def test_completing_an_observation_activity_exposes_its_continuation() -> None:
    application = make_application()
    source_id = activity_id_by_title(
        application, "Observation Drill — Everyday Object Study"
    )

    completion = complete_activity(application, source_id)

    assert isinstance(completion, CompletionView)
    assert completion.continuation is not None
    assert completion.continuation.target_title == (
        "Design Ideation — Transform the Object"
    )
    assert completion.continuation.transition_copy.strip()


def test_completion_without_an_authored_transition_has_no_continuation() -> None:
    application = make_application()
    unauthored_id = activity_id_by_title(application, UNAUTHORED_TITLE)

    completion = complete_activity(application, unauthored_id)

    assert completion.continuation is None


def test_the_same_activity_always_yields_the_same_transition() -> None:
    """AC 2: the transition is deterministic for the same source activity."""
    application = make_application()
    source_id = activity_id_by_title(
        application, "Observation Drill — Everyday Object Study"
    )

    first = complete_activity(application, source_id)
    application.submit_response(source_id, "A second considered response.")
    application.submit_reflection("A second reflection.")
    second = application.get_completion()

    assert first.continuation is not None
    assert second.continuation is not None
    assert second.continuation == first.continuation


def test_transition_map_lookup_is_deterministic() -> None:
    activities = build_demo_activities()

    assert build_practice_transition_map(activities) == build_practice_transition_map(
        activities
    )


def test_transition_lookup_rejects_unknown_activities() -> None:
    transitions = build_practice_transition_map(build_demo_activities())

    assert transitions.get(uuid4()) is None


# --- Learner independence (AC 4, AC 10) -----------------------------------------


def test_a_second_learner_receives_the_same_content_transition() -> None:
    """AC 10: another learner gets the same transition without shared state."""
    activities = build_demo_activities()
    first = make_application(activities=activities)
    second = make_application(
        learner_id=uuid4(),
        history_repository=InMemoryPracticeHistoryRepository(),
        activities=build_demo_activities(),
    )
    source_id = activity_id_by_title(
        activities, "Observation Drill — Everyday Object Study"
    )

    first_completion = complete_activity(first, source_id)
    # The second learner practises the same activity content from their own
    # build of the library — same title, freshly minted identity.
    second_completion = complete_activity(
        second,
        activity_id_by_title(second, "Observation Drill — Everyday Object Study"),
    )

    assert first_completion.continuation is not None
    assert second_completion.continuation is not None
    assert (
        second_completion.continuation.target_title
        == first_completion.continuation.target_title
    )
    assert (
        second_completion.continuation.transition_copy
        == first_completion.continuation.transition_copy
    )
    # And the second learner's history contains only their own completion.
    history = second.get_practice_history()
    assert [entry.activity_title for entry in history.entries] == [
        "Observation Drill — Everyday Object Study"
    ]


def test_prior_history_never_changes_the_continuation() -> None:
    """AC 4: the continuation does not depend on history or behaviour."""
    application = make_application(
        history_repository=InMemoryPracticeHistoryRepository()
    )
    source_id = activity_id_by_title(
        application, "Observation Drill — Everyday Object Study"
    )

    fresh = complete_activity(application, source_id)
    assert fresh.continuation is not None
    baseline = fresh.continuation

    # More completed practice for the same learner must not alter it.
    other_id = activity_id_by_title(
        application, "CAT Practice — 2D & 3D Composition Analysis"
    )
    complete_activity(application, other_id)
    application.submit_response(source_id, "Yet another response.")
    application.submit_reflection("Yet another reflection.")
    again = application.get_completion()

    assert again.continuation == baseline


# --- Following the continuation uses the existing journey (AC 5, AC 6, AC 9) ---


def test_following_a_continuation_runs_the_unchanged_journey() -> None:
    application = make_application()
    source_id = activity_id_by_title(
        application, "Observation Drill — Everyday Object Study"
    )
    completion = complete_activity(application, source_id)
    assert completion.continuation is not None

    target_id = completion.continuation.target_activity_id
    activity = application.start_practice(target_id)
    feedback = application.submit_response(target_id, "A transformed design idea.")
    following = application.submit_reflection(
        "I will explain one design choice next time."
    )

    assert activity.id == target_id
    assert feedback.activity_title == "Design Ideation — Transform the Object"
    assert following.continuation is not None


def test_a_followed_continuation_is_recorded_in_the_learners_history() -> None:
    """AC 6: the target practice persists under the current learner identity."""
    application = make_application(
        history_repository=InMemoryPracticeHistoryRepository()
    )
    source_id = activity_id_by_title(
        application, "Observation Drill — Everyday Object Study"
    )
    completion = complete_activity(application, source_id)
    assert completion.continuation is not None

    target_id = completion.continuation.target_activity_id
    application.submit_response(target_id, "A transformed design idea.")
    application.submit_reflection("I will explain one design choice next time.")

    # Newest first: the followed continuation is the most recent completion.
    history = application.get_practice_history()
    assert [entry.activity_id for entry in history.entries] == [target_id, source_id]
    review = application.get_practice_review(history.entries[0].completion_id)
    assert review.learner_response == "A transformed design idea."


# --- The learner can ignore the continuation (AC 7) -----------------------------


def test_continuation_is_optional_and_the_message_stands_alone() -> None:
    application = make_application()
    source_id = activity_id_by_title(
        application, "Observation Drill — Everyday Object Study"
    )

    completion = complete_activity(application, source_id)

    assert isinstance(completion, CompletionView)
    assert completion.message.strip()


def test_the_continuation_view_is_a_frozen_content_value() -> None:
    view = ContinuationView(
        target_activity_id=uuid4(),
        target_title="Design Ideation — Transform the Object",
        transition_copy="You just observed. Now try transforming.",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        view.transition_copy = "mutated"  # type: ignore[misc]


def test_practice_transition_is_a_frozen_content_value() -> None:
    transition = build_practice_transitions(build_demo_activities())[0]

    with pytest.raises(dataclasses.FrozenInstanceError):
        transition.transition_copy = "mutated"  # type: ignore[misc]


def test_continuation_view_can_be_replaced_for_derived_views() -> None:
    view = ContinuationView(
        target_activity_id=uuid4(),
        target_title="Design Ideation — Transform the Object",
        transition_copy="You just observed. Now try transforming.",
    )

    derived = replace(view, transition_copy="A revised relationship.")

    assert derived.transition_copy == "A revised relationship."
    assert view.transition_copy == "You just observed. Now try transforming."


# --- No recommendation or personalization machinery (AC 8, §10) ------------------


def test_transition_layer_carries_no_recommendation_or_gamification_machinery() -> None:
    # The check covers the whole module, including its docstring: the
    # forbidden vocabulary must not appear in the transition layer. The one
    # permitted occurrence is the module docstring's statement that SPEC-025
    # is NOT an adaptive system — the negated phrase is replaced before
    # checking so the assertion stays exact.
    source = PRACTICE_CONTINUITY_SOURCE.read_text(encoding="utf-8").lower()
    source = source.replace(
        "spec-025 is authored content continuity, not an",
        "spec-025 is authored content continuity, not a",
    ).replace("adaptive system", "")

    for forbidden in (
        "recommend",
        "mastery",
        "streak",
        "badge",
        "leaderboard",
        "score",
        "personaliz",
        "adaptive",
        "countdown",
        "timer",
    ):
        assert forbidden not in source, forbidden


def test_transition_layer_never_touches_history_or_persistence() -> None:
    """The content configuration cannot infer from learner state — it cannot see it."""
    source = PRACTICE_CONTINUITY_SOURCE.read_text(encoding="utf-8")

    assert "persistence" not in source
    assert "history_repository" not in source
    assert "PracticeHistoryRepository" not in source


def test_transition_copy_makes_the_relationship_visible_without_pressure() -> None:
    """§6: calm and editorial copy; no urgency or gamified language."""
    application = make_application()
    source_id = activity_id_by_title(
        application, "Observation Drill — Everyday Object Study"
    )

    completion = complete_activity(application, source_id)

    assert completion.continuation is not None
    copy = completion.continuation.transition_copy
    assert copy.startswith("You just")
    lowered = copy.lower()
    for pressure in ("don't miss", "hurry", "limited", "now or never", "best"):
        assert pressure not in lowered


def test_continuation_heading_and_action_are_calm_and_neutral() -> None:
    assert CONTINUATION_HEADING == "Continue the practice"
    assert CONTINUATION_ACTION_LABEL == "Try the next practice"
    assert "recommended" not in CONTINUATION_ACTION_LABEL.lower()
