"""Deterministic response-aware evaluation for the demo vertical slice
(SPEC-012, SPEC-015).

UC-004: the demo evaluator produces a known, deterministic Evaluation for each
seeded demo activity. It requires no AI provider, no external API, and no
asynchronous workers.

SPEC-015 extends it: for activities that depend on a visual stimulus, the
evaluator grounds its Findings in the learner's actual response by matching
known concepts (§29–31), so different responses produce different Findings
(§69). Empty or very short responses are handled explicitly without
fabricating a positive Finding (§62–63). Activities that do not depend on a
stimulus keep the predefined demo Findings. The exact structure conforms to
the existing Evaluation domain model, with the matched concept retained as
each Finding's evidence (SPEC-015 §31).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from fablit.domain import (
    AssessmentActivity,
    Evaluation,
    EvaluationFinding,
    StimulusInstance,
    Submission,
)

from .errors import ActivityNotFoundError
from .store import DemoActivity

#: A response shorter than this many words is treated as a very short
#: response that needs encouragement to elaborate (SPEC-015 §63).
_SHORT_RESPONSE_WORDS = 4


class Evaluator(Protocol):
    """Contract for an evaluator that produces a response-aware Evaluation (§28, §60).

    The evaluator receives the activity, the actual stimulus, and the
    learner's Submission (which carries the response) so it never evaluates
    the response in isolation when the activity depends on the stimulus
    (§27). Rule-based, deterministic, AI-assisted, and hybrid evaluators can
    implement this contract; SPEC-015 does not mandate a technology (§28).
    """

    def evaluate(
        self,
        submission: Submission,
        *,
        activity: AssessmentActivity,
        stimulus: StimulusInstance | None = None,
        evaluated_at: datetime | None = None,
    ) -> Evaluation:
        """Produce an Evaluation with at least one structured Finding."""
        ...


class DemoEvaluator:
    """Deterministic, response-aware evaluator for the demo activities."""

    def __init__(self, activities: Mapping[UUID, DemoActivity]) -> None:
        """Store the demo activity content keyed by activity identity."""
        self._activities = dict(activities)

    def evaluate(
        self,
        submission: Submission,
        *,
        activity: AssessmentActivity,
        stimulus: StimulusInstance | None = None,
        evaluated_at: datetime | None = None,
    ) -> Evaluation:
        """Produce the deterministic Evaluation for a demo Submission.

        The evaluator must receive the activity (its stimulus context defines
        the learning context) and, for stimulus-dependent activities, the
        stimulus shown to the learner (SPEC-015 §27, §66).
        """
        item = self._activities.get(activity.id)
        if item is None:
            raise ActivityNotFoundError("Activity not found.")
        findings = self._findings_for(submission.response, item, stimulus)
        timestamp = evaluated_at if evaluated_at is not None else datetime.now(UTC)
        return Evaluation(
            submission_id=submission.id,
            findings=findings,
            evaluated_at=timestamp,
        )

    def _findings_for(
        self,
        response: str,
        item: DemoActivity,
        stimulus: StimulusInstance | None,
    ) -> tuple[EvaluationFinding, ...]:
        """Choose response-aware Findings for stimulus activities.

        Activities without concepts (or without a stimulus) keep predefined
        Findings.
        """
        if item.concepts and stimulus is not None:
            return self._response_aware_findings(response, item)
        return self._predefined_findings(item)

    def _predefined_findings(self, item: DemoActivity) -> tuple[EvaluationFinding, ...]:
        """Return the predefined (strength, improvement, next step) Findings."""
        return (
            EvaluationFinding(observation=item.strength),
            EvaluationFinding(observation=item.improvement),
            EvaluationFinding(observation=item.next_step),
        )

    def _response_aware_findings(
        self,
        response: str,
        item: DemoActivity,
    ) -> tuple[EvaluationFinding, ...]:
        """Ground Findings in the learner's response without fabricating positives.

        Matched concepts become Findings with the matched keyword retained as
        evidence; at most two are emitted so the learner is not overwhelmed
        (§32). Empty responses produce an explicit prompt to add an
        observation (§62); very short responses produce a finding that
        encourages elaboration (§63); responses with no matched concept get an
        honest guidance finding rather than a fabricated positive (§61).
        """
        stripped = response.strip()
        lowered = stripped.lower()
        if not stripped:
            return (
                EvaluationFinding(
                    observation=(
                        "Add an observation about what you see in the image "
                        "before continuing."
                    )
                ),
            )
        if len(stripped.split()) < _SHORT_RESPONSE_WORDS:
            return (
                EvaluationFinding(
                    observation=(
                        "You've started your observation. What specifically makes "
                        "that part of the image stand out to you?"
                    ),
                    evidence=stripped[:120],
                ),
                EvaluationFinding(observation=item.next_step),
            )
        matched = tuple(
            EvaluationFinding(observation=concept.finding, evidence=concept.keyword)
            for concept in item.concepts
            if concept.keyword in lowered
        )[:2]
        if matched:
            return matched + (
                EvaluationFinding(observation=item.improvement),
                EvaluationFinding(observation=item.next_step),
            )
        return (
            EvaluationFinding(
                observation=(
                    "You've shared your own description of the image. Try to name "
                    "the specific visual quality that makes it stand out."
                )
            ),
            EvaluationFinding(observation=item.improvement),
            EvaluationFinding(observation=item.next_step),
        )
