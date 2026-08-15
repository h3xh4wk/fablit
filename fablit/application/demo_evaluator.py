"""Deterministic demo evaluation for the first vertical slice (SPEC-012).

UC-004: the demo evaluator produces a known, predefined Evaluation for each
seeded demo activity. It requires no AI provider, no external API, and no
asynchronous workers; the same activity + response combination always yields
the same Findings, which makes the vertical slice suitable for automated
tests. The exact structure conforms to the existing Evaluation domain model.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from fablit.domain import Evaluation, EvaluationFinding, Submission

from .errors import ActivityNotFoundError


class DemoEvaluator:
    """Predefined deterministic evaluator for the demo activities."""

    def __init__(self, findings: Mapping[UUID, tuple[str, str, str]]) -> None:
        """Store the predefined (strength, improvement, next step) per activity."""
        self._findings: dict[UUID, tuple[str, str, str]] = dict(findings)

    def evaluate(
        self,
        submission: Submission,
        *,
        evaluated_at: datetime | None = None,
    ) -> Evaluation:
        """Produce the deterministic Evaluation for a demo Submission.

        The predefined demo findings are emitted as three Findings in a fixed
        order: strength, improvement, then next step. Feedback preparation
        relies on that order (see ``PracticeApplication``).
        """
        predefined = self._findings.get(submission.activity_id)
        if predefined is None:
            raise ActivityNotFoundError("Activity not found.")
        strength, improvement, next_step = predefined
        findings = (
            EvaluationFinding(observation=strength),
            EvaluationFinding(observation=improvement),
            EvaluationFinding(observation=next_step),
        )
        timestamp = evaluated_at if evaluated_at is not None else datetime.now(UTC)
        return Evaluation(
            submission_id=submission.id,
            findings=findings,
            evaluated_at=timestamp,
        )
