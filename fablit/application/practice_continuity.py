"""Curated next-practice transitions at the content layer (SPEC-025).

After completing a practice activity, the learner may see a quiet
continuation: one authored next practice, with the relationship between the
two activities made visible. SPEC-025 is authored content continuity, not an
adaptive system (§2, §10): the relationship between activities is defined by
Fablit's content/design layer and is deliberately NOT derived from learner
history, completion counts, evaluations, or inferred behaviour (§3.2, AC 4).

The transition table is a small explicit content configuration (§7), in the
same style as the SPEC-022 Short Drill eligibility list: new transitions are
added by editing the configuration, never application logic. A transition
conceptually contains a source activity, a target activity, and optional
learner-facing transition copy (§7). Sources are matched to the seeded demo
activities by title — the same title-keyed convention as
``SHORT_DRILL_ACTIVITY_TITLES`` and the stimulus fallback override map — and
resolved to stable activity identities by :func:`build_practice_transitions`.

A transition is not a domain concept and never wraps or re-identifies an
Assessment Activity: starting the target activity runs the unchanged
Submission → Evaluation → Feedback → Reflection → Completion journey (§3.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .store import DemoActivity

#: Learner-facing heading for the completion continuation (SPEC-025 §6).
CONTINUATION_HEADING = "Continue the practice"

#: Learner-facing call to action for starting the curated next practice (§6).
CONTINUATION_ACTION_LABEL = "Try the next practice"

#: The authored transition table (SPEC-025 §4): (source title, target title,
#: learner-facing transition copy) triples against the seeded demo content.
#: Every relationship was checked against the actual activity content — each
#: demonstrates movement between capabilities rather than a shared label.
#: New transitions are added by editing this table, not application logic.
_AUTHORED_TRANSITIONS: tuple[tuple[str, str, str], ...] = (
    (
        "Observation Drill — Everyday Object Study",
        "Design Ideation — Transform the Object",
        "You just observed an object closely. "
        "Now try turning that observation into a design idea.",
    ),
    (
        "Memory Drawing Prep — Object & Proportion Detection",
        "Short Ideation Sprint — Alternative Uses",
        "You just practised noticing real details. "
        "Now try imagining what an everyday object could also become.",
    ),
    (
        "CAT Practice — 2D & 3D Composition Analysis",
        "Visual Interpretation — Reading a Street Scene",
        "You just analysed how a composition works. "
        "Now try reading what a whole scene might be telling you.",
    ),
    (
        "Color Theory — Mood & Atmosphere Interpretation",
        "Design Articulation — Explain a Poster Concept",
        "You just read how colour shapes mood. "
        "Now try explaining a design's choices in words.",
    ),
    (
        "Short Ideation Sprint — Alternative Uses",
        "Design Articulation — Explain a Poster Concept",
        "You just generated a range of ideas. "
        "Now try putting one idea into clear, convincing language.",
    ),
    (
        "Design Ideation — Transform the Object",
        "Design Articulation — Explain a Poster Concept",
        "You just turned an observation into a design idea. "
        "Now try explaining a concept so someone else can see it.",
    ),
    (
        "Reflection Prompt — What Did Practice Ask of You?",
        "Observation Drill — Everyday Object Study",
        "You just paused to look at your own practice. "
        "Now return to slow, deliberate looking.",
    ),
)


@dataclass(frozen=True)
class PracticeTransition:
    """One authored next-practice relationship (SPEC-025 §3.2, §7).

    A transition is content-level state, not a domain object: it names two
    existing activities and the authored copy that makes their relationship
    visible. It carries no learner state whatsoever — two learners who
    complete the same activity always receive the same continuation
    (AC 2, AC 4, AC 10).
    """

    source_activity_id: UUID
    target_activity_id: UUID
    transition_copy: str


def build_practice_transitions(
    activities: tuple[DemoActivity, ...],
) -> tuple[PracticeTransition, ...]:
    """Resolve the curated transition table to stable activity identities.

    SPEC-025 §3.2/§7: relationships are authored deliberately against the
    actual activity content and must refer to existing activities. Titles
    are resolved to the seeded activities' identities; titles that no longer
    match seeded content are skipped so the configuration can drift safely,
    in the same style as the SPEC-022 eligibility resolution.
    """
    by_title = {item.title: item for item in activities}
    transitions = (
        _resolve(by_title, source, target, copy)
        for source, target, copy in _AUTHORED_TRANSITIONS
    )
    return tuple(transition for transition in transitions if transition is not None)


def _resolve(
    by_title: dict[str, DemoActivity],
    source_title: str,
    target_title: str,
    copy: str,
) -> PracticeTransition | None:
    """Resolve one authored relationship, skipping drifted-away titles."""
    source = by_title.get(source_title)
    target = by_title.get(target_title)
    if source is None or target is None:
        return None
    return PracticeTransition(
        source_activity_id=source.activity.id,
        target_activity_id=target.activity.id,
        transition_copy=copy,
    )


def build_practice_transition_map(
    activities: tuple[DemoActivity, ...],
) -> dict[UUID, PracticeTransition]:
    """Map each source activity identity to its authored transition.

    SPEC-025 §3.2: one completed activity may point to one curated next
    activity, so the map is keyed by source identity. The lookup is
    deterministic for the same content configuration (AC 2) and touches no
    learner state.
    """
    return {
        transition.source_activity_id: transition
        for transition in build_practice_transitions(activities)
    }
