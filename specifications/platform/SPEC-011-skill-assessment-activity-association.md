# SPEC-011 — Skill–Assessment Activity Association

**Specification ID:** SPEC-011
**Title:** Skill–Assessment Activity Association
**Version:** 0.1.0
**Status:** Draft
**Priority:** High
**Epic:** Learning Platform

---

## 1. Purpose

Establish the relationship between `Skill` and `Assessment Activity`.

An Assessment Activity provides an opportunity for a learner to practice and demonstrate one or more Skills.

A Skill may be practiced and demonstrated through multiple Assessment Activities.

The relationship is therefore **many-to-many**.

SPEC-011 introduces only the minimum relationship required to express this association.

It shall not introduce a separate domain entity for the relationship unless future requirements establish that the relationship itself carries domain meaning.

---

## 2. Background

Fablit now has independent domain foundations for:

```text
Assessment Activity
Submission
Evaluation
Finding
Feedback
Reflection
Skill
```

The current learning flow is:

```text
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

SPEC-010 established `Skill` as a transferable capability that can be developed through deliberate practice.

The remaining architectural question is how Skills participate in Assessment Activities.

The agreed model is:

```text
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

An Assessment Activity does not own a Skill, and a Skill does not belong exclusively to an Assessment Activity.

---

## 3. Architectural Decision

The Skill–Assessment Activity relationship shall be modeled as a **simple many-to-many association**.

The relationship means:

> **An Assessment Activity provides an opportunity to practice and demonstrate one or more Skills.**

This deliberately does not mean that the activity:

* owns the Skill;
* defines the Skill;
* guarantees mastery of the Skill;
* automatically assesses the Skill;
* determines the learner's Progress in the Skill.

The relationship establishes the **intended learning context**.

The actual learner performance remains represented through:

```text
Assessment Activity
        ↓
Submission
        ↓
Evaluation
        ↓
Finding
```

---

## 4. Design Principle

The relationship shall remain simple unless the relationship itself acquires domain meaning.

Therefore, SPEC-011 shall **not** introduce a dedicated domain object such as:

```text
SkillAssociation
SkillActivity
SkillActivityRelationship
```

unless a concrete requirement requires attributes or behaviour belonging to the relationship itself.

A persistence layer may internally require a join table or equivalent structure.

That persistence concern does not justify introducing a new domain entity.

---

## 5. Objectives

SPEC-011 shall:

* connect Skills with Assessment Activities;
* allow an Assessment Activity to reference multiple Skills;
* allow a Skill to be referenced by multiple Assessment Activities;
* preserve Skill independence;
* preserve Assessment Activity independence;
* keep the relationship simple;
* avoid introducing relationship-specific domain state;
* preserve the separation between intended Skills and actual Evaluation findings;
* support future Skill Progress without implementing Progress;
* provide automated tests for the association behaviour;
* preserve existing domain boundaries.

---

# 6. Scope

## 6.1 In Scope

* Skill–Assessment Activity association;
* many-to-many relationship semantics;
* association validation;
* association creation/removal where required by the existing domain architecture;
* duplicate-association prevention;
* domain-level behaviour and invariants;
* automated tests;
* required domain exports;
* documentation updates required by the relationship.

---

## 6.2 Out of Scope

The following are explicitly excluded from SPEC-011:

* Skill hierarchy;
* Skill taxonomy;
* Skill scoring;
* Skill proficiency;
* Skill mastery;
* learner Progress;
* learner Skill history;
* evidence aggregation;
* Skill analytics;
* recommendations;
* curriculum-to-Skill mapping;
* examination-to-Skill mapping;
* AI-generated Skill relationships;
* AI-based Skill selection;
* evaluation criteria;
* Finding-to-Skill persistence;
* Skill-specific Feedback;
* Skill-specific Reflection;
* relationship weights;
* relationship priorities;
* relationship roles;
* relationship proficiency;
* relationship scoring;
* a dedicated `SkillAssociation` domain entity;
* database-specific implementation requirements;
* HTTP API requirements.

