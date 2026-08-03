# Fablit Project Charter

**Document ID:** PC-001
**Version:** 0.1.0
**Status:** Draft
**Last Updated:** 2026-07-26

---

# Purpose

This Project Charter defines the purpose, vision, scope, objectives, and guiding philosophy of the Fablit project.

It serves as the primary reference for contributors, maintainers, educators, and AI assistants participating in the development of the platform.

This document intentionally avoids implementation details.

Those are documented separately within the architecture and engineering documentation.

---

# Project Vision

Fablit is an open-source educational platform designed to help learners develop practical skills through deliberate practice, meaningful feedback, and continuous reflection.

Rather than focusing solely on examination preparation, Fablit aims to build transferable skills that remain valuable beyond any single assessment.

---

# Mission

Our mission is to create a modular learning platform where educators, contributors, and learners collaborate to build high-quality skill development experiences.

The platform should enable learners to:

- practice regularly
- receive constructive feedback
- reflect on their learning
- measure long-term improvement
- build confidence through continuous progress

---

# Problem Statement

Many educational platforms primarily measure performance.

Few platforms actively develop skills.

Students preparing for competitive examinations often receive:

- mock tests
- scores
- rankings

but receive limited guidance on:

- improving communication
- strengthening creative thinking
- developing observation skills
- building confidence
- reflecting on mistakes

Fablit exists to bridge that gap.

---

# Initial Product Focus

The first implementation of Fablit focuses on supporting learners preparing for design entrance examinations.

The initial Content Pack will target:

- NIFT Entrance Preparation

The architecture, however, is intentionally designed to support future educational domains without requiring changes to the platform core.

---

# Target Audience

Primary users include:

- NIFT aspirants
- Design entrance examination candidates
- Students developing communication and creative skills

Future audiences may include:

- educators
- mentors
- institutions
- researchers
- lifelong learners

---

# Project Objectives

The project aims to:

- build an extensible educational platform
- encourage deliberate practice
- provide meaningful feedback
- support modular Skill Labs
- support reusable Content Packs
- encourage open-source collaboration
- remain approachable for new contributors

---

# Scope

## In Scope

The platform will initially provide:

- Skill Labs
- Assessments
- Assessment Activities
- Feedback
- Reflection
- Progress Tracking
- Learning Resources
- Content Packs
- AI-assisted evaluation
- Analytics for learning improvement

---

## Out of Scope

The project is not intended to become:

- a general-purpose Learning Management System (LMS)
- a video conferencing platform
- a social networking platform
- a proprietary AI platform
- an examination authority
- a replacement for classroom education

These capabilities may integrate with Fablit but are not core objectives.

---

# Success Criteria

The project will be considered successful when:

- learners improve measurable skills through practice
- contributors can easily extend the platform
- new Skill Labs can be developed independently
- new Content Packs require minimal engineering effort
- documentation remains clear and current
- automated quality checks remain reliable

---

# Guiding Principles

The project follows the Architecture Principles defined in:

```
docs/architecture/architecture-principles.md
```

Key themes include:

- Skills before examinations
- Practice before theory
- Feedback before scoring
- Reflection completes learning
- Platform before content
- Specification before implementation

---

# Engineering Philosophy

Development follows an Architecture-First workflow.

```
Idea

↓

Architecture

↓

Specification

↓

Review

↓

GitHub Issue

↓

Implementation

↓

Testing

↓

Documentation

↓

Release
```

Every implementation should trace back to a documented specification.

---

# Product Philosophy

Fablit believes that effective learning follows a continuous cycle.

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

Every feature introduced into the platform should support one or more stages of this learning cycle.

---

# Open Source Philosophy

Fablit is designed as an open-source project.

The project values:

- transparency
- collaboration
- maintainability
- accessibility
- continuous improvement

Contributors are encouraged to propose ideas through Discussions, document architectural decisions, and participate in constructive technical reviews.

---

# Quality Attributes

The platform prioritizes:

- Maintainability
- Extensibility
- Testability
- Accessibility
- Simplicity
- Reliability
- Documentation

Performance and scalability should never compromise code clarity during the early stages of the project.

---

# Risks

The project recognises several long-term risks:

- unnecessary architectural complexity
- premature optimisation
- feature creep
- inconsistent terminology
- undocumented decisions
- over-reliance on AI-generated code

These risks are mitigated through documentation, code reviews, specifications, and Architecture Decision Records (ADRs).

---

# Roadmap

The project will evolve incrementally.

### Phase 1

Platform Foundation

- repository
- architecture
- documentation
- engineering workflow

---

### Phase 2

Core Platform

- backend foundation
- frontend foundation
- CI/CD
- deployment
- testing

---

### Phase 3

Learning Platform

- Skill Labs
- Assessments
- Feedback
- Progress

---

### Phase 4

Content Ecosystem

- NIFT Content Pack
- additional Content Packs
- AI-assisted learning
- plugin ecosystem

---

# Project Governance

Major architectural decisions should be documented through ADRs.

Feature development should begin with specifications.

Pull Requests should satisfy:

- implementation
- testing
- documentation
- review
- successful CI

---

# Long-Term Vision

Fablit aspires to become a platform that enables educators and contributors to create reusable, high-quality learning experiences across multiple disciplines.

The platform should evolve through extension rather than large-scale rewrites, preserving a stable architecture while supporting continuous innovation.

---

# North Star

> Build skills through deliberate practice, meaningful feedback, and continuous improvement.

This statement should guide every architectural, product, and engineering decision made within the project.
