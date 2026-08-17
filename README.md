# Fablit

Fablit is an open-source educational platform for helping learners build practical skills through deliberate practice, meaningful feedback, and continuous reflection.

This repository implements **SPEC-001 — Bootstrap Platform**, **SPEC-002 — Engineering Toolchain**, **SPEC-003 — Configuration & Logging**, **SPEC-004 — Shared Platform Services**, **SPEC-005 — Assessment Activity Domain Foundation**, **SPEC-006 — Submission Domain Foundation**, **SPEC-007 — Evaluation Domain Foundation**, **SPEC-008 — Feedback Domain Foundation**, **SPEC-009 — Reflection Domain Foundation**, **SPEC-010 — Skill Domain Foundation**, **SPEC-011 — Skill–Assessment Activity Association**, **SPEC-012 — Learner Practice Application Flow**, **SPEC-013 — Learner Experience & Visual Foundation**, **SPEC-014 — Learner Pilot Deployment**, and **SPEC-015 — Contextual Visual Stimulus & Response-Aware Evaluation**. It intentionally avoids Skill Labs, Content Packs, learner accounts, authentication, databases, AI services, analytics, user management, recommendation logic, scoring, gamification, Progress tracking, and a live external image dependency by default; production readiness (backups, monitoring, security hardening, scalability, and a full security assessment) is deliberately deferred to a separate assessment.

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
- `GET /docs` — FastAPI Swagger UI (development and testing environments only)
- `GET /redoc` — FastAPI ReDoc documentation (development and testing environments only)

The learner experience is server-rendered HTML (Jinja2 templates) enhanced with HTMX (vendored under `app/static/`); the core journey works without JavaScript. A deterministic demo evaluator (no AI, no network, no async workers) drives the feedback step, and the journey is preserved in memory for the vertical slice.

## Pilot deployment (SPEC-014)

SPEC-014 makes the current learner experience pilot-ready by placing an operational boundary around it — no new learning capability and no new domain concept. The pilot environment is driven entirely by environment-variable configuration, exposes no development interfaces or internals to learners (API documentation is disabled in `production`, unhandled errors render a learner-friendly page), and keeps the existing in-memory persistence, which is acceptable for the pilot and documented as such.

See [docs/engineering/deployment.md](docs/engineering/deployment.md) for the full deployment guide (target, runtime, environment variables, startup, persistence behaviour, health check, logs, restart, rollback, and known limitations), and [docs/pilot/](docs/pilot/README.md) for learner instructions and the lightweight feedback-recording mechanism.

SPEC-013 wraps that journey in a calm, personal learner experience: the dashboard reads as an invitation to explore, the practice page is quiet and prompt-forward, structured Findings are presented conversationally (no scores), reflection flows naturally from feedback, and completion is a quiet acknowledgement with a clear route back to practice. Visual consistency comes from a small design-system foundation and centralized design tokens in `app/static/css/fablit.css` (typography, spacing, colours, border radius, shadows, transitions, container widths), with responsive layouts for mobile, tablet, and desktop, and accessibility built in (skip link, labelled fields, visible focus states, reduced-motion support).

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
- `FABLIT_STIMULUS_PROVIDER` — `builtin` (default; deterministic bundled images, no network) or `wikimedia` (approved external source with a safe built-in fallback)
- `FABLIT_STIMULUS_FALLBACK_IMAGES` — optional JSON object mapping activity title to a custom fallback image URL, overriding the bundled images without code changes (e.g. `{"Visual Analysis — Composition": "/static/images/my-image.svg"}`)
- `FABLIT_WIKIMEDIA_ENDPOINT` — Wikimedia Commons API endpoint (default `https://commons.wikimedia.org/w/api.php`)
- `FABLIT_WIKIMEDIA_TIMEOUT` — retrieval timeout in seconds (default `10.0`)
- `FABLIT_WIKIMEDIA_WIDTH` — requested thumbnail width (default `1200`)
- `FABLIT_WIKIMEDIA_LIMIT` — candidate images searched (default `5`)

