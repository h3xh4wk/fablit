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
import math
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from threading import Event, Lock, Thread
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
    LearnerPracticeRateLimitError,
)
from .persistence import PersistenceError, StaleGenerationClaimError
from .practice_modes import PracticeMode
from .store import DemoActivity, PracticeContentContract

logger = logging.getLogger(__name__)

#: The longest free-text request the composer accepts. A learner request is a
#: short intent, not an authoring brief.
MAX_REQUEST_CHARS = 600
MAX_RESPONSE_FORM_CHARS = 200
MAX_EXAM_CONTEXT_CHARS = 200
MAX_HISTORY_ITEMS = 5

#: Default per-learner generation rate limit and rolling window (SPEC-044).
DEFAULT_LEARNER_PRACTICE_RATE_LIMIT = 5
DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS = 3600
DEFAULT_GENERATION_CLAIM_TTL_SECONDS = 60
DEFAULT_GENERATION_WAIT_TIMEOUT_SECONDS = 60.0

DEFAULT_RESPONSE_FORM = "A short written response"
GENERATION_UNAVAILABLE_MESSAGE = (
    "Making a practice is temporarily unavailable. Please try again shortly."
)
VALIDATION_FAILURE_MESSAGE = (
    "We couldn't make a practice from that request. Try describing what you "
    "want to practise in a little more detail."
)


def _format_rate_window(seconds: int) -> str:
    bounded = max(1, seconds)
    if bounded == 3600:
        return "hour"
    if bounded % 3600 == 0:
        return f"{bounded // 3600} hours"
    if bounded == 60:
        return "minute"
    if bounded % 60 == 0:
        return f"{bounded // 60} minutes"
    return "second" if bounded == 1 else f"{bounded} seconds"


def _format_retry_wait(seconds: int) -> str:
    bounded = max(1, seconds)
    if bounded >= 60:
        minutes = math.ceil(bounded / 60)
        return "1 minute" if minutes == 1 else f"{minutes} minutes"
    return "1 second" if bounded == 1 else f"{bounded} seconds"


def rate_limit_message(
    *,
    limit: int = DEFAULT_LEARNER_PRACTICE_RATE_LIMIT,
    window_seconds: int = DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS,
    retry_after_seconds: int | None = None,
) -> str:
    """Return a calm, learner-friendly message when the generation limit is reached."""
    noun = "practice request" if limit == 1 else "practice requests"
    window_label = _format_rate_window(window_seconds)
    wait_label = _format_retry_wait(
        window_seconds if retry_after_seconds is None else retry_after_seconds
    )
    return (
        f"You've reached the limit of {limit} {noun} per {window_label}. "
        "You can still use practices you've already requested or explore the "
        f"practice library, and try again in {wait_label}."
    )


RATE_LIMIT_MESSAGE = rate_limit_message()


def _normalize_rate_limit_params(
    now: datetime,
    *,
    limit: int,
    window_seconds: int,
) -> tuple[datetime, int, int]:
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("rate limit timestamp must be timezone-aware")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("rate limit must be a positive integer")
    if (
        not isinstance(window_seconds, int)
        or isinstance(window_seconds, bool)
        or window_seconds < 1
    ):
        raise ValueError("rate limit window_seconds must be a positive integer")
    return now.astimezone(UTC), limit, window_seconds


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


@dataclass(frozen=True)
class GenerationClaimOutcome:
    """Outcome of claiming a learner/request-token idempotency key."""

    claimed: bool
    existing: GeneratedPracticeRecord | None = None
    claim_token: UUID | None = None

    def __post_init__(self) -> None:
        if self.claimed:
            if self.claim_token is None:
                object.__setattr__(self, "claim_token", uuid4())
            elif not isinstance(self.claim_token, UUID):
                raise ValueError(
                    "claimed GenerationClaimOutcome requires a UUID claim_token"
                )
        elif self.claim_token is not None:
            raise ValueError(
                "unclaimed GenerationClaimOutcome must not carry a claim_token"
            )


