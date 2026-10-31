# Fablit Architecture Blueprint

**Document ID:** AB-001
**Version:** 0.21.0
**Status:** Draft
**Last Updated:** 2026-10-28

---

# Purpose

This document describes the conceptual architecture of the Fablit platform.

Its purpose is to provide a shared understanding of the platform's major building blocks, their responsibilities, and their relationships.

This document intentionally avoids implementation details, frameworks, databases, or deployment technologies.

Those belong to Architecture Decision Records (ADRs).

---

# Architectural Vision

Fablit is a modular learning platform that develops practical skills through structured practice, assessment, meaningful feedback, and reflection.

The platform separates:

- platform capabilities
- learning experiences
- educational content

This separation allows new domains, Skill Labs, and Content Packs to be introduced without changing the platform core.

---

# Platform Overview

```
                          Fablit

                             │

         ┌───────────────────┴────────────────────┐

         │                                        │

    Platform Core                          Learning Experiences

         │                                        │

         │                                  Skill Labs

         │                                        │

         │                              Assessment Activities

         │                                        │

         └───────────────────┬────────────────────┘

                             │

                      Content Packs
```

---

# Core Components

## Platform Core

The Platform Core provides capabilities shared by the entire system.

Responsibilities include:

- authentication
- user management
- progress tracking
- assessment orchestration
- feedback orchestration
- notifications
- analytics
- content management
- AI integrations

The Platform Core contains no domain-specific educational content.

---

## Skill Labs

A Skill Lab is a modular learning experience focused on developing one or more related skills.

Examples include:

- Writing
- Observation
- Creativity
- Interview
- Research

Each Skill Lab contributes:

- assessment activities
- evaluation rubrics
- learning resources
- feedback strategies
- reflection prompts

Skill Labs are independent modules.

---

## Assessment Activities

Assessment Activities are the smallest unit of learner interaction.

Examples include:

- Multiple Choice Question
- Writing Exercise
- Observation Exercise
- Interview Response
- Sketch Submission
- Portfolio Review
- Reflection

Every Assessment Activity produces a learner submission.

---

## Assessment

An Assessment is a structured collection of Assessment Activities.

Examples:

- Mock Test
- Daily Practice
- Weekly Challenge
- Skill Evaluation

Assessments define:

- activity order
- timing
- scoring rules
- completion criteria

SPEC-005 implements the Assessment and Assessment Activity concepts as an in-memory learning-domain model (`fablit.domain`), independent of the Platform Core. Activity order is enforced by the domain model; timing, scoring rules, and completion criteria are deferred to future specifications.

---

## Submission

A Submission represents a learner's response to an Assessment Activity.

Examples include:

- selected answer
- written response
- uploaded image
- recorded audio
- recorded video

Submissions are immutable records of learner work.

SPEC-006 implements the Submission concept as an in-memory learning-domain model (`fablit.domain`), independent of the Platform Core. Submissions reference the learner and the Assessment Activity by stable identity, support a Draft → Submitted lifecycle, and deliberately exclude evaluation, feedback, persistence, and examination-specific concepts.

---

## Evaluation

Evaluation determines how a submission is interpreted.

Evaluation may be:

- automatic
- AI-assisted
- instructor-reviewed
- peer-reviewed

Evaluation produces Feedback.

SPEC-007 implements the Evaluation concept as an in-memory learning-domain model (`fablit.domain`), independent of the Platform Core. Evaluations reference the Submission by stable identity (SPEC-006), contain one or more structured Findings with stable identities, record a timezone-aware evaluation timestamp, and are immutable after creation. Scoring, Feedback, evaluation mechanisms, AI providers, and persistence are deliberately excluded from the model.

SPEC-015 extends Findings so they can be **response-aware**: an optional `evidence` field (a response excerpt or matched concept) grounds each Finding in the learner's actual response, so evaluation responds to what the learner wrote rather than returning predefined feedback.

---

## Feedback

Feedback provides guidance for improvement.

Feedback may include:

- strengths grounded in observation
- specific improvement suggestions
- practical next-step guidance
- a handoff into Reflection

Feedback prioritizes learning over grading.

SPEC-008 implements the Feedback concept as an in-memory learning-domain model (`fablit.domain`), independent of the Platform Core. Feedback references the Evaluation by stable identity (SPEC-007), carries a single general learner-facing content field, records a timezone-aware creation timestamp, and is immutable after creation. Scoring, Reflection, feedback-generation mechanisms, AI providers, and persistence are deliberately excluded from the model.

SPEC-030 defines the learner-facing quality boundary for this feedback: the application layer translates Evaluation findings into grounded strengths, improvement advice, and next-step guidance that stay faithful to the practice purpose and the evidence available in the learner's response. Feedback therefore remains a learning aid, not a score, ranking, label, or recommendation engine.

---

## Sketchbook Reflection (SPEC-031)

SPEC-031 adds a lightweight optional practice entry point that brings learner-owned sketchbook work into the existing deliberate-practice loop without creating another drawing product or a public gallery.

The architecture keeps the sketch as context, while the learner's written reflection remains the primary evaluable response. The application layer treats the uploaded image as private practice material, not as a scored artifact or a separate persistent record type. It uses the same `Practice → Submission → Evaluation → Feedback → Reflection → Completion` path as other activities, preserving the same learner-scoped history boundary and completion flow.

### Relationship

```
Learner sketchbook work
          │
          ▼
    Sketchbook Reflection
          │
          ▼
    Feedback + next action
          │
          ▼
    Return to sketching / another practice
```

The use of an image is intentionally contextual and secondary: it helps the learner connect their work to a small, meaningful reflection, while the platform remains focused on the growth of the learner's reflective process rather than on judging the drawing itself.

---

## Reflection

Reflection encourages learners to evaluate their own work after receiving feedback.

Reflection is considered part of the learning process rather than an optional activity.

SPEC-009 implements the Reflection concept as an in-memory learning-domain model (`fablit.domain`), independent of the Platform Core. Reflection references the Feedback by stable identity (SPEC-008), carries a single general learner-authored content field, records a timezone-aware creation timestamp, and is immutable after creation. Confidence scoring, improvement goals, action plans, reflection-generation mechanisms, AI providers, Progress, and persistence are deliberately excluded from the model.

---

## Skill

Skill represents the measurable, transferable capability being developed through deliberate practice.

Skill is the capability being developed; an Assessment Activity provides a context in which one or more Skills may be practised, and Evaluation determines what was observed about a particular Submission. Evaluation criteria therefore remain outside the Skill model.

SPEC-010 implements the Skill concept as an in-memory learning-domain model (`fablit.domain`), independent of the Platform Core. Skill carries only a stable identity, a human-readable name, and a meaningful description, and is immutable after creation. Evaluation criteria, scoring, Progress, mastery, hierarchy, curriculum and examination structures, AI providers, and persistence are deliberately excluded from the model.

SPEC-011 connects Skills to Assessment Activities as a simple many-to-many association: an Assessment Activity references the zero or more Skills it provides an opportunity to practise, by stable identity only (`skill_ids`). The association lives on the Assessment Activity — the Activity's learning context — and introduces no dedicated relationship entity, relationship attributes, Progress, mastery, scoring, evaluation, curriculum, examination, or AI semantics. Skill and Assessment Activity remain independently meaningful, preserving the separation between intended Skills and actual Evaluation findings.

---

## Application Layer

The Application Layer orchestrates the existing learning-domain models into learner workflows.

SPEC-012 introduces the first Application Layer (`fablit.application`) as a boundary between the Web/UI and the domain:

```
USER/BROWSER → WEB/UI (HTMX + server-rendered HTML) → APPLICATION LAYER → DOMAIN → INFRASTRUCTURE
```

The Application Layer is responsible for:

- learner use cases (dashboard retrieval, start practice, submit response, demo evaluation, feedback preparation, start/submit reflection, completion result);
- workflow orchestration and application-level journey state;
- learner-facing view model preparation;
- domain coordination (creating Submissions, Evaluations, Feedback, and Reflections through the existing domain models).

The Application Layer is deliberately **not** a second domain model: it does not redefine domain invariants and contains no HTML or presentation logic. SPEC-012 also establishes a deterministic demo evaluator and a minimal in-memory journey store so the vertical slice can be demonstrated and tested end to end without AI providers, network services, asynchronous workers, or a persistence layer. The evaluator and store are replaceable without changing learner-facing concepts.

SPEC-012 deliberately introduces no authentication, user registration, Progress, mastery, proficiency, scoring, recommendations, personalization, or examination-specific logic.

## Learner Experience and Visual Foundation

SPEC-013 establishes the first coherent learner experience and visual foundation around the existing architecture. It is a presentation-layer change: the domain models and the SPEC-012 Application Layer remain unchanged, and all work lives in the Web/UI layer (Jinja2 templates, a centralized stylesheet, and small reusable presentation components).

The learner-facing experience presents the underlying structure (Skills → Activities → Evaluation → Feedback → Reflection) as an invitation to learn:

```
Dashboard (invitation to explore)
    ↓
Practice (quiet, prompt-forward)
    ↓
Feedback (conversational Findings)
    ↓
Reflection (natural continuation)
    ↓
Completion (quiet acknowledgement)
    ↓
Back to the dashboard
```

SPEC-013 introduces:

- a small design-system foundation (page container, typography hierarchy, buttons, links, cards, forms, field errors, feedback sections, completion messages) in `app/static/css/fablit.css`;
- centralized design tokens (typography, spacing, colours, border radius, shadows, transitions, container widths) as CSS custom properties;
- a warm-neutral + restrained-accent colour direction that communicates focus, invitation, and completion — never correct/incorrect or performance;
- responsive behaviour for mobile, tablet, and desktop, with mobile-first card stacking;
- accessibility as part of the experience: semantic HTML, a single-h1 document hierarchy, labelled form controls, a skip link, visible focus states, and reduced-motion support;
- conversational, score-free presentation of structured Findings, and a quiet, non-gamified completion state.

The frontend architecture remains server-rendered HTML + HTMX progressive enhancement + small reusable visual components. SPEC-013 introduces no React/Vue/Angular/SPA, no scoring or gamification, no Progress domain, no authentication, no recommendation engine, no AI evaluation dependency, and no examination-specific logic.

---

## Learner Pilot Deployment

SPEC-014 introduces no new domain capability. It establishes an operational boundary around the existing system so the current learner experience can be placed in front of a small group of real learners (approximately 5–10) safely and reliably:

```
                    Real Learner
                         │
                         ▼
                   Public HTTPS
                         │
                         ▼
                  Fablit Web/UI
                         │
                         ▼
                   Application
                         │
                         ▼
                      Domain
                         │
                         ▼
                   Persistence
```

Implemented in SPEC-014:

- a dedicated pilot environment (PythonAnywhere, per ADR-008) separate from local development, reproducible from the repository, with a stable HTTPS URL and managed TLS;
- environment-variable configuration with nothing environment-specific hard-coded and no committed secrets;
- a documented, deterministic startup mechanism (`app.main:app` served by uvicorn) that does not require a developer to start a local process after restart;
- explicit persistence verification: the current in-process `LearnerJourneyStore` (SPEC-012) is acceptable for the pilot, with restart behaviour documented and no upgrade introduced;
- a learner-facing error page with no stack traces, internal paths, environment variables, credentials, or framework debugging pages; full details are written to server logs only;
- a safety boundary that disables development-only interfaces (API documentation) and debug output in the production environment and exposes no admin endpoints, dev tools, or secrets;
- basic application logs, a simple health check (`GET /health` → `200 OK`), a Git-based rollback path, and deployment/browser/mobile/accessibility verification against the real public URL;
- pilot operations tooling: minimal learner instructions and a lightweight structured feedback-recording mechanism feeding the evidence-driven loop (Deploy → Observe → Collect feedback → Identify patterns → Form findings → Discuss implications → Define next specification).

SPEC-014 is deliberately **pilot-ready, not production-ready**: authentication, authorization, data privacy, backups, monitoring, security hardening, scalability, formal analytics, content management, and operational support remain future work.

---

## Contextual Visual Stimulus & Response-Aware Evaluation

SPEC-015 makes the visual stimulus part of the learner's activity instance rather than an attachment to an activity, and makes evaluation respond to the learner's actual response. It establishes the learning loop Activity → Contextual stimulus → Learner observes → Learner responds → Response-aware evaluation → Structured Finding → Personalized feedback → Reflection → Completion.

```
Assessment Activity
    │
    ├───────────────┐
    │               │
    ▼               ▼
Stimulus       Learner Response
    │               │
    └───────┬───────┘
            ▼
        Evaluation
            │
            ▼
         Findings
            │
            ▼
         Feedback
```

Implemented in SPEC-015:

- **Domain:** an Assessment Activity may define an `ActivityStimulusContext` (learning focus, stimulus context, retrieval query — §6), and a `StimulusInstance` represents the resolved stimulus shown to a learner, retaining provider, asset ID, image URL, source page URL, creator, license, attribution, and a timezone-aware retrieval timestamp (§15–17). Findings gain an optional `evidence` field grounding them in the learner's response (§29–31). The domain stays free of HTTP, FastAPI, provider-specific APIs, and external network calls (§39).
- **Stimulus provider abstraction (§9, §40–41):** external image retrieval is isolated behind an application-level `StimulusProvider`; provider-specific fields are translated into Fablit's internal stimulus representation (§49). One approved external source (Wikimedia Commons) is implemented as a replaceable provider, and a deterministic built-in provider serves bundled images, so the default experience — and the automated tests — never depend on a live external service (§42–43, §67).
- **Safe failure handling (§21–23, §45, §50):** a resilient provider composition falls back to a known, learner-safe stimulus when external retrieval fails; the learner never sees a blank activity, stack traces, credentials, or internal exception details. Network timeouts, unavailable providers, invalid responses, and missing metadata are all handled (§50).
- **Response-aware evaluation (§27–31, §60):** the evaluator contract receives the activity, the stimulus, and the learner's response and produces at least one structured Finding grounded in the response; different responses produce different Findings (§69). Empty and very short responses are handled explicitly without fabricating positive Findings (§62–63).
- **Learner presentation (§24–26):** the resolved image is presented before the observation prompt with a compact source/attribution treatment, meaningful alternative text, and responsive, non-overflowing layout; feedback remains score-free and is derived from the Findings (§33–35).
- **Historical integrity (§18, §48, §68):** a completed activity stays associated with the exact stimulus that was shown; the same resolved stimulus is reused while the learner works on an activity instance, and a new stimulus may be resolved for a new instance (§19).
- **Reference activity (§56–58):** the composition activity (now labelled "CAT Practice — 2D & 3D Composition Analysis" for the design-aspirant pilot, issue #65) is the reference implementation of the stimulus + response-aware evaluation flow, with three of the five demo activities now presenting bundled visual stimuli.
- **No new persistence dependency (§46):** the in-memory journey store retains stimulus metadata and evaluation results for the activity instance, so no production database is introduced.
- **No scoring or gamification (§4, §37):** SPEC-015 deliberately introduces no points, grades, rankings, or AI evaluation platform; the evaluator is the smallest viable response-aware implementation, and future rule-based, AI-assisted, or hybrid evaluators can implement the same contract (§28, §60).

---

## Learner Practice Continuity & Progress Foundation

SPEC-018 adds a deliberately small application-layer continuity boundary at
the completion-to-dashboard transition. `PracticeApplication` records a
`PracticeCompletion` in the in-process `LearnerJourneyStore` only after a
Reflection is successfully saved. The record retains the learner, activity,
reflection, and timezone-aware completion time; it is isolated from domain
models so a later durable history implementation can replace the store without
changing the learner-facing dashboard contract.

```
Response → Evaluation → Feedback → Reflection → Practice Completion → Dashboard
```

The dashboard may present a simple prior-practice indication for activities
with one or more completion events. It neither counts nor measures them:
there are no percentages, mastery or proficiency labels, scores, streaks,
rankings, recommendations, analytics, authentication, or database changes.
Activities continue to be available after completion, and repeated deliberate
practice creates distinct completion events.

---

## Visual Practice Experience

SPEC-019 and SPEC-020 strengthen how Fablit's existing learning experience is
presented, without changing the learning model. Both are presentation-layer
specifications: the domain models and the Application Layer are unchanged, and
all work lives in the Web/UI layer (Jinja2 templates, the centralized
stylesheet, and the existing design tokens).

SPEC-019 refines the Explore/practice-discovery surface. It reuses the existing
SPEC-015 stimulus content as a **card preview** — a discovery cue that is
explicitly *not* the learner's activity-instance stimulus:

```text
Explore preview  ≠  Learner activity-instance stimulus
```

Starting an activity continues to use the authoritative SPEC-015 stimulus
lifecycle. Activities without an appropriate bundled asset stay text-first; no
decorative imagery is fabricated for consistency. The desktop card grid uses
available horizontal space more effectively while preserving a comfortable
reading measure.

SPEC-020 turns the Practice Activity screen into a focused practice workspace
organised around an explicit, labelled hierarchy:

```text
Stimulus (Observe)
      ↓
Task / Instruction (Your task)
      ↓
Learner Response (Your response)
      ↓
Submit
```

The resolved activity-instance stimulus is presented inside the observe region
at a useful scale with meaningful alternative text and a compact
source/attribution treatment. Text responses receive a distinct response
surface with a generous response height, visible guidance, and keyboard
accessibility, and the learner's response is preserved when submission or
evaluation fails. The SPEC-017 submission acknowledgement and
duplicate-submission protection, and the SPEC-018 completion semantics, remain
intact.

Both specifications deliberately introduce no scoring, progress indicators,
streaks, badges, timers, recommendations, analytics, drawing/upload workflows,
new Stimulus architecture, external image-provider integration, database
migration, SPA framework, or new runtime dependency.

---

## Persistent Practice History & Learner Review

SPEC-021 establishes the first production persistence boundary for the learner
journey. The layering is deliberate:

```text
Learner Experience (app)
        ↓
Application / Use Cases (PracticeApplication)
        ↓
Learner Journey Repository / Persistence Port (PracticeHistoryRepository)
        ↓
Google Cloud Datastore Adapter (fablit.platform)
```

The application layer depends only on the port; the domain layer depends on
neither the port's adapters nor any persistence mechanism. Two adapters exist:
the in-memory repository (unit/application tests, local development) and the
Datastore adapter (the deployed App Engine environment), selected purely by
configuration (`FABLIT_PRACTICE_HISTORY_REPOSITORY`).

A completed practice becomes durable history only after the SPEC-018
completion flow succeeds; a failed write raises an explicit persistence error
instead of falsely reporting completion, and the reflection identity serves as
the stable completion identity so retried writes are idempotent. Each
completion retains the evidence needed for review — activity, the stimulus
resolved for that attempt, the learner's response, evaluation, feedback,
reflection, and completion time — so repeated practice remains distinguishable
and reviews never silently re-resolve a stimulus.

```text
Response → Evaluation → Feedback → Reflection → Completion → Durable History → Review
                                                    (SPEC-018)     (SPEC-021)  (SPEC-021)
```

The learner-facing surface ("Your practice" history and per-completion review)
is a reflection and evidence surface: no mastery, scores, percentages,
rankings, streaks, or recommendations. Per-learner Datastore key namespaces
keep learner context explicit for future authentication/ownership work without
redesigning the stored evidence.

### Private Sketchbook Artifact Storage (SPEC-033 / SPEC-034)

The sketchbook reflection practice can attach a private learner image, but the
binary payload is deliberately excluded from the practice-history record. The
boundary is layered as:

```text
Review route (learner-scoped)
        ↓
Application / Use Cases (PracticeApplication)
        ↓
Artifact Storage Port (ArtifactStorage)
        ├── FileArtifactStorage (local dev/test)
        └── GCSArtifactStorage (Google Cloud Storage, App Engine production)
```

`StoredPracticeCompletion.artifact` is an `ArtifactRef` — metadata only — so the
Datastore `PracticeCompletion` entity never carries image bytes, and the
SPEC-021 port and application layer stay independent of any storage mechanism.
The in-memory adapter stores the same reference. Upload validation
(PNG/JPEG/WebP, 5 MB) is unchanged and remains an application-boundary concern.

Ownership and access control are enforced at the application boundary, not by
obscurity: the review route resolves the artifact reference through the
requesting learner's own completion (SPEC-024 identity, per-learner history)
before reading the bytes from the private store. There are no public or direct
media URLs, and a missing reference, missing bytes, and another learner's
completion all produce the same unlisted 404.

Artifact storage backends are configurable via `FABLIT_ARTIFACT_STORAGE_BACKEND`:
- **File-backed (`file`, default):** `FileArtifactStorage` stores bytes in a
  deployment-private filesystem directory (`FABLIT_ARTIFACT_STORAGE_DIR`),
  defaulting to a process-private temp directory. Used for local development and
  automated testing without external cloud credentials.
- **Google Cloud Storage (`gcs`, SPEC-034):** `GCSArtifactStorage` in
  `fablit.platform.gcs_artifact_storage` persists objects durably in a private
  GCS bucket specified by `FABLIT_ARTIFACT_STORAGE_BUCKET`. The bucket has
  Uniform Bucket-Level Access and public access prevention enabled. The App
  Engine service account authenticates via Application Default Credentials (ADC)
  requiring `roles/storage.objectUser`.

Records written before this boundary existed embedded the bytes inline. They
still deserialize (the embedded payload is ignored), and no automatic
migration is performed: legacy bytes are no longer retrievable through the
review, and a review renders normally when an artifact's bytes are missing.

---

## Optional Practice Modes & Learner Choice

SPEC-022 adds a lightweight practice-mode concept at the
application/learner-experience boundary — deliberately outside the domain
model, which still knows nothing about modes:

```text
Learner Experience (chooser, /practice)
        ↓
Practice Choice / Application Layer (PracticeApplication, practice_modes.py)
        ↓ selects
Existing Assessment Activity → existing learner journey (SPEC-012…018)
        ↓
Persistence / History (SPEC-021)
```

The initial mode set is deliberately small: **Short Drill** (about 5–10
minutes of learner effort — an indication, never a countdown or limit) and
**Full Practice** (the existing standard experience). Short Drill eligibility
is explicit, curated content configuration (`SHORT_DRILL_ACTIVITY_TITLES` in
the demo content) resolved to stable activity identities — never title-string
inference, recommendations, or hidden personalization. The learner's explicit
selection is authoritative for the current practice entry; a learner who
ignores the chooser still reaches the ordinary activity library, and a
completed Short Drill is simply completed practice under SPEC-021. No new
domain type, no parallel workflow, no scores, streaks, timers, or
recommendation engine. SPEC-023 expands the curated drill list to six
activities without changing this mechanism.

---

## Practice Library Expansion (SPEC-023)

The practice library is content, not architecture. SPEC-023 grows the demo
library from the five-activity baseline to twelve curated Assessment
Activities so that repeated deliberate practice is plausible, and records an
internal **practice capability lens** (Observe / Interpret / Ideate /
Articulate / Reflect) on each activity as content-design metadata.

```text
Content configuration (demo_data.py — definitions + capability metadata)
        ↓ builds
Assessment Activity (existing domain model, unchanged)
        ↓
Existing practice application (unchanged journey)
        ↓
Submission → Evaluation → Feedback → Reflection → Completion
        ↓
Practice History (SPEC-021, unchanged)
```

The lens is a review aid over the library, not a runtime concept: it is not
a domain model, not a Skill hierarchy, never learner-visible, and never
drives selection or recommendations (AC-023-12, AC-023-13). New activities
add no application branches — stimulus-dependent ones reuse the SPEC-015
stimulus abstraction with deterministic bundled fallbacks, response-aware
ones reuse the SPEC-015 concept-matching evaluator, and text-first ones reuse
the predefined-feedback path. The resulting inventory, capability coverage,
and remaining gaps are documented in `docs/product/practice_coverage.md`.

---

## Learner Identity & Private Practice History (SPEC-024)

Anonymous does not have to mean shared. SPEC-024 connects the existing
learner-scoped persistence boundary (SPEC-021) to real web requests: every
anonymous learner's browser receives a unique, opaque learner identity in a
secure cookie, and every request resolves a learner-scoped application.

```text
HTTP request
   ↓
learner identity middleware (cookie, or a newly minted opaque identity)
   ↓
learner-scoped PracticeApplication (per-learner LearnerJourneyStore)
   ↓
learner-scoped persistence (SPEC-021 history repository, unchanged)
```

- **Identity primitives** live in `fablit/platform/learner_identity.py`:
  opaque UUID generation (no personal information, derived from nothing but
  a secure random source) and secure cookie transport (HttpOnly, SameSite
  Lax, one-year lifetime, Secure in production).
- **Resolution is centralised** in `app/learner_session.py`: the identity
  middleware resolves the identity once per request and the routes obtain the
  current learner's application through it — the boundary is not duplicated
  per route (SPEC-024 §6). Demo content, evaluator wiring, and the stimulus
  provider are learner-independent and built once; only learner-scoped state
  is per learner.
- **The fixed demo learner identity is no longer used for normal web
  requests** (AC-024-08): `DEMO_LEARNER_ID` remains only as seeded demo
  content metadata for application-layer tests.
- **Privacy, not accounts** (§1, §4): no registration, email, password, or
  social login; no cross-device promise — clearing the cookie simply starts a
  fresh anonymous learner (§5.3). The identity is an internal ownership
  identifier, never a credential and never rendered in pages or URLs (§9).
- **Future portability** (§10): a later recovery/sign-in mechanism attaches
  to the internal `learner_id`; the external identity never becomes the
  practice-history key.

---

## Curated Practice Continuity (SPEC-025)

SPEC-025 makes the moment after completion educationally meaningful: the
learner may see one authored next practice, with the relationship between
the two activities made visible. This is authored content continuity, not
personalization — the design principle is **connect practices, not
learners**.

```text
Completion (SPEC-018)
        ↓
Practice transition map (content configuration, practice_continuity.py)
        ↓ names one existing activity
Completion view + Continuation view → quiet continuation on /complete
        ↓ (learner's choice)
existing practice journey (SPEC-012…018) → SPEC-021 history (SPEC-024 owner)
```

- **Content configuration, not a recommendation service** (§7): the
  transition table (`_AUTHORED_TRANSITIONS` in
  `fablit/application/practice_continuity.py`) pairs source and target
  activities by title — the same title-keyed convention as the SPEC-022
  drill list — resolved once to stable activity identities. New transitions
  are added by editing the table, never application logic.
- **Deterministic and learner-independent** (AC 2, AC 4): the transition
  resolves from the completed activity's identity alone; two learners who
  complete the same activity always receive the same continuation.
- **Journey and boundaries unchanged** (§3.4): following the continuation
  runs the existing Submission → Evaluation → Feedback → Reflection →
  Completion journey, persists under the current learner's identity through
  the SPEC-021/SPEC-024 boundaries, and repeated practice stays available.
- **The learner stays in control** (§3.3): the continuation is a quiet,
  editorial invitation on the completion page — never a forced step; Explore
  and History navigation remain exactly as before.

---

## Metacognitive Practice & Reflection Integration (SPEC-026)

SPEC-026 weaves metacognition into the existing journey so the learner
experiences one continuous loop — **set intent → practise → receive
evaluation feedback → reflect → review the whole artifact** — without new
domain models, scoring, analytics, or AI analysis.

```text
Activity selected (SPEC-019 / SPEC-025)
        ↓
GET /activities/{id}/intention — optional focus prompt (Continue / Skip)
        ↓
Intention attached to the session's Submission at response time
        ↓
Evaluation feedback (SPEC-017) with the structured reflection panel
        ↓ (Save reflection / Skip reflection)
Completion (SPEC-018) → SPEC-021 review renders the whole artifact
```

- **Optional intention, never a gate** (§2.1): the single-input prompt is
  reached from the dashboard and continuation surfaces; direct activity
  entry still works unchanged, a blank submission is accepted gracefully,
  and the captured focus is echoed quietly in the workspace and on the
  reflection page.
- **Optional structured reflection** (§2.2): the feedback page carries two
  qualitative prompts — strategy assessment and gap analysis — immediately
  after the evaluation rendering, with Save and Skip controls. A skipped or
  blank reflection completes the practice in the journey store without
  creating a `Reflection` record; durable SPEC-021 history remains
  reflection-bound (PHR-001), so no history entry is written for a skipped
  reflection. The completion acknowledgement reflects what actually
  happened.
- **Whole-artifact review** (§2.3): the SPEC-021 review renders intention,
  response, evaluation feedback, and reflection in chronological order. The
  intention persists inside the stored Submission (both the in-memory and
  Datastore adapters), with backward-compatible deserialization for records
  written before SPEC-026.
- **Reflections stay qualitative** (§4): no metric, mastery level, or
  completion signal is derived from intention or reflection text, and no
  automated feedback is produced on it.

---

## Session Resilience & Local Practice Recovery (SPEC-028)

SPEC-028 protects active practice against accidental reloads, tab closures,
and transient input loss with a client-side transient storage layer. The
server application is unchanged: the entire layer is a static module
(`app/static/js/session-recovery.js`) wired once in `base.html`, and no
draft ever reaches the network.

```text
Learner typing (intention / response / reflection)
        ↓ 3s debounce or field blur
IndexedDB (primary) → localStorage (fallback) → silent no-op (§3)
        ↓ reload / return to the activity
Recovery banner (response): Resume Draft / Discard Draft
Quiet restore (intention, reflection)
        ↓ successful submission
Draft key removed immediately; 24h purge on launch
```

- **Storage key format** (§3): `fablit_draft_<scope>_<activity_id>`. The
  SPEC-024 learner cookie is deliberately HttpOnly — unreadable by client
  script — so the client layer maintains its own opaque, anonymous scope
  persisted in `localStorage`. Isolation is per browser, equivalent in
  intent to the spec's learner key, without exposing identity to
  JavaScript.
- **Tracked state** (§2.1): active activity ID, draft pre-practice
  intention, active response draft, draft post-practice reflection, and the
  timestamp of the last local mutation (driving the 24-hour expiry, §2.3).
- **Graceful degradation** (§3): when storage is disabled or quota is
  exceeded, every write/read becomes a silent no-op and standard
  uninterrupted practice continues — recovery is an enhancement, never a
  dependency.
- **Boundaries unchanged** (§3.4): drafts are transient convenience state;
  the durable artifact remains the SPEC-021 history record written after
  successful reflection. Drafts are never scored, analysed, or graded, and
  the recovery copy stays calm and factual.

---

## Internal AI Authoring Security Boundary (SEC-001 / SPEC-032)

SPEC-032 introduces an internal AI-assisted practice authoring workflow. Because the deployed Fablit platform is publicly accessible, SEC-001 establishes a strict, server-side security boundary around authoring interfaces and AI-generation capabilities:

```text
Public Learner Request (/, /practice, /history)
        ↓
Learner Identity Middleware (anonymous, public, open)
        ↓
Learner Experience & Practice Application

Internal Author Request (/authoring, /authoring/generate, /authoring/candidates)
        ↓
Authoring Authentication Guard (require_author_access)
        ↓ checks FABLIT_AUTHORING_SECRET (constant-time comparison)
        ├── If valid: Authoring Router & AI Candidate Generation
        └── If invalid/unconfigured: 401 Unauthorized (AI provider never invoked)
```

- **Strict server-side enforcement:** Authoring UI routes (`/authoring`) and candidate generation endpoints (`/authoring/generate`, `/authoring/candidates`) enforce authorization server-side prior to executing any handler logic.
- **Provider invocation protection:** Unauthorized requests are rejected immediately with 401 Unauthorized, guaranteeing that unauthenticated actors cannot consume configured AI providers.
- **Shared secret authentication:** Access requires `FABLIT_AUTHORING_SECRET`, verified with constant-time equality (`hmac.compare_digest`) in `fablit.platform.authoring_auth`. When unset or blank, authoring access is disabled by default.
- **Transport mechanisms:** Supports interactive author login via `/authoring/login` (setting an HttpOnly, SameSite=Lax, Path-restricted session cookie `fablit_author_token`, marked Secure in production) as well as header-based authentication (`Authorization: Bearer <secret>`, Basic auth, or `X-Author-Key`).
- **Complete learner isolation:** Existing learner routes remain completely anonymous, public, and unaffected. Provider credentials (`FABLIT_AI_PROVIDER_API_KEY`) stay server-side and are never exposed in HTML or client responses.
- **Minimal scope:** SEC-001 provides the smallest secure boundary for internal authoring, intentionally omitting learner authentication, multi-author RBAC, or public author registration.
- **Typed authoring brief (FIX-6 / issue #129):** the authoring boundary validates required practice area, learner context, purpose, mode, response form, evaluation intent, feedback intent, and reflection intent before generation. Optional context, lens, constraints, stimulus, and continuation fields remain optional.
- **Candidate provenance:** provider-neutral generation results become process-local `PracticeCandidate` records retaining the original brief, untrusted candidate mapping, provider, model, and timezone-aware UTC generation time. The provider adapter owns vendor configuration; candidate data remains subject to deterministic SPEC-029/SPEC-030 validation before approval.
- **Unavailable provider behavior:** no fabricated draft is returned when no provider is configured. Generation returns a service-unavailable response; the candidate store is in-memory and is not a durable history or publication mechanism.

---

## AI-Assisted Practice Authoring Workflow (SPEC-032)

SPEC-032 adds the authoring workflow itself on top of the SEC-001 boundary. It scales *curated* practice: AI drafts candidate activities, but only an explicit human approval places content in the learner-facing library (AA-001, AA-008).

```text
Authoring Brief (structured intent)
        ↓
Candidate Generation  ── no provider configured → brief-derived draft
        ↓                 provider configured → provider output
Structural (SPEC-029) + Feedback (SPEC-030) Validation
        ↓  (malformed output is non-approvable)
Human Review: inspect · compare with brief · edit · reject
        ↓  explicit approval only
Approved Practice → Curated Library
```

- **Application boundary, no new domain model:** the workflow lives in `fablit/application/authoring.py` (`PracticeAuthoringBrief`, `PracticeCandidate`, `CandidateStatus`, `AuthoringProvenance`, `validate_candidate`, `AuthoringCandidateStore`). A candidate reuses the existing SPEC-029 `PracticeContentContract`; there is no parallel learner-facing practice model.
- **Structured brief (§4):** practice area, purpose, task, thinking lens, mode, response form, intents, stimulus/constraints, and optional examination context. An exam name alone cannot form a brief (AA-006).
- **Provider-agnostic generation (§17):** with no AI provider configured the workflow derives a structured draft from the brief, so authoring and learner practice never depend on AI availability. Provider failures surface as a 502 and never create learner-facing content.
- **Validation gate (§7):** structural errors (missing/incomplete SPEC-029 contract, missing title/description) and SPEC-030 feedback violations block approval; exam-name-only and practice-area mismatches are review warnings that never auto-approve. Malformed provider output becomes a non-approvable candidate instead of entering the approval path.
- **Explicit human gate (§8):** `POST /authoring/candidates/{id}/approve` refuses any candidate that has not passed validation; `/reject` and `/edit` (new revision, superseded version retained) keep AI output a draft that the author owns.
- **Distinguishable library (§9, §10):** `AuthoringCandidateStore.approved_practices()` returns only approved content; provenance (brief, generation time, provider/model, version, reviewer, decision, revision history) is retained internally and never exposed to learners.
- **Learner isolation (§16, §18):** authoring requires no learner personal data, and the learner-facing experience is unchanged — approved content only ever enters through the ordinary curated library.

### LLM Provider Adapter Boundary (ARCH-001)

The authoring workflow depends on a provider-neutral LLM port rather than a specific LLM vendor, so provider credentials, request/response handling, structured generation, and provider failures stay inside one adapter boundary.

```text
SPEC-032 Authoring Workflow
        ↓ depends on
AuthoringLlmProvider (port)         fablit/application/authoring_llm.py
        ↓ implemented by
GeminiAuthoringProvider (adapter)   fablit/platform/gemini_authoring_provider.py
        ↓
Google Gemini REST API
```

- **Provider-neutral port:** `fablit/application/authoring_llm.py` defines the `AuthoringLlmProvider` protocol, the structured `AuthoringGenerationRequest`, and the structured `LlmGenerationResult` (candidate output plus provider/model metadata). The workflow imports no provider SDK.
- **One concrete adapter:** `fablit/platform/gemini_authoring_provider.py` implements the port against the Google Gemini REST API. It owns the API key (sent only as a server-side `x-goog-api-key` header, never in a URL, log line, or response), request construction, response parsing, and provider/model identity for SPEC-032 §10 provenance.
- **Structured results validated by SPEC-032:** the adapter returns the candidate as a structured mapping that flows into the existing SPEC-029/SPEC-030 validation. Valid JSON that omits contract fields becomes a non-approvable candidate rather than being silently accepted.
- **Clean failure translation:** configuration gaps and provider/transport failures become `AuthoringProviderConfigurationError` / `AuthoringProviderError`; the workflow maps them to a safe `502` and never creates learner-facing content, so AI availability is never a dependency of ordinary learner practice.
- **Composition-root wiring:** `app/main.py` builds the adapter only when `FABLIT_AI_PROVIDER_API_KEY` is configured (model selected via `FABLIT_AI_PROVIDER_MODEL`); otherwise the workflow uses the brief-derived draft path.
- **Testable without live calls:** `FakeAuthoringProvider` (shipped beside the port) and an injectable adapter transport let the suite exercise the workflow with no external API call. SEC-001 remains the access-control boundary for every authoring route.
- **Deliberately out of scope:** multi-provider routing, provider fallback, model-selection logic, agent frameworks, and learner-facing AI.

### AI-Assisted Brief Drafting (SPEC-040)

SPEC-040 adds a second, smaller AI operation to the same authoring workspace: an
author with only partial notes can ask Fablit to draft the brief itself, then
review and edit every field before the unchanged candidate flow begins.

```text
Authoring form (notes + current brief values)
        ↓ POST /authoring/brief/draft            (SEC-001 protected)
BriefDraftingRequest → AuthoringLlmProvider.draft_brief(...)
        ↓ provider-neutral port, existing Gemini adapter / fake provider
Untrusted structured draft (values · source · assumptions)
        ↓ parse_brief_draft(...)  existing fields, allowed values, bounds
Editable brief form + provenance markers + per-field regeneration
        ↓ author confirms
Existing POST /authoring/generate (candidate generation, unchanged)
```

- **No new model or store:** `fablit/application/authoring_brief_draft.py` describes the draft (`BriefDraft`, `BriefFieldProposal`, `BriefFieldSource`) using the existing brief field names and the existing `PracticeMode` / `PRACTICE_CAPABILITIES` allowed values. Nothing is persisted; the draft is rendered into the existing editable form.
- **Same provider boundary, one new operation:** `BriefDraftingRequest` and `AuthoringLlmProvider.draft_brief(...)` extend `fablit/application/authoring_llm.py`, implemented by the existing Gemini adapter and the deterministic fake. Provider credentials, request construction, and response parsing stay inside the adapter (ARCH-001); the notes are delimited as untrusted data, not instructions.
- **Provenance is visible:** each applied value carries `notes` / `suggested` / `assumed`, and generated examination context is always downgraded to an assumption to confirm (SPEC-040 §6, AC-5). The assumptions and refused values are shown above the form.
- **Regeneration preserves work:** a single-field regeneration replaces exactly one field and keeps every other submitted value; a whole-brief draft only fills empty fields unless the author ticks “Replace my current field values”. The notes are part of the form, so they survive every action.
- **Fail safe:** provider failure, timeout, malformed output, and validation errors keep the notes and current values, return `502`/`503`, and expose no credentials or raw provider payloads. Duplicate submissions are dropped while a request is in flight (`hx-sync`), with a truthful in-progress label.
- **Separate from the lifecycle:** `/authoring/brief/draft` never creates, approves, or publishes a candidate; the existing generate, review, and publication gates and learner routes are untouched.

### Shared Candidate State & Production Authoring Persistence (FIX-7 / SPEC-032)

In multi-instance production environments (such as Google App Engine), active authoring candidate state, revisions, and approval decisions must be shared consistently across instances without exposing draft content to learner journeys.

```text
Authoring Router (app/authoring.py)
        │
        ▼
AuthoringCandidateStore (app/authoring.py)
        │
        ├── In-Memory Store (InMemoryAuthoringCandidateStore) [local / testing]
        │
        └── Datastore Store (DatastoreAuthoringCandidateStore) [production / multi-instance]
                └── Google Cloud Datastore (namespace="authoring", kind="AuthoringCandidate")
```

- **Shared persistence adapter:** `fablit/platform/datastore_authoring_store.py` provides `DatastoreAuthoringCandidateStore`, which connects via the official Datastore client and serializes candidate briefs, contracts, diagnostics, revision history, and review states.
- **Namespace isolation:** all authoring candidate entities are isolated within the `authoring` namespace, completely separate from learner data (such as default namespace `PracticeCompletion` entities). Learner practice routes never query the authoring store.
- **Retention & lifetime policy:** unapproved candidates expire after `authoring_candidate_retention_days` (default 30 days, integer $\ge 1$), after which retrieval raises `CandidateNotFoundError` (HTTP 404) and candidate listing excludes them. Approved candidates are preserved indefinitely for curated library handoff.
- **Fail-safe mutation handling:** persistence failures are translated to `PersistenceError` and mapped to HTTP `503 Service Unavailable`, guaranteeing that storage failures never report false success.

## Publication to the Learner Library (SPEC-035)

SPEC-035 completes the handoff from the human-reviewed authoring workflow to the existing learner-facing curated library. Approval and publication are distinct decisions: *approved* means a reviewer accepted the content quality, *published* means the approved content has been deliberately made discoverable to learners.

```text
Approved Practice Candidate (SPEC-032)
        ↓ POST /authoring/candidates/{id}/publish   (SEC-001 protected)
Publication gate: revalidate content + approval state
        ↓
PublishedPractice  (existing DemoActivity + internal provenance)
        │
        ├── InMemoryPublishedPracticeStore  [local / testing]
        │
        └── DatastorePublishedPracticeStore [production / multi-instance]
                └── Google Cloud Datastore (namespace="library", kind="PublishedPractice")
        ↓ only after the write succeeds
LearnerApplicationRegistry.record_publication(...)
        ↓ reconciled on each learner request
Dashboard / Full Practice → Practice → Evaluation → Feedback → Reflection
```

- **Publication boundary (`fablit/application/publishing.py`):** `publish_candidate(...)` is written against the `PublishableCandidate` contract (satisfied by both candidate models), revalidates SPEC-029/SPEC-030 content and the approval state, and refuses generated, rejected, invalid, and edited-but-not-reapproved candidates (`CandidateNotPublishableError` → 409, `CandidateContentNotPublishableError` → 422).
- **Existing learner representation:** a published practice is a `DemoActivity` / `AssessmentActivity` (written response, prompt taken from the approved contract's task, qualitative evaluation guidance derived from the approved contract). No parallel learner practice model is introduced, and no provenance is learner-facing.
- **Idempotent, stable identity:** publishing the same approved revision twice returns the existing record; republishing a re-approved revision replaces content in place under the same activity identity, so catalogue entries never duplicate and completed learner history keeps pointing at the same practice.
- **Publication persistence (§5):** `PublishedPracticeStore` is an application port with `InMemoryPublishedPracticeStore` and `DatastorePublishedPracticeStore` (kind `PublishedPractice`, namespace `library`); `FABLIT_PUBLISHED_PRACTICE_STORE` selects the backend (`memory` by default, `datastore` in `app.yaml`). Write failures surface as `PersistenceError` → HTTP 503, and the learner catalogue is updated only after a successful write.
- **Runtime reconciliation:** `LearnerApplicationRegistry` owns the published set and `PracticeApplication.apply_publications(...)` reconciles it into each learner application on the next request (dashboard, Full Practice eligibility, evaluator activity map). Only shared catalogue content changes — in-flight learner journey state is never rebuilt or discarded.
- **Withdrawal policy (§8):** `POST /authoring/candidates/{id}/withdraw` hides the practice from learner discovery (dashboard and practice modes) while the activity stays resolvable so in-flight practice finishes, completed history stays readable, and the publication record is retained; an explicit republish restores the same identity.
- **Availability boundary (§9, §10):** a publication store that cannot be read at startup degrades to the seeded library (logged, never fatal) so learner practice never depends on the authoring workflow, and every publish/withdraw action remains behind SEC-001.

## Curated Fashion & Design Intelligence Feed (SPEC-041)

SPEC-041 adds a small, curated current-affairs feed for all learners. It is an
independent application slice: it reuses the Gemini/Datastore infrastructure
where practical, but it never changes the practice-authoring provider contract
or the practice-publication lifecycle.

```text
Approved sources (explicit allowlist)
        ↓ on-demand operator action (SEC-001 protected)
POST /authoring/pulse/curate
        ↓ persist before acknowledgement (SPEC-042)
NewsCurationJob → NewsCurationJobRepository
        ├── InMemoryNewsCurationJobRepository  [local / testing]
        └── DatastoreNewsCurationJobRepository [production: kind="NewsCurationJob"]
        ↓ durable dispatch (Cloud Tasks in production)
POST /tasks/news-curation (independent OIDC task identity)
        ↓ lease + bounded unit of work
Application NewsCurator
   fetch (bounded) → normalize → allowlist/URL safety → dedupe
        → freshness/field checks → AI curation (news port)
        → schema/category/relevance/grounding checks
        ↓ only after every check passes
NewsStory → NewsRepository
        ├── InMemoryNewsRepository   [local / testing]
        └── DatastoreNewsRepository  [production: kind="NewsStory", namespace="news"]
        ↓
GET /pulse (persisted stories only; no live AI or network)
```

- **Application workflow (`fablit/application/news.py`):** owns source iteration, normalization, canonical URL deduplication, freshness and field checks, provider invocation, result validation, publication, and batch reporting (`fetched`, `deduplicated`, `published`, `rejected`, `failed`). It imports no Gemini SDK, Datastore SDK, FastAPI object, or credential store.
- **News-specific AI port (`fablit/application/news_curation.py`):** `NewsCurationProvider`, `NewsCurationRequest`, and `NewsCurationResult` are separate from `AuthoringLlmProvider`. `fablit/platform/gemini_news_curation_provider.py` implements the port with the existing server-side key/model; `FakeNewsCurationProvider` keeps tests deterministic.
- **News-specific persistence (`NewsRepository`):** `InMemoryNewsRepository` for tests/local development and `DatastoreNewsRepository` in kind `NewsStory`, namespace `news`. It is separate from practice history, authoring candidates, and published practices. Stories are written under a stable URL-derived identity and never bulk-replaced, so a failed or empty refresh leaves the existing feed intact.
- **Source and URL safety (`fablit/application/news_sources.py`, `fablit/platform/news_source_fetcher.py`):** an explicit source allowlist, publisher-host matching, public-HTTP(S)-only URLs, DNS/redirect validation, bounded timeouts and response sizes, RSS/Atom parsing, and markup stripping. Source content is untrusted and delimited in the AI prompt; no full article or imagery is stored.
- **Learner surface (`GET /pulse`):** renders persisted stories newest first with attribution, canonical link, date when reliable, summary, controlled categories, educational relevance, and an optional reflection prompt, plus lightweight category filtering, a calm empty state, and graceful degradation when the news store is unavailable. It never invokes Gemini or fetches a source.
- **Operator surface (`GET /authoring/pulse`, `POST /authoring/pulse/curate`, `GET /authoring/pulse/jobs/*`):** behind SEC-001, on demand only — no GitHub Actions schedule or scheduled refresh, and no separate worker application. Unauthorised requests are refused before any source retrieval or AI call; a start is refused while a job is queued or running, and repeated runs are idempotent.
- **Durable job lifecycle (`fablit/application/news_jobs.py`, SPEC-042):** a validated immutable `NewsCurationJob` with explicit `queued → running → succeeded | partially_succeeded | failed` transitions, progress stages that are only reported once reached, cumulative counters, attempt/lease metadata, a bounded safe diagnostic, and the accumulated batch report. `NewsCurationJobRepository.start` and `.claim` are atomic (transactional in Datastore), so at most one job is active and at most one worker owns it; terminal outcomes cannot be rewritten.
- **Retry observability and diagnostics (`fablit/platform/gemini_news_curation_provider.py`, `fablit/application/news.py`, SPEC-042 Task 3):** transient Gemini rate-limiting and service availability errors (HTTP 429/503) are retried with bounded exponential backoff and `Retry-After` parsing (capped at 10s); non-retryable errors fail immediately. The batch report and job status distinguish transient recovery (`NewsProviderOutcome.RECOVERED`) from terminal exhaustion (`RETRIES_EXHAUSTED` / `FAILED`), record `provider_retries` counters, and expose structured `NewsCurationDiagnostics` without leaking secrets, credentials, prompts, or raw payloads.
- **Dispatch and task security (`fablit/platform/cloud_tasks_dispatcher.py`, `fablit/platform/task_auth.py`, `POST /tasks/news-curation`):** the job is persisted before the task is enqueued, a dispatch failure is stored as a failed job and reported truthfully, and the handler accepts only a Google-signed OIDC token for the configured audience and service account — never an author cookie or session. The browser is not part of the durability guarantee.
- **Bounded execution and recovery:** one task unit processes at most `FABLIT_NEWS_MAX_SOURCES_PER_TASK` approved sources; the rest is checkpointed (report, counters, next source index) and continued in a fresh unit. Duplicate delivery during a live lease is a no-op, a delivery after a terminal outcome returns the finished job, an expired lease can be taken over, and a stale active job is closed as `interrupted` by the next start rather than blocking curation forever.
- **Editorial imagery and attribution (SPEC-043, `fablit/application/news_images.py`):** a curated story may carry one illustrative stock image. `derive_visual_query` turns the story's own headline, summary, and controlled category into a short subject query; `NewsImageSelector` runs the existing provider-neutral `ImageSearchProvider` port (the same Pexafy adapter and configuration as practice authoring) with a bounded result count; `select_story_image` keeps only candidates with validated public URLs, usable dimensions, a non-extreme aspect ratio, and a relevant description, and returns no image when the match is weak. Selection happens only inside `NewsCurator` — never on a learner request — and a failure, empty result set, or unsuitable candidate leaves the story text-only with a safe logged reason. `StoryImage` is persisted through `NewsRepository` as non-indexed provenance (provider, source page, creator/attribution, alt text, asset id), and `GET /pulse` renders it responsively with a separate illustrative-image credit; stories without imagery keep a balanced text-first card.

## Private Story-Linked Responses (SPEC-044)

SPEC-044 adds a lightweight, private response path for the "What to try"
prompt on a Fashion & Design Pulse story. It is deliberately separate from
formal practice: saving a response is private capture, never an evaluation,
score, mastery signal, or practice completion.

```text
GET /pulse story card with a reflection prompt
        ↓ explicit "Try this" action
POST /pulse/stories/{story_id}/responses
        ↓ require prompt · bound and normalize learner text
StoryResponse (domain: learner · story · headline · source · URL · prompt · text)
        ↓ StoryResponseRepository
        ├── InMemoryStoryResponseRepository   [local / testing]
        └── DatastoreStoryResponseRepository  [production: kind="StoryResponse",
                                               namespace="story-responses"]
        ↓
GET /history (private list) → GET /history/story-responses/{response_id}
```

- **Application workflow (`fablit/application/story_responses.py`):** validates and bounds learner text, requires a story prompt, preserves headline/source/canonical URL/prompt provenance, and derives a stable response identity from the learner and the composer's idempotency token. It imports no provider SDK, Datastore SDK, or FastAPI object.
- **Private persistence (`StoryResponseRepository`):** `InMemoryStoryResponseRepository` for tests/local development and `DatastoreStoryResponseRepository` in its own kind and namespace. `save` executes its read-then-create check inside a Datastore transaction (and verifies learner ownership if the record already exists), so concurrent duplicate submissions resolve to the same durable `StoryResponse` without overwriting or leaking across learners. Listing is scoped by the current opaque learner identity, retrieval checks ownership, and response text is stored unindexed so a long note cannot fail the write. A storage failure is raised as `PersistenceError` and never reported as a save.
- **No AI on the capture path:** `POST /pulse/stories/{story_id}/responses` never calls the authoring or news-curation provider. A response is saved only on explicit learner action, and no completion, evaluation, feedback, or reflection record is created.
- **Honest failure and retry safety:** invalid input re-renders the composer in place with actionable copy and the learner's words preserved; a persistence failure returns an honest error and also preserves the draft; the hidden idempotency token is retained across retries, so resubmitting the same form cannot create duplicates.
- **Learner surfaces (`app/templates/news.html`, `app/templates/history.html`, `app/templates/story_response_review.html`):** a story with a prompt offers an inline, keyboard-accessible "Try this" composer; a saved response appears in the learner's private history with its story headline and prompt, and can be reopened with its source attribution and canonical story link. Story responses are visually distinct from completed practice and never counted as one.

## Learner-Requested Private Practice (SPEC-044)

SPEC-044 also lets a learner ask for practice directly: a short free-text
intent, a few plain-language choices, and an explicit submit action. Generation
runs behind a provider-neutral port, the untrusted output passes the existing
SPEC-029/SPEC-030 validation boundary before the learner sees it, and the
validated practice is persisted privately and revisited from the learner's own
request list.

```text
GET /practice/request (composer + this learner's requested practices)
        ↑ optional prefill: GET /practice/request?story={story_id}
          carries a Pulse story's "What to try" prompt as editable starter
          text, with a link back to the story (SPEC-044 §6.1)
        ↓ explicit POST /practice/request (bounded request + idempotency token)
PracticeRequest → PracticeArea · response form · challenge · optional exam context
        ↓ optional: this learner's own recent titles/areas only
LearnerPracticeGenerator (provider-neutral port)
        ↓ untrusted candidate output
candidate_from_provider_output + SPEC-029/SPEC-030 validation
        ↓
GeneratedPracticeRecord (validated contract · preferences · safe provenance)
        ↓ GeneratedPracticeRepository
        ├── InMemoryGeneratedPracticeRepository   [local / testing]
        └── DatastoreGeneratedPracticeRepository  [production: kind="GeneratedPractice",
                                                   namespace="learner-practices"]
        ↓ 303 See Other
GET /practice/request/{practice_id} (validated brief) → ordinary practice journey
```

- **Application workflow (`fablit/application/learner_practice.py`):** `PracticeRequest` and `HistoryContext` validate and bound learner input before any provider call; `generate_private_practice` derives a stable practice identity from the learner and the composer token, returns any already persisted practice for that token first (idempotent retry even at the rate limit), atomically claims `(learner_id, practice_id)` via `GeneratedPracticeRepository.claim_generation` with a unique `claim_token` and bounded lease TTL (`FABLIT_LEARNER_PRACTICE_CLAIM_TTL_SECONDS`, default `60`s) before reserving a rate-limit slot or calling the generation port, periodically renews the lease via `renew_generation_claim` while generation is active, and completes or releases the claim using the matching `claim_token` (concurrent duplicate submissions await the in-flight claim via `await_generation`; if an expired worker loses its lease to a replacement claim, its stale `complete_generation_claim` / `release_generation_claim` cannot clobber the replacement and instead awaits the replacement's durable record), reserves a per-learner rate-limit slot (`LearnerPracticeRateLimitError` when exhausted), validates the result through `candidate_from_provider_output`, and only then persists. It imports no provider SDK, Datastore SDK, or FastAPI object.
- **Per-learner rate limit (SPEC-044 §11 / Issue #177):** `GeneratedPracticeRepository.reserve_generation_slot` enforces a rolling window per learner (configured via `FABLIT_LEARNER_PRACTICE_RATE_LIMIT`, default `5`, and `FABLIT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS`, default `3600` seconds). In production, `DatastoreGeneratedPracticeRepository` updates a per-learner `GeneratedPracticeRateLimit` entity inside a Datastore transaction in the `learner-practices` namespace so the limit is shared across App Engine instances without relying on in-process memory. When the limit is reached, `POST /practice/request` returns HTTP `429 Too Many Requests` with `Retry-After`, preserves the learner's form inputs, and never invokes the AI provider.
- **History context stays minimal:** `PracticeApplication.get_history_context` reads up to five of the learner's own completed practice summaries and resolves each activity's capability lens — titles and areas only. Responses, reflections, artifacts, and other learners' records are never read, and an unavailable history store degrades to no context instead of blocking the request.
- **Provider adapter (`fablit/platform/gemini_learner_practice_provider.py`):** Gemini behind the same server-side key as authoring, with the learner request delimited as untrusted data, no learner identity in the payload, a JSON response mode, a conservative output-token ceiling (`maxOutputTokens`, default `4096` via `FABLIT_LEARNER_PRACTICE_MAX_OUTPUT_TOKENS`), an explicit response-body byte limit enforced before JSON parsing (`max_response_bytes`, default `65536` bytes via `FABLIT_LEARNER_PRACTICE_MAX_RESPONSE_BYTES`), and a short bounded retry for transient 429/503 capacity errors. Oversized, truncated, or malformed responses translate to `LearnerPracticeGenerationError` without leaking credentials or raw payloads. Without a configured key the composition root offers no generator and the composer explains that requests are unavailable, rather than fabricating practice.
- **Private persistence (`GeneratedPracticeRepository`):** `InMemoryGeneratedPracticeRepository` for tests/local development and `DatastoreGeneratedPracticeRepository` in its own kind and namespace. Pre-generation claims use a bounded-lease `GeneratedPracticeClaim` entity carrying a unique `claim_token` inside a Datastore transaction (so crashed workers do not block retries after lease expiry, while active workers renew their lease and stale expired workers cannot release, renew, or overwrite a replacement claim; if a worker's process is paused longer than the lease TTL and heartbeat renewal cannot run, a replacement worker may take over the claim, and the stale worker's completion is rejected with `StaleGenerationClaimError` so both resolve to the replacement's single persisted record), and `complete_generation_claim` / `save` transactionally verifies learner ownership and `claim_token`, creates the `GeneratedPractice` entity if absent, and clears the matching claim. The whole practice payload is stored unindexed — the embedded contract entity included — so a long generated task cannot fail the write; listing is scoped and ordered by the current learner, and retrieval checks ownership. A storage failure surfaces as `PersistenceError` and is never reported as a generated practice.
- **Reusing the learner journey (`PracticeApplication.apply_generated_practices`):** a requested practice is registered as a non-discoverable `DemoActivity`, so it never appears in the shared dashboard or practice-mode selections but runs the unchanged intention → practice → feedback → reflection → completion flow. The deterministic evaluator is rebuilt when the set changes, and re-applying the same set is a no-op.
- **Learner surfaces (`app/templates/practice_request.html`, `app/templates/requested_practice.html`, `GET /practice/request/{practice_id}`):** the brief shows the task, purpose, expected thinking, response form, preferences, and any learner-stated examination context before the learner chooses to begin. The composer is reachable from the dashboard and the practice-mode choice, and lists the practices this learner has requested. A Pulse story with a "What to try" prompt offers "Make this a practice" (SPEC-044 §6.1), which resolves the story through the `NewsRepository` port and prefills only its prompt plus reader-facing provenance; a missing story, a story without a prompt, or an unavailable feed leaves the composer empty, and nothing about the story narrows the learner's area or challenge choice.
- **Honest failure:** invalid requests and invalid generated content are refused with plain-language copy that keeps the learner's words; generation and persistence failures return an honest message and never leave a half-made practice in the request list.

---

## Progress

Progress records learner development across Skill Labs.

Progress includes:

- completed activities
- completed assessments
- streaks
- achievements
- skill development history

Progress is platform-wide.

---

## Content Packs

Content Packs organize educational material around a particular purpose.

Examples:

- NIFT Foundation
- NID Preparation
- CEED Preparation
- Fashion Communication
- Research Methodology

Content Packs reuse Skill Labs rather than duplicating platform functionality.

---

# Platform Relationships

```
Content Pack

        │

        ▼

 Skill Lab

        │

        ▼

 Assessment

        │

        ▼

Assessment Activities

        │

        ▼

 Submission

        │

        ▼

 Evaluation

        │

        ▼

 Feedback

        │

        ▼

 Reflection

        │

        ▼

 Progress
```

---

# Architectural Boundaries

Platform Core owns:

- authentication
- users
- progress
- analytics
- notifications
- AI infrastructure

Skill Labs own:

- exercises
- rubrics
- activity types
- learning resources

Content Packs own:

- curriculum
- sequencing
- recommendations

Assessment Activities own:

- learner interaction
- submission requirements

---

# Extension Points

Fablit is designed to evolve through extension rather than modification.

Future extensions include:

- additional Skill Labs
- additional Assessment Activity types
- AI evaluation providers
- custom Content Packs
- institution-specific plugins
- multilingual content

---

# Guiding Constraints

The platform should remain:

- modular
- technology-independent
- content-driven
- testable
- contributor-friendly
- AI-assisted
- open source

---

# Architectural Layers

```
Vision

↓

Architecture

↓

Platform

↓

Skill Labs

↓

Assessment Activities

↓

Content Packs

↓

Learners
```

---

# Future Architecture

This blueprint intentionally leaves implementation details unspecified.

Separate ADRs define:

- technology stack
- deployment
- database
- frontend
- plugin architecture
- development workflow

---

# Closing Statement

The Fablit architecture is designed around learning rather than software.

The platform should continue to evolve through modular extensions while preserving a stable conceptual model centered on practice, assessment, feedback, reflection, and continuous improvement.
