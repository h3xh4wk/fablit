# SPEC-009 — Reflection Domain Foundation

**Specification ID:** SPEC-009
**Title:** Reflection Domain Foundation
**Version:** 0.1.0
**Status:** Draft
**Priority:** High
**Epic:** Learning Platform

---

# Purpose

Introduce the Reflection domain concept into Fablit.

Reflection represents the learner's deliberate response to Feedback.

Its purpose is to help the learner:

- make sense of what they learned
- assess their own understanding or performance
- recognize what they want to carry forward
- identify what they may want to practice or improve next

Reflection establishes the learner-owned stage between Feedback and future improvement.

---

# Background

Fablit's learning cycle is:

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

SPEC-005 established Assessment and Assessment Activity.

SPEC-006 established Submission.

SPEC-007 established Evaluation.

SPEC-008 established Feedback.

SPEC-009 introduces Reflection as the learner's own response to Feedback.

The conceptual flow is:

Assessment
    │
    └── Assessment Activity
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

Reflection is intentionally distinct from both Evaluation and Feedback.

Evaluation represents the structured interpretation of learner work.

Feedback represents learner-facing guidance derived from that interpretation.

Reflection represents what the learner makes of that guidance.

---

# Architectural Intent

Reflection shall be represented as a learner-owned domain record.

It shall reference the Feedback that prompted it while remaining an independent domain concept.

The relationship is:

Feedback
    │
    │ prompts
    ▼
Reflection

Reflection shall not be embedded inside Feedback.

Reflection shall not duplicate the complete Feedback object.

The domain model shall reference Feedback by stable identity.

Conceptually:

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
Improvement

SPEC-009 implements only the Reflection portion of this flow.

---

# Objectives

SPEC-009 shall:

- introduce the Reflection domain concept
- associate Reflection with Feedback
- represent learner-authored reflective content
- require meaningful Reflection content
- record when Reflection was created
- preserve Reflection immutability
- distinguish Reflection from Feedback
- establish the boundary between Reflection and future Improvement
- remain independent of reflection-generation mechanisms
- avoid requiring numerical confidence scores
- avoid introducing Progress tracking
- provide automated tests for Reflection behaviour
- remain independent of persistence infrastructure

---

# Scope

## In Scope

- Reflection domain model
- Reflection identity
- Feedback association
- learner-authored content
- content validation
- Reflection creation timestamp
- Reflection immutability
- domain-level validation
- automated tests

---

## Out of Scope

The following are explicitly excluded from SPEC-009:

- Progress tracking
- Skill mastery
- Improvement tracking
- learning goals as a separate domain entity
- action-plan management
- confidence scoring
- numerical self-assessment
- AI-generated Reflection
- LLM integration
- reflection-generation services
- persistence
- database integration
- HTTP API
- authentication
- authorization
- analytics
- notifications
- examination-specific reflection rules

---

# Domain Concepts

## Reflection

Reflection is the learner's deliberate response to Feedback in which they make sense of what they learned, assess their own understanding or performance, and identify what they want to carry forward into future practice.

Reflection belongs to the learner's perspective.

It is not another Evaluation.

It is not a copy of Feedback.

It is not merely a text field attached to an Assessment.

---

## Learner-Owned Response

Reflection represents the learner's own response to the learning experience.

The Reflection domain model shall therefore represent learner-authored content.

An external system may eventually assist the learner by:

- presenting reflection prompts
- suggesting questions
- identifying areas worth considering
- helping organize thoughts

However, such mechanisms shall not redefine the Reflection domain concept.

Conceptually:

AI or system assistance
        │
        │ may prompt
        ▼
     Learner
        │
        │ responds
        ▼
   Reflection

---

# Reflection Structure

The conceptual structure is:

Reflection
├── id
├── feedback_id
├── content
└── created_at

The `feedback_id` establishes the relationship between the Reflection and the Feedback that prompted it.

The `content` field represents the learner's reflective response.

---

# Functional Requirements

## FR-001 — Reflection Identity

Each Reflection shall have a unique domain identity.

The identity shall remain stable for the lifetime of the Reflection.

