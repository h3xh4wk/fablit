# SPEC-033: Complete Sketchbook Reflection with Private Artifact Support

## 1. Overview & Goal

SPEC-033 completes the artifact boundary introduced by SPEC-031.

SPEC-031 establishes **Sketchbook Reflection — Notice What Your Work Taught You** as an optional Short Drill in which the learner brings existing sketchbook work into Fablit and reflects on it. SPEC-033 adds the private sketch/image artifact support required to make that journey complete.

The intended learner journey is:

```
Sketch/image
   ↓
Sketchbook Reflection
   ↓
Written reflection
   ↓
Evaluation
   ↓
Feedback
   ↓
Reflection / Completion
   ↓
Review
```

The sketch remains the learner's work. Fablit evaluates the learner's written reflection, not the visual quality of the sketch.

---

## 2. Product Principle

Fablit should complement the work learners already do rather than create another disconnected stream of exercises.

A learner should be able to:

```
Sketchbook work
   ↓
Bring it to Fablit
   ↓
Reflect
   ↓
Receive focused feedback
   ↓
Notice something for the next attempt
```

The artifact is context for reflection, not an object for grading, ranking, or public sharing.

---

## 3. Scope

### In scope

- Optional sketch/image input for Sketchbook Reflection.
- Explicit validation of supported image formats and file size.
- Private, learner-scoped artifact storage.
- Association of the artifact with the relevant practice/session/history record.
- Secure application-mediated artifact retrieval for review.
- Display of the artifact alongside the completed reflection where available.
- Graceful handling of invalid, oversized, missing, unavailable, or failed artifacts.
- Explicit retention/deletion behaviour.
- Testing of validation, ownership, association, retrieval, review, and failure paths.
- Preservation of the existing practice journey.

### Out of scope

- AI vision or image understanding.
- Automated drawing/sketch quality evaluation.
- Image scoring, grading, or ranking.
- Portfolio or public sharing.
- Social/community features.
- Authentication or cross-device learner identity.
- Personalised recommendations.
- Generic media-library functionality.
- A digital sketchbook application.
- Changes to ordinary non-sketchbook practices.

---

## 4. Learner Experience

The feature remains optional.

A learner using Sketchbook Reflection should be able to:

1. Choose to bring an existing sketch/image.
2. Upload a supported image.
3. See the focused reflection prompt.
4. Describe what they noticed, decided, struggled with, or would change.
5. Submit the reflection.
6. Receive feedback grounded in the written reflection.
7. Complete the practice.
8. Review the reflection together with the associated artifact when the artifact is available.

The learner must not be required to upload an image to use ordinary Fablit practices.

The upload itself is not the practice. The reflective thinking is the practice.

---

## 5. Artifact Contract

A Sketchbook Reflection artifact must have:

- a supported image format;
- a documented maximum size;
- validated image content rather than filename/MIME declaration alone;
- association with the learner-scoped practice attempt;
- a private storage reference;
- metadata sufficient for safe retrieval and review;
- defined retention/deletion behaviour.

The initial supported formats are:

- PNG
- JPEG/JPG
- WebP

The initial maximum upload size is **5 MB**.

The implementation must validate the actual image content and must not rely only on the filename or client-supplied MIME type.

The effective stored/served media type must remain consistent with the validated image format.

---

## 6. Storage Boundary

Raw artifact bytes must not be coupled to the Practice History entity.

The durable practice-history record should retain only the artifact metadata/reference required to associate and retrieve the learner's private artifact.

Conceptually:

```
Practice Completion
 ├── artifact reference
 ├── filename
 ├── content type
 ├── size
 └── learner-scoped association
             │
             ▼
       Private artifact storage
             │
             ▼
          image bytes
```

The chosen artifact storage mechanism must be appropriate to the deployment architecture and documented before implementation.

Artifact retrieval remains behind an application-controlled, learner-scoped route. Public direct media access must not be introduced.

The storage implementation must not become a generic media platform for unrelated Fablit features.

---

## 7. Ownership and Privacy

