# SPEC-010 --- Skill Domain Foundation

**Specification ID:** SPEC-010\
**Title:** Skill Domain Foundation\
**Version:** 0.1.0\
**Status:** Draft\
**Priority:** High\
**Epic:** Learning Platform

------------------------------------------------------------------------

# Purpose

Introduce the Skill domain concept into Fablit.

A Skill represents a measurable, transferable learner capability that
can be developed through deliberate practice.

The purpose of this specification is to establish the smallest stable
domain foundation for Skills while avoiding premature introduction of
Skill hierarchies, Progress state, mastery, scoring, curriculum
taxonomies, or examination-specific structures.

------------------------------------------------------------------------

# Background

Fablit's Project Charter states that the platform exists to develop
practical, transferable skills through deliberate practice, meaningful
feedback, and continuous reflection.

The Architecture Principles place **Skills Before Examinations**: the
architecture should model skills and learning experiences rather than
examination-specific workflows.

The current learning-domain chain established through SPEC-005 through
SPEC-009 is:

``` text
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
```

The Domain Language already defines Skill as a measurable capability
that can be developed through deliberate practice and notes that Skills
evolve over time and are reflected through learner Progress.

SPEC-010 establishes the domain foundation for that concept.

------------------------------------------------------------------------

# Architectural Intent

Skill represents **the capability being developed**.

Evaluation represents **what was observed in a particular learner
submission**.

Feedback represents **learner-facing guidance derived from an
Evaluation**.

Reflection represents **the learner's response to that Feedback**.

Therefore:

