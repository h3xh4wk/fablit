# Fablit Domain Language

**Document ID:** DL-001
**Version:** 1.17.0
**Status:** Draft
**Last Updated:** 2026-10-30

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

## Feedback Quality Contract (SPEC-030)

SPEC-030 defines the learner-facing quality contract for feedback produced after an Evaluation.

The implementation stays at the application/content boundary rather than introducing a new domain model: the existing `Feedback` record remains a stable domain object, while the practice content and application layer determine how evidence, improvement guidance, and next-step direction are presented to the learner.

### Relationship

```
Practice Purpose
      ↓
Learner Attempt
      ↓
Evaluation
      ↓
Evidence-based Feedback
      ↓
Reflection
      ↓
Another Attempt
```

Feedback is not a score or a label. It is the explanatory bridge between what the learner did and what they can do next.

### Quality Rules

| Rule | Description |
|------|-------------|
| DR-001 | Feedback should be grounded in observable evidence when the evaluation provides it. |
| DR-002 | Feedback should relate directly to the practice purpose and the task asked of the learner. |
| DR-003 | Improvement guidance should identify a concrete thing the learner can notice, test, compare, or explain. |
| DR-004 | Next-step guidance should be practical and proportionate to the task. |
| DR-005 | Feedback should avoid learner labelling and unsupported inference about effort, intelligence, motivation, or future performance. |
| DR-006 | Feedback should not introduce hidden scoring, mastery, or ranking semantics. |
| DR-007 | Feedback should leave the learner with a meaningful Reflection handoff. |
| DR-008 | Feedback should be concise enough to remain useful without adding length for its own sake. |

The application layer preserves this boundary by rendering structured strengths, improvement guidance, and next steps from Evaluation findings without introducing a new learner-ranking or recommendation mechanism.

---

## Sketchbook Reflection Practice (SPEC-031)

SPEC-031 introduces a lightweight sketchbook bridge for the practice journey: learners can bring work they have already created outside Fablit into a short reflection practice that helps them notice what their own work taught them.

### Relationship

```
Sketchbook Work
      ↓
Sketchbook Reflection
      ↓
Feedback
      ↓
Notice for Next Time
```

The sketch remains learner-owned context. The reflection is the primary evaluable response, and the system does not treat the sketch as a drawing-quality object to be scored.

### Domain Rules Reference

| Rule | Description |
|------|-------------|
| DR-001 | A sketchbook reflection practice is optional and remains a short drill in the existing practice journey. |
| DR-002 | The learner-provided sketch or image is contextual evidence for reflection, not the evaluative object itself. |
| DR-003 | The reflection prompt focuses on process, observation, and decisions rather than visual quality or aesthetic judgement. |
| DR-004 | Feedback should remain grounded in the learner's written reflection and the stated practice purpose. |
| DR-005 | The practice must remain within the learner-scoped private history boundary and never introduce a parallel public gallery or social artifact stream. |
| DR-006 | The sketchbook path uses the existing `Submission → Evaluation → Feedback → Reflection → Completion` flow without introducing a separate scoring or ranking model. |

The feature remains intentionally lightweight: it complements the learner's sketchbook routine rather than requiring a full digital sketchbook or a new public artifact model.

---

## AI-Assisted Practice Authoring (SPEC-032)

SPEC-032 lets an authorized internal author use AI to draft *candidate* practices while the learner-facing library stays curated and human-reviewed. It is deliberately an **application-boundary workflow**, not a learning-domain concept: it introduces no new domain model and never touches the learner journey.

### Relationship

```
Authoring Brief
      ↓
AI Candidate (or brief-derived draft)
      ↓
Structural (SPEC-029) + Feedback (SPEC-030) Validation
      ↓
Human Review
      ↓
Approved Practice → Curated Library
```

A candidate reuses the existing SPEC-029 `PracticeContentContract`; there is no parallel learner-facing practice model for AI output. Validation is a gate, never an automatic approval.

### Workflow Language

| Term | Meaning |
|------|---------|
| Authoring Brief | A structured description of the practice an author wants (area, purpose, task, thinking lens, mode, response form, intents). An exam name alone is not sufficient. |
| Candidate | A structured, SPEC-029-compatible draft with its authoring provenance. A candidate is not learner-facing content. |
| Validation | The structural and feedback check that decides whether a candidate may enter the approval path. |
| Approval | An explicit human action that places a validated candidate in the curated library. |
| Provenance | Internal authoring metadata (brief, generation time, provider/model, candidate version, reviewer, decision, revisions). Never exposed to learners. |

