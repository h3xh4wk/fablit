# SPEC-007 — Evaluation Domain Foundation

**Specification ID:** SPEC-007
**Title:** Evaluation Domain Foundation
**Version:** 0.1.0
**Status:** Draft
**Priority:** High
**Epic:** Learning Platform

---

# Purpose

Introduce the Evaluation domain concept into Fablit.

An Evaluation represents the structured interpretation of a learner's Submission against the expectations of the Assessment Activity to which that Submission responds.

Evaluation establishes the domain boundary between:

* learner-produced work
* interpretation of that work
* future learner-facing Feedback

This specification deliberately avoids reducing Evaluation to a numerical score.

It establishes the minimum domain model required for future human, rule-based, or AI-assisted evaluation without coupling the core domain to any particular evaluation mechanism.

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

SPEC-005 established the Assessment and Assessment Activity domain concepts.

SPEC-006 established Submission as the learner's response to an Assessment Activity.

SPEC-007 introduces the next stage of the learning cycle: Evaluation.

The conceptual flow becomes:

```text
Assessment
    │
    └── Assessment Activity
              │
              ▼
          Submission
              │
              ▼
          Evaluation
```

Evaluation describes how the submitted work is interpreted.

Evaluation is not the Submission itself.

Evaluation is not Feedback.

Evaluation is not necessarily a score.

---

# Architectural Intent

Evaluation shall be represented as a domain result rather than as an implementation of an evaluation mechanism.

The domain shall not assume that Evaluation is produced by:

* a human
* an automated rules engine
* an AI model
* a particular model provider
* a particular scoring algorithm

Those are mechanisms for producing an Evaluation and may be introduced through later specifications.

Conceptually:

```text
              ┌──────────────────────┐
              │      Submission      │
              └──────────┬───────────┘
                         │
                         │ evaluated
                         ▼
              ┌──────────────────────┐
              │      Evaluation      │
              │                      │
              │   1..* Findings      │
              └──────────┬───────────┘
                         │
                         │ informs
                         ▼
              ┌──────────────────────┐
              │       Feedback       │
              └──────────────────────┘
```

SPEC-007 implements only the Evaluation portion of this flow.

---

# Objectives

SPEC-007 shall:

* introduce the Evaluation domain concept
* associate an Evaluation with a Submission
* introduce structured Evaluation Findings
* require at least one Finding for a valid Evaluation
* preserve Evaluation immutability
* record when an Evaluation occurred
* distinguish Evaluation from Submission
* distinguish Evaluation from Feedback
* avoid making scoring mandatory
* remain independent of evaluation mechanisms
* provide automated tests for Evaluation behaviour
* remain independent of persistence infrastructure

---

# Scope

## In Scope

* Evaluation domain model
* Evaluation identity
* Submission association
* Evaluation Finding domain model
* one-or-more Finding invariant
* Finding structure
* Evaluation timestamp
* Evaluation validation
* Evaluation immutability
* domain-level errors
* automated tests

---

## Out of Scope

The following are explicitly excluded from SPEC-007:

* numerical scoring
* scoring algorithms
* grading
* Feedback
* Reflection
* Progress tracking
* Skill mastery
* evaluator implementations
* AI evaluation
* AI model integration
* human evaluator management
* evaluation criteria framework
* persistence
* database integration
* HTTP API
* authentication
* authorization
* analytics
* notifications
* examination-specific evaluation rules

---

# Domain Concepts

## Evaluation

An Evaluation is the structured interpretation of a Submission.

It records findings about the learner's submitted work.

An Evaluation shall reference the Submission being evaluated.

An Evaluation shall contain at least one structured Finding.

An Evaluation does not itself define how the evaluation was produced.

---

## Evaluation Finding

An Evaluation Finding represents one structured observation or judgement about the Submission.

A Finding should communicate something meaningful about the learner's work.

Examples include:

* a strength identified in the work
* an observed weakness
* evidence of a demonstrated capability
* an area requiring improvement
* an observation relevant to the Assessment Activity

A Finding is deliberately not defined as a score.

---

# Evaluation Structure

The conceptual structure is:

```text
Evaluation
├── id
├── submission_id
├── findings
│     ├── Finding
│     ├── Finding
│     └── ...
└── evaluated_at
```

The `findings` collection must contain at least one Finding.

---

# Finding Structure

SPEC-007 establishes the concept of a structured Finding without prematurely defining a complete evaluation-criteria framework.

A Finding shall contain sufficient structured information to represent a meaningful evaluation observation or judgement.

The initial implementation should prefer a small, extensible structure.

The implementation shall not require every possible future evaluation dimension.

Possible information represented by a Finding may include:

* observation
* judgement
* evidence
* area of strength
* area for improvement

These concepts may be refined by later specifications when concrete evaluation requirements emerge.

---

# Functional Requirements

## FR-001 — Evaluation Identity

Each Evaluation shall have a unique domain identity.

The identity shall remain stable for the lifetime of the Evaluation.

---

## FR-002 — Submission Association

Each Evaluation shall reference exactly one Submission.

The reference shall use the stable Submission identity established by SPEC-006.

An Evaluation shall not duplicate the complete Submission.

---

## FR-003 — Findings

Each Evaluation shall contain at least one structured Evaluation Finding.

An Evaluation with zero Findings shall be considered invalid.

---

## FR-004 — Finding Identity

Each Evaluation Finding shall have a stable identity within the Evaluation.

The Finding identity shall allow individual findings to be referenced without relying on collection position.

---

## FR-005 — Meaningful Finding

Each Finding shall contain sufficient information to represent a meaningful observation or judgement.

An empty Finding shall be rejected by the domain model.

---

## FR-006 — Evaluation Timestamp

Each Evaluation shall record when the evaluation occurred.

The timestamp shall be part of the domain state.

---

## FR-007 — Immutability

An Evaluation shall be immutable after creation.

Its:

* Submission association
* Findings
* identity
* evaluation timestamp

shall not be silently modified.

If a Submission requires another evaluation, a new Evaluation shall be created.

---

## FR-008 — Submission Preservation

Creating an Evaluation shall not modify the associated Submission.

The Submission remains the historical representation of the learner's submitted work.

---

## FR-009 — No Mandatory Score

An Evaluation shall not require a numerical score.

A score may be introduced by a future specification if a concrete learning requirement justifies it.

The absence of a score shall not make an Evaluation invalid.

---

## FR-010 — Evaluation Independence

An Evaluation shall not depend on the mechanism used to produce it.

The domain model shall not require knowledge of:

* AI providers
* model names
* prompts
* evaluator services
* human evaluator accounts
* scoring algorithms

---

## FR-011 — Finding Collection Integrity

An Evaluation shall maintain a valid collection of Findings.

The collection shall:

* contain at least one Finding
* contain only valid Finding objects
* preserve Finding identity
* preserve the integrity of each Finding

---

## FR-012 — Domain Validation

The Evaluation model shall reject invalid domain states.

Examples include:

* missing Evaluation identity
* missing Submission identity
* empty Findings collection
* invalid Finding
* missing evaluation timestamp

---

# Domain Rules

The following rules shall be enforced by the domain model.

### DR-001

An Evaluation must have a unique identity.

### DR-002

An Evaluation must reference exactly one Submission.

### DR-003

An Evaluation must contain at least one structured Finding.

### DR-004

A Finding must contain sufficient information to represent a meaningful observation or judgement.

### DR-005

An Evaluation must record when it occurred.

### DR-006

An Evaluation is immutable after creation.

### DR-007

Creating an Evaluation must not modify its Submission.

### DR-008

An Evaluation does not require a numerical score.

### DR-009

An Evaluation must not contain Feedback.

### DR-010

An Evaluation must not depend on a specific evaluation mechanism.

### DR-011

An Evaluation must not contain examination-specific concepts.

### DR-012

An Evaluation must not require persistence infrastructure.

---

# Evaluation and Scoring

Scoring is intentionally separate from the fundamental Evaluation model.

The following relationship is permitted in future specifications:

```text
Evaluation
    │
    ├── Findings
    │
    └── Optional Result
             │
             └── Score
```

