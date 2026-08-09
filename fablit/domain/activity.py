"""Assessment Activity domain model (SPEC-005)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .types import ActivityStatus, ActivityType, InvalidActivityError


@dataclass(frozen=True)
class AssessmentActivity:
    """The smallest meaningful interaction between a learner and the platform.

    An Assessment Activity is the unit of learner interaction that will
    eventually produce a Submission (SPEC-006). This model only establishes
    the stable identity, controlled type, interaction description, ordering,
    and status required to define an Assessment.

    Attributes:
        activity_type: The controlled activity type.
        instructions: The instructions or prompt reference describing the
            learner interaction.
        position: The explicit zero-based order of this activity within its
            Assessment.
        id: The stable, unique domain identity. Generated when omitted.
        status: The availability state of the activity.

    Raises:
        InvalidActivityError: When required domain information is missing or
            invalid (missing/invalid identity, type, status, blank
            instructions, or an invalid position).
    """

    activity_type: ActivityType
    instructions: str
    position: int
    id: UUID = field(default_factory=uuid4)
    status: ActivityStatus = ActivityStatus.ACTIVE

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidActivityError(
                f"assessment activity must have a valid identity (got {self.id!r})"
            )
        if not isinstance(self.activity_type, ActivityType):
            raise InvalidActivityError(
                "assessment activity must declare a valid activity type"
                f" (got {self.activity_type!r}); choose from "
                f"{', '.join(sorted(t.value for t in ActivityType))}"
            )
        if not isinstance(self.status, ActivityStatus):
            raise InvalidActivityError(
                f"assessment activity must declare a valid status (got {self.status!r})"
            )
        if not self.instructions or not self.instructions.strip():
            raise InvalidActivityError(
                "assessment activity must include instructions or a prompt reference"
            )
        if isinstance(self.position, bool) or not isinstance(self.position, int):
            raise InvalidActivityError(
                "assessment activity position must be an integer "
                f"(got {self.position!r})"
            )
        if self.position < 0:
            raise InvalidActivityError(
                "assessment activity position must be non-negative "
                f"(got {self.position})"
            )
