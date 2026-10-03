"""In-memory journey store for the learner practice vertical slice.

SPEC-012 §28: the repository has no persistence layer yet, so the vertical
slice preserves the learner journey in memory. This store keeps the seeded
demo content and the records produced along the journey (Stimulus Instance,
Submission, Evaluation, Feedback, Reflection, Practice Completion) so the
flow can be demonstrated and tested end to end. It is intentionally minimal
and structured so a real repository can replace it later without redesigning
the application layer.

SPEC-015 §16/§18: a resolved Stimulus Instance is retained with the activity
instance so the learner's completed activity stays associated with the exact
stimulus that was shown; the store never silently replaces it (§48).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fablit.domain import (
    ActivityStimulusContext,
    AssessmentActivity,
    Evaluation,
    Feedback,
    Reflection,
    Skill,
    StimulusInstance,
    Submission,
)

from .artifacts import SketchbookArtifact
from .errors import (
    ActivityNotFoundError,
    FeedbackNotFoundError,
    InvalidContentContractError,
    JourneyStateError,
)


@dataclass(frozen=True)
class Concept:
    """A concept the response-aware demo evaluator can recognise in a response.

    SPEC-015 §29–31: a Finding must be grounded in the learner's actual
    response. Each concept pairs a keyword the evaluator can match in the
    response text with the Finding that observation produces, and the
    matched keyword is retained as the Finding's evidence.
    """

    keyword: str
    finding: str


@dataclass(frozen=True)
class PracticeContentContract:
    """Explicit content metadata that defines what makes a practice a Fablit practice.

    The structure follows SPEC-029's minimum educational contract: purpose,
    task, expected thinking, response requirements, and evaluation/feedback/
    reflection/continuation intent. This metadata remains application-level
    content configuration and never becomes a learner-progress model.

    Every curated practice authors its contract explicitly in its own
    definition (SPEC-029 §4, issue #111): the fields must capture that
    practice's educational intent, not a template derived from the activity's
    title, description, or prompt. :meth:`from_activity` survives only as a
    generic fallback for definitions that author no contract; tests guard
    that its text never stands in for a curated practice's contract.
    """

    purpose: str
    task: str
    expected_thinking: str
    response_contract: str
    evaluation_intent: str
    feedback_intent: str
    reflection_intent: str
    continuation_intent: str

    def __post_init__(self) -> None:
        """Reject blank fields — an incomplete contract is not a contract."""
        for spec in dataclasses.fields(self):
            value = getattr(self, spec.name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidContentContractError(
                    f"practice content contract field {spec.name!r} must be "
                    f"non-blank text, got {value!r}"
                )

    @classmethod
    def from_activity(
        cls,
        *,
        title: str,
        description: str,
        prompt: str,
        primary_capability: str,
    ) -> PracticeContentContract:
        """Derive a generic content contract from the activity's own content.

        Fallback only (SPEC-029 §4, issue #111): curated practices author
        their contract so it captures that practice's own thinking demand.
        The text produced here is deliberately generic, and tests assert it
        never becomes the contract of a curated practice.
        """
        capability = primary_capability.lower()
        if description.strip():
            purpose = (
                f"Use the {capability} lens to {description.lower()}."
                if capability
                else description.strip()
            )
        else:
            purpose = (
                f"Exercise {capability} thinking through the activity."
                if capability
                else "Exercise deliberate creative thinking through the activity."
            )
        task = prompt.strip() or title.strip()
        expected_thinking = (
            "The learner moves from concrete evidence to a reasoned response, "
            "rather than relying on vague generalisation or unsupported claims."
        )
        response_contract = (
            "Answer with a focused, evidence-based response that matches the task "
            "without unnecessary format overhead or padding."
        )
        evaluation_intent = (
            "A useful evaluation looks for specificity, direct evidence, and clear "
            f"use of the {capability} thinking demanded by the task."
        )
        feedback_intent = (
            "Feedback should name a concrete strength, explain why it matters, "
            "and point to one useful next move."
        )
        reflection_intent = (
            "Reflection should help the learner notice how the attempt was made and "
            "what would change in a future attempt."
        )
        continuation_intent = (
            "Continue with a related practice that extends the same thinking move or "
            "uses a meaningful next step rather than a superficial repeat."
        )
        return cls(
            purpose=purpose,
            task=task,
            expected_thinking=expected_thinking,
            response_contract=response_contract,
            evaluation_intent=evaluation_intent,
            feedback_intent=feedback_intent,
            reflection_intent=reflection_intent,
            continuation_intent=continuation_intent,
        )


@dataclass(frozen=True)
class DemoActivity:
    """A seeded demo practice activity plus its learner-facing content.

    ``primary_capability`` and ``secondary_capabilities`` are internal
    content-design metadata (SPEC-023 §5): a review lens over the library,
    never learner-facing copy and never a selection or ordering signal.

    ``content_contract`` is the practice's authored SPEC-029 content
    contract (issue #111); see :attr:`contract` for the fallback rule.
    """

    activity: AssessmentActivity
    title: str
    description: str
    strength: str
    improvement: str
    next_step: str
    #: The practice's authored SPEC-029 content contract (issue #111).
    #: ``None`` only for definitions that author none; the generic
    #: :meth:`PracticeContentContract.from_activity` derivation then serves
    #: as the documented fallback. An authored contract is never overwritten.
    content_contract: PracticeContentContract | None = None
    primary_capability: str = ""
    concepts: tuple[Concept, ...] = ()
    fallback_image: str | None = None
    fallback_alt: str | None = None
    secondary_capabilities: tuple[str, ...] = ()

    @property
    def contract(self) -> PracticeContentContract:
        """This practice's SPEC-029 content contract, authored or derived.

        Curated practices author their contract in their definition; the
        generic derivation is consulted only when none was supplied.
        """
        if self.content_contract is not None:
            return self.content_contract
        return PracticeContentContract.from_activity(
            title=self.title,
            description=self.description,
            prompt=self.activity.instructions,
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

    @property
    def stimulus_context(self) -> ActivityStimulusContext | None:
        """The activity's contextual visual stimulus requirements (SPEC-015 §6)."""
        return self.activity.stimulus_context


@dataclass(frozen=True)
class PracticeCompletion:
    """A completed learner practice journey (SPEC-018).

    Completion deliberately records only the learner, activity, reflection,
    and time. It conveys continuity without inferring achievement or mastery.

    SPEC-026: ``reflection_id`` is ``None`` when the learner skipped the
    optional post-practice reflection (§2.2): the practice is still complete
    — skipping must never block completion or history recording in the
    journey store (§2.2 acceptance criteria).

    SPEC-033: a sketchbook reflection may include a private learner-owned
    artifact associated with the completed practice record.
    """

    learner_id: UUID
    activity_id: UUID
    reflection_id: UUID | None
    completed_at: datetime
    artifact: SketchbookArtifact | None = None


class LearnerJourneyStore:
    """In-memory store for the demo learner's practice journey."""

    def __init__(
        self,
        *,
        learner_id: UUID,
        activities: tuple[DemoActivity, ...],
        skills: tuple[Skill, ...],
    ) -> None:
        self._learner_id = learner_id
        self._activities: dict[UUID, DemoActivity] = {
            item.activity.id: item for item in activities
        }
        self._skills: dict[UUID, Skill] = {skill.id: skill for skill in skills}
        self._stimuli: dict[UUID, StimulusInstance] = {}
        self._submissions: dict[UUID, Submission] = {}
        self._evaluations: dict[UUID, Evaluation] = {}
        self._feedback: dict[UUID, Feedback] = {}
        self._reflections: dict[UUID, Reflection] = {}
        self._completions: list[PracticeCompletion] = []
        self._pending_artifacts: dict[UUID, SketchbookArtifact] = {}
        # SPEC-026 §2.1: the learner's optional pre-practice intention for the
        # current activity instance. Pending journey state only: it is captured
        # into the journey at submission (retry-safe) and never blocks practice.
        self._pending_intention: str | None = None
        self._pending_intention_activity_id: UUID | None = None
        self._current_stimulus_id: UUID | None = None
        self._current_stimulus_activity_id: UUID | None = None
        self._current_feedback_id: UUID | None = None
        self._last_reflection_id: UUID | None = None

    @property
    def learner_id(self) -> UUID:
        """The identity of the demo learner driving the vertical slice."""
        return self._learner_id

    def list_activities(self) -> tuple[DemoActivity, ...]:
        """Return the seeded demo activities in deterministic order."""
        return tuple(
            sorted(self._activities.values(), key=lambda item: item.activity.position)
        )

    def get_activity(self, activity_id: UUID) -> DemoActivity:
        """Return a demo activity by identity, raising when unknown."""
        try:
            return self._activities[activity_id]
        except KeyError:
            raise ActivityNotFoundError("Activity not found.") from None

    def get_skill(self, skill_id: UUID) -> Skill:
        """Return a seeded demo skill by identity."""
        try:
            return self._skills[skill_id]
        except KeyError:
            raise JourneyStateError(
                "skill reference is not part of the demo content"
            ) from None

    def save_stimulus(self, stimulus: StimulusInstance) -> None:
        self._stimuli[stimulus.id] = stimulus

    # SPEC-026 §2.1 — pending pre-practice intention

    def set_pending_intention(self, activity_id: UUID, intention: str) -> None:
        """Record the learner's pre-practice intention for an activity.

        The intention is held as pending journey state until the learner
        submits a response for that activity, at which point the application
        captures it into the journey (``take_intention``). Setting an
        intention for a different activity replaces the pending one — the
        learner practises one activity at a time.
        """
        self._pending_intention = intention
        self._pending_intention_activity_id = activity_id

    def pending_intention(self, activity_id: UUID) -> str | None:
        """Return the pending intention for an activity without consuming it.

        Used to echo the captured focus back in the active workspace
        (SPEC-026 §2.1) while the learner works on the activity.
        """
        if self._pending_intention_activity_id != activity_id:
            return None
        return self._pending_intention

    def take_intention(self, activity_id: UUID) -> str | None:
        """Consume the pending intention when it matches the given activity.

        Called when a response is submitted for ``activity_id``. A pending
        intention for a different activity (for example an abandoned
        intention) is left untouched so it cannot leak into another
        activity's journey.
        """
        if self._pending_intention_activity_id != activity_id:
            return None
        intention = self._pending_intention
        self._pending_intention = None
        self._pending_intention_activity_id = None
        return intention

    def set_current_stimulus(self, stimulus: StimulusInstance) -> None:
        """Record a stimulus as the current one for its activity instance."""
        self._stimuli[stimulus.id] = stimulus
        self._current_stimulus_id = stimulus.id
        self._current_stimulus_activity_id = stimulus.activity_id

    def current_stimulus(self, activity_id: UUID) -> StimulusInstance | None:
        """Return the stimulus resolved for the current practice of an activity.

        The same resolved stimulus is reused while the learner is working on
        an activity instance (SPEC-015 §19); a new stimulus is resolved when
        the learner starts a different activity instance.
        """
        if self._current_stimulus_id is None:
            return None
        if self._current_stimulus_activity_id != activity_id:
            return None
        return self._stimuli.get(self._current_stimulus_id)

    def get_stimulus(self, stimulus_id: UUID) -> StimulusInstance:
        """Return a recorded Stimulus Instance by identity."""
        try:
            return self._stimuli[stimulus_id]
        except KeyError:
            raise JourneyStateError(
                "stimulus is not part of the current journey"
            ) from None

    def save_submission(
        self, submission: Submission, *, intention: str | None = None
    ) -> None:
        """Record a Submission, attaching the session's intention (SPEC-026).

        The Submission domain model is immutable, so the captured
        pre-practice intention is attached by composing a new Submission
        instance with the same identity: journey records keep the response
        and its session context together for later review (§2.1, §2.3).
        """
        if intention is not None:
            submission = dataclasses.replace(
                submission, pre_practice_intention=intention
            )
        self._submissions[submission.id] = submission

    def save_evaluation(self, evaluation: Evaluation) -> None:
        self._evaluations[evaluation.id] = evaluation

    def save_feedback(self, feedback: Feedback) -> None:
        self._feedback[feedback.id] = feedback

    def save_reflection(self, reflection: Reflection) -> None:
        self._reflections[reflection.id] = reflection
        self._last_reflection_id = reflection.id

    def save_pending_artifact(
        self, activity_id: UUID, artifact: SketchbookArtifact
    ) -> None:
        """Hold a private sketchbook artifact while the activity is submitted."""
        self._pending_artifacts[activity_id] = artifact

    def take_pending_artifact(self, activity_id: UUID) -> SketchbookArtifact | None:
        """Consume the private sketchbook artifact for this activity."""
        artifact = self._pending_artifacts.pop(activity_id, None)
        if artifact is not None and artifact.learner_id != self._learner_id:
            return None
        return artifact

    def save_completion(self, completion: PracticeCompletion) -> None:
        """Record a completed practice journey without collapsing repeats."""
        self._completions.append(completion)

    def has_completed_activity(self, activity_id: UUID) -> bool:
        """Whether the demo learner has completed this activity before."""
        return any(
            completion.learner_id == self._learner_id
            and completion.activity_id == activity_id
            for completion in self._completions
        )

    def get_submission(self, submission_id: UUID) -> Submission:
        """Return a recorded Submission by identity."""
        try:
            return self._submissions[submission_id]
        except KeyError:
            raise JourneyStateError(
                "submission is not part of the current journey"
            ) from None

    def get_evaluation(self, evaluation_id: UUID) -> Evaluation:
        """Return a recorded Evaluation by identity."""
        try:
            return self._evaluations[evaluation_id]
        except KeyError:
            raise JourneyStateError(
                "evaluation is not part of the current journey"
            ) from None

    def get_feedback(self, feedback_id: UUID) -> Feedback:
        """Return a recorded Feedback by identity."""
        try:
            return self._feedback[feedback_id]
        except KeyError:
            raise FeedbackNotFoundError("Feedback not found.") from None

    def current_feedback(self) -> Feedback:
        """Return the feedback currently shown to the learner."""
        if self._current_feedback_id is None:
            raise FeedbackNotFoundError("Feedback not found.")
        try:
            return self._feedback[self._current_feedback_id]
        except KeyError:
            raise FeedbackNotFoundError("Feedback not found.") from None

    def set_current_feedback(self, feedback_id: UUID) -> None:
        self._current_feedback_id = feedback_id

    def last_reflection(self) -> Reflection | None:
        """Return the most recently saved Reflection, if any."""
        if self._last_reflection_id is None:
            return None
        return self._reflections[self._last_reflection_id]

    def activity_stimuli(self, activity_id: UUID) -> tuple[StimulusInstance, ...]:
        """Return all stimuli resolved for a specific activity instance.

        SPEC-015 §53/§68: a completed activity must provide enough
        information to determine which stimulus was shown. This method
        returns every stimulus ever resolved for the given activity so
        developers can trace the exact stimulus associated with any
        historical learner activity instance.
        """
        return tuple(
            stimulus
            for stimulus in self._stimuli.values()
            if stimulus.activity_id == activity_id
        )

    def recorded_stimuli(self) -> tuple[StimulusInstance, ...]:
        return tuple(self._stimuli.values())

    def recorded_submissions(self) -> tuple[Submission, ...]:
        return tuple(self._submissions.values())

    def recorded_evaluations(self) -> tuple[Evaluation, ...]:
        return tuple(self._evaluations.values())

    def recorded_feedback(self) -> tuple[Feedback, ...]:
        return tuple(self._feedback.values())

    def recorded_reflections(self) -> tuple[Reflection, ...]:
        return tuple(self._reflections.values())

    def recorded_completions(self) -> tuple[PracticeCompletion, ...]:
        """Return each completion event, including repeated activity practice."""
        return tuple(self._completions)
