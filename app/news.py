"""Web routes for the curated Fashion & Design Pulse (SPEC-041, SPEC-042).

Three surfaces share one application workflow:

- ``GET /pulse`` is learner-facing. It reads only persisted, already-published
  stories and never invokes Gemini or fetches a source, so it stays usable
  when curation is unavailable.
- ``GET /authoring/pulse``, ``POST /authoring/pulse/curate``, and the job status
  routes live behind the existing SEC-001 authoring boundary. An authorised
  operator initiates one durable job on demand; there is no scheduler, and
  no automatic publication path beyond the SPEC-041 checks.
- ``POST /tasks/news-curation`` is the protected task handler (SPEC-042 §7).
  It authenticates the task's own OIDC identity, independently of the author
  session, and runs one bounded unit of the accepted job.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.authoring import require_author_access
from app.request_format import wants_html
from app.task_text import split_task_text
from fablit.application.errors import (
    NewsCurationDispatchError,
    NewsCurationInProgressError,
)
from fablit.application.news import (
    NEWS_CATEGORY_LABELS,
    NewsBatchResult,
    NewsCategory,
    NewsCurationDiagnostics,
    NewsCurator,
    NewsRepository,
    NewsStory,
)
from fablit.application.news_images import StoryImage
from fablit.application.news_jobs import (
    NewsCurationJob,
    NewsCurationJobService,
    NewsCurationJobStatus,
)
from fablit.application.news_sources import NewsSource, is_safe_news_url
from fablit.application.persistence import PersistenceError
from fablit.platform.task_auth import (
    OidcVerifier,
    TaskAuthenticationError,
    TaskPrincipal,
    bearer_token,
    verify_task_oidc_token,
)

logger = logging.getLogger("fablit.news")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["split_task_text"] = split_task_text

router = APIRouter()

_PULSE_URL = "/pulse"


def _news_repository(request: Request) -> NewsRepository | None:
    repository: object = getattr(request.app.state, "news_repository", None)
    if isinstance(repository, NewsRepository):
        return repository
    return None


def _news_curator(request: Request) -> NewsCurator | None:
    curator: object = getattr(request.app.state, "news_curator", None)
    return curator if isinstance(curator, NewsCurator) else None


def _selected_category(raw: str | None) -> NewsCategory | None:
    if not raw:
        return None
    try:
        return NewsCategory(raw.strip().lower())
    except ValueError:
        return None


def _story_image_view(image: object) -> dict[str, Any] | None:
    """Shape one persisted story image for safe rendering, or ``None``.

    SPEC-043 §4.1/§4.2: only a validated public image URL is rendered, so a
    stored value can never become a broken image, an unsafe scheme, or a
    silent server-side fetch on the learner page.
    """
    if not isinstance(image, StoryImage):
        return None
    if not is_safe_news_url(image.image_url):
        return None
    thumbnail_url = image.thumbnail_url if is_safe_news_url(image.thumbnail_url) else ""
    credit_url = image.source_url if is_safe_news_url(image.source_url) else ""
    return {
        "url": image.image_url,
        "thumbnail_url": thumbnail_url or image.image_url,
        "alt": image.alt_text,
        "credit": image.credit_line,
        "credit_url": credit_url,
        "source_name": image.source_name,
        "is_illustrative": image.is_illustrative,
        "width": image.width,
        "height": image.height,
    }


def _story_view(story: NewsStory) -> dict[str, Any]:
    """Shape one persisted story for safe learner rendering."""
    return {
        "headline": story.headline,
        "summary": story.summary,
        "source_name": story.source_name,
        "url": story.canonical_url if is_safe_news_url(story.canonical_url) else "",
        "display_date": story.display_at.strftime("%d %B %Y"),
        "published_iso": story.display_at.date().isoformat(),
        "categories": [
            {
                "label": NEWS_CATEGORY_LABELS[category],
                "url": f"{_PULSE_URL}?category={category.value}",
            }
            for category in story.categories
        ],
        "educational_relevance": story.educational_relevance,
        "reflection_prompt": story.reflection_prompt or "",
        "image": _story_image_view(story.image),
    }


def _feed_view(
    stories: tuple[NewsStory, ...],
    *,
    selected: NewsCategory | None,
    unavailable: bool,
) -> dict[str, Any]:
    """Build the feed, its category filter, and the graceful empty state."""
    counts = {
        category: sum(1 for story in stories if category in story.categories)
        for category in NewsCategory
    }
    visible = (
        tuple(story for story in stories if selected in story.categories)
        if selected is not None
        else stories
    )
    filters = [
        {
            "label": "All stories",
            "count": len(stories),
            "url": _PULSE_URL,
            "is_active": selected is None,
        }
    ]
    for category in NewsCategory:
        if counts[category] == 0 and category is not selected:
            continue
        filters.append(
            {
                "label": NEWS_CATEGORY_LABELS[category],
                "count": counts[category],
                "url": f"{_PULSE_URL}?category={category.value}",
                "is_active": category is selected,
            }
        )
    return {
        "stories": [_story_view(story) for story in visible],
        "filters": filters,
        "selected": selected.value if selected is not None else "",
        "is_unavailable": unavailable,
        "has_any_stories": bool(stories),
    }


@router.get("/pulse", response_class=HTMLResponse)
async def news_feed(request: Request, category: str | None = None) -> Response:
    """Render the learner-facing curated feed from persisted stories only."""
    unavailable = False
    stories: tuple[NewsStory, ...] = ()
    repository = _news_repository(request)
    if repository is None:
        unavailable = True
    else:
        try:
            stories = repository.list_stories()
        except PersistenceError:
            logger.exception("news repository unavailable; rendering empty feed")
            unavailable = True

    view = _feed_view(
        stories,
        selected=_selected_category(category),
        unavailable=unavailable,
    )
    return templates.TemplateResponse(request, "news.html", {"view": view})


#: Operator-facing labels for the durable job lifecycle (SPEC-042 §8).
_JOB_STATUS_LABELS: dict[NewsCurationJobStatus, str] = {
    NewsCurationJobStatus.QUEUED: "Queued",
    NewsCurationJobStatus.RUNNING: "Running",
    NewsCurationJobStatus.SUCCEEDED: "Completed",
    NewsCurationJobStatus.PARTIALLY_SUCCEEDED: (
        "Completed with item or source failures"
    ),
    NewsCurationJobStatus.FAILED: "Failed",
}


def _news_job_service(request: Request) -> NewsCurationJobService | None:
    service: object = getattr(request.app.state, "news_job_service", None)
    return service if isinstance(service, NewsCurationJobService) else None


def _diagnostics_payload(
    diagnostics: NewsCurationDiagnostics | None,
) -> dict[str, Any] | None:
    if diagnostics is None:
        return None
    return {
        "provider_id": diagnostics.provider_id,
        "model_id": diagnostics.model_id,
        "provider_retries": diagnostics.provider_retries,
        "transient_retries_recovered": diagnostics.transient_retries_recovered,
        "exhausted_retries": diagnostics.exhausted_retries,
        "provider_outcome": diagnostics.provider_outcome.value,
        "last_status_code": diagnostics.last_status_code,
    }


def _report_payload(report: NewsBatchResult) -> dict[str, Any]:
    """Shape a batch report for JSON without raw provider or source detail."""
    return {
        "started_at": report.started_at.isoformat(),
        "finished_at": report.finished_at.isoformat(),
        "sources_configured": report.sources_configured,
        "sources_processed": report.sources_processed,
        "fetched": report.fetched,
        "deduplicated": report.deduplicated,
        "published": report.published,
        "rejected": report.rejected,
        "failed": report.failed,
        "provider_retries": report.provider_retries,
        "diagnostics": _diagnostics_payload(report.diagnostics),
        "summary": report.summary_line,
        "rejections": [
            {
                "source_name": item.source_name,
                "title": item.title,
                "url": item.url,
                "reason": item.reason,
            }
            for item in report.rejections
        ],
        "failures": [
            {
                "source_name": item.source_name,
                "title": item.title,
                "url": item.url,
                "reason": item.reason,
            }
            for item in report.failures
        ],
        "source_failures": [
            {"source_name": failure.source_name, "reason": failure.reason}
            for failure in report.source_failures
        ],
    }


def _job_payload(job: NewsCurationJob) -> dict[str, Any]:
    """Shape one durable job for a status response."""
    return {
        "job_id": str(job.job_id),
        "status": job.status.value,
        "status_label": _JOB_STATUS_LABELS[job.status],
        "stage": job.stage.value,
        "message": job.message,
        "is_terminal": job.is_terminal,
        "created_at": job.created_at.isoformat(),
        "started_at": (
            job.started_at.isoformat() if job.started_at is not None else None
        ),
        "finished_at": (
            job.finished_at.isoformat() if job.finished_at is not None else None
        ),
        "attempt": job.attempt,
        "counters": {
            "sources_configured": job.counters.sources_configured,
            "sources_processed": job.counters.sources_processed,
            "sources_failed": job.counters.sources_failed,
            "items_fetched": job.counters.items_fetched,
            "items_deduplicated": job.counters.items_deduplicated,
            "items_published": job.counters.items_published,
            "items_rejected": job.counters.items_rejected,
            "items_failed": job.counters.items_failed,
            "provider_retries": job.counters.provider_retries,
        },
        "diagnostics": _diagnostics_payload(job.diagnostics),
        "error": (
            {
                "category": job.error_category.value,
                "message": job.error_message,
            }
            if job.error_category is not None
            else None
        ),
        "report": (_report_payload(job.report) if job.report is not None else None),
    }


def _job_view(job: NewsCurationJob) -> dict[str, Any]:
    """Shape one job for the protected authoring page."""
    return {
        "job_id": str(job.job_id),
        "status": job.status.value,
        "status_label": _JOB_STATUS_LABELS[job.status],
        "stage": job.stage.value,
        "message": job.message,
        "is_terminal": job.is_terminal,
        "created_display": job.created_at.strftime("%d %B %Y, %H:%M UTC"),
        "error_message": job.error_message or "",
        "counters": {
            "sources_configured": job.counters.sources_configured,
            "sources_processed": job.counters.sources_processed,
            "sources_failed": job.counters.sources_failed,
            "items_fetched": job.counters.items_fetched,
            "items_deduplicated": job.counters.items_deduplicated,
            "items_published": job.counters.items_published,
            "items_rejected": job.counters.items_rejected,
            "items_failed": job.counters.items_failed,
            "provider_retries": job.counters.provider_retries,
        },
    }


def _pulse_page(
    request: Request,
    *,
    job: NewsCurationJob | None = None,
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    config = request.app.state.config
    sources: tuple[NewsSource, ...] = tuple(config.news_sources)
    return templates.TemplateResponse(
        request,
        "authoring_news.html",
        {
            "sources": sources,
            "job": _job_view(job) if job is not None else None,
            "batch": job.report if job is not None else None,
            "error": error,
            "provider_configured": _news_curator(request) is not None,
            "has_sources": bool(sources),
        },
        status_code=status_code,
    )


def _latest_job(request: Request) -> NewsCurationJob | None:
    service = _news_job_service(request)
    if service is None:
        return None
    try:
        return service.latest()
    except PersistenceError:
        logger.exception(
            "news job store unavailable; rendering the page without status"
        )
        return None


@router.get("/authoring/pulse", response_class=HTMLResponse)
async def authoring_pulse_page(request: Request) -> Response:
    """Render the protected on-demand curation page (SPEC-041 §5.1)."""
    require_author_access(request)
    return _pulse_page(request, job=_latest_job(request))


@router.post("/authoring/pulse/curate")
async def authoring_pulse_curate(request: Request) -> Response:
    """Accept one durable curation job (SPEC-042 §5, §7).

    SEC-001 is checked before any source retrieval or AI invocation. The job
    is persisted before it is acknowledged, so a refresh, navigation, or
    instance change cannot lose accepted work; a dispatch failure is reported
    as a failure rather than as queued work.
    """
    require_author_access(request)

    service = _news_job_service(request)
    if service is None:
        return _pulse_page(
            request,
            error=(
                "News curation is not configured. Set the server-side Gemini API "
                "key before refreshing the Pulse."
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        job = await asyncio.to_thread(service.start)
    except NewsCurationInProgressError:
        return _pulse_page(
            request,
            job=_latest_job(request),
            error="A refresh is already queued or running. Wait for it to finish.",
            status_code=status.HTTP_409_CONFLICT,
        )
    except NewsCurationDispatchError:
        return _pulse_page(
            request,
            job=_latest_job(request),
            error=(
                "The refresh could not be queued, so no work was accepted. "
                "Existing stories are unchanged; try again."
            ),
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    except PersistenceError:
        logger.exception("news job store unavailable; refresh not accepted")
        return _pulse_page(
            request,
            error=(
                "The refresh could not be saved, so no work was accepted. "
                "Existing stories are unchanged; try again."
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if not wants_html(request):
        return JSONResponse(_job_payload(job), status_code=status.HTTP_202_ACCEPTED)
    return _pulse_page(
        request,
        job=job,
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get("/authoring/pulse/jobs/latest")
async def authoring_pulse_latest_job(request: Request) -> Response:
    """Return the current or most recent job, so refresh and return are safe."""
    require_author_access(request)
    service = _news_job_service(request)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="News curation is not configured.",
        )
    try:
        job = service.latest()
    except PersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Curation status is temporarily unavailable.",
        ) from error
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No curation job has been started.",
        )
    return JSONResponse(_job_payload(job))


@router.get("/authoring/pulse/jobs/{job_id}")
async def authoring_pulse_job(request: Request, job_id: str) -> Response:
    """Return one job's persisted status, progress, and final report."""
    require_author_access(request)
    service = _news_job_service(request)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="News curation is not configured.",
        )
    try:
        parsed = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation job not found.",
        ) from None
    try:
        job = service.get(parsed)
    except PersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Curation status is temporarily unavailable.",
        ) from error
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation job not found.",
        )
    return JSONResponse(_job_payload(job))


