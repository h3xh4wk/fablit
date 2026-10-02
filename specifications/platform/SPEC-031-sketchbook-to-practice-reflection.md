# SPEC-031: Sketchbook-to-Practice Reflection

## 1. Overview & Goal

SPEC-031 introduces a focused bridge between the learner's existing sketchbook practice and Fablit's deliberate-practice loop.

Fablit should complement the work learners already do rather than require them to replace it with another stream of exercises.

For design-entrance preparation, sketching is often the primary activity. A learner may already have a drawing, composition, object study, ideation page, or situation-test attempt outside Fablit. SPEC-031 allows that existing work to become the starting point for a small Fablit reflection practice.

The product promise is:

> **Bring something you already practised. Notice what your own work can teach you.**

This is not a drawing-evaluation product. Fablit should help the learner reflect on their creative process, not judge the visual quality of the sketch itself.

---

## 2. Product Principle

Fablit should reduce resource and workflow fragmentation.

Instead of requiring:

```
Sketch elsewhere
   ↓
Find another resource
   ↓
Start another exercise
```

the learner can use:

```
Sketchbook work
   ↓
Bring it to Fablit
   ↓
Reflect
   ↓
Receive focused feedback
   ↓
Identify something to notice next time
   ↓
Return to sketching
```

The sketch remains the learner's work.

Fablit provides the deliberate reflection layer around that work.

---

## 3. Scope

### In scope

- An optional Sketchbook Reflection practice entry point.
- Learner-provided sketch/image as a practice artifact.
- A focused reflection prompt associated with the artifact.
- Evaluation and feedback focused on the learner's stated reflection, not visual quality.
- Persistence through the existing learner-scoped practice history.
- Review of the completed reflection alongside the practice artifact where supported.
- Calm integration with the existing Practice journey.

### Out of scope

- Automatic judging or grading of drawings.
- Computer-vision scoring of sketches.
- AI image critique.
- Drawing recognition.
- Automatic portfolio curation.
- Social sharing.
- Public galleries.
- Learner ranking.
- Image search or reference generation.
- A full digital sketchbook application.
- Required upload for ordinary Fablit practices.
- Replacing existing sketching tools.

---

## 4. Learner Experience

The feature should remain optional.

A learner may encounter an entry point such as:

> **Practised something in your sketchbook? Reflect on it.**

The learner then:

1. Selects or captures a sketch/image.
2. Sees a short reflection prompt.
3. Describes what they noticed, decided, struggled with, or would change.
4. Submits the reflection.
5. Receives feedback based on the written reflection and the stated practice purpose.
6. Completes the practice.
7. May return to sketching or choose an existing Fablit practice.

The learner should never be required to upload a sketch to use the rest of Fablit.

---

## 5. Reflection Focus

The reflection prompt should ask about the learner's creative process rather than whether the drawing is aesthetically "good".

Useful reflection dimensions include:

- observation;
- composition decisions;
- proportion decisions;
- material or form choices;
- ideation choices;
- interpretation;
- problem-solving;
- time/effort decisions;
- what changed during the attempt;
- what the learner would notice or try differently next time.

The prompt should be specific enough to produce useful reflection without becoming a long written assignment.

---

## 6. Artifact Boundary

The learner-provided sketch is an artifact associated with the practice attempt.

The artifact should be treated as learner-owned practice material.

The implementation should define:

- accepted image formats;
- reasonable file-size limits;
- validation behaviour;
- safe storage;
- association with the learner-scoped practice attempt;
- review behaviour;
- deletion/retention behaviour.

The implementation must use the smallest storage model consistent with the existing architecture.

A sketch artifact must not become a new public or searchable resource.

---

## 7. Evaluation Boundary

SPEC-031 deliberately separates **artifact observation** from **learner reflection evaluation**.

For the initial implementation:

```
Sketch
  │
  │ provides context
  ▼
Learner Reflection
  │
  ▼
Existing Evaluation
  │
  ▼
Feedback
```

The system should not claim that it has evaluated drawing quality unless a future specification explicitly introduces and validates such capability.

The learner's written reflection is the primary evaluable response.

Where the UI displays the uploaded sketch during review, it is presented as context for the learner's own reflection.

---

## 8. Feedback Relationship

SPEC-030 remains the feedback contract.

Feedback should address what the learner's reflection demonstrates.

Examples:

- The learner identified a proportion problem and described how it affected the composition.
- The learner noticed a change in their approach during the sketch.
- The learner described a design decision but did not explain why it supported the intended outcome.
- The learner identified what they would change but did not connect it to visible evidence in their own work.

Feedback should not make unsupported claims about artistic ability.

---

## 9. Practice Modes

Sketchbook Reflection should initially be available as a **Short Drill**.

The purpose is to create a small reflection layer around work the learner has already completed, not to create another long practice session.

A typical interaction should be realistically completable in approximately 5–10 minutes, excluding the time already spent creating the sketch.

The upload itself is not the practice.

The reflective thinking is the practice.

---

## 10. Practice Content Contract

The Sketchbook Reflection activity must comply with SPEC-029.

Its content definition should include:

- Purpose: turn existing sketchbook work into deliberate reflection.
- Primary creative-thinking lens: Reflect.
- Expected thinking: connect an actual creative decision or observation to evidence from the learner's own work.
- Response contract: concise written reflection.
- Evaluation intent: identify specificity, evidence, awareness of process, and meaningful next learning point.
- Feedback intent: help the learner understand something about their creative process and what to notice next time.
- Reflection intent: identify one observation or decision to carry into another attempt.
- Continuation intent: optionally return to an existing authored practice or the learner's sketching process.