@dataclass
class _InMemoryGenerationClaim:
    """In-flight generation claim for coordinating concurrent duplicate requests."""

    learner_id: UUID
    expires_at: datetime
    claim_token: UUID = field(default_factory=uuid4)
    event: Event = field(default_factory=Event)
    record: GeneratedPracticeRecord | None = None
    error: Exception | None = None


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

    def claim_generation(
        self,
        learner_id: UUID,
        practice_id: UUID,
        *,
        now: datetime | None = None,
        ttl_seconds: int = DEFAULT_GENERATION_CLAIM_TTL_SECONDS,
    ) -> GenerationClaimOutcome:
        """Atomically check for an existing practice or claim the generation key.

        When the record already exists, returns ``GenerationClaimOutcome(claimed=False,
        existing=record)``. When no active claim exists, claims the key and
        returns ``GenerationClaimOutcome(claimed=True, claim_token=...)``. When
        another request already holds an active claim for the same key, returns
        ``GenerationClaimOutcome(claimed=False, existing=None)`` so the duplicate
        request can await the in-flight generation instead of calling the
        provider a second time.
        """
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            raise ValueError(
                "claim_generation requires UUID learner_id and practice_id"
            )
        _normalize_rate_limit_params(
            now or datetime.now(UTC),
            limit=1,
            window_seconds=ttl_seconds,
        )
        existing = self.get(learner_id, practice_id)
        if existing is not None:
            return GenerationClaimOutcome(claimed=False, existing=existing)
        return GenerationClaimOutcome(claimed=True, claim_token=uuid4())

    def renew_generation_claim(
        self,
        learner_id: UUID,
        practice_id: UUID,
        claim_token: UUID | None = None,
        *,
        now: datetime | None = None,
        ttl_seconds: int = DEFAULT_GENERATION_CLAIM_TTL_SECONDS,
    ) -> bool:
        """Extend an active generation lease when ``claim_token`` still owns it."""
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            raise ValueError(
                "renew_generation_claim requires UUID learner_id and practice_id"
            )
        _normalize_rate_limit_params(
            now or datetime.now(UTC),
            limit=1,
            window_seconds=ttl_seconds,
        )
        return isinstance(claim_token, UUID)

    def complete_generation_claim(
        self,
        record: GeneratedPracticeRecord,
        claim_token: UUID | None = None,
    ) -> GeneratedPracticeRecord:
        """Persist ``record`` for the active ``claim_token`` owner."""
        _ = claim_token
        return self.save(record)

    def await_generation(
        self,
        learner_id: UUID,
        practice_id: UUID,
        *,
        timeout_seconds: float = DEFAULT_GENERATION_WAIT_TIMEOUT_SECONDS,
    ) -> GeneratedPracticeRecord:
        """Wait for an in-flight generation claim to resolve to a record."""
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            raise ValueError(
                "await_generation requires UUID learner_id and practice_id"
            )
        _ = timeout_seconds
        existing = self.get(learner_id, practice_id)
        if existing is not None:
            return existing
        raise LearnerPracticeGenerationError(GENERATION_UNAVAILABLE_MESSAGE)

    def release_generation_claim(
        self,
        learner_id: UUID,
        practice_id: UUID,
        claim_token: UUID | None = None,
        *,
        error: Exception | None = None,
    ) -> bool:
        """Release an in-flight generation claim when owned by ``claim_token``."""
        _ = (learner_id, practice_id, claim_token, error)
        return False

    def reserve_generation_slot(
        self,
        learner_id: UUID,
        *,
        now: datetime,
        limit: int = DEFAULT_LEARNER_PRACTICE_RATE_LIMIT,
        window_seconds: int = DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS,
    ) -> int | None:
        """Reserve one generation attempt within the learner's rate-limit window.

        Returns ``None`` when the attempt is within ``limit`` for the trailing
        ``window_seconds`` ending at ``now``, or the positive number of seconds
        until the learner may retry when the limit has been reached.
        """
        if not isinstance(learner_id, UUID):
            raise ValueError("rate limit learner_id must be a UUID")
        current, max_requests, window = _normalize_rate_limit_params(
            now, limit=limit, window_seconds=window_seconds
        )
        window_start = current - timedelta(seconds=window)
        active = sorted(
            record.created_at.astimezone(UTC)
            for record in self.list_for_learner(learner_id)
            if record.created_at.astimezone(UTC) > window_start
        )
        if len(active) >= max_requests:
            unlock_at = active[-max_requests] + timedelta(seconds=window)
            return max(1, math.ceil((unlock_at - current).total_seconds()))
        return None


