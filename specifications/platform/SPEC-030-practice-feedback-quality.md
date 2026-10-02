# SPEC-030: Practice Feedback Quality

## 1. Overview & Goal

SPEC-030 establishes a quality contract for learner-facing feedback in Fablit.

Fablit's product value is not only that a learner can submit a practice. The learner should be able to understand something useful about the attempt and have a clearer idea of what to try next.

SPEC-029 defines what makes a practice well-designed. SPEC-030 defines what makes the resulting feedback useful.

The goal is to improve the quality, consistency, and educational usefulness of feedback without introducing scoring, grading, mastery, personalization, or an AI tutor.

---

## 2. Product Principle

Fablit should not merely tell a learner whether an attempt is acceptable.

It should help the learner understand:

1. What they did in the attempt.
2. What was effective or meaningful.
3. Where the thinking could become stronger.
4. What they could try differently next time.

A useful feedback response should connect the learner's actual response to the practice purpose.

The core relationship is:

```
Practice Purpose
      ↓
Learner Attempt
      ↓
Evaluation
      ↓
Evidence-based Feedback
      ↓
Reflection
      ↓
Another Attempt
```

Feedback is therefore part of the practice loop, not a decorative message after submission.

---

## 3. Scope

### In scope

- Feedback quality principles.
- Relationship between Evaluation and Feedback.
- Evidence-based strengths.
- Improvement guidance.
- Actionable next steps.
- Feedback length and focus.
- Reflection handoff.
- Feedback content review.
- Existing deterministic evaluation/feedback content.
- Preparation for future richer evaluation systems.

### Out of scope

- Numerical scores or grades.
- Mastery or proficiency measurement.
- Learner ranking.
- Personalised recommendation systems.
- AI tutor/chat functionality.
- Automatic AI evaluation.
- New learner identity or authentication.
- New persistence architecture.
- New practice workflow.
- A general-purpose Learning Resource recommendation engine.

---

## 4. Feedback Contract

Every curated practice that produces learner-facing feedback should have an internal **Feedback Contract**.

The contract should make the intended feedback behaviour explicit.

### 4.1 Evidence

Feedback should refer to something observable in the learner's actual attempt whenever the evaluation mechanism provides sufficient evidence.

Evidence may include:

- a specific observation;
- a stated interpretation;
- a design choice;
- a generated idea;
- an explanation;
- a reflection statement.

Generic praise without reference to the attempt is not sufficient as the primary feedback.

### 4.2 Meaning

Feedback should explain why the identified evidence matters in relation to the practice purpose.

For example:

> You identified the worn edge and connected it to repeated handling.

is more useful when followed by an explanation of what that demonstrates about observation and inference.

The explanation should remain proportionate to the practice.

### 4.3 Improvement

Feedback should identify a concrete opportunity for improvement where one is available.

Improvement guidance should describe the thinking or action that could become stronger.

Avoid vague statements such as:

- "Be more creative."
- "Add more detail."
- "Think deeper."
- "Improve your answer."

Prefer guidance that tells the learner what to notice, compare, connect, test, or explain differently.

### 4.4 Next Step

Where appropriate, feedback should give the learner a practical next step.

A next step should be small enough to act on and connected to the practice.

Examples:

- Look again for two details that show how the object is used.
- Separate what you can see from what you infer.
- Develop one of the generated alternatives further instead of adding more ideas.
- Explain why the chosen visual element supports the intended mood.

The next step is guidance, not a required assignment.

### 4.5 Calibration

Feedback should be proportionate to the evidence available.

The evaluator must not claim to know more than the learner's response demonstrates.

Avoid:

- assumptions about the learner's ability;
- claims about motivation or effort that are not observable;
- unsupported claims about future performance;
- broad judgments about the learner.

Feedback should describe the attempt, not label the learner.

---

## 5. Feedback Structure

The existing Feedback model may contain strengths, improvement suggestions, rubric observations, recommended exercises, and learning resources.

SPEC-030 does not require a new domain model.

For Fablit's current practice experience, the preferred conceptual structure is:

```
What you did
      ↓
Why it matters
      ↓
What could be stronger
      ↓
What to try next
```

The UI may present this through the existing strengths, improvements, and next-step view.

The conceptual structure is a content-quality guide, not a requirement to expose four separate UI sections.

---

## 6. Feedback and Evaluation Relationship

Evaluation interprets the Submission.

Feedback communicates useful consequences of that evaluation to the learner.

