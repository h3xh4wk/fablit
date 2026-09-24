# Fablit Domain Language

**Document ID:** DL-001
**Version:** 1.4.0
**Status:** Draft
**Last Updated:** 2026-09-23

---

# Purpose

This document defines the ubiquitous language of the Fablit platform.

Every architectural document, specification, source file, API, database model, user interface, and discussion should use these terms consistently.

If a concept is not defined here, contributors should avoid introducing new terminology until the domain has been reviewed.

---

# Domain Philosophy

Fablit is a platform for developing skills through deliberate practice.

The platform models learning rather than examinations.

Every domain concept should contribute to one or more stages of the learning cycle.

```
Practice
    ↓
Assessment
    ↓
Evaluation
    ↓
Feedback
    ↓
Reflection
    ↓
Improvement
```

---

# Core Domain Concepts

## Learner

A Learner is a person using Fablit to improve one or more skills.

The Learner is the central participant in every learning experience.

A learner may participate in multiple Skill Labs and Content Packs simultaneously.

---

## Skill

A Skill is a measurable capability that can be developed through deliberate practice.

Examples include:

- Writing
- Observation
- Communication
- Creativity
- Critical Thinking
- Interview Performance

Skills evolve over time and are reflected through learner progress.

---

## Skill Lab

A Skill Lab is a modular learning experience focused on developing one or more related skills.

A Skill Lab contains:

- Assessments
- Learning Resources
- Evaluation Strategies
- Feedback Strategies
- Reflection Activities

Examples:

- Writing Lab
- Creativity Lab
- Interview Lab
- Observation Lab

Skill Labs are reusable across multiple Content Packs.

---

## Assessment

An Assessment is a structured learning experience composed of one or more Assessment Activities.

Examples include:

- Daily Practice
- Mock Test
- Timed Challenge
- Portfolio Review
- Weekly Evaluation

An Assessment defines:

- objectives
- activity sequence
- completion criteria
- evaluation rules

---

## Assessment Activity

An Assessment Activity is the smallest meaningful interaction between the learner and the platform.

Every Assessment Activity expects a learner response.

Examples include:

- Multiple Choice Question
- Writing Exercise
- Sketch Submission
- Observation Exercise
- Interview Recording
- Reflection Prompt

Assessment Activities are reusable building blocks.

---

## Assessment Domain Model (SPEC-005)

SPEC-005 establishes the in-memory learning-domain foundation for Assessments and Assessment Activities.

The implementation lives in `fablit.domain` and is intentionally independent of platform infrastructure, persistence, and examination-specific concepts.

### Relationship

```
Assessment
    │
    ├── Activity 1 (position 0)
    ├── Activity 2 (position 1)
    ├── Activity 3 (position 2)
    └── ...
```

An Assessment owns its Assessment Activities. Activities carry an explicit zero-based position, and the positions within an Assessment must form a complete sequential range with no duplicates.

### Domain Rules Reference

The following rules are enforced by the SPEC-005 domain model:

| Rule | Description |
|------|-------------|
| DR-001 | An Assessment must have a unique identity. |
| DR-002 | An Assessment Activity must have a unique identity. |
| DR-003 | An Assessment must contain at least one Assessment Activity. |
| DR-004 | An Assessment Activity belongs to one Assessment. |
| DR-005 | Assessment Activities have deterministic ordering within an Assessment. |
| DR-006 | Activity ordering must not contain duplicate positions. |
| DR-007 | An Assessment Activity must declare a valid activity type. |
| DR-008 | An Assessment Activity must contain sufficient information to describe the learner interaction. |
| DR-009 | Assessment and Assessment Activity remain independent of examination-specific terminology. |
| DR-010 | The domain model must not require persistence infrastructure. |

### Activity Types

The initial controlled set of Activity Types (extensible through future specifications):

- Multiple Choice
- Written Response
- Observation
- Reflection

---

## Submission Domain Model (SPEC-006)

SPEC-006 establishes the in-memory Submission domain model for the learner's response to an Assessment Activity.

The implementation lives in `fablit.domain` and is intentionally independent of platform infrastructure, persistence, evaluation, feedback, and examination-specific concepts.

### Relationship

```
Assessment
    │
    └── Assessment Activity
              │
              │ receives
              ▼
          Submission
              ▲
              │
              │ produced by
              │
           Learner
```

