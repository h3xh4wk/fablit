"""Protected internal practice-authoring workflow (SPEC-032 / SEC-001).

The workflow validates typed authoring briefs before provider invocation and
stores untrusted provider-neutral candidate data with provenance. Candidate
quality validation and the complete review lifecycle remain separate gates.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.learner_session import LearnerApplicationRegistry
from app.request_format import wants_html
from app.task_text import split_task_text
from fablit.application.authoring import (
    _CONTRACT_FIELDS,
    AuthoringRevision,
    CandidateStatus,
    CandidateValidation,
    validate_candidate,
)
from fablit.application.demo_data import PRACTICE_CAPABILITIES
from fablit.application.errors import (
    CandidateContentNotPublishableError,
    CandidateNotApprovableError,
    CandidateNotFoundError,
    CandidateNotPublishableError,
    PublishedPracticeNotFoundError,
)
from fablit.application.image_search import (
    ImageCandidate,
    ImageSearchError,
    ImageSearchProvider,
    image_candidate_from_mapping,
    image_candidate_to_mapping,
)
from fablit.application.persistence import PersistenceError
from fablit.application.practice_modes import PracticeMode
from fablit.application.publishing import (
    PublishedPractice,
    PublishedPracticeStore,
    publish_candidate,
    withdraw_publication,
)
from fablit.application.store import PracticeContentContract
from fablit.config import AppConfig
from fablit.platform.authoring_auth import (
    clear_authoring_cookie,
    extract_authoring_credential,
    set_authoring_cookie,
    verify_authoring_secret,
)

logger = logging.getLogger("fablit.authoring")
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["split_task_text"] = split_task_text

router = APIRouter(prefix="/authoring")


class InvalidAuthoringBriefError(ValueError):
    """Raised when an authoring brief is incomplete or contains unsupported values."""


class InvalidStimulusSelectionError(ValueError):
    """Raised when a selected image is not one of the stored search options."""


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class CandidateReviewOutcome(StrEnum):
    """Human review outcome recorded for an authoring candidate."""

    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class AuthoringBrief:
    """Validated, provider-neutral request for one practice candidate."""

    practice_area: str
    learner_context: str
    purpose: str
    intended_mode: PracticeMode
    response_form: str
    evaluation_intent: str
    feedback_intent: str
    reflection_intent: str
    examination_context: str | None = None
    primary_creative_thinking_lens: str | None = None
    constraints: str | None = None
    stimulus_requirements: str | None = None
    continuation_intent: str | None = None

    def __post_init__(self) -> None:
        """Enforce required text and the supported mode/lens choices."""
        for name in (
            "practice_area",
            "learner_context",
            "purpose",
            "response_form",
            "evaluation_intent",
            "feedback_intent",
            "reflection_intent",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidAuthoringBriefError(
                    f"authoring brief field {name!r} must be non-blank text"
                )
        if not isinstance(self.intended_mode, PracticeMode):
            raise InvalidAuthoringBriefError(
                f"unsupported practice mode: {self.intended_mode!r}"
            )
        lens = self.primary_creative_thinking_lens
        if lens is not None and lens not in PRACTICE_CAPABILITIES:
            raise InvalidAuthoringBriefError(
                f"unsupported creative-thinking lens: {lens!r}"
            )
        for name in (
            "examination_context",
            "constraints",
            "stimulus_requirements",
            "continuation_intent",
        ):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise InvalidAuthoringBriefError(
                    f"optional authoring brief field {name!r} must be non-blank text "
                    "when provided"
                )

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> AuthoringBrief:
        """Parse submitted values into the typed brief, rejecting unknown fields."""
        fields = {
            "practice_area",
            "learner_context",
            "purpose",
            "intended_mode",
            "response_form",
            "evaluation_intent",
            "feedback_intent",
            "reflection_intent",
            "examination_context",
            "primary_creative_thinking_lens",
            "constraints",
            "stimulus_requirements",
            "continuation_intent",
        }
        unsupported = set(values) - fields
        if unsupported:
            raise InvalidAuthoringBriefError(
                f"unsupported authoring brief fields: {', '.join(sorted(unsupported))}"
            )

        parsed: dict[str, object] = dict(values)
        for name in (
            "examination_context",
            "primary_creative_thinking_lens",
            "constraints",
            "stimulus_requirements",
            "continuation_intent",
        ):
            if parsed.get(name) == "":
                parsed[name] = None
        mode_value = parsed.get("intended_mode")
        if not isinstance(mode_value, str):
            raise InvalidAuthoringBriefError(
                f"unsupported practice mode: {mode_value!r}"
            )
        try:
            parsed["intended_mode"] = PracticeMode(mode_value)
        except ValueError:
            raise InvalidAuthoringBriefError(
                f"unsupported practice mode: {mode_value!r}"
            ) from None

        def required_text(name: str) -> str:
            value = parsed.get(name)
            if not isinstance(value, str):
                raise InvalidAuthoringBriefError(
                    f"authoring brief field {name!r} must be text"
                )
            return value

        def optional_text(name: str) -> str | None:
            value = parsed.get(name)
            if value is not None and not isinstance(value, str):
                raise InvalidAuthoringBriefError(
                    f"optional authoring brief field {name!r} must be text"
                )
            return value

        mode = parsed["intended_mode"]
        if not isinstance(mode, PracticeMode):
            raise InvalidAuthoringBriefError("unsupported practice mode")
        return cls(
            practice_area=required_text("practice_area"),
            learner_context=required_text("learner_context"),
            purpose=required_text("purpose"),
            intended_mode=mode,
            response_form=required_text("response_form"),
            evaluation_intent=required_text("evaluation_intent"),
            feedback_intent=required_text("feedback_intent"),
            reflection_intent=required_text("reflection_intent"),
            examination_context=optional_text("examination_context"),
            primary_creative_thinking_lens=optional_text(
                "primary_creative_thinking_lens"
            ),
            constraints=optional_text("constraints"),
            stimulus_requirements=optional_text("stimulus_requirements"),
            continuation_intent=optional_text("continuation_intent"),
        )


@dataclass(frozen=True)
class PracticeCandidate:
    """Untrusted generated practice content with provider-neutral provenance."""

    brief: AuthoringBrief
    candidate_data: Mapping[str, Any]
    provider: str
    model: str
    generated_at: datetime
    id: UUID = field(default_factory=uuid4)
    review_outcome: CandidateReviewOutcome | None = None
    validation: CandidateValidation = field(default_factory=CandidateValidation)
    revision: int = 1
    reviewer: str | None = None
    decided_at: datetime | None = None
    history: tuple[AuthoringRevision, ...] = ()

    def __post_init__(self) -> None:
        """Validate candidate identity, provenance, and attach quality validation."""
        if not isinstance(self.id, UUID):
            raise ValueError(f"candidate id must be a UUID, got {self.id!r}")
        if not isinstance(self.candidate_data, Mapping):
            raise ValueError("candidate data must be a mapping")
        for name in ("provider", "model"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"candidate {name} must be non-blank text")
        generated_at = self.generated_at
        if (
            not isinstance(generated_at, datetime)
            or generated_at.tzinfo is None
            or generated_at.utcoffset() != timedelta(0)
        ):
            raise ValueError("candidate generated_at must be timezone-aware UTC")
        object.__setattr__(self, "generated_at", generated_at.astimezone(UTC))

        if self.validation == CandidateValidation():
            val = validate_candidate(self)
            object.__setattr__(self, "validation", val)

    @property
    def status(self) -> str:
        """Return the lifecycle display status."""
        if self.review_outcome is not None:
            return self.review_outcome.value
        return CandidateStatus.GENERATED.value

    @property
    def is_approved(self) -> bool:
        """Whether this candidate has been approved for the curated library."""
        return self.review_outcome == CandidateReviewOutcome.APPROVED

    @property
    def title(self) -> str:
        val = self.candidate_data.get("title")
        return str(val).strip() if val is not None else ""

    @property
    def description(self) -> str:
        val = self.candidate_data.get("description")
        return str(val).strip() if val is not None else ""

    @property
    def contract(self) -> PracticeContentContract | None:
        raw = self.candidate_data.get("contract")
        if isinstance(raw, Mapping):
            try:
                vals = {
                    k: str(raw[k]).strip()
                    for k in _CONTRACT_FIELDS
                    if k in raw and isinstance(raw[k], str) and str(raw[k]).strip()
                }
                if len(vals) == len(_CONTRACT_FIELDS):
                    return PracticeContentContract(**vals)
            except Exception:
                return None
        return None

    @property
    def stimulus_query(self) -> str:
        """The one-line scene description used for image search (SPEC-036)."""
        value = self.candidate_data.get("stimulus_query")
        return str(value).strip() if value is not None else ""

    @property
    def stimulus_options(self) -> tuple[ImageCandidate, ...]:
        """The bounded image results an author can choose from (SPEC-036)."""
        raw = self.candidate_data.get("stimulus_options")
        if not isinstance(raw, list | tuple):
            return ()
        options = (image_candidate_from_mapping(item) for item in raw)
        return tuple(option for option in options if option is not None)

    @property
    def stimulus(self) -> ImageCandidate | None:
        """The selected stimulus image, or ``None`` when optional (SPEC-036)."""
        return image_candidate_from_mapping(self.candidate_data.get("stimulus"))

    @property
    def supports_sketch_upload(self) -> bool:
        """Whether the learner should see the optional sketch input.

        SPEC-037: an image-based candidate offers it by default, and an author
        can turn it off explicitly with ``allow_sketch: false``.
        """
        raw = self.candidate_data.get("allow_sketch")
        if raw is None:
            return self.stimulus is not None
        return _truthy(raw)


class AuthoringCandidateStore:
    """Base/in-memory authoring candidate store (SPEC-032 / FIX-7)."""

    def __init__(self, *, retention_days: int = 30) -> None:
        self.retention_days = retention_days
        self._candidates: dict[UUID, PracticeCandidate] = {}
        self._order: list[UUID] = []

    def _get_entity(self, candidate_id: UUID) -> PracticeCandidate | None:
        """Fetch raw candidate from storage."""
        return self._candidates.get(candidate_id)

    def _put_entity(self, candidate: PracticeCandidate) -> None:
        """Save candidate to storage."""
        if candidate.id not in self._candidates:
            self._order.append(candidate.id)
        self._candidates[candidate.id] = candidate

    def _delete_entity(self, candidate_id: UUID) -> None:
        """Delete candidate from storage."""
        self._candidates.pop(candidate_id, None)
        if candidate_id in self._order:
            self._order.remove(candidate_id)

    def _all_entities(self) -> list[PracticeCandidate]:
        """Fetch all stored candidates in insertion order."""
        return [self._candidates[cid] for cid in self._order if cid in self._candidates]

    def _is_expired(
        self, candidate: PracticeCandidate, *, now: datetime | None = None
    ) -> bool:
        """Check if an unapproved candidate has expired by retention policy."""
        if candidate.is_approved:
            return False
        current_time = now or datetime.now(UTC)
        cutoff = current_time - timedelta(days=self.retention_days)
        return candidate.generated_at < cutoff

    def add(self, candidate: PracticeCandidate) -> PracticeCandidate:
        """Store a candidate under its stable identity and attach duplicate warnings."""
        if self._get_entity(candidate.id) is not None:
            raise ValueError(f"candidate already exists: {candidate.id}")
        if candidate.title:
            for existing in self._all_entities():
                if existing.title and existing.title.lower() == candidate.title.lower():
                    warnings = candidate.validation.content_warnings + (
                        f"possible duplicate of existing candidate {existing.title!r}",
                    )
                    candidate = dataclasses.replace(
                        candidate,
                        validation=dataclasses.replace(
                            candidate.validation, content_warnings=warnings
                        ),
                    )
                    break
        self._put_entity(candidate)
        return candidate

    def get(self, candidate_id: UUID | str) -> PracticeCandidate:
        """Return a candidate by identity, or raise CandidateNotFoundError."""
        uuid_val: UUID
        if isinstance(candidate_id, str):
            try:
                uuid_val = UUID(candidate_id)
            except ValueError:
                raise CandidateNotFoundError(
                    f"Candidate {candidate_id} not found."
                ) from None
        elif isinstance(candidate_id, UUID):
            uuid_val = candidate_id
        else:
            raise CandidateNotFoundError(f"Candidate {candidate_id} not found.")

        candidate = self._get_entity(uuid_val)
        if candidate is None or self._is_expired(candidate):
            raise CandidateNotFoundError(f"Candidate {candidate_id} not found.")
        return candidate

    def list(self) -> tuple[PracticeCandidate, ...]:
        """Return active candidates within the retention window."""
        return tuple(
            candidate
            for candidate in self._all_entities()
            if not self._is_expired(candidate)
        )

    def list_candidates(self) -> tuple[PracticeCandidate, ...]:
        """Alias for list to maintain consistency across authoring layers."""
        return self.list()

    def approve(
        self, candidate_id: UUID | str, *, reviewer: str = "author"
    ) -> PracticeCandidate:
        """Approve a validated candidate for the curated library."""
        candidate = self.get(candidate_id)
        if candidate.status == CandidateStatus.APPROVED.value:
            raise CandidateNotApprovableError(
                f"Candidate {candidate.id} is already approved."
            )
        if candidate.status == CandidateStatus.REJECTED.value:
            raise CandidateNotApprovableError(
                f"Rejected candidate {candidate.id} cannot be approved."
            )
        if not candidate.validation.is_approvable:
            errors = "; ".join(
                candidate.validation.structural_errors
                + candidate.validation.feedback_errors
            )
            raise CandidateNotApprovableError(
                f"Candidate {candidate.id} has validation errors and cannot "
                f"be approved: {errors}"
            )
        approved = dataclasses.replace(
            candidate,
            review_outcome=CandidateReviewOutcome.APPROVED,
            reviewer=reviewer,
            decided_at=datetime.now(UTC),
        )
        self._put_entity(approved)
        return approved

    def reject(
        self, candidate_id: UUID | str, *, reviewer: str = "author"
    ) -> PracticeCandidate:
        """Reject a candidate from inclusion in the curated library."""
        candidate = self.get(candidate_id)
        if candidate.status == CandidateStatus.APPROVED.value:
            raise CandidateNotApprovableError(
                f"Approved candidate {candidate.id} cannot be rejected."
            )
        if candidate.status == CandidateStatus.REJECTED.value:
            raise CandidateNotApprovableError(
                f"Candidate {candidate.id} is already rejected."
            )
        rejected = dataclasses.replace(
            candidate,
            review_outcome=CandidateReviewOutcome.REJECTED,
            reviewer=reviewer,
            decided_at=datetime.now(UTC),
        )
        self._put_entity(rejected)
        return rejected

    def edit(
        self,
        candidate_id: UUID | str,
        *,
        updates: Mapping[str, Any],
        editor: str = "author",
    ) -> PracticeCandidate:
        """Edit candidate data, record superseded revision, and revalidate."""
        candidate = self.get(candidate_id)
        revision_record = AuthoringRevision(
            version=candidate.revision,
            title=candidate.title,
            description=candidate.description,
            contract=candidate.contract,
            edited_at=datetime.now(UTC),
            editor=editor,
        )

        new_candidate_data = dict(candidate.candidate_data)
        if "title" in updates and updates["title"] is not None:
            new_candidate_data["title"] = str(updates["title"]).strip()
        if "description" in updates and updates["description"] is not None:
            new_candidate_data["description"] = str(updates["description"]).strip()

        existing_contract: dict[str, Any] = {}
        if isinstance(new_candidate_data.get("contract"), Mapping):
            existing_contract = dict(new_candidate_data["contract"])

        contract_updates = updates.get("contract")
        if isinstance(contract_updates, Mapping):
            existing_contract.update(contract_updates)

        for field_name in _CONTRACT_FIELDS:
            if field_name in updates and updates[field_name] is not None:
                existing_contract[field_name] = str(updates[field_name]).strip()

        if existing_contract:
            new_candidate_data["contract"] = existing_contract

        # SPEC-037: the edit form sends a marker so an unchecked box can
        # explicitly turn sketch evidence off instead of leaving it absent.
        if "allow_sketch" in updates or "allow_sketch_present" in updates:
            new_candidate_data["allow_sketch"] = _truthy(updates.get("allow_sketch"))

        updated = dataclasses.replace(
            candidate,
            candidate_data=new_candidate_data,
            review_outcome=None,
            revision=candidate.revision + 1,
            reviewer=editor,
            decided_at=None,
            history=candidate.history + (revision_record,),
            validation=CandidateValidation(),
        )
        updated = dataclasses.replace(updated, validation=validate_candidate(updated))
        self._put_entity(updated)
        return updated

    def select_stimulus(
        self,
        candidate_id: UUID | str,
        photo_id: str | None,
        *,
        editor: str = "author",
    ) -> PracticeCandidate:
        """Select one stored stimulus option, or clear the selection (SPEC-036).

        The image is learner-facing content, so changing it follows the same
        edit lifecycle as the written contract: a new revision and a renewed
        human approval before it can be published again.
        """
        candidate = self.get(candidate_id)
        new_candidate_data = dict(candidate.candidate_data)
        if photo_id is None or not str(photo_id).strip():
            new_candidate_data.pop("stimulus", None)
        else:
            selection = str(photo_id).strip()
            match = next(
                (
                    option
                    for option in candidate.stimulus_options
                    if option.photo_id == selection
                ),
                None,
            )
            if match is None:
                raise InvalidStimulusSelectionError(
                    "the selected image is no longer one of this candidate's options"
                )
            new_candidate_data["stimulus"] = image_candidate_to_mapping(match)

        revision_record = AuthoringRevision(
            version=candidate.revision,
            title=candidate.title,
            description=candidate.description,
            contract=candidate.contract,
            edited_at=datetime.now(UTC),
            editor=editor,
        )
        updated = dataclasses.replace(
            candidate,
            candidate_data=new_candidate_data,
            review_outcome=None,
            revision=candidate.revision + 1,
            reviewer=editor,
            decided_at=None,
            history=candidate.history + (revision_record,),
            validation=CandidateValidation(),
        )
        updated = dataclasses.replace(updated, validation=validate_candidate(updated))
        self._put_entity(updated)
        return updated

    def approved_practices(self) -> tuple[PracticeCandidate, ...]:
        """Return approved practices isolated from learner library until curated."""
        return tuple(c for c in self.list() if c.is_approved)

    def cleanup_expired(self, *, now: datetime | None = None) -> int:
        """Remove unapproved candidates exceeding the retention window."""
        count = 0
        for candidate in self._all_entities():
            if self._is_expired(candidate, now=now):
                self._delete_entity(candidate.id)
                count += 1
        return count


InMemoryAuthoringCandidateStore = AuthoringCandidateStore


def verify_author_access(request: Request) -> bool:
    """Verify whether the incoming request is authorized for authoring access.

    Checks credentials against the server-side AppConfig.authoring_secret.
    If authoring_secret is None or empty, authoring access is disabled.
    """
    config: AppConfig = request.app.state.config
    configured_secret = config.authoring_secret
    if not configured_secret or not configured_secret.strip():
        return False

    auth_header = request.headers.get("Authorization")
    cookie_header = request.headers.get("Cookie")
    custom_header = request.headers.get("X-Author-Key") or request.headers.get(
        "X-Author-Token"
    )

    provided_token = extract_authoring_credential(
        authorization_header=auth_header,
        cookie_header=cookie_header,
        custom_header=custom_header,
    )
    return verify_authoring_secret(provided_token, configured_secret)


def require_author_access(request: Request) -> None:
    """FastAPI guard requiring valid authoring authentication.

    Raises HTTPException(401) if authentication is absent or invalid.
    Server-side enforcement ensures downstream handlers (including AI provider
    invocations) are never executed for unauthorized requests.
    """
    if not verify_author_access(request):
        logger.warning(
            "unauthorized authoring access attempt",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client": request.client.host if request.client else None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authoring authentication required.",
            headers={"WWW-Authenticate": 'Bearer realm="Fablit Authoring"'},
        )


def _provider_diagnostics(provider: Any) -> tuple[str, str]:
    """Name the configured provider and model for failure logs (FIX-9).

    Only stable identifiers are returned: the exception message and the
    authoring brief stay out of diagnostics because either can carry provider
    response detail or sensitive request content.
    """
    provider_id = getattr(provider, "provider_id", None)
    model_id = getattr(provider, "model_id", None)
    provider_name = (
        provider_id
        if isinstance(provider_id, str) and provider_id.strip()
        else type(provider).__name__
    )
    model_name = (
        model_id if isinstance(model_id, str) and model_id.strip() else "unknown"
    )
    return provider_name, model_name


async def _invoke_ai_provider(
    request: Request, provider: Any, brief: AuthoringBrief
) -> object:
    """Invoke the provider-neutral generation operation without blocking the loop."""
    fn = getattr(provider, "generate", None)
    if not callable(fn):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI generation service is not configured.",
        )
    try:
        return await asyncio.to_thread(fn, brief)
    except Exception as error:
        provider_name, model_name = _provider_diagnostics(provider)
        logger.error(
            "AI provider generation failed: provider=%s model=%s error=%s",
            provider_name,
            model_name,
            type(error).__name__,
            extra={"path": request.url.path, "method": request.method},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI generation service is temporarily unavailable.",
        ) from None


def _candidate_from_generation_result(
    result: object, brief: AuthoringBrief
) -> PracticeCandidate:
    """Map a provider-neutral result into the stored authoring candidate."""
    candidate_data = getattr(result, "candidate_data", None)
    provider = getattr(result, "provider", None)
    model = getattr(result, "model", None)
    generated_at = getattr(result, "generated_at", None)
    if (
        not isinstance(candidate_data, Mapping)
        or not isinstance(provider, str)
        or not isinstance(model, str)
        or not isinstance(generated_at, datetime)
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI generation service returned an invalid result.",
        )
    try:
        return PracticeCandidate(
            brief=brief,
            candidate_data=candidate_data,
            provider=provider,
            model=model,
            generated_at=generated_at,
        )
    except ValueError as error:
        logger.error(
            "AI provider returned invalid provenance",
            extra={"error_type": type(error).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI generation service returned an invalid result.",
        ) from None


def _candidate_payload(
    candidate: PracticeCandidate,
    publication: PublishedPractice | None = None,
) -> dict[str, Any]:
    """Encode a candidate for authoring responses without provider SDK objects."""
    encoded: object = jsonable_encoder(asdict(candidate))
    if not isinstance(encoded, dict):
        raise TypeError("Authoring candidate must encode to a JSON object.")
    payload: dict[str, Any] = encoded
    payload["title"] = candidate.title
    payload["description"] = candidate.description
    payload["status"] = candidate.status
    payload["is_approved"] = candidate.is_approved
    payload["validation"] = {
        "structural_errors": list(candidate.validation.structural_errors),
        "feedback_errors": list(candidate.validation.feedback_errors),
        "content_warnings": list(candidate.validation.content_warnings),
        "is_approvable": candidate.validation.is_approvable,
    }
    payload["revision"] = candidate.revision
    payload["reviewer"] = candidate.reviewer
    payload["decided_at"] = (
        candidate.decided_at.isoformat() if candidate.decided_at else None
    )
    payload["history"] = [
        {
            "version": h.version,
            "title": h.title,
            "description": h.description,
            "edited_at": h.edited_at.isoformat(),
            "editor": h.editor,
        }
        for h in candidate.history
    ]
    payload["publication"] = (
        {
            "activity_id": str(publication.activity_id),
            "published_at": publication.published_at.isoformat(),
            "published_revision": publication.source_revision,
            "withdrawn_at": (
                publication.withdrawn_at.isoformat()
                if publication.withdrawn_at is not None
                else None
            ),
            "is_withdrawn": publication.is_withdrawn,
        }
        if publication is not None
        else None
    )
    return payload


def _stimulus_query_for(candidate: PracticeCandidate) -> str:
    """Return the one-line scene description used for image search.

    The authoring model supplies ``stimulus_query``. Older or incomplete
    generations fall back to the brief's stimulus requirement, then to the
    practice area and purpose, so image search never blocks generation.
    """
    raw = candidate.candidate_data.get("stimulus_query")
    if isinstance(raw, str) and raw.strip():
        return " ".join(raw.split())
    requirement = candidate.brief.stimulus_requirements
    if isinstance(requirement, str) and requirement.strip():
        return " ".join(requirement.split())
    return " ".join(
        f"{candidate.brief.practice_area}: {candidate.brief.purpose}".split()
    )


def _attach_stimulus_options(
    request: Request, candidate: PracticeCandidate
) -> PracticeCandidate:
    """Search optional images for a generated candidate (SPEC-036).

    A missing provider or a failed search leaves the candidate exactly as it
    was; images are optional and must never block candidate creation.
    """
    provider: ImageSearchProvider | None = getattr(
        request.app.state, "authoring_image_search", None
    )
    if provider is None or not callable(getattr(provider, "search", None)):
        return candidate
    query = _stimulus_query_for(candidate)
    try:
        options = provider.search(query)
    except ImageSearchError:
        logger.warning(
            "stimulus image search failed; continuing without options",
            extra={"candidate_id": str(candidate.id)},
        )
        options = ()
    data = dict(candidate.candidate_data)
    data["stimulus_query"] = query
    data["stimulus_options"] = [
        image_candidate_to_mapping(option) for option in options
    ]
    return dataclasses.replace(candidate, candidate_data=data)


def _candidate_store(request: Request) -> AuthoringCandidateStore:
    """Resolve the app-scoped in-memory authoring candidate store."""
    store: object = request.app.state.authoring_candidate_store
    if not isinstance(store, AuthoringCandidateStore):
        raise RuntimeError("Authoring candidate store is not initialized.")
    return store


def _published_store(request: Request) -> PublishedPracticeStore:
    """Resolve the app-scoped published practice store (SPEC-035 §5)."""
    store: object = request.app.state.published_practice_store
    if not isinstance(store, PublishedPracticeStore):
        raise RuntimeError("Published practice store is not initialized.")
    return store


def _publication_map(request: Request) -> dict[UUID, PublishedPractice]:
    """Publication records keyed by source candidate for workspace rendering.

    Publication metadata is authoring-side only. A store that cannot be read
    degrades the workspace to "no publication shown" (logged, never a false
    publish), so listing candidates still works while publication storage is
    unavailable.
    """
    try:
        records = _published_store(request).list_records()
    except PersistenceError:
        logger.exception("Failed to load published practice records for the workspace")
        return {}
    return {record.source_candidate_id: record for record in records}


#: Candidate stage filters offered on the workspace queue. Every candidate
#: belongs to exactly one of these buckets (plus "all"), so the counts add up.
_AUTHORING_QUEUE_FILTERS: tuple[tuple[str, str], ...] = (
    ("all", "All"),
    ("awaiting", "Awaiting decision"),
    ("ready", "Ready to publish"),
    ("library", "In the learner library"),
    ("withdrawn", "Withdrawn"),
    ("rejected", "Rejected"),
)

_AUTHORING_QUEUE_KEYS = frozenset(key for key, _ in _AUTHORING_QUEUE_FILTERS)

_STATUS_PRESENTATION: dict[str, tuple[str, str]] = {
    "candidate": ("Awaiting your decision", "caution"),
    "approved": ("Approved for the library", "success"),
    "rejected": ("Rejected", "danger"),
}


def _queue_stage(
    candidate: PracticeCandidate, publication: PublishedPractice | None
) -> str:
    """Return the single queue bucket this candidate belongs to (SPEC-035 §5)."""
    if publication is not None:
        return "library" if not publication.is_withdrawn else "withdrawn"
    if candidate.is_approved:
        return "ready"
    if candidate.review_outcome is CandidateReviewOutcome.REJECTED:
        return "rejected"
    return "awaiting"


def _publication_label(publication: PublishedPractice | None) -> str:
    """Describe the publication state in the author's terms."""
    if publication is None:
        return "Not published"
    if publication.is_withdrawn:
        return "Withdrawn from the learner library"
    return "Published to Learner Library"


