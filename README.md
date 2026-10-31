# Fablit

Fablit is an open-source educational platform for helping learners build practical skills through deliberate practice, meaningful feedback, and continuous reflection.

This repository implements **SPEC-001 — Bootstrap Platform**, **SPEC-002 — Engineering Toolchain**, **SPEC-003 — Configuration & Logging**, **SPEC-004 — Shared Platform Services**, **SPEC-005 — Assessment Activity Domain Foundation**, **SPEC-006 — Submission Domain Foundation**, **SPEC-007 — Evaluation Domain Foundation**, **SPEC-008 — Feedback Domain Foundation**, **SPEC-009 — Reflection Domain Foundation**, **SPEC-010 — Skill Domain Foundation**, **SPEC-011 — Skill–Assessment Activity Association**, **SPEC-012 — Learner Practice Application Flow**, **SPEC-013 — Learner Experience & Visual Foundation**, **SPEC-014 — Learner Pilot Deployment**, **SPEC-015 — Contextual Visual Stimulus & Response-Aware Evaluation**, **SPEC-016 — First Learner Experience Refinement**, **SPEC-017 — Submission & Evaluation Feedback**, **SPEC-018 — Learner Practice Continuity & Progress Foundation**, **SPEC-019 — Explore Surface & Visual Practice Refinement**, **SPEC-020 — Visual Practice Experience Foundation**, **SPEC-021 — Persistent Practice History & Learner Review**, **SPEC-022 — Optional Practice Modes & Learner Choice**, **SPEC-023 — Practice Library Expansion & Skill Coverage**, **SPEC-024 — Learner Identity & Private Practice History**, **SPEC-025 — Curated Practice Continuity**, **SPEC-026 — Metacognitive Practice & Reflection Integration**, **SPEC-029 — Practice Content Model & Learning Contract**, **SPEC-030 — Practice Feedback Quality**, **SPEC-031 — Sketchbook-to-Practice Reflection**, **SPEC-032 — AI-Assisted Practice Authoring**, **SPEC-035 — Publish Approved Practice Candidates to the Learner Library**, **SPEC-040 — AI-Assisted Authoring Brief Creation**, **SPEC-041 — Curated Fashion & Design Intelligence Feed**, **SPEC-043 — Fashion & Design Pulse Editorial UI and Source Attribution**, and **SPEC-044 — Learner-Requested Personalised Practice (story-linked responses)**. It intentionally avoids Skill Labs, Content Packs, learner accounts, authentication, learner-facing AI services (internal AI authoring and news curation are opt-in, human-operated tools), analytics, user management, recommendation logic, scoring, gamification, mastery, and a live external image dependency by default; learner persistence is the focused SPEC-021 practice-history boundary (Google Cloud Datastore in production, opt-in via configuration) alongside the opt-in authoring-side stores for internal candidates (FIX-7), published practices (SPEC-035), and curated news stories (SPEC-041), and production readiness (backups, monitoring, security hardening, scalability, and a full security assessment) is deliberately deferred to a separate assessment.

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

- `GET /` — the learner practice dashboard (the available activity library)
- `GET /practice` — the practice-mode choice: a short drill or a full practice (SPEC-022; optional — the activity library below needs no mode selection)
- `GET /practice/{mode_id}` — the activities a chosen practice mode offers (`short-drill`, `full-practice`; SPEC-022)
- `GET /practice/request` and `POST /practice/request` — the short request composer for a private, learner-requested practice (SPEC-044); `?story={story_id}` prefills it from a Pulse story's "What to try" prompt
- `GET /practice/request/{practice_id}` — the validated brief for one requested practice, before the learner chooses to begin (SPEC-044)
- `GET /activities/{activity_id}` — the practice activity page (echoes the captured intention, SPEC-026)
- `GET /activities/{activity_id}/intention` and `POST …/intention` — the optional pre-practice intention prompt; skipping never blocks practice (SPEC-026)
- `POST /activities/{activity_id}/submit` — submit a learner response
- `GET /feedback` — learner feedback derived from the demo evaluation, with the structured optional reflection panel (SPEC-026)
- `GET /reflect` and `POST /reflect` — the purposeful reflection prompt and submission; skipping is accepted gracefully and never blocks completion (SPEC-026)
- `GET /complete` — the completion confirmation, with the activity's curated next-practice continuation when one is authored (SPEC-025)
- `GET /history` — the learner's practice history (completed practice, newest first; SPEC-021)
- `GET /history/{completion_id}` — review of one completed practice (response, feedback, reflection, stimulus, completion time; SPEC-021)
- `GET /history/story-responses/{response_id}` — revisit one private response to a Pulse story prompt with its originating story and prompt (SPEC-044)
- `GET /pulse` — the learner-facing Fashion & Design Pulse feed of curated stories (SPEC-041)
- `POST /pulse/stories/{story_id}/responses` — save a private "Try this" response to a story prompt, without evaluation or a practice completion (SPEC-044)
- `GET /authoring/pulse` and `POST /authoring/pulse/curate` — the SEC-001-protected on-demand curation page and durable job start (SPEC-041, SPEC-042)
- `GET /authoring/pulse/jobs/latest` and `GET /authoring/pulse/jobs/{job_id}` — persisted curation job status, progress, counters, and final report, behind the same author credential (SPEC-042)
- `POST /tasks/news-curation` — the task handler that runs one bounded unit of an accepted curation job, authenticated by the task's own OIDC identity rather than an author session (SPEC-042)
- `GET /health` — returns `{ "status": "healthy" }`
- `GET /metrics` — returns in-memory Prometheus-style metrics
- `GET /docs` — FastAPI Swagger UI (development and testing environments only)
- `GET /redoc` — FastAPI ReDoc documentation (development and testing environments only)