A Submission references a Learner and an Assessment Activity by stable identity only. It never duplicates the activity definition.

### Lifecycle

The initial Submission lifecycle is intentionally small:

```
Draft
  │
  │ submit
  ▼
Submitted
```

A Draft may be incomplete. Submitting a Draft requires a learner response, records the submission timestamp, and produces an immutable Submitted Submission whose core response and associations cannot be silently modified.

### Domain Rules Reference

The following rules are enforced by the SPEC-006 domain model:

| Rule | Description |
|------|-------------|
| DR-001 | A Submission must have a unique identity. |
| DR-002 | A Submission must identify a learner. |
| DR-003 | A Submission must identify an Assessment Activity. |
| DR-004 | A Submission must contain a response appropriate to its lifecycle state. |
| DR-005 | A Draft Submission may be incomplete. |
| DR-006 | A Submitted Submission must contain the required learner response. |
| DR-007 | A Submitted Submission must contain a submission timestamp. |
| DR-008 | A Submitted Submission shall not allow silent modification of its core learner response or associations. |
| DR-009 | A Submission shall reference an Assessment Activity by identity. |
| DR-010 | A Submission shall not contain evaluation results. |
| DR-011 | A Submission shall not contain feedback. |
| DR-012 | A Submission shall not require persistence infrastructure. |
| DR-013 | A Submission shall not contain examination-specific concepts. |

### Response Representation

A Submission carries a generic, extensible learner response. SPEC-006 deliberately avoids a premature hierarchy of submission types; richer response forms (multiple-choice selections, structured responses, artifact references) may be introduced by future specifications without redesigning the Submission aggregate.

---

## Evaluation Domain Model (SPEC-007)

SPEC-007 establishes the in-memory Evaluation domain model for the structured interpretation of a learner's Submission.

The implementation lives in `fablit.domain` and is intentionally independent of platform infrastructure, persistence, evaluation mechanisms, AI providers, feedback, and examination-specific concepts.

### Relationship

```
Submission
    │
    │ evaluated
    ▼
Evaluation
    │
    ├── Finding
    ├── Finding
    └── ...
```

An Evaluation references exactly one Submission by stable identity (SPEC-006). It never duplicates the Submission. Each Evaluation contains one or more structured Findings, each with a stable identity so it can be referenced without relying on collection position.

### Lifecycle

The Evaluation lifecycle is intentionally minimal:

```
Evaluation (immutable record)
```

An Evaluation is created complete and immutable: its Submission association, Findings, identity, and evaluation timestamp cannot be silently modified. If a Submission requires another evaluation, a new Evaluation is created rather than mutating an existing one.

### Domain Rules Reference

The following rules are enforced by the SPEC-007 domain model:

| Rule | Description |
|------|-------------|
| DR-001 | An Evaluation must have a unique identity. |
| DR-002 | An Evaluation must reference exactly one Submission. |
| DR-003 | An Evaluation must contain at least one structured Finding. |
| DR-004 | A Finding must contain sufficient information to represent a meaningful observation or judgement. |
| DR-005 | An Evaluation must record when it occurred. |
| DR-006 | An Evaluation is immutable after creation. |
| DR-007 | Creating an Evaluation must not modify its Submission. |
| DR-008 | An Evaluation does not require a numerical score. |
| DR-009 | An Evaluation must not contain Feedback. |
| DR-010 | An Evaluation must not depend on a specific evaluation mechanism. |
| DR-011 | An Evaluation must not contain examination-specific concepts. |
| DR-012 | An Evaluation must not require persistence infrastructure. |

### Finding Structure

A Finding is deliberately not a score. Each Finding carries a meaningful observation or judgement about the learner's work and a stable identity. The initial structure is intentionally small and extensible; richer Finding dimensions (criteria references, categories) may be introduced by future specifications without redesigning the Evaluation aggregate.

SPEC-015 adds one optional dimension: **evidence** — a response excerpt or matched concept that grounds the Finding in the learner's actual response (response-aware evaluation). Evidence must be a non-blank string when present, and is deliberately optional so predefined Findings remain valid.

---

## Feedback Domain Model (SPEC-008)

SPEC-008 establishes the in-memory Feedback domain model for learner-facing guidance derived from an Evaluation.

The implementation lives in `fablit.domain` and is intentionally independent of platform infrastructure, persistence, feedback-generation mechanisms, AI providers, scoring, Reflection, and examination-specific concepts.