def _queue_item(
    candidate: PracticeCandidate, publication: PublishedPractice | None
) -> dict[str, Any]:
    """Shape one queue row for rendering without template-side logic."""
    status_label, status_variant = _STATUS_PRESENTATION[candidate.status]
    label = _publication_label(publication)
    return {
        "id": str(candidate.id),
        "url": f"/authoring/candidates/{candidate.id}",
        "title": candidate.title or "Untitled candidate",
        "status_label": status_label,
        "status_variant": status_variant,
        "publication_label": "" if publication is None else label,
        "revision": candidate.revision,
        "generated_at_iso": candidate.generated_at.isoformat(),
        "generated_at_display": candidate.generated_at.isoformat(),
    }


def _queue_view(
    candidates: Iterable[PracticeCandidate],
    publications: Mapping[UUID, PublishedPractice],
    *,
    selected: str,
) -> dict[str, Any]:
    """Build the filter tabs, counts, and newest-first queue rows for the UI."""
    active = selected if selected in _AUTHORING_QUEUE_KEYS else "all"
    entries = sorted(
        ((candidate, publications.get(candidate.id)) for candidate in candidates),
        key=lambda entry: entry[0].generated_at,
        reverse=True,
    )
    stages = {
        candidate.id: _queue_stage(candidate, publication)
        for candidate, publication in entries
    }
    counts = {"all": len(entries)}
    for stage in stages.values():
        counts[stage] = counts.get(stage, 0) + 1

    filters = [
        {
            "key": key,
            "label": label,
            "count": counts.get(key, 0),
            "is_active": key == active,
            "url": "/authoring" if key == "all" else f"/authoring?stage={key}",
        }
        for key, label in _AUTHORING_QUEUE_FILTERS
    ]
    return {
        # Named "rows" because Jinja resolves ``queue.items`` to the dict's own
        # ``items`` method rather than to a key of that name.
        "rows": [
            _queue_item(candidate, publication)
            for candidate, publication in entries
            if active == "all" or stages[candidate.id] == active
        ],
        "filters": filters,
        "total": len(entries),
        "selected": active,
        "all_url": "/authoring",
    }


