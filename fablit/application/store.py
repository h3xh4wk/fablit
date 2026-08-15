"""In-memory journey store for the learner practice vertical slice (SPEC-012).

SPEC-012 §28: the repository has no persistence layer yet, so the vertical
slice preserves the learner journey in memory. This store keeps the seeded
demo content and the records produced along the journey (Submission,
Evaluation, Feedback, Reflection) so the flow can be demonstrated and tested
end to end. It is intentionally minimal and structured so a real repository
can replace it later without redesigning the application layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fablit.domain import (
    AssessmentActivity,
    Evaluation,
    Feedback,
    Reflection,
    Skill,
    Submission,
)

from .errors import ActivityNotFoundError, FeedbackNotFoundError, JourneyStateError


@dataclass(frozen=True)
class DemoActivity:
    """A seeded demo practice activity plus its learner-facing content."""

    activity: AssessmentActivity
    title: str
    description: str
    strength: str
    improvement: str
    next_step: str


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
        self._submissions: dict[UUID, Submission] = {}
        self._evaluations: dict[UUID, Evaluation] = {}
        self._feedback: dict[UUID, Feedback] = {}
        self._reflections: dict[UUID, Reflection] = {}
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

    def save_submission(self, submission: Submission) -> None:
        self._submissions[submission.id] = submission

    def save_evaluation(self, evaluation: Evaluation) -> None:
        self._evaluations[evaluation.id] = evaluation

    def save_feedback(self, feedback: Feedback) -> None:
        self._feedback[feedback.id] = feedback

    def save_reflection(self, reflection: Reflection) -> None:
        self._reflections[reflection.id] = reflection
        self._last_reflection_id = reflection.id

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

    def recorded_submissions(self) -> tuple[Submission, ...]:
        return tuple(self._submissions.values())

    def recorded_evaluations(self) -> tuple[Evaluation, ...]:
        return tuple(self._evaluations.values())

    def recorded_feedback(self) -> tuple[Feedback, ...]:
        return tuple(self._feedback.values())

    def recorded_reflections(self) -> tuple[Reflection, ...]:
        return tuple(self._reflections.values())
