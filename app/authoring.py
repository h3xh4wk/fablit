"""Protected internal practice-authoring workflow (SPEC-032 / SEC-001).

The workflow validates typed authoring briefs before provider invocation and
stores untrusted provider-neutral candidate data with provenance. Candidate
quality validation and the complete review lifecycle remain separate gates.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
from collections.abc import Mapping
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

from fablit.application.authoring import (
    _CONTRACT_FIELDS,
    AuthoringRevision,
    CandidateStatus,
    CandidateValidation,
    validate_candidate,
)
from fablit.application.demo_data import PRACTICE_CAPABILITIES
from fablit.application.errors import (
    CandidateNotApprovableError,
    CandidateNotFoundError,
)
from fablit.application.persistence import PersistenceError
from fablit.application.practice_modes import PracticeMode
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

router = APIRouter(prefix="/authoring")


class InvalidAuthoringBriefError(ValueError):
    """Raised when an authoring brief is incomplete or contains unsupported values."""


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


async def _invoke_ai_provider(provider: Any, brief: AuthoringBrief) -> object:
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
        logger.error(
            "AI provider generation failed",
            extra={"error_type": type(error).__name__},
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


def _candidate_payload(candidate: PracticeCandidate) -> dict[str, Any]:
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
    return payload


def _candidate_store(request: Request) -> AuthoringCandidateStore:
    """Resolve the app-scoped in-memory authoring candidate store."""
    store: object = request.app.state.authoring_candidate_store
    if not isinstance(store, AuthoringCandidateStore):
        raise RuntimeError("Authoring candidate store is not initialized.")
    return store


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
        return templates.TemplateResponse(
            request,
            "authoring.html",
            {
                "message": "The authoring candidate store is temporarily unavailable.",
                "candidates": (),
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {"candidates": candidates},
    )


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
        return templates.TemplateResponse(
            request,
            "authoring.html",
            {
                "message": message,
                "brief": brief_values,
                "candidates": candidates,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    ai_provider = getattr(request.app.state, "authoring_ai_provider", None)
    if ai_provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI generation service is not configured.",
        )
    result = await _invoke_ai_provider(ai_provider, brief)
    candidate = _candidate_from_generation_result(result, brief)
    accept = request.headers.get("accept", "")
    try:
        _candidate_store(request).add(candidate)
    except PersistenceError as error:
        logger.exception("Failed to persist generated authoring candidate")
        if "application/json" in accept or "application/json" in content_type:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The authoring candidate store is temporarily unavailable.",
            ) from error
        return templates.TemplateResponse(
            request,
            "authoring.html",
            {
                "message": "The authoring candidate store is temporarily unavailable.",
                "brief": brief_values,
                "candidates": (),
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    candidate_payload = _candidate_payload(candidate)

    accept = request.headers.get("accept", "")
    if "application/json" in accept or "application/json" in content_type:
        return JSONResponse(candidate_payload)

    return templates.TemplateResponse(
        request,
        "authoring.html",
        {
            "candidate": candidate,
            "brief": brief,
            "candidates": _candidate_store(request).list(),
        },
    )


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
    return JSONResponse(
        {"candidates": [_candidate_payload(candidate) for candidate in candidates]}
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

    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
        try:
            candidates = store.list()
        except PersistenceError:
            candidates = ()
        return templates.TemplateResponse(
            request,
            "authoring.html",
            {
                "candidate": candidate,
                "brief": candidate.brief,
                "candidates": candidates,
            },
        )
    return JSONResponse(_candidate_payload(candidate))


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
        if (
            "already approved" in err_msg
            or "already rejected" in err_msg
            or "Rejected candidate" in err_msg
            or "Approved candidate" in err_msg
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=err_msg,
            ) from error
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=err_msg,
        ) from error
    except PersistenceError as error:
        logger.exception("Failed to save approval to store")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    accept = request.headers.get("accept", "")
    content_type = request.headers.get("content-type", "")
    if (
        "application/json" in accept
        or "application/json" in content_type
        or ("text/html" not in accept and "*/*" in accept)
    ):
        return JSONResponse(
            {"status": "approved", "candidate_id": str(candidate_id)},
            status_code=status.HTTP_200_OK,
        )
    try:
        candidates = store.list()
    except PersistenceError:
        candidates = ()
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {
            "message": f"Candidate {candidate_id} approved for curated library.",
            "candidate": approved,
            "candidates": candidates,
        },
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except PersistenceError as error:
        logger.exception("Failed to save rejection to store")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authoring candidate store is temporarily unavailable.",
        ) from error

    accept = request.headers.get("accept", "")
    content_type = request.headers.get("content-type", "")
    if (
        "application/json" in accept
        or "application/json" in content_type
        or ("text/html" not in accept and "*/*" in accept)
    ):
        return JSONResponse(
            {"status": "rejected", "candidate_id": str(candidate_id)},
            status_code=status.HTTP_200_OK,
        )
    try:
        candidates = store.list()
    except PersistenceError:
        candidates = ()
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {
            "message": f"Candidate {candidate_id} rejected.",
            "candidate": rejected,
            "candidates": candidates,
        },
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

    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
        try:
            candidates = store.list()
        except PersistenceError:
            candidates = ()
        return templates.TemplateResponse(
            request,
            "authoring.html",
            {
                "message": (
                    f"Candidate {candidate_id} updated (revision {edited.revision})."
                ),
                "candidate": edited,
                "candidates": candidates,
            },
        )
    return JSONResponse(
        _candidate_payload(edited),
        status_code=status.HTTP_200_OK,
    )
