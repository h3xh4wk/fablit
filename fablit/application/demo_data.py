"""Demo content for the first learner vertical slice (SPEC-012).

Provides the small, deterministic set of Skills and Assessment Activities the
dashboard shows (3–5 activities) plus the predefined demo findings used by the
demo evaluator. The content is generic practice material: it is not
examination-specific and requires no content infrastructure. The demo learner
context (SPEC-012 §27) is a stable identity — no fake user-management model.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fablit.domain import ActivityType, AssessmentActivity, Skill

from .store import DemoActivity

# The deterministic demo learner context (SPEC-012 §27). Authentication and
# real learner identity are out of scope for the vertical slice; a stable
# identity leaves room for a future authenticated learner context.
DEMO_LEARNER_ID = UUID("6f9b1c4e-8a2d-4f3b-9c1e-5d7a2b4c8e10")

REFLECTION_PROMPT = (
    "What will you try differently the next time you practise this skill?"
)


@dataclass(frozen=True)
class DemoActivityDefinition:
    """Definition of one demo activity plus its predefined demo findings."""

    title: str
    description: str
    activity_type: ActivityType
    prompt: str
    skill_names: tuple[str, ...]
    strength: str
    improvement: str
    next_step: str


_DEMO_ACTIVITIES: tuple[DemoActivityDefinition, ...] = (
    DemoActivityDefinition(
        title="Visual Analysis — Composition",
        description="Analyse the composition of this photograph.",
        activity_type=ActivityType.WRITTEN_RESPONSE,
        prompt=(
            "Look at the photograph provided. Analyse its composition: identify the "
            "dominant visual elements and explain how they work together."
        ),
        skill_names=("Visual Analysis",),
        strength="You identified the dominant visual elements in your response.",
        improvement=(
            "Your response describes the elements separately; "
            "try explaining how they interact."
        ),
        next_step=(
            "Choose two elements and describe how their relationship "
            "affects the composition."
        ),
    ),
    DemoActivityDefinition(
        title="Written Communication — Explaining an Idea",
        description="Explain a complex idea in simple, clear language.",
        activity_type=ActivityType.WRITTEN_RESPONSE,
        prompt=(
            "Write a short response explaining a complex idea to someone who has "
            "never encountered it before."
        ),
        skill_names=("Written Communication",),
        strength="Your response explains the idea in clear, accessible language.",
        improvement=(
            "Your explanation could include a concrete example to anchor the idea."
        ),
        next_step=(
            "Rewrite one sentence with a specific example that illustrates the idea."
        ),
    ),
    DemoActivityDefinition(
        title="Observation — Detail Spotting",
        description="Practice noticing and describing meaningful visual details.",
        activity_type=ActivityType.OBSERVATION,
        prompt=(
            "Look at the image provided and describe the key visual details you "
            "notice, including their possible significance."
        ),
        skill_names=("Visual Analysis", "Critical Observation"),
        strength="You noticed several concrete details in the image.",
        improvement=(
            "Your observations focus on the obvious; try including smaller or "
            "less prominent details."
        ),
        next_step=(
            "Re-examine the image and find one detail you overlooked the first time."
        ),
    ),
    DemoActivityDefinition(
        title="Reflection — Process Review",
        description="Reflect on your recent practice process.",
        activity_type=ActivityType.REFLECTION,
        prompt=(
            "Think about your most recent practice session. What did you find most "
            "challenging, and why?"
        ),
        skill_names=("Critical Observation",),
        strength="You identified a specific challenge from your practice.",
        improvement=("Your reflection describes the challenge but not what caused it."),
        next_step=("Write one sentence about what you think caused the challenge."),
    ),
    DemoActivityDefinition(
        title="Visual Analysis — Colour and Mood",
        description="Analyse how colour shapes the mood of an image.",
        activity_type=ActivityType.WRITTEN_RESPONSE,
        prompt=(
            "Analyse how colour contributes to the mood of the image provided. "
            "Refer to specific colours."
        ),
        skill_names=("Visual Analysis",),
        strength="You correctly connected specific colours to the overall mood.",
        improvement=(
            "Your analysis mentions colour but does not explain how it guides "
            "the viewer's attention."
        ),
        next_step=("Describe how a single colour directs your eye through the image."),
    ),
)

_DEMO_SKILLS: tuple[Skill, ...] = (
    Skill(
        name="Visual Analysis",
        description=(
            "The ability to observe, interpret, and explain visual information."
        ),
    ),
    Skill(
        name="Written Communication",
        description="The ability to express ideas clearly and effectively in writing.",
    ),
    Skill(
        name="Critical Observation",
        description="The ability to notice and describe meaningful details.",
    ),
)


def _skill_ids(skill_names: tuple[str, ...]) -> tuple[UUID, ...]:
    """Map demo skill names to their stable identities."""
    by_name = {skill.name: skill.id for skill in _DEMO_SKILLS}
    return tuple(by_name[name] for name in skill_names)


def build_demo_skills() -> tuple[Skill, ...]:
    """Return the seeded demo Skills."""
    return _DEMO_SKILLS


def build_demo_activities() -> tuple[DemoActivity, ...]:
    """Build the seeded demo activities in deterministic order."""
    return tuple(
        DemoActivity(
            activity=AssessmentActivity(
                activity_type=definition.activity_type,
                instructions=definition.prompt,
                position=position,
                skill_ids=_skill_ids(definition.skill_names),
            ),
            title=definition.title,
            description=definition.description,
            strength=definition.strength,
            improvement=definition.improvement,
            next_step=definition.next_step,
        )
        for position, definition in enumerate(_DEMO_ACTIVITIES)
    )


def build_demo_findings(
    activities: tuple[DemoActivity, ...],
) -> dict[UUID, tuple[str, str, str]]:
    """Map each demo activity identity to its predefined findings.

    Each entry is ordered (strength, improvement, next step); the demo
    evaluator emits them as Findings in that order.
    """
    return {
        item.activity.id: (item.strength, item.improvement, item.next_step)
        for item in activities
    }
