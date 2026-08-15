"""Tests for the deterministic demo evaluator (SPEC-012, UC-004)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from fablit.application import (
    ActivityNotFoundError,
    DemoEvaluator,
    build_demo_activities,
    build_demo_findings,
)
from tests.domain.helpers import make_submitted_submission


def make_evaluator() -> tuple[DemoEvaluator, UUID]:
    """Build a demo evaluator wired to the seeded demo activities."""
    activities = build_demo_activities()
    evaluator = DemoEvaluator(build_demo_findings(activities))
    return evaluator, activities[0].activity.id


def test_evaluate_produces_at_least_one_structured_finding() -> None:
    evaluator, activity_id = make_evaluator()
    evaluation = evaluator.evaluate(make_submitted_submission(activity_id=activity_id))

    assert len(evaluation.findings) >= 1
    for finding in evaluation.findings:
        assert finding.observation


def test_evaluate_emits_findings_in_fixed_order() -> None:
    evaluator, activity_id = make_evaluator()
    evaluation = evaluator.evaluate(make_submitted_submission(activity_id=activity_id))

    observations = tuple(finding.observation for finding in evaluation.findings)
    assert len(observations) == 3
    assert "dominant visual elements" in observations[0]
    assert "interact" in observations[1]
    assert "Choose two elements" in observations[2]


def test_evaluate_is_deterministic() -> None:
    evaluator, activity_id = make_evaluator()
    timestamp = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

    first = evaluator.evaluate(
        make_submitted_submission(activity_id=activity_id),
        evaluated_at=timestamp,
    )
    second = evaluator.evaluate(
        make_submitted_submission(
            activity_id=activity_id,
            response="A different response.",
        ),
        evaluated_at=timestamp,
    )

    first_observations = [finding.observation for finding in first.findings]
    second_observations = [finding.observation for finding in second.findings]
    assert first_observations == second_observations
    assert first.evaluated_at == second.evaluated_at == timestamp


def test_evaluate_references_the_submission_by_identity() -> None:
    evaluator, activity_id = make_evaluator()
    submission = make_submitted_submission(activity_id=activity_id)

    evaluation = evaluator.evaluate(submission)

    assert evaluation.submission_id == submission.id


def test_evaluate_unknown_activity_raises() -> None:
    evaluator, _ = make_evaluator()

    with pytest.raises(ActivityNotFoundError):
        evaluator.evaluate(make_submitted_submission(activity_id=uuid4()))
