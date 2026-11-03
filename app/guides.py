"""Learning Guides: authoring workflow and learner presentation (SPEC-045).

Authors create, edit, preview, publish, and archive guides through the
existing protected authoring experience; learners open a published guide from
an associated practice and return without touching their practice progress.

Image search runs only when an author explicitly searches a section. It reuses
the provider-neutral :mod:`fablit.application.image_search` port and the
configured Pexafy adapter already used by practice authoring — there is no
second provider integration. Published guide pages render persisted content
and image metadata only: no search and no LLM call.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.authoring import require_author_access
from app.task_text import split_task_text
from fablit.application.errors import (
    InvalidLearningGuideError,
    LearningGuideNotPublishableError,
)
from fablit.application.image_search import (
    ImageCandidate,
    ImageSearchError,
    ImageSearchProvider,
)
from fablit.application.learning_guides import (
    LAYOUT_LABELS,
    STAGE_LABELS,
    GuideSection,
    GuideStage,
    GuideValidation,
    LearningGuide,
    LearningGuideRepository,
    add_section,
    archive_guide,
    move_section,
    publish_guide,
    remove_image,
    remove_section,
    save_guide_details,
    select_image,
    set_search_candidates,
    update_section,
    validate_guide,
)
from fablit.application.persistence import PersistenceError

logger = logging.getLogger("fablit.guides")
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["split_task_text"] = split_task_text

router = APIRouter()

_STORE_UNAVAILABLE = (
    "The learning guide store is temporarily unavailable. Please try again."
)


def _repository(request: Request) -> LearningGuideRepository:
    """Resolve the app-scoped learning guide repository."""
    repository: object = request.app.state.learning_guide_repository
    if not isinstance(repository, LearningGuideRepository):
        raise RuntimeError("Learning guide repository is not initialized.")
    return repository


def _image_search(request: Request) -> ImageSearchProvider | None:
    """Resolve the existing optional image-search provider, when configured."""
    provider: ImageSearchProvider | None = getattr(
        request.app.state, "authoring_image_search", None
    )
    return provider


def _practice_options(request: Request) -> tuple[tuple[UUID, str], ...]:
    """Every existing practice an author can associate, ordered stably.

    Associations use the practice's stable activity identity, never its title,
    and creating a guide never creates a practice.
    """
    options: list[tuple[UUID, str]] = []
    seen: set[UUID] = set()
    content = getattr(request.app.state, "demo_content", None)
    for activity in getattr(content, "activities", ()):
        identifier = activity.activity.id
        if identifier not in seen:
            options.append((identifier, activity.title))
            seen.add(identifier)
    registry = getattr(request.app.state, "learner_applications", None)
    for record in getattr(registry, "publications", ()):
        if record.activity_id not in seen:
            options.append((record.activity_id, record.activity.title))
            seen.add(record.activity_id)
    return tuple(options)


def _guide_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning guide not found.",
        ) from None


def _section_id(value: str) -> UUID:
    return _guide_id(value)


def _load_guide(repository: LearningGuideRepository, guide_id: str) -> LearningGuide:
    identifier = _guide_id(guide_id)
    try:
        guide = repository.get(identifier)
    except PersistenceError as error:
        logger.exception("failed to load learning guide")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_STORE_UNAVAILABLE,
        ) from error
    if guide is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning guide not found.",
        )
    return guide


def _persist(repository: LearningGuideRepository, guide: LearningGuide) -> None:
    try:
        repository.save(guide)
    except PersistenceError as error:
        logger.exception("failed to save learning guide")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_STORE_UNAVAILABLE,
        ) from error


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


def _practice_ids(raw: list[str] | None) -> tuple[UUID, ...]:
    identifiers: list[UUID] = []
    for value in raw or ():
        try:
            identifiers.append(UUID(value))
        except ValueError:
            raise InvalidLearningGuideError(
                f"associated practice {value!r} is not a valid practice identity"
            ) from None
    return tuple(dict.fromkeys(identifiers))


def _stage(value: str) -> GuideStage:
    try:
        return GuideStage(value.strip().lower())
    except ValueError:
        raise InvalidLearningGuideError(
            f"{value!r} is not a supported guide stage; choose from "
            f"{', '.join(stage.value for stage in GuideStage)}"
        ) from None


def _log_guide_event(
    event: str, guide: LearningGuide, *, practice_id: UUID | None = None
) -> None:
    """Record a lightweight product signal (SPEC-045 §11).

    Events carry only guide identity, version, and the associated practice.
    Learner-written work is never captured.
    """
    extra: dict[str, object] = {
        "guide_id": str(guide.id),
        "guide_version": guide.version,
    }
    if practice_id is not None:
        extra["practice_id"] = str(practice_id)
    logger.info(event, extra=extra)


def _render_editor(
    request: Request,
    guide: LearningGuide,
    *,
    message: str | None = None,
    error: str | None = None,
    validation: GuideValidation | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    return templates.TemplateResponse(
        request,
        "authoring_guide.html",
        {
            "guide": guide,
            "practices": _practice_options(request),
            "stages": [(stage.value, label) for stage, label in STAGE_LABELS.items()],
            "layouts": [
                (layout.value, label) for layout, label in LAYOUT_LABELS.items()
            ],
            "validation": validation,
            "message": message,
            "error": error,
        },
        status_code=status_code,
    )


def _render_guide_list(
    request: Request,
    guides: tuple[LearningGuide, ...],
    *,
    message: str | None = None,
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    return templates.TemplateResponse(
        request,
        "authoring_guides.html",
        {"guides": guides, "message": message, "error": error},
        status_code=status_code,
    )


# ---------------------------------------------------------------------------
# Authoring workflow
# ---------------------------------------------------------------------------


@router.get("/authoring/guides", response_class=HTMLResponse)
async def authoring_guides_page(request: Request) -> Response:
    """List every guide the author can open, publish, or archive."""
    require_author_access(request)
    repository = _repository(request)
    try:
        guides = repository.list_guides()
    except PersistenceError:
        logger.exception("failed to load learning guides")
        return _render_guide_list(
            request,
            (),
            error=_STORE_UNAVAILABLE,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return _render_guide_list(request, guides)


@router.post("/authoring/guides")
async def authoring_create_guide(
    request: Request,
    title: str = Form(""),
    practice_area: str = Form(""),
) -> Response:
    """Create a draft guide; no practice has to exist for this to work."""
    require_author_access(request)
    repository = _repository(request)
    guide = LearningGuide(
        title=title.strip() or "Untitled learning guide",
        summary="",
        practice_area=practice_area.strip(),
    )
    _persist(repository, guide)
    logger.info("learning guide created", extra={"guide_id": str(guide.id)})
    return RedirectResponse(
        url=f"/authoring/guides/{guide.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/authoring/guides/{guide_id}", response_class=HTMLResponse)
async def authoring_guide_editor(request: Request, guide_id: str) -> Response:
    """Render the manual guide authoring surface."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    return _render_editor(request, guide)