### Domain Rules Reference

| Rule | Description |
|------|-------------|
| DR-001 | AI proposes candidates; only explicit human approval places content in the curated library (AA-001, AA-008). |
| DR-002 | Every candidate is structured against the SPEC-029 Practice Content Contract (AA-002). |
| DR-003 | Generated evaluation/feedback guidance must satisfy SPEC-030 and carry no grading, mastery, ranking, ability, motivation, or effort language (AA-003). |
| DR-004 | Malformed or incomplete candidates cannot enter the approval path (SPEC-032 §7, §17). |
| DR-005 | Candidates may be edited (producing a revision) or rejected; approved content stays distinct from unapproved candidates. |
| DR-006 | Authoring never requires learner personal data and is never shown to learners (AA-007, §16, §18). |
| DR-007 | AI availability never affects ordinary learner practice: authoring works without a provider and is fully separate from the learner flow (§17). |
| DR-008 | The workflow depends on a provider-neutral LLM port (`fablit/application/authoring_llm.py`), never on a specific provider SDK; a concrete adapter owns credentials, request/response handling, and provider failures (ARCH-001). |

The implementation lives at the application boundary (`fablit/application/authoring.py`) behind the SEC-001 access boundary, so the internal Observe / Interpret / Ideate / Articulate / Reflect lens and all authoring metadata stay internal review aids rather than learner-facing progress data. The provider-neutral LLM port (`AuthoringLlmProvider`) and its structured `LlmGenerationResult` keep the workflow independent of any vendor; the initial Google Gemini adapter (`fablit/platform/gemini_authoring_provider.py`) keeps credentials and provider failures inside the server-side provider boundary.

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
| PHR-001 | A Practice History Record exists when the practice completion flow succeeds regardless of whether reflection is saved or skipped (SPEC-018/SPEC-159); a reflection may be absent or attached later. |
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

## Practice Transition (SPEC-025)

A **Practice Transition** is a content-level relationship from one completed
Assessment Activity to one authored next practice. It exists to make visible
that one kind of design thinking can lead naturally into another —
**Observe → Interpret → Ideate → Articulate → Reflect → practise again** —
after the learner finishes an activity.

A transition is authored deliberately by Fablit's content/design layer, not
computed: it never derives from learner history, completion counts,
evaluations, scores, or inferred behaviour, and it is not a recommendation,
a mastery signal, or a schedule. The relationship points at an existing
Assessment Activity; starting it runs the unchanged SPEC-012 journey and the
resulting practice is ordinary SPEC-021 history under the learner's SPEC-024
identity. The learner may follow the continuation, return to Explore, or
simply leave it — the continuation is an invitation, never a forced step.

### Relationship

```
Completion (SPEC-018)
    │
    ▼
Practice Transition (content configuration, one per source activity)
    │ names
    ▼
existing Assessment Activity → unchanged learner journey (SPEC-012)
    │
    ▼
Practice History (SPEC-021) under the learner's identity (SPEC-024)
```

### Domain Rules Reference

| Rule | Description |
|------|-------------|
| PT-001 | A Practice Transition exists at the content layer and is not a domain model; it names existing Assessment Activities by identity and never re-identifies, wraps, or replaces them. |
| PT-002 | A source activity has at most one authored transition; the lookup is deterministic for the same content configuration. |
| PT-003 | A transition is authored, curated content — never derived from learner identity, history, scores, completion counts, or inferred behaviour. |
| PT-004 | Transition copy makes the relationship between the two practices visible, calmly and editorially, with no “recommended”, “best”, or pressure language. |
| PT-005 | Following a transition starts the unchanged journey; the target practice is recorded and reviewed like any other completion, and the learner can always ignore the continuation. |

## Pre-Practice Intention (SPEC-026)

A **Pre-Practice Intention** is the learner's own optional, qualitative
statement of focus for the practice they are about to begin — captured after
selecting an activity and before entering the active workspace, attached to
the session's Submission, and rendered for review with the completed
artifact. It exists to support metacognition: naming a focus before
practising, then seeing that focus again while reflecting.

