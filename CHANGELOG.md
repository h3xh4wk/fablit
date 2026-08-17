# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **SPEC-015 — Contextual Visual Stimulus & Response-Aware Evaluation**: the visual stimulus becomes part of the learner's activity instance, and evaluation responds to what the learner actually wrote.
  - Domain: `ActivityStimulusContext` (learning focus, stimulus context, retrieval query) on `AssessmentActivity`, and `StimulusInstance` (provider, asset ID, image URL, source URL, creator, license, attribution, alt text, timezone-aware retrieval timestamp) — both immutable and free of HTTP/provider/network dependencies; `EvaluationFinding` gains an optional `evidence` field grounding a Finding in the learner's response.
  - Application: `StimulusProvider` abstraction (§9) with a deterministic built-in provider (bundled images, the default), a `WikimediaCommonsProvider` for the approved external source (§8, §10), and a `ResilientStimulusProvider` that falls back to the built-in stimulus when external retrieval fails (§21–22). The Wikimedia provider sends the descriptive User-Agent Wikimedia requires, restricts search to bitmap images, and filters responses to image mime types so documents never become a stimulus; `DemoEvaluator` is now response-aware — matched concepts produce response-specific Findings with evidence, and empty/very short responses are handled without fabricating positives (§62–63, §69).
  - Web/UI: the resolved image is presented on the practice page before the observation prompt with meaningful alt text and a compact source/attribution treatment (§24–26); responsive, non-overflowing presentation in `app/static/css/fablit.css`.
  - Reference activity: "Visual Analysis — Composition" (plus the Observation and Colour & Mood activities) now displays a bundled visual stimulus and produces response-aware feedback (§56–58).
  - Historical integrity: the journey store retains the stimulus with the activity instance and never silently replaces it (§18, §48); the same stimulus is reused within an instance, a new one is resolved for a new instance (§19).
  - Configuration: `FABLIT_STIMULUS_PROVIDER` (`builtin` default / `wikimedia`) drives provider selection; the default experience and tests never depend on a live external provider (§67). The bundled fallback images are overridable per activity via `FABLIT_STIMULUS_FALLBACK_IMAGES` (JSON map of activity title to image URL), and the Wikimedia provider is tunable via `FABLIT_WIKIMEDIA_ENDPOINT`, `FABLIT_WIKIMEDIA_TIMEOUT`, `FABLIT_WIKIMEDIA_WIDTH`, and `FABLIT_WIKIMEDIA_LIMIT`.
  - Tests: domain unit tests (100% `fablit.domain` coverage), provider tests with an injectable fetch, response-specific acceptance tests, historical-reference tests, web/route tests, and an updated browser journey that verifies the learner sees the image and receives response-aware feedback (§66–71).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-015](specifications/platform/SPEC-015-contextual-visual-stimulus.md) for details.

- **SPEC-014 — Learner Pilot Deployment**: operational boundary around the existing SPEC-013 learner experience so a small group of real learners can use Fablit safely and reliably — no new learning capability and no new domain concept.
  - `create_app(config)` application factory so environment-specific safety settings can be applied and tested; the module-level `app` remains available as `app.main:app`.
  - Learner-facing error handling: unhandled errors now render a simple error page (`Something went wrong.`) with no stack traces, file paths, environment variables, or framework debugging pages; the full exception is logged server-side for investigation.
  - Development-only interfaces (Swagger UI, ReDoc, OpenAPI schema) are disabled in the `production` environment; `FABLIT_DEBUG` now drives FastAPI debug mode.
  - Deployment guide (`docs/engineering/deployment.md`) covering the PythonAnywhere target, required runtime, environment variables, build/install, startup command, persistence behaviour, health check, log access, restart procedure, rollback, safety boundary, verification, and known pilot limitations.
  - Pilot operations docs (`docs/pilot/`): learner instructions (the single-line invitation), a lightweight structured feedback-recording template, and the evidence-driven loop.
  - Persistence explicitly verified as acceptable for the pilot: the in-memory `LearnerJourneyStore` is documented (what/where/how long/restart behaviour); no persistence upgrade introduced.
  - Web/route tests for the deployment boundary (`tests/web/test_deployment.py`); all existing automated suites continue to pass.

