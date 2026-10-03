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

from .store import Concept, DemoActivity, PracticeContentContract

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

#: Learner-facing copy for the optional pre-practice intention prompt
#: (SPEC-026 §2.1). The intention is an invitation, never a gate: skipping
#: always leads straight into the unchanged practice journey.
INTENTION_PROMPT = (
    "Before you begin, is there a specific focus you'd like to hold for "
    "this practice? (For example: focus on explicit naming, or check "
    "boundary cases before submitting.)"
)
INTENTION_HEADING = "Set an intention"
INTENTION_ACTION_LABEL = "Continue with intention"
INTENTION_SKIP_LABEL = "Skip — go straight to practice"

#: Learner-facing copy for the optional post-evaluation reflection prompts
#: (SPEC-026 §2.2). Both prompts are optional and purely qualitative: the
#: system never grades, evaluates, or critiques what the learner writes.
STRATEGY_ASSESSMENT_PROMPT = (
    "What strategy or mental model did you use to complete this activity?"
)
GAP_ANALYSIS_PROMPT = (
    "What was the primary friction point or misconception you encountered?"
)
REFLECTION_HEADING = "A moment to reflect"
REFLECTION_SAVE_LABEL = "Save reflection"
REFLECTION_SKIP_LABEL = "Skip reflection"