An intention is never required, never blocks practice, and is never graded,
analysed, or shown to any evaluator — it is a qualitative learner artifact,
not an assessment input. A blank or skipped intention simply leaves nothing
behind.

### Domain Rules Reference

| Rule | Description |
|------|-------------|
| PPI-001 | A Pre-Practice Intention is optional; stating or skipping it never blocks entry into practice or completion. |
| PPI-002 | A captured intention is attached to the session's Submission and remains associated with that attempt only. |
| PPI-003 | An intention is never graded, analysed, or consumed by evaluation, feedback, or any scoring mechanism. |
| PPI-004 | A reviewed practice shows the intention captured for that attempt, before the response, when one exists. |

## Local Practice Draft (SPEC-028)

A **Local Practice Draft** is the learner's uncommitted, in-progress input —
the response being written, the pre-practice intention being phrased, or the
reflection being considered — held transiently in the learner's own browser
so an accidental reload or tab closure does not lose work. It is a
device-local convenience artifact, not a platform record: it never reaches
the server, is never scored, analysed, or graded, and is removed once the
real artifact (a `Submission`, an intention attached to the journey, or a
`Reflection`) is committed, or after 24 hours.

The draft layer is deliberately absent from the domain and application
layers — it lives entirely in a client module (`app/static/js/session-
recovery.js`). A draft that never became a submission leaves no trace
anywhere but the learner's device.

### Domain Rules Reference

| Rule | Description |
|------|-------------|
| LPD-001 | A Local Practice Draft exists only in the learner's browser storage (IndexedDB primary, `localStorage` fallback) and is never transmitted to the server. |
| LPD-002 | A draft is keyed by browser scope and activity identity; the SPEC-024 learner cookie stays HttpOnly and is never exposed to the draft layer. |
| LPD-003 | A draft is an offer, never a gate: resuming or discarding is always the learner's choice, and missing storage degrades to standard practice. |
| LPD-004 | A draft is removed when the corresponding artifact commits (successful submission) or after 24 hours, so no stale state outlives its usefulness. |
| LPD-005 | A draft is never scored, analysed, or graded; recovery copy stays calm and factual, with no urgency or progress language. |

## Internal Authoring Brief and Candidate (SPEC-032)

An **Authoring Brief** is a typed, validated request from an internal content
author describing the educational intent and context for a proposed practice.
It may include optional examination context, a primary creative-thinking
lens, stimulus requirements, constraints, and continuation intent. It contains
no learner personal data.

A **Practice Candidate** is an untrusted, structured draft returned by an AI
provider. It retains the Authoring Brief and provider-neutral provenance
(provider, model, and timezone-aware generation time). The candidate undergoes
deterministic validation against the SPEC-029 Practice Content Contract and
SPEC-030 feedback quality rules before entering the human review lifecycle. Approved
candidates remain isolated from learner-facing practices until explicitly curated.
The candidate store tracks revision history across edits and prevents unvalidated
or conflicting approval transitions.

```
Authoring Brief
      ↓
Provider-neutral generation
      ↓
Untrusted Practice Candidate + provenance
      ↓
SPEC-029 / SPEC-030 validation
      ↓
Human review (inspect · edit · reject · approve)
      ↓
Curated library isolation
```

### Rules

| Rule | Description |
|------|-------------|
| AA-001 | The brief requires practice area, learner context, purpose, mode, response form, evaluation intent, feedback intent, and reflection intent. |
| AA-002 | Examination context, creative-thinking lens, constraints, stimulus requirements, and continuation intent are optional. |
| AA-003 | Provider output remains untrusted candidate data; this model does not imply educational validation or approval. |
| AA-004 | Provenance identifies provider, model, and timezone-aware UTC generation time, and never contains credentials or provider SDK objects. |
| AA-005 | Authoring candidates and provenance are internal workflow data, never learner-facing progress or content until curated. |
| AA-006 | Deterministic validation checks all 8 SPEC-029 contract fields and forbids evaluative language (SPEC-030); candidates failing validation cannot be approved. |
| AA-007 | Candidate editing produces a new revision with preserved history and re-triggers contract validation. |
| AA-008 | Candidate review outcomes (`pending`, `approved`, `rejected`) follow strict state transitions; approved candidates stay separate from public learner routes until they are explicitly published (SPEC-035). |
| AA-009 | Shared candidate state is persisted across application instances in an authoring-scoped namespace, strictly isolating candidate storage from learner routes. |
| AA-010 | Unapproved candidates are governed by a configurable retention policy (default 30 days); approved candidates are retained indefinitely for curation. |
| AA-011 | Candidate store failures result in service unavailable (503) responses and never report false authoring success. |