---

# 7. Relationship Semantics

## 7.1 Activity → Skills

An Assessment Activity may provide an opportunity to practice and demonstrate multiple Skills.

For example:

```text
Assessment Activity
"Analyse this fashion photograph"

Skills:
- Observation
- Visual Analysis
- Written Communication
```

The activity therefore establishes a learning context involving multiple capabilities.

---

## 7.2 Skill → Activities

A Skill may appear in multiple Assessment Activities.

For example:

```text
Visual Analysis
    ├── Activity A
    ├── Activity C
    ├── Activity F
    └── Activity H
```

This enables the same capability to be practiced repeatedly across different learning contexts.

---

## 7.3 Many-to-Many Relationship

The conceptual relationship is:

```text
             ┌───────────────┐
             │     Skill     │
             └───────┬───────┘
                     │
              many   │   many
                     │
             ┌───────▼───────┐
             │   Assessment  │
             │    Activity   │
             └───────────────┘
```

Neither side is the conceptual owner of the other.

---

# 8. Functional Requirements

## FR-001 — Skill Association

An Assessment Activity shall be capable of being associated with one or more Skills.

## FR-002 — Activity Association

A Skill shall be capable of being associated with multiple Assessment Activities.

## FR-003 — Independent Skill

A Skill shall remain valid independently of any Assessment Activity.

Creating a Skill shall not require an Activity to exist.

## FR-004 — Independent Activity

An Assessment Activity shall remain a valid domain concept independently of a Skill association unless an existing architectural rule explicitly requires otherwise.

SPEC-011 shall not make Skills a mandatory prerequisite for creating an Assessment Activity.

## FR-005 — Multiple Skills

An Assessment Activity shall not be restricted to a single Skill.

## FR-006 — Multiple Activities

A Skill shall not be restricted to a single Assessment Activity.

## FR-007 — Duplicate Prevention

The same Skill shall not be associated with the same Assessment Activity more than once.

For example:

```text
Activity A
    └── Visual Analysis
    └── Visual Analysis   ← invalid duplicate
```

The domain shall prevent duplicate associations.

## FR-008 — Association Integrity

An association shall reference valid existing domain objects.

An invalid or non-existent Skill or Assessment Activity shall not result in a valid association.

## FR-009 — No Relationship Attributes

The association shall not require additional domain attributes.

The initial relationship shall contain only the information necessary to establish:

```text
Skill ↔ Assessment Activity
```

## FR-010 — No Ownership Transfer

Associating a Skill with an Assessment Activity shall not transfer ownership or lifecycle responsibility for either object.

## FR-011 — No Evaluation Semantics

The association shall not imply that every Evaluation must evaluate every associated Skill.

An activity may provide an opportunity to practice multiple Skills while a particular Evaluation may produce findings relevant to only some aspects of the learner's work.

## FR-012 — No Progress Semantics

Creating an association shall not modify learner Progress.

No learner-specific state shall be created by the relationship.

## FR-013 — No Mastery Semantics

Creating an association shall not imply Skill mastery, proficiency, completion, or achievement.

---

# 9. Domain Rules

### DR-001

A Skill may be associated with zero or more Assessment Activities.

### DR-002

An Assessment Activity may be associated with zero or more Skills.

### DR-003

The relationship is many-to-many.

### DR-004

A Skill remains valid without an Assessment Activity.

### DR-005

An Assessment Activity remains independently meaningful without a Skill association.

### DR-006

A Skill may be associated with multiple Assessment Activities.

### DR-007

An Assessment Activity may be associated with multiple Skills.

### DR-008

The same Skill–Assessment Activity pair cannot occur more than once.

### DR-009

An association must reference valid Skill and Assessment Activity instances.

### DR-010

The relationship does not own either domain object.

### DR-011

The relationship does not contain scoring information.

### DR-012

The relationship does not contain Progress information.

### DR-013

The relationship does not contain mastery information.

### DR-014

The relationship does not contain evaluation criteria.

### DR-015