class InMemoryGeneratedPracticeRepository(GeneratedPracticeRepository):
    """Deterministic in-memory store for tests and local development."""

    def __init__(self) -> None:
        self._records: dict[UUID, GeneratedPracticeRecord] = {}
        self._learner_records: dict[UUID, list[UUID]] = {}
        self._rate_limit_attempts: dict[UUID, list[datetime]] = {}
        self._claims: dict[UUID, _InMemoryGenerationClaim] = {}
        self._lock = Lock()

    def claim_generation(
        self,
        learner_id: UUID,
        practice_id: UUID,
        *,
        now: datetime | None = None,
        ttl_seconds: int = DEFAULT_GENERATION_CLAIM_TTL_SECONDS,
    ) -> GenerationClaimOutcome:
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            raise ValueError(
                "claim_generation requires UUID learner_id and practice_id"
            )
        current, _, ttl = _normalize_rate_limit_params(
            now or datetime.now(UTC),
            limit=1,
            window_seconds=ttl_seconds,
        )
        with self._lock:
            existing = self._records.get(practice_id)
            if existing is not None:
                if existing.learner_id != learner_id:
                    raise PersistenceError(
                        f"Generated practice {practice_id} belongs to another learner"
                    )
                return GenerationClaimOutcome(claimed=False, existing=existing)

            active_claim = self._claims.get(practice_id)
            if active_claim is not None:
                if active_claim.learner_id != learner_id:
                    raise PersistenceError(
                        f"Generated practice claim {practice_id} "
                        "belongs to another learner"
                    )
                if active_claim.expires_at > current:
                    return GenerationClaimOutcome(claimed=False, existing=None)
                active_claim.event.set()

            claim_token = uuid4()
            self._claims[practice_id] = _InMemoryGenerationClaim(
                learner_id=learner_id,
                expires_at=current + timedelta(seconds=ttl),
                claim_token=claim_token,
            )
            return GenerationClaimOutcome(
                claimed=True,
                existing=None,
                claim_token=claim_token,
            )

    def renew_generation_claim(
        self,
        learner_id: UUID,
        practice_id: UUID,
        claim_token: UUID | None = None,
        *,
        now: datetime | None = None,
        ttl_seconds: int = DEFAULT_GENERATION_CLAIM_TTL_SECONDS,
    ) -> bool:
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            raise ValueError(
                "renew_generation_claim requires UUID learner_id and practice_id"
            )
        current, _, ttl = _normalize_rate_limit_params(
            now or datetime.now(UTC),
            limit=1,
            window_seconds=ttl_seconds,
        )
        if not isinstance(claim_token, UUID):
            return False
        with self._lock:
            existing = self._records.get(practice_id)
            if existing is not None:
                if existing.learner_id != learner_id:
                    raise PersistenceError(
                        f"Generated practice {practice_id} belongs to another learner"
                    )
                return False
            claim = self._claims.get(practice_id)
            if claim is None:
                return False
            if claim.learner_id != learner_id:
                raise PersistenceError(
                    f"Generated practice claim {practice_id} belongs to another learner"
                )
            if claim.claim_token != claim_token or claim.expires_at <= current:
                return False
            claim.expires_at = current + timedelta(seconds=ttl)
            return True

    def complete_generation_claim(
        self,
        record: GeneratedPracticeRecord,
        claim_token: UUID | None = None,
    ) -> GeneratedPracticeRecord:
        if "save" in self.__dict__:
            return self.save(record)
        return self.save(record, claim_token=claim_token)

    def await_generation(
        self,
        learner_id: UUID,
        practice_id: UUID,
        *,
        timeout_seconds: float = DEFAULT_GENERATION_WAIT_TIMEOUT_SECONDS,
    ) -> GeneratedPracticeRecord:
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            raise ValueError(
                "await_generation requires UUID learner_id and practice_id"
            )
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        last_claim: _InMemoryGenerationClaim | None = None
        while True:
            with self._lock:
                existing = self._records.get(practice_id)
                if existing is not None:
                    if existing.learner_id != learner_id:
                        raise PersistenceError(
                            f"Generated practice {practice_id} "
                            "belongs to another learner"
                        )
                    return existing
                claim = self._claims.get(practice_id)
                if claim is not None and claim.learner_id != learner_id:
                    raise PersistenceError(
                        f"Generated practice claim {practice_id} "
                        "belongs to another learner"
                    )

            if claim is None:
                break
            last_claim = claim
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            claim.event.wait(timeout=remaining)
            if claim.record is not None:
                if claim.record.learner_id != learner_id:
                    raise PersistenceError(
                        f"Generated practice {practice_id} belongs to another learner"
                    )
                return claim.record
            persisted = self.get(learner_id, practice_id)
            if persisted is not None:
                return persisted
            with self._lock:
                current_claim = self._claims.get(practice_id)
            if current_claim is not None and current_claim is not claim:
                continue
            if claim.error is not None:
                raise claim.error
            if current_claim is None:
                break

        persisted = self.get(learner_id, practice_id)
        if persisted is not None:
            return persisted
        if last_claim is not None and last_claim.error is not None:
            raise last_claim.error
        raise LearnerPracticeGenerationError(GENERATION_UNAVAILABLE_MESSAGE)

    def release_generation_claim(
        self,
        learner_id: UUID,
        practice_id: UUID,
        claim_token: UUID | None = None,
        *,
        error: Exception | None = None,
    ) -> bool:
        if (
            not isinstance(learner_id, UUID)
            or not isinstance(practice_id, UUID)
            or not isinstance(claim_token, UUID)
        ):
            return False
        with self._lock:
            claim = self._claims.get(practice_id)
            if (
                claim is not None
                and claim.learner_id == learner_id
                and claim.claim_token == claim_token
            ):
                self._claims.pop(practice_id, None)
                claim.error = error
                claim.event.set()
                return True
        return False

    def save(
        self,
        record: GeneratedPracticeRecord,
        *,
        claim_token: UUID | None = None,
    ) -> GeneratedPracticeRecord:
        if not isinstance(record, GeneratedPracticeRecord):
            raise ValueError(
                "generated practice repository only accepts GeneratedPracticeRecord"
            )
        if claim_token is not None and not isinstance(claim_token, UUID):
            raise ValueError("save claim_token must be a UUID when provided")
        with self._lock:
            existing = self._records.get(record.practice_id)
            claim = self._claims.get(record.practice_id)
            if existing is not None:
                if existing.learner_id != record.learner_id:
                    raise PersistenceError(
                        f"Generated practice {record.practice_id} "
                        "belongs to another learner"
                    )
                persisted = existing
                if (
                    claim is not None
                    and claim_token is not None
                    and claim.claim_token == claim_token
                ):
                    self._claims.pop(record.practice_id, None)
                    claim.record = persisted
                    claim.event.set()
                return persisted

            if claim is not None:
                if claim.learner_id != record.learner_id:
                    raise PersistenceError(
                        f"Generated practice claim {record.practice_id} "
                        "belongs to another learner"
                    )
                if claim_token is None or claim.claim_token != claim_token:
                    raise StaleGenerationClaimError(
                        f"Generated practice claim {record.practice_id} "
                        "is owned by another generation attempt"
                    )
            elif claim_token is not None:
                raise StaleGenerationClaimError(
                    f"Generated practice claim {record.practice_id} is no longer active"
                )

            self._records[record.practice_id] = record
            self._learner_records.setdefault(record.learner_id, []).append(
                record.practice_id
            )
            if claim is not None:
                self._claims.pop(record.practice_id, None)
                claim.record = record
                claim.event.set()
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

    def reserve_generation_slot(
        self,
        learner_id: UUID,
        *,
        now: datetime,
        limit: int = DEFAULT_LEARNER_PRACTICE_RATE_LIMIT,
        window_seconds: int = DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS,
    ) -> int | None:
        if not isinstance(learner_id, UUID):
            raise ValueError("rate limit learner_id must be a UUID")
        current, max_requests, window = _normalize_rate_limit_params(
            now, limit=limit, window_seconds=window_seconds
        )
        window_start = current - timedelta(seconds=window)
        with self._lock:
            active = sorted(
                ts
                for ts in self._rate_limit_attempts.get(learner_id, ())
                if ts > window_start
            )
            if len(active) >= max_requests:
                self._rate_limit_attempts[learner_id] = active
                unlock_at = active[-max_requests] + timedelta(seconds=window)
                return max(1, math.ceil((unlock_at - current).total_seconds()))
            active.append(current)
            self._rate_limit_attempts[learner_id] = active
            return None


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