The artifact belongs to the learner identity associated with the practice attempt.

The implementation must:

- associate the artifact with the existing anonymous learner identity from SPEC-024;
- enforce learner ownership when retrieving an artifact;
- prevent access by changing completion or artifact identifiers;
- avoid exposing the anonymous learner identifier unnecessarily;
- keep artifacts private and non-indexable;
- avoid public/static media URLs that bypass application ownership checks.

Two anonymous learners must not be able to retrieve one another's artifacts.

The feature does not introduce authentication or cross-device identity.

---

## 8. Practice Association

Each artifact must be associated with the specific Sketchbook Reflection practice/session/history entry from which it originated.

The artifact must remain part of the existing Practice History model rather than creating a parallel journal or attachment history.

A completed history record should retain enough information for review to understand:

- which reflection practice was completed;
- the submitted reflection;
- the associated artifact metadata/reference, when present;
- evaluation;
- feedback;
- reflection;
- completion time.

---

## 9. Evaluation Boundary

SPEC-031 deliberately separates artifact context from reflection evaluation.

The initial flow is:

```
Sketch
  │
  │ context
  ▼
Written Reflection
  │
  ▼
Existing Evaluation
  │
  ▼
Feedback
```

The evaluator must not claim to judge visual quality.

The uploaded sketch must not be used to infer artistic ability, effort, motivation, mastery, or other learner traits.

Any future image understanding or drawing evaluation requires a separate specification.

---

## 10. Feedback Relationship

SPEC-030 remains the feedback contract.

Feedback should address what the learner's written reflection demonstrates, for example:

- whether the learner identified a concrete decision or observation;
- whether the learner connected that observation to evidence from their own work;
- whether the learner explained why a decision mattered;
- whether the learner identified a useful next learning point.

The artifact may provide context for the learner's reflection, but it does not itself become a graded response.

---

## 11. Practice Mode

Sketchbook Reflection is a **Short Drill**.

The intended interaction is approximately 5–10 minutes, excluding time already spent creating the sketch.

The feature should remain lightweight and should not turn an existing sketching session into a second long assignment.

---

## 12. Failure and Degraded Behaviour

The feature must fail safely.

Examples:

- unsupported file type → clear validation message;
- oversized file → clear validation message;
- invalid image content → clear validation message;
- artifact storage failure → do not create a misleading completed record;
- persistence failure → preserve the artifact for a safe retry where feasible;
- missing artifact during review → continue to display the written reflection and other history;
- unavailable artifact → do not make the practice history unusable;
- learner skips the upload → normal reflection/practice behaviour remains available.

A failed artifact operation must not silently corrupt or falsely complete the practice.

Artifact lifecycle handling must define a safe boundary between temporary upload state and durable completed practice state.

---

## 13. Retention and Cleanup

Artifact retention must follow the same privacy expectations as the associated learner practice history.

The implementation must document:

- when an uploaded artifact becomes durable;
- when an abandoned or failed temporary artifact is removed;
- how artifacts associated with deleted/expired history are handled, where applicable;
- how missing or orphaned artifact references are handled.

The system should avoid indefinite orphaned artifacts.

No public or searchable copy of the artifact should be created.

---

## 14. Review Experience

The completed practice review should display:

- the learner's written reflection;
- the associated sketch/image when available;
- basic artifact metadata where useful, such as filename;
- existing evaluation and feedback.

If the artifact is unavailable, review should remain useful and should not fail merely because the image cannot be retrieved.

Artifact retrieval must continue to enforce learner ownership.

---

## 15. Relationship to Existing Specifications

SPEC-033 builds directly on:

- SPEC-024 — Learner Identity & Private Practice History.
- SPEC-021 — Persistent Practice History & Learner Review.
- SPEC-022 — Optional Practice Modes & Learner Choice.
- SPEC-029 — Practice Content Model & Learning Contract.
- SPEC-030 — Practice Feedback Quality.
- SPEC-031 — Sketchbook-to-Practice Reflection.

It completes the artifact portion of SPEC-031 without changing the existing learner journey.

