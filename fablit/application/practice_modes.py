"""Practice-mode selection at the application/learner-experience boundary (SPEC-022).

SPEC-022 gives learners an explicit, small choice about the shape of their
practice: a compact Short Drill (about 5–10 minutes of learner effort, as an
indication rather than a limit) or the existing Full Practice experience. A
practice mode is deliberately NOT a domain concept: it never re-identifies,
wraps, or replaces an Assessment Activity, and it carries no scheduling,
scoring, mastery, or personalization semantics. A mode only points at
existing activities; choosing one starts the unchanged SPEC-012 learner
journey, and completed practice remains ordinary SPEC-021 history.

Eligibility is explicit, curated configuration (SPEC-022 §6, AC-022-07): the
Short Drill resolves to activities listed in the demo/content configuration
(``SHORT_DRILL_ACTIVITY_TITLES``), never to an activity whose title merely
looks suitable at request time, and never from learner history or hidden
personalization (§12, AC-022-10). New activities become drill-eligible by
editing the content list — not application logic (§13).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from .demo_data import (
    FULL_PRACTICE_DESCRIPTION,
    FULL_PRACTICE_EFFORT_GUIDANCE,
    FULL_PRACTICE_LABEL,
    SHORT_DRILL_ACTIVITY_TITLES,
    SHORT_DRILL_DESCRIPTION,
    SHORT_DRILL_EFFORT_GUIDANCE,
    SHORT_DRILL_LABEL,
)
from .store import DemoActivity


class PracticeMode(StrEnum):
    """The learner-selectable shapes of practice (SPEC-022 §5).

    Values are stable learner-facing identifiers used in URLs; the initial
    set is deliberately small so the choice stays understandable in seconds.
    """

    SHORT_DRILL = "short-drill"
    FULL_PRACTICE = "full-practice"


@dataclass(frozen=True)
class PracticeModeDefinition:
    """One supported practice mode and its curated eligibility (SPEC-022 §5).

    A definition is application/learner-experience state, not a domain
    object: it never duplicates activity identity, Skill semantics,
    Evaluation semantics, or Completion semantics — it only names which
    existing activities the learner may practise through the unchanged
    journey when they choose this mode.
    """

    mode: PracticeMode
    label: str
    description: str
    effort_guidance: str
    eligible_activity_ids: tuple[UUID, ...]

    def is_eligible(self, activity_id: UUID) -> bool:
        """Whether an existing activity is offered through this mode."""
        return activity_id in self.eligible_activity_ids


def _short_drill_eligibility(
    activities: tuple[DemoActivity, ...],
) -> tuple[UUID, ...]:
    """Resolve the curated Short Drill content to stable activity identities.

    SPEC-022 §6/§13: eligibility is explicit content configuration. The
    curated titles are resolved to the seeded activities' identities;
    titles that no longer match seeded content are skipped so the
    configuration can drift safely. Nothing here judges an activity's title
    for suitability — the list itself is the configuration (AC-022-07).
    """
    by_title = {item.title: item for item in activities}
    return tuple(
        by_title[title].activity.id
        for title in SHORT_DRILL_ACTIVITY_TITLES
        if title in by_title
    )


def build_practice_mode_definitions(
    activities: tuple[DemoActivity, ...],
) -> tuple[PracticeModeDefinition, ...]:
    """Build the supported practice modes against the seeded activities.

    SPEC-022 §5/§14: the application layer presents the available modes and
    resolves each to eligible existing activities. Short Drill eligibility
    comes from the curated content list; Full Practice is the existing
    library, so every seeded activity is eligible (§6, §9).
    """
    return (
        PracticeModeDefinition(
            mode=PracticeMode.SHORT_DRILL,
            label=SHORT_DRILL_LABEL,
            description=SHORT_DRILL_DESCRIPTION,
            effort_guidance=SHORT_DRILL_EFFORT_GUIDANCE,
            eligible_activity_ids=_short_drill_eligibility(activities),
        ),
        PracticeModeDefinition(
            mode=PracticeMode.FULL_PRACTICE,
            label=FULL_PRACTICE_LABEL,
            description=FULL_PRACTICE_DESCRIPTION,
            effort_guidance=FULL_PRACTICE_EFFORT_GUIDANCE,
            eligible_activity_ids=tuple(item.activity.id for item in activities),
        ),
    )