## AI-Assisted Authoring Brief Drafting (SPEC-040)

SPEC-040 lowers the entry barrier to SPEC-032 authoring without changing what
a brief is. An authorised author who has only rough notes, pasted source text,
or a short topic can ask Fablit to draft the *existing* Authoring Brief fields.
A draft is application-boundary state, not a new domain concept and not a new
persistence model: it is rendered straight back into the same editable brief
form, and candidate generation, approval, and publication stay separate
explicit actions.

```
Author's notes / pasted source / short topic
      ↓
Provider-neutral drafting request (notes + current brief)
      ↓
Untrusted structured draft (values · provenance · assumptions)
      ↓ server-side validation: existing fields, allowed values, bounded text
Editable brief form with source markers
      ↓ author edits or regenerates a field
Existing SPEC-032 candidate generation (separate explicit action)
```

### Rules

| Rule | Description |
|------|-------------|
| BD-001 | Drafting reuses the existing brief fields and allowed values; it introduces no parallel brief model and no new persistence. |
| BD-002 | A drafted value is labelled as notes-grounded, an AI suggestion, or an assumption to confirm; it is never presented as an author-supplied fact. |
| BD-003 | Generated examination or institutional context is always an assumption to confirm; Fablit never presents it as official guidance. |
| BD-004 | A single-field regeneration changes only that field; a whole-brief draft keeps the author's existing values unless replacement is explicitly chosen. |
| BD-005 | Drafting never discards the original notes or current edits; failed, malformed, or invalid drafts leave the form retryable. |
| BD-006 | Brief drafting and candidate generation are separate explicit actions; drafting never creates, approves, or publishes a candidate. |

## Published Practice Publication (SPEC-035)

A **Published Practice** is approved, human-reviewed authoring content that an
author has deliberately made available in the learner-facing curated practice
library. Approval and publication are distinct decisions: *approved* records
that a reviewer accepted the candidate's content quality; *published* means the
approved content is discoverable by learners. Publication is an explicit human
curation action — never a side effect of generation or approval.

The publication record carries the existing learner-facing activity
representation (`DemoActivity` / `AssessmentActivity`) plus internal
provenance: the source authoring candidate identity, the approved revision,
the publication time, and any withdrawal time. Provenance is authoring-side
data and never appears on learner-facing routes.

```
Approved Practice Candidate
           ↓ explicit publish action
     Published Practice
   (learner-facing activity + internal provenance)
           ↓
Learner discovery → Practice → Evaluation → Feedback → Reflection
           ↓ explicit withdrawal
hidden from discovery; completed history preserved
```

### Rules

| Rule | Description |
|------|-------------|
| PUB-001 | Only an explicitly approved candidate may be published; generated, rejected, invalid, and edited-but-not-reapproved candidates are refused at the publication boundary. |
| PUB-002 | Approval alone never makes content learner-visible; publication is a separate, explicit human action. |
| PUB-003 | The publication boundary revalidates content (SPEC-029/SPEC-030) and approval state again before anything is written. |
| PUB-004 | A published practice reuses the existing learner-facing activity representation; publication never introduces a parallel learner practice model. |
| PUB-005 | Repeating the same publish request is idempotent and never creates a duplicate catalogue entry; republishing a re-approved revision replaces content in place under the same stable activity identity. |
| PUB-006 | Publication state and provenance are kept behind the published practice store port; a storage failure is reported as a failure and never leaves misleading partial state. |
| PUB-007 | Withdrawing a published practice removes it from learner discovery only: completed history stays readable, in-flight practice can finish, and the publication record is retained for traceability. |
| PUB-008 | Learner-facing routes expose only published practice content — never authoring candidates, provenance, reviewer decisions, validation diagnostics, or provider details. |

## Curated News Story (SPEC-041)

