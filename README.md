# Fablit

Fablit is an open-source educational platform for helping learners build practical skills through deliberate practice, meaningful feedback, and continuous reflection.

This repository implements **SPEC-001 — Bootstrap Platform**, **SPEC-002 — Engineering Toolchain**, **SPEC-003 — Configuration & Logging**, **SPEC-004 — Shared Platform Services**, **SPEC-005 — Assessment Activity Domain Foundation**, **SPEC-006 — Submission Domain Foundation**, **SPEC-007 — Evaluation Domain Foundation**, and **SPEC-008 — Feedback Domain Foundation**. It intentionally avoids Skill Labs, Content Packs, learner accounts, authentication, databases, AI services, analytics, and user management.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Local setup

Install the application and development dependencies:

```bash
uv sync --dev
```

Install Git hooks for local quality checks:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## Run the application

Start the FastAPI application with a single command:

```bash
uv run uvicorn app.main:app --reload
```

The bootstrap platform exposes:

- `GET /` — returns `Welcome to Fablit`
- `GET /health` — returns `{ "status": "healthy" }`
- `GET /metrics` — returns in-memory Prometheus-style metrics
- `GET /docs` — FastAPI Swagger UI
- `GET /redoc` — FastAPI ReDoc documentation

## Configuration and logging

Fablit loads configuration from environment variables, an optional JSON or YAML config file referenced by `FABLIT_CONFIG`, and built-in defaults.

Key settings include:

- `FABLIT_SERVICE_NAME`
- `FABLIT_ENV`
- `FABLIT_HOST`
- `FABLIT_PORT`
- `FABLIT_DEBUG`
- `FABLIT_LOG_LEVEL`
- `FABLIT_LOG_FORMAT`

The application initializes structured logging during startup and attaches service and environment context to every log record.

## Shared platform services

The repository now includes a lightweight shared-platform package under fablit.platform with reusable helpers for configuration loading, structured correlation context, metrics, authentication helpers, resilience primitives, and health checks. See examples/platform_services.py for a simple integration example.

## Learning domain

SPEC-005, SPEC-006, SPEC-007, and SPEC-008 introduce the learning-domain capabilities as in-memory packages under `fablit.domain`, independent of platform infrastructure and persistence:

- `Assessment` — a structured collection of Assessment Activities with stable identity, metadata (title, description, status), and sequential ordering
- `AssessmentActivity` — the smallest unit of learner interaction, with stable identity, a controlled activity type, instructions/prompt reference, an explicit position, and status
- `Submission` — the learner's response to an Assessment Activity, with stable identity, learner and activity references, a generic extensible response, and a Draft → Submitted lifecycle enforced by `submit()`
- `Evaluation` — the structured interpretation of a Submission, with stable identity, a Submission reference, one or more structured Findings, and a timezone-aware evaluation timestamp; immutable after creation
- `EvaluationFinding` — one structured observation or judgement about a Submission, with stable identity and meaningful observation text
- `Feedback` — learner-facing guidance derived from an Evaluation, with stable identity, an Evaluation reference, a general learner-facing content field, and a timezone-aware creation timestamp; immutable after creation and free of scoring, Reflection, generation-mechanism, and persistence concerns
- Controlled `ActivityType`, `SubmissionStatus`, and assessment status enumerations (multiple choice, written response, observation, reflection; draft, submitted; draft, published)
- Domain exceptions: `InvalidAssessmentError`, `InvalidActivityError`, `DuplicateActivityPositionError`, `InvalidSubmissionError`, `InvalidSubmissionTransitionError`, `InvalidEvaluationError`, `InvalidEvaluationFindingError`, `InvalidFeedbackError`

No database, scoring, Reflection, delivery, or AI feedback-generation behaviour is included; those are deferred to future specifications.

## Quality checks

Run the automated checks locally:

```bash
uv run pre-commit run --all-files
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=app --cov-report=xml
```

You can also run the consolidated developer workflow:

```bash
make check
```

Playwright is included in the development toolchain for future browser-level checks. SPEC-001 does not add browser workflows beyond confirming FastAPI documentation routes are available through API tests.

## PythonAnywhere deployment notes

The ASGI application object is available at:

```text
app.main:app
```

PythonAnywhere deployments should install dependencies with uv and point the web app configuration at the `app.main:app` ASGI application.
