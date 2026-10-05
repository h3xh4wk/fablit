"""Internal AI authoring access and management router (SEC-001).

SPEC-032 introduces an internal AI-assisted practice authoring workflow.
SEC-001 enforces the security boundary around authoring before SPEC-032
is implemented:
- All authoring routes and AI-generation operations are protected server-side.
- Access requires a shared authoring secret configured via FABLIT_AUTHORING_SECRET.
- When unconfigured, authoring access is disabled by default.
- Unauthorized requests are strictly rejected before invoking the AI provider.
- Public learner routes remain anonymous and completely unaffected.
"""

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

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


async def _invoke_ai_provider(
    provider: Any, brief_data: dict[str, Any]
) -> dict[str, Any]:
    """Invoke the configured AI authoring provider safely."""
    if hasattr(provider, "generate_candidate"):
        fn = provider.generate_candidate
    elif callable(provider):
        fn = provider
    else:
        return {"status": "unsupported_provider"}

    try:
        if inspect.iscoroutinefunction(fn):
            result = await fn(brief_data)
        else:
            result = fn(brief_data)
        return result if isinstance(result, dict) else {"candidate": result}
    except Exception:
        logger.exception("AI provider generation error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI generation service is temporarily unavailable.",
        ) from None


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
    return templates.TemplateResponse(request, "authoring.html", {})


@router.post("/generate")
async def authoring_generate(request: Request) -> Response:
    """Server-side AI-generation endpoint for practice candidates.

    Enforces authorization check BEFORE invoking any AI provider logic.
    """
    require_author_access(request)

    brief_data: dict[str, Any] = {}
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            parsed = await request.json()
            if isinstance(parsed, dict):
                brief_data = parsed
        except Exception:
            brief_data = {}
    else:
        form = await request.form()
        brief_data = dict(form)

    ai_provider = getattr(request.app.state, "authoring_ai_provider", None)
    if ai_provider is not None:
        candidate = await _invoke_ai_provider(ai_provider, brief_data)
    else:
        candidate = {
            "id": "candidate-draft-1",
            "status": "candidate",
            "brief": brief_data,
            "activity": {
                "title": brief_data.get("practice_area") or "Generated Practice",
                "instructions": (
                    brief_data.get("learning_focus")
                    or "Practice drafted by AI authoring."
                ),
            },
        }

    accept = request.headers.get("accept", "")
    if "application/json" in accept or "application/json" in content_type:
        return JSONResponse(candidate)

    return templates.TemplateResponse(
        request,
        "authoring.html",
        {"candidate": candidate, "brief": brief_data},
    )


@router.get("/candidates")
async def authoring_candidates(request: Request) -> Response:
    """Retrieve practice candidates for human review (SPEC-032 §8)."""
    require_author_access(request)
    return JSONResponse({"candidates": []})


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
