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


class StimulusRetrievalError(ApplicationError):
    """Raised when the stimulus provider cannot supply a stimulus (SPEC-015 §21)."""


class EvaluationFailedError(ApplicationError):
    """Raised when the evaluator cannot evaluate a submitted response (SPEC-015 §64)."""


class SubmissionInProgressError(ApplicationError):
    """Raised when an activity already has a submission being evaluated (SPEC-017)."""


class InvalidContentContractError(ApplicationError):
    """Raised when a Practice Content Contract has a blank field (SPEC-029)."""


class UnknownPracticeModeError(ApplicationError):
    """Raised when a requested practice mode does not exist (SPEC-022)."""


class InvalidAuthoringBriefError(ApplicationError):
    """Raised when an authoring brief is incomplete or invalid (SPEC-032 §4)."""


class CandidateNotFoundError(ApplicationError):
    """Raised when an authoring candidate does not exist (SPEC-032 §9)."""


class CandidateNotApprovableError(ApplicationError):
    """Raised when a malformed or invalid candidate cannot be approved.

    SPEC-032 §7: validation is a hard gate — malformed AI output can never
    enter the approval path.
    """


class AuthoringProviderError(ApplicationError):
    """Raised when an authoring LLM provider cannot produce a candidate.

    ARCH-001: provider API failures, timeouts, and unusable responses are
    translated into this application-level error at the provider boundary so
    the authoring workflow never depends on a specific provider's exceptions
    and ordinary learner practice never fails because AI is unavailable.
    """


class AuthoringProviderConfigurationError(AuthoringProviderError):
    """Raised when an authoring LLM provider is misconfigured.

    ARCH-001: for example a concrete adapter is requested without the
    credentials it needs. Configuration failures are surfaced cleanly rather
    than deferring to a confusing runtime error.
    """