``` text
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

The central boundary is:

> **Skill defines the capability; the learning activity and evaluation
> context determine how that capability is demonstrated.**

Evaluation criteria therefore do not belong inside the Skill model.

------------------------------------------------------------------------

# Objectives

SPEC-010 shall:

-   introduce the Skill domain concept
-   provide a stable Skill identity
-   represent a Skill name
-   represent a Skill description
-   require meaningful Skill identity and descriptive content
-   preserve Skill immutability after creation
-   keep Skills independent of a single Assessment Activity
-   allow a Skill to be reusable across learning contexts
-   keep Skills independent of examination-specific terminology
-   keep Skills independent of curriculum-specific terminology
-   keep Skills independent of Progress state
-   keep Skills independent of scoring and mastery state
-   keep Skills independent of AI or generation mechanisms
-   provide automated tests for Skill behaviour
-   preserve domain independence from persistence and infrastructure

------------------------------------------------------------------------

# Scope

## In Scope

-   Skill domain model
-   Skill identity
-   Skill name
-   Skill description
-   Skill validation
-   Skill immutability
-   domain-level validation
-   automated tests
-   domain exports
-   documentation required to describe the new domain concept

------------------------------------------------------------------------

## Out of Scope

The following are explicitly excluded from SPEC-010:

-   Progress tracking
-   Skill development history
-   Mastery
-   proficiency levels
-   numerical Skill scoring
-   Skill hierarchy
-   parent/child Skills
-   Skill taxonomy
-   curriculum management
-   examination-specific Skill models
-   Skill-to-Assessment Activity persistence relationships
-   Evaluation criteria owned by Skill
-   learner-specific Skill state
-   analytics
-   recommendations
-   AI-generated Skills
-   AI-assisted Skill evaluation
-   persistence
-   database integration
-   HTTP API
-   authentication
-   authorization
-   notifications

------------------------------------------------------------------------

# Domain Concept

## Skill

A Skill is a measurable capability that can be developed through
deliberate practice.

For Fablit, a Skill should also represent a transferable capability that
can have meaning across more than one learning activity or educational
context.

Examples may include:

-   Writing
-   Observation
-   Communication
-   Creativity
-   Critical Thinking
-   Interview Performance

These examples are illustrative only.

SPEC-010 shall not introduce a predefined Skill catalogue.

------------------------------------------------------------------------

# Skill Characteristics

## Transferable

A Skill should have meaning beyond one Assessment Activity.

The same Skill may eventually be relevant to multiple learning
experiences.

## Practiceable

A learner should be able to deliberately practice the capability
represented by the Skill.

## Observable

The capability should be capable of being demonstrated through learner
work or behaviour that can provide meaningful evidence.

## Evaluable

The capability should be capable of being evaluated independently in an
appropriate learning context.

Evaluation does not require a numerical score.

## Activity-Independent

A Skill shall not belong exclusively to one Assessment Activity.

## Curriculum-Independent

A Skill shall not be defined as belonging to a particular examination,
curriculum, or preparation program.

------------------------------------------------------------------------

# Skill Structure

The initial Skill structure is intentionally minimal:

``` text
Skill
├── id
├── name
└── description
```

No additional learner-specific state is required by SPEC-010.

------------------------------------------------------------------------

# Functional Requirements

## FR-001 --- Skill Identity

Each Skill shall have a unique stable identity.

The identity shall remain unchanged for the lifetime of the Skill.

## FR-002 --- Skill Name

Each Skill shall have a human-readable name identifying the capability.

The name shall not be empty or whitespace-only.

## FR-003 --- Skill Description

Each Skill shall contain a meaningful description explaining the
capability represented by the Skill.

The description shall not be empty or whitespace-only.

## FR-004 --- Skill Immutability

A Skill shall be immutable after creation.

Its identity, name, and description shall not be silently modified.

If Fablit later requires a revised Skill definition, that change shall
be handled through an explicitly designed domain mechanism.

## FR-005 --- Activity Independence

A Skill shall not require an Assessment Activity to exist.

## FR-006 --- Multiple Activity Compatibility

The domain model shall not restrict a Skill to one Assessment Activity.

The actual Skill-to-Activity association mechanism is outside the scope
of SPEC-010.

## FR-007 --- Multiple Skill Compatibility

The domain model shall not restrict an Assessment Activity to developing
only one Skill.

The actual association mechanism is outside the scope of SPEC-010.

## FR-008 --- Evaluation Independence

A Skill shall not contain evaluation criteria.

The same Skill may be evaluated differently in different learning
contexts.

## FR-009 --- No Mandatory Scoring

A Skill shall not contain a score, percentage, grade, proficiency
number, or confidence value.

## FR-010 --- No Progress State

A Skill shall not contain learner-specific Progress state.

For example, the following shall not be part of the Skill model:

``` text
Skill
├── progress
├── mastery
├── current_level
└── proficiency
```

Progress is a future domain concern.

## FR-011 --- No Skill Hierarchy

SPEC-010 shall not require parent/child Skill relationships.

The initial Skill model shall remain flat.

## FR-012 --- No Examination Ownership

A Skill shall not contain examination-specific ownership or
classification.

Examples of excluded concepts include:

-   `exam_id`
-   `exam_type`
-   `nift_skill`
-   `nid_skill`
-   `ceed_skill`

## FR-013 --- No Curriculum Ownership

A Skill shall not require a curriculum to exist.

Curricula may eventually reference Skills, but Skills shall not depend
on a particular curriculum.

## FR-014 --- No Generation Dependency

Skill shall not depend on:

-   AI providers
-   LLM models
-   prompts
-   generation services
-   external APIs
-   machine-learning infrastructure

The domain concept must remain valid without any generation mechanism.

------------------------------------------------------------------------

# Domain Rules

The following rules shall be enforced by the domain model.

### DR-001

A Skill must have a unique stable identity.

### DR-002

A Skill must have a meaningful name.

### DR-003

A Skill must have a meaningful description.

### DR-004

A Skill name must not be empty or whitespace-only.

### DR-005

A Skill description must not be empty or whitespace-only.

### DR-006

A Skill is immutable after creation.

### DR-007

A Skill does not require an Assessment Activity.

### DR-008

A Skill is not owned by a single Assessment Activity.

### DR-009

A Skill does not contain evaluation criteria.

### DR-010

A Skill does not require numerical scoring.

### DR-011

A Skill does not contain Progress state.

### DR-012

A Skill does not require a hierarchy.

### DR-013

A Skill is not examination-specific.

### DR-014

A Skill is not curriculum-specific.

### DR-015

A Skill does not depend on AI or external generation mechanisms.

### DR-016

A Skill remains independent of persistence infrastructure.

------------------------------------------------------------------------

# Skill and Assessment Activity

An Assessment Activity provides a context in which a learner can
practice one or more Skills.

Conceptually:

``` text
                 Skill
               /   |   \
              /    |    \
       Activity A  B   Activity C