The learner experience is server-rendered HTML (Jinja2 templates) enhanced with HTMX (vendored under `app/static/`); the core journey works without JavaScript. A deterministic demo evaluator (no AI, no network, no async workers) drives the feedback step, and the journey is preserved in memory for the vertical slice.

## Deployment (SPEC-014 / SPEC-034)

The Fablit platform targets Google App Engine (standard environment, Python 3.12) with Google Cloud Datastore for practice history persistence (SPEC-021), curated news stories (SPEC-041), and private story responses (SPEC-044), and Google Cloud Storage for durable private sketchbook artifact storage (SPEC-034). The production environment is driven entirely by environment-variable configuration, uses Google Application Default Credentials (ADC), exposes no development interfaces or internals to learners (API documentation is disabled in `production`, unhandled errors render a learner-friendly page), and serves private artifacts through authenticated, learner-scoped application routes (`Cache-Control: private, no-store`). Local development and testing run out of the box with in-memory or file-backed storage without any GCP credentials.

See [docs/engineering/deployment.md](docs/engineering/deployment.md) for the full deployment guide (target, runtime, environment variables, startup, persistence behaviour, health check, logs, restart, rollback, and known limitations), and [docs/pilot/](docs/pilot/README.md) for learner instructions and the lightweight feedback-recording mechanism.

SPEC-013 wraps that journey in a calm, personal learner experience: the dashboard reads as an invitation to explore, the practice page is quiet and prompt-forward, structured Findings are presented conversationally (no scores), reflection flows naturally from feedback, and completion is a quiet acknowledgement with a clear route back to practice. Visual consistency comes from a small design-system foundation and centralized design tokens in `app/static/css/fablit.css` (typography, spacing, colours, border radius, shadows, transitions, container widths), with responsive layouts for mobile, tablet, and desktop, and accessibility built in (skip link, labelled fields, visible focus states, reduced-motion support).

SPEC-016 refines the complete learner activity from functional to intentional and inviting: conversational invitations, hero stimulus presentation, notebook-like response areas, conversational submit actions, "Something you noticed" feedback presentation, quiet accomplishment on completion, and consistent use of semantic emoji cues — all without introducing new domain models, persistence, or backend architecture.