def _candidate_view(
    candidate: PracticeCandidate, publication: PublishedPractice | None
) -> dict[str, Any]:
    """Describe a candidate's stage and the actions available at that stage."""
    status_label, status_variant = _STATUS_PRESENTATION[candidate.status]
    approvable = candidate.validation.is_approvable
    decided = candidate.review_outcome is not None
    published = publication is not None and not publication.is_withdrawn
    withdrawn = publication is not None and publication.is_withdrawn

    if published:
        note = (
            "This practice is in the learner library. Withdrawing removes it from "
            "discovery; completed learner history stays readable."
        )
    elif withdrawn:
        note = (
            "This practice is no longer in the learner library. It keeps the same "
            "activity identity if you return it."
        )
    elif candidate.review_outcome is CandidateReviewOutcome.REJECTED:
        note = (
            "This candidate was rejected, so it is closed. Editing the draft reopens "
            "it for review."
        )
    elif candidate.is_approved:
        note = (
            "A human approved this content and the checks passed. Learners cannot see "
            "it until it is published."
        )
    elif approvable:
        note = (
            "The checks passed. Approve the content if it matches your intent, or "
            "reject it if it does not."
        )
    else:
        note = (
            "Content checks found issues that block approval. Edit the draft to "
            "resolve them, then save to revalidate."
        )

    if decided:
        decision_state = "done"
    elif approvable:
        decision_state = "current"
    else:
        decision_state = "pending"

    return {
        "title": candidate.title or "Untitled candidate",
        "description": candidate.description,
        "status": candidate.status,
        "status_label": status_label,
        "status_variant": status_variant,
        "publication": publication,
        "publication_label": _publication_label(publication),
        "is_published": published,
        "is_withdrawn": withdrawn,
        "is_approvable": approvable,
        "can_approve": not decided,
        "can_reject": not decided,
        "can_publish": candidate.is_approved and not published,
        "can_withdraw": published,
        "action_note": note,
        "queue_url": "/authoring",
        "stages": [
            {"label": "Generated", "state": "done"},
            {"label": "Content checks", "state": "done" if approvable else "current"},
            {"label": "Human decision", "state": decision_state},
            {
                "label": "In the learner library",
                "state": "done" if published else "pending",
            },
        ],
    }


