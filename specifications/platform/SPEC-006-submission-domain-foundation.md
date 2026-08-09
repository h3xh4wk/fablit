# SPEC-006 — Submission Domain Foundation

**Specification ID:** SPEC-006
**Title:** Submission Domain Foundation
**Version:** 0.1.0
**Status:** Draft
**Priority:** High
**Epic:** Learning Platform

---

# Purpose

Introduce the Submission domain concept into Fablit.

A Submission represents a learner's response to an Assessment Activity and establishes the domain boundary between a learner interaction and the future evaluation process.

This specification builds upon the Assessment and Assessment Activity foundation established by SPEC-005.

The implementation shall provide a minimal, testable Submission model without introducing evaluation, feedback, persistence, authentication, or learner-management infrastructure.

---

# Background

Fablit's learning cycle is:

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

SPEC-005 established the Assessment and Assessment Activity concepts.

The next domain boundary is the learner's response to an Assessment Activity.

The Domain Language defines a Submission as the learner's response to an Assessment Activity.

A Submission may represent different forms of learner work, including:

* written responses
* multiple-choice selections
* sketches
* uploaded work
* interview responses
* observations
* reflections

The Submission model should therefore describe the learner's work without embedding evaluation logic.

---

# Architectural Intent

SPEC-006 introduces the first learner-produced domain object.

The relationship established by this specification is:

```text
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

The Submission belongs to the learning domain.

It shall not be implemented as part of the shared platform layer.

The implementation shall remain independent of:

* authentication providers
* databases
* HTTP frameworks
* AI providers
* evaluation engines
* feedback systems

---

# Objectives

SPEC-006 shall:

* introduce the Submission domain concept
* establish the relationship between Submission and Assessment Activity
* associate a Submission with a learner identity
* represent learner-provided response data
* support different response forms without premature specialization
* define the minimum Submission lifecycle
* validate Submission domain invariants
* preserve the boundary between submission and evaluation
* provide automated tests for Submission behaviour
* remain independent of persistence infrastructure

---

# Scope

## In Scope

* Submission domain model
* Learner identity reference
* Assessment Activity reference
* Submission identity
* Submission response data
* Submission status
* Submission timestamps where required by domain behaviour
* Submission validation
* Submission lifecycle foundation
* Automated tests

---

## Out of Scope

The following are explicitly excluded from SPEC-006:

* full Learner domain model
* learner profiles
* user registration
* authentication
* authorization
* database persistence
* file storage
* object storage
* HTTP API
* frontend submission forms
* submission scoring
* evaluation
* AI-assisted evaluation
* feedback
* reflection
* progress tracking
* analytics
* notifications
* plagiarism detection
* examination-specific submission rules

---

# Domain Concepts

## Submission

A Submission is a learner's response to an Assessment Activity.

A Submission captures the learner's work at a particular point in the learning process.

A Submission is not an evaluation.

A Submission is not a score.

A Submission is not feedback.

These concerns belong to later stages of the learning cycle.

---

## Learner Identity

SPEC-006 requires a minimal learner identity reference so that a Submission can identify who produced it.

This is not a complete Learner domain model.

The learner identity should be represented using a stable domain identifier.

The implementation shall not introduce:

* learner profiles
* authentication credentials
* personal preferences
* account management
* authorization rules

Those concerns belong to other domain or platform specifications.

---

## Assessment Activity Reference

Every Submission shall reference the Assessment Activity to which the learner is responding.

The reference shall use the stable identity established by SPEC-005.

A Submission shall not duplicate the complete Assessment Activity definition.

---

# Submission Structure

The conceptual structure is:

```text
Submission
├── id
├── learner_id
├── activity_id
├── response
├── status
└── timestamps
```

The exact representation of response data shall remain intentionally small and extensible.

---

# Response Representation

Assessment Activities can require different forms of learner response.

SPEC-006 shall therefore avoid creating a large hierarchy of submission types prematurely.

The initial Submission model should support a generic response representation that can evolve as concrete activity types require richer data.

Examples include:

```text
text response
multiple-choice selection
structured response
observation response
reflection response
reference to uploaded work
```

SPEC-006 does not require implementation of file-upload infrastructure.

A future specification may introduce a richer representation for binary or externally stored learner artifacts.

---

# Functional Requirements

## FR-001 — Submission Identity

Each Submission shall have a unique domain identity.

The identity shall remain stable for the lifetime of the Submission.

---

## FR-002 — Learner Association

Each Submission shall identify the learner who produced it.

The learner shall be represented by a stable domain identifier.

---

## FR-003 — Activity Association

Each Submission shall identify the Assessment Activity to which it responds.

The reference shall use the Assessment Activity identity established by SPEC-005.

---

## FR-004 — Response

Each Submission shall contain the learner's response.

A response shall not be empty when the selected Submission state requires learner work to be present.

The response representation shall support future extension without requiring a redesign of the Submission aggregate.

---

## FR-005 — Submission Status

A Submission shall have an explicit status.

The initial lifecycle shall support at least:

* Draft
* Submitted

Additional lifecycle states shall not be introduced unless required by a concrete use case.

---

## FR-006 — Draft Behaviour

A Draft Submission represents learner work that has not yet been submitted for evaluation.

A Draft may be incomplete.

The domain shall distinguish an editable Draft from a completed Submission.

---

## FR-007 — Submitted Behaviour

A Submitted Submission represents learner work that has been submitted for subsequent processing.

A Submitted Submission shall contain the required learner response.

---

## FR-008 — Submission Immutability After Submission

Once a Submission reaches the Submitted state, its learner response and core associations shall not be silently modified.

If the product later requires revisions, resubmissions, or attempts, those behaviours shall be introduced through a separate specification.

---

## FR-009 — Submission Timestamp

A Submitted Submission shall record the time at which it was submitted.

The timestamp shall be part of the domain state rather than being inferred solely from infrastructure metadata.

---

## FR-010 — Domain Validation

The Submission model shall reject invalid domain states.

Examples include:

* missing Submission identity
* missing learner identity
* missing Assessment Activity identity
* invalid status
* missing response for a Submitted Submission
* missing submission timestamp for a Submitted Submission

---

## FR-011 — Activity Ownership Boundary

The Submission shall reference an Assessment Activity but shall not duplicate or own the Assessment Activity definition.

---

## FR-012 — Evaluation Boundary

The Submission shall provide sufficient information for a future Evaluation component to consume the learner's work.

SPEC-006 shall not implement Evaluation.

---

## FR-013 — Feedback Boundary

The Submission model shall preserve a clear boundary for future Feedback.

Feedback shall not be stored as part of the Submission unless a future specification explicitly defines such behaviour.

---

# Domain Rules

The following rules shall be enforced by the domain model.

### DR-001

A Submission must have a unique identity.

### DR-002

A Submission must identify a learner.

### DR-003

A Submission must identify an Assessment Activity.

### DR-004

A Submission must contain a response appropriate to its lifecycle state.

### DR-005

A Draft Submission may be incomplete.

### DR-006

A Submitted Submission must contain the required learner response.

### DR-007

A Submitted Submission must contain a submission timestamp.

### DR-008

A Submitted Submission shall not allow silent modification of its core learner response or associations.

### DR-009

A Submission shall reference an Assessment Activity by identity.

### DR-010

A Submission shall not contain evaluation results.

### DR-011

A Submission shall not contain feedback.

### DR-012

A Submission shall not require persistence infrastructure.

### DR-013

A Submission shall not contain examination-specific concepts.

---

# Lifecycle

The initial Submission lifecycle is intentionally small:

```text
Draft
  │
  │ submit
  ▼
