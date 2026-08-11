"""Feedback domain model (SPEC-008)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from .types import InvalidFeedbackError


@dataclass(frozen=True)
class Feedback:
    """Learner-facing guidance derived from an Evaluation (SPEC-008).

    Feedback represents the learner-facing result of an Evaluation: it helps
    the learner understand what was observed about their work and identify
    meaningful opportunities for continued learning. It references the
    Evaluation by its stable identity (SPEC-007) and carries a single general
    learner-facing content field. It does not duplicate the Evaluation, does
    not require a numerical score, and does not contain Reflection — those
    concepts remain outside this model.

    The content representation is intentionally simple and general. Separate
    fields for strengths, improvement areas, next steps, or reflection
    prompts are deliberately avoided; future specifications may introduce
    them as first-class concepts when concrete requirements justify doing so.

    Feedback is immutable after creation. If new or revised feedback is
    required later, a new Feedback instance shall be created rather than
    silently modifying an existing one.

    Attributes:
        evaluation_id: The stable identity (SPEC-007) of the Evaluation from
            which this Feedback is derived.
        content: The learner-facing guidance. Must be meaningful (non-empty,
            non-whitespace).
        id: The stable, unique domain identity. Generated when omitted.
        created_at: The timezone-aware time the Feedback was created.

    Raises:
        InvalidFeedbackError: When required domain information is missing or
            invalid (missing/invalid identity, evaluation reference, empty or
            whitespace-only content, or a missing/naive timestamp).
    """

    evaluation_id: UUID
    content: str
    created_at: datetime
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidFeedbackError(
                f"feedback must have a valid identity (got {self.id!r})"
            )
        if not isinstance(self.evaluation_id, UUID):
            raise InvalidFeedbackError(
                "feedback must reference a valid evaluation identity"
                f" (got {self.evaluation_id!r})"
            )
        if not isinstance(self.content, str) or not self.content.strip():
            raise InvalidFeedbackError(
                "feedback must contain meaningful learner-facing guidance"
                f" (got {self.content!r})"
            )
        if not isinstance(self.created_at, datetime):
            raise InvalidFeedbackError("feedback must record when it was created")
        if self.created_at.tzinfo is None:
            raise InvalidFeedbackError("feedback timestamp must be timezone-aware")
