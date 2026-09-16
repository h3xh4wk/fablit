"""In-memory implementation of the practice history repository (SPEC-021).

SPEC-021 §13: the persistence boundary should allow application tests to
remain fast and deterministic. Unit/application tests use this in-memory
repository or equivalent test double. Production credentials are not required
for ordinary unit-test execution.

This implementation is suitable for:
- Unit tests of application logic
- Integration tests that don't require Datastore
- Local development without GCP setup
"""

from __future__ import annotations

from uuid import UUID

from fablit.application.persistence import (
    PracticeHistoryRepository,
    PracticeHistorySummary,
    StoredPracticeCompletion,
)
from fablit.domain import Evaluation, Feedback, Reflection, StimulusInstance, Submission


class InMemoryPracticeHistoryRepository(PracticeHistoryRepository):
    """In-memory test double for practice history persistence (SPEC-021).

    All data is stored in process memory and lost on application restart.
    This is appropriate for tests and local development.

    SPEC-021 §6: the in-memory implementation remains useful for unit tests
    and local development where practical, keeping ordinary unit/application
    tests independent of production GCP credentials.
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
        reflection: Reflection,
        stimulus: StimulusInstance | None,
    ) -> StoredPracticeCompletion:
        """Persist a completed practice journey in memory.

        SPEC-021 §14: this in-memory implementation is not crash-safe, but
        the interface supports idempotency at the application level via
        stable identity (the reflection ID can serve as stable completion
        identity).

        Args:
            learner_id: The learner whose practice is being completed.
            activity_id: The activity that was practiced.
            activity_title: The activity's display title.
            submission: The learner's response.
            evaluation: The evaluation result.
            feedback: The feedback.
            reflection: The learner's reflection.
            stimulus: The resolved stimulus, if any.

        Returns:
            StoredPracticeCompletion: The persisted record.

        Raises:
            PersistenceError: Never in this test implementation, but kept
                for interface compatibility.
        """
        # Use reflection_id as the stable completion identity.
        # SPEC-021 §10: each completed practice must remain independently
        # reviewable. Repeated practice creates separate history records.
        completion_id = reflection.id
        # The completion timestamp is the moment the learner's Reflection was
        # recorded — deterministic and identical to the Datastore adapter.
        completed_at = reflection.created_at

        completion = StoredPracticeCompletion(
            completion_id=completion_id,
            learner_id=learner_id,
            activity_id=activity_id,
            activity_title=activity_title,
            completed_at=completed_at,
            submission=submission,
            evaluation=evaluation,
            feedback=feedback,
            reflection=reflection,
            stimulus=stimulus,
        )

        # Store the completion
        self._completions[(learner_id, completion_id)] = completion

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