See [SPEC-014](specifications/platform/SPEC-014-learner-pilot-deployment.md) for details.

- **SPEC-013 — Learner Experience & Visual Foundation**: first coherent learner experience and visual foundation around the SPEC-012 journey, implemented entirely in the Web/UI layer — the domain models and the SPEC-012 Application Layer are unchanged.
  - Dashboard redesigned as an invitation to learn: activity cards present title → invitation → relevant Skill → action (`Try it`), with no internal identifiers or technical metadata visible.
  - Practice page is visually quieter than the dashboard, with the prompt strongly emphasized and a comfortable, clearly labelled response area; existing validation behaviour retained.
  - Feedback presented conversationally (`A little feedback` / `What you noticed` / `What to think about` / `Try this next` / `Reflect`), translating structured Findings into learner-friendly language with no score/grade/pass/fail terminology.
  - Reflection reads as a natural continuation of feedback with the purposeful SPEC-012 prompt retained.
  - Completion is a quiet acknowledgement (`That's one done.`) with a clear route back to practice — no victory, defeat, ranking, or score.
  - Minimum design-system foundation and centralized design tokens (typography, spacing, colours, border radius, shadows, transitions, container widths) in `app/static/css/fablit.css`.
  - Responsive behaviour for mobile, tablet, and desktop (mobile-first card stacking); accessibility improvements including a skip link, labelled form controls, single-h1 document hierarchy, visible focus states, and reduced-motion support.
  - Core journey preserved end to end and still usable without JavaScript; HTMX remains progressive enhancement.
  - Web/route, bootstrap, and opt-in browser tests updated and extended (mobile viewport journey, keyboard navigation); all domain and application tests continue to pass.
  - Documentation updates to the Architecture Blueprint and README.

See [SPEC-013](specifications/platform/SPEC-013-learner-experience-and-visual-foundation.md) for details.

- **SPEC-012 — Learner Practice Application Flow**: first user-facing vertical slice of Fablit, establishing the first Application Layer (`fablit.application`) between the Web/UI and the existing learning domain.
  - `PracticeApplication` use-case facade implementing UC-001–UC-007: dashboard retrieval, start practice, submit response, demo evaluation, feedback presentation, reflection, and completion.
  - Learner-facing view models (`PracticeDashboardView`, `PracticeActivityView`, `FeedbackView`, `ReflectionView`, `CompletionView`) that keep presentation concerns out of domain objects.
  - Deterministic `DemoEvaluator` producing a known Evaluation with at least one structured Finding per demo activity — no AI provider, network service, or asynchronous worker.
  - Minimal in-memory `LearnerJourneyStore` preserving the Submission → Evaluation → Feedback → Reflection chain for the vertical slice.
  - Demo content: 5 practice activities across the Visual Analysis, Written Communication, and Critical Observation Skills, with a stable demo learner context and no fake user-management model.
  - Server-rendered Jinja2 templates and routes in `app/main.py` (dashboard, practice, submit, feedback, reflection, completion) with HTMX progressive enhancement (vendored under `app/static/`); the core journey works without JavaScript.
  - Learner-friendly error and validation messages (`Activity not found.`, `Please enter a response before submitting.`); invalid responses never create a Submission.
  - Application-layer, web/route, and end-to-end learner journey tests; existing domain tests continue to pass.
  - Opt-in browser-level learner journey test (`tests/e2e`, Playwright) run by a dedicated CI job (`uv run playwright install --with-deps chromium`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-012](specifications/platform/SPEC-012-learner-practice-application-flow.md) for details.

- **SPEC-011 — Skill–Assessment Activity Association**: in-memory many-to-many association between `Skill` (SPEC-010) and `AssessmentActivity` (SPEC-005) under `fablit.domain`.
  - `AssessmentActivity` references zero or more Skills by stable identity (`skill_ids`), validated on construction: references must be valid identities and unique within the collection.
  - Skills and Assessment Activities remain independently valid; the association carries no relationship attributes and introduces no Progress, mastery, scoring, evaluation, curriculum, examination, or AI semantics.
  - No dedicated relationship domain entity is introduced.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-011](specifications/platform/SPEC-011-skill-assessment-activity-association.md) for details.