def _render_workspace(
    request: Request,
    candidates: Iterable[PracticeCandidate],
    *,
    message: str | None = None,
    error: str | None = None,
    brief: object | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """Render the workspace: the authoring brief and the candidate queue."""
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {
            "message": message,
            "error": error,
            "brief": brief,
            "queue": _queue_view(
                candidates,
                _publication_map(request),
                selected=request.query_params.get("stage", "all"),
            ),
        },
        status_code=status_code,
    )


def _candidate_page(
    request: Request,
    candidate: PracticeCandidate,
    *,
    message: str | None = None,
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """Render one candidate: its stage, its content, and its next action."""
    publication = _publication_map(request).get(candidate.id)
    return templates.TemplateResponse(
        request,
        "authoring_candidate.html",
        {
            "candidate": candidate,
            "publication": publication,
            "view": _candidate_view(candidate, publication),
            "message": message,
            "error": error,
        },
        status_code=status_code,
    )


#: Safe retry guidance appended to every HTML generation failure (FIX-9).
_GENERATION_RETRY_HINT = (
    "No candidate was created, and the brief you submitted is still below, "
    "so you can review it and try again."
)


def _generation_failure_response(
    request: Request,
    *,
    brief_values: Mapping[str, object],
    status_code: int,
    detail: str,
) -> Response:
    """Keep the submitted brief on screen when generation fails (FIX-9).

    JSON clients keep the machine-readable error they already rely on. An
    author working in the browser gets the workspace back with every submitted
    value — required and optional — so a provider or configuration failure
    never costs them the brief they just wrote.
    """
    if not wants_html(request):
        raise HTTPException(status_code=status_code, detail=detail)
    try:
        candidates = _candidate_store(request).list()
    except PersistenceError:
        candidates = ()
    return _render_workspace(
        request,
        candidates,
        error=f"{detail} {_GENERATION_RETRY_HINT}",
        brief=brief_values,
        status_code=status_code,
    )


def _learner_registry(request: Request) -> LearnerApplicationRegistry:
    """Resolve the learner application registry publication writes into."""
    registry: object = request.app.state.learner_applications
    if not isinstance(registry, LearnerApplicationRegistry):
        raise RuntimeError("Learner application registry is not initialized.")
    return registry


def _authoring_error_response(
    request: Request,
    *,
    status_code: int,
    detail: str,
    error: Exception,
    candidate_id: str | None = None,
) -> Response:
    """Surface a refused or failed authoring transition to the author.

    JSON clients keep the machine-readable error; an author working in the
    browser (including an htmx-boosted form) gets the candidate back with the
    reason visible, so an invalid state transition or a storage failure is
    never a bare status code or a JSON payload swapped into the page
    (SPEC-035 §9: failures are explicit and visibly explained). The failure
    stays on the candidate's own page and falls back to the workspace queue
    only when that candidate cannot be read.
    """
    if not wants_html(request):
        raise HTTPException(status_code=status_code, detail=detail) from error

    store = _candidate_store(request)
    if candidate_id is not None:
        try:
            return _candidate_page(
                request,
                store.get(candidate_id),
                error=detail,
                status_code=status_code,
            )
        except (PersistenceError, CandidateNotFoundError):
            logger.exception("Failed to reload candidate for a publication error")
    try:
        candidates = store.list()
    except PersistenceError:
        candidates = ()
    return _render_workspace(
        request,
        candidates,
        error=detail,
        status_code=status_code,
    )


@router.get("/login", response_class=HTMLResponse)
async def authoring_login_page(request: Request) -> Response:
    """Render the internal authoring login form.

    If the author is already authenticated, redirects directly to the workspace.
    """
    if verify_author_access(request):
        return RedirectResponse(url="/authoring", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "authoring_login.html", {})


@router.post("/login")
async def authoring_login(request: Request, secret: str = Form("")) -> Response:
    """Authenticate an author session and set the secure session cookie."""
    config: AppConfig = request.app.state.config
    if not config.authoring_secret or not verify_authoring_secret(
        secret, config.authoring_secret
    ):
        return templates.TemplateResponse(
            request,
            "authoring_login.html",
            {"error": "Invalid authoring secret. Access denied."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    response = RedirectResponse(url="/authoring", status_code=status.HTTP_303_SEE_OTHER)
    is_secure = request.url.scheme == "https" or config.environment == "production"
    set_authoring_cookie(
        response,
        secret,
        secure=is_secure,
    )
    return response


@router.post("/logout")
async def authoring_logout(request: Request) -> Response:
    """Terminate the author session by clearing the cookie."""
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    clear_authoring_cookie(response)
    return response


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def authoring_workspace(request: Request) -> Response:
    """Render the internal authoring workspace UI (SPEC-032 / SEC-001)."""
    require_author_access(request)
    try:
        candidates = _candidate_store(request).list()
    except PersistenceError:
        logger.exception("Failed to load authoring candidates")
        return _render_workspace(
            request,
            (),
            message="The authoring candidate store is temporarily unavailable.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return _render_workspace(request, candidates)


@router.post("/generate")
async def authoring_generate(request: Request) -> Response:
    """Server-side AI-generation endpoint for practice candidates.

    Enforces authorization check BEFORE invoking any AI provider logic.
    """
    require_author_access(request)

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            parsed = await request.json()
        except ValueError:
            parsed = None
        if not isinstance(parsed, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="The authoring brief must be a JSON object.",
            )
        brief_values: Mapping[str, object] = parsed
    else:
        form = await request.form()
        brief_values = dict(form)

    try:
        brief = AuthoringBrief.from_mapping(brief_values)
    except InvalidAuthoringBriefError as error:
        message = str(error)
        if "application/json" in content_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=message,
            ) from error
        try:
            candidates = _candidate_store(request).list()
        except PersistenceError:
            candidates = ()
        # A rejected brief is a failure to explain, not a neutral update, so it
        # reaches the author through the alert region with their answers kept.
        return _render_workspace(
            request,
            candidates,
            error=message,
            brief=brief_values,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    ai_provider = getattr(request.app.state, "authoring_ai_provider", None)
    if ai_provider is None:
        return _generation_failure_response(
            request,
            brief_values=brief_values,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI generation service is not configured.",
        )
    try:
        result = await _invoke_ai_provider(request, ai_provider, brief)
        candidate = _candidate_from_generation_result(result, brief)
    except HTTPException as error:
        if error.status_code not in (
            status.HTTP_502_BAD_GATEWAY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ):
            raise
        return _generation_failure_response(
            request,
            brief_values=brief_values,
            status_code=error.status_code,
            detail=str(error.detail),
        )
    candidate = _attach_stimulus_options(request, candidate)
    try:
        _candidate_store(request).add(candidate)
    except PersistenceError as error:
        logger.exception("Failed to persist generated authoring candidate")
        if not wants_html(request):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The authoring candidate store is temporarily unavailable.",
            ) from error
        return _render_workspace(
            request,
            (),
            message="The authoring candidate store is temporarily unavailable.",
            brief=brief_values,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if wants_html(request):
        return _candidate_page(request, candidate)
    return JSONResponse(_candidate_payload(candidate))


@router.get("/candidates")
async def authoring_candidates(request: Request) -> Response:
    """Retrieve practice candidates for human review (SPEC-032 §8)."""
    require_author_access(request)
    try:
        candidates = _candidate_store(request).list()
    except PersistenceError as error:
        logger.exception("Failed to query authoring candidates from store")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error
    publications = _publication_map(request)
    return JSONResponse(
        {
            "candidates": [
                _candidate_payload(candidate, publications.get(candidate.id))
                for candidate in candidates
            ]
        }
    )


@router.get("/candidates/{candidate_id}")
async def authoring_candidate_detail(request: Request, candidate_id: str) -> Response:
    """Retrieve details for a single practice candidate (SPEC-032 §8)."""
    require_author_access(request)
    store = _candidate_store(request)
    try:
        candidate = store.get(candidate_id)
    except CandidateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found.",
        ) from None
    except PersistenceError as error:
        logger.exception("Failed to retrieve candidate from store")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    if wants_html(request):
        return _candidate_page(request, candidate)
    publication = _publication_map(request).get(candidate.id)
    return JSONResponse(_candidate_payload(candidate, publication))


@router.post("/candidates/{candidate_id}/stimulus")
async def authoring_select_stimulus(request: Request, candidate_id: str) -> Response:
    """Select or clear a candidate's optional stimulus image (SPEC-036)."""
    require_author_access(request)
    store = _candidate_store(request)
    try:
        candidate = store.get(candidate_id)
    except CandidateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found.",
        ) from None
    except PersistenceError as error:
        logger.exception("Failed to retrieve candidate before image selection")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    photo_id: str | None = None
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            parsed = await request.json()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid JSON payload.",
            ) from None
        if isinstance(parsed, Mapping):
            raw = parsed.get("photo_id")
            photo_id = str(raw) if raw is not None else None
    else:
        form = await request.form()
        raw = form.get("photo_id")
        photo_id = str(raw) if raw is not None else None

    try:
        updated = store.select_stimulus(candidate.id, photo_id)
    except InvalidStimulusSelectionError as error:
        return _authoring_error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
            error=error,
            candidate_id=candidate_id,
        )
    except PersistenceError as error:
        logger.exception("Failed to save selected stimulus image")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    message = (
        f"“{updated.title}” will use this image."
        if updated.stimulus is not None
        else f"“{updated.title}” has no stimulus image."
    )
    if wants_html(request):
        return _candidate_page(request, updated, message=message)
    return JSONResponse(
        _candidate_payload(updated, _publication_map(request).get(updated.id)),
        status_code=status.HTTP_200_OK,
    )


