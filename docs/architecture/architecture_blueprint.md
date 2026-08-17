# Fablit Architecture Blueprint

**Document ID:** AB-001
**Version:** 0.5.0
**Status:** Draft
**Last Updated:** 2026-08-17

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

- strengths
- improvement suggestions
- rubric scoring
- learning recommendations
- follow-up activities

Feedback prioritizes learning over grading.

SPEC-008 implements the Feedback concept as an in-memory learning-domain model (`fablit.domain`), independent of the Platform Core. Feedback references the Evaluation by stable identity (SPEC-007), carries a single general learner-facing content field, records a timezone-aware creation timestamp, and is immutable after creation. Scoring, Reflection, feedback-generation mechanisms, AI providers, and persistence are deliberately excluded from the model.

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
- **Reference activity (§56–58):** the existing "Visual Analysis — Composition" activity is upgraded to the reference implementation of the stimulus + response-aware evaluation flow, with three of the five demo activities now presenting bundled visual stimuli.
- **No new persistence dependency (§46):** the in-memory journey store retains stimulus metadata and evaluation results for the activity instance, so no production database is introduced.
- **No scoring or gamification (§4, §37):** SPEC-015 deliberately introduces no points, grades, rankings, or AI evaluation platform; the evaluator is the smallest viable response-aware implementation, and future rule-based, AI-assisted, or hybrid evaluators can implement the same contract (§28, §60).

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
