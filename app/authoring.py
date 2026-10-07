"""Internal AI authoring access and management router (SEC-001, SPEC-032).

SPEC-032 introduces an internal AI-assisted practice authoring workflow.
SEC-001 enforces the security boundary around authoring:
- All authoring routes and AI-generation operations are protected server-side.
- Access requires a shared authoring secret configured via FABLIT_AUTHORING_SECRET.
- When unconfigured, authoring access is disabled by default.
- Unauthorized requests are strictly rejected before invoking the AI provider.
- Public learner routes remain anonymous and completely unaffected.

SPEC-032 adds the workflow itself on top of that boundary: a structured
authoring brief, provider-agnostic candidate generation, structural and
feedback validation, an explicit human approval gate, editing, and rejection.
Only approved candidates are exposed as curated library content.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from fablit.application import (
    AuthoringCandidateStore,
    AuthoringGenerationRequest,
    AuthoringLlmProvider,
    AuthoringProviderError,
    CandidateNotApprovableError,
    CandidateNotFoundError,
    InvalidAuthoringBriefError,
    LlmGenerationResult,
    PracticeAuthoringBrief,
    PracticeContentContract,
    PracticeMode,
    candidate_from_provider_output,
    draft_candidate_from_brief,
    serialize_candidate,
)
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

_CONTRACT_FIELDS: tuple[str, ...] = (
    "purpose",
    "task",
    "expected_thinking",
    "response_contract",
    "evaluation_intent",
    "feedback_intent",
    "reflection_intent",
    "continuation_intent",
)


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


def _candidate_store(request: Request) -> AuthoringCandidateStore:
    """Return the process-wide authoring candidate store."""
    return cast(AuthoringCandidateStore, request.app.state.authoring_candidates)


def _reviewer_name(request: Request) -> str:
    """Identify the reviewing author for provenance (never learner data)."""
    return request.headers.get("X-Author-Name", "").strip() or "internal-author"


#: A single, provider-agnostic message so no provider detail reaches clients.
_PROVIDER_UNAVAILABLE_DETAIL = "The AI generation service is temporarily unavailable."


async def _generate_with_provider(
    provider: AuthoringLlmProvider, brief: PracticeAuthoringBrief
) -> LlmGenerationResult:
    """Request a candidate through the provider-neutral LLM port (ARCH-001).

    The concrete adapter is invoked off the event loop because provider
    transport is blocking I/O. Provider failures are translated into a safe
    ``502`` here: the workflow depends only on the port, never on a vendor
    SDK's exception types, and no learner-facing content is produced.
    """
    request = AuthoringGenerationRequest(brief=brief)
    try:
        result = await run_in_threadpool(provider.generate_candidate, request)
    except AuthoringProviderError:
        logger.warning(
            "authoring provider unavailable",
            extra={"provider": getattr(provider, "provider_id", "unknown")},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_PROVIDER_UNAVAILABLE_DETAIL,
        ) from None
    except Exception:
        logger.exception("AI provider generation error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_PROVIDER_UNAVAILABLE_DETAIL,
        ) from None

    if not isinstance(result, LlmGenerationResult):
        logger.error("authoring provider returned an unsupported result")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_PROVIDER_UNAVAILABLE_DETAIL,
        )
    return result


async def _request_data(request: Request) -> dict[str, Any]:
    """Read a request body as a plain mapping from JSON or form data."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            parsed = await request.json()
        except Exception:
            return {}
        return dict(parsed) if isinstance(parsed, Mapping) else {}
    form = await request.form()
    return {key: value for key, value in form.items() if isinstance(value, str)}


def _text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    return value.strip() if isinstance(value, str) else ""


def _parse_brief(data: Mapping[str, Any]) -> PracticeAuthoringBrief:
    """Build a structured authoring brief from request data (SPEC-032 §4)."""
    mode_raw = _text(data, "practice_mode") or _text(data, "mode_intent")
    mode_raw = mode_raw or PracticeMode.FULL_PRACTICE.value
    try:
        practice_mode = PracticeMode(mode_raw)
    except ValueError:
        raise InvalidAuthoringBriefError(
            f"unsupported practice mode {mode_raw!r}; choose from "
            f"{', '.join(mode.value for mode in PracticeMode)}"
        ) from None

    constraints_raw = data.get("constraints")
    if isinstance(constraints_raw, str):
        constraints = tuple(
            line.strip() for line in constraints_raw.splitlines() if line.strip()
        )
    elif isinstance(constraints_raw, list | tuple):
        constraints = tuple(
            str(item).strip() for item in constraints_raw if str(item).strip()
        )
    else:
        constraints = ()

    purpose = _text(data, "practice_purpose") or _text(data, "learning_focus")
    return PracticeAuthoringBrief(
        practice_area=_text(data, "practice_area"),
        practice_purpose=purpose,
        task=_text(data, "task") or purpose,
        response_form=_text(data, "response_form"),
        primary_capability=_text(data, "primary_capability"),
        practice_mode=practice_mode,
        learner_context=_text(data, "learner_context") or _text(data, "learning_focus"),
        expected_thinking=_text(data, "expected_thinking"),
        evaluation_intent=_text(data, "evaluation_intent"),
        feedback_intent=_text(data, "feedback_intent"),
        reflection_intent=_text(data, "reflection_intent"),
        continuation_intent=_text(data, "continuation_intent"),
        examination_context=_text(data, "examination_context") or None,
        secondary_capability=_text(data, "secondary_capability") or None,
        stimulus_requirements=_text(data, "stimulus_requirements")
        or _text(data, "stimulus_intent"),
        constraints=constraints,
    )


