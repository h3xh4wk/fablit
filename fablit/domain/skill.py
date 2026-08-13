"""Skill domain model (SPEC-010)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .types import InvalidSkillError


@dataclass(frozen=True)
class Skill:
    """A measurable, transferable learner capability (SPEC-010).

    Skill represents the capability being developed through deliberate
    practice. It is intentionally standalone: it carries only a stable
    identity, a human-readable name, and a meaningful description. It does
    not reference an Assessment Activity, Evaluation, Finding, Feedback, or
    Reflection, does not contain evaluation criteria, scoring, Progress,
    mastery, or hierarchy state, and does not depend on AI or external
    generation mechanisms — those concepts remain outside this model.

    The structure is intentionally minimal so that future specifications may
    introduce Skill-to-Activity relationships, Progress, mastery, taxonomies,
    and curriculum or examination mappings without redesigning the Skill
    aggregate. SPEC-010 does not introduce a predefined Skill catalogue.

    Skill is immutable after creation. If a revised Skill definition is
    required later, that change shall be handled through an explicitly
    designed domain mechanism rather than silently modifying an existing one.

    Attributes:
        name: The human-readable name identifying the capability. Must be
            meaningful (non-empty, non-whitespace).
        description: A meaningful description explaining the capability
            represented by the Skill. Must be non-empty, non-whitespace.
        id: The stable, unique domain identity. Generated when omitted.

    Raises:
        InvalidSkillError: When required domain information is missing or
            invalid (missing/invalid identity, empty or whitespace-only name,
            or empty or whitespace-only description).
    """

    name: str
    description: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidSkillError(
                f"skill must have a valid identity (got {self.id!r})"
            )
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidSkillError(
                f"skill must have a meaningful name (got {self.name!r})"
            )
        if not isinstance(self.description, str) or not self.description.strip():
            raise InvalidSkillError(
                f"skill must have a meaningful description (got {self.description!r})"
            )
