"""Web routes for the curated Fashion & Design Pulse (SPEC-041).

Two surfaces share one application workflow:

- ``GET /pulse`` is learner-facing. It reads only persisted, already-published
  stories and never invokes Gemini or fetches a source, so it stays usable
  when curation is unavailable.
- ``GET /authoring/pulse`` and ``POST /authoring/pulse/curate`` live behind the
  existing SEC-001 authoring boundary. An authorised operator initiates one
  bounded refresh on demand; there is no scheduler, workflow, or automatic
  publication path. The batch result is shown back to the operator, including
  the safe reason a candidate was rejected or failed.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.authoring import require_author_access
from app.task_text import split_task_text
from fablit.application.errors import (
    NewsCurationInProgressError,
    NewsFeedError,
)
from fablit.application.news import (
    NEWS_CATEGORY_LABELS,
    NewsBatchResult,
    NewsCategory,
    NewsCurator,
    NewsRepository,
    NewsStory,
)
from fablit.application.news_sources import NewsSource, is_safe_news_url
from fablit.application.persistence import PersistenceError

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


def _last_batch(request: Request) -> NewsBatchResult | None:
    batch = getattr(request.app.state, "news_last_batch", None)
    return batch if isinstance(batch, NewsBatchResult) else None


def _pulse_page(
    request: Request,
    *,
    batch: NewsBatchResult | None = None,
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
            "batch": batch,
            "error": error,
            "provider_configured": _news_curator(request) is not None,
            "has_sources": bool(sources),
        },
        status_code=status_code,
    )


@router.get("/authoring/pulse", response_class=HTMLResponse)
async def authoring_pulse_page(request: Request) -> Response:
    """Render the protected on-demand curation page (SPEC-041 §5.1)."""
    require_author_access(request)
    return _pulse_page(request, batch=_last_batch(request))


@router.post("/authoring/pulse/curate")
async def authoring_pulse_curate(request: Request) -> Response:
    """Run one bounded refresh and report its batch result (SPEC-041 §5.1).

    SEC-001 is checked before any source retrieval or AI invocation. Repeated
    submissions are idempotent through canonical-URL deduplication, and an
    overlapping refresh is refused rather than run concurrently.
    """
    require_author_access(request)

    curator = _news_curator(request)
    if curator is None:
        return _pulse_page(
            request,
            error=(
                "News curation is not configured. Set the server-side Gemini API "
                "key before refreshing the Pulse."
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        batch = await asyncio.to_thread(curator.curate_batch)
    except NewsCurationInProgressError:
        return _pulse_page(
            request,
            batch=_last_batch(request),
            error="A refresh is already running. Wait for it to finish.",
            status_code=status.HTTP_409_CONFLICT,
        )
    except NewsFeedError as error:
        logger.warning(
            "news refresh failed",
            extra={"error_type": type(error).__name__},
        )
        return _pulse_page(
            request,
            error="The refresh could not be completed. Existing stories are unchanged.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception as error:
        logger.exception(
            "unexpected news refresh failure",
            extra={"error_type": type(error).__name__},
        )
        return _pulse_page(
            request,
            error="The refresh could not be completed. Existing stories are unchanged.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

    request.app.state.news_last_batch = batch
    # Render the report directly rather than redirecting: on a multi-instance
    # deployment the follow-up GET could land on another instance and lose the
    # result. Repeating the action is idempotent, so a browser refresh is safe.
    return _pulse_page(request, batch=batch)
