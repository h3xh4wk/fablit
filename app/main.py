"""FastAPI application entry point for the Fablit bootstrap platform."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run bootstrap startup and shutdown lifecycle hooks."""
    app.state.ready = True
    yield
    app.state.ready = False


app = FastAPI(
    title="Fablit",
    description="Bootstrap platform for Fablit.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", response_class=PlainTextResponse)
async def homepage() -> str:
    """Return the bootstrap homepage response."""
    return "Welcome to Fablit"


@app.get("/health")
async def health() -> dict[str, str]:
    """Return the platform health status."""
    return {"status": "healthy"}
