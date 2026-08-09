# Fablit Domain Language

**Document ID:** DL-001
**Version:** 0.2.0
**Status:** Draft
**Last Updated:** 2026-08-09

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

These product-level rules use the `DLR-` prefix to distinguish them from the SPEC-005 domain rules (`DR-001`–`DR-010`), which are documented in the Assessment Domain Model (SPEC-005) section above.

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