---

## 11. Practice History

A completed Sketchbook Reflection should use the existing learner identity and practice-history mechanisms.

The history record should retain enough information for the learner to understand:

- which reflection practice was completed;
- the submitted reflection;
- the associated sketch artifact, subject to the artifact-retention policy;
- evaluation;
- feedback;
- reflection;
- completion time.

The feature must not create a parallel personal journal or second history system.

---

## 12. Privacy and Ownership

Sketch artifacts may contain personal, educational, or contextual information.

Therefore:

- artifacts are private to the learner identity associated with the practice;
- artifacts must never be publicly indexed;
- artifact URLs must not expose another learner's material;
- access must respect the existing learner-scoped history boundary;
- the implementation must not expose the anonymous learner identifier to client-side code unnecessarily;
- the feature must not introduce social sharing.

A learner should have a clear way to remove an uploaded artifact where the implementation supports persistent storage.

---

## 13. Failure and Degraded Behaviour

The feature must degrade gracefully.

Examples:

- unsupported file type → clear validation message;
- oversized image → clear validation message;
- upload failure → learner can retry without losing the written reflection where feasible;
- storage unavailable → do not create a misleading completed record;
- image unavailable during review → reflection remains understandable without the image;
- browser/device without image selection → learner can skip the feature and continue normal Fablit practice.

Ordinary Fablit practices must remain fully usable if the Sketchbook Reflection feature is unavailable.

---

## 14. Relationship to Existing Specifications

SPEC-031 builds on:

- SPEC-018 — Learner Practice Continuity & Progress Foundation.
- SPEC-021 — Persistent Practice History & Learner Review.
- SPEC-022 — Optional Practice Modes & Learner Choice.
- SPEC-023 — Practice Library Expansion & Skill Coverage.
- SPEC-024 — Learner Identity & Private Practice History.
- SPEC-025 — Curated Practice Continuity.
- SPEC-026 — Pre-Practice Intention.
- SPEC-027 — Learner Portfolio & Artifact Export.
- SPEC-028 — Local Practice Draft.
- SPEC-029 — Practice Content Model & Learning Contract.
- SPEC-030 — Practice Feedback Quality.

It should reuse the existing practice journey rather than introduce a separate workflow.

---

## 15. Architecture Boundaries

Implementation must preserve:

- FastAPI + HTMX architecture.
- Existing Assessment Activity model where appropriate.
- Existing Submission → Evaluation → Feedback → Reflection → Completion journey.
- Existing learner-scoped identity.
- Existing Practice History.
- Existing Short Drill mode.
- Existing feedback contract.
- Existing export behaviour where practical.

The feature should not require a new learner-account model.

If persistent image storage requires infrastructure not currently present, implementation should use the smallest repository-compatible mechanism and document the boundary before introducing it.

Do not introduce a cloud media platform solely for speculative future use.

---

## 16. Content and UI Principles

The feature should feel like an extension of Fablit's calm editorial practice experience.

Avoid:

- "Upload your work for grading."
- scores;
- star ratings;
- "AI judge" language;
- competitive comparison;
- portfolio-performance claims;
- pressure to upload after every sketch.

Prefer language such as:

- "Bring a sketch"
- "Look again"
- "What did you notice?"
- "What would you try differently?"
- "Keep this reflection"

The feature should feel optional and useful, not like another obligation.

---

## 17. Non-Goals

SPEC-031 does not:

- evaluate drawing quality;
- compare sketches between learners;
- infer learner ability from images;
- create an AI vision evaluator;
- create a digital sketchbook;
- create a portfolio marketplace;
- create social sharing;
- create public profiles;
- create personalized recommendations;
- require image upload for normal practices;
- introduce scores or mastery;
- replace existing sketching workflows.

---

## 18. Acceptance Criteria

- [ ] An optional Sketchbook Reflection practice exists.
- [ ] A learner can provide a sketch/image as context for the practice.
- [ ] The feature uses the existing learner-scoped identity boundary.
- [ ] The learner can complete the reflection without the system judging drawing quality.
- [ ] The written reflection is the primary evaluable response.
- [ ] The practice is classified as a Short Drill.
- [ ] Feedback follows SPEC-030 and is grounded in the learner's reflection.
- [ ] Completed practice is represented in the existing Practice History.
- [ ] Review can show the reflection and associated artifact subject to retention rules.
- [ ] Artifact access is private and learner-scoped.
- [ ] Invalid/oversized/unavailable uploads fail gracefully.
- [ ] Ordinary Fablit practices remain unaffected if the feature is unavailable.
- [ ] No scoring, mastery, ranking, recommendation, social sharing, or AI image evaluation is introduced.
- [ ] Automated tests cover validation, ownership boundaries, successful completion, and failure paths.
- [ ] Documentation explains artifact handling and retention/deletion behaviour.
- [ ] The implementation remains consistent with the existing FastAPI + HTMX architecture.

---

## 19. Definition of Done

SPEC-031 is complete when a learner can take work they already created in their sketchbook, bring it into Fablit for a short, purposeful reflection, receive useful feedback on their thinking, and retain the resulting practice in the existing private history.

The feature should strengthen the relationship:

```
Sketch
  ↓
Reflection
  ↓
Feedback
  ↓
Learning
  ↓
Next sketch
```

without turning Fablit into a drawing grader, portfolio platform, or another large resource library.
