# SPEC-021 — Persistent Practice History & Learner Review

**Status:** Proposed  
**Version:** 0.1  
**Type:** Platform / Persistence / Learner Experience  
**Depends on:** SPEC-015, SPEC-017, SPEC-018, SPEC-020  
**Primary Modules:** Application / Persistence / Learner Experience

---

## 1. Problem Statement

Fablit now captures a complete learner practice journey in the application layer:

```text
Stimulus
   ↓
Submission
   ↓
Evaluation
   ↓
Feedback
   ↓
Reflection
   ↓
Practice Completion
```

The current learner-journey store is in-memory. That was appropriate while establishing the domain and validating the first learner experience, but Fablit is now deployed on Google App Engine and requires application data to survive instance restarts, redeployments, and normal App Engine instance lifecycle behaviour.

The next step is therefore to establish a small, production-appropriate persistence boundary and use it to provide learners with a useful history of completed practice.

The goal is:

> **Make completed practice durable and reviewable without prematurely introducing skill mastery, scoring, analytics, or recommendations.**

The core learning progression remains:

> **Practice → Remember → Review → Improve**

---

## 2. Objectives

SPEC-021 shall:

1. Introduce a persistence abstraction around the existing learner-journey records.
2. Provide a Google Cloud Datastore-backed implementation suitable for the current Google App Engine deployment.
3. Persist completed practice records and the learner-journey evidence required to review them.
4. Allow a learner to review previous completed practice.
5. Preserve repeated practice as separate completion/history records.
6. Keep the existing in-memory implementation useful for unit tests and local development where practical.
7. Keep persistence concerns out of the domain model.
8. Avoid introducing progress, mastery, scoring, analytics, recommendations, or gamification.

---

## 3. Scope

### In Scope

- Persistence abstraction for learner-journey data.
- Google Cloud Datastore implementation.
- Durable storage of practice completion/history records.
- Durable storage or retrieval of the associated practice evidence required for review:
  - activity identity;
  - activity/stimulus context;
  - learner response/submission;
  - evaluation result;
  - feedback;
  - reflection;
  - completion timestamp/context.
- Learner-facing practice history.
- Chronological history of completed practice.
- Review of a previous completed practice.
- Exact or equivalent activity-instance stimulus/context used for the reviewed attempt, subject to the existing SPEC-015 stimulus semantics.
- Repeated practice without collapsing earlier history.
- Empty-history state for learners with no completed practice.
- Unit/application tests using an in-memory implementation or suitable test double.
- Datastore integration tests where practical and appropriate to the repository's testing infrastructure.
- Documentation of the persistence boundary and local/deployed configuration.

### Out of Scope

- Skill mastery or proficiency calculation.
- Skill-level progress metrics.
- Scores, percentages, grades, ranks, or leaderboards.
- Analytics dashboards.
- Recommendations or adaptive learning.
- Streaks, badges, points, or gamification.
- Changes to evaluator logic.
- Changes to evaluation criteria or scoring semantics.
- Changes to feedback semantics.
- Changes to reflection semantics.
- Changes to PracticeCompletion meaning beyond making it durable.
- Authentication or account-management architecture.
- Social/peer review.
- Portfolio/gallery functionality.
- New visual stimulus providers.
- Pixabay API integration.
- New frontend framework or SPA architecture.
- Background jobs or event streaming.
- Generic persistence infrastructure for unrelated future modules.
- Large-scale database optimisation beyond what is required for the scoped queries.

---

## 4. Architectural Direction

SPEC-021 establishes the first production persistence boundary for the learner journey.

The intended layering is:

```text
Learner Experience
        ↓
Application / Use Cases
        ↓
Learner Journey Repository / Persistence Port
        ↓
Google Cloud Datastore Adapter
```

The application layer must not depend directly on Google Cloud Datastore APIs where a persistence abstraction can express the required operation.

The domain layer must remain independent of:

- Datastore entities;
- Datastore keys;
- App Engine environment details;
- HTTP concerns;
- templates;
- CSS;
- serialization details.

The first persistence boundary should be deliberately narrow and focused on the existing learner journey rather than becoming a generic repository framework.

---

## 5. Persistence Model

The implementation shall persist enough information to reconstruct a completed practice review without relying on process-local memory.

At minimum, the persisted learner-history record must retain relationships equivalent to:

```text
Practice History / Completion
    ├── learner context
    ├── activity identity
    ├── completion timestamp
    ├── reflection identity/content
    ├── submission identity/content
    ├── evaluation identity/result
    ├── feedback identity/content
    └── stimulus/activity-instance context
```