### Relationship

```
Evaluation
    │
    │ interpreted for learner
    ▼
Feedback
    │
    │ enables
    ▼
Reflection (future specification)
```

Feedback references exactly one Evaluation by stable identity (SPEC-007). It never duplicates the Evaluation. Feedback is the learner-facing interpretation derived from the Evaluation's structured findings; it is not merely a copy of those findings exposed to the learner.

### Lifecycle

The Feedback lifecycle is intentionally minimal:

```
Feedback (immutable record)
```

Feedback is created complete and immutable: its Evaluation association, content, identity, and creation timestamp cannot be silently modified. If new or revised feedback is required, a new Feedback instance is created rather than mutating an existing one.

### Content Representation

Feedback carries a single, general learner-facing content field. SPEC-008 deliberately avoids a premature hierarchy of feedback categories; separate fields for strengths, improvement areas, next steps, and reflection prompts may be introduced by future specifications without redesigning the Feedback aggregate.

### Domain Rules Reference

The following rules are enforced by the SPEC-008 domain model:

| Rule | Description |
|------|-------------|
| DR-001 | Feedback must have a unique identity. |
| DR-002 | Feedback must reference exactly one Evaluation. |
| DR-003 | Feedback must contain at least one meaningful learner-facing piece of guidance. |
| DR-004 | Feedback content must not be empty or whitespace-only. |
| DR-005 | Feedback must record when it was created. |
| DR-006 | Feedback is immutable after creation. |
| DR-007 | Creating Feedback must not modify its Evaluation. |
| DR-008 | Feedback does not require a numerical score. |
| DR-009 | Feedback must not contain learner Reflection. |
| DR-010 | Feedback must not depend on a specific generation mechanism. |
| DR-011 | Feedback must not require persistence infrastructure. |
| DR-012 | Feedback must not contain examination-specific concepts. |

---

## Reflection Domain Model (SPEC-009)

SPEC-009 establishes the in-memory Reflection domain model for the learner's deliberate response to Feedback.

The implementation lives in `fablit.domain` and is intentionally independent of platform infrastructure, persistence, reflection-generation mechanisms, AI providers, scoring, improvement goals, Progress, and examination-specific concepts.

### Relationship

```
Feedback
    │
    │ prompts
    ▼
Reflection
    │
    │ supports
    ▼
Improvement (future specification)
```

A Reflection references exactly one Feedback by stable identity (SPEC-008). It never duplicates the Feedback. Reflection is the learner's own response to the Feedback they received; it is not another Evaluation and it is not a copy of the Feedback.

### Lifecycle

The Reflection lifecycle is intentionally minimal:

```
Reflection (immutable record)
```

A Reflection is created complete and immutable: its Feedback association, content, identity, and creation timestamp cannot be silently modified. If the learner reflects again later, a new Reflection instance is created rather than mutating an existing one, preserving the learner's evolving understanding over time.

### Content Representation

Reflection carries a single, general learner-authored content field. SPEC-009 deliberately avoids a premature hierarchy of reflection fields; separate fields for self-assessment, confidence, learning goals, improvement goals, action plans, next steps, and learning notes may be introduced by future specifications without redesigning the Reflection aggregate.

### Domain Rules Reference

The following rules are enforced by the SPEC-009 domain model:

| Rule | Description |
|------|-------------|
| DR-001 | Reflection must have a unique identity. |
| DR-002 | Reflection must reference exactly one Feedback. |
| DR-003 | Reflection must contain learner-authored content. |
| DR-004 | Reflection content must not be empty or whitespace-only. |
| DR-005 | Reflection must record when it was created. |
| DR-006 | Reflection is immutable after creation. |
| DR-007 | Creating Reflection must not modify its Feedback. |
| DR-008 | Reflection does not require a numerical confidence score. |
| DR-009 | Reflection does not require a separate improvement goal or action plan. |
| DR-010 | Reflection must not depend on a specific prompting or generation mechanism. |
| DR-011 | Reflection must not require persistence infrastructure. |
| DR-012 | Reflection must not contain examination-specific concepts. |

---

## Skill Domain Model (SPEC-010)

SPEC-010 establishes the in-memory Skill domain model for the measurable, transferable capability developed through deliberate practice.