#: The structured post-practice reflection prompts, in presentation order.
#: SPEC-026 composes the single purposeful SPEC-012 reflection prompt with
#: the two qualitative SPEC-026 prompts on the same panel.
POST_EVALUATION_PROMPTS: tuple[str, ...] = (
    STRATEGY_ASSESSMENT_PROMPT,
    GAP_ANALYSIS_PROMPT,
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
    "Sketchbook Reflection — Notice What Your Work Taught You",
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
    #: The practice's authored SPEC-029 content contract (issue #111).
    #: Curated practices author all eight fields against their own task,
    #: thinking demand, and intents; ``None`` only for ad-hoc definitions,
    #: which fall back to the generic derivation (see :attr:`contract`).
    content_contract: PracticeContentContract | None = None
    #: The activity's primary practice capability (SPEC-023 §5, AC-023-03):
    #: an internal content-design label, never learner-facing.
    primary_capability: str = ""
    stimulus_context: ActivityStimulusContext | None = None
    concepts: tuple[Concept, ...] = ()
    fallback_image: str | None = None
    fallback_alt: str | None = None
    #: Capabilities the activity genuinely exercises beyond its primary one
    #: (SPEC-023 §5); empty when the activity is single-focused.
    secondary_capabilities: tuple[str, ...] = ()

    @property
    def contract(self) -> PracticeContentContract:
        """This practice's SPEC-029 content contract, authored or derived.

        The authored contract is returned untouched — generic derivation
        never overwrites practice-specific intent (issue #111). Only a
        definition that supplies no contract receives the fallback.
        """
        if self.content_contract is not None:
            return self.content_contract
        return PracticeContentContract.from_activity(
            title=self.title,
            description=self.description,
            prompt=self.prompt,
            primary_capability=self.primary_capability,
        )

    @property
    def purpose(self) -> str:
        return self.contract.purpose

    @property
    def task(self) -> str:
        return self.contract.task

    @property
    def expected_thinking(self) -> str:
        return self.contract.expected_thinking

    @property
    def response_contract(self) -> str:
        return self.contract.response_contract

    @property
    def evaluation_intent(self) -> str:
        return self.contract.evaluation_intent

    @property
    def feedback_intent(self) -> str:
        return self.contract.feedback_intent

    @property
    def reflection_intent(self) -> str:
        return self.contract.reflection_intent

    @property
    def continuation_intent(self) -> str:
        return self.contract.continuation_intent


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
        content_contract=PracticeContentContract(
            purpose=(
                "Examine how the dominant visual elements of a photograph's "
                "composition work together, and explain their combined effect "
                "on where the viewer's attention goes."
            ),
            task=(
                "Analyse the provided photograph: identify its dominant visual "
                "elements and explain how they work together to hold the "
                "composition."
            ),
            expected_thinking=(
                "The learner moves from naming visible elements to explaining "
                "the relationships between them — an element is tied to how it "
                "directs attention or anchors the composition, not listed in "
                "isolation."
            ),
            response_contract=(
                "A short analytical written response: a paragraph or two that "
                "names the main elements and explains at least one relationship "
                "between them. No structure beyond clear sentences; a list of "
                "elements with no relationships does not answer the task."
            ),
            evaluation_intent=(
                "Look for specific visual elements named as evidence, at least "
                "one explained relationship between them, and claims that stay "
                "inside what the photograph actually shows."
            ),
            feedback_intent=(
                "Feedback should take one composition relationship the learner "
                "actually described, explain how it shapes where the eye goes, "
                "and point to one further relationship worth examining."
            ),
            reflection_intent=(
                "Invite the learner to notice which element they treated as the "
                "anchor of the composition, and what made it read that way."
            ),
            continuation_intent=(
                "A natural next step is reading a whole scene for what might be "
                "happening — moving from how a composition works to what a "
                "composition is telling the viewer."
            ),
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
        strength=(
            "Your explanation gives the idea a clear structure and keeps the reader "
            "oriented to the central point."
        ),
        primary_capability=PRACTICE_CAPABILITY_ARTICULATE,
        improvement=(
            "The idea is clear, but the explanation could anchor it in one concrete "
            "example or comparison."
        ),
        next_step=(
            "Rewrite one sentence so the idea is tied to a visible example that a "
            "reader can picture."
        ),
        content_contract=PracticeContentContract(
            purpose=(
                "Practise explaining a complex idea in plain language so a "
                "newcomer can follow it — choosing structure and a concrete "
                "anchor over jargon or compressed summary."
            ),
            task=(
                "Explain a complex idea clearly enough that a reader who has "
                "never encountered it can follow it from the words alone."
            ),
            expected_thinking=(
                "The learner breaks the idea into a shape a reader can follow — "
                "what it is, why it matters, one concrete anchor — rather than "
                "compressing everything into an abstract summary."
            ),
            response_contract=(
                "A short explanatory piece — a few sentences to a short "
                "paragraph — that stands on its own for a reader who does not "
                "already know the idea. Clarity and one worked example matter "
                "more than covering every facet."
            ),
            evaluation_intent=(
                "Look for a clear central point, plain language throughout, and "
                "at least one concrete example or comparison the reader can "
                "picture."
            ),
            feedback_intent=(
                "Feedback should name where the explanation became clear for a "
                "reader, where it leaned on abstraction, and one sentence worth "
                "grounding in an example."
            ),
            reflection_intent=(
                "Invite the learner to notice which part of the idea was hardest "
                "to say simply, and what that difficulty suggests about their "
                "own understanding of it."
            ),
            continuation_intent=(
                "A natural next step is explaining a design decision in "
                "convincing language — the same clarity put in service of a "
                "choice rather than only an idea."
            ),
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
        content_contract=PracticeContentContract(
            purpose=(
                "Practise noticing meaningful visual detail and stating what "
                "each detail suggests — the careful looking that drawing from "
                "observation depends on."
            ),
            task=(
                "Describe the key visual details you notice in the image, "
                "including what each one suggests about the subject."
            ),
            expected_thinking=(
                "The learner moves from the obvious to the specific: a small or "
                "overlooked detail is named first, then paired with a plausible "
                "reading of what it suggests, rather than restating the "
                "subject of the image."
            ),
            response_contract=(
                "A short observational response: several concrete details, "
                "each with a brief note on what it suggests. Detail before "
                "interpretation; covering the whole image is not required."
            ),
            evaluation_intent=(
                "Look for concreteness over general impression, variety across "
                "the image rather than one favoured area, and at least one "
                "detail paired with a plausible reading of it."
            ),
            feedback_intent=(
                "Feedback should pick out a detail the learner actually "
                "noticed, say what it opened up, and point to one overlooked "
                "region worth a closer look on the next attempt."
            ),
            reflection_intent=(
                "Invite the learner to notice which detail they reached for "
                "first, and which one only appeared after they slowed down."
            ),
            continuation_intent=(
                "A natural next step is turning one noticed detail into many "
                "possibilities — moving from detecting what is there to "
                "imagining what else it could become."
            ),
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
        strength=(
            "You identified a specific challenge and named the demand the practice "
            "made on you."
        ),
        primary_capability=PRACTICE_CAPABILITY_REFLECT,
        improvement=(
            "Your reflection names the challenge, but it could explain which part of "
            "the task created the friction."
        ),
        next_step=(
            "Write one sentence about the moment or detail that made the task feel "
            "hardest."
        ),
        content_contract=PracticeContentContract(
            purpose=(
                "Practise examining your own recent practice process — "
                "locating where difficulty actually came from instead of "
                "reporting it in general terms."
            ),
            task=(
                "Think about your most recent practice session, name what you "
                "found most challenging, and explain why it was hard."
            ),
            expected_thinking=(
                "The learner traces a stated difficulty back to a particular "
                "demand of the task — naming the moment and the friction, not "
                "only the general feeling of having found it difficult."
            ),
            response_contract=(
                "A concise reflective response: one challenge, one reason why. "
                "Primarily reflective in nature and written for yourself; "
                "defending or rating the work is not the task."
            ),
            evaluation_intent=(
                "Look for a concrete challenge connected to a specific part of "
                "the task, rather than a general statement about practice being "
                "hard in the abstract."
            ),
            feedback_intent=(
                "Feedback should mirror the learner's own words with "
                "specificity — one place the difficulty was pinned down, and "
                "one question that would make the account sharper."
            ),
            reflection_intent=(
                "Invite the learner to notice what describing the difficulty "
                "changed about it, and what they want to bring to the next "
                "session."
            ),
            continuation_intent=(
                "A natural next step is a focused observation drill: a bounded "
                "task where attention works on the material in front of you "
                "rather than on memory."
            ),
        ),
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
        content_contract=PracticeContentContract(
            purpose=(
                "Examine how specific colour relationships contribute to the "
                "mood of a visual composition, and how colour directs the "
                "viewer's attention through it."
            ),
            task=(
                "Analyse how colour contributes to the mood of the provided "
                "image, referring to specific colours and where they send the "
                "eye."
            ),
            expected_thinking=(
                "The learner names particular colours or tones and traces their "
                "effect on mood and attention — from what is visible to how it "
                "is experienced — rather than labelling the whole image warm "
                "or cool."
            ),
            response_contract=(
                "An interpretive written response of a short paragraph that "
                "anchors every claim about mood in a named colour; at least two "
                "distinct colours keep the analysis grounded."
            ),
            evaluation_intent=(
                "Look for specific colours cited as evidence, an explicit link "
                "from colour to felt mood, and — where present — how a colour "
                "guides the eye through the image."
            ),
            feedback_intent=(
                "Feedback should take one colour the learner read well, explain "
                "how that reading holds up against the image, and offer one "
                "further colour relationship to examine."
            ),
            reflection_intent=(
                "Invite the learner to notice which colour they responded to "
                "before analysing it, and whether the analysis changed their "
                "reading of the mood."
            ),
            continuation_intent=(
                "A natural next step is putting a design's colour and mood "
                "choices into words — moving from reading mood to "
                "deliberately setting it."
            ),
        ),
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
        content_contract=PracticeContentContract(
            purpose=(
                "Practise slow, deliberate looking at a single object — "
                "reading surface, edge, and wear as evidence of how the object "
                "has actually been used."
            ),
            task=(
                "Describe the object's surfaces, edges, and details, and say "
                "what the wear and material suggest about how it has been "
                "used."
            ),
            expected_thinking=(
                "The learner looks long enough for detail to become evidence: "
                "a scratch read as history, a finish read as material — each "
                "description moving from what is seen to what it suggests."
            ),
            response_contract=(
                "A short observational response built from concrete surface "
                "descriptions. A few specific details with their suggestions "
                "beat a complete survey of the object."
            ),
            evaluation_intent=(
                "Look for concrete surface detail, material and wear read as "
                "evidence of use, and at least one connection between two "
                "details — not merely an inventory of what the object has."
            ),
            feedback_intent=(
                "Feedback should name one detail described well and what it "
                "revealed, then point to one surface or edge passed over in the "
                "first pass."
            ),
            reflection_intent=(
                "Invite the learner to notice when naming became reading — the "
                "moment a detail started to suggest something — and how to "
                "reach that point sooner next time."
            ),
            continuation_intent=(
                "A natural next step is transforming the observed object into "
                "a design possibility — carrying what careful looking revealed "
                "into something new."
            ),
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
        content_contract=PracticeContentContract(
            purpose=(
                "Practise building a plausible reading of a busy scene from "
                "visual evidence, keeping interpretation accountable to what "
                "is actually visible."
            ),
            task=(
                "Read what might be happening in the street scene, supporting "
                "your reading with at least two specific visual details."
            ),
            expected_thinking=(
                "The learner forms a reading and then tests it against the "
                "image — choosing details that support the reading and dropping "
                "claims the scene does not show."
            ),
            response_contract=(
                "An interpretive written response: a short paragraph offering "
                "a possible reading, with at least two specific visual details "
                "cited as its support."
            ),
            evaluation_intent=(
                "Look for claims tied to visible details, at least two distinct "
                "pieces of evidence, and honest boundaries — reading that knows "
                "where the image stops supporting it."
            ),
            feedback_intent=(
                "Feedback should take the strongest evidence-and-reading pair, "
                "explain why it works, and challenge one claim that goes beyond "
                "what the scene shows."
            ),
            reflection_intent=(
                "Invite the learner to notice which detail their reading began "
                "from, and whether a different starting detail would have led "
                "to a different story."
            ),
            continuation_intent=(
                "A natural next step is an articulation practice: putting an "
                "evidenced reading into clear, justified language for someone "
                "else to follow."
            ),
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
        content_contract=PracticeContentContract(
            purpose=(
                "Practise generating a range of possibilities from an ordinary "
                "object quickly, then choosing one deliberately instead of "
                "settling on the first idea."
            ),
            task=(
                "List as many unusual uses as you can for an everyday object, "
                "then mark the one you would develop further."
            ),
            expected_thinking=(
                "The learner produces variety before judgement: uses that "
                "genuinely depart from the object's usual role come first, and "
                "the final choice is made on merit rather than by default."
            ),
            response_contract=(
                "A short generative list — each use a phrase or sentence — "
                "plus one marked choice. Range and distance from the usual "
                "role matter more than polish or completeness."
            ),
            evaluation_intent=(
                "Look for a real spread of different possibilities rather than "
                "variations on one, at least one use far from the object's "
                "usual function, and a chosen idea worth developing."
            ),
            feedback_intent=(
                "Feedback should contrast two of the learner's uses to show "
                "where the range is widest, and push the closest variation one "
                "step further from the usual role."
            ),
            reflection_intent=(
                "Invite the learner to notice which use they were tempted to "
                "stop at, and what made the chosen one worth developing."
            ),
            continuation_intent=(
                "A natural next step is putting one idea into clear, "
                "convincing language — moving from generating possibilities "
                "to articulating a single one."
            ),
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
        content_contract=PracticeContentContract(
            purpose=(
                "Practise transforming an observed object into a new design "
                "possibility, grounding the idea in what was actually seen "
                "rather than inventing in a vacuum."
            ),
            task=(
                "Transform the object in the image into something new, then "
                "describe the result and explain the reasoning behind it."
            ),
            expected_thinking=(
                "The learner works from observation to transformation: a real "
                "feature of the object is carried, changed, or deliberately "
                "dropped — and the choice is explained, not just presented."
            ),
            response_contract=(
                "A generative written response with an explanatory core: what "
                "the new design is, plus reasoning that connects it back to the "
                "object's actual form. Two well-developed ideas beat a long "
                "list."
            ),
            evaluation_intent=(
                "Look for a transformation grounded in observed features, an "
                "explanation that ties design choices to the source object, "
                "and awareness of form, material, or user."
            ),
            feedback_intent=(
                "Feedback should identify one design choice that clearly grows "
                "from observation, explain why that connection strengthens the "
                "concept, and name one feature left unexplained."
            ),
            reflection_intent=(
                "Invite the learner to notice which observed feature they could "
                "not let go of, and what keeping or changing it cost the "
                "design."
            ),
            continuation_intent=(
                "A natural next step is explaining the concept in convincing "
                "language — so someone else can see the design without seeing "
                "the object it came from."
            ),
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
        content_contract=PracticeContentContract(
            purpose=(
                "Practise finding the structure inside an arrangement — "
                "tracing where the eye lands first and what keeps it moving "
                "through the whole composition."
            ),
            task=(
                "Identify what holds the arrangement together: where your eye "
                "lands first, and what keeps it moving through the image."
            ),
            expected_thinking=(
                "The learner treats their own looking as evidence — recording "
                "the path the eye actually takes and naming the devices "
                "(balance, repetition, contrast) responsible for that path."
            ),
            response_contract=(
                "An observational response that traces movement through the "
                "arrangement: a first landing point, at least one device, and "
                "how they work together — not a glossary of devices."
            ),
            evaluation_intent=(
                "Look for attention traced rather than merely named: a claimed "
                "focal point, a described path, and an explicit link between "
                "two devices working together."
            ),
            feedback_intent=(
                "Feedback should confirm the path the learner described using "
                "the arrangement's own evidence, and offer one device they did "
                "not connect to it."
            ),
            reflection_intent=(
                "Invite the learner to notice whether their eye went where "
                "they expected, and what that says about how the arrangement "
                "holds together."
            ),
            continuation_intent=(
                "A natural next step is analysing a real photograph's "
                "composition — carrying the structural reading from an abstract "
                "arrangement into an image with a subject."
            ),
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
        content_contract=PracticeContentContract(
            purpose=(
                "Practise explaining design choices in convincing language — "
                "linking image, words, and mood to the cause each choice is "
                "meant to serve."
            ),
            task=(
                "Describe a poster for a cause you care about — its image, "
                "words, and mood — and explain why each choice serves that "
                "cause."
            ),
            expected_thinking=(
                "The learner moves from choice to reason: each visual or "
                "verbal decision is stated together with the argument for it, "
                "rather than described and left there."
            ),
            response_contract=(
                "A short explanatory response covering image, words, and mood, "
                "with the reasoning for at least one choice made explicit. "
                "Conviction matters more than covering every element."
            ),
            evaluation_intent=(
                "Look for choices paired with reasons, a connection back to the "
                "cause itself, and language vivid enough for a reader to "
                "picture the poster."
            ),
            feedback_intent=(
                "Feedback should take one choice the learner justified well, "
                "say why the reasoning holds, and press for the missing reason "
                "behind another choice."
            ),
            reflection_intent=(
                "Invite the learner to notice which choice came easiest to "
                "justify, and which one their reasoning was still circling "
                "without landing."
            ),
            continuation_intent=(
                "A natural next step is an ideation practice: generating "
                "several concepts first, so articulation has more than one "
                "idea to choose between."
            ),
        ),
        primary_capability=PRACTICE_CAPABILITY_ARTICULATE,
        secondary_capabilities=(PRACTICE_CAPABILITY_IDEATE,),
    ),
    DemoActivityDefinition(
        title="Sketchbook Reflection — Notice What Your Work Taught You",
        description=(
            "Bring something you already practised. Notice what your own work can "
            "teach you."
        ),
        activity_type=ActivityType.REFLECTION,
        prompt=(
            "Practised something in your sketchbook? Reflect on it. Describe one "
            "decision, observation, or challenge in your own work and what it "
            "taught you about your process."
        ),
        skill_names=("Critical Observation",),
        strength=(
            "You connected a concrete decision or observation in your work to "
            "what it taught you about your process."
        ),
        improvement=(
            "Your reflection could tie one observation or decision more directly "
            "to the evidence in the sketch or the problem you were solving."
        ),
        next_step=(
            "Write one sentence about what you would notice or change next time."
        ),
        content_contract=PracticeContentContract(
            purpose=(
                "Practise reading your own sketchbook work for what it reveals "
                "about your process — treating your own pages as material to "
                "observe, not to judge."
            ),
            task=(
                "Describe one decision, observation, or challenge in your own "
                "work, and what it taught you about how you work."
            ),
            expected_thinking=(
                "The learner moves from a concrete moment in their own work to "
                "a statement about how they work — a specific page, mark, or "
                "problem producing a genuine observation about process."
            ),
            response_contract=(
                "A concise reflective response: one moment from your own work "
                "and one thing it taught you. A sketchbook image may support "
                "it if you have one, but the written notice is the substance; "
                "rating the drawing is not the task."
            ),
            evaluation_intent=(
                "Look for a concrete anchor in the learner's own work and a "
                "genuine observation about process — never a verdict on the "
                "quality of the work itself."
            ),
            feedback_intent=(
                "Feedback should reflect one specific observation back to the "
                "learner, connect it to the work it came from, and pose one "
                "question that would extend it — never judge the artwork."
            ),
            reflection_intent=(
                "Invite the learner to notice what looking back at their own "
                "work changed: which assumption about their process the "
                "example confirmed or unsettled."
            ),
            continuation_intent=(
                "A natural next step is returning to slow, deliberate looking — "
                "taking the attention just used on your own work back to a "
                "single external object."
            ),
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
            content_contract=definition.content_contract,
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