def _invoke_generator_with_lease_renewal(
    repository: GeneratedPracticeRepository,
    generator: LearnerPracticeGenerator,
    *,
    generation_request: LearnerPracticeGenerationRequest,
    learner_id: UUID,
    practice_id: UUID,
    claim_token: UUID | None,
    claimed_at: datetime,
    ttl_seconds: int,
    renewal_interval_seconds: float | None,
) -> LearnerPracticeGenerationResult:
    interval = (
        ttl_seconds / 2.0
        if renewal_interval_seconds is None
        else float(renewal_interval_seconds)
    )
    if claim_token is None or interval <= 0:
        return generator.generate(generation_request)

    stop_event = Event()
    started_monotonic = time.monotonic()

    def _renew_loop() -> None:
        while not stop_event.wait(interval):
            elapsed = max(0.0, time.monotonic() - started_monotonic)
            renewal_time = claimed_at + timedelta(seconds=elapsed)
            try:
                renewed = repository.renew_generation_claim(
                    learner_id,
                    practice_id,
                    claim_token,
                    now=renewal_time,
                    ttl_seconds=ttl_seconds,
                )
            except Exception:
                logger.warning(
                    "failed to renew generation claim lease",
                    extra={
                        "practice_id": str(practice_id),
                        "learner_id": str(learner_id),
                    },
                    exc_info=True,
                )
                return
            if not renewed:
                return

    renewal_thread = Thread(
        target=_renew_loop,
        name=f"fablit-claim-renew-{practice_id}",
        daemon=True,
    )
    renewal_thread.start()
    try:
        return generator.generate(generation_request)
    finally:
        stop_event.set()
        renewal_thread.join(timeout=1.0)