The `FABLIT_WIKIMEDIA_*` settings only take effect with `FABLIT_STIMULUS_PROVIDER=wikimedia`.

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
- `ActivityStimulusContext` (SPEC-015) — the contextual visual stimulus requirements an activity may define (learning focus, stimulus context, retrieval query), used to identify an appropriate image for the learner
- `StimulusInstance` (SPEC-015) — the resolved visual stimulus shown to a learner as part of an activity instance, retaining provider, asset ID, direct image URL, source page URL, creator, license, attribution, alternative text, and a timezone-aware retrieval timestamp; immutable after creation, independent of any specific image provider, HTTP, or network calls
- `EvaluationFinding.evidence` (SPEC-015) — an optional non-blank response excerpt or matched concept that grounds a Finding in the learner's actual response (response-aware evaluation)
- Controlled `ActivityType`, `SubmissionStatus`, and assessment status enumerations (multiple choice, written response, observation, reflection; draft, submitted; draft, published)
- Domain exceptions: `InvalidAssessmentError`, `InvalidActivityError`, `DuplicateActivityPositionError`, `InvalidSubmissionError`, `InvalidSubmissionTransitionError`, `InvalidEvaluationError`, `InvalidEvaluationFindingError`, `InvalidFeedbackError`, `InvalidReflectionError`, `InvalidSkillError`

No database, scoring, Skill hierarchies, Progress, mastery, delivery, or AI feedback-generation behaviour is included; those are deferred to future specifications.

## Application layer and learner practice flow

SPEC-012 introduces the first application layer under `fablit.application`, separate from both the Web/UI layer (`app`) and the learning domain (`fablit.domain`):

- `PracticeApplication` — the use-case facade (UC-001–UC-007): dashboard retrieval, start practice, submit response, response-aware demo evaluation, feedback preparation, reflection, and completion
- View models (`PracticeDashboardView`, `PracticeActivityView`, `FeedbackView`, `ReflectionView`, `CompletionView`, `StimulusView`) — learner-facing representations that keep presentation concerns out of the domain
- `DemoEvaluator` — a deterministic, response-aware evaluator (no AI provider, no network, no async workers): for stimulus activities it grounds Findings in the learner's actual response by matching known concepts, so different responses produce different Findings (SPEC-015 §69); empty and very short responses are handled without fabricating positive Findings (§62–63)
- `StimulusProvider` abstraction (SPEC-015) — external image retrieval isolated behind an application-level boundary: a deterministic built-in provider serving bundled images (the default), a `WikimediaCommonsProvider` for the approved external source, and a resilient composition that falls back to the built-in stimulus when external retrieval fails (§21–22)
- `LearnerJourneyStore` — a minimal in-memory store preserving the Stimulus → Submission → Evaluation → Feedback → Reflection chain for the vertical slice; a completed activity retains the exact stimulus that was shown (§18, §48)
- Demo content: 3–5 practice activities across the Visual Analysis, Written Communication, and Critical Observation Skills, with a stable demo learner context; three image-dependent activities present a bundled visual stimulus, and "Visual Analysis — Composition" is the SPEC-015 reference activity (§56–58)

The vertical slice introduces no authentication, scoring, Progress, mastery, recommendations, gamification, or examination-specific logic.

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

Playwright is included in the development toolchain for browser-level checks. The browser journey test (`tests/e2e`) drives the full learner flow — including the SPEC-015 visual stimulus and response-aware feedback — in Chromium, but it is **skipped in the local environment by default**: it only runs when `RUN_BROWSER_TESTS=1` is set, and the CI workflow runs it in a dedicated browser job (`uv run playwright install --with-deps chromium`). Normal local runs (`make check`, `pytest`) stay green without any browser installed.

Because many local environments have constraints (no Playwright browser download, no display, or sandbox restrictions — root containers in particular), browser tests are not supported locally: keep them skipped and let the CI browser job cover them. Only opt in locally when a compatible browser is genuinely available:

```bash
uv run playwright install chromium
make e2e
```

If you have an existing Chromium/Chrome binary instead of a Playwright download, point Playwright at it with `PLAYWRIGHT_EXECUTABLE_PATH` (root containers may also need `PLAYWRIGHT_NO_SANDBOX=1`).

## PythonAnywhere deployment

The ASGI application object is available at `app.main:app`. The SPEC-014 pilot runs on PythonAnywhere (see [ADR-008](docs/adr/ADR-008-pythonanywhere-deployment.md)); follow [docs/engineering/deployment.md](docs/engineering/deployment.md) for the complete, reproducible deployment process.