The later hardening issues **FIX-2** and **FIX-3** address storage-boundary and retry/validation concerns discovered during implementation. They refine the implementation of this specification; they do not replace SPEC-033.

---

## 16. Architecture Boundaries

Implementation must preserve:

- FastAPI + HTMX architecture;
- Python 3.12 and existing project conventions;
- existing Assessment Activity model;
- existing Submission → Evaluation → Feedback → Reflection → Completion journey;
- existing anonymous learner identity;
- existing Practice History;
- existing Short Drill mode;
- existing feedback contract.

The artifact storage mechanism must be the smallest production-appropriate boundary consistent with the deployment architecture.

Do not introduce:

- authentication;
- a general-purpose media-management system;
- public media access;
- AI image evaluation;
- a separate learner journal;
- a separate artifact history.

---

## 17. Content Contract

The Sketchbook Reflection practice must comply with SPEC-029.

Its content contract should include:

- **Purpose:** turn existing sketchbook work into deliberate reflection.
- **Primary lens:** Reflect.
- **Expected thinking:** connect an actual creative decision or observation to evidence from the learner's own work.
- **Response contract:** concise written reflection.
- **Evaluation intent:** identify specificity, evidence, awareness of process, and a meaningful next learning point.
- **Feedback intent:** help the learner understand something about their creative process and what to notice next time.
- **Reflection intent:** identify one observation or decision to carry into another attempt.
- **Continuation intent:** optionally return to an existing authored practice or the learner's sketching process.

The lens remains internal content metadata and is not a learner-facing progress category.

---

## 18. Non-Goals

SPEC-033 does not:

- evaluate drawing quality;
- compare sketches between learners;
- infer learner ability from images;
- create an AI vision evaluator;
- create a digital sketchbook;
- create a portfolio marketplace;
- create social sharing;
- create public profiles;
- create personalised recommendations;
- require image upload for normal practices;
- introduce scores or mastery;
- replace existing sketching workflows.

---

## 19. Acceptance Criteria

- [ ] A learner can optionally attach a supported sketch/image to Sketchbook Reflection.
- [ ] PNG, JPEG/JPG, and WebP are explicitly supported.
- [ ] The upload is limited to 5 MB.
- [ ] Image content is validated rather than relying only on filename/MIME declaration.
- [ ] Validated media type is consistent with the stored/served artifact.
- [ ] Artifact bytes are stored outside Practice History persistence.
- [ ] Practice History stores only the artifact reference/metadata needed for association and retrieval.
- [ ] Artifacts are private and learner-scoped.
- [ ] Artifact retrieval enforces learner ownership.
- [ ] The artifact is associated with the correct Sketchbook Reflection practice/history entry.
- [ ] Review displays the artifact and written reflection together when the artifact exists.
- [ ] Review remains usable when the artifact is missing or unavailable.
- [ ] Failed persistence does not silently lose an uploaded artifact needed for retry.
- [ ] Successful completion does not duplicate or corrupt the artifact.
- [ ] Retention and cleanup behaviour is documented.
- [ ] Cross-learner artifact access is prevented.
- [ ] Existing non-sketchbook practices remain unaffected.
- [ ] No AI vision, grading, scoring, portfolio, public sharing, authentication, or personalisation is introduced.
- [ ] Automated tests cover validation, storage/reference separation, ownership, retrieval, retry/failure behaviour, and review.
- [ ] Full CI/test/check suite passes.

---

## 20. Definition of Done

SPEC-033 is complete when a learner can take work already created in their sketchbook, optionally bring it into Fablit for a short, purposeful reflection, receive useful feedback on their thinking, and retain the resulting practice in the existing private history without exposing the artifact publicly or turning it into a drawing-grading system.

The resulting relationship is:

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

The artifact is private learner context throughout this journey.

---

## 21. Implementation Note

The original implementation work for SPEC-033 was tracked through GitHub Issue #109 and merged in PR #110.

Subsequent hardening work is tracked separately so that storage-boundary and retry semantics can be implemented and reviewed without obscuring the core feature specification.