A **Curated News Story** is a current fashion, textiles, sustainability, Indian
craft, design, or visual-culture story that has passed source, freshness,
safety, relevance, and grounding checks and is available in the learner-facing
Fashion & Design Pulse. It is an **application-layer concept**, not part of the
learning domain: it carries no learner identity, progress, evaluation, or
mastery meaning, and it never affects practice history.

A story retains its publisher attribution, canonical link, publication date
when the source supplies one, retrieval and curation timestamps, a concise
summary, controlled categories, an educational-relevance note, an optional
reflection prompt, and curation provider/model provenance.

A story may also carry one optional **Story Image**: an illustrative stock
photograph selected during curation, stored with its provider, source page,
creator/attribution, alt text, and asset identifier. Imagery is illustrative
only, always credited separately from the publisher, and never a substitute
for a publisher photograph.

```
Approved source (explicit allowlist)
        ↓ bounded fetch and normalization
Untrusted source item
        ↓ allowlisting · URL safety · freshness · deduplication
Provider-neutral curation request
        ↓ AI curation behind a news-specific port
Untrusted structured result
        ↓ schema · category · relevance · grounding · language checks
Curated News Story
        ├── optional illustrative Story Image (validated capture only)
        ↓ news-specific repository port
Persisted feed → learner Pulse (no live AI, image search, or network)
```

### Rules

| Rule | Description |
|------|-------------|
| NEWS-001 | Only stories from an explicit allowlist of approved sources may be curated; a story link must belong to the publisher host of the source that supplied it. |
| NEWS-002 | Only absolute, public HTTP(S) links are accepted; credentials, private/loopback/link-local destinations, non-default ports, and unsafe redirects are refused. |
| NEWS-003 | Retrieval and curation are bounded: per-source item counts, response size, timeouts, field lengths, and summary length all have explicit limits. |
| NEWS-004 | Stories without a reliable publication date, or outside the freshness window, are rejected; Fablit never invents a date. |
| NEWS-005 | A story is deduplicated by canonical URL against the current batch and persisted stories, so repeated refreshes are idempotent. |
| NEWS-006 | AI output is untrusted until it passes schema, controlled-category, relevance-threshold, grounding-term, and learner-language checks; failed candidates are never published. |
| NEWS-007 | News curation is separate from practice authoring: it has its own provider port, request/result types, persistence boundary, and publication decision. |
| NEWS-008 | A failed, partial, or empty refresh never clears previously published stories. The learner feed reads persisted stories only and remains usable without live AI or network access. |
| NEWS-009 | Learner-facing story copy stays qualitative and attributed; full articles, large source excerpts, and unlicensed imagery are not stored or rendered. |
| NEWS-010 | News curation provider errors distinguish transient retries (HTTP 429/503) from terminal failure; retries are bounded and structured diagnostics never leak credentials or raw payloads. |
| NEWS-011 | Story imagery is optional and illustrative: it is selected only inside curation from the existing provider-neutral image-search port, stored with its provenance, and labelled as illustrative so a generic stock photograph is never presented as evidence of a specific designer, collection, product, event, or craft item. |
| NEWS-012 | Image search never runs on a learner request; a story renders its persisted image or a clean text-first card, and a search or persistence failure never blocks, removes, or misattributes an otherwise valid story. |
| NEWS-013 | Only a public HTTP(S) image URL with a usable size, a non-extreme aspect ratio, and relevance to the story's derived visual query is persisted; unsafe, incomplete, or uncertain candidates yield no image. |

## Story Response (SPEC-044)

A **Story Response** is a learner's private, lightweight answer to the "What
to try" prompt attached to a Fashion & Design Pulse story. It is a qualitative
learner artifact, not a Submission, not a completed practice, and not a signal
used to infer ability. Saving one records the learner's own words together
with enough provenance to understand the context later.

A Story Response retains the originating story's stable identity, the headline
and source name shown when the response was written, the canonical story URL,
the prompt the learner answered, the response text, and the UTC save time. It
is owned by the current opaque learner identity and is never visible to other
learners, never listed in the shared library, and never published.

```
Pulse story with "What to try" prompt
        ↓ learner chooses "Try this"
Short private response composer
        ↓ explicit save + bounded text validation
Story Response (story id · headline · source · canonical URL · prompt · text)
        ↓ learner-scoped repository port
Private learner history
        ↓
Revisit the response with its originating story and prompt
```

