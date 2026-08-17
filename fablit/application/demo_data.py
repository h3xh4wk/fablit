"""Demo content for the first learner vertical slice (SPEC-012, SPEC-015).

Provides the small, deterministic set of Skills and Assessment Activities the
dashboard shows (3–5 activities). SPEC-015 extends the demo content so that
image-dependent activities define a contextual stimulus requirement (§6), the
concepts a response-aware evaluator can recognise in learner responses
(§29–31), and a deterministic bundled fallback image (§22). The content is
generic practice material: it is not examination-specific and requires no
content infrastructure. The demo learner context (SPEC-012 §27) is a stable
identity — no fake user-management model.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fablit.domain import (
    ActivityStimulusContext,
    ActivityType,
    AssessmentActivity,
    Skill,
)

from .store import Concept, DemoActivity

# The deterministic demo learner context (SPEC-012 §27). Authentication and
# real learner identity are out of scope for the vertical slice; a stable
# identity leaves room for a future authenticated learner context.
DEMO_LEARNER_ID = UUID("6f9b1c4e-8a2d-4f3b-9c1e-5d7a2b4c8e10")

REFLECTION_PROMPT = (
    "What will you try differently the next time you practise this skill?"
)

#: The bundled fallback images served by the application (SPEC-015 §22).
COMPOSITION_IMAGE = "/static/images/stimulus-composition.svg"
DETAIL_IMAGE = "/static/images/stimulus-detail.svg"
COLOUR_MOOD_IMAGE = "/static/images/stimulus-colour-mood.svg"


@dataclass(frozen=True)
class DemoActivityDefinition:
    """Definition of one demo activity plus its demo findings and stimulus content."""

    title: str
    description: str
    activity_type: ActivityType
    prompt: str
    skill_names: tuple[str, ...]
    strength: str
    improvement: str
    next_step: str
    stimulus_context: ActivityStimulusContext | None = None
    concepts: tuple[Concept, ...] = ()
    fallback_image: str | None = None
    fallback_alt: str | None = None


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
        stimulus_context=ActivityStimulusContext(
            learning_focus="Composition",
            stimulus_context="Fashion editorial photography",
            retrieval_query="fashion editorial composition",
        ),
        concepts=(
            Concept(
                keyword="contrast",
                finding=(
                    "You noticed the contrast in the image, which is an important "
                    "part of how the composition directs attention."
                ),
            ),
            Concept(
                keyword="negative space",
                finding=(
                    "You noticed the use of negative space around the subject and "
                    "connected it to visual emphasis."
                ),
            ),
            Concept(
                keyword="empty space",
                finding=(
                    "You noticed the empty space around the subject, which shapes "
                    "the composition."
                ),
            ),
            Concept(
                keyword="balance",
                finding=(
                    "You noticed how the composition is balanced, which gives the "
                    "image its stability."
                ),
            ),
            Concept(
                keyword="symmetry",
                finding=(
                    "You noticed the symmetry in the image, which creates a sense "
                    "of order."
                ),
            ),
            Concept(
                keyword="leading lines",
                finding=(
                    "You noticed how lines lead your eye through the image, which "
                    "guides your attention."
                ),
            ),
            Concept(
                keyword="line",
                finding=(
                    "You noticed the lines in the image and how they direct your "
                    "eye through the composition."
                ),
            ),
            Concept(
                keyword="light",
                finding=(
                    "You noticed how light is used in the image, which shapes the "
                    "composition."
                ),
            ),
            Concept(
                keyword="shadow",
                finding=(
                    "You noticed the shadows, which add depth to the composition."
                ),
            ),
            Concept(
                keyword="texture",
                finding=(
                    "You noticed the texture in the image, which adds richness to "
                    "the composition."
                ),
            ),
            Concept(
                keyword="background",
                finding=(
                    "You noticed the background and how it relates to the subject, "
                    "which is central to the composition."
                ),
            ),
            Concept(
                keyword="foreground",
                finding=("You noticed the foreground, which anchors the composition."),
            ),
            Concept(
                keyword="subject",
                finding=(
                    "You identified the subject of the image, which is the focus "
                    "of the composition."
                ),
            ),
            Concept(
                keyword="figure",
                finding=(
                    "You noticed the figure in the image and how it sits within "
                    "the composition."
                ),
            ),
            Concept(
                keyword="model",
                finding=(
                    "You noticed the model in the image and how they are framed "
                    "by the composition."
                ),
            ),
            Concept(
                keyword="colour",
                finding=(
                    "You noticed how colour shapes the composition and directs the eye."
                ),
            ),
            Concept(
                keyword="color",
                finding=(
                    "You noticed how color shapes the composition and directs the eye."
                ),
            ),
            Concept(
                keyword="focus",
                finding=(
                    "You noticed what is in focus, which reveals the intended "
                    "emphasis of the composition."
                ),
            ),
        ),
        fallback_image=COMPOSITION_IMAGE,
        fallback_alt="A photograph-style composition for visual analysis.",
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
        stimulus_context=ActivityStimulusContext(
            learning_focus="Detail",
            stimulus_context="Everyday objects with interesting surface details",
            retrieval_query="macro close up surface detail texture",
        ),
        concepts=(
            Concept(
                keyword="texture",
                finding=(
                    "You noticed the texture, which is one of the most telling "
                    "details in the image."
                ),
            ),
            Concept(
                keyword="pattern",
                finding=(
                    "You noticed the pattern, which repeats in a meaningful way "
                    "across the image."
                ),
            ),
            Concept(
                keyword="shape",
                finding=(
                    "You noticed the shape of the object, which is a key visual detail."
                ),
            ),
            Concept(
                keyword="edge",
                finding=(
                    "You noticed the edges, which define where one detail ends and "
                    "another begins."
                ),
            ),
            Concept(
                keyword="reflection",
                finding=(
                    "You noticed the reflection, a subtle detail that reveals "
                    "something about the surface."
                ),
            ),
            Concept(
                keyword="light",
                finding=(
                    "You noticed how light falls across the surface, which reveals "
                    "its details."
                ),
            ),
            Concept(
                keyword="shadow",
                finding=(
                    "You noticed the shadow, which helps you read the depth of the "
                    "image."
                ),
            ),
            Concept(
                keyword="colour",
                finding=(
                    "You noticed the colour, which is a meaningful detail of the image."
                ),
            ),
            Concept(
                keyword="color",
                finding=(
                    "You noticed the color, which is a meaningful detail of the image."
                ),
            ),
            Concept(
                keyword="surface",
                finding=(
                    "You noticed the surface itself, which carries the finer "
                    "details of the image."
                ),
            ),
            Concept(
                keyword="background",
                finding=(
                    "You noticed the background, which frames the main subject of "
                    "the image."
                ),
            ),
            Concept(
                keyword="detail",
                finding=(
                    "You noticed a specific detail, which is exactly what careful "
                    "observation is about."
                ),
            ),
            Concept(
                keyword="grain",
                finding=(
                    "You noticed the grain, a fine detail that gives the image its "
                    "character."
                ),
            ),
        ),
        fallback_image=DETAIL_IMAGE,
        fallback_alt="A close-up view of a detailed surface for observation.",
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
        stimulus_context=ActivityStimulusContext(
            learning_focus="Colour and mood",
            stimulus_context="Warm and cool toned landscapes",
            retrieval_query="warm cool colour mood landscape",
        ),
        concepts=(
            Concept(
                keyword="warm",
                finding=(
                    "You noticed the warm colours, which give the image its "
                    "inviting mood."
                ),
            ),
            Concept(
                keyword="cool",
                finding=(
                    "You noticed the cool colours, which bring a quieter, calmer "
                    "mood to the image."
                ),
            ),
            Concept(
                keyword="bright",
                finding=("You noticed how brightness lifts the mood of the image."),
            ),
            Concept(
                keyword="dark",
                finding=(
                    "You noticed how the darker tones deepen the mood of the image."
                ),
            ),
            Concept(
                keyword="mood",
                finding=(
                    "You connected the colours to the overall mood, which is the "
                    "heart of this activity."
                ),
            ),
            Concept(
                keyword="tone",
                finding=(
                    "You noticed the tones in the image, which shape how the mood "
                    "is read."
                ),
            ),
            Concept(
                keyword="sky",
                finding=(
                    "You noticed the sky, which carries much of the colour in the "
                    "image."
                ),
            ),
            Concept(
                keyword="sunset",
                finding=(
                    "You noticed the sunset, whose colours set the mood of the "
                    "whole image."
                ),
            ),
            Concept(
                keyword="blue",
                finding=(
                    "You noticed the blue, which brings a calm, cool quality to "
                    "the image."
                ),
            ),
            Concept(
                keyword="red",
                finding=(
                    "You noticed the red, which adds energy and warmth to the image."
                ),
            ),
            Concept(
                keyword="orange",
                finding=(
                    "You noticed the orange, which sits between warmth and calm in "
                    "the image."
                ),
            ),
            Concept(
                keyword="yellow",
                finding=(
                    "You noticed the yellow, which brings a bright, sunny quality "
                    "to the image."
                ),
            ),
            Concept(
                keyword="colour",
                finding=(
                    "You noticed the colours themselves, which is the starting "
                    "point of this analysis."
                ),
            ),
            Concept(
                keyword="color",
                finding=(
                    "You noticed the colors themselves, which is the starting "
                    "point of this analysis."
                ),
            ),
            Concept(
                keyword="light",
                finding=(
                    "You noticed how light and colour work together to shape the mood."
                ),
            ),
            Concept(
                keyword="shadow",
                finding=(
                    "You noticed the shadows, whose darkness balances the brighter "
                    "colours."
                ),
            ),
        ),
        fallback_image=COLOUR_MOOD_IMAGE,
        fallback_alt="A landscape scene with warm and cool colours for analysis.",
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
                stimulus_context=definition.stimulus_context,
            ),
            title=definition.title,
            description=definition.description,
            strength=definition.strength,
            improvement=definition.improvement,
            next_step=definition.next_step,
            concepts=definition.concepts,
            fallback_image=definition.fallback_image,
            fallback_alt=definition.fallback_alt,
        )
        for position, definition in enumerate(_DEMO_ACTIVITIES)
    )


def build_demo_activity_map(
    activities: tuple[DemoActivity, ...],
) -> dict[UUID, DemoActivity]:
    """Map each demo activity identity to its demo activity content."""
    return {item.activity.id: item for item in activities}