```

A single activity may develop multiple Skills:

``` text
Assessment Activity
        │
        ├── Skill A
        ├── Skill B
        └── Skill C
```

SPEC-010 establishes compatibility with these relationships but does not
implement the persistence relationship.

------------------------------------------------------------------------

# Skill and Evaluation

The relationship is:

``` text
Skill
   │
   │ capability
   ▼
Assessment Activity
   │
   │ contextual evaluation
   ▼
Evaluation
   │
   ▼
Finding
```

A Skill defines what capability is being developed.

An Evaluation determines what was observed about a particular
Submission.

Therefore, evaluation criteria shall remain outside the Skill model.

This follows the agreed Option C boundary:

> **Skill defines the capability; Evaluation defines what evidence
> demonstrates that capability in a particular context.**

------------------------------------------------------------------------

# Skill and Finding

SPEC-007 established that every Evaluation contains one or more
structured Findings.

A Finding is not a Skill.

A Finding represents an observation or judgement about learner work.

Conceptually:

``` text
Skill
   │
   │ capability being developed
   ▼
Activity
   │
   ▼
Submission
   │
   ▼
Evaluation
   │
   ▼
Finding
```

SPEC-010 does not modify the Finding model or introduce Skill-specific
Finding fields.

------------------------------------------------------------------------

# Skill and Feedback

Feedback is learner-facing guidance derived from an Evaluation.

Skill does not own Feedback.

The conceptual relationship is:

``` text
Skill
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
```

The existing Feedback boundary established by SPEC-008 remains
unchanged.

------------------------------------------------------------------------

# Skill and Reflection

Reflection is the learner's response to Feedback.

Skill does not own Reflection.

The conceptual relationship is:

``` text
Skill
   │
   ▼
Practice
   ▼
Evaluation
   ▼
Feedback
   ▼
Reflection
```

The existing Reflection boundary established by SPEC-009 remains
unchanged.

------------------------------------------------------------------------

# Skill and Progress

The Project Charter identifies Progress Tracking as part of the intended
platform scope.

The Architecture Blueprint describes Progress as representing learner
development over time, including skill development history.

SPEC-010 does not implement Progress.

The future relationship may be:

``` text
Evidence across learning activities
             │
             ▼
           Skill
             │
             ▼
          Progress
```

A Skill can therefore exist before Progress is implemented.

Progress remains a future domain concern and shall not be embedded
inside Skill.

------------------------------------------------------------------------

# Skill and Mastery

Mastery is explicitly deferred.

SPEC-010 shall not introduce:

-   mastery levels
-   mastery scores
-   proficiency thresholds
-   completion percentages
-   automatic mastery calculations

A future specification may determine whether Fablit needs a distinct
mastery concept.

------------------------------------------------------------------------

# Skill Hierarchy

SPEC-010 deliberately uses a flat Skill model.

It shall not introduce:

``` text
parent_skill_id
child_skills
skill_tree
skill_taxonomy
```

For example:

``` text
Visual Analysis
├── Observation
├── Composition
└── Colour Relationships
```

may eventually become useful, but the current domain model shall not
assume that hierarchy exists.

This preserves simplicity and allows a future specification to introduce
relationships only when justified.

------------------------------------------------------------------------

# Skill Granularity

A capability should be represented as a Skill when it can reasonably
satisfy all of the following:

1.  it can be deliberately practiced;
2.  it can be demonstrated through learner work;
3.  it can be evaluated independently;
4.  it has meaning beyond a single task or exercise.

This is a domain modelling guideline rather than a requirement for a
universal Skill taxonomy.

------------------------------------------------------------------------

# Skill Reuse

A Skill should be reusable across learning contexts.

Conceptually:

``` text
                 Skill
              Visual Analysis
                /    |    \
               /     |     \
          Activity A B   Activity C