- **SPEC-010 — Skill Domain Foundation**: in-memory `Skill` domain model under `fablit.domain`.
  - Stable identity, a human-readable name, and a meaningful description as domain state.
  - Meaningful-content validation rejecting empty and whitespace-only names and descriptions; immutable after creation.
  - Skill remains independent of any single Assessment Activity, Evaluation criteria, Progress, mastery, scoring, hierarchy, curriculum and examination structures, and AI or external generation mechanisms.
  - Domain exception: `InvalidSkillError`.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-010](specifications/platform/SPEC-010-skill-domain-foundation.md) for details.

- **SPEC-009 — Reflection Domain Foundation**: in-memory `Reflection` domain model under `fablit.domain`.
  - Stable identity, Feedback identity reference (SPEC-008), a single general learner-authored content field, and a timezone-aware creation timestamp as domain state.
  - Meaningful-content validation rejecting empty and whitespace-only reflection; immutable after creation; creating Reflection does not modify the associated Feedback.
  - Confidence scoring, improvement goals, action plans, reflection-generation mechanisms, AI providers, Progress, and persistence are deliberately excluded from the model.
  - Domain exception: `InvalidReflectionError`.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-009](specifications/platform/SPEC-009-reflection-domain-foundation.md) for details.

- **SPEC-008 — Feedback Domain Foundation**: in-memory `Feedback` domain model under `fablit.domain`.
  - Stable identity, Evaluation identity reference (SPEC-007), a single general learner-facing content field, and a timezone-aware creation timestamp as domain state.
  - Meaningful-content validation rejecting empty and whitespace-only guidance; immutable after creation; creating Feedback does not modify the associated Evaluation.
  - Scoring, Reflection, feedback-generation mechanisms, AI providers, and persistence are deliberately excluded from the model.
  - Domain exception: `InvalidFeedbackError`.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-008](specifications/platform/SPEC-008-feedback-domain-foundation.md) for details.

- **SPEC-005 — Assessment Activity Domain Foundation**: in-memory `Assessment` and `AssessmentActivity` domain models under `fablit.domain`.
  - Stable unique identities, metadata, lifecycle status, and controlled activity types.
  - Domain validation enforcing identity, required metadata, minimum activity count, and deterministic sequential activity ordering.
  - Domain exceptions: `InvalidAssessmentError`, `InvalidActivityError`, `DuplicateActivityPositionError`.
  - Unit, composition, and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-005](specifications/platform/SPEC-005-assessment-activity-domain-foundation.md) for details.

- **SPEC-006 — Submission Domain Foundation**: in-memory `Submission` domain model under `fablit.domain`.
  - Stable identity, learner identity reference, and Assessment Activity reference (SPEC-005 identity only, without duplicating the activity).
  - Generic extensible learner response, `SubmissionStatus` lifecycle (`Draft` → `Submitted`), and timezone-aware submission timestamp as domain state.
  - Explicit `submit()` transition enforcing a non-empty response and producing an immutable Submitted Submission.
  - Domain exceptions: `InvalidSubmissionError`, `InvalidSubmissionTransitionError`.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-006](specifications/platform/SPEC-006-submission-domain-foundation.md) for details.

- **SPEC-007 — Evaluation Domain Foundation**: in-memory `Evaluation` and `EvaluationFinding` domain models under `fablit.domain`.
  - Stable identity, Submission identity reference (SPEC-006), one-or-more structured Findings with stable identities, and a timezone-aware evaluation timestamp as domain state.
  - Immutable after creation; creating an Evaluation does not modify the associated Submission.
  - Scoring, Feedback, evaluation mechanisms, AI providers, and persistence are deliberately excluded from the model.
  - Domain exceptions: `InvalidEvaluationError`, `InvalidEvaluationFindingError`.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-007](specifications/platform/SPEC-007-evaluation-domain-foundation.md) for details.
