"""In-memory implementation of the practice history repository (SPEC-021).

SPEC-021 §13: the persistence boundary should allow application tests to
remain fast and deterministic. Unit/application tests use this in-memory
repository or equivalent test double. Production credentials are not required
for ordinary unit-test execution.

This implementation is suitable for:
- Unit tests of application logic
- Integration tests that don't require Datastore
- Local development without GCP setup

SPEC-033: the artifact is persisted as a reference only. The private binary
bytes live behind the artifact-storage boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fablit.application.persistence import (
    PracticeHistoryRepository,
    PracticeHistorySummary,
    StoredPracticeCompletion,
)
from fablit.domain import Evaluation, Feedback, Reflection, StimulusInstance, Submission

from .artifacts import ArtifactRef


class InMemoryPracticeHistoryRepository(PracticeHistoryRepository):
    """In-memory test double for practice history persistence (SPEC-021).

    All data is stored in process memory and lost on application restart.
    This is appropriate for tests and local development.

    SPEC-021 §6: the in-memory implementation remains useful for unit tests
    and local development where practical, keeping ordinary unit/application
    tests independent of production GCP credentials.

    SPEC-033: the artifact is persisted as a reference only.

    SPEC-159: completion identity is independent of reflection; reflection
    may be absent or attached later to an existing completion.
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory store."""
        # Maps (learner_id, completion_id) → StoredPracticeCompletion
        self._completions: dict[tuple[UUID, UUID], StoredPracticeCompletion] = {}
        # Maps learner_id → list of completion_ids (for history retrieval)
        self._learner_completions: dict[UUID, list[UUID]] = {}

    def save_completion(
        self,
        learner_id: UUID,
        activity_id: UUID,
        activity_title: str,
        submission: Submission,
        evaluation: Evaluation,
        feedback: Feedback,
        reflection: Reflection | None,
        stimulus: StimulusInstance | None,
        artifact: ArtifactRef | None = None,
        completion_id: UUID | None = None,
    ) -> StoredPracticeCompletion:
        """Persist a completed practice journey in memory.

        SPEC-021 §14: this in-memory implementation is not crash-safe, but
        the interface supports idempotency at the application level via
        stable identity.

        SPEC-159: if a reflection is added later, it is attached to the
        existing completion (by completion_id) without creating a duplicate.
        """
        # Use provided completion_id for idempotency/retry and for attaching
        # reflections later; fall back to reflection.id for backward compat.
        if completion_id is None:
            if reflection is not None:
                completion_id = reflection.id
            else:
                # Should not happen with new API, but be defensive
                from uuid import uuid4

                completion_id = uuid4()

        key = (learner_id, completion_id)
        existing = self._completions.get(key)

        reflection_to_store: Reflection | None
        if existing is not None:
            completed_at = existing.completed_at
            # Attach reflection later if provided and not already present
            if reflection is not None:
                reflection_to_store = reflection
            else:
                reflection_to_store = existing.reflection
            activity_title_to_store = activity_title or existing.activity_title
            artifact_to_store = artifact if artifact is not None else existing.artifact
            submission_to_store = submission or existing.submission
            evaluation_to_store = evaluation or existing.evaluation
            feedback_to_store = feedback or existing.feedback
            stimulus_to_store = stimulus if stimulus is not None else existing.stimulus
        else:
            if reflection is not None:
                completed_at = reflection.created_at
            else:
                # Use feedback/evaluation/submission timestamps as fallback
                completed_at = (
                    feedback.created_at
                    if hasattr(feedback, "created_at")
                    else datetime.now(UTC)
                )
            reflection_to_store = reflection
            activity_title_to_store = activity_title
            artifact_to_store = artifact
            submission_to_store = submission
            evaluation_to_store = evaluation
            feedback_to_store = feedback
            stimulus_to_store = stimulus

        completion = StoredPracticeCompletion(
            completion_id=completion_id,
            learner_id=learner_id,
            activity_id=activity_id,
            activity_title=activity_title_to_store,
            completed_at=completed_at,
            submission=submission_to_store,
            evaluation=evaluation_to_store,
            feedback=feedback_to_store,
            reflection=reflection_to_store,
            stimulus=stimulus_to_store,
            artifact=artifact_to_store,
        )

        # Store the completion
        self._completions[key] = completion

        # Track the completion in the learner's history list
        if learner_id not in self._learner_completions:
            self._learner_completions[learner_id] = []
        if completion_id not in self._learner_completions[learner_id]:
            self._learner_completions[learner_id].append(completion_id)

        return completion

    def get_completion(
        self, learner_id: UUID, completion_id: UUID
    ) -> StoredPracticeCompletion | None:
        """Retrieve a specific completed practice by identity.

        Args:
            learner_id: The learner whose practice is being retrieved.
            completion_id: The stable identity of the completion record.

        Returns:
            StoredPracticeCompletion: The complete record, or None if not found.
        """
        return self._completions.get((learner_id, completion_id))

    def list_completions(self, learner_id: UUID) -> tuple[PracticeHistorySummary, ...]:
        """List all completed practice for a learner in chronological order.

        SPEC-021 §8: ordered newest first.

        Args:
            learner_id: The learner whose history is being listed.

        Returns:
            tuple[PracticeHistorySummary, ...]: Summaries ordered newest first.
        """
        if learner_id not in self._learner_completions:
            return ()

        completion_ids = self._learner_completions[learner_id]
        completions = [
            self._completions[(learner_id, cid)]
            for cid in completion_ids
            if (learner_id, cid) in self._completions
        ]

        # Sort by completed_at descending (newest first)
        completions.sort(key=lambda c: c.completed_at, reverse=True)

        summaries = tuple(
            PracticeHistorySummary(
                completion_id=c.completion_id,
                activity_id=c.activity_id,
                activity_title=c.activity_title,
                completed_at=c.completed_at,
                submission_preview=self._preview_text(c.submission.response),
            )
            for c in completions
        )

        return summaries

    def has_completed_activity(self, learner_id: UUID, activity_id: UUID) -> bool:
        """Whether the learner has completed this activity at least once.

        Args:
            learner_id: The learner.
            activity_id: The activity.

        Returns:
            bool: True if at least one completion exists for this pair.
        """
        if learner_id not in self._learner_completions:
            return False

        completion_ids = self._learner_completions[learner_id]
        return any(
            self._completions[(learner_id, cid)].activity_id == activity_id
            for cid in completion_ids
            if (learner_id, cid) in self._completions
        )

    @staticmethod
    def _preview_text(response: str, max_length: int = 60) -> str:
        """Create a brief preview of the learner's response.

        Args:
            response: The full response text.
            max_length: Maximum preview length.

        Returns:
            str: A truncated preview ending with ellipsis if needed.
        """
        if len(response) <= max_length:
            return response
        return response[:max_length].rstrip() + "…"