def _contract_from_request(data: Mapping[str, Any]) -> PracticeContentContract | None:
    """Build a SPEC-029 contract from an edit request, if all fields present."""
    nested = data.get("contract")
    source: Mapping[str, Any] = nested if isinstance(nested, Mapping) else data
    values: dict[str, str] = {}
    for name in _CONTRACT_FIELDS:
        raw = source.get(name)
        if not isinstance(raw, str) or not raw.strip():
            return None
        values[name] = raw.strip()
    try:
        return PracticeContentContract(**values)
    except Exception:
        return None


def _wants_json(request: Request) -> bool:
    """Whether to answer an authoring request with JSON rather than HTML.

    JSON is the default for non-browser clients; an explicit ``text/html``
    preference (the browser workspace) gets the rendered page.
    """
    accept = request.headers.get("accept", "")
    content_type = request.headers.get("content-type", "")
    if "application/json" in accept or "application/json" in content_type:
        return True
    return "text/html" not in accept and "*/*" in accept


def _candidate_error(exc: Exception) -> HTTPException:
    """Map an authoring workflow error onto an HTTP response."""
    if isinstance(exc, CandidateNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
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
    store = _candidate_store(request)
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {
            "candidates": [
                serialize_candidate(candidate) for candidate in store.list_candidates()
            ],
            "approved": [
                serialize_candidate(candidate)
                for candidate in store.approved_practices()
            ],
        },
    )


@router.post("/generate")
async def authoring_generate(request: Request) -> Response:
    """Generate a validated practice candidate from an authoring brief.

    Enforces authorization BEFORE invoking any AI provider logic. Provider
    failure never affects learner practice, and malformed output becomes a
    non-approvable candidate rather than entering the approval path.
    """
    require_author_access(request)

    data = await _request_data(request)
    try:
        brief = _parse_brief(data)
    except InvalidAuthoringBriefError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from None

    provider: AuthoringLlmProvider | None = getattr(
        request.app.state, "authoring_ai_provider", None
    )
    if provider is not None:
        result = await _generate_with_provider(provider, brief)
        candidate = candidate_from_provider_output(
            result.output,
            brief,
            provider=result.provider,
            model=result.model,
            generated_at=datetime.now(UTC),
        )
    else:
        candidate = draft_candidate_from_brief(brief)

    candidate = _candidate_store(request).add(candidate)
    view = serialize_candidate(candidate)

    if _wants_json(request):
        return JSONResponse(view)

    return templates.TemplateResponse(
        request,
        "authoring.html",
        {
            "candidate": view,
            "brief": brief.as_dict(),
            "candidates": [
                serialize_candidate(item)
                for item in _candidate_store(request).list_candidates()
            ],
        },
    )


@router.get("/candidates")
async def authoring_candidates(request: Request) -> Response:
    """Retrieve practice candidates for human review (SPEC-032 §8)."""
    require_author_access(request)
    store = _candidate_store(request)
    return JSONResponse(
        {
            "candidates": [
                serialize_candidate(candidate) for candidate in store.list_candidates()
            ],
            "approved": [
                serialize_candidate(candidate)
                for candidate in store.approved_practices()
            ],
        }
    )


@router.post("/candidates/{candidate_id}/approve")
async def authoring_approve_candidate(request: Request, candidate_id: str) -> Response:
    """Human review approval gate (SPEC-032 §8).

    Approval is refused unless the candidate exists and has passed structural
    and feedback validation.
    """
    require_author_access(request)
    try:
        candidate = _candidate_store(request).approve(
            _candidate_uuid(candidate_id), reviewer=_reviewer_name(request)
        )
    except (CandidateNotFoundError, CandidateNotApprovableError) as exc:
        raise _candidate_error(exc) from None

    if _wants_json(request):
        return JSONResponse(serialize_candidate(candidate))
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {
            "message": f"Candidate {candidate_id} approved for curated library.",
            "approved": [serialize_candidate(candidate)],
        },
    )


@router.post("/candidates/{candidate_id}/reject")
async def authoring_reject_candidate(request: Request, candidate_id: str) -> Response:
    """Human review rejection gate (SPEC-032 §8)."""
    require_author_access(request)
    try:
        candidate = _candidate_store(request).reject(
            _candidate_uuid(candidate_id), reviewer=_reviewer_name(request)
        )
    except CandidateNotFoundError as exc:
        raise _candidate_error(exc) from None

    if _wants_json(request):
        return JSONResponse(serialize_candidate(candidate))
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {"message": f"Candidate {candidate_id} rejected."},
    )


@router.post("/candidates/{candidate_id}/edit")
async def authoring_edit_candidate(request: Request, candidate_id: str) -> Response:
    """Edit a candidate before approval (SPEC-032 §11).

    Editing produces a new revision; the superseded version is retained for
    traceability. AI output is a draft, so the author may change wording,
    task, response form, evaluation/feedback intent, reflection, continuation,
    and stimulus context.
    """
    require_author_access(request)
    data = await _request_data(request)
    try:
        candidate = _candidate_store(request).edit(
            _candidate_uuid(candidate_id),
            editor=_reviewer_name(request),
            title=_text(data, "title") or None,
            description=_text(data, "description") or None,
            contract=_contract_from_request(data),
        )
    except CandidateNotFoundError as exc:
        raise _candidate_error(exc) from None

    if _wants_json(request):
        return JSONResponse(serialize_candidate(candidate))
    return templates.TemplateResponse(
        request,
        "authoring.html",
        {
            "message": f"Candidate {candidate_id} updated for review.",
            "candidate": serialize_candidate(candidate),
        },
    )


def _candidate_uuid(candidate_id: str) -> UUID:
    try:
        return UUID(candidate_id)
    except ValueError:
        raise CandidateNotFoundError(
            f"authoring candidate {candidate_id} was not found"
        ) from None
