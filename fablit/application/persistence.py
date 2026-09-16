"""Persistence port for learner practice history (SPEC-021).

This module defines the abstract persistence interface for learner journey
history. The port is deliberately narrow and focused on the existing learner
journey rather than becoming a generic repository framework.

The application layer depends on this port, not on Datastore implementations
directly. Concrete implementations (in-memory, Datastore) live in separate
adapters behind this boundary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fablit.domain import Evaluation, Feedback, Reflection, StimulusInstance, Submission


@dataclass(frozen=True)
class StoredPracticeCompletion:
    """A durable record of a completed learner practice instance.

    SPEC-021 §5: the persisted learner-history record retains relationships
    equivalent to a completed practice with all evidence required for review.

    This dataclass represents the reconstituted data after retrieval from
    durable storage. It carries only domain/application semantics, never
    Datastore-specific concerns.
    """

    completion_id: UUID  # Stable identity of this completion record
    learner_id: UUID
    activity_id: UUID
    activity_title: str
    completed_at: datetime
    # Journey evidence required for review
    submission: Submission
    evaluation: Evaluation
    feedback: Feedback
    reflection: Reflection
    stimulus: StimulusInstance | None = None  # SPEC-015 stimulus preservation


@dataclass(frozen=True)
class PracticeHistorySummary:
    """A brief summary for a practice history list entry.

    SPEC-021 §8: the history view should provide enough context to distinguish
    records (activity title, completion date/time, concise practice context).
    """

    completion_id: UUID
    activity_id: UUID
    activity_title: str
    completed_at: datetime
    submission_preview: str  # Brief excerpt of the learner's response


class PracticeHistoryRepository(ABC):
    """Persistence port for learner practice history (SPEC-021).

    The application layer uses this abstract interface to store and retrieve
    completed practice records. Concrete implementations (in-memory,
    Datastore) are isolated behind this boundary.

    SPEC-021 §11: the adapter is responsible for converting application/domain
    records to persistence-compatible representations, assigning stable
    identifiers, and reconstructing domain records for review. The domain
    model remains independent of persistence mechanics.
    """

    @abstractmethod
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
        """Persist a completed practice journey durably.

        SPEC-021 §14: completion persistence must be idempotent/retry-safe and
        must not silently report durable completion when the write fails.

        Args:
            learner_id: The learner whose practice is being completed.
            activity_id: The activity that was practiced.
            activity_title: The activity's display title.
            submission: The learner's response (Submission domain object).
            evaluation: The evaluation result (Evaluation domain object).
            feedback: The feedback derived from the evaluation (Feedback).
            reflection: The learner's reflection (Reflection domain object).
            stimulus: The resolved stimulus shown during practice, if any.

        Returns:
            StoredPracticeCompletion: The persisted record with stable identity.

        Raises:
            PersistenceError: If the write to durable storage fails.
                The application must handle this explicitly and not falsely
                report the completion as durable.
        """

    @abstractmethod
    def get_completion(
        self, learner_id: UUID, completion_id: UUID
    ) -> StoredPracticeCompletion | None:
        """Retrieve a specific completed practice by identity.

        SPEC-021 §9: selecting a completed practice allows review of the
        meaningful parts of that specific practice instance.

        Args:
            learner_id: The learner whose practice is being retrieved.
            completion_id: The stable identity of the completion record.

        Returns:
            StoredPracticeCompletion: The complete record with all evidence,
                or None if the completion does not exist or does not belong
                to the learner.
        """

    @abstractmethod
    def list_completions(self, learner_id: UUID) -> tuple[PracticeHistorySummary, ...]:
        """List all completed practice for a learner in chronological order.

        SPEC-021 §8: the history should be ordered predictably with recent
        completed practice first. Empty history is valid and returns an empty
        tuple.

        Args:
            learner_id: The learner whose history is being listed.

        Returns:
            tuple[PracticeHistorySummary, ...]: Summaries ordered newest first,
                or empty tuple if the learner has no completed practice.
        """

    @abstractmethod
    def has_completed_activity(self, learner_id: UUID, activity_id: UUID) -> bool:
        """Whether the learner has completed this activity at least once.

        This method supports the dashboard's "has_completed_practice" indicator.

        Args:
            learner_id: The learner whose history is being checked.
            activity_id: The activity whose completion status is being checked.

        Returns:
            bool: True if at least one completed practice exists for this
                learner/activity pair, False otherwise.
        """


class PersistenceError(Exception):
    """Base exception for persistence-layer failures (SPEC-021 §14).

    SPEC-021 §14: persistence failures must be explicit and observable at the
    application boundary. The application shall not silently discard data or
    report durable completion when the write failed.
    """