SPEC-019 strengthens the Explore surface so it reads as a minimal design-practice library — image-dependent activities show a bundled preview (a discovery cue, never a second stimulus lifecycle), text-first activities stay text-first, and the card grid uses desktop space more effectively. SPEC-020 then makes the Practice Activity screen a focused practice workspace: the existing stimulus, task, and response are presented as an explicit labelled hierarchy (Observe → Your task → Your response), the resolved stimulus is shown at a useful scale inside the observe region, text responses get a comfortable response surface with visible guidance, and learner input is preserved on failure. Both specs are presentation-only: the SPEC-015 stimulus lifecycle, SPEC-017 submission acknowledgement and duplicate-submission protection, and the SPEC-018 completion semantics are unchanged, and no scoring, progress indicators, gamification, new image provider, database migration, or new runtime dependency is introduced.

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
- `FABLIT_STIMULUS_FALLBACK_IMAGES` — optional JSON object mapping activity title to a custom fallback image URL, overriding the bundled images without code changes (e.g. `{"CAT Practice — 2D & 3D Composition Analysis": "/static/images/my-image.svg"}`)
- `FABLIT_WIKIMEDIA_ENDPOINT` — Wikimedia Commons API endpoint (default `https://commons.wikimedia.org/w/api.php`)
- `FABLIT_WIKIMEDIA_TIMEOUT` — retrieval timeout in seconds (default `10.0`)
- `FABLIT_WIKIMEDIA_WIDTH` — requested thumbnail width (default `1200`)
- `FABLIT_WIKIMEDIA_LIMIT` — candidate images searched (default `5`)
- `FABLIT_PRACTICE_HISTORY_REPOSITORY` — practice history persistence (SPEC-021): `memory` (in-memory, for tests and local development), `datastore` (Google Cloud Datastore, for the deployed App Engine environment), or unset (history persistence disabled; the `/history` surface shows an empty state)
- `FABLIT_ARTIFACT_STORAGE_BACKEND` — private sketchbook artifact storage (SPEC-034): `file` (default; file-backed private storage for local development and tests) or `gcs` (Google Cloud Storage for deployed App Engine environment)
- `FABLIT_ARTIFACT_STORAGE_BUCKET` — GCS bucket name for private sketchbook artifacts (required when `FABLIT_ARTIFACT_STORAGE_BACKEND=gcs`)
- `FABLIT_ARTIFACT_STORAGE_DIR` — optional filesystem directory for file-backed storage (when backend is `file`)
- `FABLIT_AUTHORING_SECRET` — shared secret for internal AI authoring access (SEC-001). When unset, internal authoring routes reject all requests by default
- `FABLIT_AUTHORING_CANDIDATE_STORE` — shared candidate store for internal authoring (FIX-7): `memory` (default; in-memory for tests and local development) or `datastore` (Google Cloud Datastore for multi-instance production)
- `FABLIT_AUTHORING_CANDIDATE_RETENTION_DAYS` — candidate retention window in days for unapproved authoring drafts (default `30`)
- `FABLIT_PUBLISHED_PRACTICE_STORE` — published practice store for the learner library (SPEC-035): `memory` (default; in-memory for tests and local development) or `datastore` (Google Cloud Datastore for multi-instance production)
- `FABLIT_AI_PROVIDER_API_KEY` — optional server-side API key for the AI practice authoring provider (SPEC-032 / SEC-001). Kept strictly server-side and never exposed to learners or browsers
- `FABLIT_AI_PROVIDER_MODEL` — model identifier for the AI practice authoring provider (default `gemini-2.5-flash`), retained as authoring provenance. Only used when `FABLIT_AI_PROVIDER_API_KEY` is configured
- `FABLIT_NEWS_REPOSITORY` — curated news persistence (SPEC-041): `memory` (default; in-memory for tests and local development) or `datastore` (Google Cloud Datastore for multi-instance production)
- `FABLIT_STORY_RESPONSE_REPOSITORY` — private story-response persistence (SPEC-044): `memory` (default; in-memory for tests and local development) or `datastore` (Google Cloud Datastore for multi-instance production)
- `FABLIT_GENERATED_PRACTICE_REPOSITORY` — private requested-practice persistence (SPEC-044): `memory` (default; in-memory for tests and local development) or `datastore` (Google Cloud Datastore for multi-instance production). Learner requests and their generation also need `FABLIT_AI_PROVIDER_API_KEY`; without it the composer explains that requests are unavailable
- `FABLIT_NEWS_SOURCES` — JSON allowlist of approved news sources (SPEC-041), for example `[{"name": "The Guardian — Fashion", "feed_url": "https://www.theguardian.com/fashion/rss", "site_url": "https://www.theguardian.com"}]`. Defaults to The Guardian's Fashion and Art & Design feeds; an empty list disables fetching
- `FABLIT_NEWS_MAX_ITEMS_PER_SOURCE` — maximum stories considered per source in one refresh (default `6`)
- `FABLIT_NEWS_FRESHNESS_DAYS` — oldest eligible publication date in days (default `14`)
- `FABLIT_NEWS_MAX_SUMMARY_CHARS` — longest accepted curated summary (default `600`)
- `FABLIT_NEWS_RELEVANCE_THRESHOLD` — minimum provider relevance score, 0–1 (default `0.5`)
- `FABLIT_NEWS_MAX_SOURCES_PER_TASK` — approved sources processed by one durable curation task unit (default `2`; a larger batch is checkpointed and continued)
- `FABLIT_NEWS_TASK_DISPATCH` — durable dispatch for curation jobs: `inline` (default; local development and tests, not durable) or `cloud_tasks` (managed production dispatch)
- `FABLIT_NEWS_TASK_QUEUE` — full Cloud Tasks queue resource name used when `FABLIT_NEWS_TASK_DISPATCH=cloud_tasks`
- `FABLIT_NEWS_TASK_HANDLER_URL` — absolute HTTPS URL of this application's `/tasks/news-curation` handler
- `FABLIT_NEWS_TASK_SERVICE_ACCOUNT` — service account that signs task requests and is the only accepted task identity
- `FABLIT_NEWS_TASK_AUDIENCE` — optional expected OIDC audience when it differs from the handler URL
- `FABLIT_NEWS_FETCH_TIMEOUT` — per-source fetch timeout in seconds (default `10.0`)
- `FABLIT_NEWS_MAX_RESPONSE_BYTES` — maximum feed response size (default `512000`)

Every anonymous learner receives a unique, opaque learner identity stored in a secure, HttpOnly cookie (SPEC-024): practice history is private to that learner's browser, with no registration, email, or password. The identity cookie carries the `Secure` attribute in production and a one-year lifetime; clearing cookies simply starts a fresh anonymous learner.

