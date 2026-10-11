"""Protected internal practice-authoring workflow (SPEC-032 / SEC-001).

The workflow validates typed authoring briefs before provider invocation and
stores untrusted provider-neutral candidate data with provenance. Candidate
quality validation and the complete review lifecycle remain separate gates.
"""

from __future__ import annotations

import asyncio
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

from fablit.application.demo_data import PRACTICE_CAPABILITIES
from fablit.application.practice_modes import PracticeMode
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

    def __post_init__(self) -> None:
        """Validate candidate identity and provenance, not educational content."""
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

    @property
    def status(self) -> str:
        """Return the display status while review state is still pending."""
        return self.review_outcome.value if self.review_outcome else "candidate"


class AuthoringCandidateStore:
    """Small process-local store for candidates in the protected authoring flow."""

    def __init__(self) -> None:
        self._candidates: dict[UUID, PracticeCandidate] = {}

    def add(self, candidate: PracticeCandidate) -> None:
        """Store a generated candidate under its stable identity."""
        if candidate.id in self._candidates:
            raise ValueError(f"candidate already exists: {candidate.id}")
        self._candidates[candidate.id] = candidate

    def get(self, candidate_id: UUID) -> PracticeCandidate | None:
        """Return a candidate by identity, or None when it is not stored."""
        return self._candidates.get(candidate_id)

    def list(self) -> tuple[PracticeCandidate, ...]:
        """Return stored candidates in insertion order."""
        return tuple(self._candidates.values())


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
    payload["status"] = candidate.status
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
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {"candidates": _candidate_store(request).list()},
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
        return templates.TemplateResponse(
            request,
            "authoring.html",
            {
                "message": message,
                "brief": brief_values,
                "candidates": _candidate_store(request).list(),
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
    _candidate_store(request).add(candidate)
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
    candidates = _candidate_store(request).list()
    return JSONResponse(
        {"candidates": [_candidate_payload(candidate) for candidate in candidates]}
    )


@router.post("/candidates/{candidate_id}/approve")
async def authoring_approve_candidate(request: Request, candidate_id: str) -> Response:
    """Human review approval gate (SPEC-032 §8)."""
    require_author_access(request)
    accept = request.headers.get("accept", "")
    content_type = request.headers.get("content-type", "")
    if (
        "application/json" in accept
        or "application/json" in content_type
        or ("text/html" not in accept and "*/*" in accept)
    ):
        return JSONResponse({"status": "approved", "candidate_id": candidate_id})
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {"message": f"Candidate {candidate_id} approved for curated library."},
    )


@router.post("/candidates/{candidate_id}/reject")
async def authoring_reject_candidate(request: Request, candidate_id: str) -> Response:
    """Human review rejection gate (SPEC-032 §8)."""
    require_author_access(request)
    accept = request.headers.get("accept", "")
    content_type = request.headers.get("content-type", "")
    if (
        "application/json" in accept
        or "application/json" in content_type
        or ("text/html" not in accept and "*/*" in accept)
    ):
        return JSONResponse({"status": "rejected", "candidate_id": candidate_id})
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {"message": f"Candidate {candidate_id} rejected."},
    )
