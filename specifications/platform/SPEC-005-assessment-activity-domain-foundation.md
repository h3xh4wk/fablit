# SPEC-005 — Assessment Activity Domain Foundation

**Specification ID:** SPEC-005
**Title:** Assessment Activity Domain Foundation
**Version:** 0.2.0
**Status:** Implemented
**Priority:** High
**Epic:** Learning Platform

---

# Purpose

Introduce the first learning-domain capability into Fablit by establishing the foundational domain model for Assessments and Assessment Activities.

This specification creates the smallest meaningful learner-interaction boundary defined by the Fablit Domain Language while preserving the separation between:

* platform infrastructure
* learning-domain behaviour
* educational content

The implementation shall establish the domain concepts and relationships required for future learner submissions, evaluation, feedback, reflection, and progress.

This specification does not implement the complete learning cycle.

---

# Background

The Fablit Project Charter defines the product around a continuous learning cycle:

```text
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

Fablit is intended to develop transferable skills through deliberate practice rather than merely measure examination performance.

The Architecture Blueprint defines an Assessment as a structured collection of Assessment Activities and identifies an Assessment Activity as the smallest unit of learner interaction.

Every Assessment Activity produces a learner Submission.

This specification introduces the first part of that model without implementing Submission or the downstream evaluation pipeline.

---

# Architectural Intent

SPEC-005 marks the transition from platform infrastructure to learning-domain functionality.

The platform foundation established by SPEC-001 through SPEC-004 shall remain reusable and independent of the educational domain.

The new domain functionality shall depend on the platform where necessary but shall not introduce educational-domain concepts into the shared platform layer.

Conceptually:

```text
┌─────────────────────────────────────────┐
│            Learning Domain              │
│                                         │
│ Assessment                              │
│      │                                  │
│      └── Assessment Activity             │
└───────────────────┬─────────────────────┘
                    │
                    │ uses
                    ▼
┌─────────────────────────────────────────┐
│           Shared Platform               │
│                                         │
│ Config · Logging · Health · Metrics     │
│ Auth · Resilience · Utilities           │
└─────────────────────────────────────────┘
```

---

# Objectives

SPEC-005 shall:

* introduce the Assessment domain concept
* introduce the Assessment Activity domain concept
* establish the relationship between an Assessment and its Activities
* define the minimum lifecycle and state required for these concepts
* validate Assessment Activity definitions
* preserve domain terminology defined by the Domain Language
* provide testable domain behaviour
* establish a foundation for future Submission handling
* avoid introducing unnecessary infrastructure
* remain independent of examination-specific concepts

---

# Scope

## In Scope

* Assessment domain model
* Assessment Activity domain model
* Assessment-to-Activity relationship
* Activity ordering
* Activity identity
* Activity type
* Activity instructions or prompt reference
* Activity status
* Assessment identity
* Assessment metadata
* Assessment lifecycle validation
* Domain-level validation
* Automated tests for the new domain behaviour

---

## Out of Scope

The following are explicitly excluded from SPEC-005:

* Learner accounts
* User management
* Authentication workflows
* Database persistence
* Assessment delivery UI
* Submission implementation
* Evaluation
* AI-assisted evaluation
* Feedback
* Reflection
* Progress tracking
* Analytics
* Notifications
* Content Packs
* Skill Lab implementation
* Examination-specific workflows
* External content-management systems
* External AI services

---

# Domain Concepts

## Assessment

An Assessment is a structured collection of Assessment Activities.

An Assessment may represent experiences such as:

* Mock Test
* Daily Practice
* Weekly Challenge
* Skill Evaluation

The specific educational purpose of an Assessment shall not be hard-coded into the platform.

An Assessment defines the ordered set of activities that make up the experience.

---

## Assessment Activity

An Assessment Activity is the smallest meaningful interaction between a learner and the Fablit platform.

An Assessment Activity defines an interaction that will eventually produce a Submission.

Examples include:

* Multiple Choice Question
* Writing Exercise
* Observation Exercise
* Interview Response
* Sketch Submission
* Portfolio Review
* Reflection

The implementation shall not require all activity types to be fully executable in SPEC-005.

The domain model shall provide a stable foundation for future activity implementations.

---

# Domain Relationships

The relationship established by this specification is:

```text
Assessment
    │
    ├── Activity 1
    ├── Activity 2
    ├── Activity 3
    └── ...