Therefore:

- Evaluation should provide enough evidence for Feedback to be grounded.
- Feedback should not invent findings absent from Evaluation.
- Feedback should translate evaluation findings into learner-understandable guidance.
- Feedback should remain faithful to the practice purpose.
- Feedback should not become a second, hidden scoring system.

Existing deterministic demo evaluation may continue to be used.

SPEC-030 does not require replacing the current evaluator.

---

## 7. Practice-Specific Feedback

Feedback should be specific to the work demanded by the practice.

For example:

### Observation practice

Useful feedback can distinguish:

- visible detail;
- specificity;
- inference from evidence;
- unsupported assumptions.

### Interpretation practice

Useful feedback can distinguish:

- interpretation;
- supporting visual evidence;
- alternative readings;
- connection between evidence and conclusion.

### Ideation practice

Useful feedback can distinguish:

- number or range of possibilities where relevant;
- transformation of the starting idea;
- specificity of the chosen concept;
- development beyond a generic alternative.

### Articulation practice

Useful feedback can distinguish:

- clarity of explanation;
- connection between choice and intended effect;
- use of concrete design language;
- completeness appropriate to the task.

### Reflection practice

Useful feedback can help the learner identify:

- what changed in their awareness;
- what they would approach differently;
- whether the reflection connects to the actual attempt.

These are examples of feedback intent, not universal scoring criteria.

---

## 8. Feedback Length

Feedback should be concise enough to remain usable after a practice session.

More feedback is not necessarily better feedback.

A practice should normally receive:

- at least one concrete observation about the attempt when evidence permits;
- one meaningful improvement opportunity when one exists;
- a practical next direction when appropriate.

The system should avoid long generic explanations that obscure the useful point.

Feedback length should be driven by the complexity of the practice and the evidence available, not by a fixed word-count target.

---

## 9. Feedback Quality Rules

### FQ-001 — Evidence before judgment

Feedback should identify observable evidence before making an evaluative statement.

### FQ-002 — Practice alignment

Feedback must relate to the stated purpose and task of the practice.

### FQ-003 — Specific improvement

Improvement guidance should identify what the learner can change, notice, test, or explain.

### FQ-004 — Actionable next step

Where a next step is given, it should be concrete and realistically actionable.

### FQ-005 — No learner labelling

Feedback describes the attempt and its evidence rather than labelling the learner as talented, weak, creative, poor, advanced, or similar.

### FQ-006 — No unsupported inference

Feedback must not infer motivation, effort, intelligence, personality, or future performance from a response.

### FQ-007 — Proportionate detail

Feedback should be appropriate to the complexity and evidence of the practice.

### FQ-008 — No empty praise

Positive feedback should identify what was effective rather than relying on generic encouragement.

### FQ-009 — No hidden scoring

Feedback must not introduce implicit grades, ranks, percentages, mastery levels, or performance bands.

### FQ-010 — Reflection handoff

Feedback should leave the learner with something meaningful to consider during Reflection.

### FQ-011 — Practice-again usefulness

Feedback should make a subsequent attempt more informed without requiring a recommendation engine.

---

## 10. Reflection Handoff

Feedback and Reflection should form a deliberate handoff.

Feedback answers:

> What can I learn from this attempt?

Reflection then asks:

> What will I carry into my next attempt?

A reflection prompt should not simply ask the learner to repeat the feedback.

Where useful, it should invite the learner to examine:

- what they noticed;
- what surprised them;
- what they would change;
- what they want to pay attention to next time.

Reflection remains learner-authored and is not itself a second evaluation.

---

## 11. Practice Again

The existing Fablit journey supports practising again.

Feedback should support this without turning into personalised recommendation logic.

A learner may:

- repeat the same practice;
- follow an authored Practice Transition;
- choose another practice independently.

Feedback should not claim that one particular next activity is objectively required unless future product specifications explicitly define such behaviour.

SPEC-025 remains the mechanism for authored practice-to-practice continuity.

---

## 12. Current Feedback Audit

Implementation must audit the current practice feedback against this contract.

The audit should examine:

- whether feedback refers to the actual practice;
- whether strengths are concrete;
- whether improvement guidance is specific;
- whether next steps are actionable;
- whether feedback is proportionate;
- whether feedback supports reflection;
- whether any feedback wording accidentally introduces grading or learner labelling.

The audit should improve content quality rather than simply add more feedback fields.

---