However, SPEC-007 shall not introduce a mandatory numerical score.

This preserves Fablit's learning philosophy by ensuring that evaluation is not reduced to measurement alone.

A future scoring model shall be introduced only when a concrete product requirement establishes:

* what is being scored
* why it is being scored
* how scores are interpreted
* how scores contribute to learning

---

# Evaluation and Feedback

Evaluation and Feedback are separate domain concepts.

Evaluation answers:

> How does the learner's submitted work relate to the expectations of the Assessment Activity?

Feedback answers:

> What can the learner understand or do differently as a result?

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

SPEC-007 shall not implement Feedback.

Feedback shall be introduced through a future specification.

---

# Evaluation and Assessment Activity

The Assessment Activity defines the learner interaction and establishes the expectations against which the Submission is interpreted.

The relationship is:

```text
Assessment Activity
        │
        │ produces
        ▼
    Submission
        │
        │ evaluated
        ▼
    Evaluation
```

SPEC-007 shall not duplicate the Assessment Activity definition inside Evaluation.

Evaluation shall reference the Submission, and the Submission already references the Assessment Activity.

---

# Evaluation Mechanism Boundary

Evaluation may eventually be produced by multiple mechanisms.

Examples include:

```text
Human Evaluator
      │
      ▼
  Evaluation


Rule Engine
      │
      ▼
  Evaluation


AI Evaluator
      │
      ▼
  Evaluation
```

These mechanisms shall remain outside the core Evaluation domain model.

The domain object represents the resulting evaluation, not the machinery that produced it.

---

# AI Evaluation Boundary

AI-assisted evaluation is explicitly deferred.

SPEC-007 shall not introduce:

* model providers
* model identifiers
* prompts
* token usage
* AI confidence scores
* AI-specific response formats
* LLM clients
* AI service dependencies

Future AI evaluation functionality shall adapt its output into the domain Evaluation model rather than redefining Evaluation around a specific AI implementation.

---

# Evaluation History

SPEC-007 establishes Evaluation as an immutable record.

This permits future evaluation history such as:

```text
Submission #123
    │
    ├── Evaluation #1
    │
    ├── Evaluation #2
    │
    └── Evaluation #3
```

Multiple evaluations are not required by SPEC-007.

If reevaluation is introduced later, it shall create a new Evaluation rather than mutate an existing one.

---

# Persistence Boundary

No database or persistence technology is required by SPEC-007.

The Evaluation domain model shall be usable in memory.

Persistence shall be introduced through a future specification when the product requires durable evaluation records.

---

# API Boundary

An HTTP API is not required by SPEC-007.

The primary objective is to establish the domain model and its invariants.

If an API is introduced later, it shall expose domain behaviour rather than framework-specific implementation details.

---

# Testing Requirements

SPEC-007 shall include automated tests for externally observable Evaluation behaviour.

Tests shall cover at least:

* Evaluation creation
* Evaluation identity
* Submission association
* Finding creation
* Finding identity
* requirement for at least one Finding
* invalid empty Finding rejection
* evaluation timestamp
* Evaluation immutability
* preservation of the associated Submission
* absence of mandatory scoring
* invalid domain state rejection
* independence from evaluation mechanisms
* independence from persistence infrastructure

Tests should focus on domain behaviour rather than implementation details.

---

# Acceptance Criteria

SPEC-007 is complete when:

* [ ] An Evaluation domain model exists.
* [ ] An Evaluation has a stable identity.
* [ ] An Evaluation references exactly one Submission.
* [ ] An Evaluation contains at least one structured Finding.
* [ ] Evaluation Findings have stable identities.
* [ ] Invalid or empty Findings are rejected.
* [ ] An Evaluation records its evaluation timestamp.
* [ ] An Evaluation is immutable after creation.
* [ ] Creating an Evaluation does not modify its Submission.
* [ ] An Evaluation does not require a numerical score.
* [ ] Feedback is not implemented.
* [ ] AI evaluation is not implemented.
* [ ] No evaluation-provider dependency is introduced.
* [ ] No persistence infrastructure is introduced.
* [ ] No examination-specific evaluation concepts are introduced.
* [ ] Automated tests cover the Evaluation domain rules.
* [ ] Existing SPEC-005 and SPEC-006 tests continue to pass.
* [ ] Existing platform tests continue to pass.
* [ ] CI quality gates continue to pass.
* [ ] Documentation reflects the implemented Evaluation domain.

