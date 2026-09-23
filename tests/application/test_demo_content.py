"""Content-coverage tests for the expanded practice library (SPEC-023).

Covers the acceptance criteria that are about the content itself: the
library has been meaningfully expanded (AC-023-01), all five practice
capabilities are represented (AC-023-02), every activity has exactly one
primary capability (AC-023-03), the library varies meaningfully rather than
duplicating prompts (AC-023-04), activities reference valid Skill identities
and evaluation/feedback content (§19), Short Drill eligibility resolves only
to valid activities with expanded variety (AC-023-06, §19), and stimulus
configuration stays valid (§19).

The Observe / Interpret / Ideate / Articulate / Reflect lens is internal
content-design metadata: these tests also guard that it never leaks into the
learner journey and that no selection or recommendation machinery is built
on it (§14, AC-023-12, AC-023-13).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fablit.application import (
    DEMO_LEARNER_ID,
    PRACTICE_CAPABILITIES,
    PRACTICE_CAPABILITY_ARTICULATE,
    PRACTICE_CAPABILITY_IDEATE,
    PRACTICE_CAPABILITY_INTERPRET,
    PRACTICE_CAPABILITY_OBSERVE,
    PRACTICE_CAPABILITY_REFLECT,
    SHORT_DRILL_ACTIVITY_TITLES,
    DemoEvaluator,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
)
from fablit.application.demo_data import DemoActivityDefinition
from fablit.domain import ActivityType
from tests.domain.helpers import make_stimulus, make_submitted_submission

# --------------------------------------------------------------------------- #
# Expanded library (AC-023-01, §11)
# --------------------------------------------------------------------------- #


def test_library_is_meaningfully_expanded_beyond_the_baseline() -> None:
    """The five-activity baseline grows past the 10–12 initial target."""
    activities = build_demo_activities()

    assert len(activities) >= 10
    assert len(activities) <= 12


def test_original_five_activities_remain_available() -> None:
    """Expansion preserves the existing baseline library (AC-023-15)."""
    titles = {item.title for item in build_demo_activities()}

    assert {
        "CAT Practice — 2D & 3D Composition Analysis",
        "Creative Writing — Concept Explanations for Poster Designs",
        "Memory Drawing Prep — Object & Proportion Detection",
        "Situation Test Prep — Material & Design Process Reflection",
        "Color Theory — Mood & Atmosphere Interpretation",
    } <= titles


def test_every_activity_has_required_content_fields() -> None:
    """Each activity defines title, description, prompt, and feedback content."""
    for item in build_demo_activities():
        assert item.title.strip()
        assert item.description.strip()
        assert item.activity.instructions.strip()
        assert item.strength.strip()
        assert item.improvement.strip()
        assert item.next_step.strip()


def test_every_activity_references_valid_skill_identities() -> None:
    """Each activity's Skill references resolve to seeded demo Skills (§19)."""
    valid_skill_ids = {skill.id for skill in build_demo_skills()}

    for item in build_demo_activities():
        assert item.activity.skill_ids
        for skill_id in item.activity.skill_ids:
            assert skill_id in valid_skill_ids


def test_activity_titles_are_unique() -> None:
    """Titles are the stable content-configuration keys; they must not collide."""
    titles = [item.title for item in build_demo_activities()]

    assert len(titles) == len(set(titles))


# --------------------------------------------------------------------------- #
# Practice capability coverage (AC-023-02, AC-023-03, §5)
# --------------------------------------------------------------------------- #


def test_the_lens_defines_exactly_the_five_documented_capabilities() -> None:
    """The capability lens is the Observe/Interpret/Ideate/Articulate/Reflect set."""
    assert PRACTICE_CAPABILITIES == (
        PRACTICE_CAPABILITY_OBSERVE,
        PRACTICE_CAPABILITY_INTERPRET,
        PRACTICE_CAPABILITY_IDEATE,
        PRACTICE_CAPABILITY_ARTICULATE,
        PRACTICE_CAPABILITY_REFLECT,
    )


def test_every_activity_has_one_documented_primary_capability() -> None:
    """Each activity has exactly one primary capability (AC-023-03)."""
    for item in build_demo_activities():
        assert item.primary_capability in PRACTICE_CAPABILITIES


def test_secondary_capabilities_are_valid_and_distinct() -> None:
    """Secondaries extend — never contradict — the primary capability."""
    for item in build_demo_activities():
        for capability in item.secondary_capabilities:
            assert capability in PRACTICE_CAPABILITIES
            assert capability != item.primary_capability
        assert len(item.secondary_capabilities) == len(set(item.secondary_capabilities))


