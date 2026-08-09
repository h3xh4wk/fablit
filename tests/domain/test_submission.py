"""Unit tests for the Submission domain model (SPEC-006)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import fablit.domain.submission
from fablit.domain import (
    InvalidSubmissionError,
    InvalidSubmissionTransitionError,
    Submission,
    SubmissionStatus,
)

from .helpers import make_activity, make_submission, make_submitted_submission

SUBMISSION_SOURCE = Path(fablit.domain.submission.__file__).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Creation and identity
# ---------------------------------------------------------------------------


def test_create_draft_submission_with_valid_data() -> None:
    submission = make_submission(response="My written response.")

    assert isinstance(submission.id, UUID)
    assert submission.response == "My written response."
    assert submission.status is SubmissionStatus.DRAFT
    assert submission.submitted_at is None


def test_create_submission_with_generated_identity() -> None:
    submission = make_submission()

    assert isinstance(submission.id, UUID)


def test_submission_identity_is_unique_across_instances() -> None:
    first = make_submission()
    second = make_submission()

    assert first.id != second.id


def test_submission_identity_remains_stable() -> None:
    submission = make_submission()
    original_id = submission.id

    assert submission.id == original_id
    with pytest.raises(FrozenInstanceError):
        submission.id = uuid4()  # type: ignore[misc]


def test_submission_with_explicit_identity() -> None:
    submission_id = uuid4()

    submission = make_submission(id=submission_id)

    assert submission.id == submission_id


def test_reject_submission_without_identity() -> None:
    with pytest.raises(InvalidSubmissionError, match="identity"):
        make_submission(id=None)


def test_reject_submission_with_invalid_identity() -> None:
    with pytest.raises(InvalidSubmissionError, match="identity"):
        make_submission(id="not-a-uuid")


# ---------------------------------------------------------------------------
# Learner association (FR-002 / DR-002)
# ---------------------------------------------------------------------------


def test_submission_references_learner() -> None:
    learner_id = uuid4()

    submission = make_submission(learner_id=learner_id)

    assert submission.learner_id == learner_id


def test_reject_submission_without_learner() -> None:
    with pytest.raises(InvalidSubmissionError, match="learner"):
        make_submission(learner_id=None)


def test_reject_submission_with_invalid_learner() -> None:
    with pytest.raises(InvalidSubmissionError, match="learner"):
        make_submission(learner_id="learner-1")


# ---------------------------------------------------------------------------
# Assessment Activity association (FR-003 / FR-011 / DR-009)
# ---------------------------------------------------------------------------


def test_submission_references_assessment_activity_by_identity() -> None:
    activity = make_activity()
    submission = make_submission(activity_id=activity.id)

    assert submission.activity_id == activity.id
    # The activity is referenced by identity only; it is not duplicated.
    assert not hasattr(submission, "activity")


def test_reject_submission_without_activity() -> None:
    with pytest.raises(InvalidSubmissionError, match="activity"):
        make_submission(activity_id=None)


def test_reject_submission_with_invalid_activity() -> None:
    with pytest.raises(InvalidSubmissionError, match="activity"):
        make_submission(activity_id="activity-1")


# ---------------------------------------------------------------------------
# Draft behaviour (FR-006 / DR-005)
# ---------------------------------------------------------------------------


def test_draft_may_be_incomplete() -> None:
    submission = make_submission(response="")

    assert submission.status is SubmissionStatus.DRAFT
    assert submission.response == ""


def test_draft_has_no_submission_timestamp() -> None:
    submission = make_submission()

    assert submission.submitted_at is None


def test_reject_draft_with_submission_timestamp() -> None:
    with pytest.raises(InvalidSubmissionError, match="timestamp"):
        make_submission(submitted_at=datetime.now(UTC))


def test_draft_can_be_updated_via_replace() -> None:
    submission = make_submission(response="first attempt")

    updated = replace(submission, response="revised attempt")

    assert updated.status is SubmissionStatus.DRAFT
    assert updated.response == "revised attempt"
    assert updated.id == submission.id
    assert submission.response == "first attempt"


# ---------------------------------------------------------------------------
# Submitted behaviour (FR-007 / FR-009 / DR-006 / DR-007)
# ---------------------------------------------------------------------------


def test_create_submitted_submission_with_valid_data() -> None:
    submitted_at = datetime.now(UTC)

    submission = make_submitted_submission(
        response="Final response.",
        submitted_at=submitted_at,
    )

    assert submission.status is SubmissionStatus.SUBMITTED
    assert submission.response == "Final response."
    assert submission.submitted_at == submitted_at


def test_submitted_submission_timestamp_is_timezone_aware() -> None:
    submission = make_submitted_submission()

    assert submission.submitted_at is not None
    assert submission.submitted_at.tzinfo is not None


def test_reject_submitted_submission_without_response() -> None:
    with pytest.raises(InvalidSubmissionError, match="response"):
        make_submitted_submission(response=None)


def test_reject_submitted_submission_with_empty_response() -> None:
    with pytest.raises(InvalidSubmissionError, match="response"):
        make_submitted_submission(response="")


def test_reject_submitted_submission_with_blank_response() -> None:
    with pytest.raises(InvalidSubmissionError, match="response"):
        make_submitted_submission(response="   ")


def test_reject_submitted_submission_without_timestamp() -> None:
    with pytest.raises(InvalidSubmissionError, match="timestamp"):
        make_submitted_submission(submitted_at=None)


def test_reject_submitted_submission_with_naive_timestamp() -> None:
    with pytest.raises(InvalidSubmissionError, match="timestamp"):
        make_submitted_submission(submitted_at=datetime(2026, 8, 9, 12, 0, 0))


def test_reject_submission_without_status() -> None:
    with pytest.raises(InvalidSubmissionError, match="status"):
        make_submission(status=None)


def test_reject_submission_with_invalid_status() -> None:
    with pytest.raises(InvalidSubmissionError, match="status"):
        make_submission(status="finalized")


# ---------------------------------------------------------------------------
# Draft → Submitted transition (FR-008 / DR-008)
# ---------------------------------------------------------------------------


def test_submit_draft_transitions_to_submitted() -> None:
    submission = make_submission(response="My answer.")

    submitted = submission.submit()

    assert submitted is not submission
    assert submitted.status is SubmissionStatus.SUBMITTED
    assert submitted.response == "My answer."
    assert submitted.id == submission.id
    assert submitted.learner_id == submission.learner_id
    assert submitted.activity_id == submission.activity_id
    assert submitted.submitted_at is not None
    assert submitted.submitted_at.tzinfo is not None
    # The original Draft remains untouched.
    assert submission.status is SubmissionStatus.DRAFT
    assert submission.submitted_at is None


def test_submit_records_provided_timestamp() -> None:
    submitted_at = datetime.now(UTC) - timedelta(minutes=5)

    submitted = make_submission().submit(submitted_at=submitted_at)

    assert submitted.submitted_at == submitted_at


def test_submit_requires_a_learner_response() -> None:
    with pytest.raises(InvalidSubmissionError, match="response"):
        make_submission(response="").submit()


def test_submit_rejects_blank_response() -> None:
    with pytest.raises(InvalidSubmissionError, match="response"):
        make_submission(response="   ").submit()


def test_submit_rejects_already_submitted_submission() -> None:
    submitted = make_submitted_submission()

    with pytest.raises(InvalidSubmissionTransitionError, match="submitted"):
        submitted.submit()


def test_submitted_submission_cannot_be_silently_modified() -> None:
    submission = make_submitted_submission()

    with pytest.raises(FrozenInstanceError):
        submission.response = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        submission.learner_id = uuid4()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        submission.activity_id = uuid4()  # type: ignore[misc]


def test_replace_cannot_create_invalid_submitted_submission() -> None:
    submission = make_submitted_submission()

    with pytest.raises(InvalidSubmissionError, match="response"):
        replace(submission, response="")


# ---------------------------------------------------------------------------
# Domain boundaries (DR-010 / DR-011 / DR-012 / DR-013)
# ---------------------------------------------------------------------------


def test_submission_has_no_evaluation_or_feedback_concerns() -> None:
    submission = make_submitted_submission()

    assert not hasattr(submission, "evaluation")
    assert not hasattr(submission, "feedback")
    assert not hasattr(submission, "score")


def test_submission_source_has_no_persistence_dependencies() -> None:
    for module in ("sqlalchemy", "psycopg", "redis", "sqlite3", "motor"):
        assert f"import {module}" not in SUBMISSION_SOURCE
        assert f"from {module}" not in SUBMISSION_SOURCE


def test_submission_source_has_no_framework_dependencies() -> None:
    for module in ("fastapi", "pydantic", "uvicorn"):
        assert f"import {module}" not in SUBMISSION_SOURCE
        assert f"from {module}" not in SUBMISSION_SOURCE


@pytest.mark.parametrize("forbidden", ["NIFT", "NID", "CEED"])
def test_submission_source_has_no_examination_specific_terminology(
    forbidden: str,
) -> None:
    assert forbidden.lower() not in SUBMISSION_SOURCE.lower()


def test_submission_is_usable_in_memory_without_infrastructure() -> None:
    submission = make_submitted_submission()

    assert isinstance(submission, Submission)
    assert submission.status is SubmissionStatus.SUBMITTED
