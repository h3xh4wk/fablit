"""Tests for the deterministic response-aware demo evaluator
(SPEC-012 UC-004, SPEC-015).

SPEC-015 extends the demo evaluator so that, for activities that depend on a
visual stimulus, Findings are grounded in the learner's actual response and
different responses produce different Findings (§69); empty and very short
responses are handled explicitly without fabricating a positive Finding
(§62–63).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from fablit.application import (
    ActivityNotFoundError,
    DemoEvaluator,
    build_demo_activities,
    build_demo_activity_map,
)
from fablit.domain import AssessmentActivity, StimulusInstance
from tests.domain.helpers import (
    make_activity,
    make_stimulus,
    make_submission,
    make_submitted_submission,
)


def make_evaluator() -> tuple[DemoEvaluator, UUID]:
    """Build a demo evaluator wired to the seeded demo activities."""
    activities = build_demo_activities()
    evaluator = DemoEvaluator(build_demo_activity_map(activities))
    return evaluator, activities[0].activity.id


def make_context(
    activity: AssessmentActivity,
) -> tuple[AssessmentActivity, StimulusInstance]:
    """Return the activity together with a stimulus resolved for it."""
    return activity, make_stimulus(activity_id=activity.id)


def test_evaluate_produces_at_least_one_structured_finding() -> None:
    evaluator, activity_id = make_evaluator()
    activity, stimulus = make_context(make_activity(id=activity_id))
    evaluation = evaluator.evaluate(
        make_submitted_submission(activity_id=activity_id),
        activity=activity,
        stimulus=stimulus,
    )

    assert len(evaluation.findings) >= 1
    for finding in evaluation.findings:
        assert finding.observation


def test_evaluate_receives_activity_and_stimulus() -> None:
    """The evaluator must receive the activity and the actual stimulus (§27, §66)."""
    evaluator, activity_id = make_evaluator()
    activity, stimulus = make_context(make_activity(id=activity_id))

    evaluation = evaluator.evaluate(
        make_submitted_submission(
            activity_id=activity_id,
            response="The contrast between the subject and the background is strong.",
        ),
        activity=activity,
        stimulus=stimulus,
    )

    assert evaluation.submission_id is not None
    assert len(evaluation.findings) >= 1


def test_evaluate_grounds_finding_in_matched_concept() -> None:
    evaluator, activity_id = make_evaluator()
    activity, stimulus = make_context(make_activity(id=activity_id))

    evaluation = evaluator.evaluate(
        make_submitted_submission(
            activity_id=activity_id,
            response=(
                "The contrast between the subject and the dark background stands out."
            ),
        ),
        activity=activity,
        stimulus=stimulus,
    )

    assert any(finding.evidence == "contrast" for finding in evaluation.findings)
    assert any("contrast" in finding.observation for finding in evaluation.findings)


def test_different_responses_produce_different_findings() -> None:
    """Acceptance criterion: evaluation is not predefined regardless of input (§69)."""
    evaluator, activity_id = make_evaluator()
    activity, stimulus = make_context(make_activity(id=activity_id))

    contrast = evaluator.evaluate(
        make_submitted_submission(
            activity_id=activity_id,
            response="The contrast between the subject and the background is strong.",
        ),
        activity=activity,
        stimulus=stimulus,
    )
    negative_space = evaluator.evaluate(
        make_submitted_submission(
            activity_id=activity_id,
            response=(
                "The model stands out because she is surrounded "
                "by a lot of empty space."
            ),
        ),
        activity=activity,
        stimulus=stimulus,
    )

    contrast_observations = tuple(f.observation for f in contrast.findings)
    negative_space_observations = tuple(f.observation for f in negative_space.findings)
    assert contrast_observations != negative_space_observations
    assert any("contrast" in observation for observation in contrast_observations)
    assert any(
        "negative space" in observation or "empty space" in observation
        for observation in negative_space_observations
    )


def test_evaluate_keeps_at_least_one_guidance_finding_when_no_concept_matches() -> None:
    evaluator, activity_id = make_evaluator()
    activity, stimulus = make_context(make_activity(id=activity_id))

    evaluation = evaluator.evaluate(
        make_submitted_submission(
            activity_id=activity_id,
            response=(
                "I have described the image in my own words "
                "without using any of the usual terms."
            ),
        ),
        activity=activity,
        stimulus=stimulus,
    )

    observations = tuple(f.observation for f in evaluation.findings)
    assert len(observations) >= 1
    # The noticed finding must not fabricate a positive (§61).
    assert not any("good job" in observation.lower() for observation in observations)


def test_evaluate_does_not_fabricate_positive_for_empty_response() -> None:
    evaluator, activity_id = make_evaluator()
    activity, stimulus = make_context(make_activity(id=activity_id))

    # A Submitted Submission must be non-empty, so the evaluator's explicit
    # empty-response handling is exercised with a Draft carrying no response.
    evaluation = evaluator.evaluate(
        make_submission(activity_id=activity_id, response=""),
        activity=activity,
        stimulus=stimulus,
    )

    assert len(evaluation.findings) >= 1
    observation = evaluation.findings[0].observation
    assert "add an observation" in observation.lower()
    assert "good job" not in observation.lower()


def test_evaluate_encourages_elaboration_for_very_short_response() -> None:
    evaluator, activity_id = make_evaluator()
    activity, stimulus = make_context(make_activity(id=activity_id))

    evaluation = evaluator.evaluate(
        make_submitted_submission(activity_id=activity_id, response="A figure."),
        activity=activity,
        stimulus=stimulus,
    )

    observations = tuple(f.observation for f in evaluation.findings)
    assert any("stand out" in observation.lower() for observation in observations)


def test_evaluate_without_stimulus_uses_predefined_findings() -> None:
    """Activities that do not depend on a stimulus keep predefined findings."""
    evaluator, activity_id = make_evaluator()
    activity = make_activity(id=activity_id)

    evaluation = evaluator.evaluate(
        make_submitted_submission(activity_id=activity_id, response="Anything."),
        activity=activity,
        stimulus=None,
    )

    observations = tuple(f.observation for f in evaluation.findings)
    assert len(observations) == 3
    assert "dominant visual elements" in observations[0]


def test_evaluate_is_deterministic() -> None:
    evaluator, activity_id = make_evaluator()
    activity, stimulus = make_context(make_activity(id=activity_id))
    timestamp = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

    first = evaluator.evaluate(
        make_submitted_submission(
            activity_id=activity_id,
            response="The contrast is the strongest part of the composition.",
        ),
        activity=activity,
        stimulus=stimulus,
        evaluated_at=timestamp,
    )
    second = evaluator.evaluate(
        make_submitted_submission(
            activity_id=activity_id,
            response="The contrast is the strongest part of the composition.",
        ),
        activity=activity,
        stimulus=stimulus,
        evaluated_at=timestamp,
    )

    first_observations = [finding.observation for finding in first.findings]
    second_observations = [finding.observation for finding in second.findings]
    assert first_observations == second_observations
    assert first.evaluated_at == second.evaluated_at == timestamp


def test_evaluate_references_the_submission_by_identity() -> None:
    evaluator, activity_id = make_evaluator()
    activity, stimulus = make_context(make_activity(id=activity_id))
    submission = make_submitted_submission(activity_id=activity_id)

    evaluation = evaluator.evaluate(
        submission,
        activity=activity,
        stimulus=stimulus,
    )

    assert evaluation.submission_id == submission.id


def test_evaluate_unknown_activity_raises() -> None:
    evaluator, _ = make_evaluator()
    activity, stimulus = make_context(make_activity())

    with pytest.raises(ActivityNotFoundError):
        evaluator.evaluate(
            make_submitted_submission(activity_id=activity.id),
            activity=activity,
            stimulus=stimulus,
        )