The implementation lives in `fablit.domain` and is intentionally independent of platform infrastructure, persistence, evaluation criteria, Progress, mastery, scoring, hierarchy, curriculum, examination-specific concepts, and AI providers.

### Relationship

```
Skill
  ▲
  │ developed through
  │
Assessment Activity
  │
  ▼
Submission
  │
  ▼
Evaluation
  │
  ▼
Finding
  │
  ▼
Feedback
  │
  ▼
Reflection
```

A Skill defines the capability being developed. An Assessment Activity provides a context in which one or more Skills may be practised; the Skill-to-Activity association mechanism is deliberately deferred to a future specification. Skill does not own Evaluation, Finding, Feedback, or Reflection, and it does not contain evaluation criteria.

### Structure

The initial Skill structure is intentionally minimal:

- identity
- name
- description

No learner-specific state, Progress state, mastery, scoring, or hierarchy is required by SPEC-010.

### Domain Rules Reference

The following rules are enforced by the SPEC-010 domain model:

| Rule | Description |
|------|-------------|
| DR-001 | A Skill must have a unique stable identity. |
| DR-002 | A Skill must have a meaningful name. |
| DR-003 | A Skill must have a meaningful description. |
| DR-004 | A Skill name must not be empty or whitespace-only. |
| DR-005 | A Skill description must not be empty or whitespace-only. |
| DR-006 | A Skill is immutable after creation. |
| DR-007 | A Skill does not require an Assessment Activity. |
| DR-008 | A Skill is not owned by a single Assessment Activity. |
| DR-009 | A Skill does not contain evaluation criteria. |
| DR-010 | A Skill does not require numerical scoring. |
| DR-011 | A Skill does not contain Progress state. |
| DR-012 | A Skill does not require a hierarchy. |
| DR-013 | A Skill is not examination-specific. |
| DR-014 | A Skill is not curriculum-specific. |
| DR-015 | A Skill does not depend on AI or external generation mechanisms. |
| DR-016 | A Skill remains independent of persistence infrastructure. |

---

## Skill–Assessment Activity Association (SPEC-011)

SPEC-011 establishes the many-to-many association between Skill (SPEC-010) and Assessment Activity (SPEC-005).

The implementation lives in `fablit.domain` and is intentionally simple: the Assessment Activity references the Skills it provides an opportunity to practise, by stable identity only (`skill_ids`). No dedicated relationship entity, relationship attributes, Progress, mastery, scoring, evaluation, curriculum, examination, or AI semantics are introduced.

### Relationship

```
                 Skill
                   ▲
                   │
              many │ many
                   │
                   ▼
          Assessment Activity
                   │
                   ▼
               Submission
                   │
                   ▼
               Evaluation
                   │
                   ▼
                Finding
                   │
                   ▼
                Feedback
                   │
                   ▼
               Reflection
```

An Assessment Activity provides an opportunity to practise and demonstrate one or more Skills. A Skill may be practised through multiple Assessment Activities. Neither concept owns the other, and neither requires the other to exist. The association establishes the intended learning context only: it does not imply mastery, proficiency, scoring, Progress, or that every Evaluation must evaluate every associated Skill.

### Domain Rules Reference

The following rules are enforced by the SPEC-011 association:

| Rule | Description |
|------|-------------|
| DR-001 | A Skill may be associated with zero or more Assessment Activities. |
| DR-002 | An Assessment Activity may be associated with zero or more Skills. |
| DR-003 | The relationship is many-to-many. |
| DR-004 | A Skill remains valid without an Assessment Activity. |
| DR-005 | An Assessment Activity remains independently meaningful without a Skill association. |
| DR-006 | A Skill may be associated with multiple Assessment Activities. |
| DR-007 | An Assessment Activity may be associated with multiple Skills. |
| DR-008 | The same Skill–Assessment Activity pair cannot occur more than once. |
| DR-009 | An association must reference valid Skill and Assessment Activity instances. |
| DR-010 | The relationship does not own either domain object. |
| DR-011 | The relationship does not contain scoring information. |
| DR-012 | The relationship does not contain Progress information. |
| DR-013 | The relationship does not contain mastery information. |
| DR-014 | The relationship does not contain evaluation criteria. |
| DR-015 | The relationship does not contain curriculum-specific information. |
| DR-016 | The relationship does not contain examination-specific information. |
| DR-017 | The relationship does not depend on AI. |
| DR-018 | A persistence join structure, if required, shall not automatically become a new domain entity. |