def test_all_five_capabilities_are_represented_across_the_library() -> None:
    """The library provides intentional coverage of every capability (AC-023-02)."""
    primary = {item.primary_capability for item in build_demo_activities()}

    assert primary == set(PRACTICE_CAPABILITIES)


def test_no_capability_relies_on_a_single_activity() -> None:
    """Each capability has more than one primary activity — coverage is robust."""
    primary_counts: dict[str, int] = {
        capability: 0 for capability in PRACTICE_CAPABILITIES
    }
    for item in build_demo_activities():
        primary_counts[item.primary_capability] += 1

    assert all(count >= 2 for count in primary_counts.values()), primary_counts


# --------------------------------------------------------------------------- #
# Meaningful variety (AC-023-04, §10)
# --------------------------------------------------------------------------- #


def test_activity_prompts_are_not_superficial_duplicates() -> None:
    """Every activity asks a distinct question of the learner (§10)."""
    prompts = [item.activity.instructions for item in build_demo_activities()]

    assert len(prompts) == len(set(prompts))


def test_library_varies_across_the_variety_dimensions() -> None:
    """Stimulus presence, activity type, and capability all vary (§10)."""
    activities = build_demo_activities()

    stimulus_states = {item.stimulus_context is not None for item in activities}
    assert stimulus_states == {True, False}

    assert len({item.activity.activity_type for item in activities}) >= 3

    assert len({item.primary_capability for item in activities}) == len(
        PRACTICE_CAPABILITIES
    )


def test_stimulus_activities_vary_their_retrieval_context() -> None:
    """Image-dependent activities do not all retrieve the same kind of image."""
    queries = [
        item.stimulus_context.retrieval_query
        for item in build_demo_activities()
        if item.stimulus_context is not None
    ]

    assert len(queries) >= 5
    assert len(queries) == len(set(queries))


# --------------------------------------------------------------------------- #
# Evaluation and feedback content (§12, §19)
# --------------------------------------------------------------------------- #


def test_every_activity_defines_feedback_and_next_step_content() -> None:
    """Each activity carries a plausible strength, improvement, and next step."""
    for item in build_demo_activities():
        assert item.strength.strip()
        assert item.improvement.strip()
        assert item.next_step.strip()


def test_stimulus_activities_define_response_aware_concepts() -> None:
    """Response-aware evaluation stays grounded: concepts and alt text present."""
    for item in build_demo_activities():
        if item.stimulus_context is None:
            continue
        assert item.concepts
        keywords = {concept.keyword for concept in item.concepts}
        assert len(keywords) == len(item.concepts)
        for concept in item.concepts:
            assert concept.keyword.strip()
            assert concept.finding.strip()
        assert item.fallback_image is not None
        assert item.fallback_alt is not None


def test_spaced_concept_keywords_ground_findings_in_real_responses() -> None:
    """A multi-word concept still matches and grounds a Finding (SPEC-015 §31).

    The evaluator lowercases the response and matches concepts by substring,
    so a spaced keyword such as "negative space" must surface as Finding
    evidence when the learner actually writes that phrase.
    """
    activities = build_demo_activities()
    item = next(
        candidate
        for candidate in activities
        if any(" " in concept.keyword for concept in candidate.concepts)
    )
    spaced = next(concept for concept in item.concepts if " " in concept.keyword)
    evaluator = DemoEvaluator(build_demo_activity_map(activities))
    submission = make_submitted_submission(
        learner_id=DEMO_LEARNER_ID,
        activity_id=item.activity.id,
        response=f"I notice the {spaced.keyword}.",
    )

    evaluation = evaluator.evaluate(
        submission,
        activity=item.activity,
        stimulus=make_stimulus(activity_id=item.activity.id, provider="fablit"),
    )

    assert spaced.keyword in [finding.evidence for finding in evaluation.findings]


# --------------------------------------------------------------------------- #
# Short Drill configuration (AC-023-06, §8, §19)
# --------------------------------------------------------------------------- #


def test_short_drill_configuration_resolves_only_to_valid_activities() -> None:
    """Every curated title resolves to a seeded activity (§19)."""
    seeded_titles = {item.title for item in build_demo_activities()}

    assert set(SHORT_DRILL_ACTIVITY_TITLES) <= seeded_titles


def test_short_drill_set_is_expanded_beyond_the_original_two() -> None:
    """The curated set is larger and more varied than the SPEC-022 baseline."""
    assert len(SHORT_DRILL_ACTIVITY_TITLES) > 2


def test_short_drill_set_provides_capability_variety() -> None:
    """The curated set spans multiple capabilities (AC-023-06)."""
    by_title = {item.title: item for item in build_demo_activities()}
    capabilities = {
        by_title[title].primary_capability for title in SHORT_DRILL_ACTIVITY_TITLES
    }

    assert len(capabilities) >= 4


