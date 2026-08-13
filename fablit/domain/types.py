"""Controlled terminology and domain errors for the Fablit learning domain.

This module belongs to the learning-domain layer introduced by SPEC-005 and
extended by SPEC-006, SPEC-007, SPEC-008, and SPEC-009. It must remain
independent of platform infrastructure, persistence, and examination-specific
concepts.
"""

from __future__ import annotations

from enum import StrEnum


class ActivityType(StrEnum):
    """The controlled set of Assessment Activity types.

    The initial set is deliberately small and extensible. Additional types
    shall be introduced through future specifications when concrete
    requirements exist.
    """

    MULTIPLE_CHOICE = "multiple_choice"
    WRITTEN_RESPONSE = "written_response"
    OBSERVATION = "observation"
    REFLECTION = "reflection"


class AssessmentStatus(StrEnum):
    """Lifecycle states of an Assessment.

    The lifecycle distinguishes an editable definition (``DRAFT``) from an
    available learning experience (``PUBLISHED``). Runtime delivery lifecycle
    is intentionally deferred to future specifications.
    """

    DRAFT = "draft"
    PUBLISHED = "published"


class ActivityStatus(StrEnum):
    """Availability states of an Assessment Activity."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class SubmissionStatus(StrEnum):
    """Lifecycle states of a Submission.

    The lifecycle distinguishes an editable, possibly incomplete Draft from a
    complete, immutable Submitted Submission. Additional states shall be
    introduced through future specifications when concrete use cases require
    them.
    """

    DRAFT = "draft"
    SUBMITTED = "submitted"


class DomainError(Exception):
    """Base class for all learning-domain errors."""


class InvalidActivityError(DomainError):
    """Raised when an Assessment Activity violates a domain rule."""


class InvalidAssessmentError(DomainError):
    """Raised when an Assessment violates a domain rule."""


class DuplicateActivityPositionError(InvalidAssessmentError):
    """Raised when an Assessment contains two activities with the same position."""


class InvalidSubmissionError(DomainError):
    """Raised when a Submission violates a domain rule."""


class InvalidSubmissionTransitionError(InvalidSubmissionError):
    """Raised when a Submission lifecycle transition is invalid."""


class InvalidEvaluationError(DomainError):
    """Raised when an Evaluation violates a domain rule."""


class InvalidEvaluationFindingError(InvalidEvaluationError):
    """Raised when an Evaluation Finding violates a domain rule."""


class InvalidFeedbackError(DomainError):
    """Raised when a Feedback violates a domain rule."""


class InvalidReflectionError(DomainError):
    """Raised when a Reflection violates a domain rule."""


class InvalidSkillError(DomainError):
    """Raised when a Skill violates a domain rule."""