---

## Stimulus Context & Stimulus Instance (SPEC-015)

SPEC-015 establishes that **the image is part of the learner's activity instance**, not merely an attachment to an activity. It introduces two domain concepts: the contextual visual stimulus requirements an activity may define, and the resolved stimulus that was actually shown to a learner.

The implementation lives in `fablit.domain` and is intentionally independent of HTTP, FastAPI, any specific image provider, browser rendering, provider-specific APIs, and external network calls (SPEC-015 §39).

### Relationship

```
Assessment Activity
    │
    │ defines (optional)
    ▼
ActivityStimulusContext
    │   (learning focus, stimulus context, retrieval query)
    │
    │ resolves (application boundary)
    ▼
Stimulus Instance
    │
    ├── Provider
    ├── Asset ID
    ├── Image URL       ← what was displayed
    ├── Source URL      ← where it came from
    ├── Creator
    ├── License
    ├── Attribution
    └── Retrieved At
```

Within a learner's activity instance, the stimulus sits alongside the response and the evaluation:

```
Assessment Activity
    │
    └── Activity Instance
            ├── Stimulus Instance
            ├── Learner Response (Submission)
            └── Evaluation
                    └── Findings (each may carry evidence)
```

An Assessment Activity references a stimulus context by value (an `ActivityStimulusContext`). A Stimulus Instance references its Assessment Activity by stable identity only and never duplicates the activity definition. The activity instance is preserved by the application layer: the same resolved stimulus is reused while a learner works on an instance, and a new stimulus may be resolved when a new instance starts (SPEC-015 §19). A completed activity stays associated with the original stimulus; the system never silently replaces it (§18, §48).

### Domain Rules Reference

The following rules are enforced by the SPEC-015 domain models:

| Rule | Description |
|------|-------------|
| DR-001 | A Stimulus Instance must have a unique identity. |
| DR-002 | A Stimulus Instance must reference an Assessment Activity by identity. |
| DR-003 | An activity's stimulus context must define a meaningful learning focus. |
| DR-004 | An activity's stimulus context must define a meaningful stimulus context. |
| DR-005 | An activity's stimulus context must define a meaningful retrieval query. |
| DR-006 | A Stimulus Instance must record the provider that supplied it. |
| DR-007 | A Stimulus Instance must preserve a direct image URL (what was displayed). |
| DR-008 | A Stimulus Instance must preserve a source page URL (where it came from). |
| DR-009 | A Stimulus Instance must record when it was retrieved (timezone-aware). |
| DR-010 | A Stimulus Instance is immutable after creation. |
| DR-011 | Optional metadata (asset, creator, license, attribution, alt text) must be non-blank when present. |
| DR-012 | A Stimulus Instance must not depend on a specific image provider, HTTP, FastAPI, or external network calls. |
| DR-013 | An Evaluation Finding may carry optional evidence grounding it in the learner's response (SPEC-015 §31). |
| DR-014 | An Evaluation Finding's evidence must be a non-blank string when present. |
| DR-015 | A Stimulus Instance must not contain examination-specific concepts. |

---

## Practice Completion (SPEC-018)

A Practice Completion is an application-level record that acknowledges a
learner has finished one deliberate-practice journey. It is created only after
the learner successfully saves a Reflection; a submitted response, Evaluation,
or Feedback alone never creates one.

### Relationship

```
Learner ────────┐
                ▼
Assessment Activity ◀── Practice Completion ──▶ Reflection
                         │
                         ▼
                   completion time
```

Practice Completion references the learner, Assessment Activity, and
Reflection by identity. It deliberately does not duplicate the associated
objects or record a score, quality judgement, skill level, mastery,
proficiency, streak, ranking, or recommendation. Repeated practice creates
another completion record for the same activity rather than making that
activity unavailable.

### Domain Rules Reference

| Rule | Description |
|------|-------------|
| DLR-009 | A Practice Completion exists only after a Reflection is successfully saved. |
| DLR-010 | A Practice Completion identifies its learner, activity, reflection, and completion time. |
| DLR-011 | A Practice Completion is not evidence of mastery, proficiency, score, or Progress. |
| DLR-012 | Repeated completion of an activity is permitted and remains separate completion history. |

---

## Practice History Record (SPEC-021)