@router.post("/candidates/{candidate_id}/approve")
async def authoring_approve_candidate(request: Request, candidate_id: str) -> Response:
    """Human review approval gate (SPEC-032 §8)."""
    require_author_access(request)
    store = _candidate_store(request)
    try:
        candidate = store.get(candidate_id)
    except CandidateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found.",
        ) from None
    except PersistenceError as error:
        logger.exception("Failed to retrieve candidate before approval")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    try:
        approved = store.approve(candidate.id, reviewer="author")
    except CandidateNotApprovableError as error:
        err_msg = str(error)
        conflict = (
            "already approved" in err_msg
            or "already rejected" in err_msg
            or "Rejected candidate" in err_msg
            or "Approved candidate" in err_msg
        )
        return _authoring_error_response(
            request,
            status_code=(
                status.HTTP_409_CONFLICT
                if conflict
                else status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=err_msg,
            error=error,
            candidate_id=candidate_id,
        )
    except PersistenceError as error:
        logger.exception("Failed to save approval to store")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    if wants_html(request):
        return _candidate_page(
            request,
            approved,
            message=f"“{approved.title}” is approved for the curated library.",
        )
    return JSONResponse(
        {"status": "approved", "candidate_id": str(candidate_id)},
        status_code=status.HTTP_200_OK,
    )


@router.post("/candidates/{candidate_id}/reject")
async def authoring_reject_candidate(request: Request, candidate_id: str) -> Response:
    """Human review rejection gate (SPEC-032 §8)."""
    require_author_access(request)
    store = _candidate_store(request)
    try:
        candidate = store.get(candidate_id)
    except CandidateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found.",
        ) from None
    except PersistenceError as error:
        logger.exception("Failed to retrieve candidate before rejection")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    try:
        rejected = store.reject(candidate.id, reviewer="author")
    except CandidateNotApprovableError as error:
        return _authoring_error_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
            error=error,
            candidate_id=candidate_id,
        )
    except PersistenceError as error:
        logger.exception("Failed to save rejection to store")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    if wants_html(request):
        return _candidate_page(
            request,
            rejected,
            message=f"“{rejected.title}” was rejected.",
        )
    return JSONResponse(
        {"status": "rejected", "candidate_id": str(candidate_id)},
        status_code=status.HTTP_200_OK,
    )


