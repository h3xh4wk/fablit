"""FastAPI application entry point for the Fablit platform (SPEC-012…024).

SPEC-014 establishes the learner pilot deployment boundary: the application
is assembled by ``create_app`` so environment-specific safety settings can be
applied and tested, development-only interfaces (API documentation) are
hidden in the pilot environment, and unhandled errors render a learner-facing
page instead of exposing internals.

SPEC-021 adds web routes for practice history and review, allowing learners
to access their durable practice completion records.

SPEC-024 connects the learner-scoped application boundary to real web
requests: each anonymous learner's browser receives a unique opaque learner
identity in a secure cookie, and every request resolves a learner-scoped
application so journey state and practice history stay private to that
learner (see ``app.learner_session``).
"""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import FastAPI, Form, Request
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.learner_session import (
    DemoContent,
    LearnerApplicationRegistry,
    learner_identity_middleware,
    practice_for_request,
)
from fablit.application import (
    ActivityNotFoundError,
    CompletionNotFoundError,
    EvaluationFailedError,
    FeedbackNotFoundError,
    InvalidPracticeResponseError,
    InvalidReflectionResponseError,
    PracticeApplication,
    PracticeMode,
    SubmissionInProgressError,
    UnknownPracticeModeError,
)
from fablit.application.persistence import (
    PersistenceError,
    PracticeHistoryRepository,
)
from fablit.config import AppConfig, load_config
from fablit.logging import init_logging, reset_request_context, set_request_context
from fablit.platform.metrics import MetricsRegistry

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

config = load_config()
init_logging(config)
logger = logging.getLogger("fablit.app")
metrics_registry = MetricsRegistry()


def _build_learner_applications(
    app_config: AppConfig,
) -> tuple[DemoContent, LearnerApplicationRegistry]:
    """Assemble the shared demo content and the learner application registry.

    SPEC-024 §6: demo content, evaluator wiring, and the stimulus provider
    are identical for every learner and built once; each request resolves its
    anonymous learner identity to a learner-scoped ``PracticeApplication``
    via the registry (``app.learner_session``). The history repository
    (SPEC-021) is shared — it is learner-scoped by contract — and may be
    ``None`` when persistence is not configured.
    """
    content = DemoContent.build(app_config)
    history_repository = _build_history_repository(app_config)
    return content, LearnerApplicationRegistry(content, history_repository)


def _build_history_repository(
    app_config: AppConfig,
) -> PracticeHistoryRepository | None:
    """Build the appropriate history repository based on configuration.

    SPEC-021 §13: unit/application tests use the in-memory repository.
    Production uses Google Cloud Datastore. If neither is configured,
    history is disabled.
    """
    repository_type = app_config.practice_history_repository

    if repository_type == "datastore":
        try:
            from google.cloud import datastore

            from fablit.platform.datastore_repository import (
                DatastorePracticeHistoryRepository,
            )

            client: datastore.Client = datastore.Client()
            logger.info(
                "initialized datastore practice history repository",
                extra={"project_id": client.project},
            )
            return DatastorePracticeHistoryRepository(client)
        except Exception as e:
            logger.exception(
                "failed to initialize datastore practice history repository"
            )
            raise RuntimeError(
                "Could not initialize Google Cloud Datastore for practice history. "
                "Check GCP configuration and credentials."
            ) from e

    elif repository_type == "memory":
        from fablit.application.repositories import (
            InMemoryPracticeHistoryRepository,
        )

        logger.info("initialized in-memory practice history repository")
        return InMemoryPracticeHistoryRepository()

    else:
        logger.warning(
            "practice history repository not configured; history will be unavailable"
        )
        return None


def _activity_id(value: str) -> UUID:
    """Parse an activity identity, raising ActivityNotFoundError when invalid."""
    try:
        return UUID(value)
    except ValueError:
        raise ActivityNotFoundError("Activity not found.") from None


def _completion_id(value: str) -> UUID:
    """Parse a completion identity, raising CompletionNotFoundError when invalid."""
    try:
        return UUID(value)
    except ValueError:
        raise CompletionNotFoundError("Practice record not found.") from None