## 13. Feedback Content Authoring

Feedback content should be authored alongside practice content.

SPEC-029 defines the Practice Content Contract.

For each practice, the content author should be able to define:

- evaluation intent;
- evidence to look for;
- likely useful observations;
- improvement opportunities;
- possible next-step guidance;
- reflection handoff.

This does not require storing every possible feedback sentence as static text.

The implementation should choose the smallest representation that supports current needs and future evolution.

---

## 14. Future AI Evaluation Boundary

SPEC-030 prepares Fablit for richer evaluation mechanisms but does not introduce them.

A future evaluator, including an AI-assisted evaluator, should still operate within the same conceptual boundary:

```
Submission
   ↓
Evaluation
   ↓
Feedback
```

The evaluation mechanism may change.

The learner-facing feedback contract should not.

Any future AI evaluator must not automatically create scores, mastery estimates, learner profiles, or recommendations merely because the technology makes them possible.

AI-generated feedback should remain grounded in the practice purpose and available evidence and should be subject to appropriate validation before being treated as trustworthy product behaviour.

---

## 15. Content Review Checklist

Before feedback for a practice is approved, reviewers should be able to answer yes to the following:

- Does the feedback refer to the work the practice actually asks for?
- Is there concrete evidence behind positive observations?
- Is any improvement guidance specific?
- Is the learner told what could be tried differently?
- Is the feedback proportionate to the practice?
- Does it avoid labelling the learner?
- Does it avoid unsupported claims?
- Does it avoid scores and mastery semantics?
- Does it leave a useful question or direction for Reflection?
- Would the feedback help a learner make a more informed second attempt?

---

## 16. Architecture Boundaries

Implementation must preserve:

- FastAPI application architecture.
- Existing Assessment Activity model.
- Existing Submission → Evaluation → Feedback → Reflection → Completion journey.
- Existing Evaluation and Feedback domain models.
- SPEC-021 persistent Practice History.
- SPEC-022 Practice Modes.
- SPEC-023 internal Practice Capability Lens.
- SPEC-024 anonymous Learner Identity.
- SPEC-025 authored Practice Transitions.
- SPEC-026 Pre-Practice Intention.
- SPEC-027 learner artifact export.
- SPEC-028 Local Practice Draft.
- SPEC-029 Practice Content Model & Learning Contract.

Do not create a separate feedback domain merely to satisfy this specification.

---

## 17. Non-Goals

SPEC-030 does not:

- introduce scores;
- introduce grades;
- introduce mastery;
- rank learners;
- label learners by ability;
- create personalised recommendations;
- create an AI tutor;
- replace the existing evaluation mechanism;
- require an AI provider;
- add a feedback chat interface;
- add a new learner workflow;
- add authentication;
- add new persistence infrastructure;
- turn feedback into a Progress dashboard.

---

## 18. Acceptance Criteria

- [ ] A documented Feedback Contract is implemented or represented at the appropriate content/application boundary.
- [ ] Existing practice feedback is audited against SPEC-030.
- [ ] Feedback is grounded in the practice purpose and available evaluation evidence.
- [ ] Positive feedback is concrete rather than generic praise.
- [ ] Improvement guidance is specific and actionable.
- [ ] Feedback avoids unsupported claims about the learner.
- [ ] Feedback does not introduce scores, grades, mastery, ranking, or learner labels.
- [ ] Feedback supports a meaningful Reflection handoff.
- [ ] Existing Evaluation → Feedback behaviour remains architecturally intact.
- [ ] Existing practice history and review behaviour continue to work.
- [ ] Automated tests pass.
- [ ] Documentation explains how future evaluation mechanisms should preserve the Feedback Contract.
- [ ] The implementation remains compatible with the existing FastAPI + HTMX architecture.

---

## 19. Definition of Done

SPEC-030 is complete when a contributor can inspect the repository and understand what good Fablit feedback is expected to accomplish, and the existing practice feedback has been reviewed and refined accordingly.

The result should make the feedback loop materially more useful without making Fablit feel like a grading system.

---

## 20. Relationship to SPEC-029

SPEC-029 answers:

> **What makes a practice worth practising?**

SPEC-030 answers:

> **What makes the response to that practice worth learning from?**

Together they establish the foundation:

```
Practice Content Contract
          ↓
       Practice
          ↓
      Evaluation
          ↓
   Feedback Contract
          ↓
      Reflection
          ↓
   Practice Again
```