def test_short_drill_entries_have_focused_prompts_and_responses() -> None:
    """Drill candidates stay concise (§8): short prompt, no countdown language."""
    by_title = {item.title: item for item in build_demo_activities()}
    forbidden = ("countdown", "time limit", "deadline", "must finish")

    for title in SHORT_DRILL_ACTIVITY_TITLES:
        item = by_title[title]
        lowered_prompt = item.activity.instructions.lower()
        assert len(item.activity.instructions) <= 260
        assert not any(term in lowered_prompt for term in forbidden)


# --------------------------------------------------------------------------- #
# Stimulus configuration (§13, §19)
# --------------------------------------------------------------------------- #


def test_bundled_fallback_images_exist_for_every_stimulus_activity() -> None:
    """Each stimulus activity points at a bundled, deterministic fallback."""
    static_images = Path("app/static/images")

    for item in build_demo_activities():
        if item.fallback_image is None:
            continue
        assert item.fallback_image.startswith("/static/images/")
        asset = static_images / Path(item.fallback_image).name
        assert asset.is_file(), f"missing bundled stimulus: {asset}"


def test_fallback_images_are_unique_per_activity() -> None:
    """Each stimulus activity offers a visually distinct fallback stimulus."""
    images = [
        item.fallback_image
        for item in build_demo_activities()
        if item.fallback_image is not None
    ]

    assert len(images) == len(set(images))


# --------------------------------------------------------------------------- #
# The lens never reaches the learner (§6, §14, AC-023-12, AC-023-13)
# --------------------------------------------------------------------------- #


def test_capability_data_never_reaches_learner_facing_templates() -> None:
    """The capability lens stays internal: no template renders or filters on it.

    (The "Observe" section heading in the practice workspace is SPEC-020 UI
    language, not the SPEC-023 capability lens — plain-word scanning would
    give a false positive here, so this guards the actual leak vector:
    capability fields reaching template context.)
    """
    template_dir = Path("app/templates")
    pattern = re.compile(r"capability|primary_capab|secondary_capab", re.IGNORECASE)

    for template in sorted(template_dir.glob("*.html")):
        matches = pattern.findall(template.read_text(encoding="utf-8"))
        assert not matches, f"{template.name} references capability data: {matches}"


def test_capability_metadata_is_not_exposed_through_view_models() -> None:
    """Dashboard and mode summaries carry no capability field (§6)."""
    from fablit.application.view_models import (
        CompletionView,
        FeedbackView,
        PracticeActivitySummary,
        PracticeActivityView,
        PracticeDashboardView,
        PracticeHistoryEntry,
        PracticeModeActivitiesView,
        PracticeModeChoiceView,
        PracticeModeOption,
        PracticeReviewView,
        ReflectionView,
        StimulusView,
    )

    learner_facing_views = (
        PracticeActivitySummary,
        PracticeActivityView,
        PracticeDashboardView,
        PracticeModeChoiceView,
        PracticeModeOption,
        PracticeModeActivitiesView,
        FeedbackView,
        ReflectionView,
        CompletionView,
        PracticeHistoryEntry,
        PracticeReviewView,
        StimulusView,
    )

    for view in learner_facing_views:
        fields = {name.lower() for name in view.__dataclass_fields__}
        for forbidden in ("capability", "primary_capability", "secondary_capability"):
            assert not any(forbidden in field for field in fields), view.__name__


# --------------------------------------------------------------------------- #
# Definitions carry no content-infra weight (§4 out of scope)
# --------------------------------------------------------------------------- #


def test_activity_definitions_stay_pure_content_configuration() -> None:
    """A definition is plain content data — no infrastructure or schema creep."""
    definition = DemoActivityDefinition(
        title="t",
        description="d",
        activity_type=ActivityType.OBSERVATION,
        prompt="p",
        skill_names=("Visual Analysis",),
        strength="s",
        improvement="i",
        next_step="n",
        primary_capability=PRACTICE_CAPABILITY_OBSERVE,
    )

    assert definition.stimulus_context is None
    assert definition.concepts == ()
    assert definition.fallback_image is None
    assert definition.secondary_capabilities == ()


@pytest.mark.parametrize("term", ["score", "points", "badge", "streak", "leaderboard"])
def test_content_contains_no_gamification_language(term: str) -> None:
    """Expansion adds no scoring or rewards language (AC-023-13)."""
    source = Path("fablit/application/demo_data.py").read_text(encoding="utf-8")

    assert term not in source.lower()