def _error_response(
    request: Request,
    message: str,
    *,
    status_code: int = 404,
    description: str | None = None,
) -> Response:
    """Render the learner-facing error page (SPEC-014 §20)."""
    return templates.TemplateResponse(
        request,
        "error.html",
        {"message": message, "description": description},
        status_code=status_code,
    )


def _practice_partial(
    request: Request,
    view: object,
    *,
    error: str | None = None,
    submitted_response: str | None = None,
) -> HTMLResponse:
    """Render just the submission area for HTMX partial swap (SPEC-017)."""
    html = templates.env.get_template("_practice_partial.html").render(
        request=request,
        view=view,
        error=error,
        submitted_response=submitted_response,
    )
    return HTMLResponse(content=html)


def _feedback_partial(request: Request, practice: PracticeApplication) -> HTMLResponse:
    """Render the feedback content for HTMX partial swap (SPEC-017).

    The feedback view is obtained from the practice application and rendered
    from a partial template that contains no page chrome.
    """
    view = practice.get_feedback()
    html = templates.env.get_template("_feedback_partial.html").render(
        request=request,
        view=view,
    )
    return HTMLResponse(content=html)


def _mode_id(value: str) -> PracticeMode:
    """Parse a mode identifier, raising UnknownPracticeModeError when invalid."""
    try:
        return PracticeMode(value)
    except ValueError:
        raise UnknownPracticeModeError("Practice mode not found.") from None


async def _unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    """Turn unexpected failures into a learner-friendly page (SPEC-014 §20).

    The full exception is logged server-side so the team can investigate,
    while the learner only ever sees a generic message.
    """
    logger.exception(
        "unhandled exception",
        extra={"path": request.url.path, "method": request.method},
    )
    return _error_response(
        request,
        "Something went wrong.",
        status_code=500,
        description="We couldn't complete that action. Please try again.",
    )


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    trace_id = request.headers.get("X-Trace-ID")
    token = set_request_context(request_id=request_id, trace_id=trace_id)
    metrics_registry.counter("requests_total").inc()

    try:
        response = await call_next(request)
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
                "status_code": response.status_code,
            },
        )
        return response
    finally:
        reset_request_context(token)


