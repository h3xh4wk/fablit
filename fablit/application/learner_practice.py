"""Learner-requested private practice generation (SPEC-044 §5.2, §6.2, §8).

This module owns the bounded, learner-initiated generation workflow:

- a short request is validated and bounded before any provider call;
- optional context is drawn only from the current learner's own completed
  practice titles and areas, and only when the learner opts in;
- generation goes through a provider-neutral port, and the untrusted result is
  validated against the existing SPEC-029 content contract and SPEC-030
  feedback rules before it is offered;
- a validated practice is persisted privately under the learner's opaque
  identity and reconstructed exactly on return visits.

A generated practice is explicit learner-requested content: it never enters
the shared curated library, never becomes visible to another learner, and is
not scored, graded, ranked, or treated as evidence of ability.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from typing import Any, Protocol, runtime_checkable
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fablit.domain import ActivityStatus, ActivityType, AssessmentActivity

from .authoring import (
    PracticeAuthoringBrief,
    candidate_from_provider_output,
)
from .demo_data import (
    PRACTICE_CAPABILITY_ARTICULATE,
    PRACTICE_CAPABILITY_INTERPRET,
    PRACTICE_CAPABILITY_OBSERVE,
    PRACTICE_CAPABILITY_REFLECT,
)
from .errors import (
    GeneratedPracticeValidationError,
    InvalidLearnerPracticeRequestError,
    LearnerPracticeGenerationError,
)
from .practice_modes import PracticeMode
from .store import DemoActivity, PracticeContentContract

logger = logging.getLogger(__name__)

#: The longest free-text request the composer accepts. A learner request is a
#: short intent, not an authoring brief.
MAX_REQUEST_CHARS = 600
MAX_RESPONSE_FORM_CHARS = 200
MAX_EXAM_CONTEXT_CHARS = 200
MAX_HISTORY_ITEMS = 5

DEFAULT_RESPONSE_FORM = "A short written response"
GENERATION_UNAVAILABLE_MESSAGE = (
    "Making a practice is temporarily unavailable. Please try again shortly."
)
VALIDATION_FAILURE_MESSAGE = (
    "We couldn't make a practice from that request. Try describing what you "
    "want to practise in a little more detail."
)


class PracticeArea(StrEnum):
    """Learner-requestable practice areas (SPEC-044 §6.2)."""

    CREATIVE_ABILITY = "creative-ability"
    APTITUDE = "aptitude"
    ENGLISH = "english"
    VISUAL_ANALYSIS = "visual-analysis"
    COMMUNICATION = "communication"
    OTHER = "other"


PRACTICE_AREA_LABELS: dict[PracticeArea, str] = {
    PracticeArea.CREATIVE_ABILITY: "Creative ability",
    PracticeArea.APTITUDE: "Aptitude",
    PracticeArea.ENGLISH: "English",
    PracticeArea.VISUAL_ANALYSIS: "Visual analysis",
    PracticeArea.COMMUNICATION: "Communication",
    PracticeArea.OTHER: "Something else",
}


class ChallengePreference(StrEnum):
    """Plain-language challenge preferences (SPEC-044 §6.2)."""

    INTRODUCTORY = "introductory"
    FAMILIAR = "familiar"
    MORE_CHALLENGING = "more-challenging"


CHALLENGE_LABELS: dict[ChallengePreference, str] = {
    ChallengePreference.INTRODUCTORY: "Introductory",
    ChallengePreference.FAMILIAR: "Familiar",
    ChallengePreference.MORE_CHALLENGING: "More challenging",
}

#: The internal thinking lens used for generation. The learner-facing practice
#: area is carried separately; the lens only anchors the SPEC-029 contract
#: guidance and is never shown as progress or assessment.
_AREA_LENS: dict[PracticeArea, str] = {
    PracticeArea.CREATIVE_ABILITY: PRACTICE_CAPABILITY_INTERPRET,
    PracticeArea.APTITUDE: PRACTICE_CAPABILITY_INTERPRET,
    PracticeArea.ENGLISH: PRACTICE_CAPABILITY_ARTICULATE,
    PracticeArea.VISUAL_ANALYSIS: PRACTICE_CAPABILITY_OBSERVE,
    PracticeArea.COMMUNICATION: PRACTICE_CAPABILITY_ARTICULATE,
    PracticeArea.OTHER: PRACTICE_CAPABILITY_REFLECT,
}


@dataclass(frozen=True)
class PracticeRequest:
    """One validated, learner-authored practice request (SPEC-044 §6.2)."""

    learner_id: UUID
    text: str
    area: PracticeArea
    response_form: str
    challenge: ChallengePreference
    include_history: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    token: UUID = field(default_factory=uuid4)
    examination_context: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.learner_id, UUID):
            raise InvalidLearnerPracticeRequestError(
                "practice request learner identity must be a UUID "
                f"(got {self.learner_id!r})"
            )
        if not isinstance(self.token, UUID):
            raise InvalidLearnerPracticeRequestError(
                f"practice request token must be a UUID (got {self.token!r})"
            )
        if not isinstance(self.include_history, bool):
            raise InvalidLearnerPracticeRequestError(
                "practice request include_history must be a boolean "
                f"(got {self.include_history!r})"
            )
        if not isinstance(self.text, str) or not self.text.strip():
            raise InvalidLearnerPracticeRequestError(
                "Write what you would like to practise."
            )
        if len(self.text.strip()) > MAX_REQUEST_CHARS:
            raise InvalidLearnerPracticeRequestError(
                f"Keep your request to {MAX_REQUEST_CHARS} characters or fewer."
            )
        if not isinstance(self.area, PracticeArea):
            raise InvalidLearnerPracticeRequestError(
                f"Choose a supported practice area (got {self.area!r})."
            )
        if not isinstance(self.challenge, ChallengePreference):
            raise InvalidLearnerPracticeRequestError(
                f"Choose a supported challenge preference (got {self.challenge!r})."
            )
        if not isinstance(self.response_form, str) or not self.response_form.strip():
            raise InvalidLearnerPracticeRequestError(
                "Choose the kind of response you want to make."
            )
        if len(self.response_form.strip()) > MAX_RESPONSE_FORM_CHARS:
            raise InvalidLearnerPracticeRequestError(
                "Keep the response form to "
                f"{MAX_RESPONSE_FORM_CHARS} characters or fewer."
            )
        if self.examination_context is not None:
            if (
                not isinstance(self.examination_context, str)
                or not self.examination_context.strip()
            ):
                raise InvalidLearnerPracticeRequestError(
                    "Examination context must be non-blank when provided."
                )
            if len(self.examination_context.strip()) > MAX_EXAM_CONTEXT_CHARS:
                raise InvalidLearnerPracticeRequestError(
                    "Keep the examination context to "
                    f"{MAX_EXAM_CONTEXT_CHARS} characters or fewer."
                )
        if not isinstance(self.created_at, datetime):
            raise InvalidLearnerPracticeRequestError(
                "Practice request must record when it was made."
            )
        if self.created_at.tzinfo is None:
            raise InvalidLearnerPracticeRequestError(
                "Practice request timestamp must be timezone-aware."
            )


@dataclass(frozen=True)
class HistoryContext:
    """A minimal, relevant slice of the current learner's own history.

    Only completed practice titles and their internal capability lenses are
    carried. Full responses, reflections, artifacts, and the histories of
    other learners are never included (SPEC-044 §7).
    """

    recent_titles: tuple[str, ...] = ()
    recent_areas: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("recent_titles", "recent_areas"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or len(values) > MAX_HISTORY_ITEMS:
                raise InvalidLearnerPracticeRequestError(
                    f"history context {name!r} must be a bounded tuple"
                )
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    raise InvalidLearnerPracticeRequestError(
                        f"history context {name!r} must contain non-blank text"
                    )

    @property
    def is_empty(self) -> bool:
        return not self.recent_titles and not self.recent_areas


@dataclass(frozen=True)
class LearnerPracticeGenerationRequest:
    """What the generation port is asked for.

    Learner identity is deliberately absent: the provider receives only the
    learner's explicit request and the optional history context the workflow
    selected.
    """

    request: PracticeRequest
    history: HistoryContext

    def as_payload(self) -> dict[str, Any]:
        history = self.history if self.request.include_history else HistoryContext()
        return {
            "request_text": self.request.text.strip(),
            "practice_area": self.request.area.value,
            "practice_area_label": PRACTICE_AREA_LABELS[self.request.area],
            "examination_context": (
                self.request.examination_context.strip()
                if self.request.examination_context is not None
                else None
            ),
            "response_form": self.request.response_form.strip(),
            "challenge": self.request.challenge.value,
            "history": {
                "recent_titles": list(history.recent_titles),
                "recent_areas": list(history.recent_areas),
            },
        }


@dataclass(frozen=True)
class LearnerPracticeGenerationResult:
    """Untrusted provider output plus safe provenance (SPEC-044 §8.1)."""

    candidate_data: Mapping[str, Any] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_data, Mapping):
            raise LearnerPracticeGenerationError(
                "generation result candidate data must be a mapping"
            )
        for name in ("provider", "model"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise LearnerPracticeGenerationError(
                    f"generation result {name!r} must be non-blank text"
                )
        if (
            not isinstance(self.generated_at, datetime)
            or self.generated_at.tzinfo is None
        ):
            raise LearnerPracticeGenerationError(
                "generation result timestamp must be timezone-aware"
            )


@runtime_checkable
class LearnerPracticeGenerator(Protocol):
    """Provider-neutral port for one bounded learner-requested practice."""

    @property
    def provider_id(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    def generate(
        self, request: LearnerPracticeGenerationRequest
    ) -> LearnerPracticeGenerationResult:
        """Generate one structured candidate, or raise a safe application error."""
        ...


class FakeLearnerPracticeGenerator:
    """Deterministic provider for tests and local workflows (no network)."""

    def __init__(
        self,
        candidate_data: Mapping[str, Any] | None = None,
        *,
        provider: str = "fake-learner-generator",
        model: str = "fake-model",
        generated_at: datetime | None = None,
        error: Exception | None = None,
    ) -> None:
        self._candidate_data = (
            dict(candidate_data) if candidate_data is not None else None
        )
        self._provider = provider
        self._model = model
        self._generated_at = generated_at or datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
        self._error = error
        self.calls: list[LearnerPracticeGenerationRequest] = []

    @property
    def provider_id(self) -> str:
        return self._provider

    @property
    def model_id(self) -> str:
        return self._model

    def generate(
        self, request: LearnerPracticeGenerationRequest
    ) -> LearnerPracticeGenerationResult:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        data = (
            dict(self._candidate_data)
            if self._candidate_data is not None
            else default_candidate_data(request)
        )
        return LearnerPracticeGenerationResult(
            candidate_data=data,
            provider=self._provider,
            model=self._model,
            generated_at=self._generated_at,
        )


def default_candidate_data(
    request: LearnerPracticeGenerationRequest,
) -> dict[str, Any]:
    """Build a valid deterministic candidate from the learner's request."""
    area = PRACTICE_AREA_LABELS[request.request.area].lower()
    task = request.request.text.strip()
    return {
        "title": f"A focused practice: {area}",
        "description": (
            "A short practice made for your request. It asks you to work through "
            "one concrete idea and explain the evidence behind it."
        ),
        "contract": {
            "purpose": f"Practise {area} through one focused, evidence-based response.",
            "task": task,
            "expected_thinking": (
                "Move from a specific observation or example to a reasoned response, "
                "rather than relying on a general impression."
            ),
            "response_contract": request.request.response_form.strip(),
            "evaluation_intent": (
                "Look for a specific, relevant response grounded in the learner's "
                "own observation or example."
            ),
            "feedback_intent": (
                "Name one concrete strength, explain why it matters, and point to "
                "one useful next move."
            ),
            "reflection_intent": (
                "Notice which part of the task felt most useful and what you would "
                "try differently in another attempt."
            ),
            "continuation_intent": (
                "Carry the same thinking move into a related subject or example."
            ),
        },
    }