A Practice History Record is the durable evidence of one completed practice
journey. It is created only when the existing SPEC-018 completion flow succeeds:
a submitted or evaluated response alone never becomes history. Each record is
an independently reviewable unit — `activity_id` is never the identity of
history, so repeated practice of the same activity remains distinguishable.

### Relationship

```
Practice History Record
    ├── learner context
    ├── activity identity + title
    ├── completion timestamp
    ├── Stimulus Instance (SPEC-015, as resolved for that attempt)
    ├── Submission (SPEC-006)
    ├── Evaluation (SPEC-007)
    ├── Feedback (SPEC-008)
    └── Reflection (SPEC-009)
```

The record is expressed through a narrow persistence port
(`PracticeHistoryRepository`) in the application layer. The domain model never
depends on persistence mechanics; concrete adapters (in-memory, Google Cloud
Datastore) live behind the boundary. The reflection identity is the stable
completion identity, making retries idempotent. The learner context is kept
explicit so future authentication/account work can establish ownership without
redesigning the stored evidence.

### Domain Rules Reference

| Rule | Description |
|------|-------------|
| PHR-001 | A Practice History Record exists only after a successful Reflection/Completion (SPEC-018 boundary unchanged). |
| PHR-002 | A Practice History Record retains the evidence required for review: activity, stimulus, response, evaluation, feedback, reflection, completion time. |
| PHR-003 | A Practice History Record has a stable identity distinct from the activity identity; repeated practice creates separate records. |
| PHR-004 | A reviewed practice shows the stimulus originally resolved for that attempt, never a newly resolved one. |
| PHR-005 | Persistence is expressed through a port; the domain layer remains independent of Datastore, App Engine, HTTP, and serialization. |
| PHR-006 | A failed persistence write is explicit; a completion is never falsely reported as durably recorded, and retries do not duplicate history. |
| PHR-007 | History is not evidence of mastery, proficiency, score, Progress, or ranking. |

## Practice Mode (SPEC-022)

A **Practice Mode** is a learner-experience/application concept — not a domain
model — describing the *shape* of practice the learner explicitly chooses for
the current interaction: a compact **Short Drill** (about 5–10 minutes of
learner effort, as an indication rather than a limit) or the existing **Full
Practice** experience.

A mode is only a pointer at existing Assessment Activities: it never
re-identifies an activity, never duplicates Skill, Evaluation, or Completion
semantics, and never becomes a scoring, progress, or ranking dimension. Its
eligibility is explicit, curated content configuration rather than
inference from titles or learner history, and the learner's selection is
authoritative for the current practice entry. A learner who ignores the mode
chooser still reaches the ordinary activity library, and a completed Short
Drill is simply completed practice recorded under SPEC-021.

### Domain Rules Reference

| Rule | Description |
|------|-------------|
| PM-001 | A Practice Mode exists at the application/learner-experience boundary and is not a domain model. |
| PM-002 | A Practice Mode selects existing Assessment Activities; it never re-identifies, wraps, or replaces them. |
| PM-003 | Mode eligibility is explicit configuration, never title-string inference, history-based selection, or hidden personalization. |
| PM-004 | Indicative effort guidance is guidance only — never a countdown, enforced window, or grading input. |
| PM-005 | A completed practice in any mode is recorded and reviewed exactly like any other completion (SPEC-021). |

## Practice Capability Lens (SPEC-023)

A **Practice Capability** is a content-design label — not a domain concept,
not a Skill, and not learner-visible state — used to review the practice
library for balance. The lens is the internal set **Observe, Interpret,
Ideate, Articulate, Reflect**. Every Assessment Activity in the demo content
carries exactly one *primary* capability plus optional *secondary*
capabilities.

The lens lives in demo content metadata only: it never appears in
learner-facing copy, never reaches a view model, and never drives selection,
ordering, or recommendations (AC-023-12). The library expansion it reviews is
itself content: new activities reuse the existing Assessment Activity model,
the unchanged learner journey, and SPEC-021 history, and the Short Drill
curated list simply names more of them.

### Domain Rules Reference