def create_app(config: AppConfig) -> FastAPI:
    """Assemble the Fablit FastAPI application for the given configuration.

    SPEC-014 §19/§43: development-only interfaces (API documentation and the
    OpenAPI schema) are not exposed in the pilot environment, and debug mode
    is driven by configuration so production debugging stays disabled.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Run startup and shutdown lifecycle hooks."""
        logger.info("application startup", extra={"version": config.version})
        app.state.ready = True
        app.state.config = config
        app.state.demo_content, app.state.learner_applications = (
            _build_learner_applications(config)
        )
        yield
        app.state.ready = False
        app.state.demo_content = None
        app.state.learner_applications = None
        logger.info("application shutdown")

    docs_enabled = config.environment != "production"
    app = FastAPI(
        title="Fablit",
        description="Bootstrap platform for Fablit.",
        version=config.version,
        debug=config.debug,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    # SPEC-024: the identity boundary is centralised in middleware rather
    # than duplicated across routes (§6): every request resolves its
    # anonymous learner identity before reaching a handler.
    app.middleware("http")(learner_identity_middleware)
    app.middleware("http")(request_logging_middleware)
    app.add_exception_handler(Exception, _unhandled_exception_handler)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> Response:
        """Render the learner practice dashboard (UC-001)."""
        view = practice_for_request(request).get_dashboard()
        return templates.TemplateResponse(request, "dashboard.html", {"view": view})

    # SPEC-022: Practice Mode Choice Routes

    @app.get("/practice", response_class=HTMLResponse)
    async def practice_mode_choice(request: Request) -> Response:
        """Render the practice-mode choice (SPEC-022 §7).

        A calm, low-friction invitation to choose how to practise right now:
        no mode is pre-selected or recommended, and the normal activity
        library stays reachable without choosing (AC-022-02).
        """
        view = practice_for_request(request).get_practice_modes()
        return templates.TemplateResponse(
            request, "practice_mode_choice.html", {"view": view}
        )

    @app.get("/practice/{mode_id}", response_class=HTMLResponse)
    async def practice_mode_activities(request: Request, mode_id: str) -> Response:
        """Render the activities a chosen practice mode offers (SPEC-022 §6, §8).

        The learner's explicit selection is authoritative for this practice
        entry (§12): activities come from the mode's curated configuration
        and each starts the unchanged practice journey.
        """
        try:
            mode = _mode_id(mode_id)
        except UnknownPracticeModeError:
            return _error_response(request, "Practice mode not found.")
        view = practice_for_request(request).get_practice_mode_activities(mode)
        return templates.TemplateResponse(
            request, "practice_mode_activities.html", {"view": view}
        )

    @app.get("/activities/{activity_id}", response_class=HTMLResponse)
    async def practice_page(request: Request, activity_id: str) -> Response:
        """Render the practice activity page (UC-002)."""
        practice = practice_for_request(request)
        try:
            view = practice.start_practice(_activity_id(activity_id))
        except ActivityNotFoundError:
            return _error_response(request, "Activity not found.")
        return templates.TemplateResponse(request, "practice.html", {"view": view})

    @app.post("/activities/{activity_id}/submit", response_class=HTMLResponse)
    async def submit_response(
        request: Request,
        activity_id: str,
        response: Annotated[str, Form()] = "",
    ) -> Response:
        """Accept a learner response and move to feedback (UC-003/004/005).

        SPEC-017: HTMX requests receive partial HTML so the submission area
        is replaced in-place without a full page navigation. Non-HTMX
        requests (progressive enhancement, no JavaScript) continue to
        receive a full-page redirect.
        """
        practice = practice_for_request(request)
        is_htmx = request.headers.get("HX-Request") == "true"
        try:
            activity = _activity_id(activity_id)
        except ActivityNotFoundError:
            return _error_response(request, "Activity not found.")
        try:
            practice.submit_response(activity, response)
        except ActivityNotFoundError:
            return _error_response(request, "Activity not found.")
        except InvalidPracticeResponseError as exc:
            view = practice.start_practice(activity)
            if is_htmx:
                return _practice_partial(
                    request,
                    view,
                    error=str(exc),
                    submitted_response=response,
                )
            return templates.TemplateResponse(
                request,
                "practice.html",
                {"view": view, "error": str(exc), "submitted_response": response},
            )
        except SubmissionInProgressError as exc:
            view = practice.start_practice(activity)
            if is_htmx:
                return _practice_partial(
                    request,
                    view,
                    error=str(exc),
                    submitted_response=response,
                )
            return templates.TemplateResponse(
                request,
                "practice.html",
                {"view": view, "error": str(exc), "submitted_response": response},
            )
        except EvaluationFailedError as exc:
            # SPEC-015 §64: preserve the learner's response and show a safe
            # message instead of an internal failure.
            view = practice.start_practice(activity)
            if is_htmx:
                return _practice_partial(
                    request,
                    view,
                    error=str(exc),
                    submitted_response=response,
                )
            return templates.TemplateResponse(
                request,
                "practice.html",
                {"view": view, "error": str(exc), "submitted_response": response},
            )
        if is_htmx:
            return _feedback_partial(request, practice)
        return RedirectResponse("/feedback", status_code=303)

    @app.get("/feedback", response_class=HTMLResponse)
    async def feedback_page(request: Request) -> Response:
        """Render the learner feedback page (UC-005)."""
        practice = practice_for_request(request)
        try:
            view = practice.get_feedback()
        except FeedbackNotFoundError:
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(request, "feedback.html", {"view": view})

    @app.get("/reflect", response_class=HTMLResponse)
    async def reflection_page(request: Request) -> Response:
        """Render the purposeful reflection prompt (UC-006)."""
        practice = practice_for_request(request)
        try:
            view = practice.get_reflection()
        except FeedbackNotFoundError:
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(request, "reflection.html", {"view": view})

    @app.post("/reflect", response_class=HTMLResponse)
    async def submit_reflection(
        request: Request,
        content: Annotated[str, Form()] = "",
    ) -> Response:
        """Save the learner's Reflection and show completion (UC-007).

        SPEC-021: if persistence fails, an error is shown and the learner is
        not falsely told the completion was recorded.
        """
        practice = practice_for_request(request)
        try:
            practice.submit_reflection(content)
        except FeedbackNotFoundError:
            return RedirectResponse("/", status_code=303)
        except InvalidReflectionResponseError as exc:
            view = practice.get_reflection()
            return templates.TemplateResponse(
                request,
                "reflection.html",
                {"view": view, "error": str(exc), "submitted_content": content},
            )
        except PersistenceError as exc:
            # SPEC-021 §14: persistence failures are explicit and observable
            view = practice.get_reflection()
            return templates.TemplateResponse(
                request,
                "reflection.html",
                {"view": view, "error": str(exc), "submitted_content": content},
                status_code=500,
            )
        return RedirectResponse("/complete", status_code=303)

    @app.get("/complete", response_class=HTMLResponse)
    async def completion_page(request: Request) -> Response:
        """Render the completion confirmation with its continuation (SPEC-025).

        The continuation is authored content resolved by the completed
        activity alone — never learner state — and is an invitation, not a
        forced next step: Explore and History stay reachable as before.
        """
        practice = practice_for_request(request)
        try:
            view = practice.get_completion()
        except CompletionNotFoundError:
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(
            request,
            "complete.html",
            {
                "view": view,
                "continuation_heading": practice.continuation_heading,
                "continuation_action_label": practice.continuation_action_label,
            },
        )

    # SPEC-021: Practice History and Review Routes

    @app.get("/history", response_class=HTMLResponse)
    async def practice_history(request: Request) -> Response:
        """Render the learner's practice history (SPEC-021 §8).

        SPEC-021 §8: the history view should make it easy to answer
        "What have I practised recently?" Recent completed practice appears first.

        Empty history is a valid state showing a clear empty state explaining
        that completed practice will appear here.
        """
        practice = practice_for_request(request)
        try:
            view = practice.get_practice_history()
        except PersistenceError as exc:
            return _error_response(
                request,
                "We couldn't load your practice history.",
                status_code=500,
                description=str(exc),
            )
        return templates.TemplateResponse(request, "history.html", {"view": view})

    @app.get("/history/{completion_id}", response_class=HTMLResponse)
    async def practice_review(request: Request, completion_id: str) -> Response:
        """Render a review of a completed practice (SPEC-021 §9).

        SPEC-021 §9: selecting a completed practice allows the learner to review
        the meaningful parts of that specific practice instance. The review
        contains the relevant activity, stimulus/context, response, evaluation,
        feedback, reflection, and completion timestamp available to the
        application. The review is a reflection and evidence surface, not a
        grading dashboard.

        Args:
            completion_id: The stable identity of the completion to review.

        Returns:
            HTML response with the review, or an error page if the completion
            does not exist or retrieval fails.
        """
        practice = practice_for_request(request)
        try:
            cid = _completion_id(completion_id)
        except CompletionNotFoundError:
            return _error_response(request, "Practice record not found.")

        try:
            view = practice.get_practice_review(cid)
        except CompletionNotFoundError:
            return _error_response(
                request,
                "Practice record not found.",
                description="This completed practice record is no longer available.",
            )
        except PersistenceError as exc:
            return _error_response(
                request,
                "We couldn't load the practice record.",
                status_code=500,
                description=str(exc),
            )

        return templates.TemplateResponse(request, "review.html", {"view": view})

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Return the platform health status."""
        return {"status": "healthy"}

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics() -> str:
        """Expose the in-memory metrics registry in Prometheus-like format."""
        return metrics_registry.render()

    return app


app = create_app(config)