```

Each Assessment Activity belongs to an Assessment.

Activities have an explicit order within their Assessment.

The ordering of activities is part of the Assessment definition.

---

# Functional Requirements

## FR-001 — Assessment Identity

Each Assessment shall have a unique domain identity.

The identity shall remain stable for the lifetime of the Assessment.

---

## FR-002 — Assessment Metadata

An Assessment shall support the minimum metadata necessary to describe the assessment experience.

At minimum this shall include:

* title
* description or purpose
* status

The implementation shall avoid introducing additional metadata unless required by a concrete use case.

---

## FR-003 — Assessment Activity Identity

Each Assessment Activity shall have a unique domain identity.

The identity shall remain stable for the lifetime of the activity.

---

## FR-004 — Activity Type

Each Assessment Activity shall declare an activity type.

The activity type shall be represented using controlled domain terminology rather than arbitrary free-form strings where practical.

The initial implementation shall provide a small extensible representation rather than implementing every possible activity type.

---

## FR-005 — Activity Ordering

Assessment Activities shall have an explicit order within their Assessment.

The ordering shall be deterministic.

An Assessment shall not contain two activities with the same position.

---

## FR-006 — Activity Instructions

An Assessment Activity shall support instructions or a prompt reference describing the learner interaction.

The implementation shall not embed educational content directly into platform infrastructure.

---

## FR-007 — Assessment Composition

An Assessment shall support one or more Assessment Activities.

Activities shall belong to exactly one Assessment within the scope of the domain model established by this specification.

---

## FR-008 — Activity Validation

An Assessment Activity shall be rejected when required domain information is missing or invalid.

Examples include:

* missing identity
* missing activity type
* missing instructions or prompt reference
* invalid ordering information

---

## FR-009 — Assessment Validation

An Assessment shall be rejected when its required domain information is invalid.

An Assessment shall not contain duplicate activity positions.

---

## FR-010 — Domain Independence

Assessment and Assessment Activity models shall not contain examination-specific concepts.

The same domain model shall be usable for:

* design education
* communication practice
* research methodology
* creative practice
* future educational domains

---

## FR-011 — Submission Boundary

The Assessment Activity model shall define the boundary at which a future Submission can be associated with learner work.

SPEC-005 shall not implement the Submission domain model.

---

## FR-012 — Feedback Boundary

Assessment Activities shall be designed so that future Evaluation can interpret a resulting Submission and produce Feedback.

SPEC-005 shall not implement Evaluation or Feedback.

---

# Domain Rules

The following rules shall be enforced by the domain model.

### DR-001

An Assessment must have a unique identity.

### DR-002

An Assessment Activity must have a unique identity.

### DR-003

An Assessment must contain at least one Assessment Activity.

### DR-004

An Assessment Activity belongs to one Assessment.

### DR-005

Assessment Activities have deterministic ordering within an Assessment.

### DR-006

Activity ordering must not contain duplicate positions.

### DR-007

An Assessment Activity must declare a valid activity type.

### DR-008

An Assessment Activity must contain sufficient information to describe the learner interaction.

### DR-009

Assessment and Assessment Activity shall remain independent of examination-specific terminology.

### DR-010

The domain model shall not require persistence infrastructure.

---

# Activity Types

The first implementation shall support a minimal set of activity types sufficient to prove the domain model.

The initial set should be deliberately small.

Possible initial types include:

* multiple choice
* written response
* observation
* reflection

Additional activity types shall be introduced through subsequent specifications when concrete requirements exist.

The implementation shall avoid creating a large enumeration of speculative activity types.

---

# Lifecycle

SPEC-005 establishes the minimum lifecycle required for defining an Assessment.

An Assessment shall support a lifecycle that distinguishes an editable definition from an available learning experience.

The exact runtime delivery lifecycle is intentionally deferred.

The implementation should provide only the states required to enforce the domain rules introduced by this specification.

Future specifications may extend the lifecycle when learner delivery, submission, evaluation, or completion behaviour is introduced.

---

# Content Boundary

Assessment Activities may refer to educational content, but SPEC-005 shall not implement a complete Content Pack or Learning Resource system.

Educational content should remain representable as structured data rather than being hard-coded into domain logic wherever practical.

This preserves the Content Before Code principle.

---

# API Boundary

SPEC-005 is primarily a domain-foundation specification.

An HTTP API is not required unless needed to demonstrate or consume the domain behaviour.

If an API is introduced, it shall expose domain concepts rather than framework-specific implementation details.

The API shall not become a reason to introduce persistence, authentication, or frontend functionality prematurely.

---

# Persistence Boundary

No database or persistence technology is required by SPEC-005.

The domain model shall be usable in memory.

Persistence shall be introduced through a future specification when the learning workflow requires durable storage.

This keeps the domain model independent of infrastructure choices.

---

# Testing Requirements

SPEC-005 shall include automated tests for the externally observable domain behaviour.

Tests shall cover at least:

* Assessment creation
* Assessment Activity creation
* Assessment identity validation
* Assessment Activity identity validation
* Activity type validation
* Activity ordering
* duplicate activity-order rejection
* Assessment composition
* minimum activity requirement
* invalid domain state rejection
* domain independence from examination-specific concepts

Tests should focus on domain behaviour rather than implementation details.

---

# Acceptance Criteria

SPEC-005 is complete when:

* [x] An Assessment domain model exists.
* [x] An Assessment Activity domain model exists.
* [x] Assessments have stable identities.
* [x] Assessment Activities have stable identities.
* [x] Assessment Activities belong to an Assessment.
* [x] Assessment Activities have deterministic ordering.
* [x] Duplicate activity positions are rejected.
* [x] Assessments cannot exist without the required minimum activity structure.
* [x] Assessment Activities require valid activity types.
* [x] Assessment Activities contain sufficient interaction information.
* [x] Invalid domain states are rejected.
* [x] The domain model contains no examination-specific concepts.
* [x] The domain model does not require a database.
* [x] Automated tests cover the domain rules.
* [x] Existing platform tests continue to pass.
* [x] CI quality gates continue to pass.
* [x] Documentation reflects the implemented domain model.

---

# Implementation

The implemented learning-domain foundation is organized as:

```text
fablit/
└── domain/
    ├── __init__.py
    ├── activity.py
    ├── assessment.py
    └── types.py