| Rule | Description |
|------|-------------|
| PCL-001 | The capability lens (Observe/Interpret/Ideate/Articulate/Reflect) is internal content-design metadata, never a domain model, Skill hierarchy, or learner-facing taxonomy. |
| PCL-002 | Every activity carries exactly one primary capability; secondaries are optional and must differ from the primary. |
| PCL-003 | The lens never drives selection, ordering, recommendation, or any learner-visible presentation. |
| PCL-004 | Library expansion adds content only: no new activity type, workflow, or journey semantics (the Submission → Evaluation → Feedback → Reflection → Completion flow is unchanged). |
| PCL-005 | Expanded Short Drill eligibility is explicit content configuration (an extension of PM-003), never history-based. |

## Learner Identity (SPEC-024)

A **Learner Identity** is the anonymous, opaque identifier Fablit uses as
the ownership key for practice history. Every anonymous learner's browser
receives a unique identity (a random UUID in a secure cookie); practice
submissions, completions, history, and review are resolved against that
identity, so two independent learners never share history.

The identity is deliberately *not* an account: it encodes no personal
information, is derived from no identifying data, requires no registration,
and is local to the browser until a future recovery mechanism attaches to it
(SPEC-024 §5.3, §10). Anonymous does not have to mean shared.

### Domain Rules Reference

| Rule | Description |
|------|-------------|
| LI-001 | Every anonymous learner receives a unique, opaque learner identity; it encodes no personal information and is derived from no identifying data. |
| LI-002 | The identity persists across requests from the same browser; a missing or invalid identity starts a fresh anonymous learner. |
| LI-003 | Practice history and review are reachable only through the current learner's identity; crossing the boundary behaves exactly like an unknown record. |
| LI-004 | The fixed demo learner identity is never used for normal web traffic; demo fixtures stay isolated to application-layer tests. |
| LI-005 | The learner identity is an internal ownership identifier, never an authentication credential and never learner-visible in pages or URLs. |

## Learner Practice Application Flow (SPEC-012)

SPEC-012 establishes the first **Application Layer** in Fablit: the orchestration that connects user interaction to the existing learning-domain models so a learner can complete a meaningful practice → feedback → reflection cycle.

SPEC-012 introduces **no new core domain concept**. It composes the concepts established by SPEC-005 through SPEC-011 (Assessment Activity, Submission, Evaluation, Finding, Feedback, Reflection, Skill) into a learner-facing vertical slice. The implementation lives in `fablit.application` and is deliberately separate from the Web/UI layer (`app`) and the learning domain (`fablit.domain`).

### Relationship

```
Learner (demo context)
    │
    ▼
Practice Dashboard        UC-001
    │
    ▼
Practice Activity         UC-002
    │
    ▼
Submission                (SPEC-006)
    │
    ▼
Demo Evaluation           UC-004 (deterministic, predefined)
    │
    ▼
Feedback                  (SPEC-008)
    │
    ▼
Reflection                (SPEC-009)
    │
    ▼
Completion Confirmation   UC-007
```

### Use Cases

| Use Case | Name | Purpose |
|----------|------|---------|
| UC-001 | Get Practice Dashboard | Provide the learner with 3–5 available practice activities. |
| UC-002 | Start Practice Activity | Present an Assessment Activity in a form suitable for practice. |
| UC-003 | Submit Response | Accept a learner response and create a valid Submission. |
| UC-004 | Evaluate Demo Submission | Produce a known, deterministic Evaluation with at least one structured Finding. |
| UC-005 | Present Feedback | Transform the Evaluation into learner-facing strengths, improvements, and next steps. |
| UC-006 | Start Reflection | Present the purposeful reflection prompt together with feedback context. |
| UC-007 | Submit Reflection | Create a valid Reflection and return a completion result. |

### Boundaries

- The Application Layer orchestrates domain behaviour and prepares **view models**; it contains no HTML and no presentation logic.
- The Application Layer never redefines domain invariants; Submission, Evaluation, Finding, Feedback, and Reflection are created through the existing domain models.
- The demo learner context is a stable identity only; no user-management domain model is introduced (SPEC-012 §27). Since SPEC-024, normal web requests resolve a unique anonymous learner identity per browser instead of the fixed demo identity; the fixed identity remains demo-content metadata.
- The demo evaluator is deterministic and predefined; it requires no AI provider, network service, or asynchronous worker, and can be replaced later without changing learner-facing concepts (SPEC-012 §11–12, §40).
- The vertical slice preserves the learner journey in memory; persistence remains outside the domain model (SPEC-012 §28).
- No Progress, mastery, proficiency, scoring, recommendations, authentication, or examination-specific logic is introduced (SPEC-012 §6.2).

