# Fablit Domain Language

**Document ID:** DL-001
**Version:** 0.8.0
**Status:** Draft
**Last Updated:** 2026-08-15

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

A Finding is deliberately not a score. Each Finding carries a meaningful observation or judgement about the learner's work and a stable identity. The initial structure is intentionally small and extensible; richer Finding dimensions (evidence, criteria references, categories) may be introduced by future specifications without redesigning the Evaluation aggregate.

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

These product-level rules use the `DLR-` prefix to distinguish them from the domain rules (`DR-001`–`DR-018`) documented in the Assessment Domain Model (SPEC-005), Submission Domain Model (SPEC-006), Evaluation Domain Model (SPEC-007), Feedback Domain Model (SPEC-008), Reflection Domain Model (SPEC-009), Skill Domain Model (SPEC-010), and Skill–Assessment Activity Association (SPEC-011) sections above.

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
