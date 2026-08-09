"""Assessment domain model (SPEC-005)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .activity import AssessmentActivity
from .types import (
    AssessmentStatus,
    DuplicateActivityPositionError,
    InvalidAssessmentError,
)


@dataclass(frozen=True)
class Assessment:
    """A structured collection of Assessment Activities (SPEC-005).

    An Assessment is a learning experience composed of one or more ordered
    Assessment Activities. This model is intentionally in-memory only: no
    persistence, submission, or delivery behaviour is introduced here.

    Attributes:
        title: The short name of the assessment experience.
        description: The description or purpose of the assessment.
        status: The lifecycle state of the assessment.
        activities: The ordered collection of activities owned by this
            assessment (at least one, occupying sequential positions).
        id: The stable, unique domain identity. Generated when omitted.

    Raises:
        InvalidAssessmentError: When required metadata is missing or invalid,
            when the assessment has no activities, or when activity positions
            are not sequential starting from zero.
        DuplicateActivityPositionError: When two activities share a position.
    """

    title: str
    description: str
    status: AssessmentStatus
    activities: tuple[AssessmentActivity, ...]
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidAssessmentError(
                f"assessment must have a valid identity (got {self.id!r})"
            )
        if not self.title or not self.title.strip():
            raise InvalidAssessmentError("assessment must have a title")
        if not self.description or not self.description.strip():
            raise InvalidAssessmentError(
                "assessment must have a description or purpose"
            )
        if not isinstance(self.status, AssessmentStatus):
            raise InvalidAssessmentError(
                f"assessment must declare a valid status (got {self.status!r})"
            )
        if not self.activities:
            raise InvalidAssessmentError(
                "assessment must contain at least one activity"
            )
        for activity in self.activities:
            if not isinstance(activity, AssessmentActivity):
                raise InvalidAssessmentError(
                    "assessment activities must be AssessmentActivity instances"
                    f" (got {activity!r})"
                )
        positions = [activity.position for activity in self.activities]
        if len(set(positions)) != len(positions):
            raise DuplicateActivityPositionError(
                f"assessment activities must not share positions (got {positions})"
            )
        if positions != list(range(len(self.activities))):
            raise InvalidAssessmentError(
                "assessment activity positions must be sequential starting from 0"
                f" (got {positions})"
            )

    def ordered_activities(self) -> tuple[AssessmentActivity, ...]:
        """Return the activities in deterministic position order."""
        return tuple(sorted(self.activities, key=lambda activity: activity.position))