```

This reuse is important for future consideration of learner development
across multiple activities.

SPEC-010 does not calculate that development.

------------------------------------------------------------------------

# Examination and Curriculum Independence

The Architecture Principles state that Fablit should model skills and
learning experiences rather than examination-specific workflows.

Therefore:

``` text
Skill
  ↑
  ├── Curriculum A
  ├── Curriculum B
  └── Examination Context C
```

may eventually be supported.

The underlying Skill remains independent.

SPEC-010 shall not introduce examination or curriculum models.

------------------------------------------------------------------------

# Persistence Boundary

No persistence mechanism is required by SPEC-010.

The Skill domain model shall be usable in memory, consistent with the
existing in-memory learning-domain foundations established by SPEC-005
through SPEC-009.

Database storage, repositories, migrations, and persistence
relationships shall be introduced by future specifications when
justified.

------------------------------------------------------------------------

# API Boundary

No HTTP API is required by SPEC-010.

The purpose of this specification is to establish the domain concept and
its invariants.

If a future API exposes Skills, it should do so through existing
application/domain boundaries rather than embedding framework concerns
in the Skill model.

------------------------------------------------------------------------

# Testing Requirements

SPEC-010 shall include automated tests for externally observable Skill
behaviour.

Tests shall cover at least:

-   Skill creation
-   Skill identity
-   Skill name
-   Skill description
-   empty name rejection
-   whitespace-only name rejection
-   empty description rejection
-   whitespace-only description rejection
-   Skill immutability
-   creation without an Assessment Activity
-   absence of Progress state
-   absence of scoring state
-   absence of mastery state
-   absence of hierarchy requirements
-   absence of examination-specific state
-   absence of curriculum-specific state
-   independence from persistence infrastructure

Tests should focus on domain behaviour rather than implementation
details.

Existing tests for Assessment, Assessment Activity, Submission,
Evaluation, Feedback, and Reflection shall continue to pass.

------------------------------------------------------------------------

# Acceptance Criteria

SPEC-010 is complete when:

-   [ ] A Skill domain model exists.
-   [ ] Skill has a stable identity.
-   [ ] Skill has a meaningful name.
-   [ ] Skill has a meaningful description.
-   [ ] Empty names are rejected.
-   [ ] Whitespace-only names are rejected.
-   [ ] Empty descriptions are rejected.
-   [ ] Whitespace-only descriptions are rejected.
-   [ ] Skill is immutable after creation.
-   [ ] Skill does not require an Assessment Activity.
-   [ ] Skill is not restricted to a single Assessment Activity.
-   [ ] Skill does not contain Evaluation criteria.
-   [ ] Skill does not contain scoring state.
-   [ ] Skill does not contain Progress state.
-   [ ] Skill does not contain mastery state.
-   [ ] Skill does not require a hierarchy.
-   [ ] Skill is not examination-specific.
-   [ ] Skill is not curriculum-specific.
-   [ ] Skill does not depend on AI or external generation mechanisms.
-   [ ] No Progress implementation is introduced.
-   [ ] No mastery implementation is introduced.
-   [ ] No Skill hierarchy is introduced.
-   [ ] No persistence infrastructure is introduced.
-   [ ] Automated tests cover the Skill domain rules.
-   [ ] Existing learning-domain tests continue to pass.
-   [ ] Existing platform tests continue to pass.
-   [ ] CI quality gates continue to pass.
-   [ ] Domain Language documentation is updated where required.
-   [ ] Architecture documentation is updated where required.

------------------------------------------------------------------------

# Architectural Constraints

SPEC-010 shall comply with the project's Architecture Principles.

## AP-001 --- Skills Before Examinations

Skill is a first-class domain concept because Fablit models transferable
capabilities rather than examination-specific workflows.

No examination-specific Skill structure shall be introduced.

## AP-002 --- Practice Before Theory

Skills exist to support deliberate practice.

The Skill model shall remain connected conceptually to learner
activities rather than passive content consumption.

## AP-003 --- Feedback Before Scoring

Skill shall not require numerical scoring.

Feedback remains the mechanism through which learners receive guidance
for improvement.

## AP-004 --- Reflection Completes Learning

Skill does not replace Reflection.

Reflection remains the learner's response to Feedback.

## AP-005 --- Platform Before Content

Skill shall remain independent of any specific examination, institution,
or educational discipline.

## AP-006 --- Content Before Code

Skill definitions shall remain domain data rather than hardcoded
examination-specific application logic.

## AP-007 --- Modular by Default

Skill shall be independently modelled and shall not require coupling to
a particular Assessment Activity, curriculum, examination, or AI
provider.

## AP-008 --- Simplicity Over Complexity

SPEC-010 shall implement the minimum Skill model required by the current
architecture.

No hierarchy, taxonomy, mastery framework, scoring system, or Progress
model shall be introduced speculatively.

## AP-009 --- AI as a Collaborator

AI may eventually assist with Skill identification or evaluation, but
the Skill domain model shall remain independent of AI.

## AP-010 --- Specification Before Implementation

Implementation shall begin only after SPEC-010 has been reviewed and
converted into a GitHub Issue.

## AP-011 --- Testability is a Feature

Every significant Skill domain rule shall have automated test coverage.

## AP-012 --- Documentation is Part of the Product

The Domain Language and relevant architecture documentation shall remain
aligned with the implemented Skill concept.

------------------------------------------------------------------------

# Relationship to Previous Specifications

SPEC-010 builds upon:

-   SPEC-001 --- Bootstrap Platform
-   SPEC-002 --- Engineering Toolchain
-   SPEC-003 --- Configuration & Logging
-   SPEC-004 --- Shared Platform Services
-   SPEC-005 --- Assessment Activity Domain Foundation
-   SPEC-006 --- Submission Domain Foundation
-   SPEC-007 --- Evaluation Domain Foundation
-   SPEC-008 --- Feedback Domain Foundation
-   SPEC-009 --- Reflection Domain Foundation

The current learning-domain chain is:

``` text
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
```

SPEC-010 introduces Skill as the transferable capability that may be
developed across multiple learning interactions.

------------------------------------------------------------------------

# Relationship to Future Specifications

The conceptual direction is:

``` text
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
Evidence across activities
    ↓