---

## FR-002 — Feedback Association

Each Reflection shall reference exactly one Feedback.

The reference shall use the stable Feedback identity established by SPEC-008.

Reflection shall not duplicate the complete Feedback object.

---

## FR-003 — Learner-Owned Content

Each Reflection shall contain learner-authored content.

The domain model shall represent the Reflection as the learner's response rather than as system-generated evaluation.

---

## FR-004 — Meaningful Content

Each Reflection shall contain at least one meaningful piece of reflective content.

Reflection with empty or whitespace-only content shall be considered invalid.

---

## FR-005 — Content Representation

The initial Reflection model shall use a simple content representation.

The model shall not prematurely require separate fields for:

- self-assessment
- confidence
- learning goals
- improvement goals
- action plans
- next steps
- learning notes

These concepts may be introduced through future specifications if concrete requirements justify making them first-class domain concepts.

---

## FR-006 — Creation Timestamp

Each Reflection shall record when it was created.

The timestamp shall be part of the domain state.

---

## FR-007 — Immutability

Reflection shall be immutable after creation.

Its:

- identity
- Feedback association
- content
- creation timestamp

shall not be silently modified.

If the learner reflects again later, a new Reflection instance shall be created rather than mutating the existing Reflection.

---

## FR-008 — Feedback Preservation

Creating Reflection shall not modify the associated Feedback.

Feedback remains the learner-facing guidance produced from the Evaluation.

Reflection represents the learner's response to that guidance.

---

## FR-009 — No Mandatory Confidence Score

Reflection shall not require a numerical confidence rating.

A confidence rating may be introduced later if a concrete learning requirement justifies it.

The absence of a confidence score shall not make a Reflection invalid.

---

## FR-010 — No Mandatory Improvement Goal

Reflection shall not require a formal improvement goal or action plan.

A learner may express an intended next step as part of their reflective content, but a separate goal structure shall not be required by SPEC-009.

---

## FR-011 — Generation Mechanism Independence

Reflection shall not depend on a mechanism used to prompt or assist the learner.

The domain model shall not require knowledge of:

- AI providers
- model names
- prompts
- reflection-generation services
- human facilitator accounts
- generation algorithms

---

## FR-012 — Domain Validation

The Reflection model shall reject invalid domain states.

Examples include:

- missing Reflection identity
- missing Feedback identity
- empty content
- whitespace-only content
- missing creation timestamp

---

# Domain Rules

The following rules shall be enforced by the domain model.

### DR-001

Reflection must have a unique identity.

### DR-002

Reflection must reference exactly one Feedback.

### DR-003

Reflection must contain learner-authored content.

### DR-004

Reflection content must not be empty or whitespace-only.

### DR-005

Reflection must record when it was created.

### DR-006

Reflection is immutable after creation.

### DR-007

Creating Reflection must not modify its Feedback.

### DR-008

Reflection does not require a numerical confidence score.

### DR-009

Reflection does not require a separate improvement goal or action plan.

### DR-010

Reflection must not depend on a specific prompting or generation mechanism.

### DR-011

Reflection must not require persistence infrastructure.

### DR-012

Reflection must not contain examination-specific concepts.

---

# Evaluation, Feedback, and Reflection

Evaluation, Feedback, and Reflection represent different perspectives in the learning cycle.

Evaluation answers:

> What did we observe about the learner's submitted work?

Feedback answers:

> What can the learner understand or do differently as a result?

Reflection answers:

> What did the learner understand, and what will they take forward?

The relationship is:

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

Each stage has a distinct responsibility.

---

# Reflection and Feedback

Reflection is prompted by Feedback but remains independent of it.

The relationship is:

Feedback
    │
    │ prompts
    ▼
Reflection

A Reflection references the Feedback by stable identity.

It does not embed or duplicate the Feedback.

This provides traceability without coupling the two domain objects.

---

# Reflection and Improvement

Reflection should support future learner improvement.

The conceptual relationship is:

Feedback
    │
    ▼
Reflection
    │
    ▼
Improvement