@router.post("/authoring/guides/{guide_id}/details")
async def authoring_save_guide_details(
    request: Request,
    guide_id: str,
    title: str = Form(""),
    summary: str = Form(""),
    practice_area: str = Form(""),
    intended_learner_context: str = Form(""),
    associated_practice_ids: Annotated[list[str] | None, Form()] = None,
) -> Response:
    """Save guide metadata and its stable practice associations."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    try:
        updated = save_guide_details(
            guide,
            title=title,
            summary=summary,
            practice_area=practice_area,
            intended_learner_context=intended_learner_context,
            associated_practice_ids=_practice_ids(associated_practice_ids),
        )
    except InvalidLearningGuideError as error:
        return _render_editor(
            request,
            guide,
            error=str(error),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    _persist(repository, updated)
    return _render_editor(request, updated, message="Guide details saved.")


@router.post("/authoring/guides/{guide_id}/sections")
async def authoring_add_guide_section(
    request: Request,
    guide_id: str,
    stage: str = Form("observe"),
    heading: str = Form(""),
    body: str = Form(""),
) -> Response:
    """Append an ordered section to the guide."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    try:
        section = GuideSection(stage=_stage(stage), heading=heading, body=body)
    except InvalidLearningGuideError as error:
        return _render_editor(
            request,
            guide,
            error=str(error),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    updated = add_section(guide, section)
    _persist(repository, updated)
    return _render_editor(request, updated, message="Section added.")


@router.post("/authoring/guides/{guide_id}/sections/{section_id}")
async def authoring_update_guide_section(
    request: Request,
    guide_id: str,
    section_id: str,
    stage: str = Form("observe"),
    heading: str = Form(""),
    body: str = Form(""),
    questions: str = Form(""),
    examples: str = Form(""),
    reflection_prompt: str = Form(""),
    layout: str = Form("default"),
) -> Response:
    """Edit one section's content and its controlled layout hint."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    existing = guide.section(_section_id(section_id))
    try:
        replacement = GuideSection(
            id=existing.id,
            stage=_stage(stage),
            heading=heading,
            body=body,
            questions=tuple(
                line.strip() for line in questions.splitlines() if line.strip()
            ),
            examples=tuple(
                line.strip() for line in examples.splitlines() if line.strip()
            ),
            reflection_prompt=reflection_prompt.strip(),
            layout=layout or "default",
            images=existing.images,
            search_query=existing.search_query,
            search_candidates=existing.search_candidates,
        )
        updated = update_section(guide, replacement)
    except InvalidLearningGuideError as error:
        return _render_editor(
            request,
            guide,
            error=str(error),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    _persist(repository, updated)
    return _render_editor(request, updated, message="Section saved.")


@router.post("/authoring/guides/{guide_id}/sections/{section_id}/move")
async def authoring_move_guide_section(
    request: Request,
    guide_id: str,
    section_id: str,
    direction: str = Form("up"),
) -> Response:
    """Reorder a section without losing its content or imagery."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    updated = move_section(
        guide,
        _section_id(section_id),
        -1 if direction.strip().lower() == "up" else 1,
    )
    _persist(repository, updated)
    return _render_editor(request, updated)


