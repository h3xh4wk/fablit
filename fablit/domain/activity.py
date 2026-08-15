"""Assessment Activity domain model (SPEC-005, SPEC-011)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .types import ActivityStatus, ActivityType, InvalidActivityError


@dataclass(frozen=True)
class AssessmentActivity:
    """The smallest meaningful interaction between a learner and the platform.

    An Assessment Activity is the unit of learner interaction that will
    eventually produce a Submission (SPEC-006). This model establishes the
    stable identity, controlled type, interaction description, ordering, and
    status required to define an Assessment, and (SPEC-011) the Skills the
    activity provides an opportunity to practise.

    SPEC-011 associates an activity with zero or more Skills by stable
    identity only. The association is intentionally simple: it establishes
    the intended learning context, does not own either domain object, carries
    no relationship attributes, and introduces no Progress, mastery, scoring,
    evaluation, curriculum, examination, or AI semantics. Neither a Skill nor
    an Assessment Activity requires the other to exist.

    Attributes:
        activity_type: The controlled activity type.
        instructions: The instructions or prompt reference describing the
            learner interaction.
        position: The explicit zero-based order of this activity within its
            Assessment.
        id: The stable, unique domain identity. Generated when omitted.
        status: The availability state of the activity.
        skill_ids: The stable identities (SPEC-010) of the Skills this
            activity provides an opportunity to practise. May be empty; each
            identity must be unique within the collection.

    Raises:
        InvalidActivityError: When required domain information is missing or
            invalid (missing/invalid identity, type, status, blank
            instructions, an invalid position, or invalid/duplicate skill
            references).
    """

    activity_type: ActivityType
    instructions: str
    position: int
    id: UUID = field(default_factory=uuid4)
    status: ActivityStatus = ActivityStatus.ACTIVE
    skill_ids: tuple[UUID, ...] = ()

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
        if not isinstance(self.skill_ids, tuple):
            raise InvalidActivityError(
                "assessment activity skill references must be provided as a tuple"
                f" (got {self.skill_ids!r})"
            )
        for skill_id in self.skill_ids:
            if not isinstance(skill_id, UUID):
                raise InvalidActivityError(
                    "assessment activity must reference valid skill identities"
                    f" (got {self.skill_ids!r})"
                )
        if len(self.skill_ids) != len(set(self.skill_ids)):
            raise InvalidActivityError(
                "assessment activity must not reference the same skill more than once"
                f" (got {self.skill_ids!r})"
            )