The relationship does not contain curriculum-specific information.

### DR-016

The relationship does not contain examination-specific information.

### DR-017

The relationship does not depend on AI.

### DR-018

A persistence join structure, if required, shall not automatically become a new domain entity.

---

# 10. Skill and Assessment Activity Ownership

Neither concept owns the other.

The distinction is:

```text
Skill
    = capability

Assessment Activity
    = learning opportunity
```

The association means:

```text
Assessment Activity
    provides an opportunity
    to practice and demonstrate
    Skill
```

It does not mean:

```text
Assessment Activity
    owns
    Skill
```

or:

```text
Skill
    owns
    Assessment Activity
```

This distinction shall remain explicit in the implementation.

---

# 11. Skill and Submission

The Skill relationship exists at the Assessment Activity level.

The conceptual flow is:

```text
Skill
   │
   ▼
Assessment Activity
   │
   ▼
Submission
```

A Submission is produced in response to an Assessment Activity.

The Submission does not need to duplicate the Activity's Skill associations.

The association remains part of the Activity's learning context.

---

# 12. Skill and Evaluation

The relationship between Skill and Evaluation is intentionally indirect:

```text
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
Finding
```

The Activity identifies the capabilities that the learner has an opportunity to practice.

The Evaluation identifies what was observed in the learner's Submission.

Therefore, SPEC-011 shall not introduce:

```text
Skill → Evaluation
```

as a required primary relationship.

---

# 13. Skill and Finding

Findings represent structured observations or judgements produced by an Evaluation.

A Finding is not automatically a Skill result.

For example:

```text
Skill:
Visual Analysis

Finding:
"The response identifies the dominant visual elements
but does not explain their relationship."
```

The finding may provide future evidence relevant to the Skill, but SPEC-011 shall not create an Evidence or SkillFinding domain model.

That decision remains deferred.

---

# 14. Skill and Feedback

Feedback remains associated with Evaluation rather than directly with Skill.

The conceptual flow is:

```text
Skill
   ↓
Assessment Activity
   ↓
Submission
   ↓
Evaluation
   ↓
Feedback
```

SPEC-011 shall not change the existing Feedback boundary established by SPEC-008.

---

# 15. Skill and Reflection

Reflection remains associated with the learner's response to Feedback.

The conceptual flow is:

```text
Skill
   ↓
Assessment Activity
   ↓
Submission
   ↓
Evaluation
   ↓
Feedback
   ↓
Reflection
```

SPEC-011 shall not change the existing Reflection boundary established by SPEC-009.

---

# 16. Future Progress

SPEC-011 provides a foundation for future Progress without implementing it.

A future Progress model may eventually reason about:

```text
Skill
   ↑
   │ evidence from multiple activities
   │
Activity A ── Evaluation
Activity B ── Evaluation
Activity C ── Evaluation
```

This allows Fablit to consider development of a Skill across repeated learning experiences.

However, SPEC-011 shall not:

* calculate Progress;
* store learner Progress;
* aggregate Findings;
* calculate Skill scores;
* determine mastery.

---

# 17. Future Evidence

SPEC-011 intentionally does not introduce an Evidence domain object.

The future relationship may eventually become:

```text
Skill
   ▲
   │
Evidence
   ▲
   │
Evaluation / Finding
```

The exact Evidence model shall be determined by a future specification.

The Skill–Activity association must not prematurely encode that future model.

---

# 18. Relationship Attributes

The initial relationship shall have no domain-specific attributes.

The following are explicitly excluded:

```text
weight
priority
role
score
proficiency
mastery_threshold
evidence_type
assessment_weight
```

If a future requirement establishes that one of these concepts has genuine domain meaning, a separate architectural decision shall be made before extending the relationship.

---

# 19. Relationship Lifecycle

The relationship shall not alter the lifecycle of either domain object.

For example:

```text
Create Skill
      │
      ├── no Activity required
      ▼
    Skill

Create Activity
      │
      ├── no Skill required
      ▼
  Activity

Associate
 Skill ↔ Activity
```

