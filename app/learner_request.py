"""Learner-requested private practice routes (SPEC-044 §5.2, §10).

The request flow is deliberately short: a free-text intent, a few optional
controls, and an explicit submit action. Generation starts only from that
action, the learner sees the validated brief before starting, and the result
is persisted privately and revisited from the learner's own request history.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.learner_session import learner_id_for_request, practice_for_request
from fablit.application.errors import (
    GeneratedPracticeValidationError,
    InvalidLearnerPracticeRequestError,
    LearnerPracticeGenerationError,
    LearnerPracticeRateLimitError,
)
from fablit.application.learner_practice import (
    CHALLENGE_LABELS,
    DEFAULT_GENERATION_CLAIM_TTL_SECONDS,
    DEFAULT_LEARNER_PRACTICE_RATE_LIMIT,
    DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS,
    DEFAULT_RESPONSE_FORM,
    GENERATION_UNAVAILABLE_MESSAGE,
    MAX_REQUEST_CHARS,
    PRACTICE_AREA_LABELS,
    ChallengePreference,
    GeneratedPracticeRepository,
    HistoryContext,
    LearnerPracticeGenerator,
    PracticeArea,
    PracticeRequest,
    generate_private_practice,
    new_request_token,
)
from fablit.application.news import NewsRepository
from fablit.application.persistence import PersistenceError

BASE_DIR = Path(__file__).resolve().parent
_PULSE_URL = "/pulse"
logger = logging.getLogger("fablit.learner.request")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

router = APIRouter()

_REQUEST_URL = "/practice/request"

_RESPONSE_FORMS = (
    "A short written response",
    "A detailed written response",
    "A plan or set of notes",
    "A reflection",
)


def _generated_practice_repository(
    request: Request,
) -> GeneratedPracticeRepository | None:
    repository: object = getattr(
        request.app.state, "generated_practice_repository", None
    )
    return repository if isinstance(repository, GeneratedPracticeRepository) else None


def _learner_practice_generator(
    request: Request,
) -> LearnerPracticeGenerator | None:
    generator: object = getattr(request.app.state, "learner_practice_generator", None)
    return generator if isinstance(generator, LearnerPracticeGenerator) else None


def _rate_limit_settings(request: Request) -> tuple[int, int]:
    config: object = getattr(request.app.state, "config", None)
    limit = getattr(
        config, "learner_practice_rate_limit", DEFAULT_LEARNER_PRACTICE_RATE_LIMIT
    )
    window = getattr(
        config,
        "learner_practice_rate_window_seconds",
        DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS,
    )
    return int(limit), int(window)


def _claim_ttl_seconds(request: Request) -> int:
    config: object = getattr(request.app.state, "config", None)
    ttl = getattr(
        config,
        "learner_practice_claim_ttl_seconds",
        DEFAULT_GENERATION_CLAIM_TTL_SECONDS,
    )
    return int(ttl)


def _error_response(
    request: Request,
    message: str,
    *,
    status_code: int = 404,
    description: str | None = None,
) -> Response:
    return templates.TemplateResponse(
        request,
        "error.html",
        {"message": message, "description": description},
        status_code=status_code,
    )


def _story_context(request: Request, story_id: str | None) -> dict[str, str] | None:
    """Resolve an optional story prefill for the request composer (SPEC-044 §6.1).

    A story contributes only its "What to try" prompt and reader-facing
    provenance. The learner can edit the prefilled text freely, and a missing
    story, a story without a prompt, or an unavailable feed simply leaves the
    composer empty rather than blocking the request.
    """
    if not story_id:
        return None
    try:
        parsed_id = UUID(story_id)
    except (ValueError, AttributeError):
        return None
    repository: object = getattr(request.app.state, "news_repository", None)
    if not isinstance(repository, NewsRepository):
        return None
    try:
        story = repository.get(parsed_id)
    except PersistenceError:
        logger.exception("news feed unavailable for practice request prefill")
        return None
    if story is None or not story.reflection_prompt:
        return None
    return {
        "story_id": str(story.story_id),
        "headline": story.headline,
        "source_name": story.source_name,
        "prompt": story.reflection_prompt,
        "anchor": f"{_PULSE_URL}#story-{story.story_id}",
    }


def _include_history(value: str) -> bool:
    """Return True only when the learner explicitly opted in to history context."""
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _request_view(
    practice: Any,
    *,
    token: str | None = None,
    request_text: str = "",
    story_context: dict[str, str] | None = None,
    area: str = PracticeArea.CREATIVE_ABILITY.value,
    challenge: str = ChallengePreference.FAMILIAR.value,
    response_form: str = DEFAULT_RESPONSE_FORM,
    examination_context: str = "",
    include_history: bool = False,
    error: str | None = None,
    is_available: bool = True,
    status_message: str | None = None,
) -> dict[str, Any]:
    """Build the request form with preserved values and private history."""
    return {
        "token": token or str(new_request_token()),
        "request_text": request_text,
        "selected_area": area,
        "selected_challenge": challenge,
        "selected_response_form": response_form,
        "examination_context": examination_context,
        "include_history": include_history,
        "areas": [
            {"value": item.value, "label": PRACTICE_AREA_LABELS[item]}
            for item in PracticeArea
        ],
        "challenges": [
            {"value": item.value, "label": CHALLENGE_LABELS[item]}
            for item in ChallengePreference
        ],
        "response_forms": _RESPONSE_FORMS,
        "max_request_chars": MAX_REQUEST_CHARS,
        "error": error or "",
        "is_available": is_available,
        "status_message": status_message or "",
        "story_context": story_context,
        "requested": practice.get_requested_practices(),
        "has_history": not practice.get_history_context().is_empty,
        "generator_available": is_available,
    }


def _render_request(
    request: Request,
    practice: Any,
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    token: str | None = None,
    request_text: str = "",
    story_context: dict[str, str] | None = None,
    area: str = PracticeArea.CREATIVE_ABILITY.value,
    challenge: str = ChallengePreference.FAMILIAR.value,
    response_form: str = DEFAULT_RESPONSE_FORM,
    examination_context: str = "",
    include_history: bool = False,
    error: str | None = None,
    is_available: bool = True,
    status_message: str | None = None,
) -> Response:
    view = _request_view(
        practice,
        token=token,
        request_text=request_text,
        story_context=story_context,
        area=area,
        challenge=challenge,
        response_form=response_form,
        examination_context=examination_context,
        include_history=include_history,
        error=error,
        is_available=is_available,
        status_message=status_message,
    )
    return templates.TemplateResponse(
        request,
        "practice_request.html",
        {"view": view},
        status_code=status_code,
        headers=headers,
    )


@router.get(_REQUEST_URL, response_class=HTMLResponse)
async def practice_request_page(request: Request, story: str | None = None) -> Response:
    """Render the short request composer and this learner's own practices.

    A ``story`` query parameter carries one Pulse story's "What to try" prompt
    into the composer as editable starter text (SPEC-044 §6.1).
    """
    practice = practice_for_request(request)
    generator = _learner_practice_generator(request)
    story_context = _story_context(request, story)
    return _render_request(
        request,
        practice,
        request_text=story_context["prompt"] if story_context else "",
        story_context=story_context,
        is_available=generator is not None,
        status_message=(
            None
            if generator is not None
            else "Making a new practice is temporarily unavailable. "
            "You can still revisit practices you already requested."
        ),
    )


@router.post(_REQUEST_URL, response_class=HTMLResponse)
async def submit_practice_request(
    request: Request,
    request_text: Annotated[str, Form()] = "",
    practice_area: Annotated[str, Form()] = PracticeArea.CREATIVE_ABILITY.value,
    challenge: Annotated[str, Form()] = ChallengePreference.FAMILIAR.value,
    response_form: Annotated[str, Form()] = DEFAULT_RESPONSE_FORM,
    examination_context: Annotated[str, Form()] = "",
    include_history: Annotated[str, Form()] = "",
    request_token: Annotated[str, Form()] = "",
) -> Response:
    """Validate the request, generate one private practice, and persist it."""
    practice = practice_for_request(request)
    generator = _learner_practice_generator(request)
    repository = _generated_practice_repository(request)
    opted_in = _include_history(include_history)

    error = _validate_choices(
        practice_area=practice_area,
        challenge=challenge,
        response_form=response_form,
    )
    if error is not None:
        return _render_request(
            request,
            practice,
            status_code=400,
            token=request_token,
            request_text=request_text,
            area=practice_area,
            challenge=challenge,
            response_form=response_form,
            examination_context=examination_context,
            include_history=opted_in,
            error=error,
            is_available=generator is not None,
        )

    if generator is None or repository is None:
        return _render_request(
            request,
            practice,
            status_code=503,
            token=request_token,
            request_text=request_text,
            area=practice_area,
            challenge=challenge,
            response_form=response_form,
            examination_context=examination_context,
            include_history=opted_in,
            error=GENERATION_UNAVAILABLE_MESSAGE,
            is_available=False,
        )

    try:
        token = UUID(request_token)
    except (ValueError, AttributeError):
        token = new_request_token()
        request_token = str(token)

    try:
        practice_request = PracticeRequest(
            learner_id=learner_id_for_request(request),
            text=request_text,
            area=PracticeArea(practice_area),
            response_form=response_form.strip() or DEFAULT_RESPONSE_FORM,
            challenge=ChallengePreference(challenge),
            include_history=opted_in,
            created_at=datetime.now(UTC),
            token=token,
            examination_context=examination_context.strip() or None,
        )
    except InvalidLearnerPracticeRequestError as exc:
        return _render_request(
            request,
            practice,
            status_code=400,
            token=request_token,
            request_text=request_text,
            area=practice_area,
            challenge=challenge,
            response_form=response_form,
            examination_context=examination_context,
            include_history=opted_in,
            error=str(exc),
            is_available=True,
        )

    history = (
        practice.get_history_context()
        if practice_request.include_history
        else HistoryContext()
    )
    rate_limit, rate_window_seconds = _rate_limit_settings(request)
    claim_ttl_seconds = _claim_ttl_seconds(request)
    try:
        record = generate_private_practice(
            repository,
            generator,
            request=practice_request,
            history=history,
            now=practice_request.created_at,
            rate_limit=rate_limit,
            rate_window_seconds=rate_window_seconds,
            claim_ttl_seconds=claim_ttl_seconds,
        )
    except LearnerPracticeRateLimitError as exc:
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds > 0
            else None
        )
        return _render_request(
            request,
            practice,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers=headers,
            token=request_token,
            request_text=request_text,
            area=practice_area,
            challenge=challenge,
            response_form=response_form,
            examination_context=examination_context,
            include_history=opted_in,
            error=str(exc),
            is_available=True,
        )
    except GeneratedPracticeValidationError as exc:
        return _render_request(
            request,
            practice,
            status_code=422,
            token=request_token,
            request_text=request_text,
            area=practice_area,
            challenge=challenge,
            response_form=response_form,
            examination_context=examination_context,
            include_history=opted_in,
            error=str(exc),
            is_available=True,
        )
    except LearnerPracticeGenerationError as exc:
        return _render_request(
            request,
            practice,
            status_code=503,
            token=request_token,
            request_text=request_text,
            area=practice_area,
            challenge=challenge,
            response_form=response_form,
            examination_context=examination_context,
            include_history=opted_in,
            error=str(exc),
            is_available=True,
        )
    except PersistenceError:
        return _render_request(
            request,
            practice,
            status_code=503,
            token=request_token,
            request_text=request_text,
            area=practice_area,
            challenge=challenge,
            response_form=response_form,
            examination_context=examination_context,
            include_history=opted_in,
            error=_persistence_failure_message(),
            is_available=True,
        )

    practice.register_generated_practice(record)
    return RedirectResponse(
        f"{_REQUEST_URL}/{record.practice_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(f"{_REQUEST_URL}/{{practice_id}}", response_class=HTMLResponse)
async def requested_practice_page(request: Request, practice_id: str) -> Response:
    """Show the validated brief before the learner chooses to begin."""
    practice = practice_for_request(request)
    try:
        pid = UUID(practice_id)
    except ValueError:
        return _error_response(request, "Practice not found.")

    view = practice.get_generated_practice_preview(pid)
    if view is None:
        return _error_response(
            request,
            "Practice not found.",
            description="This requested practice is no longer available.",
        )
    return templates.TemplateResponse(
        request,
        "requested_practice.html",
        {"view": view},
    )


def _validate_choices(
    *,
    practice_area: str,
    challenge: str,
    response_form: str,
) -> str | None:
    try:
        PracticeArea(practice_area)
    except ValueError:
        return "Choose a supported practice area."
    try:
        ChallengePreference(challenge)
    except ValueError:
        return "Choose a supported challenge preference."
    if not response_form.strip():
        return "Choose the kind of response you want to make."
    return None


def _persistence_failure_message() -> str:
    return (
        "We couldn't save this practice. Nothing has been added to your history — "
        "please try again."
    )