The `FABLIT_WIKIMEDIA_*` settings only take effect with `FABLIT_STIMULUS_PROVIDER=wikimedia`. With `FABLIT_PRACTICE_HISTORY_REPOSITORY=datastore` and `FABLIT_ARTIFACT_STORAGE_BACKEND=gcs`, the application uses the standard Google Cloud authentication mechanism available to App Engine (application-default credentials) — no credentials are hard-coded or stored in source. No Datastore indexes are required for the scoped history queries.

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
- `Feedback` — learner-facing guidance derived from an Evaluation, with stable identity, an Evaluation reference, a general learner-facing content field, and a timezone-aware creation timestamp; immutable after creation and free of scoring, Reflection, generation-mechanism, and persistence concerns. SPEC-030 defines the content boundary for useful practice feedback: grounded strengths, specific improvement guidance, actionable next steps, and a meaningful handoff into Reflection without labelling the learner or introducing hidden scoring
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
- `PracticeCompletion` (SPEC-018) — an application-level record written after successful reflection, retaining learner, activity, reflection, and completion time; dashboard cards acknowledge previously practised activities while repeated practice remains available. It does not calculate Progress, mastery, scores, streaks, or recommendations.
- Demo content: 12 practice activities across the Visual Analysis, Written Communication, and Critical Observation Skills (SPEC-023); seven image-dependent activities present a bundled visual stimulus, and "CAT Practice — 2D & 3D Composition Analysis" is the SPEC-015 reference activity (§56–58). Activity titles use exam-oriented labels for the initial design-aspirant pilot ([issue #65](https://github.com/h3xh4wk/fablit/issues/65)); the underlying Skill and Assessment Activity model stays exam-neutral. Each web request resolves a unique anonymous learner identity per browser (SPEC-024), so practice history stays private to that learner
- Practice history port (SPEC-021) — `PracticeHistoryRepository`, a deliberately narrow persistence boundary for learner practice history, with `InMemoryPracticeHistoryRepository` (tests/local development) and `DatastorePracticeHistoryRepository` (production Datastore adapter, isolated in `fablit.platform`) as interchangeable implementations; completed practice is persisted when the completion flow succeeds regardless of whether an optional reflection is saved or skipped, completion identity is stable (idempotent retries), a reflection may be attached later to an existing completion, and history/review view models (`PracticeHistoryView`, `PracticeReviewView`) keep persistence concerns out of the domain
- Learner identity boundary (SPEC-024) — `fablit/platform/learner_identity.py` provides the opaque identity and secure cookie primitives, and `app/learner_session.py` centralises per-request identity resolution and learner-scoped application wiring; the fixed demo learner identity is no longer used for normal web traffic, and two anonymous learners never share history
- Practice transition configuration (SPEC-025) — `fablit/application/practice_continuity.py` holds the authored source → target transition table (title-keyed, resolved to stable activity identities) and the `ContinuationView` view model surfaces it on completion; the continuation resolves from the completed activity alone and never from learner state
- Pre-practice intention (SPEC-026) — an optional, qualitative focus statement captured before the active workspace (`get_intention`/`set_intention`), held as pending journey state in `LearnerJourneyStore`, attached to the session's `Submission` (`pre_practice_intention`) at response time, persisted with history, and rendered in review; it is never graded or consumed by evaluation
- Story-linked responses (SPEC-044) — `fablit/domain/story_response.py` models a private answer to a Pulse story's "What to try" prompt with its story identity, headline, source, canonical URL, prompt, text, and save time; `fablit/application/story_responses.py` validates and bounds the text, derives a retry-safe identity from the composer token, and saves through `StoryResponseRepository` (`InMemoryStoryResponseRepository` locally, `fablit/platform/datastore_story_response_repository.py` in production). Saving never calls an AI provider, evaluates the response, or creates a practice completion; the learner can revisit it from private history
- Session recovery layer (SPEC-028) — `app/static/js/session-recovery.js`, a client-only static module that auto-saves the active response, intention, and reflection drafts to browser storage (IndexedDB primary, `localStorage` fallback) on a 3-second debounce or blur, offers a quiet Resume/Discard banner for uncommitted response drafts, purges drafts after successful submission and after 24 hours, and degrades gracefully when storage is unavailable; drafts never reach the server
- Private sketchbook artifact storage (SPEC-033 / SPEC-034) — `fablit/application/artifact_storage.py` isolates sketchbook reflection image binaries from history records behind the `ArtifactStorage` port; implemented via `FileArtifactStorage` (local dev/test) and `GCSArtifactStorage` (Google Cloud Storage adapter in `fablit/platform/gcs_artifact_storage.py` for App Engine). Practice reviews reference artifacts by opaque ID, and missing objects degrade gracefully with an unlisted 404 while leaving written practice history intact.
- Structured authoring brief and candidate provenance (FIX-6 / issue #129) — required brief fields are validated before generation; optional context, creative-thinking lens, constraints, stimulus requirements, and continuation intent may be omitted. Generated candidate mappings remain untrusted, retain the brief and provider/model/UTC-time provenance, and are stored in process memory.
- LLM provider adapter boundary (ARCH-001 / issue #123) — the authoring workflow depends on a provider-neutral LLM port (`fablit/application/authoring_llm.py`), not a specific vendor SDK. The initial concrete adapter (`fablit/platform/gemini_authoring_provider.py`) implements it against Google Gemini: credentials, request construction, response parsing, provider/model provenance, and provider failures stay inside that server-side boundary. Tests use a deterministic fake provider and an injectable transport, so the suite makes no live API calls.
- AI-assisted authoring brief creation (SPEC-040) — an authorised author with only rough notes, pasted source text, or a short topic can draft the existing brief fields at `POST /authoring/brief/draft` (SEC-001 protected). Drafted values are rendered into the same editable form with visible provenance (notes-grounded, AI suggestion, or assumption to confirm); examination context is always an assumption to confirm. A single-field regeneration preserves every other value, a whole-brief draft only fills empty fields unless replacement is explicitly chosen, and provider, malformed-output, or validation failures keep the notes and edits retryable. Drafting never creates, approves, or publishes a candidate.
- Candidate validation against SPEC-029 and SPEC-030 (FIX-4 / issue #127) — deterministic validation checks generated candidate output against the 8 required dimensions of the SPEC-029 `PracticeContentContract` and SPEC-030 feedback quality rules (forbidding scores, grades, mastery, rank, and ability language); unvalidated candidates cannot be approved.
- Real authoring candidate review and approval lifecycle (FIX-5 / issue #128) — internal authoring candidate store manages review state transitions (`pending`, `approved`, `rejected`), maintains revision history across candidate and contract edits with automatic re-validation, rejects unvalidated candidate approvals with HTTP 422, and isolates approved practices from the learner library.
- Shared candidate state for production authoring (FIX-7 / issue #132) — `fablit/platform/datastore_authoring_store.py` provides `DatastoreAuthoringCandidateStore` persisting active candidates, revisions, and approval outcomes across instances in the `authoring` Datastore namespace. Candidates follow a 30-day retention lifetime policy while preserving approved content indefinitely. Storage failures fail safe with HTTP 503 rather than false success, and learner routes remain completely decoupled.
- Publication to the learner library (SPEC-035 / issue #135) — `fablit/application/publishing.py` defines the explicit publication boundary: `publish_candidate(...)` revalidates content and approval state, converts the approved candidate into the existing `DemoActivity`/`AssessmentActivity` representation with internal provenance (source candidate, approved revision, publish/withdraw times), and writes it through the `PublishedPracticeStore` port (`InMemoryPublishedPracticeStore` locally, `fablit/platform/datastore_published_store.py` for Datastore). Publishing is idempotent per approved revision and replaces content in place under one stable activity identity; `POST /authoring/candidates/{id}/publish` and `/withdraw` (SEC-001) are the only transitions, and `LearnerApplicationRegistry` reconciles the published set into each learner application's dashboard, Full Practice eligibility, and evaluator map on the next request.

The learner experience introduces no learner authentication, scoring, Progress, mastery, recommendations, gamification, or examination-specific logic.

## Practice content contract (SPEC-029)

The repository treats the practice contract as explicit, authored content metadata, not as hidden application logic. Each of the twelve curated practices carries its own written purpose, task, expected thinking, response contract, evaluation intent, feedback intent, reflection intent, and continuation intent in the application content model (`fablit/application/demo_data.py`; contract type in `fablit/application/store.py`) — authored against that practice's actual task and thinking demand rather than derived generically from its title, description, or prompt. A generic derivation (`PracticeContentContract.from_activity`) survives only as the documented fallback for definitions that author no contract: an authored contract is never overwritten, and blank contract fields are rejected at construction (`InvalidContentContractError`). Tests guard specificity directly — every curated field must be populated, must differ from generic derivation output for its own and every other practice, must differ across practices, and must carry no scoring, mastery, or streak language. The content remains intentionally platform-neutral and learner-facing copy stays unchanged: the internal Observe / Interpret / Ideate / Articulate / Reflect lens is retained as a review aid only and is never exposed as progress, scoring, or recommendation data. The authored contract is the quality boundary SPEC-032 AI-assisted authoring validates candidates against.

## Practice modes (SPEC-022)

Learners can explicitly choose the shape of practice that fits the moment at `/practice`: **A short drill** (about 5–10 minutes of learner effort — an indication, never a countdown or limit) or **A full practice** (the existing standard experience). The choice is optional: the Explore dashboard remains the primary, ungated path, and a learner who ignores the chooser loses nothing.

- **Application boundary only:** practice modes live in `fablit/application/practice_modes.py` and the view models — they are deliberately outside the domain model and introduce no new Assessment Activity type, submission workflow, scoring, progress, or personalization semantics.
- **Curated eligibility:** Short Drill activities come from explicit content configuration (`SHORT_DRILL_ACTIVITY_TITLES` in `fablit/application/demo_data.py` — six concise activities spanning observation, writing, ideation, and reflection), resolved to stable activity identities; new activities become drill-eligible by editing the list, not application logic. Full Practice resolves the whole existing library.
- **Explicit choice, no hidden selection:** the learner's selection is authoritative for the current practice entry; no mode is ever recommended, ranked, or pre-selected from history or behaviour.
- **Journey and history unchanged:** either choice starts the existing Activity → Submission → Evaluation → Feedback → Reflection → Completion journey, and a completed Short Drill is simply completed practice, recorded and reviewable through the SPEC-021 history.

## Practice library (SPEC-023)

The activity library is meaningfully expanded — twelve curated activities covering observation, interpretation, ideation, articulation, and reflection — so repeated deliberate practice is plausible while content quality stays reviewable.

- **Content, not architecture:** new activities are content configuration in `fablit/application/demo_data.py`; they enter the unchanged learner journey with no new activity type, no application branches, and no parallel workflow.
- **Capability lens (internal):** each activity carries one primary practice capability (plus optional secondaries) on the internal Observe / Interpret / Ideate / Articulate / Reflect lens — a content-design review aid that is never learner-visible and never drives selection or recommendations.
- **Meaningful variety:** activities vary across stimulus (photograph composition, object detail, colour mood, object study, street scene, abstract arrangement, text-first), thinking task, response style, and context; every stimulus activity keeps a deterministic bundled fallback.
- **Short Drill grows through configuration:** the curated drill set is now six activities (observation, writing, ideation, articulation, reflection) chosen for capability variety — still explicit configuration, never history-based.
- **Inventory and gaps:** the full activity inventory, capability coverage, and documented remaining gaps live in `docs/product/practice_coverage.md`.

## Curated practice continuity (SPEC-025)

After completing a practice, the learner may see a quiet continuation: one authored next practice, with the relationship between the two activities made visible — **Observe → Interpret → Ideate → Articulate → Reflect → practise again**.

- **Connect practices, not learners:** transitions are authored content configuration (`_AUTHORED_TRANSITIONS` in `fablit/application/practice_continuity.py`), checked against the actual activity content so each demonstrates meaningful movement between capabilities. Seven of the twelve activities carry an initial transition.
- **Deterministic and learner-independent:** the continuation resolves from the completed activity's identity alone — never history, scores, completion counts, or behaviour — so every learner completing the same activity sees the same continuation.
- **An invitation, never a forced step:** the completion page presents the relationship calmly and editorially, with no recommendation, ranking, or pressure language; Explore and History navigation are unchanged, and starting the next practice runs the existing journey into the SPEC-021 history.

## Session resilience and local practice recovery (SPEC-028)

An accidental reload or closed tab no longer loses work in progress — uncommitted drafts survive entirely on the learner's device.

- **Client-only by design:** drafts live in the browser (IndexedDB primary, `localStorage` fallback); no auto-save request is ever sent to the server, and the Python application is unaware of the layer.
- **Quiet recovery:** returning to an activity with an uncommitted response draft shows an understated banner with **Resume Draft** and **Discard Draft**; intention and reflection drafts restore quietly on their own pages. Recovery is always an offer, never a gate.
- **Self-cleaning:** a successful submission removes the draft key immediately, and drafts older than 24 hours are purged on launch. If storage is disabled or quota is exceeded, standard uninterrupted practice continues.
- **No pressure, no scores:** the recovery copy describes what was saved on the device — no urgency, streak, or progress language, and drafts are never analysed or scored.

## Metacognitive practice and reflection (SPEC-026)

The learning loop is continuous: **set intent → practise → receive evaluation feedback → reflect → review the whole artifact**.

- **Optional pre-practice intention:** after selecting an activity (from Explore or a curated continuation), the learner may state a focus or skip; the prompt is an invitation, never a gate. A captured intention is echoed in the workspace, attached to the session's Submission, and shown in review before the response.
- **Optional structured reflection:** the feedback page carries two qualitative prompts (strategy assessment and gap analysis) immediately after the evaluation rendering with Save and Skip controls. A skipped or blank reflection completes the practice — skipping never blocks completion; durable history is created regardless of whether reflection is saved or skipped (SPEC-021, SPEC-159), and a reflection may be attached later to an existing completion.
- **Whole-artifact review:** the SPEC-021 review renders intention, response, evaluation feedback, and reflection in chronological order. Records stored before SPEC-026 remain readable (backward-compatible deserialization).
- **Qualitative by design:** no metric, mastery level, or completion signal is derived from intention or reflection text, and no automated feedback is produced on it.

## Persistent practice history (SPEC-021)

Completed practice is durable: when the practice completion flow succeeds (with or without a reflection), the completion and its available journey evidence (activity, stimulus, response, evaluation, feedback, reflection if present, completion time) are persisted through the practice-history repository, so a completed practice remains reviewable after an application instance restarts or is redeployed.

- **Completion boundary unchanged (SPEC-018):** a submitted or evaluated response alone never creates history; persistence happens only after the existing successful reflection/completion flow, and a failed write raises an explicit `PersistenceError` rather than falsely reporting completion. The reflection ID is the stable completion identity, so a retried write never duplicates history.
- **Repeated practice:** completing the same activity again creates a separate, independently reviewable history record; `activity_id` is never treated as the history identity.
- **Stable stimulus context:** a review shows the stimulus that was originally resolved for that attempt (SPEC-015 semantics), never a newly resolved one.
- **Production backend:** Google Cloud Datastore (`FABLIT_PRACTICE_HISTORY_REPOSITORY=datastore`), using per-learner key namespaces so learner context stays explicit for future ownership work. Records are stored under the `PracticeCompletion` kind; no Datastore indexes are required for the scoped queries. `google-cloud-datastore` is an optional dependency extra (`pip install fablit[datastore]` / `uv sync --extra datastore`) so ordinary unit tests never require Google Cloud credentials.
- **Local development and tests:** `FABLIT_PRACTICE_HISTORY_REPOSITORY=memory` (or unset) keeps the journey fully functional with the in-memory repository; the Datastore adapter is unit-tested against a lightweight fake client, so the test suite never needs a live emulator or credentials.
- **Learner surface:** "Your practice" (`/history`) answers *What have I practised recently?* with newest-first entries and a calm empty state pointing back to Explore; a review page answers *What did I do, what feedback did I receive, and what did I learn from it?* No scores, percentages, mastery labels, streaks, rankings, or recommendations are introduced.

## Private sketchbook artifact storage

Sketchbook reflection images are private learner media, not practice-history evidence. Since the sketchbook reflection practice added optional sketch upload, their binary payload is deliberately kept **outside** the practice-history record:

- **History keeps metadata only:** a completion stores an artifact *reference* (artifact id, learner id, activity id, filename, content type, size, created-at) — never the image bytes. The Datastore adapter serializes exactly those fields, so a `PracticeCompletion` entity can never grow by the 5 MB upload limit.
- **Storage boundary:** `ArtifactStorage` (`fablit/application/artifact_storage.py`) isolates the bytes. The current deployment uses `FileArtifactStorage`, a deployment-private, file-backed store keyed by the opaque artifact id; the directory is created lazily and is selected with `FABLIT_ARTIFACT_STORAGE_DIR` (or the `artifact_storage_dir` setting). Unset falls back to a process-private directory under the system temp location, so local development and tests work without a writable `/private` mount. No new dependency or GCP service is introduced.
- **Ownership and access control:** retrieval stays behind the existing learner-scoped route `/history/{completion_id}/artifact`. The application resolves the artifact reference only through the requesting learner's own completion (the SPEC-024 anonymous identity plus per-learner history), then reads the bytes from the private store. There are no public or direct media URLs; a missing reference, missing bytes, and another learner's completion all return the same unlisted `404`.
- **Validation unchanged:** PNG/JPEG/WebP and the 5 MB limit are still enforced at upload time, and non-sketchbook practices are unaffected.
- **Existing records:** records written before this change stored the bytes inline. They still load (the embedded payload is ignored), but no automated migration is performed — those legacy bytes are no longer retrievable through the review, and a review renders normally when an artifact's bytes are missing.

## Publishing approved candidates (SPEC-035)

Approval and publication are two separate human decisions, and the platform keeps them separate:

- **Approved** means an internal author accepted the candidate's content quality in the SPEC-032 review workflow. Approval alone never makes content visible to learners.
- **Published** means that approved content has been deliberately added to the learner-facing curated library through `POST /authoring/candidates/{id}/publish` (protected by SEC-001 like every authoring action).

The publication boundary (`fablit/application/publishing.py`) revalidates the SPEC-029/SPEC-030 contract and the approval state before anything is written, so generated, invalid, rejected, and edited-but-not-reapproved candidates can never be published (HTTP 422 for content problems, HTTP 409 for invalid state transitions, HTTP 503 when storage fails). The published record reuses the existing learner-facing activity representation — no parallel practice model — and keeps its provenance (source candidate, approved revision, publication time) internal.

Publication behaviour:

- **Idempotent:** repeating the same publish request returns the same publication; no duplicate catalogue entries.
- **Stable identity:** republishing a re-approved revision replaces the content in place under the same activity identity, so completed history keeps pointing at the same practice.
- **Withdrawal:** `POST /authoring/candidates/{id}/withdraw` removes the practice from the dashboard and Full Practice mode while completed history stays readable; an explicit republish restores it.
- **Independent of authoring availability:** learners never read the authoring store, and an unavailable publication store degrades to the seeded library instead of failing learner practice.

To verify a published practice end to end: set `FABLIT_AUTHORING_SECRET`, generate a candidate at `/authoring`, approve it, confirm it is absent from `/`, publish it, confirm it appears on `/` and under `/practice/full-practice`, then complete it through the ordinary intention → practice → feedback → reflection → completion flow and find it in `/history`. The same run is covered by `tests/web/test_authoring_publish.py` and makes no live AI or cloud calls.

## Fashion & Design Pulse (SPEC-041)

A small, curated feed of current fashion, textiles, sustainability, Indian craft, design, and visual-culture stories for all learners. It is separate from practice authoring and publication: its own application workflow, provider-neutral news-curation port, and news-specific persistence boundary.

- **On demand, never scheduled:** an authorised operator opens `/authoring/pulse` (behind SEC-001) and selects **Curate this week's news**. There is no GitHub Actions schedule or scheduled refresh.
- **Durable, not browser-bound:** starting curation persists a job and dispatches it as a managed task, so accepted work continues after the author leaves, refreshes, or closes the browser. Status, progress, counters, and the final report are shared across instances and survive a restart; a second start is refused while a job is active, duplicate task delivery is a no-op, and an interrupted worker is recovered safely.
- **Automatic publication after checks:** each candidate must pass source allowlisting, safe HTTP(S) link handling, bounded retrieval, freshness, deduplication, schema validation, relevance, grounding, and controlled-category checks. There is no per-story approval step; invalid or failed candidates never reach learners.
- **Accurate batch reporting:** fetched, already-known (deduplicated), published, rejected, and failed counts, with safe reasons for rejected/failed items and per-source failures. Raw provider payloads and secrets are never shown.
- **Learner browsing is independent of AI:** `/pulse` reads only persisted stories, shows imagery when one was persisted, attribution, canonical links, dates when reliable, summaries, categories, educational relevance, and optional reflection prompts, with lightweight category filtering and a calm empty/unavailable state. A failed or empty refresh never clears the feed.
- **Illustrative imagery, credited separately:** a story may carry one optional stock photograph selected during curation from the existing Pexafy image search (the same provider-neutral port and configuration as practice authoring). Search and selection run only inside curation, never on a page request; a provider failure, empty result, or weak match leaves the story text-only. The image is stored with its provenance and shown with a distinct “Illustrative image” credit, so generic stock imagery is never presented as evidence of a specific collection, designer, event, or product.
- **Respectful reuse:** only the minimal curation data is stored — no full articles, large excerpts, or publisher photographs.
- **Configuration and operation:** see [docs/engineering/curated-news-feed.md](docs/engineering/curated-news-feed.md) for the source allowlist, server-side Gemini configuration, Datastore setup, and batch interpretation.

## Story responses (SPEC-044)

Every Pulse story that offers a "What to try" prompt also offers a quiet **Try this** action. Opening it reveals a short private composer on the story card itself, so the learner can respond without leaving the story's context.

- **Private capture, not assessment:** saving a response records the learner's words with the originating story identity, headline, source, canonical URL, prompt, and save time. It never invokes an AI provider, never evaluates or grades the response, and never creates a practice completion.
- **Bounded and retry-safe:** the response is trimmed and limited to 2,000 characters; empty or over-long input is refused with actionable copy and the learner's draft stays in the form. A hidden idempotency token makes a retried submission resolve to the same record rather than a duplicate.
- **Owned by the current learner:** listing, retrieval, and the history display are scoped by the anonymous learner identity. Another learner's response is indistinguishable from one that does not exist, and the confirmation after saving is derived from the learner's own record.
- **Return path:** saved responses appear in `/history` under **Story responses**, visually separate from completed practice, and each links to a review page with the story, prompt, learner's words, source attribution, and original-story link.
- **Honest failure:** a persistence failure reports that the response was not saved, keeps the learner's words on the page, and leaves the rest of the Pulse and practice history usable.

Persistence defaults to in-memory for tests and local development; production sets `FABLIT_STORY_RESPONSE_REPOSITORY=datastore`, which stores responses in their own kind (`StoryResponse`) and namespace (`story-responses`).

## Requesting a practice (SPEC-044)

A learner who wants something more specific than the curated library can ask for it: `/practice/request` offers a short composer for what they want to practise, an area, a response form, an optional challenge preference, and an optional examination context they state themselves.

A Pulse story that carries a "What to try" prompt also offers **Make this a practice**, which opens the composer with that story's prompt as editable starter text and a link back to the story, so the learner can add their own intent or replace it.

- **Explicit, bounded requests:** nothing is generated until the learner submits; the request is trimmed and limited to 600 characters, choices are validated against supported values, and invalid input comes back with plain-language copy and the learner's words intact.
- **Validated before it is offered:** generation runs through a provider-neutral port, and the untrusted output must pass the existing practice content contract and feedback language validation. Invalid output never reaches the learner and is never persisted.
- **Private, and never the shared library:** a requested practice is stored under the learner's own opaque identity, never enters the shared library, learner discovery, or practice-mode selections, and is never visible to another learner. Its brief is shown first, so the learner decides whether to begin.
- **Minimal context, opt-in:** if the learner leaves "Use my recent practice as context" on, generation receives up to five of their own completed practice titles and areas — nothing else, no responses, reflections, artifacts, or identity. Turning it off sends no history at all.
- **Ordinary practice afterwards:** practising a requested practice runs the unchanged intention → practice → feedback → reflection → completion flow, and the result is ordinary practice history. Nothing is scored, graded, ranked, or described as mastery.
- **Honest failure:** generation or persistence failures say plainly that no practice was made, keep the learner's request on the page, and leave the practices already requested available.

Persistence defaults to in-memory for tests and local development; production sets `FABLIT_GENERATED_PRACTICE_REPOSITORY=datastore`, which stores practices in their own kind (`GeneratedPractice`) and namespace (`learner-practices`). Requests need a server-side `FABLIT_AI_PROVIDER_API_KEY`; without one the composer says requests are temporarily unavailable instead of inventing content.

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

Playwright is included in the development toolchain for browser-level checks. The browser journey test (`tests/e2e`) drives the full learner flow — including the SPEC-026 intention prompt, the SPEC-015 visual stimulus, response-aware feedback with the structured reflection panel, and the skip path — and `test_session_recovery.py` drives the SPEC-028 draft recovery lifecycle (auto-save, reload, resume/discard, clear-on-submit) against real browser storage, in Chromium, but they are **skipped in the local environment by default**: they only run when `RUN_BROWSER_TESTS=1` is set, and the CI workflow runs them in a dedicated browser job (`uv run playwright install --with-deps chromium`). Normal local runs (`make check`, `pytest`) stay green without any browser installed.

Because many local environments have constraints (no Playwright browser download, no display, or sandbox restrictions — root containers in particular), browser tests are not supported locally: keep them skipped and let the CI browser job cover them. Only opt in locally when a compatible browser is genuinely available:

```bash
uv run playwright install chromium
make e2e
```

If you have an existing Chromium/Chrome binary instead of a Playwright download, point Playwright at it with `PLAYWRIGHT_EXECUTABLE_PATH` (root containers may also need `PLAYWRIGHT_NO_SANDBOX=1`).

## PythonAnywhere deployment

The ASGI application object is available at `app.main:app`. The SPEC-014 pilot runs on PythonAnywhere (see [ADR-008](docs/adr/ADR-008-pythonanywhere-deployment.md)); follow [docs/engineering/deployment.md](docs/engineering/deployment.md) for the complete, reproducible deployment process.