Removing an association shall not delete either the Skill or the Assessment Activity.

Deleting or archiving either object is outside the scope of SPEC-011.

---

# 20. Persistence Boundary

SPEC-011 defines a domain relationship.

The physical persistence mechanism is an implementation concern.

A relational implementation may use a join table such as:

```text
assessment_activity_skill
```

However, the exact persistence structure shall follow the repository's established persistence architecture.

The existence of a database join table shall not imply that a new domain entity is required.

---

# 21. API Boundary

SPEC-011 does not require a new HTTP API.

If the existing application architecture exposes Assessment Activities or Skills through an API, the association may eventually be represented at that boundary.

That API representation shall not introduce domain concepts that do not exist in the domain model.

---

# 22. Testing Requirements

Automated tests shall verify the externally observable behaviour of the relationship.

Tests shall cover at least:

* associating one Skill with one Assessment Activity;
* associating multiple Skills with one Assessment Activity;
* associating one Skill with multiple Assessment Activities;
* confirming many-to-many behaviour;
* preventing duplicate associations;
* preserving Skill validity without an Activity;
* preserving Activity validity without a Skill;
* rejecting invalid association references;
* confirming that association does not modify Skill identity;
* confirming that association does not modify Activity identity;
* confirming that association does not create Progress state;
* confirming that association does not create mastery state;
* confirming that association does not introduce scoring state;
* confirming existing Assessment Activity behaviour remains intact;
* confirming existing Skill behaviour remains intact.

Tests should focus on domain behaviour rather than persistence implementation details.

---

# 23. Acceptance Criteria

SPEC-011 is complete when:

* [ ] A Skill can be associated with an Assessment Activity.
* [ ] An Assessment Activity can be associated with multiple Skills.
* [ ] A Skill can be associated with multiple Assessment Activities.
* [ ] The relationship is many-to-many.
* [ ] A Skill can exist without an Assessment Activity.
* [ ] An Assessment Activity can exist without a Skill association.
* [ ] Duplicate Skill–Activity associations are prevented.
* [ ] Invalid association references are rejected.
* [ ] The relationship does not modify Skill identity.
* [ ] The relationship does not modify Assessment Activity identity.
* [ ] The relationship does not introduce scoring.
* [ ] The relationship does not introduce Progress.
* [ ] The relationship does not introduce mastery.
* [ ] The relationship does not introduce proficiency.
* [ ] The relationship does not introduce evaluation criteria.
* [ ] The relationship does not introduce curriculum-specific state.
* [ ] The relationship does not introduce examination-specific state.
* [ ] The relationship does not introduce AI dependency.
* [ ] No dedicated relationship domain entity is introduced.
* [ ] Persistence implementation, if required, follows existing architecture.
* [ ] Automated tests cover the relationship invariants.
* [ ] Existing domain tests continue to pass.
* [ ] Existing platform tests continue to pass.
* [ ] CI quality gates continue to pass.
* [ ] Domain Language is updated where required.
* [ ] Architecture documentation is updated where required.
* [ ] SPEC-011 remains aligned with the Project Charter and Architecture Principles.

---

# 24. Architectural Constraints

SPEC-011 shall comply with the existing Fablit Architecture Principles.

## AP-001 — Skills Before Examinations

The relationship shall connect Skills to learning activities rather than to examination-specific structures.

## AP-002 — Practice Before Theory

The relationship represents an opportunity for deliberate Skill practice.

## AP-003 — Feedback Before Scoring

The relationship does not introduce numerical scoring.

Evaluation and Feedback remain separate domain concerns.

## AP-004 — Reflection Completes Learning

The relationship does not replace or modify Reflection.

## AP-005 — Platform Before Content

The association remains independent of any specific examination, institution, or curriculum.

## AP-006 — Content Before Code

Skill relationships should represent learning concepts rather than examination-specific application logic.

## AP-007 — Modular by Default

Skill and Assessment Activity remain independently meaningful domain concepts.

