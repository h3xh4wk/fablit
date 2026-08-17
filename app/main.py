"""FastAPI application entry point for the Fablit platform (SPEC-012).

SPEC-014 establishes the learner pilot deployment boundary: the application
is assembled by ``create_app`` so environment-specific safety settings can be
applied and tested, development-only interfaces (API documentation) are
hidden in the pilot environment, and unhandled errors render a learner-facing
page instead of exposing internals.
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

from fablit.application import (
    DEMO_LEARNER_ID,
    ActivityNotFoundError,
    CompletionNotFoundError,
    DemoEvaluator,
    EvaluationFailedError,
    FeedbackNotFoundError,
    InvalidPracticeResponseError,
    InvalidReflectionResponseError,
    LearnerJourneyStore,
    PracticeApplication,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
    build_stimulus_provider,
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


def _build_practice_application() -> PracticeApplication:
    """Assemble the demo learner application for the first vertical slice.

    SPEC-015: stimulus resolution goes through the provider abstraction so
    external image retrieval is isolated and replaceable, and the demo
    evaluator is wired to the seeded activity content.
    """
    activities = build_demo_activities()
    store = LearnerJourneyStore(
        learner_id=DEMO_LEARNER_ID,
        activities=activities,
        skills=build_demo_skills(),
    )
    return PracticeApplication(
        store=store,
        evaluator=DemoEvaluator(build_demo_activity_map(activities)),
        stimulus_provider=build_stimulus_provider(
            activities,
            provider_name=config.stimulus_provider,
            fallback_image_overrides=config.stimulus_fallback_images,
            wikimedia_endpoint=config.wikimedia_endpoint,
            wikimedia_timeout=config.wikimedia_timeout,
            wikimedia_width=config.wikimedia_width,
            wikimedia_limit=config.wikimedia_limit,
        ),
    )


def _practice(request: Request) -> PracticeApplication:
    """Return the lifespan-initialised practice application."""
    practice: PracticeApplication | None = request.app.state.practice
    if practice is None:
        raise RuntimeError("practice application is not initialised")
    return practice


def _activity_id(value: str) -> UUID:
    """Parse an activity identity, raising ActivityNotFoundError when invalid."""
    try:
        return UUID(value)
    except ValueError:
        raise ActivityNotFoundError("Activity not found.") from None


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
        app.state.practice = _build_practice_application()
        yield
        app.state.ready = False
        app.state.practice = None
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
    app.middleware("http")(request_logging_middleware)
    app.add_exception_handler(Exception, _unhandled_exception_handler)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> Response:
        """Render the learner practice dashboard (UC-001)."""
        view = _practice(request).get_dashboard()
        return templates.TemplateResponse(request, "dashboard.html", {"view": view})

    @app.get("/activities/{activity_id}", response_class=HTMLResponse)
    async def practice_page(request: Request, activity_id: str) -> Response:
        """Render the practice activity page (UC-002)."""
        practice = _practice(request)
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
        """Accept a learner response and move to feedback (UC-003/004/005)."""
        practice = _practice(request)
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
            return templates.TemplateResponse(
                request,
                "practice.html",
                {"view": view, "error": str(exc), "submitted_response": response},
            )
        except EvaluationFailedError as exc:
            # SPEC-015 §64: preserve the learner's response and show a safe
            # message instead of an internal failure.
            view = practice.start_practice(activity)
            return templates.TemplateResponse(
                request,
                "practice.html",
                {"view": view, "error": str(exc), "submitted_response": response},
            )
        return RedirectResponse("/feedback", status_code=303)

    @app.get("/feedback", response_class=HTMLResponse)
    async def feedback_page(request: Request) -> Response:
        """Render the learner feedback page (UC-005)."""
        practice = _practice(request)
        try:
            view = practice.get_feedback()
        except FeedbackNotFoundError:
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(request, "feedback.html", {"view": view})

    @app.get("/reflect", response_class=HTMLResponse)
    async def reflection_page(request: Request) -> Response:
        """Render the purposeful reflection prompt (UC-006)."""
        practice = _practice(request)
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
        """Save the learner's Reflection and show completion (UC-007)."""
        practice = _practice(request)
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
        return RedirectResponse("/complete", status_code=303)

    @app.get("/complete", response_class=HTMLResponse)
    async def completion_page(request: Request) -> Response:
        """Render the completion confirmation."""
        practice = _practice(request)
        try:
            view = practice.get_completion()
        except CompletionNotFoundError:
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(request, "complete.html", {"view": view})

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