@router.post("/authoring/guides/{guide_id}/sections/{section_id}/remove")
async def authoring_remove_guide_section(
    request: Request, guide_id: str, section_id: str
) -> Response:
    """Remove a section from the guide."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    updated = remove_section(guide, _section_id(section_id))
    _persist(repository, updated)
    return _render_editor(request, updated, message="Section removed.")


@router.post("/authoring/guides/{guide_id}/sections/{section_id}/images/search")
async def authoring_search_section_images(
    request: Request,
    guide_id: str,
    section_id: str,
    query: str = Form(""),
) -> Response:
    """Search images for one section using the existing image-search port."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    section = guide.section(_section_id(section_id))
    cleaned = " ".join(query.split())
    provider = _image_search(request)

    candidates: tuple[ImageCandidate, ...] = ()
    error: str | None = None
    if provider is None or not callable(getattr(provider, "search", None)):
        error = "Image search is not configured. This section can stay text-only."
    elif not cleaned:
        error = "Enter a search query to look for images."
    else:
        try:
            candidates = tuple(provider.search(cleaned))
        except ImageSearchError:
            logger.warning(
                "section image search failed; section can remain text-only",
                extra={"guide_id": str(guide.id), "section_id": str(section.id)},
            )
            error = (
                "Image search is unavailable right now. This section can stay "
                "text-only, and you can try again later."
            )
        if error is None and not candidates:
            error = (
                "No images matched that search. Try different words, or keep "
                "this section text-only."
            )

    updated = set_search_candidates(guide, section.id, candidates, query=cleaned)
    _persist(repository, updated)
    section = updated.section(section.id)

    if _is_htmx(request):
        return templates.TemplateResponse(
            request,
            "_guide_image_candidates.html",
            {
                "guide": updated,
                "section": section,
                "candidates": candidates,
                "error": error,
            },
        )
    return RedirectResponse(
        url=f"/authoring/guides/{updated.id}#section-{section.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/authoring/guides/{guide_id}/sections/{section_id}/images")
