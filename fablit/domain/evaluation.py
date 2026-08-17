"""Evaluation domain model (SPEC-007, SPEC-015)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from .types import InvalidEvaluationError, InvalidEvaluationFindingError


@dataclass(frozen=True)
class EvaluationFinding:
    """One structured observation or judgement about a Submission (SPEC-007).

    A Finding represents a single meaningful evaluation observation or
    judgement about the learner's work — for example a strength, a weakness,
    evidence of a demonstrated capability, or an area requiring improvement.
    It is deliberately not a score.

    The initial structure is intentionally small and extensible: a stable
    identity, the meaningful observation text, and (SPEC-015 §31) an optional
    piece of evidence explaining why the Finding was produced — a response
    excerpt, a matched concept, or another evaluator-supported reference.
    The evidence grounds the Finding in the learner's actual response so
    evaluation is response-aware rather than predefined (§29–30).

    Attributes:
        observation: The meaningful observation or judgement about the
            learner's work. Must be non-empty.
        id: The stable, unique domain identity. Generated when omitted.
        evidence: Optional evidence supporting the Finding (a response
            excerpt or matched concept). Must be a non-blank string when
            present; ``None`` when the Finding carries no evidence.

    Raises:
        InvalidEvaluationFindingError: When the identity is invalid, the
            observation is empty/blank, or the evidence is present but
            empty/whitespace-only.
    """

    observation: str
    id: UUID = field(default_factory=uuid4)
    evidence: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidEvaluationFindingError(
                f"evaluation finding must have a valid identity (got {self.id!r})"
            )
        if not isinstance(self.observation, str) or not self.observation.strip():
            raise InvalidEvaluationFindingError(
                "an evaluation finding must contain a meaningful observation"
                f" (got {self.observation!r})"
            )
        if self.evidence is not None and (
            not isinstance(self.evidence, str) or not self.evidence.strip()
        ):
            raise InvalidEvaluationFindingError(
                "evaluation finding evidence must be a non-blank string when present"
                f" (got {self.evidence!r})"
            )


@dataclass(frozen=True)
class Evaluation:
    """The structured interpretation of a Submission (SPEC-007).

    An Evaluation records the findings about a learner's Submission: it
    references the Submission by its stable identity (SPEC-006) and contains
    one or more structured Evaluation Findings. It does not duplicate the
    Submission, does not require a numerical score, and does not contain
    Feedback — those concepts remain outside this model.

    An Evaluation is immutable after creation. If a Submission requires
    another evaluation, a new Evaluation shall be created rather than
    mutating an existing one.    Attributes:
        submission_id: The stable identity (SPEC-006) of the Submission being
            evaluated.
        findings: The structured findings about the Submission (at least one,
            each a valid EvaluationFinding).
        id: The stable, unique domain identity. Generated when omitted.
        evaluated_at: The timezone-aware time the evaluation occurred.

    Raises:
        InvalidEvaluationError: When required domain information is missing or
            invalid (missing/invalid identity, submission reference, empty or
            invalid findings collection, or a missing/naive timestamp).
    """

    submission_id: UUID
    findings: tuple[EvaluationFinding, ...]
    evaluated_at: datetime
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidEvaluationError(
                f"evaluation must have a valid identity (got {self.id!r})"
            )
        if not isinstance(self.submission_id, UUID):
            raise InvalidEvaluationError(
                "evaluation must reference a valid submission identity"
                f" (got {self.submission_id!r})"
            )
        if not isinstance(self.findings, tuple):
            raise InvalidEvaluationError(
                "evaluation findings must be provided as a tuple"
                f" (got {self.findings!r})"
            )
        if not self.findings:
            raise InvalidEvaluationError(
                "an evaluation must contain at least one finding"
            )
        for finding in self.findings:
            if not isinstance(finding, EvaluationFinding):
                raise InvalidEvaluationError(
                    "evaluation findings must be EvaluationFinding instances"
                    f" (got {finding!r})"
                )
        if not isinstance(self.evaluated_at, datetime):
            raise InvalidEvaluationError("an evaluation must record when it occurred")
        if self.evaluated_at.tzinfo is None:
            raise InvalidEvaluationError("evaluation timestamp must be timezone-aware")