The association connects them without making either concept dependent on the other.

## AP-008 — Simplicity Over Complexity

No relationship entity shall be introduced without domain justification.

No relationship attributes shall be introduced speculatively.

## AP-009 — AI as a Collaborator

The relationship shall remain independent of AI.

AI may eventually assist in creating or recommending associations, but AI shall not be a domain dependency.

## AP-010 — Specification Before Implementation

Implementation shall begin only after SPEC-011 has been reviewed and converted into a GitHub Issue.

## AP-011 — Testability is a Feature

Relationship invariants shall have automated test coverage.

## AP-012 — Documentation is Part of the Product

Domain Language and architecture documentation shall remain aligned with the implemented relationship.

---

# 25. Relationship to Previous Specifications

SPEC-011 builds upon:

* SPEC-005 — Assessment Activity Domain Foundation
* SPEC-006 — Submission Domain Foundation
* SPEC-007 — Evaluation Domain Foundation
* SPEC-008 — Feedback Domain Foundation
* SPEC-009 — Reflection Domain Foundation
* SPEC-010 — Skill Domain Foundation

The resulting conceptual model is:

```text
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

---

# 26. Relationship to Future Specifications

SPEC-011 intentionally creates a foundation rather than completing the long-term Skill model.

Future specifications may introduce:

* learner-specific Skill state;
* Evidence;
* Progress;
* mastery;
* proficiency;
* Skill analytics;
* adaptive practice;
* Skill recommendations;
* curriculum-to-Skill mappings;
* examination-to-Skill mappings;
* Skill hierarchies;
* richer Skill relationships.

Those concepts shall be introduced through separate specifications.

---

# 27. Future Architectural Trigger

A dedicated Skill–Activity relationship domain entity may be considered only if a future requirement establishes that the relationship itself has meaningful behaviour or state.

Examples of such a trigger would include a requirement to represent:

```text
primary Skill
supporting Skill
practice-only Skill
explicitly assessed Skill
Skill weight
Skill-specific evidence requirements
```

Until such a requirement exists, the relationship shall remain simple.

This is an intentional architectural constraint.

---

# 28. Definition of Done

SPEC-011 is considered complete when:

* the Skill–Assessment Activity relationship is implemented;
* the relationship supports many-to-many semantics;
* Skills remain independent of Activities;
* Activities remain independently meaningful;
* duplicate relationships are prevented;
* invalid references are rejected;
* no relationship-specific domain entity is introduced;
* no speculative relationship attributes are introduced;
* no Progress or mastery implementation is introduced;
* no Skill scoring is introduced;
* no curriculum or examination dependency is introduced;
* no AI dependency is introduced;
* automated tests cover all relationship invariants;
* existing domain tests remain passing;
* existing platform tests remain passing;
* CI quality gates remain passing;
* Domain Language documentation is updated;
* architecture documentation is updated where necessary;
* implementation remains aligned with the Project Charter;
* implementation remains aligned with the Architecture Principles;
* the corresponding GitHub Issue and Pull Request are complete.

---

# 29. North Star Alignment

SPEC-011 supports Fablit's North Star:

> **Build skills through deliberate practice, meaningful feedback, and continuous improvement.**

The Skill–Assessment Activity association creates the missing connection between:

```text
what the learner is developing
            │
            ▼
          Skill
            │
            ▼
where the learner practices it
            │
            ▼
 Assessment Activity
            │
            ▼
what the learner produces
            │
            ▼
        Submission
            │
            ▼
what was observed
            │
            ▼
       Evaluation
            │
            ▼
how the learner can improve
            │
            ▼
         Feedback
            │
            ▼
what the learner thinks about
            │
            ▼
        Reflection
```

This creates a foundation from which Fablit can eventually reason about Skill development over repeated learning experiences, without prematurely introducing Progress, mastery, scoring, or evidence aggregation.

The implementation should remain intentionally small.

The relationship is valuable because it connects the existing learning lifecycle to the Skill domain while preserving the independence and simplicity of both domain concepts.
