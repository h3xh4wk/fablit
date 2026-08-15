"""Application use cases for the learner practice flow (SPEC-012).

This module implements UC-001 through UC-007 from SPEC-012 by composing the
existing learning-domain models. It contains no HTML and no presentation
logic: learner-facing view models (``view_models.py``) are prepared here and
rendered by the Web/UI layer.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from fablit.domain import Evaluation, Feedback, Reflection, Submission

from .demo_data import REFLECTION_PROMPT
from .demo_evaluator import DemoEvaluator
from .errors import (
    CompletionNotFoundError,
    InvalidPracticeResponseError,
    InvalidReflectionResponseError,
)
from .store import DemoActivity, LearnerJourneyStore
from .view_models import (
    CompletionView,
    FeedbackView,
    PracticeActivitySummary,
    PracticeActivityView,
    PracticeDashboardView,
    ReflectionView,
)


def _now() -> datetime:
    return datetime.now(UTC)


class PracticeApplication:
    """Application-layer orchestration for the learner practice flow.

    The facade the Web/UI layer uses to drive the learner journey. Each
    method maps to a SPEC-012 use case and returns a learner-facing view
    model, never a domain object.
    """

    def __init__(
        self,
        *,
        store: LearnerJourneyStore,
        evaluator: DemoEvaluator,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._evaluator = evaluator
        self._clock = clock or _now

    # UC-001 — Get Practice Dashboard
    def get_dashboard(self) -> PracticeDashboardView:
        """Return the available practice activities for the dashboard."""
        summaries = tuple(
            PracticeActivitySummary(
                id=item.activity.id,
                title=item.title,
                description=item.description,
                skills=self._skill_names(item.activity.skill_ids),
            )
            for item in self._store.list_activities()
        )
        return PracticeDashboardView(activities=summaries)

    # UC-002 — Start Practice Activity
    def start_practice(self, activity_id: UUID) -> PracticeActivityView:
        """Prepare an activity for learner practice."""
        item = self._store.get_activity(activity_id)
        return PracticeActivityView(
            id=item.activity.id,
            title=item.title,
            description=item.description,
            skills=self._skill_names(item.activity.skill_ids),
            prompt=item.activity.instructions,
        )

    # UC-003/004/005 — Submit Response + Demo Evaluation + Feedback
    def submit_response(self, activity_id: UUID, response: str) -> FeedbackView:
        """Accept a learner response, create the journey records, and prepare feedback.

        Creates a Submitted Submission through the existing domain model,
        evaluates it with the deterministic demo evaluator, creates the
        corresponding Feedback, and marks it as the feedback currently shown
        to the learner.
        """
        item = self._store.get_activity(activity_id)
        if not isinstance(response, str) or not response.strip():
            raise InvalidPracticeResponseError(
                "Please enter a response before submitting."
            )
        submitted = Submission(
            learner_id=self._store.learner_id,
            activity_id=activity_id,
            response=response,
        ).submit(submitted_at=self._clock())
        evaluation = self._evaluator.evaluate(submitted, evaluated_at=self._clock())
        feedback = Feedback(
            evaluation_id=evaluation.id,
            content=self._feedback_content(evaluation),
            created_at=self._clock(),
        )
        self._store.save_submission(submitted)
        self._store.save_evaluation(evaluation)
        self._store.save_feedback(feedback)
        self._store.set_current_feedback(feedback.id)
        return self._feedback_view(item, feedback)

    # UC-005 — Present Feedback
    def get_feedback(self) -> FeedbackView:
        """Return the feedback currently being shown to the learner."""
        feedback = self._store.current_feedback()
        item = self._activity_for_feedback(feedback)
        return self._feedback_view(item, feedback)

    # UC-006 — Start Reflection
    def get_reflection(self) -> ReflectionView:
        """Return the purposeful reflection prompt with feedback context."""
        feedback = self._store.current_feedback()
        item = self._activity_for_feedback(feedback)
        return ReflectionView(
            activity_title=item.title,
            prompt=REFLECTION_PROMPT,
            context=feedback.content,
        )

    # UC-007 — Submit Reflection
    def submit_reflection(self, content: str) -> CompletionView:
        """Save the learner's Reflection and return the completion result."""
        feedback = self._store.current_feedback()
        if not isinstance(content, str) or not content.strip():
            raise InvalidReflectionResponseError(
                "Please enter a reflection before saving."
            )
        reflection = Reflection(
            feedback_id=feedback.id,
            content=content,
            created_at=self._clock(),
        )
        self._store.save_reflection(reflection)
        return self._completion_view()

    def get_completion(self) -> CompletionView:
        """Return the completion confirmation once a Reflection has been saved."""
        if self._store.last_reflection() is None:
            raise CompletionNotFoundError("No completed practice yet.")
        return self._completion_view()

    def _completion_view(self) -> CompletionView:
        return CompletionView(
            message=(
                "You have completed this practice. Your reflection has been recorded."
            )
        )

    def _skill_names(self, skill_ids: tuple[UUID, ...]) -> tuple[str, ...]:
        return tuple(self._store.get_skill(skill_id).name for skill_id in skill_ids)

    def _activity_for_feedback(self, feedback: Feedback) -> DemoActivity:
        """Walk the journey chain back to the activity for a Feedback record."""
        evaluation = self._store.get_evaluation(feedback.evaluation_id)
        submission = self._store.get_submission(evaluation.submission_id)
        return self._store.get_activity(submission.activity_id)

    def _feedback_content(self, evaluation: Evaluation) -> str:
        strengths, improvements, next_steps = self._categorise(evaluation)
        return "\n".join(
            (
                f"Strengths: {' '.join(strengths)}",
                f"Improvement: {' '.join(improvements)}",
                f"Next step: {' '.join(next_steps)}",
            )
        )

    def _feedback_view(self, item: DemoActivity, feedback: Feedback) -> FeedbackView:
        evaluation = self._store.get_evaluation(feedback.evaluation_id)
        strengths, improvements, next_steps = self._categorise(evaluation)
        return FeedbackView(
            activity_title=item.title,
            strengths=strengths,
            improvements=improvements,
            next_steps=next_steps,
            reflection_prompt=REFLECTION_PROMPT,
        )

    def _categorise(
        self,
        evaluation: Evaluation,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        """Split findings into strengths, improvements, and next steps.

        The demo evaluator emits exactly three Findings per activity in a
        fixed order (strength, improvement, next step); this categorisation
        relies on that order. A future evaluator with a richer Finding
        structure can replace it without changing the learner-facing view.
        """
        observations = tuple(finding.observation for finding in evaluation.findings)
        return observations[:1], observations[1:2], observations[2:3]