Saving a Story Response never invokes an AI provider, never evaluates or grades
the response, and never creates a practice completion. A story prompt that is
deliberately modelled as a supported formal practice follows the ordinary
practice journey instead.

### Rules

| Rule | Description |
|------|-------------|
| SR-001 | A Story Response is saved only after an explicit learner action, and only for a story that offers a "What to try" prompt. |
| SR-002 | A saved response retains the story's identity, headline, source name, canonical URL, prompt text, and the learner's response text. |
| SR-003 | A Story Response is private to the current anonymous learner; listing, retrieval, and history display are scoped by learner identity. |
| SR-004 | Saving a Story Response never evaluates, scores, grades, ranks, or sends the response to an AI provider, and never creates a practice completion. |
| SR-005 | Retrying the same composer submission resolves to the same stable response identity, so a double submit or retry never creates a duplicate. |
| SR-006 | Response text is bounded and validated before persistence; empty and over-long responses receive actionable, non-technical feedback without losing the learner's words. |
| SR-007 | A persistence failure is reported honestly; Fablit never tells a learner a response was saved when the write failed. |
| SR-008 | Saved responses are immutable; writing another response to the same story creates a separate record rather than silently changing the earlier one. |

## Requested Practice (SPEC-044)

A **Requested Practice** is one private practice generated for a single learner
from that learner's own short request. It is explicit learner-requested
content: it is not part of the shared curated library, it is never visible to
another learner, and it is never scored, graded, ranked, or treated as evidence
of ability. "Practice" stays the noun — the learner is practising, not being
assessed.

A **Practice Request** is the learner's short statement of what they want to
practise, together with a few plain-language choices: a practice area, a
preferred response form, an optional challenge preference, an optional
examination context the learner states themselves, and whether their own
recent practice may be used as context. The request is bounded before any
generation happens, and nothing is generated until the learner submits it.

A Requested Practice retains the validated title, description, and complete
practice content contract the learner was shown, the request's own preferences,
and safe provenance (provider, model, generation time). It reuses the ordinary
learner activity and practice journey, so practising it produces ordinary
practice history under the learner's own identity.

```
Learner request (what to practise + preferences)
        ↓ explicit submit; bounded and validated first
Generation through the provider-neutral port
        ↓ untrusted output validated against the content + feedback boundary
Requested Practice (title · description · contract · preferences · provenance)
        ↓ learner-scoped repository port (never the shared library)
Private practice brief
        ↓ learner chooses to begin
Ordinary practice journey → ordinary practice history
```

A Practice Request may also start from a Pulse story: "Make this a practice"
carries that story's "What to try" prompt into the request as editable
starter text, with a link back to the story. The prompt is a suggestion, not a
constraint — the learner can rewrite it, and the story never narrows the area
or challenge choice on their behalf.

Generation receives only the learner's request, its preferences, and — when
the learner leaves the option on — a minimal slice of that learner's own
completed practice (titles and capability areas). Full responses, reflections,
artifacts, other learners' records, and the learner's identity are never sent.

### Rules

| Rule | Description |
|------|-------------|
| RP-001 | A Requested Practice is generated only after an explicit learner action, from a request that is non-blank and bounded in length. |
| RP-002 | A Requested Practice is private to the current anonymous learner; listing and retrieval are scoped by learner identity, and another learner's practice is indistinguishable from one that does not exist. |
| RP-003 | A Requested Practice never enters the shared curated library, learner discovery, or practice-mode selections. |
| RP-004 | Generated output is untrusted until it passes the existing practice content contract and feedback language validation; invalid output never reaches the learner and is never persisted. |
| RP-005 | History context is opt-in, limited to the learner's own recent completed practice titles and areas, and never includes their responses, reflections, artifacts, or identity. |
| RP-006 | A Requested Practice is never scored, graded, ranked, or used to infer ability, motivation, or future performance. |
| RP-007 | Retrying the same request token resolves to the same stable practice identity, so a double submit or retry never creates a duplicate. |
| RP-008 | A generation or persistence failure is reported honestly with plain language; Fablit never claims a practice was made or saved when it was not. |
| RP-009 | Requested Practices are always self-contained: the task must be doable in one focused response with no external material the learner does not have. |
| RP-010 | Practising a Requested Practice follows the ordinary practice journey and produces ordinary practice history under the learner's own identity. |

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
