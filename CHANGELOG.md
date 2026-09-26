# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **SPEC-026 — Metacognitive Practice & Reflection Integration**: the optional pre-practice intention and structured post-evaluation reflection are woven into the active practice journey, linking intent, practice execution, evaluation feedback, and self-assessment into one continuous learning loop.
  - Before entering a practice, the learner may state a focus (`GET/POST /activities/{id}/intention`, reachable from Explore and curated continuations): it is captured in session context, echoed quietly in the workspace and on the reflection page, attached to the session's Submission, and later rendered in the SPEC-021 review before the response. Skipping or submitting it blank is accepted gracefully and never blocks practice; direct activity entry works unchanged.
  - After evaluation feedback, the reflection panel carries the two structured qualitative prompts (strategy assessment and gap analysis) with explicit Save and Skip controls. A skipped or blank reflection completes the practice without creating a `Reflection` record; durable SPEC-021 history remains reflection-bound (PHR-001), so a skipped reflection writes no history entry, and the completion acknowledgement reflects what actually happened.
  - No scoring, mastery, analytics, or automated feedback is derived from intention or reflection text (SPEC-026 §4): reflections are qualitative learner artifacts, not assessment inputs.
  - New domain field (`Submission.pre_practice_intention`, optional), application use cases (`get_intention`, `set_intention`), and backward-compatible persistence of the intention inside the stored Submission in both the in-memory and Datastore adapters.
  - New tests across all layers: domain (intention invariants and `submit()` preservation), application (17 covering capture, attachment, retry-after-failure, skip paths, and review), web (14 covering the intention surface, reflection panel, and chronological whole-artifact review), and persistence (intention round trip and pre-SPEC-026 record compatibility).

