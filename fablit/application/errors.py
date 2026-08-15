"""Application-layer errors for the learner practice flow (SPEC-012)."""

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for all application-layer errors."""


class ActivityNotFoundError(ApplicationError):
    """Raised when a requested practice activity does not exist."""


class FeedbackNotFoundError(ApplicationError):
    """Raised when there is no current feedback for the learner."""


class CompletionNotFoundError(ApplicationError):
    """Raised when the learner has not yet completed a practice cycle."""


class InvalidPracticeResponseError(ApplicationError):
    """Raised when a learner response cannot form a valid Submission."""


class InvalidReflectionResponseError(ApplicationError):
    """Raised when a learner reflection cannot be saved."""


class JourneyStateError(ApplicationError):
    """Raised when an internal journey record is missing (programming error)."""