@router.post("/candidates/{candidate_id}/edit")
async def authoring_edit_candidate(request: Request, candidate_id: str) -> Response:
    """Author editing gate: revalidates candidate and increments revision."""
    require_author_access(request)
    store = _candidate_store(request)
    try:
        candidate = store.get(candidate_id)
    except CandidateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found.",
        ) from None
    except PersistenceError as error:
        logger.exception("Failed to retrieve candidate before edit")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    content_type = request.headers.get("content-type", "")
    updates: dict[str, Any] = {}
    if "application/json" in content_type:
        try:
            parsed = await request.json()
            if isinstance(parsed, dict):
                updates = parsed
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid JSON payload.",
            ) from None
    else:
        form = await request.form()
        for key, value in form.items():
            if isinstance(value, str) and value.strip():
                updates[key] = value.strip()

    try:
        edited = store.edit(candidate.id, updates=updates, editor="author")
    except PersistenceError as error:
        logger.exception("Failed to save edited candidate to store")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    if wants_html(request):
        return _candidate_page(
            request,
            edited,
            message=f"“{edited.title}” was saved as revision {edited.revision}.",
        )
    return JSONResponse(
        _candidate_payload(edited, _publication_map(request).get(edited.id)),
        status_code=status.HTTP_200_OK,
    )


