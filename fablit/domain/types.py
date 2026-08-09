"""Controlled terminology and domain errors for the Fablit learning domain.

This module belongs to the learning-domain layer introduced by SPEC-005. It
must remain independent of platform infrastructure, persistence, and
examination-specific concepts.
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


class DomainError(Exception):
    """Base class for all learning-domain errors."""


class InvalidActivityError(DomainError):
    """Raised when an Assessment Activity violates a domain rule."""


class InvalidAssessmentError(DomainError):
    """Raised when an Assessment violates a domain rule."""


class DuplicateActivityPositionError(InvalidAssessmentError):
    """Raised when an Assessment contains two activities with the same position."""