The implementation may persist the existing records as separate Datastore entities or as an appropriately bounded aggregate/document structure, provided that:

1. the application can retrieve a completed practice efficiently;
2. repeated attempts remain distinguishable;
3. the review does not depend on another live in-memory instance retaining state;
4. domain/application semantics remain clear;
5. the chosen representation can evolve without coupling the domain to Datastore.

Do not create a broad relational-style schema or a generic data-access abstraction solely for theoretical future requirements.

---

## 6. Identity and Repeated Practice

A learner may practise the same activity multiple times.

SPEC-021 must **not** treat `activity_id` as the unique identity of practice history.

Each completed practice must remain independently reviewable.

Conceptually:

```text
Activity A
   ├── Completion 1
   ├── Completion 2
   └── Completion 3
```

Each completion/history record must have a stable identity or equivalent way to distinguish it from other attempts.

The existing `PracticeCompletion` semantics should remain intact. Persistence should make those records durable rather than redefine what completion means.

---

## 7. Completion Boundary

The authoritative completion boundary remains SPEC-018:

```text
Submit Response
      ↓
Evaluation
      ↓
Feedback
      ↓
Reflection
      ↓
Practice Completion
```

A practice must not appear in completed-practice history merely because a response was submitted or evaluated.

A completion becomes part of durable learner history only after the existing successful reflection/completion flow has succeeded.

Persistence failures must not silently create a false impression that completion was durably recorded.

The implementation should define clear error behaviour for a Datastore write failure and must not mark a learner's practice as durably complete if the persistence operation did not succeed.

---

## 8. Learner Practice History

The learner should have a simple way to access previous completed practice.

The intended conceptual flow is:

```text
Explore
   ↓
Your Practice / History
   ↓
Previous Practice
   ↓
Review
```

The history view should provide enough context to distinguish records, such as:

- activity title;
- completion date/time;
- concise practice context;
- indication that the item can be reviewed.

Do not add numerical performance indicators, scores, mastery labels, or progress percentages.

The history should be ordered predictably, with recent completed practice first unless the existing UX establishes another clear convention.

---

## 9. Practice Review

Selecting a completed practice should allow the learner to review the meaningful parts of that specific practice instance.

The review should expose, where available:

1. activity identity/title;
2. stimulus/context used for the practice;
3. original learner response;
4. evaluation result as currently defined by the application;
5. feedback;
6. learner reflection;
7. completion timestamp.

The review experience should preserve the existing editorial visual direction from SPEC-019 and SPEC-020 but should remain functionally simple.

The review is a **reflection and evidence surface**, not a grading dashboard.

---

## 10. Stimulus Preservation

A review must not unexpectedly replace the original activity-instance stimulus with a newly resolved random/external stimulus.

The implementation shall follow the existing SPEC-015 stimulus semantics.

If the current application stores a resolved `StimulusInstance`, the persisted history must retain enough information to reproduce the relevant review context.

Where an external asset is involved, the implementation must follow the existing provider/attribution/fallback rules. SPEC-021 does not introduce a new image provider or live media retrieval strategy.

---

## 11. Persistence Adapter

The Google Cloud Datastore implementation should be isolated behind the persistence boundary.

The adapter is responsible for:

- converting application/domain records to Datastore-compatible representations;
- assigning and retrieving stable identifiers;
- writing learner-journey records;
- querying completed practice history;
- reconstructing application/domain records for review;
- handling Datastore-specific errors without leaking them into domain objects.

The application layer is responsible for:

- deciding when a completion should be recorded;
- orchestrating the learner journey;
- requesting history/review data;
- presenting appropriate success/failure states.

The domain model remains responsible for domain semantics, not persistence mechanics.

---

## 12. Google App Engine / Datastore Configuration

The implementation must support the current Google App Engine deployment model.

Configuration shall:

- keep Google Cloud project/environment configuration outside source-code business logic;
- use the normal Google Cloud authentication/application-default mechanism available to App Engine;
- avoid hard-coded credentials or service-account secrets;
- remain testable locally without requiring production credentials for unit tests;
- document any required Datastore configuration or indexes.

If Datastore indexes are required for the history queries, the implementation shall add and document only the indexes actually required by this specification.

Do not introduce a separate database service when Google Cloud Datastore satisfies the scoped requirements.

---

## 13. Local Development and Testing

The persistence boundary should allow application tests to remain fast and deterministic.

At minimum:

- unit/application tests should use an in-memory repository or equivalent test double;
- persistence mapping should be independently testable;
- Datastore integration tests should be isolated from tests that do not require GCP;
- production credentials must not be required for ordinary unit-test execution.

Where a local Datastore emulator is practical for the project, it may be used for integration testing, but SPEC-021 must not make the full test suite dependent on a running external emulator unless the repository already establishes that convention.

---

## 14. Failure Behaviour

Persistence failures must be explicit and observable at the application boundary.

The implementation shall not:

- silently discard completed-practice data;
- report a durable completion when the Datastore write failed;
- expose raw Datastore exceptions directly to learners;
- corrupt or partially overwrite an existing history record without a defined consistency strategy.

The learner-facing behaviour should provide a clear recoverable failure state where appropriate.

A retry must not unintentionally create duplicate completion records.

The implementation should therefore use stable completion identity or another idempotency strategy for the completion write.

---

## 15. Data Ownership and Privacy Boundary

SPEC-021 introduces persistence of learner-generated practice data.

The implementation should persist only the data necessary for the current learner-history/review capability.

Do not introduce unrelated personal information or profiling data.

The persistence model should keep learner context explicit so that future authentication/account work can establish ownership cleanly without requiring a redesign of the stored practice evidence.

SPEC-021 does not establish the complete authentication/authorization model. It should, however, avoid designing history as globally accessible or inherently tied to a single process instance.

---

## 16. UI / UX Requirements

The learner-facing history/review experience should remain consistent with the existing Fablit direction:

- calm;
- spacious;
- editorial;
- warm-neutral visual language;
- clear serif/sans hierarchy;
- restrained accents;
- minimal controls;
- no dashboard overload.

### Empty History

A learner with no completed practice should see a clear empty state explaining that completed practice will appear here.

The empty state should provide a natural path back to Explore/Practice without introducing gamification.

### History

History should make it easy to answer:

> **What have I practised recently?**

### Review

Review should make it easy to answer:

> **What did I do, what feedback did I receive, and what did I learn from it?**

---

## 17. Existing Learner Journey Preservation

The existing journey remains authoritative:

```text
Explore
   ↓
Choose Practice
   ↓
Practice Activity
   ↓
Submit Response
   ↓
Evaluation
   ↓
Feedback
   ↓
Reflection
   ↓
Completion
   ↓
Durable Practice History
   ↓
Review
```

SPEC-021 extends the journey after completion. It must not alter the meaning of earlier stages.

---

## 18. Acceptance Criteria

### AC-021-01 — Persistence Boundary

**Given** the learner journey is executed
**When** application code needs to store or retrieve learner-history data
**Then** it uses a persistence abstraction rather than depending directly on Datastore APIs throughout the application layer.

### AC-021-02 — Datastore Persistence

**Given** Fablit is running in the supported App Engine environment
**When** a learner completes practice successfully
**Then** the completion/history data is persisted in Google Cloud Datastore.

### AC-021-03 — Completion Semantics

**Given** a learner has submitted and evaluated a response
**When** reflection has not successfully completed
**Then** the practice does not appear as completed history.

### AC-021-04 — Durable Completion

**Given** a learner successfully completes reflection
**When** the completion persistence succeeds
**Then** the completed practice can be retrieved after the in-memory application state is no longer available.

### AC-021-05 — Reviewable Practice

**Given** a completed practice exists in durable storage
**When** the learner opens it from practice history
**Then** the review contains the relevant activity, stimulus/context, response, evaluation, feedback, reflection, and completion timestamp available to the application.

### AC-021-06 — Repeated Practice

**Given** the learner completes the same activity multiple times
**When** the learner opens practice history
**Then** each completed practice remains distinguishable and reviewable.

### AC-021-07 — Stable Stimulus Context

**Given** a completed practice used a resolved stimulus
**When** that practice is reviewed later
**Then** the review does not silently resolve an unrelated new stimulus merely because the learner is revisiting the record.

### AC-021-08 — Empty History

**Given** the learner has no completed practice
**When** practice history is opened
**Then** a clear empty state is shown with a path back to practice.

### AC-021-09 — Datastore Failure

**Given** a Datastore write fails during completion persistence
**When** the learner completes reflection
**Then** the application does not falsely represent the completion as durably recorded and presents a recoverable failure state.

### AC-021-10 — Idempotent Completion

**Given** the same completion operation is retried
**When** persistence is attempted again
**Then** the retry does not unintentionally create duplicate history for the same completion.

### AC-021-11 — Test Isolation

