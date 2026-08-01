# Fablit

Fablit is an open-source educational platform for helping learners build practical skills through deliberate practice, meaningful feedback, and continuous reflection.

This repository currently implements **SPEC-001 — Bootstrap Platform** only. It intentionally avoids educational-domain features such as Skill Labs, Assessments, Content Packs, authentication, databases, AI services, analytics, and user management.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Local setup

Install the application and development dependencies:

```bash
uv sync --dev
```

## Run the application

Start the FastAPI application with a single command:

```bash
uv run uvicorn app.main:app --reload
```

The bootstrap platform exposes:

- `GET /` — returns `Welcome to Fablit`
- `GET /health` — returns `{ "status": "healthy" }`
- `GET /docs` — FastAPI Swagger UI
- `GET /redoc` — FastAPI ReDoc documentation

## Quality checks

Run the automated checks locally:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

Playwright is included in the development toolchain for future browser-level checks. SPEC-001 does not add browser workflows beyond confirming FastAPI documentation routes are available through API tests.

## PythonAnywhere deployment notes

The ASGI application object is available at:

```text
app.main:app
```

PythonAnywhere deployments should install dependencies with uv and point the web app configuration at the `app.main:app` ASGI application.