def _publication_response(
    request: Request,
    *,
    message: str,
    record: PublishedPractice,
    candidate_id: str,
    status_text: str,
) -> Response:
    """Render the authoring outcome for JSON clients and the workspace UI."""
    if not wants_html(request):
        return JSONResponse(
            {
                "status": status_text,
                "candidate_id": candidate_id,
                "activity_id": str(record.activity_id),
                "revision": record.source_revision,
                "withdrawn_at": (
                    record.withdrawn_at.isoformat()
                    if record.withdrawn_at is not None
                    else None
                ),
            },
            status_code=status.HTTP_200_OK,
        )
    store = _candidate_store(request)
    try:
        candidates = store.list()
        candidate: PracticeCandidate | None = store.get(candidate_id)
    except (PersistenceError, CandidateNotFoundError):
        candidates, candidate = (), None
    if candidate is None:
        return _render_workspace(request, candidates, message=message)
    return _candidate_page(request, candidate, message=message)


@router.post("/candidates/{candidate_id}/publish")
async def authoring_publish_candidate(request: Request, candidate_id: str) -> Response:
    """Explicit publish action: approved candidate → learner library (SPEC-035 §5).

    Publication is a deliberate human action, never a side effect of
    generation or approval. The boundary revalidates content and approval
    state, writes the publication through the published practice store
    first, and only then hands the record to the learner-facing registry —
    so a storage failure is reported as a failure and never leaves content
    learners can see but the store does not keep.
    """
    require_author_access(request)
    store = _candidate_store(request)
    try:
        candidate = store.get(candidate_id)
    except CandidateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found.",
        ) from None
    except PersistenceError as error:
        logger.exception("Failed to retrieve candidate before publication")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    registry = _learner_registry(request)
    published_store = _published_store(request)
    try:
        record = publish_candidate(
            candidate,
            store=published_store,
            position=registry.next_activity_position(),
        )
    except CandidateContentNotPublishableError as error:
        return _authoring_error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
            error=error,
            candidate_id=candidate_id,
        )
    except CandidateNotPublishableError as error:
        return _authoring_error_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
            error=error,
            candidate_id=candidate_id,
        )
    except PersistenceError as error:
        logger.exception(
            "Failed to persist candidate publication",
            extra={"candidate_id": str(candidate.id)},
        )
        return _authoring_error_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The published practice store is temporarily unavailable.",
            error=error,
            candidate_id=candidate_id,
        )

    # Only after the write succeeded does the learner-facing catalogue learn
    # about the publication (SPEC-035 §9: no misleading partial state).
    registry.record_publication(record)
    logger.info(
        "practice candidate published",
        extra={
            "candidate_id": str(candidate.id),
            "activity_id": str(record.activity_id),
            "revision": record.source_revision,
        },
    )
    return _publication_response(
        request,
        message=(
            f"“{candidate.title}” is now in the learner library "
            f"(revision {record.source_revision})."
        ),
        record=record,
        candidate_id=candidate_id,
        status_text="published",
    )