**Given** the ordinary unit/application test suite runs
**When** Datastore credentials or production infrastructure are unavailable
**Then** tests that do not require Datastore can still run using the in-memory implementation/test double.

### AC-021-12 — No Premature Progress System

**Given** the learner reviews practice history
**When** history and review are displayed
**Then** the UI does not introduce mastery, scores, percentages, rankings, streaks, or recommendations.

### AC-021-13 — Existing Journey Preservation

**Given** the learner completes a practice
**When** SPEC-021 is enabled
**Then** submission, evaluation, feedback, reflection, and completion behaviour remain semantically unchanged except for durable persistence of the resulting history.

---

## 19. Testing Requirements

### Unit / Application Tests

Cover at minimum:

- repository/persistence interface behaviour;
- in-memory repository compatibility;
- completion creation and retrieval;
- repeated completion records;
- history ordering;
- review reconstruction;
- completion boundary after successful reflection;
- no completion on failed reflection;
- idempotent completion persistence;
- persistence failure handling.

### Datastore Tests

Where supported by the project infrastructure, cover:

- entity serialization/deserialization;
- create/read of completion history;
- repeated practice records;
- history query ordering;
- review reconstruction;
- duplicate/idempotency protection;
- expected Datastore failure mapping.

### Web/UI Tests

Verify:

- history is reachable from the learner experience;
- empty history renders correctly;
- completed practices appear in chronological order;
- selecting a history item opens the correct review;
- response, feedback, reflection, and completion information are displayed correctly;
- repeated practices remain distinct;
- the existing practice journey still completes successfully.

### Regression

The complete existing learner journey and current test suite must continue to pass.

---

## 20. Architectural Constraints

- Preserve FastAPI.
- Preserve HTMX/server-rendered frontend.
- Preserve the existing domain model wherever possible.
- Preserve SPEC-015 stimulus semantics.
- Preserve SPEC-017 submission/evaluation interaction semantics.
- Preserve SPEC-018 completion semantics.
- Preserve SPEC-020 practice presentation.
- Use Google Cloud Datastore as the production persistence mechanism for this capability.
- Keep Datastore-specific code behind a persistence/application boundary.
- Do not make the domain layer depend on Google Cloud libraries.
- Do not hard-code credentials.
- Do not introduce a new SPA/frontend framework.
- Do not introduce unrelated persistence for future modules.
- Do not introduce scoring, mastery, analytics, recommendations, or gamification.

---

## 21. Future Progression

SPEC-021 establishes durable learner practice history. It deliberately does not attempt to answer every question that persistent data makes possible.

Future specifications may separately introduce:

- richer attempt/evidence modelling;
- skill-level evidence aggregation;
- Skill Progress and mastery;
- learner analytics;
- recommendations/adaptive practice;
- authenticated learner ownership;
- data retention/export/deletion policies;
- richer Content Packs;
- mentor/peer review;
- production-scale Datastore optimisation if learner volume requires it.

Those capabilities should build on validated persistence and learner-history behaviour rather than being introduced speculatively here.

---

## 22. Definition of Done

SPEC-021 is complete when:

- [ ] A focused persistence abstraction exists for learner practice history.
- [ ] Google Cloud Datastore is the production persistence implementation.
- [ ] Completed practice survives application instance lifecycle changes.
- [ ] Practice history can be viewed by the learner.
- [ ] A previous completed practice can be reviewed.
- [ ] Review retains the relevant activity/stimulus/response/evaluation/feedback/reflection context.
- [ ] Repeated practice remains distinguishable.
- [ ] Completion is persisted only after successful reflection/completion.
- [ ] Completion writes are safe against unintended duplication on retry.
- [ ] Datastore failures have explicit application-level handling.
- [ ] Unit tests remain independent of production Datastore credentials.
- [ ] Required Datastore indexes/configuration are documented.
- [ ] Existing learner journey semantics remain unchanged.
- [ ] Full regression suite passes.
- [ ] FastAPI + HTMX architecture is preserved.
- [ ] No mastery, scoring, analytics, recommendations, or gamification is introduced.
- [ ] Architecture review approves the implementation.

---

## 23. References

- Project Charter
- Architecture Blueprint
- SPEC-015 — Contextual Visual Stimulus & Response-Aware Evaluation
- SPEC-017 — Submission & Evaluation Feedback
- SPEC-018 — Learner Practice Continuity & Progress Foundation
- SPEC-019 — Explore Surface & Visual Practice Refinement
- SPEC-020 — Visual Practice Experience Foundation