---

## Submission

A Submission is the learner's response to an Assessment Activity.

Examples include:

- selected option
- written response
- uploaded sketch
- uploaded document
- recorded audio
- recorded video

Every Submission belongs to exactly one learner and one Assessment Activity.

---

## Evaluation

Evaluation is the process of interpreting a Submission.

Evaluation may be:

- automatic
- AI-assisted
- instructor-reviewed
- peer-reviewed

Evaluation always produces Feedback.

---

## Feedback

Feedback communicates how the learner can improve.

Feedback should prioritise learning rather than grading.

Feedback may contain:

- strengths
- improvement suggestions
- rubric observations
- recommended exercises
- learning resources

---

## Reflection

Reflection is the learner's own evaluation after receiving Feedback.

Reflection is considered part of the learning process.

Reflection may include:

- self-assessment
- confidence rating
- improvement goals
- learning notes

---

## Progress

Progress represents the learner's development over time.

Progress includes:

- completed activities
- completed assessments
- skill trends
- learning streaks
- milestones
- achievements

Progress belongs to the learner rather than a specific assessment.

---

## Rubric

A Rubric defines how a Submission should be evaluated.

A Rubric may include:

- criteria
- weightage
- performance indicators
- expected outcomes

Rubrics should be reusable across multiple Assessment Activities.

---

## Learning Resource

A Learning Resource supports learner improvement.

Examples include:

- article
- video
- infographic
- case study
- example submission
- reference material

Learning Resources support Skill Labs but are not assessments.

---

## Content Pack

A Content Pack is a curated collection of Skill Labs, Assessments, and Learning Resources designed for a particular educational objective.

Examples include:

- NIFT Preparation
- NID Preparation
- CEED Preparation
- Fashion Communication
- Design Thinking

Content Packs do not introduce new platform capabilities.

They assemble existing capabilities into a coherent learning journey.

---

## Recommendation

A Recommendation is a suggested next action generated for the learner.

Recommendations may be based on:

- assessment history
- learner goals
- weak skills
- completed activities
- feedback history

---

## Learning Path

A Learning Path is an ordered sequence of Skill Labs and Assessments.

Learning Paths may be predefined or personalized.

---

# Relationships

```
Learner

    │

    ▼

Learning Path

    │

    ▼

Content Pack

    │

    ▼

Skill Lab

    │

    ▼

Assessment

    │

    ▼

Assessment Activity

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

# Domain Rules

The following rules guide domain modelling.

These product-level rules use the `DLR-` prefix to distinguish them from the domain rules (`DR-001`–`DR-018`) documented in the Assessment Domain Model (SPEC-005), Submission Domain Model (SPEC-006), Evaluation Domain Model (SPEC-007), Feedback Domain Model (SPEC-008), Reflection Domain Model (SPEC-009), Skill Domain Model (SPEC-010), Skill–Assessment Activity Association (SPEC-011), and Stimulus Context & Stimulus Instance (SPEC-015) sections above.

## DLR-001

Every Assessment contains one or more Assessment Activities.

---

## DLR-002

Every Assessment Activity accepts exactly one Submission per attempt.

---

## DLR-003

Every Submission produces one Evaluation.

---

## DLR-004

Every Evaluation produces Feedback.

---

## DLR-005

Reflection always occurs after Feedback.

---

## DLR-006

Progress is calculated from learner history rather than individual assessments.

---

## DLR-007

Skill Labs are reusable across multiple Content Packs.

---

## DLR-008

Content Packs compose learning experiences but do not define platform behaviour.

---

# Terminology to Avoid

To maintain consistency, avoid introducing alternative names for established concepts.

| Avoid | Preferred |
|--------|-----------|
| Course | Content Pack |
| Lesson | Learning Resource |
| Question | Assessment Activity |
| Test | Assessment |
| Student | Learner |
| Result | Feedback / Progress |
| Module | Skill Lab |

---

# Ubiquitous Language

Every contributor should use the terminology defined in this document consistently across:

- architecture
- specifications
- ADRs
- source code
- APIs
- database models
- documentation
- discussions
- pull requests

Consistency in language leads to consistency in software.

---

# Closing Statement

The language of Fablit is part of its architecture.

When contributors share the same vocabulary, communication becomes clearer, software becomes easier to maintain, and the platform evolves with less ambiguity.