SPEC-009 does not implement Improvement.

Improvement may eventually include:

- subsequent practice
- revised submissions
- changed learning strategies
- skill development
- recommendations

Those concerns belong to future specifications.

---

# Reflection and Progress

Reflection may eventually provide useful evidence for Progress.

However, Reflection shall not calculate or modify Progress.

The relationship may eventually become:

Reflection
    │
    ▼
Progress

but Progress remains outside the scope of SPEC-009.

---

# Reflection Generation Boundary

Reflection itself is learner-authored.

The platform may eventually provide mechanisms that help the learner reflect.

Examples include:

- reflection prompts
- guided questions
- suggested topics
- AI-assisted questioning
- facilitator prompts

These mechanisms shall remain outside the core Reflection domain model.

Conceptually:

System assistance
       │
       ▼
    Learner
       │
       ▼
   Reflection

The system does not own the learner's reflective response.

---

# AI Reflection Boundary

AI-assisted reflection is explicitly deferred.

SPEC-009 shall not introduce:

- LLM clients
- model providers
- model identifiers
- prompts
- token usage
- AI confidence scores
- model-specific response structures
- external AI service dependencies

Future AI functionality may assist the learner in producing Reflection without redefining Reflection around a particular AI implementation.

---

# Reflection History

SPEC-009 establishes Reflection as an immutable domain record.

This permits future reflection history such as:

Feedback #21
    │
    ├── Reflection #31
    │
    └── Reflection #38

Multiple Reflections are not required by SPEC-009.

If a learner reflects again later, a new Reflection instance shall be created rather than silently modifying a previous Reflection.

This preserves the learner's evolving understanding over time.

---

# Persistence Boundary

No database or persistence technology is required by SPEC-009.

The Reflection domain model shall be usable in memory.

Persistence shall be introduced through a future specification when durable Reflection records become a product requirement.

---

# API Boundary

An HTTP API is not required by SPEC-009.

The primary objective is to establish the domain model and its invariants.

If an API is introduced later, it shall expose domain behaviour rather than framework-specific implementation details.

---

# Testing Requirements

SPEC-009 shall include automated tests for externally observable Reflection behaviour.

Tests shall cover at least:

- Reflection creation
- Reflection identity
- Feedback association
- learner-authored content
- meaningful content validation
- empty content rejection
- whitespace-only content rejection
- creation timestamp
- Reflection immutability
- preservation of the associated Feedback
- absence of mandatory confidence scoring
- absence of mandatory improvement goals
- independence from prompting or generation mechanisms
- invalid domain state rejection
- independence from persistence infrastructure

Tests should focus on domain behaviour rather than implementation details.

---

# Acceptance Criteria

SPEC-009 is complete when:

- [ ] A Reflection domain model exists.
- [ ] Reflection has a stable identity.
- [ ] Reflection references exactly one Feedback.
- [ ] Reflection contains learner-authored content.
- [ ] Empty content is rejected.
- [ ] Whitespace-only content is rejected.
- [ ] Reflection records its creation timestamp.
- [ ] Reflection is immutable after creation.
- [ ] Creating Reflection does not modify its Feedback.
- [ ] Reflection does not require a numerical confidence score.
- [ ] Reflection does not require a separate improvement goal or action plan.
- [ ] Progress tracking is not implemented.
- [ ] Improvement tracking is not implemented.
- [ ] AI-generated Reflection is not implemented.
- [ ] No reflection-generation dependency is introduced.
- [ ] No persistence infrastructure is introduced.
- [ ] No examination-specific Reflection concepts are introduced.
- [ ] Automated tests cover the Reflection domain rules.
- [ ] Existing Assessment, Assessment Activity, Submission, Evaluation, and Feedback tests continue to pass.
- [ ] Existing platform tests continue to pass.
- [ ] CI quality gates continue to pass.
- [ ] Documentation reflects the implemented Reflection domain.

---

# Architectural Constraints

SPEC-009 shall comply with the project's Architecture Principles.

## Skills Before Examinations

Reflection shall support transferable learning rather than examination-specific preparation.