@dataclass(frozen=True)
class GeneratedPracticeRecord:
    """A validated private practice generated for one learner (SPEC-044 §9)."""

    practice_id: UUID
    learner_id: UUID
    request_token: UUID
    title: str
    description: str
    contract: PracticeContentContract
    area: PracticeArea
    challenge: ChallengePreference
    response_form: str
    primary_capability: str
    used_history: bool
    provider: str
    model: str
    generated_at: datetime
    created_at: datetime
    examination_context: str | None = None

    def __post_init__(self) -> None:
        for name in ("practice_id", "learner_id", "request_token"):
            value = getattr(self, name)
            if not isinstance(value, UUID):
                raise GeneratedPracticeValidationError(
                    f"generated practice {name!r} must be a UUID"
                )
        for name in ("title", "description", "response_form", "primary_capability"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise GeneratedPracticeValidationError(
                    f"generated practice {name!r} must be non-blank text"
                )
        if not isinstance(self.contract, PracticeContentContract):
            raise GeneratedPracticeValidationError(
                "generated practice must carry a complete SPEC-029 contract"
            )
        if not isinstance(self.area, PracticeArea):
            raise GeneratedPracticeValidationError(
                "generated practice must carry a supported practice area"
            )
        if not isinstance(self.challenge, ChallengePreference):
            raise GeneratedPracticeValidationError(
                "generated practice must carry a supported challenge preference"
            )
        for name in ("provider", "model"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise GeneratedPracticeValidationError(
                    f"generated practice {name!r} must be non-blank text"
                )
        for name in ("generated_at", "created_at"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise GeneratedPracticeValidationError(
                    f"generated practice {name!r} must be timezone-aware"
                )
        if self.examination_context is not None and (
            not isinstance(self.examination_context, str)
            or not self.examination_context.strip()
        ):
            raise GeneratedPracticeValidationError(
                "generated practice examination context must be non-blank when provided"
            )


class GeneratedPracticeRepository(ABC):
    """Persistence port for private, learner-requested practices."""

    @abstractmethod
    def save(self, record: GeneratedPracticeRecord) -> GeneratedPracticeRecord:
        """Persist one record, returning the existing record on a retry."""

    @abstractmethod
    def get(
        self, learner_id: UUID, practice_id: UUID
    ) -> GeneratedPracticeRecord | None:
        """Return the learner's own record, or ``None``."""

    @abstractmethod
    def list_for_learner(self, learner_id: UUID) -> tuple[GeneratedPracticeRecord, ...]:
        """Return the learner's records, newest first."""


class InMemoryGeneratedPracticeRepository(GeneratedPracticeRepository):
    """Deterministic in-memory store for tests and local development."""

    def __init__(self) -> None:
        self._records: dict[UUID, GeneratedPracticeRecord] = {}
        self._learner_records: dict[UUID, list[UUID]] = {}
        self._lock = Lock()

    def save(self, record: GeneratedPracticeRecord) -> GeneratedPracticeRecord:
        if not isinstance(record, GeneratedPracticeRecord):
            raise ValueError(
                "generated practice repository only accepts GeneratedPracticeRecord"
            )
        with self._lock:
            existing = self._records.get(record.practice_id)
            if existing is not None:
                return existing
            self._records[record.practice_id] = record
            self._learner_records.setdefault(record.learner_id, []).append(
                record.practice_id
            )
            return record

    def get(
        self, learner_id: UUID, practice_id: UUID
    ) -> GeneratedPracticeRecord | None:
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            return None
        with self._lock:
            record = self._records.get(practice_id)
        if record is None or record.learner_id != learner_id:
            return None
        return record

    def list_for_learner(self, learner_id: UUID) -> tuple[GeneratedPracticeRecord, ...]:
        if not isinstance(learner_id, UUID):
            return ()
        with self._lock:
            record_ids = tuple(self._learner_records.get(learner_id, ()))
            records = [
                self._records[record_id]
                for record_id in record_ids
                if record_id in self._records
            ]
        return tuple(
            sorted(
                records,
                key=lambda record: (record.created_at, str(record.practice_id)),
                reverse=True,
            )
        )


def new_request_token() -> UUID:
    """Return a fresh idempotency token for one request composer render."""
    return uuid4()


def practice_id_for(learner_id: UUID, token: UUID) -> UUID:
    """Derive a stable private practice identity from the learner and token."""
    return uuid5(
        NAMESPACE_URL,
        f"fablit:learner-practice:{learner_id}:{token}",
    )


def _brief_for(
    request: PracticeRequest,
    history: HistoryContext,
) -> PracticeAuthoringBrief:
    context_lines = [
        "This practice was requested privately by one learner and will not be",
        "published to the shared library. Do not infer ability, motivation, or",
        "future performance from the request or from any history context.",
    ]
    if history.recent_titles:
        context_lines.append(
            "Recent practice titles: " + "; ".join(history.recent_titles)
        )
    if history.recent_areas:
        context_lines.append(
            "Recent practice areas: " + "; ".join(history.recent_areas)
        )
    return PracticeAuthoringBrief(
        practice_area=PRACTICE_AREA_LABELS[request.area],
        practice_purpose=request.text.strip(),
        task=request.text.strip(),
        response_form=request.response_form.strip(),
        primary_capability=_AREA_LENS[request.area],
        practice_mode=PracticeMode.FULL_PRACTICE,
        learner_context=" ".join(context_lines),
        examination_context=(
            request.examination_context.strip()
            if request.examination_context is not None
            else None
        ),
        constraints=(f"Challenge preference: {CHALLENGE_LABELS[request.challenge]}",),
    )


def generate_private_practice(
    repository: GeneratedPracticeRepository,
    generator: LearnerPracticeGenerator,
    *,
    request: PracticeRequest,
    history: HistoryContext,
    now: datetime | None = None,
) -> GeneratedPracticeRecord:
    """Generate, validate, and privately persist one requested practice.

    A repeated request with the same token returns the already-persisted
    record without calling the provider again. Invalid provider output never
    reaches persistence or the learner.
    """
    practice_id = practice_id_for(request.learner_id, request.token)
    existing = repository.get(request.learner_id, practice_id)
    if existing is not None:
        return existing

    effective_history = history if request.include_history else HistoryContext()
    brief = _brief_for(request, effective_history)
    try:
        result = generator.generate(
            LearnerPracticeGenerationRequest(request=request, history=effective_history)
        )
    except LearnerPracticeGenerationError:
        raise
    except Exception as exc:
        logger.exception("learner practice generator failed")
        raise LearnerPracticeGenerationError(GENERATION_UNAVAILABLE_MESSAGE) from exc

    candidate = candidate_from_provider_output(
        result.candidate_data,
        brief,
        provider=result.provider,
        model=result.model,
        generated_at=result.generated_at,
    )
    validation = candidate.validation
    contract = candidate.contract
    if (
        not validation.is_approvable
        or contract is None
        or not candidate.title.strip()
        or not candidate.description.strip()
    ):
        logger.warning(
            "generated practice failed validation",
            extra={
                "structural_errors": list(validation.structural_errors),
                "feedback_errors": list(validation.feedback_errors),
            },
        )
        raise GeneratedPracticeValidationError(VALIDATION_FAILURE_MESSAGE)

    created_at = now or datetime.now(UTC)
    record = GeneratedPracticeRecord(
        practice_id=practice_id,
        learner_id=request.learner_id,
        request_token=request.token,
        title=candidate.title.strip(),
        description=candidate.description.strip(),
        contract=contract,
        area=request.area,
        challenge=request.challenge,
        response_form=request.response_form.strip(),
        primary_capability=brief.primary_capability,
        used_history=not effective_history.is_empty,
        provider=result.provider,
        model=result.model,
        generated_at=result.generated_at,
        created_at=created_at,
        examination_context=(
            request.examination_context.strip()
            if request.examination_context is not None
            else None
        ),
    )
    return repository.save(record)


def build_generated_activity(record: GeneratedPracticeRecord) -> DemoActivity:
    """Represent a generated practice as the existing learner activity.

    Generated practices reuse the learner-facing ``DemoActivity`` /
    ``AssessmentActivity`` representation and the ordinary practice journey.
    """
    contract = record.contract
    return DemoActivity(
        activity=AssessmentActivity(
            activity_type=ActivityType.WRITTEN_RESPONSE,
            instructions=contract.task.strip(),
            position=0,
            id=record.practice_id,
            status=ActivityStatus.ACTIVE,
        ),
        title=record.title,
        description=record.description,
        strength=f"You worked through this practice's task: {contract.task}",
        improvement=(
            "Check your response against what the task asks for: "
            f"{contract.response_contract}"
        ),
        next_step=f"Take another pass with the purpose in mind: {contract.purpose}",
        content_contract=contract,
        primary_capability=record.primary_capability,
    )


@dataclass(frozen=True)
class RequestedPracticeSummary:
    """One private requested practice in the learner's request/history list."""

    practice_id: UUID
    title: str
    description: str
    area_label: str
    created_at: datetime
    is_completed: bool


@dataclass(frozen=True)
class GeneratedPracticePreview:
    """The brief shown before a learner chooses to begin a requested practice."""

    practice_id: UUID
    title: str
    description: str
    task: str
    purpose: str
    expected_thinking: str
    response_contract: str
    area_label: str
    challenge_label: str
    response_form: str
    examination_context: str | None
    created_at: datetime
    is_completed: bool
