# Fablit Architecture Blueprint

**Document ID:** AB-001
**Version:** 0.1.0
**Status:** Draft
**Last Updated:** 2026-08-09

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
