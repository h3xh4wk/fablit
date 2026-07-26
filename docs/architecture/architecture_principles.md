# Fablit Architecture Principles

**Document ID:** AP-001  
**Version:** 0.1.0  
**Status:** Draft  
**Last Updated:** 2026-07-26

---

# Purpose

This document defines the architectural principles that guide the design and evolution of the Fablit platform.

Unlike implementation details or technology choices, these principles are intended to remain stable over the lifetime of the project. Every architectural decision, feature proposal, and implementation should be evaluated against these principles.

---

# Vision

Fablit is an open-source platform that helps learners develop practical skills through deliberate practice, meaningful feedback, and continuous reflection.

The platform is designed to be domain-independent while supporting specialized content packs such as fashion education, design entrance examinations, research methodology, communication skills, and future disciplines.

---

# Guiding Principles

## AP-001 — Skills Before Examinations

The platform exists to develop transferable skills.

Preparing for an examination is only one application of those skills.

The architecture should therefore model skills and learning experiences rather than examination-specific workflows.

---

## AP-002 — Practice Before Theory

Learning occurs through practice.

Every concept introduced within the platform should encourage the learner to perform an activity rather than passively consume information.

Reading supports practice.

Practice drives learning.

---

## AP-003 — Feedback Before Scoring

Scores communicate performance.

Feedback develops capability.

Every assessment activity should attempt to provide meaningful, actionable feedback rather than only numerical scores.

---

## AP-004 — Reflection Completes Learning

An assessment is not complete when an answer is submitted.

Learning concludes only after the learner has reflected upon the received feedback.

Reflection is therefore considered a first-class learning activity.

---

## AP-005 — Platform Before Content

The platform provides capabilities.

Content Packs provide subject matter.

The platform must remain independent of any specific examination, institution, or educational discipline.

Examples include:

- NIFT
- NID
- CEED
- Fashion Communication
- Research Methods

These belong to Content Packs, not the platform core.

---

## AP-006 — Content Before Code

Educational content should be represented as structured content rather than hardcoded application logic whenever practical.

Examples include:

- exercises
- prompts
- rubrics
- assessments
- interview questions
- evaluation criteria

This enables educators and contributors to expand the platform without modifying software.

---

## AP-007 — Modular by Default

New functionality should be added through modular components with clearly defined interfaces.

The addition of a new Skill Lab should not require modifications to unrelated parts of the platform.

---

## AP-008 — Simplicity Over Complexity

Prefer simple, understandable solutions.

Architectural complexity must only be introduced when justified by measurable benefits.

The platform should remain approachable for individual contributors as well as larger teams.

---

## AP-009 — AI as a Collaborator

Artificial Intelligence assists development and learning.

Human judgment remains responsible for:

- architecture
- educational quality
- ethical decisions
- final review

AI should accelerate implementation without replacing thoughtful design.

---

## AP-010 — Specification Before Implementation

Every feature should begin with a written specification.

Implementation follows review and approval.

The preferred lifecycle is:

Specification

↓

Architecture Review

↓

Implementation

↓

Testing

↓

Documentation

---

## AP-011 — Testability is a Feature

Every significant capability should be testable.

Automated testing is considered part of the feature rather than an optional activity.

Where appropriate, features should include:

- unit tests
- integration tests
- end-to-end tests

---

## AP-012 — Documentation is Part of the Product

Documentation is not an afterthought.

Architectural decisions, specifications, and implementation guidance are maintained alongside source code.

Every major architectural decision should be discoverable by future contributors.

---

# Architectural Layers

Fablit is organised into four conceptual layers.

```
Vision
    ↓
Platform
    ↓
Skill Labs
    ↓
Content Packs
```

Each layer builds upon the previous without violating its responsibilities.

---

# Engineering Philosophy

Development follows an Architecture-First workflow.

```
Architecture

↓

Specification

↓

GitHub Issue

↓

Implementation

↓

Testing

↓

Review

↓

Merge

↓

Release
```

This approach reduces ambiguity, improves maintainability, and enables effective AI-assisted software development.

---

# Long-Term Goals

The architecture should support:

- multiple educational domains
- multiple assessment formats
- plugin-based Skill Labs
- AI-assisted feedback
- open-source collaboration
- gradual evolution without large rewrites

---

# Success Criteria

The architecture is considered successful if:

- new Skill Labs can be added without changing the platform core
- new Content Packs require minimal engineering effort
- contributors can understand the project structure quickly
- architectural decisions remain understandable years later
- the platform evolves through extension rather than modification

---
# Non-Goals

At this stage, Fablit is not intended to:

- become a general-purpose Learning Management System (LMS)
- replace classroom teaching
- depend on proprietary AI services
- require cloud-native infrastructure for local development
- optimize for premature scalability over simplicity

These constraints help keep the platform focused on its core mission.

# Closing Statement

Fablit is designed as a platform for developing skills rather than delivering courses.

Every architectural decision should reinforce the platform's mission:

> Build skills through deliberate practice, meaningful feedback, and continuous improvement.