Submitted
```

The lifecycle shall not include evaluation states at this stage.

Future specifications may introduce:

```text
Submitted
    │
    ▼
Evaluated
    │
    ▼
Feedback Available
    │
    ▼
Reflected
```

These states are illustrative only and shall not be implemented by SPEC-006.

---

# Revision and Resubmission

SPEC-006 intentionally does not implement revision or resubmission behaviour.

A learner may eventually need to:

* revise a response
* submit a new attempt
* respond to feedback
* improve an earlier submission

These behaviours have implications for evaluation history and progress tracking.

They should therefore be introduced through a dedicated specification rather than being embedded into the initial Submission model.

---

# Learner Model Boundary

SPEC-006 shall not create a complete Learner aggregate.

Only the minimum learner identity required by Submission shall be represented.

Conceptually:

```text
Learner Identity
       │
       │ referenced by
       ▼
   Submission
```

A future Learner specification may introduce:

* learner profile
* preferences
* skill history
* progress
* enrolment
* learning goals

SPEC-006 shall not anticipate those structures unnecessarily.

---

# Persistence Boundary

No database or persistence technology is required by SPEC-006.

The Submission domain model shall be usable in memory.

Persistence shall be introduced when a concrete workflow requires durable Submission storage.

The domain model shall remain independent of the selected persistence technology.

---

# File and Artifact Boundary

Some Assessment Activities may eventually accept:

* images
* documents
* sketches
* audio
* video
* portfolio artifacts

SPEC-006 shall not introduce file-storage infrastructure.

Where a future Submission needs to reference an externally stored artifact, that behaviour should be introduced through a separate specification.

---

# API Boundary

An HTTP API is not required by SPEC-006.

The primary objective is to establish the domain model and its invariants.

If an API is introduced later, it shall expose domain behaviour rather than framework-specific implementation details.

---

# Evaluation Boundary

Evaluation is a separate domain concern.

The conceptual relationship is:

```text
Submission
    │
    │ consumed by
    ▼
Evaluation
    │
    ▼
Evaluation Result
```

SPEC-006 establishes only the first part of this relationship.

Evaluation logic shall be introduced through a future specification.

This includes:

* human evaluation
* rule-based evaluation
* AI-assisted evaluation
* scoring
* qualitative assessment

---

# Feedback Boundary

Feedback follows Evaluation in the Fablit learning cycle.

The conceptual relationship is:

```text
Submission
    │
    ▼
Evaluation
    │
    ▼