---

# Architectural Constraints

SPEC-007 shall comply with the project's Architecture Principles.

## Skills Before Examinations

Evaluation shall assess transferable learner capabilities rather than examination-specific performance.

The domain shall not introduce NIFT-, NID-, CEED-, or other examination-specific evaluation concepts.

---

## Practice Before Theory

Evaluation shall interpret evidence produced through learner activity.

---

## Feedback Before Scoring

Evaluation shall prioritize meaningful findings rather than treating numerical scoring as the primary domain output.

A score is optional and deferred.

---

## Reflection Completes Learning

Evaluation shall preserve the information required for future learner reflection.

Reflection itself remains outside the scope of SPEC-007.

---

## Platform Before Content

Evaluation belongs to the learning domain and shall not introduce educational evaluation logic into the shared platform layer.

---

## Content Before Code

Evaluation findings shall describe learner work without embedding educational content directly into executable platform logic.

---

## Modular by Default

Evaluation shall depend on Submission through a stable domain boundary.

Future evaluator implementations shall be replaceable without changing the fundamental Evaluation model.

---

## Simplicity Over Complexity

SPEC-007 shall implement only the minimum Evaluation model required for the current learning-domain workflow.

No database, message broker, external AI service, evaluator framework, or distributed architecture shall be introduced solely for this specification.

---

## Specification Before Implementation

Implementation shall begin only after SPEC-007 has been reviewed and converted into a GitHub issue.

---

## Testability is a Feature

Every significant Evaluation domain rule shall have automated test coverage.

---

## Documentation is Part of the Product

The Domain Language and relevant architecture documentation shall remain aligned with the implementation.

---

# Relationship to Previous Specifications

SPEC-007 builds upon:

* SPEC-001 — Bootstrap Platform
* SPEC-002 — Engineering Toolchain
* SPEC-003 — Configuration & Logging
* SPEC-004 — Shared Platform Services
* SPEC-005 — Assessment Activity Domain Foundation
* SPEC-006 — Submission Domain Foundation

SPEC-005 establishes Assessment and Assessment Activity.

SPEC-006 establishes Submission.

SPEC-007 consumes Submission and establishes Evaluation.

The dependency chain is:

```text
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
```

---

# Relationship to Future Specifications

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

* explicit evaluation criteria
* criterion-specific findings
* scoring
* qualitative grading
* human evaluator identity
* evaluator roles
* AI-assisted evaluation
* evaluation provenance
* evaluation confidence
* reevaluation workflows
* Feedback
* Reflection
* Progress tracking
* Skill mastery
* analytics
* persistent evaluation history

These capabilities shall be introduced through separate specifications rather than being included speculatively in SPEC-007.

---

# Definition of Done

SPEC-007 is considered complete when:

* the Evaluation domain model is implemented
* Evaluation Finding is implemented
* Evaluation-to-Submission association is implemented
* the minimum-one-Finding invariant is enforced
* invalid Findings are rejected
* Evaluation immutability is enforced
* Evaluation timestamps are represented
* Submission state remains unchanged by Evaluation
* scoring remains optional and outside the initial model
* Feedback remains outside the Evaluation model
* AI evaluation remains outside the core domain
* automated tests cover the domain rules
* existing platform, Assessment, Assessment Activity, and Submission behaviour remains intact
* all automated quality checks pass
* documentation is updated
* the implementation has been reviewed
* the corresponding GitHub issue and Pull Request are complete

---

# North Star Alignment

SPEC-007 contributes to the Fablit North Star:

> Build skills through deliberate practice, meaningful feedback, and continuous improvement.

It establishes Evaluation as a meaningful interpretation of learner work rather than reducing learning to a numerical score.

The resulting Evaluation provides the foundation from which future Feedback can help the learner understand strengths, identify areas for improvement, and continue the learning cycle.
