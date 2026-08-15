# Fablit

Fablit is an open-source educational platform for helping learners build practical skills through deliberate practice, meaningful feedback, and continuous reflection.

This repository implements **SPEC-001 — Bootstrap Platform**, **SPEC-002 — Engineering Toolchain**, **SPEC-003 — Configuration & Logging**, **SPEC-004 — Shared Platform Services**, **SPEC-005 — Assessment Activity Domain Foundation**, **SPEC-006 — Submission Domain Foundation**, **SPEC-007 — Evaluation Domain Foundation**, **SPEC-008 — Feedback Domain Foundation**, **SPEC-009 — Reflection Domain Foundation**, **SPEC-010 — Skill Domain Foundation**, **SPEC-011 — Skill–Assessment Activity Association**, and **SPEC-012 — Learner Practice Application Flow**. It intentionally avoids Skill Labs, Content Packs, learner accounts, authentication, databases, AI services, analytics, user management, and recommendation logic.

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

The platform exposes:

- `GET /` — the learner practice dashboard (3–5 available activities)
- `GET /activities/{activity_id}` — the practice activity page
- `POST /activities/{activity_id}/submit` — submit a learner response
- `GET /feedback` — learner feedback derived from the demo evaluation
- `GET /reflect` and `POST /reflect` — the purposeful reflection prompt and submission
- `GET /complete` — the completion confirmation
- `GET /health` — returns `{ "status": "healthy" }`
- `GET /metrics` — returns in-memory Prometheus-style metrics
- `GET /docs` — FastAPI Swagger UI
- `GET /redoc` — FastAPI ReDoc documentation

The learner experience is server-rendered HTML (Jinja2 templates) enhanced with HTMX (vendored under `app/static/`); the core journey works without JavaScript. A deterministic demo evaluator (no AI, no network, no async workers) drives the feedback step, and the journey is preserved in memory for the vertical slice.

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

SPEC-005 through SPEC-011 introduce the learning-domain capabilities as in-memory packages under `fablit.domain`, independent of platform infrastructure and persistence:

- `Assessment` — a structured collection of Assessment Activities with stable identity, metadata (title, description, status), and sequential ordering
- `AssessmentActivity` — the smallest unit of learner interaction, with stable identity, a controlled activity type, instructions/prompt reference, an explicit position, status, and zero or more Skill references by stable identity (`skill_ids`) establishing the many-to-many Skill–Activity association (SPEC-011)
- `Submission` — the learner's response to an Assessment Activity, with stable identity, learner and activity references, a generic extensible response, and a Draft → Submitted lifecycle enforced by `submit()`
- `Evaluation` — the structured interpretation of a Submission, with stable identity, a Submission reference, one or more structured Findings, and a timezone-aware evaluation timestamp; immutable after creation
- `EvaluationFinding` — one structured observation or judgement about a Submission, with stable identity and meaningful observation text
- `Feedback` — learner-facing guidance derived from an Evaluation, with stable identity, an Evaluation reference, a general learner-facing content field, and a timezone-aware creation timestamp; immutable after creation and free of scoring, Reflection, generation-mechanism, and persistence concerns
- `Reflection` — the learner's deliberate response to Feedback, with stable identity, a Feedback reference, a general learner-authored content field, and a timezone-aware creation timestamp; immutable after creation and free of confidence scoring, improvement goals, action plans, generation-mechanism, and persistence concerns
- `Skill` — the measurable, transferable learner capability being developed, with stable identity, a meaningful name and description, and immutability after creation; independent of any single Assessment Activity, Evaluation criteria, Progress, mastery, scoring, hierarchy, curriculum, examination, and AI concerns, and reusable across any number of Assessment Activities (SPEC-011)
- Controlled `ActivityType`, `SubmissionStatus`, and assessment status enumerations (multiple choice, written response, observation, reflection; draft, submitted; draft, published)
- Domain exceptions: `InvalidAssessmentError`, `InvalidActivityError`, `DuplicateActivityPositionError`, `InvalidSubmissionError`, `InvalidSubmissionTransitionError`, `InvalidEvaluationError`, `InvalidEvaluationFindingError`, `InvalidFeedbackError`, `InvalidReflectionError`, `InvalidSkillError`

No database, scoring, Skill hierarchies, Progress, mastery, delivery, or AI feedback-generation behaviour is included; those are deferred to future specifications.

## Application layer and learner practice flow

SPEC-012 introduces the first application layer under `fablit.application`, separate from both the Web/UI layer (`app`) and the learning domain (`fablit.domain`):

- `PracticeApplication` — the use-case facade (UC-001–UC-007): dashboard retrieval, start practice, submit response, demo evaluation, feedback preparation, reflection, and completion
- View models (`PracticeDashboardView`, `PracticeActivityView`, `FeedbackView`, `ReflectionView`, `CompletionView`) — learner-facing representations that keep presentation concerns out of the domain
- `DemoEvaluator` — a deterministic, predefined evaluation for the demo activities (no AI provider, no network, no async workers)
- `LearnerJourneyStore` — a minimal in-memory store preserving the Submission → Evaluation → Feedback → Reflection chain for the vertical slice
- Demo content: 3–5 practice activities across the Visual Analysis, Written Communication, and Critical Observation Skills, with a stable demo learner context

The vertical slice introduces no authentication, scoring, Progress, mastery, recommendations, or examination-specific logic.

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

Playwright is included in the development toolchain for browser-level checks. SPEC-012 adds an opt-in browser journey test (`tests/e2e`) that drives the full learner flow in Chromium; it is skipped unless `RUN_BROWSER_TESTS=1` is set, and the CI workflow runs it in a dedicated browser job (`uv run playwright install --with-deps chromium`).

Run the browser journey tests locally:

```bash
uv run playwright install chromium
make e2e
```

If you have an existing Chromium/Chrome binary instead of a Playwright download, point Playwright at it with `PLAYWRIGHT_EXECUTABLE_PATH` (root containers may also need `PLAYWRIGHT_NO_SANDBOX=1`).

## PythonAnywhere deployment notes

The ASGI application object is available at:

```text
app.main:app
```

PythonAnywhere deployments should install dependencies with uv and point the web app configuration at the `app.main:app` ASGI application.
