"""Demo content for the first learner vertical slice (SPEC-012, SPEC-015, SPEC-022,
SPEC-023).

Provides the deterministic set of Skills and Assessment Activities the
dashboard shows. SPEC-023 expands the practice library from the original
five-activity baseline to a varied twelve-activity set so that repeated
deliberate practice is plausible, and gives every activity a documented
primary practice capability (and optional secondary capabilities) using the
internal Observe / Interpret / Ideate / Articulate / Reflect lens (§2, §5).
That lens is a content-design and review aid — it is deliberately NOT a
domain concept, a learner-facing taxonomy, or a model of what a learner has
achieved, and no recommendation or selection logic is built on it
(§12, AC-023-12).
SPEC-015 extends the demo content so that
image-dependent activities define a contextual stimulus requirement (§6), the
concepts a response-aware evaluator can recognise in learner responses
(§29–31), and a deterministic bundled fallback image (§22). Activity titles use
exam-oriented labels for the initial design-aspirant pilot (issue #65) while the
underlying Skill and Assessment Activity model stays exam-neutral; the labels
live in demo content, not application logic. The content requires no content
infrastructure. The demo learner context (SPEC-012 §27) is a stable identity —
no fake user-management model.
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
#
# SPEC-024: this fixed identity is no longer used for normal web traffic —
# the web layer resolves a unique anonymous learner identity per browser
# (app.learner_session). It remains demo-content metadata used by
# application-layer tests to exercise the learner-scoped contracts.
DEMO_LEARNER_ID = UUID("6f9b1c4e-8a2d-4f3b-9c1e-5d7a2b4c8e10")

REFLECTION_PROMPT = (
    "What will you try differently the next time you practise this skill?"
)

#: The bundled fallback images served by the application (SPEC-015 §22).
COMPOSITION_IMAGE = "/static/images/stimulus-composition.svg"
DETAIL_IMAGE = "/static/images/stimulus-detail.svg"
COLOUR_MOOD_IMAGE = "/static/images/stimulus-colour-mood.svg"
OBJECT_STUDY_IMAGE = "/static/images/stimulus-object-study.svg"
STREET_SCENE_IMAGE = "/static/images/stimulus-street-scene.svg"
OBJECT_TRANSFORM_IMAGE = "/static/images/stimulus-object-transform.svg"
COMPOSITION_DETECTIVE_IMAGE = "/static/images/stimulus-composition-detective.svg"

# --- Practice-mode content (SPEC-022) ------------------------------------------
# Learner-facing copy for the practice-mode chooser (SPEC-022 §7). The exact
# wording may evolve through UX review; the semantics do not: effort guidance
# is an indication, never a countdown, a limit, or a penalty (§10).

PRACTICE_MODE_CHOICE_QUESTION = "What kind of practice feels right today?"

SHORT_DRILL_LABEL = "A short drill"
SHORT_DRILL_DESCRIPTION = "A few minutes to notice, write, or reset your attention."
SHORT_DRILL_EFFORT_GUIDANCE = "About 5–10 minutes, whenever suits you."

FULL_PRACTICE_LABEL = "A full practice"
FULL_PRACTICE_DESCRIPTION = (
    "A longer focused activity with the complete practice journey."
)
FULL_PRACTICE_EFFORT_GUIDANCE = "Take as long as you like — there's no clock."

#: Activities eligible for the Short Drill practice mode (SPEC-022 §6, §13,
#: expanded by SPEC-023 §8). Explicit, curated content configuration
#: (AC-022-07, AC-023-06): concise activities with a focused prompt and a
#: short response expectation, chosen for capability variety — observation,
#: writing, ideation, and reflection are all represented. Matched to the
#: seeded demo activities by title — the same title-keyed convention as the
#: FABLIT_STIMULUS_FALLBACK_IMAGES override map. Eligibility is resolved to
#: stable activity identities by the application's mode layer; new activities
#: become drill-eligible by editing this list, not application logic, and
#: nothing selects or orders activities from learner history (AC-023-12).
SHORT_DRILL_ACTIVITY_TITLES: tuple[str, ...] = (
    "Memory Drawing Prep — Object & Proportion Detection",
    "Creative Writing — Concept Explanations for Poster Designs",
    "Observation Drill — Everyday Object Study",
    "Short Ideation Sprint — Alternative Uses",
    "Design Articulation — Explain a Poster Concept",
    "Reflection Prompt — What Did Practice Ask of You?",
)

# --- Practice coverage lens (SPEC-023 §2, §5) -----------------------------------
# The five practice capabilities are an internal content-design lens for
# reviewing the library for balance and coverage. They are deliberately NOT
# a domain concept: no Skill hierarchy, no learner mastery model, no
# learner-facing taxonomy — activity content stays understandable without
# them (§6), and no capability drives selection, ordering, or recommendations
# (§14, AC-023-12). The labels never appear in learner-visible copy or URLs.

PRACTICE_CAPABILITY_OBSERVE = "Observe"
PRACTICE_CAPABILITY_INTERPRET = "Interpret"
PRACTICE_CAPABILITY_IDEATE = "Ideate"
PRACTICE_CAPABILITY_ARTICULATE = "Articulate"
PRACTICE_CAPABILITY_REFLECT = "Reflect"

#: Every capability the content-design lens recognises, in review order.
PRACTICE_CAPABILITIES: tuple[str, ...] = (
    PRACTICE_CAPABILITY_OBSERVE,
    PRACTICE_CAPABILITY_INTERPRET,
    PRACTICE_CAPABILITY_IDEATE,
    PRACTICE_CAPABILITY_ARTICULATE,
    PRACTICE_CAPABILITY_REFLECT,
)


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
    #: The activity's primary practice capability (SPEC-023 §5, AC-023-03):
    #: an internal content-design label, never learner-facing.
    primary_capability: str
    stimulus_context: ActivityStimulusContext | None = None
    concepts: tuple[Concept, ...] = ()
    fallback_image: str | None = None
    fallback_alt: str | None = None
    #: Capabilities the activity genuinely exercises beyond its primary one
    #: (SPEC-023 §5); empty when the activity is single-focused.
    secondary_capabilities: tuple[str, ...] = ()


_DEMO_ACTIVITIES: tuple[DemoActivityDefinition, ...] = (
    DemoActivityDefinition(
        title="CAT Practice — 2D & 3D Composition Analysis",
        description="Analyse the composition of this photograph.",
        activity_type=ActivityType.WRITTEN_RESPONSE,
        prompt=(
            "Look at the photograph provided. Analyse its composition: identify the "
            "dominant visual elements and explain how they work together."
        ),
        skill_names=("Visual Analysis",),
        strength="You identified the dominant visual elements in your response.",
        primary_capability=PRACTICE_CAPABILITY_INTERPRET,
        secondary_capabilities=(PRACTICE_CAPABILITY_OBSERVE,),
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
        title="Creative Writing — Concept Explanations for Poster Designs",
        description="Explain a complex idea in simple, clear language.",
        activity_type=ActivityType.WRITTEN_RESPONSE,
        prompt=(
            "Write a short response explaining a complex idea to someone who has "
            "never encountered it before."
        ),
        skill_names=("Written Communication",),
        strength="Your response explains the idea in clear, accessible language.",
        primary_capability=PRACTICE_CAPABILITY_ARTICULATE,
        improvement=(
            "Your explanation could include a concrete example to anchor the idea."
        ),
        next_step=(
            "Rewrite one sentence with a specific example that illustrates the idea."
        ),
    ),
    DemoActivityDefinition(
        title="Memory Drawing Prep — Object & Proportion Detection",
        description="Practice noticing and describing meaningful visual details.",
        activity_type=ActivityType.OBSERVATION,
        prompt=(
            "Look at the image provided and describe the key visual details you "
            "notice, including their possible significance."
        ),
        skill_names=("Visual Analysis", "Critical Observation"),
        strength="You noticed several concrete details in the image.",
        primary_capability=PRACTICE_CAPABILITY_OBSERVE,
        secondary_capabilities=(PRACTICE_CAPABILITY_INTERPRET,),
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
        title="Situation Test Prep — Material & Design Process Reflection",
        description="Reflect on your recent practice process.",
        activity_type=ActivityType.REFLECTION,
        prompt=(
            "Think about your most recent practice session. What did you find most "
            "challenging, and why?"
        ),
        skill_names=("Critical Observation",),
        strength="You identified a specific challenge from your practice.",
        primary_capability=PRACTICE_CAPABILITY_REFLECT,
        improvement=("Your reflection describes the challenge but not what caused it."),
        next_step=("Write one sentence about what you think caused the challenge."),
    ),
    DemoActivityDefinition(
        title="Color Theory — Mood & Atmosphere Interpretation",
        description="Analyse how colour shapes the mood of an image.",
        activity_type=ActivityType.WRITTEN_RESPONSE,
        prompt=(
            "Analyse how colour contributes to the mood of the image provided. "
            "Refer to specific colours."
        ),
        skill_names=("Visual Analysis",),
        strength="You correctly connected specific colours to the overall mood.",
        primary_capability=PRACTICE_CAPABILITY_INTERPRET,
        secondary_capabilities=(
            PRACTICE_CAPABILITY_OBSERVE,
            PRACTICE_CAPABILITY_ARTICULATE,
        ),
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
    DemoActivityDefinition(
        title="Observation Drill — Everyday Object Study",
        description="Practise slow, detailed looking at a single object.",
        activity_type=ActivityType.OBSERVATION,
        prompt=(
            "Look closely at the object in the image. Describe its surfaces, edges, "
            "and details — include what the wear and material suggest about how it "
            "has been used."
        ),
        skill_names=("Visual Analysis", "Critical Observation"),
        strength="You described concrete surface details of the object.",
        improvement=(
            "Your observations stay at the level of naming; try describing how one "
            "detail relates to another."
        ),
        next_step=(
            "Pick the smallest detail you can find and describe what it tells you "
            "about the object."
        ),
        primary_capability=PRACTICE_CAPABILITY_OBSERVE,
        secondary_capabilities=(PRACTICE_CAPABILITY_INTERPRET,),
        stimulus_context=ActivityStimulusContext(
            learning_focus="Object detail",
            stimulus_context="A well-used everyday object",
            retrieval_query="worn everyday object close up surface",
        ),
        concepts=(
            Concept(
                keyword="wear",
                finding=(
                    "You noticed the wear on the object, which records how it has "
                    "actually been used."
                ),
            ),
            Concept(
                keyword="texture",
                finding=(
                    "You noticed the texture of the object's surface, which tells "
                    "you about its material."
                ),
            ),
            Concept(
                keyword="edge",
                finding=(
                    "You noticed the object's edges, which define its form against "
                    "the background."
                ),
            ),
            Concept(
                keyword="scratch",
                finding=(
                    "You noticed the scratches, small details that carry the "
                    "object's history."
                ),
            ),
            Concept(
                keyword="surface",
                finding=(
                    "You described the object's surface, which is where careful "
                    "observation begins."
                ),
            ),
            Concept(
                keyword="handle",
                finding=("You noticed the handle and how it has been shaped by use."),
            ),
            Concept(
                keyword="metal",
                finding=(
                    "You noticed the metal, whose finish changes how light sits on "
                    "the object."
                ),
            ),
            Concept(
                keyword="wood",
                finding=(
                    "You noticed the wood, whose grain adds direction to the surface."
                ),
            ),
            Concept(
                keyword="light",
                finding=(
                    "You noticed how light falls on the object, which reveals its form."
                ),
            ),
            Concept(
                keyword="shadow",
                finding=(
                    "You noticed the shadow the object casts, which grounds it in "
                    "the scene."
                ),
            ),
            Concept(
                keyword="reflection",
                finding=(
                    "You noticed the reflection on the surface, a detail that "
                    "reveals the material."
                ),
            ),
            Concept(
                keyword="colour",
                finding=(
                    "You noticed the object's colour, including how it varies "
                    "across the surface."
                ),
            ),
            Concept(
                keyword="color",
                finding=(
                    "You noticed the object's color, including how it varies "
                    "across the surface."
                ),
            ),
            Concept(
                keyword="detail",
                finding=(
                    "You noticed a specific detail, which is exactly what slow "
                    "looking is about."
                ),
            ),
            Concept(
                keyword="material",
                finding=(
                    "You considered the material itself, which explains much of "
                    "what you see."
                ),
            ),
        ),
        fallback_image=OBJECT_STUDY_IMAGE,
        fallback_alt="A close-up study of a worn everyday object.",
    ),
    DemoActivityDefinition(
        title="Visual Interpretation — Reading a Street Scene",
        description="Read the story a busy scene might tell.",
        activity_type=ActivityType.WRITTEN_RESPONSE,
        prompt=(
            "Look at the street scene in the image. What might be happening here? "
            "Support your reading with at least two specific visual details."
        ),
        skill_names=("Visual Analysis",),
        strength=(
            "You connected specific details in the scene to a possible reading of it."
        ),
        improvement=(
            "Some of your reading goes beyond what the image shows; tie each claim "
            "back to a visible detail."
        ),
        next_step=(
            "Choose one detail in the scene and describe two different things it "
            "could mean."
        ),
        primary_capability=PRACTICE_CAPABILITY_INTERPRET,
        secondary_capabilities=(
            PRACTICE_CAPABILITY_OBSERVE,
            PRACTICE_CAPABILITY_ARTICULATE,
        ),
        stimulus_context=ActivityStimulusContext(
            learning_focus="Interpretation",
            stimulus_context="Everyday street scenes with people",
            retrieval_query="street scene people daily life city",
        ),
        concepts=(
            Concept(
                keyword="people",
                finding=(
                    "You noticed the people in the scene, whose positions and "
                    "movement carry much of its story."
                ),
            ),
            Concept(
                keyword="movement",
                finding=(
                    "You noticed the movement in the scene, which gives the image "
                    "its sense of pace."
                ),
            ),
            Concept(
                keyword="sign",
                finding=(
                    "You noticed the signs, which anchor the scene in a particular "
                    "place."
                ),
            ),
            Concept(
                keyword="shop",
                finding=(
                    "You noticed the shopfronts, which suggest the everyday life "
                    "of the street."
                ),
            ),
            Concept(
                keyword="light",
                finding=(
                    "You noticed how light falls across the scene, which shapes "
                    "its time of day and mood."
                ),
            ),
            Concept(
                keyword="shadow",
                finding=(
                    "You noticed the shadows, which add depth and direction to "
                    "the scene."
                ),
            ),
            Concept(
                keyword="mood",
                finding=(
                    "You connected the scene's details to an overall mood, which "
                    "is the heart of interpretation."
                ),
            ),
            Concept(
                keyword="story",
                finding=(
                    "You read a possible story in the scene, which is exactly what "
                    "this activity asks."
                ),
            ),
            Concept(
                keyword="foreground",
                finding=(
                    "You noticed the foreground, which brings the viewer into the "
                    "scene."
                ),
            ),
            Concept(
                keyword="background",
                finding=(
                    "You noticed the background, which sets the context for what "
                    "is happening."
                ),
            ),
            Concept(
                keyword="street",
                finding=(
                    "You considered the street itself — its space, direction, and "
                    "rhythm."
                ),
            ),
            Concept(
                keyword="crowd",
                finding=(
                    "You noticed the crowd, whose density tells you something "
                    "about the moment."
                ),
            ),
            Concept(
                keyword="colour",
                finding=(
                    "You noticed the scene's colours, which suggest its time, "
                    "weather, and atmosphere."
                ),
            ),
            Concept(
                keyword="color",
                finding=(
                    "You noticed the scene's colors, which suggest its time, "
                    "weather, and atmosphere."
                ),
            ),
        ),
        fallback_image=STREET_SCENE_IMAGE,
        fallback_alt="A street scene with people and shopfronts for interpretation.",
    ),
    DemoActivityDefinition(
        title="Short Ideation Sprint — Alternative Uses",
        description="Practise generating many ideas in a few minutes.",
        activity_type=ActivityType.WRITTEN_RESPONSE,
        prompt=(
            "Think of an ordinary object you use every day. List as many unusual "
            "uses for it as you can — then mark the one you would develop further."
        ),
        skill_names=("Written Communication",),
        strength=(
            "You generated several different directions instead of settling on the "
            "first idea."
        ),
        improvement=(
            "Several of your uses are close variations; push one further from the "
            "object's usual role."
        ),
        next_step=(
            "Take your strongest idea and write two sentences on why it could "
            "actually work."
        ),
        primary_capability=PRACTICE_CAPABILITY_IDEATE,
        secondary_capabilities=(PRACTICE_CAPABILITY_ARTICULATE,),
    ),
    DemoActivityDefinition(
        title="Design Ideation — Transform the Object",
        description="Turn an observed object into a new design possibility.",
        activity_type=ActivityType.WRITTEN_RESPONSE,
        prompt=(
            "Look at the object in the image and reimagine it as something new. "
            "Describe your transformed design and explain the thinking behind it."
        ),
        skill_names=("Visual Analysis", "Written Communication"),
        strength=(
            "You proposed a clear transformation grounded in the object's actual form."
        ),
        improvement=(
            "Your concept explains what the new design is but not why it works; "
            "connect the design back to what you observed."
        ),
        next_step=(
            "Name one feature of the original object your design keeps, and why."
        ),
        primary_capability=PRACTICE_CAPABILITY_IDEATE,
        secondary_capabilities=(
            PRACTICE_CAPABILITY_INTERPRET,
            PRACTICE_CAPABILITY_ARTICULATE,
        ),
        stimulus_context=ActivityStimulusContext(
            learning_focus="Transformation",
            stimulus_context="Ordinary household objects",
            retrieval_query="single household object white background",
        ),
        concepts=(
            Concept(
                keyword="form",
                finding=(
                    "You worked with the object's form, which gives your new design "
                    "its structure."
                ),
            ),
            Concept(
                keyword="function",
                finding=(
                    "You thought about function, which turns a shape into a real "
                    "design."
                ),
            ),
            Concept(
                keyword="transform",
                finding=(
                    "You transformed the object deliberately, which is exactly what "
                    "ideation asks of you."
                ),
            ),
            Concept(
                keyword="combine",
                finding=(
                    "You combined the object with something new — a productive "
                    "ideation move."
                ),
            ),
            Concept(
                keyword="material",
                finding=(
                    "You considered the material, which constrains and inspires "
                    "what the design can be."
                ),
            ),
            Concept(
                keyword="scale",
                finding=(
                    "You played with scale, one of the simplest ways to open up a "
                    "new design idea."
                ),
            ),
            Concept(
                keyword="shape",
                finding=(
                    "You used the object's shape as the starting point of your design."
                ),
            ),
            Concept(
                keyword="purpose",
                finding=(
                    "You explained the design's purpose, which makes the concept "
                    "convincing."
                ),
            ),
            Concept(
                keyword="handle",
                finding=(
                    "You kept the handle in your design, a feature worth holding onto."
                ),
            ),
            Concept(
                keyword="light",
                finding=(
                    "You considered how light works in your design, which gives it "
                    "depth."
                ),
            ),
            Concept(
                keyword="texture",
                finding=(
                    "You carried the object's texture into your design, which keeps "
                    "it grounded."
                ),
            ),
            Concept(
                keyword="user",
                finding=(
                    "You thought about the person using the design, which is at the "
                    "centre of design thinking."
                ),
            ),
        ),
        fallback_image=OBJECT_TRANSFORM_IMAGE,
        fallback_alt="An everyday object drawn as a simple form for transformation.",
    ),
    DemoActivityDefinition(
        title="Composition Detective — What Holds This Together?",
        description="Find the structure inside an arrangement of shapes.",
        activity_type=ActivityType.OBSERVATION,
        prompt=(
            "Look at the arrangement in the image. Identify what holds the "
            "composition together — where your eye goes first, and what keeps it "
            "moving."
        ),
        skill_names=("Visual Analysis", "Critical Observation"),
        strength="You identified where the composition directs your attention.",
        improvement=(
            "You named compositional devices; explain how two of them work together."
        ),
        next_step=(
            "Describe one change to the arrangement that would make the composition "
            "calmer."
        ),
        primary_capability=PRACTICE_CAPABILITY_OBSERVE,
        secondary_capabilities=(PRACTICE_CAPABILITY_INTERPRET,),
        stimulus_context=ActivityStimulusContext(
            learning_focus="Composition",
            stimulus_context="Abstract still-life arrangements",
            retrieval_query="abstract geometric still life arrangement",
        ),
        concepts=(
            Concept(
                keyword="focal point",
                finding=(
                    "You identified the focal point, which explains where the eye "
                    "lands first."
                ),
            ),
            Concept(
                keyword="balance",
                finding=(
                    "You noticed how the arrangement is balanced, which gives it "
                    "stability."
                ),
            ),
            Concept(
                keyword="symmetry",
                finding=(
                    "You noticed the symmetry in the arrangement, which creates a "
                    "sense of order."
                ),
            ),
            Concept(
                keyword="asymmetry",
                finding=(
                    "You noticed the asymmetry, which gives the arrangement its "
                    "tension."
                ),
            ),
            Concept(
                keyword="diagonal",
                finding=(
                    "You noticed the diagonals, which set the arrangement's "
                    "direction of movement."
                ),
            ),
            Concept(
                keyword="repetition",
                finding=(
                    "You noticed the repetition of shapes, which gives the "
                    "composition its rhythm."
                ),
            ),
            Concept(
                keyword="negative space",
                finding=(
                    "You noticed the negative space, which shapes the arrangement "
                    "as much as the forms do."
                ),
            ),
            Concept(
                keyword="empty space",
                finding=(
                    "You noticed the empty space, which shapes the arrangement as "
                    "much as the forms do."
                ),
            ),
            Concept(
                keyword="leading lines",
                finding=(
                    "You noticed how lines lead your eye through the arrangement."
                ),
            ),
            Concept(
                keyword="light",
                finding=(
                    "You noticed how light separates the shapes and guides your eye."
                ),
            ),
            Concept(
                keyword="shadow",
                finding=("You noticed the shadows, which anchor the shapes in space."),
            ),
            Concept(
                keyword="depth",
                finding=(
                    "You noticed how the arrangement reads as depth, not just pattern."
                ),
            ),
            Concept(
                keyword="contrast",
                finding=(
                    "You noticed the contrast between the shapes, which creates "
                    "emphasis."
                ),
            ),
            Concept(
                keyword="foreground",
                finding=(
                    "You noticed the foreground shapes, which carry the "
                    "arrangement's weight."
                ),
            ),
            Concept(
                keyword="shape",
                finding=(
                    "You described the shapes themselves, which is where "
                    "composition analysis starts."
                ),
            ),
        ),
        fallback_image=COMPOSITION_DETECTIVE_IMAGE,
        fallback_alt=("An abstract arrangement of shapes for composition analysis."),
    ),
    DemoActivityDefinition(
        title="Design Articulation — Explain a Poster Concept",
        description="Practise explaining a design idea in convincing language.",
        activity_type=ActivityType.WRITTEN_RESPONSE,
        prompt=(
            "Imagine a poster for a cause you care about. Describe the poster — its "
            "image, its words, and its mood — and explain why each choice serves "
            "the cause."
        ),
        skill_names=("Written Communication",),
        strength="You communicated the poster concept in clear, confident language.",
        improvement=(
            "Your explanation states the choices but not the reasons; give the "
            "reasoning behind one visual choice."
        ),
        next_step=(
            "Rewrite one sentence so it links a design choice directly to the cause."
        ),
        primary_capability=PRACTICE_CAPABILITY_ARTICULATE,
        secondary_capabilities=(PRACTICE_CAPABILITY_IDEATE,),
    ),
    DemoActivityDefinition(
        title="Reflection Prompt — What Did Practice Ask of You?",
        description="A short reflective pause after practice.",
        activity_type=ActivityType.REFLECTION,
        prompt=(
            "Think about the last practice activity you completed. What kind of "
            "thinking did it ask of you, and what would make your next attempt "
            "stronger?"
        ),
        skill_names=("Critical Observation",),
        strength="You looked honestly at what the practice demanded of you.",
        improvement=(
            "Your reflection stays general; name the specific moment that was hardest."
        ),
        next_step=(
            "Write one sentence you would want to read before your next attempt."
        ),
        primary_capability=PRACTICE_CAPABILITY_REFLECT,
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
            primary_capability=definition.primary_capability,
            secondary_capabilities=definition.secondary_capabilities,
        )
        for position, definition in enumerate(_DEMO_ACTIVITIES)
    )


def build_demo_activity_map(
    activities: tuple[DemoActivity, ...],
) -> dict[UUID, DemoActivity]:
    """Map each demo activity identity to its demo activity content."""
    return {item.activity.id: item for item in activities}