Skill Development
    ↓
Progress
```

This is a conceptual relationship rather than a binding implementation
roadmap.

Future specifications may introduce additional domain concepts or alter
these relationships when architectural or product requirements justify
doing so.

------------------------------------------------------------------------

# Future Extension Points

Future specifications may introduce:

-   Skill-to-Assessment Activity relationships
-   Skill-to-Skill relationships
-   Skill hierarchies
-   Skill taxonomies
-   curriculum-to-Skill mappings
-   examination-to-Skill mappings
-   learner-to-Skill relationships
-   evidence associated with Skills
-   Progress
-   mastery
-   proficiency levels
-   Skill analytics
-   recommendations
-   adaptive practice
-   AI-assisted Skill identification
-   AI-assisted Skill evaluation

These capabilities shall be introduced through separate specifications.

------------------------------------------------------------------------

# Definition of Done

SPEC-010 is considered complete when:

-   the Skill domain model is implemented
-   stable Skill identity is implemented
-   Skill name is implemented
-   Skill description is implemented
-   meaningful-content validation is enforced
-   Skill immutability is enforced
-   Skill remains independent of Assessment Activity persistence
-   Skill remains independent of Evaluation criteria
-   Skill remains independent of Progress
-   Skill remains independent of mastery
-   Skill remains independent of scoring
-   Skill remains independent of curriculum and examination structures
-   Skill remains independent of AI and external generation mechanisms
-   automated tests cover the domain rules
-   existing platform and learning-domain behaviour remains intact
-   all automated quality checks pass
-   Domain Language documentation is updated
-   Architecture documentation is updated where required
-   the implementation has been reviewed
-   the corresponding GitHub Issue and Pull Request are complete

------------------------------------------------------------------------

# North Star Alignment

SPEC-010 directly supports Fablit's North Star:

> **Build skills through deliberate practice, meaningful feedback, and
> continuous improvement.**

Skill gives Fablit a stable representation of the capability being
developed.

The domain direction becomes:

``` text
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
Skill Development
   ↓
Future Progress
```

The implementation remains intentionally small so that future Progress,
mastery, curriculum, and adaptive-learning concepts can be introduced
without prematurely constraining the architecture.
