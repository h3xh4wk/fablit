"""FastAPI application entry point for the Fablit bootstrap platform."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from fablit.config import load_config
from fablit.logging import init_logging, reset_request_context, set_request_context

config = load_config()
init_logging(config)
logger = logging.getLogger("fablit.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run bootstrap startup and shutdown lifecycle hooks."""
    logger.info("application startup", extra={"version": config.version})
    app.state.ready = True
    app.state.config = config
    yield
    app.state.ready = False
    logger.info("application shutdown")


app = FastAPI(
    title="Fablit",
    description="Bootstrap platform for Fablit.",
    version=config.version,
    lifespan=lifespan,
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    trace_id = request.headers.get("X-Trace-ID")
    token = set_request_context(request_id=request_id, trace_id=trace_id)

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


@app.get("/", response_class=PlainTextResponse)
async def homepage() -> str:
    """Return the bootstrap homepage response."""
    return "Welcome to Fablit"


@app.get("/health")
async def health() -> dict[str, str]:
    """Return the platform health status."""
    return {"status": "healthy"}
