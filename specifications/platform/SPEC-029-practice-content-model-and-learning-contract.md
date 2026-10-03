# SPEC-029: Practice Content Model & Learning Contract

## 1. Overview & Goal

SPEC-029 establishes the content and learning contract that defines what makes an activity a Fablit practice.

The purpose is not to introduce a new learner-facing feature. It is to give Fablit a consistent, reviewable standard for designing, evaluating, connecting, and eventually generating practices.

Fablit should not become another large collection of study resources. Its product promise is deliberate practice: a learner receives a focused creative task, produces a response, receives useful feedback, reflects, and has a meaningful basis for practising again.

This specification therefore defines the minimum educational intent and content structure required for an activity to belong in the Fablit practice library.

The contract must remain independent of any particular evaluation mechanism, AI provider, UI implementation, persistence mechanism, or examination.

---

## 2. Product Principle

Fablit should optimise for **quality of practice rather than quantity of content**.

A Fablit practice should answer five questions:

1. What is the learner being asked to practise?
2. What kind of thinking should the learner perform?
3. What should a useful response contain or demonstrate?
4. What can meaningful feedback say about the attempt?
5. What could the learner practise next?

A practice that cannot answer these questions clearly should not be added to the curated library without explicit review.

The contract supports Fablit's existing learning cycle:

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

## 3. Scope

### In scope

- A content contract for Fablit practices.
- Required and optional practice metadata.
- Educational intent and expected learner thinking.
- Response expectations.
- Evaluation and feedback guidance.
- Reflection relationship.
- Short Drill and Full Practice suitability.
- Practice-to-practice continuity.
- Content review criteria.
- Preparation for future AI-assisted practice authoring.

### Out of scope

- A new learner-facing practice workflow.
- A recommendation engine.
- Personalised practice selection.
- Skill scoring, mastery, proficiency, or ranking.
- A new Progress model.
- AI-generated practices delivered directly to learners.
- AI evaluation of learner responses.
- Authentication or learner-account changes.
- New persistence requirements.
- Examination-specific domain models.

---

## 4. Practice Content Contract

Every curated Assessment Activity intended for the Fablit practice library must have the following content definition.

The contract is **authored content, per practice**: each curated practice's own definition carries a written contract describing that practice's purpose, thinking demand, and intents — not text derived generically from the activity's title, description, or prompt. A generic derivation may exist as a fallback for definitions that have not authored a contract, but it must never stand in for a curated practice's contract. Automated tests enforce this boundary so generic fallback text cannot silently become practice content.

### 4.1 Identity

A practice must have:

- Stable activity identity.
- Clear learner-facing title.
- Concise learner-facing description.
- Activity type compatible with the existing Assessment Activity model.

The title and description should describe the learner's work rather than use generic educational terminology.

### 4.2 Purpose

Each practice must state an internal **practice purpose**.

The purpose answers:

> What is this practice deliberately exercising?

The purpose must describe a concrete form of creative thinking or creative work, rather than merely naming a broad topic.

Examples:

- Notice visual details and infer evidence of use.
- Interpret how colour contributes to mood.
- Generate alternative possibilities from an ordinary object.
- Explain the thinking behind a design decision.

A topic alone is not a purpose.

Bad:

> Practice colour theory.

Better:

> Examine how specific colour relationships contribute to the mood of a visual composition.

### 4.3 Primary Creative Thinking Lens

The existing internal content-design lens remains:

- Observe
- Interpret
- Ideate
- Articulate
- Reflect

Exactly one lens is primary. Optional secondary lenses may be recorded.

This lens is an **internal content-design aid**, consistent with SPEC-023. It is not a learner-facing skill taxonomy, progress measure, score, or recommendation signal.

The lens should describe the dominant kind of creative thinking demanded by the practice.

It must not be forced onto future Aptitude or English practice areas.

### 4.4 Learner Task

The task must make the learner's required action clear.

A learner should be able to answer:

> What am I actually being asked to do?

The task should use concrete verbs such as:

- notice
- compare
- identify
- interpret
- infer
- transform
- generate
- imagine
- explain
- justify
- reflect

Avoid prompts whose intended work is ambiguous or whose response can be completed through generic statements.

### 4.5 Expected Thinking

Each practice must define internally what useful thinking looks like.

Expected thinking is not a model answer. It describes the reasoning behaviour the practice is intended to elicit.

For example:

> The learner moves from visible evidence to an interpretation, rather than making an unsupported assumption.

This information is used to support evaluation and feedback design.

### 4.6 Response Contract

Each practice must make clear:

- what form of response is expected;
- approximately how much work is appropriate;
- whether the response is primarily observational, interpretive, generative, explanatory, or reflective;
- any meaningful constraints.

The response contract should avoid unnecessary formatting requirements.

A short practice should not become a long exercise merely because the input field permits a long answer.

### 4.7 Evaluation Intent

Each practice must identify what a useful evaluation should look for.

Evaluation intent should describe observable qualities of the response, such as:

- specificity of observations;
- use of visual evidence;
- connection between evidence and interpretation;
- range or originality of possibilities;
- clarity of explanation;
- awareness of the learner's own process.

Evaluation intent is not a numerical rubric unless a future specification explicitly introduces one.

The existing Evaluation model remains unchanged.

### 4.8 Feedback Intent

Each practice must define what useful learner-facing feedback should help the learner understand.

Feedback should preferentially:

1. identify something concrete in the attempt;
2. explain why it matters;
3. identify one meaningful opportunity for improvement;
4. give the learner a practical direction for another attempt.

Feedback should not merely restate the prompt or praise effort without evidence.

The contract does not require every practice to expose separate learner-facing fields for strengths, weaknesses, and next steps. Those remain presentation choices within the existing Feedback model.

### 4.9 Reflection Intent

Where reflection is part of the practice journey, the content definition should state what the learner is being invited to notice about their own process.

Reflection should connect the completed attempt to future practice.

Examples:

- What did you notice only after starting?
- Which part of the interpretation was supported by evidence?
- What would you look for differently next time?

Reflection should remain learner-authored and should not become a second evaluation.

### 4.10 Continuation Intent

A practice should have an internal answer to:

> If the learner wants to continue, what kind of practice would naturally follow?

This does not require every activity to have a transition.

Where a transition exists, it should represent a meaningful learning relationship rather than simply another activity from the same category.

SPEC-025 remains the mechanism for authored transitions.

---

## 5. Practice Mode Contract

Short Drill and Full Practice remain application-level practice modes defined by SPEC-022.

Mode suitability must be determined by the **work demanded by the task**, not by the response input type.

### Short Drill

A Short Drill should normally:

- have a focused objective;
- require a bounded amount of cognitive work;
- be realistically approachable in approximately 5–10 minutes;
- produce a useful learner response without requiring extensive setup;
- provide enough material for meaningful feedback.

The 5–10 minute guidance is indicative, not a timer or completion requirement.

### Full Practice

A Full Practice may:

- require deeper analysis;
- combine multiple forms of creative thinking;
- require more developed explanation or ideation;
- involve a richer stimulus or greater response depth.

A Full Practice should still have a clear purpose and should not become longer merely to justify the label.

### Mode review test

If the Short Drill / Full Practice label were removed, the intended mode should still be reasonably inferable from the task itself.

---

## 6. Practice Quality Rules

A curated practice should satisfy all of the following.

### PQ-001 — Deliberate purpose

The practice exercises a specific form of creative thinking or creative work.

### PQ-002 — Clear learner action

The learner can understand what they are being asked to do without interpreting hidden requirements.

### PQ-003 — Observable response

The response provides sufficient evidence for meaningful evaluation or reflection.

### PQ-004 — Feedback opportunity

A reasonable evaluator can identify something concrete that the learner did and provide useful improvement guidance.

### PQ-005 — Appropriate effort

The expected effort is consistent with the declared Practice Mode.

### PQ-006 — No content padding

Length, instructions, or response requirements must not be added merely to make a practice appear substantial.

### PQ-007 — Reflection supports learning

Where reflection is present, it should help the learner connect the attempt to future practice.

### PQ-008 — Continuity is meaningful

Where a transition exists, the next practice should have a defensible learning relationship to the current one.

### PQ-009 — No hidden learner model

Practice content must not require learner-specific inference, scoring, mastery estimation, or behavioural profiling.

### PQ-010 — Reusable content

The practice definition should be useful independently of a particular learner, browser session, or evaluation implementation.

---

## 7. Creative Thinking Lens

The existing internal lens is retained as a content-authoring aid:

```
Observe
   ↓
Interpret
   ↓
Ideate
   ↓
Articulate
   ↓
Reflect
```

This sequence is illustrative, not a mandatory linear curriculum.

A practice may move between multiple forms of thinking. One is identified as primary only to make content review and library balance easier.

The lens must not be presented to learners as a five-level progression or used to imply mastery.

Future top-level practice areas such as Aptitude Practice and English Practice must define their own appropriate internal structures rather than inheriting these five labels.

---

## 8. Exam Relevance

Fablit may support learners preparing for design entrance examinations, but an exam name must not substitute for a practice purpose.