Feedback
```

SPEC-006 shall not introduce feedback behaviour.

This preserves the architectural principle that meaningful feedback should not be reduced to a score.

---

# Testing Requirements

SPEC-006 shall include automated tests for externally observable Submission behaviour.

Tests shall cover at least:

* Submission creation
* Submission identity
* learner association
* Assessment Activity association
* Draft creation
* Submitted state
* submission validation
* empty response validation
* submission timestamp
* transition from Draft to Submitted
* protection of Submitted state
* invalid domain state rejection
* independence from persistence infrastructure
* absence of evaluation and feedback concerns

Tests should focus on domain behaviour rather than implementation details.

---

# Acceptance Criteria

SPEC-006 is complete when:

* [ ] A Submission domain model exists.
* [ ] A Submission has a stable identity.
* [ ] A Submission references a learner identity.
* [ ] A Submission references an Assessment Activity.
* [ ] A Submission contains learner response data.
* [ ] Draft and Submitted states are supported.
* [ ] Draft Submissions may be incomplete.
* [ ] Submitted Submissions contain the required response.
* [ ] Submitted Submissions record a submission timestamp.
* [ ] Submitted Submission core data cannot be silently modified.
* [ ] Invalid Submission states are rejected.
* [ ] Evaluation is not implemented.
* [ ] Feedback is not implemented.
* [ ] A complete Learner domain model is not introduced.
* [ ] Persistence is not required.
* [ ] File-storage infrastructure is not introduced.
* [ ] Automated tests cover the Submission domain rules.
* [ ] Existing SPEC-005 tests continue to pass.
* [ ] Existing platform tests continue to pass.
* [ ] CI quality gates continue to pass.
* [ ] Documentation reflects the implemented Submission domain.

---

# Architectural Constraints

SPEC-006 shall comply with the project's Architecture Principles.

## Skills Before Examinations

Submission shall represent learner work in a transferable learning context.

The domain shall not introduce NIFT-, NID-, CEED-, or other examination-specific submission concepts.

---

## Practice Before Theory

Submission shall represent an actual learner interaction with an Assessment Activity.

---

## Feedback Before Scoring

Submission shall remain independent of scoring and evaluation.

A Submission is evidence of learner work, not a measure of learner ability.

---

## Reflection Completes Learning

The Submission model shall not prevent future reflection on submitted work.

Reflection shall remain a separate learning-domain concern.

---

## Platform Before Content

Submission belongs to the learning domain and shall not introduce educational business rules into the shared platform.

---

## Content Before Code

Submission shall represent learner responses without embedding educational content directly into executable platform logic.

---

## Modular by Default

Submission shall depend on Assessment Activity through a stable domain boundary.

Future activity types shall not require unrelated platform changes.

---

## Simplicity Over Complexity

SPEC-006 shall implement only the minimum Submission model required by the current learning-domain workflow.

No database, object-storage system, message broker, external AI service, or distributed architecture shall be introduced solely for this specification.

---

## Specification Before Implementation

Implementation shall begin only after SPEC-006 has been reviewed and converted into a GitHub issue.

---

## Testability is a Feature

Every significant Submission domain rule shall have automated test coverage.

---

## Documentation is Part of the Product

The Domain Language and relevant architecture documentation shall remain aligned with the implementation.

---

# Relationship to Previous Specifications

SPEC-006 builds upon:

* SPEC-001 — Bootstrap Platform
* SPEC-002 — Engineering Toolchain
* SPEC-003 — Configuration & Logging
* SPEC-004 — Shared Platform Services
* SPEC-005 — Assessment Activity Domain Foundation

SPEC-005 establishes the Assessment and Assessment Activity concepts consumed by Submission.

SPEC-006 shall not modify the responsibilities of the shared platform specifications.

---

# Relationship to Future Specifications

SPEC-006 establishes the foundation for subsequent learning-domain capabilities.

The expected conceptual progression is:

```text
SPEC-005
Assessment Activity
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

This sequence is indicative rather than binding.

Future specifications may adjust the sequence when architectural or product requirements justify doing so.

---

# Future Extension Points

Future specifications may introduce:

* richer response types
* learner profiles
* submission attempts
* revision and resubmission
* artifact references
* persistent Submission storage
* Evaluation
* AI-assisted Evaluation
* scoring
* Feedback
* Reflection
* Progress tracking
* analytics
* Skill Labs
* Content Packs

These capabilities shall be introduced through separate specifications rather than being included speculatively in SPEC-006.

---

# Definition of Done

SPEC-006 is considered complete when:

* the Submission domain model is implemented
* learner identity association is implemented
* Assessment Activity association is implemented
* Submission lifecycle rules are implemented
* domain invariants are enforced
* automated tests cover the domain rules
* the implementation remains independent of persistence infrastructure
* evaluation and feedback remain outside the Submission model
* no examination-specific concepts are introduced
* existing platform and SPEC-005 behaviour remains intact
* all automated quality checks pass
* documentation is updated
* the implementation has been reviewed
* the corresponding GitHub issue and Pull Request are complete

---

# North Star Alignment

SPEC-006 contributes to the Fablit North Star:

> Build skills through deliberate practice, meaningful feedback, and continuous improvement.

It establishes the learner-work boundary required to move from Assessment into Evaluation and Feedback while deliberately keeping those later stages outside the scope of this specification.