The domain shall not introduce NIFT-, NID-, CEED-, or other examination-specific Reflection concepts.

---

## Practice Before Theory

Reflection shall connect learner experience and Feedback to future practice.

---

## Feedback Before Scoring

Reflection shall remain useful without requiring numerical measurement.

A confidence rating may eventually be introduced, but it shall not define Reflection.

---

## Reflection Completes Learning

Reflection is the learner's deliberate response to Feedback and provides the bridge toward continued improvement.

The Reflection domain shall remain learner-owned.

---

## Platform Before Content

Reflection belongs to the learning domain and shall not introduce learner-specific educational logic into the shared platform layer.

---

## Content Before Code

Reflection content shall represent learner thinking without embedding educational content directly into executable platform logic.

---

## Modular by Default

Reflection shall depend on Feedback through a stable domain boundary.

Future prompting and reflection-assistance mechanisms shall be replaceable without changing the fundamental Reflection model.

---

## Simplicity Over Complexity

SPEC-009 shall implement only the minimum Reflection model required by the current learning-domain workflow.

No database, message broker, external AI service, reflection framework, or distributed architecture shall be introduced solely for this specification.

---

## Specification Before Implementation

Implementation shall begin only after SPEC-009 has been reviewed and converted into a GitHub issue.

---

## Testability is a Feature

Every significant Reflection domain rule shall have automated test coverage.

---

## Documentation is Part of the Product

The Domain Language and relevant architecture documentation shall remain aligned with the implementation.

---

# Relationship to Previous Specifications

SPEC-009 builds upon:

- SPEC-001 — Bootstrap Platform
- SPEC-002 — Engineering Toolchain
- SPEC-003 — Configuration & Logging
- SPEC-004 — Shared Platform Services
- SPEC-005 — Assessment Activity Domain Foundation
- SPEC-006 — Submission Domain Foundation
- SPEC-007 — Evaluation Domain Foundation
- SPEC-008 — Feedback Domain Foundation

The domain dependency chain is:

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

SPEC-009 consumes Feedback and establishes learner-owned Reflection.

---

# Relationship to Future Specifications

The expected conceptual progression is:

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
Improvement / Progress

This sequence is indicative rather than binding.

Future specifications may adjust the sequence when architectural or product requirements justify doing so.

---

# Future Extension Points

Future specifications may introduce:

- structured reflection categories
- self-assessment
- confidence ratings
- reflection prompts
- improvement goals
- action plans
- learner intentions
- guided reflection
- AI-assisted reflection
- reflection history
- persistent reflection storage
- Progress
- Skill mastery
- recommendations
- subsequent practice linkage
- learning analytics

These capabilities shall be introduced through separate specifications rather than being included speculatively in SPEC-009.

---

# Definition of Done

SPEC-009 is considered complete when:

- the Reflection domain model is implemented
- Reflection-to-Feedback association is implemented
- learner-authored content is implemented
- meaningful content validation is enforced
- Reflection immutability is enforced
- creation timestamps are represented
- Feedback state remains unchanged by Reflection
- confidence scoring remains optional and outside the Reflection model
- improvement goals remain optional and outside the Reflection model
- Progress remains outside the Reflection model
- AI-assisted reflection remains outside the core domain
- automated tests cover the domain rules
- existing platform and learning-domain behaviour remains intact
- all automated quality checks pass
- documentation is updated
- the implementation has been reviewed
- the corresponding GitHub issue and Pull Request are complete

---

# North Star Alignment

SPEC-009 contributes to the Fablit North Star:

> Build skills through deliberate practice, meaningful feedback, and continuous improvement.

Reflection provides the learner-owned bridge between Feedback and future improvement.

It allows the learner to make sense of what they experienced, identify what they learned, and carry that understanding into subsequent practice.

The resulting learning cycle is:

Practice
   ↓
Assessment
   ↓
Submission
   ↓
Evaluation
   ↓
Feedback
   ↓
Reflection
   ↓
Improvement
   ↓
Practice

Reflection therefore represents an essential part of Fablit's learning philosophy rather than simply another record attached to an Assessment.