def _task_verifier(request: Request) -> OidcVerifier | None:
    verifier: object = getattr(request.app.state, "news_task_verifier", None)
    return verifier if callable(verifier) else None


def require_task_access(request: Request) -> TaskPrincipal:
    """Authenticate a task request independently of the author session.

    SPEC-042 §7: only a Google-signed OIDC token issued to the configured task
    service account for this handler's audience is accepted. A missing or
    unexpected header is refused before the handler can read or run a job.
    """
    config = request.app.state.config
    audience = config.news_task_audience or config.news_task_handler_url
    try:
        return verify_task_oidc_token(
            bearer_token(request.headers.get("Authorization")),
            audience=audience,
            service_account_email=config.news_task_service_account,
            verifier=_task_verifier(request),
        )
    except TaskAuthenticationError:
        logger.warning(
            "unauthorized curation task access attempt",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client": request.client.host if request.client else None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Task authentication required.",
            headers={"WWW-Authenticate": 'Bearer realm="Fablit Tasks"'},
        ) from None


async def _task_payload(request: Request) -> Mapping[str, Any]:
    """Read the task body, refusing anything that is not one job identity."""
    try:
        payload = await request.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The task body must be a JSON object.",
        ) from None
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The task body must be a JSON object.",
        )
    return {str(key): value for key, value in payload.items()}


@router.post("/tasks/news-curation")
async def news_curation_task(request: Request) -> Response:
    """Run one bounded unit of an accepted curation job (SPEC-042 §7).

    Duplicate delivery is safe: the repository grants the job's lease to one
    worker, and a task that arrives for a terminal job is an accepted no-op.
    """
    require_task_access(request)
    service = _news_job_service(request)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="News curation is not configured.",
        )

    payload = await _task_payload(request)
    try:
        job_id = UUID(str(payload.get("job_id", "")))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The task must name one curation job.",
        ) from None

    owner = request.headers.get("X-CloudTasks-TaskName") or f"task-{job_id}"
    try:
        job = await asyncio.to_thread(service.handle_task, job_id, owner=owner)
    except NewsCurationDispatchError as error:
        logger.warning(
            "news curation continuation could not be queued",
            extra={"job_id": str(job_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Curation could not continue; the task will be retried.",
        ) from error
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation job not found.",
        )
    return JSONResponse(_job_payload(job))