```

The domain package provides in-memory models for Assessments and Assessment Activities, together with the controlled terminology and domain errors they require.

The domain layer is intentionally independent of platform infrastructure and persistence: it can be imported and used in memory without framework or database dependencies.

Automated tests under `tests/domain` cover the externally observable domain behaviour, including validation, composition, ordering, and domain independence.

---

# Architectural Constraints

SPEC-005 shall comply with the following Architecture Principles:

## AP-001 — Skills Before Examinations

The model shall not be designed around NIFT, NID, CEED, or any other examination.

Assessment Activities must represent transferable learning interactions.

---

## AP-002 — Practice Before Theory

The domain model shall represent learner activity rather than passive content consumption.

---

## AP-003 — Feedback Before Scoring

The model shall preserve a clear boundary for future Evaluation and Feedback.

The specification shall not optimize the domain around scores alone.

---

## AP-004 — Reflection Completes Learning

Reflection remains part of the future learning cycle.

SPEC-005 shall not prevent Assessment Activities from eventually supporting reflection.

---

## AP-005 — Platform Before Content

The domain implementation shall not introduce examination-specific or institution-specific logic into the shared platform layer.

---

## AP-006 — Content Before Code

Educational content should remain separable from executable domain logic wherever practical.

---

## AP-007 — Modular by Default

Assessment Activities shall be represented so that additional activity types can be introduced without modifying unrelated platform components.

---

## AP-008 — Simplicity Over Complexity

Only the minimum domain structure required for this specification shall be implemented.

No database, message broker, external AI provider, plugin framework, or distributed architecture shall be introduced solely for SPEC-005.

---

## AP-010 — Specification Before Implementation

Implementation shall begin only after this specification has been reviewed and converted into an implementation issue.

---

## AP-011 — Testability is a Feature

Every significant domain rule introduced by SPEC-005 shall have automated test coverage.

---

## AP-012 — Documentation is Part of the Product

The Domain Language and relevant architecture documentation shall remain aligned with the implementation.

---

# Relationship to Previous Specifications

SPEC-005 builds upon the platform foundation established by:

* SPEC-001 — Bootstrap Platform
* SPEC-002 — Engineering Toolchain
* SPEC-003 — Configuration & Logging
* SPEC-004 — Shared Platform Services

The learning-domain implementation shall consume platform capabilities where appropriate without moving domain concepts into the platform layer.

---

# Relationship to Future Specifications

SPEC-005 establishes the foundation for subsequent learning-domain capabilities.

The expected conceptual progression is:

```text
SPEC-005
Assessment Activity Domain Foundation
        │
        ▼
SPEC-006
Submission
        │
        ▼
SPEC-007
Evaluation
        │
        ▼
SPEC-008
Feedback
        │
        ▼
SPEC-009
Reflection
        │
        ▼
SPEC-010
Progress
```

This progression is indicative rather than binding.

Future specifications may adjust the sequence when architectural or product requirements justify doing so.

---

# Future Extension Points

Future specifications may introduce:

* additional Assessment Activity types
* richer Assessment lifecycle behaviour
* learner-specific assessment instances
* Submission handling
* Evaluation strategies
* AI-assisted evaluation
* Feedback generation
* Reflection workflows
* Progress tracking
* Skill Labs
* Content Packs

These capabilities shall be introduced through separate specifications rather than being included speculatively in SPEC-005.

---

# Definition of Done

SPEC-005 is considered complete when:

* the Assessment domain model is implemented
* the Assessment Activity domain model is implemented
* domain relationships are validated
* domain rules are covered by automated tests
* the implementation remains independent of persistence infrastructure
* no examination-specific concepts are introduced into the domain model
* existing platform behaviour remains intact
* all automated quality checks pass
* documentation is updated
* the implementation has been reviewed
* the corresponding GitHub issue and Pull Request are complete

---

# North Star Alignment

SPEC-005 contributes to the Fablit North Star:

> Build skills through deliberate practice, meaningful feedback, and continuous improvement.

It establishes the first domain-level representation of deliberate practice and assessment while leaving the later stages of the learning cycle to subsequent specifications.