async def authoring_select_section_image(
    request: Request,
    guide_id: str,
    section_id: str,
    photo_id: str = Form(""),
    alt_text: str = Form(""),
    caption: str = Form(""),
) -> Response:
    """Select one displayed candidate, retaining its provenance."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    try:
        updated = select_image(
            guide,
            _section_id(section_id),
            photo_id=photo_id,
            alt_text=alt_text,
            caption=caption,
        )
    except InvalidLearningGuideError as error:
        return _render_editor(
            request,
            guide,
            error=str(error),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    _persist(repository, updated)
    return _render_editor(request, updated, message="Image added to this section.")


@router.post("/authoring/guides/{guide_id}/sections/{section_id}/images/remove")
async def authoring_remove_section_image(
    request: Request,
    guide_id: str,
    section_id: str,
    asset_id: str = Form(""),
) -> Response:
    """Replace or remove a selected section image before publication."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    updated = remove_image(guide, _section_id(section_id), asset_id=asset_id)
    _persist(repository, updated)
    return _render_editor(request, updated, message="Image removed.")


@router.get("/authoring/guides/{guide_id}/preview", response_class=HTMLResponse)
async def authoring_preview_guide(request: Request, guide_id: str) -> Response:
    """Preview the learner-facing presentation of a draft guide."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    return templates.TemplateResponse(
        request,
        "guide.html",
        {
            "guide": guide,
            "preview": True,
            "return_practice": (
                guide.associated_practice_ids[0]
                if guide.associated_practice_ids
                else None
            ),
        },
    )


@router.post("/authoring/guides/{guide_id}/publish")
async def authoring_publish_guide(request: Request, guide_id: str) -> Response:
    """Publish intentionally, revalidating content before learners see it."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    known = {identifier for identifier, _ in _practice_options(request)}
    try:
        published = publish_guide(
            guide, repository=repository, known_practice_ids=known
        )
    except LearningGuideNotPublishableError as error:
        return _render_editor(
            request,
            guide,
            error=str(error),
            validation=validate_guide(guide, known_practice_ids=known),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return _render_editor(
        request,
        published,
        message="Guide published. Learners can open it from its practices.",
    )


@router.post("/authoring/guides/{guide_id}/archive")
async def authoring_archive_guide(request: Request, guide_id: str) -> Response:
    """Archive a guide so learners can no longer reach it."""
    require_author_access(request)
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    archived = archive_guide(guide, repository=repository)
    return _render_editor(
        request,
        archived,
        message="Guide archived. It no longer appears beside its practices.",
    )


# ---------------------------------------------------------------------------
# Learner-facing guide
# ---------------------------------------------------------------------------


@router.get("/guides/{guide_id}", response_class=HTMLResponse)
async def learning_guide_page(
    request: Request, guide_id: str, practice_id: str | None = None
) -> Response:
    """Read a published guide through the anonymous learner journey."""
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    if not guide.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning guide not found.",
        )

    return_practice: UUID | None = None
    if practice_id is not None:
        try:
            candidate = UUID(practice_id)
        except ValueError:
            candidate = None
        if candidate is not None and candidate in guide.associated_practice_ids:
            return_practice = candidate
    if return_practice is None and guide.associated_practice_ids:
        return_practice = guide.associated_practice_ids[0]

    _log_guide_event("learning_guide_opened", guide, practice_id=return_practice)
    return templates.TemplateResponse(
        request,
        "guide.html",
        {"guide": guide, "preview": False, "return_practice": return_practice},
    )


@router.get("/guides/{guide_id}/return-to-practice")
async def learning_guide_return(
    request: Request, guide_id: str, practice_id: str = ""
) -> Response:
    """Return the learner to the associated practice, recording the event."""
    repository = _repository(request)
    guide = _load_guide(repository, guide_id)
    if not guide.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning guide not found.",
        )
    try:
        target = UUID(practice_id)
    except ValueError:
        target = None
    if target is not None and target in guide.associated_practice_ids:
        _log_guide_event(
            "learning_guide_returned_to_practice", guide, practice_id=target
        )
        return RedirectResponse(
            url=f"/activities/{target}", status_code=status.HTTP_303_SEE_OTHER
        )
    return RedirectResponse(
        url=f"/guides/{guide.id}", status_code=status.HTTP_303_SEE_OTHER
    )
