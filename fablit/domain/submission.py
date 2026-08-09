"""Submission domain model (SPEC-006)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from .types import (
    InvalidSubmissionError,
    InvalidSubmissionTransitionError,
    SubmissionStatus,
)


@dataclass(frozen=True)
class Submission:
    """A learner's response to an Assessment Activity (SPEC-006).

    A Submission is the first learner-produced domain object: it captures the
    learner's work at a point in time so that future Evaluation and Feedback
    stages can consume it. It references the learner and the Assessment
    Activity by stable identity only and never duplicates the activity
    definition (DR-009 / DR-011).

    The lifecycle distinguishes an editable Draft, which may be incomplete,
    from a Submitted Submission, which must contain a non-empty response and
    a submission timestamp and may not be silently modified. ``submit()``
    performs the explicit Draft → Submitted transition.

    Attributes:
        response: The learner-provided response data. A Draft may be
            incomplete (empty); a Submitted Submission must contain a
            non-empty response.
        learner_id: The stable identity of the learner who produced the
            submission.
        activity_id: The stable identity (SPEC-005) of the Assessment
            Activity being answered.
        id: The stable, unique domain identity. Generated when omitted.
        status: The lifecycle state of the submission.
        submitted_at: The timezone-aware time of submission. Required for a
            Submitted Submission, absent for a Draft.

    Raises:
        InvalidSubmissionError: When required domain information is missing
            or invalid (missing/invalid identity, learner, activity, status,
            response, or timestamp).
        InvalidSubmissionTransitionError: When ``submit()`` is called on an
            already submitted Submission.
    """

    response: str
    learner_id: UUID
    activity_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: SubmissionStatus = SubmissionStatus.DRAFT
    submitted_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidSubmissionError(
                f"submission must have a valid identity (got {self.id!r})"
            )
        if not isinstance(self.learner_id, UUID):
            raise InvalidSubmissionError(
                "submission must reference a valid learner identity"
                f" (got {self.learner_id!r})"
            )
        if not isinstance(self.activity_id, UUID):
            raise InvalidSubmissionError(
                "submission must reference a valid assessment activity identity"
                f" (got {self.activity_id!r})"
            )
        if not isinstance(self.status, SubmissionStatus):
            raise InvalidSubmissionError(
                f"submission must declare a valid status (got {self.status!r})"
            )
        if self.status is SubmissionStatus.SUBMITTED:
            if not isinstance(self.response, str) or not self.response.strip():
                raise InvalidSubmissionError(
                    "a submitted submission must contain a learner response"
                )
            if not isinstance(self.submitted_at, datetime):
                raise InvalidSubmissionError(
                    "a submitted submission must record a submission timestamp"
                )
            if self.submitted_at.tzinfo is None:
                raise InvalidSubmissionError(
                    "submission timestamp must be timezone-aware"
                )
        elif self.submitted_at is not None:
            raise InvalidSubmissionError(
                "a draft submission must not record a submission timestamp"
            )

    def submit(self, *, submitted_at: datetime | None = None) -> Submission:
        """Transition this Draft Submission to Submitted.

        The transition requires a non-empty learner response and records the
        time of submission. The resulting Submitted Submission is immutable:
        its core response and associations cannot be silently modified.

        Args:
            submitted_at: The time of submission. Defaults to the current UTC
                time when omitted.

        Returns:
            A new Submitted Submission preserving the identity, learner, and
            activity references.

        Raises:
            InvalidSubmissionTransitionError: When the submission has already
                been submitted.
            InvalidSubmissionError: When the draft has no learner response.
        """
        if self.status is SubmissionStatus.SUBMITTED:
            raise InvalidSubmissionTransitionError(
                "cannot submit an already submitted submission"
            )
        if not isinstance(self.response, str) or not self.response.strip():
            raise InvalidSubmissionError(
                "a submission must contain a learner response before being submitted"
            )
        timestamp = submitted_at if submitted_at is not None else datetime.now(UTC)
        return Submission(
            id=self.id,
            learner_id=self.learner_id,
            activity_id=self.activity_id,
            response=self.response,
            status=SubmissionStatus.SUBMITTED,
            submitted_at=timestamp,
        )