A practice may record internal exam relevance where useful, including the relevant examination or exam-style context.

Exam relevance should answer:

> Where might this kind of thinking or response be useful?

It should not turn the practice into a simulated examination unless the activity is explicitly designed for that purpose.

This preserves the distinction between deliberate creative practice and future exam-practice experiences.

---

## 9. Content Review Checklist

Before a new or revised practice is approved, reviewers should be able to answer **yes** to the following:

- Is the purpose specific?
- Is the learner action unambiguous?
- Is the dominant creative thinking lens clear?
- Is the expected thinking described?
- Is the response contract appropriate?
- Can the response provide meaningful evidence for evaluation?
- Can feedback identify a concrete learning opportunity?
- Is the reflection purposeful?
- Is the declared mode consistent with the work demanded?
- Is the practice useful without relying on learner-specific data?
- Does it avoid unnecessary gamification or progress semantics?
- If connected to another practice, is the relationship educationally meaningful?

If several answers are no, the activity should be revised before being treated as curated Fablit content.

---

## 10. Existing Library Audit

Implementation of this specification must begin with an audit of the existing practice library.

The current activities should not simply receive metadata to satisfy the contract. Their prompts, response expectations, mode classification, evaluation intent, feedback intent, and continuation relationships should be reviewed against the contract.

In particular, implementation should reconsider activities whose current Short Drill / Full Practice classification does not clearly follow from the task itself.

No activity should be removed solely because it does not fit the contract. Where useful, its content should be refined.

---

## 11. AI-Assisted Authoring Preparation

This specification establishes the contract required for future AI-assisted content generation.

A future authoring workflow may use:

```
Authoring brief
      ↓
AI-generated candidate
      ↓
Practice Content Contract validation
      ↓
Human content review
      ↓
Approved Fablit practice
      ↓
Curated library
```

AI-generated content must not enter the learner-facing library automatically.

SPEC-029 does not introduce an AI provider, generation endpoint, learner-facing AI feature, or automated approval mechanism.

---

## 12. Architecture Boundaries

Implementation must preserve:

- FastAPI application architecture.
- Existing Assessment Activity model.
- Existing Submission → Evaluation → Feedback → Reflection → Completion journey.
- SPEC-021 persistent Practice History.
- SPEC-022 explicit Practice Modes.
- SPEC-023 internal Practice Capability Lens.
- SPEC-024 anonymous Learner Identity.
- SPEC-025 authored Practice Transitions.
- SPEC-026 Pre-Practice Intention.
- SPEC-028 Local Practice Draft.

The content contract should be represented at the appropriate content/application boundary without introducing unnecessary domain entities.

Do not redesign the core learning-domain aggregates solely to implement this specification.

---

## 13. Non-Goals

SPEC-029 does not:

- create a new dashboard;
- expose creative-thinking lenses as learner progress;
- calculate mastery;
- introduce scores or grades;
- personalise practice selection;
- create recommendations;
- add a timer;
- create a new practice workflow;
- add authentication;
- generate AI practices for individual learners;
- automatically publish AI-generated content;
- create a large content-management system;
- expand into Aptitude or English practice implementation.

---

## 14. Acceptance Criteria

- [ ] A documented Practice Content Contract exists in the repository.
- [ ] The contract clearly distinguishes purpose, task, expected thinking, response, evaluation intent, feedback intent, reflection intent, and continuation intent.
- [ ] The existing Observe / Interpret / Ideate / Articulate / Reflect lens remains internal content metadata and is not exposed as learner progress.
- [ ] Short Drill / Full Practice suitability is defined by cognitive work demanded rather than input type.
- [ ] Existing practice content is audited against the contract.
- [ ] Existing activities receive content refinements where the audit identifies ambiguity or weak alignment.
- [ ] Existing practice transitions are reviewed for meaningful learning relationships.
- [ ] No new scoring, mastery, recommendation, personalization, authentication, or gamification mechanism is introduced.
- [ ] The existing learner journey remains unchanged.
- [ ] Automated tests continue to pass.
- [ ] Documentation identifies the contract as the foundation for future AI-assisted practice authoring.
- [ ] The implementation remains compatible with the existing FastAPI + HTMX architecture and current persistence model.

---

## 15. Definition of Done

SPEC-029 is complete when the repository contains an approved, implementation-aligned Practice Content Contract and the current practice library has been reviewed against it, with necessary content refinements implemented and tested.

The result should make it possible for a contributor to answer:

> "What makes an activity a Fablit practice?"

without relying on undocumented assumptions.

The specification is successful if it improves the quality and consistency of Fablit practices without making the product heavier, more gamified, or more complicated for learners.