See [SPEC-026](specifications/platform/SPEC-026-metacognitive-practice-and-reflection-integration.md) — issue [#90](https://github.com/h3xh4wk/fablit/issues/90) — for details.

- **SPEC-025 — Curated Practice Continuity**: completing a practice can now offer a deliberately curated next practice, making the movement between kinds of design thinking visible — Observe → Interpret → Ideate → Articulate → Reflect → practise again. Authored content continuity, not personalization: connect practices, not learners.
  - A quiet continuation appears on the completion page when the completed activity has an authored transition: the relationship in one or two editorial sentences ("You just observed an object closely. Now try turning that observation into a design idea."), the next practice's title, and a single calm call to action. No recommendation, ranking, pressure, or gamified language.
  - The transition table is explicit content configuration (`fablit/application/practice_continuity.py`, `_AUTHORED_TRANSITIONS`), pairing seven of the twelve library activities with a curated next practice — checked against the actual activity content so each demonstrates meaningful movement between capabilities, not a shared label. New transitions are added by editing the table, never application logic; drifted titles are skipped safely.
  - The continuation is deterministic and learner-independent: it resolves from the completed activity's identity alone — never learner history, scores, completion counts, or behaviour — so a second learner completing the same activity receives the same content transition with no shared state.
  - Following the continuation runs the unchanged Submission → Evaluation → Feedback → Reflection → Completion journey, and the target practice is recorded and reviewable through the SPEC-021 history under the learner's SPEC-024 identity. The learner can equally ignore the continuation: Explore and History navigation are unchanged.
  - New application tests (23) and web/route tests (8) cover the transition configuration, deterministic resolution, learner independence, journey and history boundaries, copy language, and the optionality of the continuation.

See [SPEC-025](specifications/platform/SPEC-025-curated-practice-continuity.md) — issue [#87](https://github.com/h3xh4wk/fablit/issues/87) — for details.

- **SPEC-024 — Learner Identity & Private Practice History**: every anonymous learner now has a distinct, opaque learner identity, so persistent practice history belongs only to that learner's browser — anonymous does not have to mean shared.
  - Each browser receives a unique, high-entropy learner identity (a random UUID) persisted as a secure cookie (`fablit_learner_id`; HttpOnly, SameSite Lax, one-year lifetime, `Secure` in production). No registration, email, password, or social login is introduced, and the identity encodes no personal information and is derived from no identifying data.
  - The web/application boundary now resolves the learner-scoped application per request (`app/learner_session.py`): the fixed `DEMO_LEARNER_ID` is no longer used for normal web traffic, journey state (submissions, feedback, reflections) is per learner, and the existing learner-scoped SPEC-021 persistence receives only the current learner's identity. Demo content, evaluator wiring, and the stimulus provider remain learner-independent and are built once.
  - Privacy isolation at the surfaces learners already use: `/history` lists only the current learner's completions, and opening another learner's completion ID behaves exactly like an unknown record — direct URL manipulation cannot cross the ownership boundary (no existence leak).
  - Identity primitives (opaque ID generation, secure cookie transport) live in `fablit/platform/learner_identity.py`; resolution is centralised in middleware rather than duplicated per route. Clearing cookies starts a fresh anonymous learner; cross-device recovery is explicitly deferred and a future sign-in mechanism would attach to the internal `learner_id`, never replace it.
  - New web tests cover the SPEC-024 §8 scenario matrix: distinct identities for fresh clients, identity persistence, submission attribution, two-learner history isolation, cross-learner review returning not-found, navigation scoping, repeated practice separation, invalid IDs, persistence-failure handling, and in-flight state isolation. Existing SPEC-021/022 journey tests pass unchanged.

See [SPEC-024](specifications/platform/SPEC-024-learner-identity-and-private-practice-history.md) — issue [#85](https://github.com/h3xh4wk/fablit/issues/85) — for details.

- **SPEC-023 — Practice Library Expansion & Skill Coverage**: the practice library grows from the five-activity baseline to twelve curated activities so that repeated deliberate practice is plausible, with meaningful variety rather than superficial prompt duplication.
  - Seven new Assessment Activities join the library as pure content configuration in `fablit/application/demo_data.py`: an everyday-object observation drill, a street-scene interpretation, a short alternative-uses ideation sprint, an object-transformation design ideation, a composition-detective observation, a poster-concept articulation activity, and a post-practice reflection prompt. No new activity type, workflow, or journey semantics — every new activity runs the unchanged Submission → Evaluation → Feedback → Reflection → Completion journey and is recorded through the SPEC-021 history.
  - Every activity now carries one documented primary practice capability (and optional secondaries) on the internal Observe / Interpret / Ideate / Articulate / Reflect lens (SPEC-023 §5). The lens is content-design metadata only: never learner-visible, never a domain concept, and never a selection or recommendation signal.
  - Four of the new activities are image-dependent and reuse the SPEC-015 stimulus abstraction with four new deterministic bundled fallback images; response-aware evaluation carries over through concept-matching for the new stimulus activities, and the feedback presentation now reliably surfaces an improvement and an actionable next step alongside matched strengths.
  - Short Drill eligibility expands from two to six curated activities spanning observation, writing, ideation, articulation, and reflection — still explicit content configuration (`SHORT_DRILL_ACTIVITY_TITLES`), still resolved to stable activity identities, still never history-based.
  - The activity inventory, capability coverage, variety dimensions, and documented remaining gaps (spatial reasoning, figure/gesture, material ideation, colour application, sequential thinking) are recorded in `docs/product/practice_coverage.md`.
  - Content-coverage tests (34) and journey regression tests (12) cover the expanded library: capability coverage, required fields, valid Skill references, unique prompts and titles, Short Drill configuration validity and variety, bundled stimulus presence, the lens never reaching view models or templates, and representative new activities completing the existing journey into reviewable history.

See [SPEC-023](specifications/platform/SPEC-023-practice-library-expansion-and-skill-coverage.md) — issue [#83](https://github.com/h3xh4wk/fablit/issues/83) — for details.

- **SPEC-022 — Optional Practice Modes & Learner Choice**: learners can now explicitly choose the shape of practice that fits the moment, while shorter practice stays optional and the existing learner journey is preserved.
  - A calm, low-friction chooser at `/practice` presents two modes: **A short drill** (about 5–10 minutes of learner effort — an indication, never a countdown, limit, or penalty) and **A full practice** (the existing standard experience). The Explore dashboard keeps a quiet invite link, and the normal activity library remains fully available without any mode selection.
  - Practice modes live entirely at the application/learner-experience boundary (`fablit/application/practice_modes.py` plus view models): a `PracticeMode` StrEnum (`short-drill`, `full-practice`), curated eligibility definitions, and `PracticeApplication.get_practice_modes()`/`get_practice_mode_activities()`. No new domain model, no new Assessment Activity type, no parallel submission/evaluation workflow.
  - Short Drill eligibility is explicit content configuration (`SHORT_DRILL_ACTIVITY_TITLES` in `fablit/application/demo_data.py`, resolved to stable activity identities): one concise observation activity and one concise writing activity, reusing existing Assessment Activities. New activities become drill-eligible by editing the list — not application logic.
  - Explicit learner choice only: no mode is recommended, ranked, or pre-selected from history or behaviour; the mode layer never touches the history repository.
  - Either choice enters the unchanged Activity → Submission → Evaluation → Feedback → Reflection → Completion journey, and a completed Short Drill is simply completed practice, stored and reviewable through the SPEC-021 history/review.
  - Application tests (21) and web/route tests (16) cover the mode set, curated resolution and ordering, empty/stale eligibility configuration, journey preservation through both paths, history compatibility, accessible links and labels, the ungated return path to Explore, and absence of countdown/scoring language.

See [SPEC-022](specifications/platform/SPEC-022-optional-practice-modes-and-learner-choice.md) — issue [#81](https://github.com/h3xh4wk/fablit/issues/81) — for details.

- **SPEC-021 — Persistent Practice History & Learner Review**: completed practice is now durable and reviewable. Completed practice survives application restarts and redeployments through a new persistence boundary backed by Google Cloud Datastore in production, and learners can browse their practice history and revisit any completed practice.
  - A narrow `PracticeHistoryRepository` port (application layer) isolates persistence: an in-memory implementation serves unit/application tests and local development, and a Google Cloud Datastore adapter serves the deployed App Engine environment (`FABLIT_PRACTICE_HISTORY_REPOSITORY=datastore`), with no Datastore imports in the domain or application layers.
  - Completion is persisted only after the existing successful reflection/completion flow (SPEC-018 semantics unchanged); the reflection ID is the stable completion identity, so retries never duplicate history, and a failed write raises an explicit persistence error instead of falsely reporting completion.
  - The new "Your practice" surface lists completed practice newest-first with title, completion time, and a response preview, with a calm empty state pointing back to Explore; selecting an entry opens a review showing the original stimulus (never re-resolved), the learner's response, the feedback, the learner's reflection, and the completion timestamp — an evidence surface, not a dashboard.
  - Repeated practice of the same activity remains distinguishable as separate completion records; per-learner namespacing keeps learner context explicit for future ownership work.
  - Configuration via `FABLIT_PRACTICE_HISTORY_REPOSITORY` (`memory`, `datastore`, or unset/disabled); `google-cloud-datastore` is an optional extra so ordinary tests never require Google Cloud credentials.
  - Application, persistence (fake Datastore client), configuration, and web tests cover the repository port, ordering, review reconstruction, idempotency, failure mapping, empty state, and the unchanged journey.

See [SPEC-021](specifications/platform/SPEC-021-persistent-practice-history-and-learner-review.md) — issue [#74](https://github.com/h3xh4wk/fablit/issues/74) — for details.

### Changed

- **Exam-oriented activity labels ([issue #65](https://github.com/h3xh4wk/fablit/issues/65))**: the demo activities now use terminology that is immediately recognisable to design-entrance aspirants, while the Skill, Assessment Activity, Submission, Evaluation, Feedback, and Reflection structure stays unchanged:
  - "Visual Analysis — Composition" → "CAT Practice — 2D & 3D Composition Analysis"
  - "Visual Analysis — Colour and Mood" → "Color Theory — Mood & Atmosphere Interpretation"
  - "Written Communication — Explaining an Idea" → "Creative Writing — Concept Explanations for Poster Designs"
  - "Observation — Detail Spotting" → "Memory Drawing Prep — Object & Proportion Detection"
  - "Reflection — Process Review" → "Situation Test Prep — Material & Design Process Reflection"
  - The labels live in the demo/content configuration (`fablit/application/demo_data.py`), not application logic; activity IDs, Skill behaviour, and evaluation are unchanged, and no database migration or new architectural layer is introduced. Final labels are as proposed in issue #65 and remain subject to manual review before deployment.

### Added

- **SPEC-020 — Visual Practice Experience Foundation**: the Practice Activity screen now reads as a focused design-practice workspace rather than a question-and-answer form, while preserving the existing learner journey and learning model.
  - The screen is organised around an explicit, labelled hierarchy — stimulus (Observe) → task (Your task) → response (Your response) — so the learner can see what to look at, what to do, and where to respond without searching the interface.
  - The existing SPEC-015 resolved stimulus is presented inside the observe region at a useful scale with meaningful alternative text and a compact source/attribution treatment; activities without a suitable stimulus stay clean and text-first with no fabricated imagery.
  - Text responses get a distinct response surface, a generous minimum response height, visible guidance text, and the response is preserved when submission or evaluation fails.
  - SPEC-017 submission acknowledgement and duplicate-submission protection, and the SPEC-018 completion semantics, are unchanged; evaluation, feedback, reflection, and completion behave exactly as before.
  - Presentation only: no scores, progress, streaks, timers, gamification, drawing/upload, new stimulus architecture, new external image provider, database migration, or new runtime dependency.
  - Web tests cover the practice hierarchy, stimulus/no-stimulus presentation, response comfort and preservation, submission continuity, and the unchanged journey; the opt-in browser journey checks the practice workspace regions on desktop and mobile viewports.

See [SPEC-020](specifications/platform/SPEC-020-visual-practice-experience-foundation.md) — issue [#72](https://github.com/h3xh4wk/fablit/issues/72) — for details.

- **SPEC-018 — Learner Practice Continuity & Progress Foundation**: successful
  reflections now create an in-memory `PracticeCompletion` record containing
  the demo learner, activity, reflection, and timezone-aware completion time.
  - Dashboard activity cards give a lightweight “Practised” indication after a
    completed journey; repeated completions remain supported and activities
    remain available to practise again.
  - The implementation introduces no percentage, mastery, proficiency, score,
    streak, ranking, recommendation, database, or analytics behaviour.
  - Application and web tests cover completion timing, failed/blank reflection,
    dashboard continuity, and repeated practice.

See [SPEC-018](specifications/platform/SPEC-018-learner-practice-continuity-and-progress-foundation.md) — issue [#66](https://github.com/h3xh4wk/fablit/issues/66), PR [#68](https://github.com/h3xh4wk/fablit/pulls/68) — for details.

- **SPEC-017 — Submission & Evaluation Feedback**: the learner is immediately
  acknowledged while a response is being evaluated, with an accessible,
  server-rendered HTMX processing state and an in-place transition to the
  existing feedback experience.
  - Submission controls communicate the evaluation state, disable repeated
    clicks, and retain progressive enhancement for learners without JavaScript.
  - The application layer also rejects concurrent submissions for the same
    activity, so duplicate evaluation is prevented even when client-side
    controls are bypassed or requests race.
  - Recoverable validation and evaluation failures preserve the learner's
    response and render a clear retry path with accessible error messaging.
  - Web and application tests cover the processing state, successful and
    failed transitions, response preservation, and duplicate prevention.

See [SPEC-017](specifications/platform/SPEC-017-submission-and-evaluation-feedback.md) for details.

- **SPEC-016 — First Learner Experience Refinement**: visual and interaction refinement of the complete learner activity from functional to intentional and inviting, guided by UX-001 and UX-002.
  - Dashboard: conversational greeting with activity cards featuring clear visual hierarchy (title, invitation, skill, explore action).
  - Practice page: conversational invitation cue, hero stimulus presentation, observation prompt encouraging curiosity, notebook-like response area with guidance text ("There isn't a right answer. Tell us what you notice..."), and conversational submit action ("I'm ready →").
  - Feedback: "Something you noticed" heading with personalized Finding presentation, conversational tone (insight, not grade).
  - Reflection: conversational heading with emoji cue, natural continuation from feedback.
  - Completion: quiet accomplishment ("You noticed. You thought. You found something.") with clear return navigation.
  - CSS: intentional whitespace, warm editorial typography, subtle interaction states, responsive mobile-first layout, preserved accessibility (focus states, reduced motion, semantic labels).
  - No new domain models, no new persistence, no new backend architecture, no gamification.
  - Tests updated and extended; all quality gates pass.

See [SPEC-016](specifications/platform/SPEC-016-first-learner-experience-refinement.md) for details.

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