def generate_private_practice(
    repository: GeneratedPracticeRepository,
    generator: LearnerPracticeGenerator,
    *,
    request: PracticeRequest,
    history: HistoryContext,
    now: datetime | None = None,
    rate_limit: int = DEFAULT_LEARNER_PRACTICE_RATE_LIMIT,
    rate_window_seconds: int = DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS,
    claim_ttl_seconds: int = DEFAULT_GENERATION_CLAIM_TTL_SECONDS,
    wait_timeout_seconds: float = DEFAULT_GENERATION_WAIT_TIMEOUT_SECONDS,
    claim_renewal_interval_seconds: float | None = None,
) -> GeneratedPracticeRecord:
    """Generate, validate, and privately persist one requested practice.

    A repeated request with the same token returns the already-persisted
    record without calling the provider again. A fresh generation attempt is
    bounded by the learner's rate limit before invoking the provider. Invalid
    provider output never reaches persistence or the learner.
    """
    practice_id = practice_id_for(request.learner_id, request.token)
    created_at, _, ttl = _normalize_rate_limit_params(
        now or datetime.now(UTC),
        limit=1,
        window_seconds=claim_ttl_seconds,
    )
    claim = repository.claim_generation(
        request.learner_id,
        practice_id,
        now=created_at,
        ttl_seconds=ttl,
    )
    if claim.existing is not None:
        return claim.existing
    if not claim.claimed:
        return repository.await_generation(
            request.learner_id,
            practice_id,
            timeout_seconds=wait_timeout_seconds,
        )

    failure: Exception | None = None
    persisted: GeneratedPracticeRecord | None = None
    try:
        retry_after = repository.reserve_generation_slot(
            request.learner_id,
            now=created_at,
            limit=rate_limit,
            window_seconds=rate_window_seconds,
        )
        if retry_after is not None:
            raise LearnerPracticeRateLimitError(
                rate_limit_message(
                    limit=rate_limit,
                    window_seconds=rate_window_seconds,
                    retry_after_seconds=retry_after,
                ),
                retry_after_seconds=retry_after,
            )

        effective_history = history if request.include_history else HistoryContext()
        brief = _brief_for(request, effective_history)
        try:
            result = _invoke_generator_with_lease_renewal(
                repository,
                generator,
                generation_request=LearnerPracticeGenerationRequest(
                    request=request, history=effective_history
                ),
                learner_id=request.learner_id,
                practice_id=practice_id,
                claim_token=claim.claim_token,
                claimed_at=created_at,
                ttl_seconds=ttl,
                renewal_interval_seconds=claim_renewal_interval_seconds,
            )
        except LearnerPracticeGenerationError:
            raise
        except Exception as exc:
            logger.exception("learner practice generator failed")
            raise LearnerPracticeGenerationError(
                GENERATION_UNAVAILABLE_MESSAGE
            ) from exc

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
        try:
            persisted = repository.complete_generation_claim(
                record,
                claim.claim_token,
            )
        except StaleGenerationClaimError:
            logger.warning(
                "generated practice claim expired before save; awaiting replacement",
                extra={
                    "practice_id": str(practice_id),
                    "learner_id": str(request.learner_id),
                },
            )
            persisted = repository.await_generation(
                request.learner_id,
                practice_id,
                timeout_seconds=wait_timeout_seconds,
            )
        return persisted
    except Exception as exc:
        failure = exc
        raise
    finally:
        if persisted is None:
            repository.release_generation_claim(
                request.learner_id,
                practice_id,
                claim.claim_token,
                error=failure,
            )


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
