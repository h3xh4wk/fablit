"""Application use cases for the learner practice flow (SPEC-012…022).

This module implements UC-001 through UC-007 from SPEC-012 by composing the
existing learning-domain models, and adds the SPEC-015 stimulus flow: when an
activity defines a stimulus context, a stimulus is resolved at practice start
(UC-002) and passed to the evaluator at submission (UC-003/004). It contains
no HTML and no presentation logic: learner-facing view models
(``view_models.py``) are prepared here and rendered by the Web/UI layer.

SPEC-021 extends this with durable practice history and review: completed
practice is persisted through the PracticeHistoryRepository port, and the
learner can later retrieve and review specific completions.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Lock
from uuid import UUID

from fablit.application.persistence import PracticeHistoryRepository
from fablit.domain import (
    Evaluation,
    Feedback,
    Reflection,
    StimulusInstance,
    Submission,
)

from .demo_data import PRACTICE_MODE_CHOICE_QUESTION, REFLECTION_PROMPT
from .demo_evaluator import Evaluator
from .errors import (
    CompletionNotFoundError,
    EvaluationFailedError,
    InvalidPracticeResponseError,
    InvalidReflectionResponseError,
    SubmissionInProgressError,
    UnknownPracticeModeError,
)
from .practice_modes import (
    PracticeMode,
    PracticeModeDefinition,
    build_practice_mode_definitions,
)
from .stimulus import StimulusProvider
from .store import DemoActivity, LearnerJourneyStore, PracticeCompletion
from .view_models import (
    CompletionView,
    FeedbackView,
    PracticeActivitySummary,
    PracticeActivityView,
    PracticeDashboardView,
    PracticeHistoryEntry,
    PracticeHistoryView,
    PracticeModeActivitiesView,
    PracticeModeChoiceView,
    PracticeModeOption,
    PracticeReviewView,
    ReflectionView,
    StimulusView,
)

logger = logging.getLogger("fablit.application")


def _now() -> datetime:
    return datetime.now(UTC)


class PracticeApplication:
    """Application-layer orchestration for the learner practice flow.

    The facade the Web/UI layer uses to drive the learner journey. Each
    method maps to a SPEC-012 use case and returns a learner-facing view
    model, never a domain object.

    SPEC-021: this application now also orchestrates durable practice history
    persistence and review. The persistence boundary isolates Datastore
    concerns via the PracticeHistoryRepository port.
    """

    def __init__(
        self,
        *,
        store: LearnerJourneyStore,
        evaluator: Evaluator,
        stimulus_provider: StimulusProvider,
        history_repository: PracticeHistoryRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._evaluator = evaluator
        self._stimulus_provider = stimulus_provider
        self._history_repository = history_repository
        self._clock = clock or _now
        # HTMX disables the submit button in normal browser use, but requests
        # can still race due to retries or multiple clients. Keep this guard at
        # the application boundary so only one evaluation per activity runs at
        # a time (SPEC-017 FR-017-03).
        self._submitting_activity_ids: set[UUID] = set()
        self._submission_lock = Lock()
        # SPEC-022: the supported practice modes and their curated activity
        # eligibility, resolved once from the seeded content configuration.
        self._practice_modes = build_practice_mode_definitions(store.list_activities())

    # SPEC-022 — Practice Mode Choice

    def get_practice_modes(self) -> PracticeModeChoiceView:
        """Return the available practice modes (SPEC-022 §7).

        The chooser presents every supported mode with its learner-facing
        label, brief description, and indicative effort guidance (a guide,
        never a countdown or limit). No mode is recommended, ranked, or
        pre-selected from learner history or behaviour (§12, AC-022-10).
        """
        return PracticeModeChoiceView(
            question=PRACTICE_MODE_CHOICE_QUESTION,
            modes=tuple(
                PracticeModeOption(
                    mode_id=definition.mode.value,
                    label=definition.label,
                    description=definition.description,
                    effort_guidance=definition.effort_guidance,
                )
                for definition in self._practice_modes
            ),
        )

    def get_practice_mode_activities(
        self, mode: PracticeMode
    ) -> PracticeModeActivitiesView:
        """Resolve the existing activities a chosen mode offers (SPEC-022 §6).

        Selection is always the learner's explicit choice: activities come
        from the mode's curated eligibility configuration, never from
        history-based inference. Entries reuse the ordinary dashboard
        summaries, and every eligible activity runs the unchanged practice
        journey (§8, §9).

        Raises:
            UnknownPracticeModeError: If the mode is not supported.
        """
        definition = self._practice_mode_definition(mode)
        # The curated configuration defines both membership and order; Full
        # Practice's eligibility tuple already follows library order.
        summaries = tuple(
            self._activity_summary(self._store.get_activity(activity_id))
            for activity_id in definition.eligible_activity_ids
        )
        return PracticeModeActivitiesView(
            mode_id=definition.mode.value,
            mode_label=definition.label,
            mode_description=definition.description,
            effort_guidance=definition.effort_guidance,
            activities=summaries,
            is_empty=len(summaries) == 0,
        )

    def _activity_summary(self, item: DemoActivity) -> PracticeActivitySummary:
        """Prepare the dashboard summary for one available activity."""
        return PracticeActivitySummary(
            id=item.activity.id,
            title=item.title,
            description=item.description,
            skills=self._skill_names(item.activity.skill_ids),
            has_completed_practice=self._has_completed_activity(item.activity.id),
            preview_image_url=item.fallback_image,
            preview_alt_text=item.fallback_alt,
        )

    def _practice_mode_definition(self, mode: PracticeMode) -> PracticeModeDefinition:
        """Return the definition of a supported mode, rejecting unknown ones."""
        for definition in self._practice_modes:
            if definition.mode is mode:
                return definition
        raise UnknownPracticeModeError("That practice mode isn't available.")

    # UC-001 — Get Practice Dashboard
    def get_dashboard(self) -> PracticeDashboardView:
        """Return the available practice activities for the dashboard."""
        return PracticeDashboardView(
            activities=tuple(
                self._activity_summary(item) for item in self._store.list_activities()
            )
        )

    # UC-002 — Start Practice Activity
    def start_practice(self, activity_id: UUID) -> PracticeActivityView:
        """Prepare an activity for learner practice, resolving its stimulus.

        When the activity depends on a visual stimulus, the stimulus is
        resolved through the provider abstraction and becomes part of the
        learner's activity instance (§14). The same resolved stimulus is
        reused while the learner is working on this instance (§19).
        """
        item = self._store.get_activity(activity_id)
        stimulus = self._resolve_stimulus(item)
        return PracticeActivityView(
            id=item.activity.id,
            title=item.title,
            description=item.description,
            skills=self._skill_names(item.activity.skill_ids),
            prompt=item.activity.instructions,
            stimulus=self._stimulus_view(stimulus),
        )

    # UC-003/004/005 — Submit Response + Response-Aware Evaluation + Feedback
    def submit_response(self, activity_id: UUID, response: str) -> FeedbackView:
        """Accept a learner response, create the journey records, and prepare feedback.

        Creates a Submitted Submission through the existing domain model,
        evaluates it with the deterministic response-aware demo evaluator
        (receiving the activity and the resolved stimulus, SPEC-015 §27),
        creates the corresponding Feedback, and marks it as the feedback
        currently shown to the learner.
        """
        item = self._store.get_activity(activity_id)
        if not isinstance(response, str) or not response.strip():
            raise InvalidPracticeResponseError(
                "Please enter a response before submitting."
            )
        self._begin_submission(activity_id)
        try:
            submitted = Submission(
                learner_id=self._store.learner_id,
                activity_id=activity_id,
                response=response,
            ).submit(submitted_at=self._clock())
            # The stimulus is normally resolved when the activity is started; if
            # it was not (for example a direct submission), resolve it now so the
            # evaluator always receives the actual stimulus (§27).
            stimulus = self._store.current_stimulus(activity_id)
            if stimulus is None:
                stimulus = self._resolve_stimulus(item)
            try:
                evaluation = self._evaluator.evaluate(
                    submitted,
                    activity=item.activity,
                    stimulus=stimulus,
                    evaluated_at=self._clock(),
                )
            except Exception:
                # SPEC-015 §64: an evaluation failure must not lose the learner's
                # response; the Web/UI layer re-presents it with a safe message.
                logger.exception(
                    "evaluation failed",
                    extra={"activity_id": str(activity_id)},
                )
                raise EvaluationFailedError(
                    "We couldn't evaluate your response. Please try again."
                ) from None
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
        finally:
            self._finish_submission(activity_id)

    def _begin_submission(self, activity_id: UUID) -> None:
        """Reserve an activity while its submitted response is evaluated."""
        with self._submission_lock:
            if activity_id in self._submitting_activity_ids:
                raise SubmissionInProgressError(
                    "Your response is already being evaluated. Please wait."
                )
            self._submitting_activity_ids.add(activity_id)

    def _finish_submission(self, activity_id: UUID) -> None:
        """Make an activity available for a later submission or retry."""
        with self._submission_lock:
            self._submitting_activity_ids.discard(activity_id)

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
        """Save the learner's Reflection and return the completion result.

        SPEC-021: after successful reflection, the completion is persisted
        durably through the history repository. If persistence fails, an
        explicit error is raised and the learner is not falsely told the
        completion was recorded (SPEC-021 §14).
        """
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
        activity = self._activity_for_feedback(feedback)
        self._store.save_completion(
            PracticeCompletion(
                learner_id=self._store.learner_id,
                activity_id=activity.activity.id,
                reflection_id=reflection.id,
                completed_at=self._clock(),
            )
        )

        # SPEC-021: persist the completion durably if a repository is configured
        if self._history_repository is not None:
            evaluation = self._store.get_evaluation(feedback.evaluation_id)
            submission = self._store.get_submission(evaluation.submission_id)
            stimulus = self._store.current_stimulus(activity.activity.id)
            self._history_repository.save_completion(
                learner_id=self._store.learner_id,
                activity_id=activity.activity.id,
                activity_title=activity.title,
                submission=submission,
                evaluation=evaluation,
                feedback=feedback,
                reflection=reflection,
                stimulus=stimulus,
            )
            logger.info(
                "practice completion persisted",
                extra={
                    "learner_id": str(self._store.learner_id),
                    "activity_id": str(activity.activity.id),
                    "reflection_id": str(reflection.id),
                },
            )

        return self._completion_view()

    def get_completion(self) -> CompletionView:
        """Return the completion confirmation once a Reflection has been saved."""
        if self._store.last_reflection() is None:
            raise CompletionNotFoundError("No completed practice yet.")
        return self._completion_view()

    # SPEC-021: Practice History and Review

    def get_practice_history(self) -> PracticeHistoryView:
        """Retrieve the learner's completed practice history (SPEC-021 §8).

        SPEC-021 §8: history should make it easy to answer "What have I
        practised recently?" Recent completed practice appears first.

        If no repository is configured, returns empty history. Otherwise
        retrieves from durable storage.

        Returns:
            PracticeHistoryView: The history with entries ordered newest first,
                or empty if no completed practice exists.

        Raises:
            PersistenceError: If durable storage retrieval fails.
        """
        if self._history_repository is None:
            return PracticeHistoryView(entries=(), is_empty=True)

        summaries = self._history_repository.list_completions(self._store.learner_id)
        entries = tuple(
            PracticeHistoryEntry(
                completion_id=s.completion_id,
                activity_id=s.activity_id,
                activity_title=s.activity_title,
                completed_at=s.completed_at,
                submission_preview=s.submission_preview,
            )
            for s in summaries
        )

        return PracticeHistoryView(
            entries=entries,
            is_empty=len(entries) == 0,
        )

    def get_practice_review(self, completion_id: UUID) -> PracticeReviewView:
        """Retrieve a specific completed practice for review (SPEC-021 §9).

        SPEC-021 §9: selecting a completed practice allows the learner to review
        the meaningful parts of that specific practice instance, including
        activity, stimulus/context, response, evaluation, feedback, reflection,
        and completion timestamp.

        Args:
            completion_id: The stable identity of the completion to review.

        Returns:
            PracticeReviewView: The review with all evidence.

        Raises:
            CompletionNotFoundError: If the completion doesn't exist or doesn't
                belong to the learner.
            PersistenceError: If durable storage retrieval fails.
        """
        if self._history_repository is None:
            raise CompletionNotFoundError("Practice history is not available.")

        completion = self._history_repository.get_completion(
            self._store.learner_id, completion_id
        )
        if completion is None:
            raise CompletionNotFoundError("Completed practice not found.")

        # Split the evaluation findings into categories for presentation
        strengths, improvements, next_steps = self._categorise(completion.evaluation)

        return PracticeReviewView(
            activity_title=completion.activity_title,
            activity_id=completion.activity_id,
            completed_at=completion.completed_at,
            stimulus=self._stimulus_view(completion.stimulus),
            learner_response=completion.submission.response,
            strengths=strengths,
            improvements=improvements,
            next_steps=next_steps,
            feedback=completion.feedback.content,
            reflection=completion.reflection.content,
        )

    def _resolve_stimulus(self, item: DemoActivity) -> StimulusInstance | None:
        """Resolve (or reuse) the stimulus for an activity instance, if required.

        Activities without a stimulus context have no stimulus (§6). For
        stimulus-dependent activities the current instance's stimulus is
        reused (§19); otherwise the provider resolves one, which is then
        retained with the activity instance (§14–16).
        """
        if item.stimulus_context is None:
            return None
        existing = self._store.current_stimulus(item.activity.id)
        if existing is not None:
            return existing
        stimulus = self._stimulus_provider.resolve(
            item.activity, resolved_at=self._clock()
        )
        self._store.set_current_stimulus(stimulus)
        return stimulus

    def _stimulus_view(self, stimulus: StimulusInstance | None) -> StimulusView | None:
        if stimulus is None:
            return None
        return StimulusView(
            image_url=stimulus.image_url,
            alt_text=stimulus.alt_text or "An image for this activity.",
            attribution=stimulus.attribution,
            source_url=stimulus.source_url,
        )

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

    def _has_completed_activity(self, activity_id: UUID) -> bool:
        """Check if the learner has completed an activity.

        First checks in-memory store for current session, then checks durable
        history repository if configured.
        """
        # Check in-memory store first (current session)
        if self._store.has_completed_activity(activity_id):
            return True

        # Check durable history if available
        if self._history_repository is not None:
            return self._history_repository.has_completed_activity(
                self._store.learner_id, activity_id
            )

        return False

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
        """Split findings into what was noticed, what to think about, and next steps.

        Response-aware Findings carry evidence (a matched concept or response
        excerpt) and are presented as ``strengths``/``what you noticed``;
        guidance Findings (improvement, next step) carry no evidence. When no
        Finding carries evidence (predefined evaluation for non-stimulus
        activities), the first guidance finding is presented as what was
        noticed, preserving the SPEC-012 presentation. A future evaluator
        with a richer Finding structure can replace this categorisation
        without changing the learner-facing view.
        """
        grounded = tuple(
            finding for finding in evaluation.findings if finding.evidence is not None
        )
        guidance = tuple(
            finding for finding in evaluation.findings if finding.evidence is None
        )
        if grounded:
            strengths = tuple(finding.observation for finding in grounded)
        elif guidance:
            strengths = (guidance[0].observation,)
        else:
            strengths = ()
        improvements = tuple(finding.observation for finding in guidance[1:2])
        next_steps = tuple(finding.observation for finding in guidance[2:3])
        return strengths, improvements, next_steps
