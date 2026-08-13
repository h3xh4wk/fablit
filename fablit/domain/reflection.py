"""Reflection domain model (SPEC-009)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from .types import InvalidReflectionError


@dataclass(frozen=True)
class Reflection:
    """The learner's deliberate response to Feedback (SPEC-009).

    Reflection represents what the learner makes of the Feedback they
    received: it helps them make sense of what they learned, assess their own
    understanding or performance, and identify what they want to carry forward
    into future practice. It references the Feedback by its stable identity
    (SPEC-008) and carries a single general learner-authored content field. It
    does not duplicate the Feedback, does not require a numerical confidence
    score, and does not contain improvement goals or action plans — those
    concepts remain outside this model.

    The content representation is intentionally simple and general. Separate
    fields for self-assessment, confidence, learning goals, improvement goals,
    action plans, next steps, or learning notes are deliberately avoided;
    future specifications may introduce them as first-class concepts when
    concrete requirements justify doing so.

    Reflection is immutable after creation. If the learner reflects again
    later, a new Reflection instance shall be created rather than silently
    modifying an existing one.

    Attributes:
        feedback_id: The stable identity (SPEC-008) of the Feedback that
            prompted this Reflection.
        content: The learner-authored reflective content. Must be meaningful
            (non-empty, non-whitespace).
        id: The stable, unique domain identity. Generated when omitted.
        created_at: The timezone-aware time the Reflection was created.

    Raises:
        InvalidReflectionError: When required domain information is missing or
            invalid (missing/invalid identity, feedback reference, empty or
            whitespace-only content, or a missing/naive timestamp).
    """

    feedback_id: UUID
    content: str
    created_at: datetime
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidReflectionError(
                f"reflection must have a valid identity (got {self.id!r})"
            )
        if not isinstance(self.feedback_id, UUID):
            raise InvalidReflectionError(
                "reflection must reference a valid feedback identity"
                f" (got {self.feedback_id!r})"
            )
        if not isinstance(self.content, str) or not self.content.strip():
            raise InvalidReflectionError(
                "reflection must contain meaningful reflective content"
                f" (got {self.content!r})"
            )
        if not isinstance(self.created_at, datetime):
            raise InvalidReflectionError("reflection must record when it was created")
        if self.created_at.tzinfo is None:
            raise InvalidReflectionError("reflection timestamp must be timezone-aware")