@router.post("/candidates/{candidate_id}/withdraw")
async def authoring_withdraw_candidate(request: Request, candidate_id: str) -> Response:
    """Withdraw a published practice from learner discovery (SPEC-035 §8).

    The minimal explicit withdrawal policy: the practice stops appearing in
    learner discovery while completed learner history and the publication
    record stay intact, and the source candidate can be republished later.
    """
    require_author_access(request)
    try:
        source_candidate_id = UUID(candidate_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found.",
        ) from None

    registry = _learner_registry(request)
    published_store = _published_store(request)
    try:
        record = withdraw_publication(source_candidate_id, store=published_store)
    except PublishedPracticeNotFoundError as error:
        return _authoring_error_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
            error=error,
            candidate_id=candidate_id,
        )
    except PersistenceError as error:
        logger.exception(
            "Failed to persist publication withdrawal",
            extra={"candidate_id": candidate_id},
        )
        return _authoring_error_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The published practice store is temporarily unavailable.",
            error=error,
            candidate_id=candidate_id,
        )

    registry.record_publication(record)
    logger.info(
        "practice candidate withdrawn from the learner library",
        extra={"candidate_id": candidate_id, "activity_id": str(record.activity_id)},
    )
    return _publication_response(
        request,
        message=(f"“{record.activity.title}” was withdrawn from the learner library."),
        record=record,
        candidate_id=candidate_id,
        status_text="withdrawn",
    )
