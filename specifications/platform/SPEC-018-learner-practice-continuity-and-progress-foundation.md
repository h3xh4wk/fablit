# SPEC-018 — Learner Practice Continuity & Progress Foundation

**Status:** Proposed
**Version:** 0.1
**Type:** Platform / Learner Experience
**Depends on:** SPEC-017
**Primary Module:** Practice / Learner Journey

---

## 1. Problem Statement

The current learner journey supports a complete practice cycle through submission, evaluation, feedback, reflection, and completion. However, the MVP does not yet establish a small foundation for recognizing that a learner has completed practice and for showing continuity when the learner returns.

The next step should not be a full progress or mastery system. The immediate goal is to preserve the fact that meaningful practice was completed so the learner experience can begin to acknowledge prior practice without introducing scores, mastery calculations, streaks, recommendations, or analytics.

This specification establishes a minimal practice-completion foundation while deliberately leaving richer Progress capabilities for a later specification.

---

## 2. Objectives

SPEC-018 shall:

1. Record a practice completion only after the learner successfully completes reflection.
2. Preserve enough information to identify the completed activity and when it was completed.
3. Allow the learner dashboard to recognize previously completed practice.
4. Support repeated practice of the same activity.
5. Keep the implementation lightweight and compatible with the current MVP architecture.
6. Establish a clean foundation for future Progress and mastery capabilities without implementing them now.

---

## 3. Scope

### In Scope

- Practice completion recording.
- Completion association with the activity being practised.
- Completion timestamp.
- Minimal learner context required by the current application architecture.
- Dashboard recognition of completed/practised activities.
- Repeated completion of an activity.
- Application-level tests for completion and dashboard continuity.

### Out of Scope

- Numerical progress percentages.
- Skill mastery or proficiency levels.
- Scores or ranking.
- Streaks, badges, points, or gamification.
- Recommendations or adaptive learning.
- Analytics or reporting infrastructure.
- Authentication or identity management.
- Durable database architecture if the current MVP persistence model does not require it.
- Rich attempt history or evidence aggregation.
- Changes to evaluation or scoring behaviour.
- Content Pack infrastructure.

---

## 4. User Stories

### US-018-01 — Recognize Completed Practice

**As a learner,**
I want the application to remember that I completed an activity,
**so that** returning to the practice area feels continuous rather than starting from zero each time.

### US-018-02 — Repeat Practice

**As a learner,**
I want to practise an activity again after completing it,
**so that** completion does not prevent deliberate repetition.

### US-018-03 — Avoid Premature Completion

**As a learner,**
I want an activity to count as completed only after I finish the intended practice journey,
**so that** simply submitting an answer does not incorrectly represent completed practice.

---

## 5. Functional Requirements

### FR-018-01 — Completion Trigger

A practice completion shall be recorded only after the learner successfully saves/submits the reflection for the current practice journey.

Submitting a response or receiving an evaluation result alone shall not create a practice completion.

### FR-018-02 — Completion Record

The application shall maintain a minimal completion record containing, as supported by the current architecture:

- learner context;
- activity identifier;
- completion timestamp;
- completion context if required to distinguish the current learner journey.

The record must not infer skill mastery, proficiency, quality, or improvement.

### FR-018-03 — Dashboard Continuity

The learner dashboard shall be able to identify activities that have previously been completed.

The initial presentation may remain lightweight—for example, a simple completed/practised indication or a list of previously practised activities. It shall not become a progress dashboard as part of SPEC-018.

### FR-018-04 — Repeated Practice

Completing an activity shall not make it unavailable for future practice.

The implementation should conceptually support multiple completion events for the same activity rather than treating completion as a permanent one-time state.

### FR-018-05 — No Mastery Inference

A completion event shall not be interpreted as evidence that the learner has mastered the associated skill.

No mastery, proficiency, skill-level score, or progress percentage shall be calculated from completion records.

### FR-018-06 — Existing Journey Preservation

The existing journey remains:

```text
Dashboard
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
Dashboard
```

SPEC-018 adds continuity to the completion/dashboard boundary without changing the existing evaluation, feedback, or reflection behaviour.

---

## 6. Persistence Approach

SPEC-018 should use the existing persistence/retention architecture rather than introducing a new database solely for this capability.

If the current MVP deliberately uses in-memory application state, an in-memory completion record is acceptable for this specification. The design should nevertheless keep the completion concept isolated enough that it can later be moved to durable persistence without changing the learner-facing contract.

Do not introduce authentication, database migrations, repositories, queues, or distributed infrastructure unless the current implementation already requires them for the smallest viable completion record.

---

## 7. Dashboard Behaviour

The dashboard should distinguish between activities that have never been completed and activities for which the learner has completed practice before.

The first implementation should remain deliberately simple. Suitable examples include:

- “Practised” or “Completed” metadata on an activity;
- a small completion indicator;
- a lightweight previously-practised section.

Avoid:

- percentage bars;
- mastery labels;
- comparative rankings;
- streak counters;
- recommendations;
- gamification.

The purpose is continuity, not measurement.

---

## 8. Acceptance Criteria

### AC-018-01 — Completion after Reflection

**Given** a learner completes the response, evaluation, feedback, and reflection flow
**When** the reflection is successfully saved
**Then** a practice completion record exists for the activity.

### AC-018-02 — No Completion on Failed Reflection

**Given** the learner has reached reflection
**When** saving/submitting the reflection fails
**Then** no new completion record is created.

### AC-018-03 — Dashboard Continuity

**Given** a learner has previously completed an activity
**When** the learner returns to the dashboard/practice area
**Then** the activity can be identified as previously practised/completed.

### AC-018-04 — Repeated Practice

**Given** a learner has previously completed an activity
**When** the learner practises and completes the same activity again
**Then** the second completion is accepted and the activity remains available for practice.

### AC-018-05 — No Premature Completion

**Given** a learner submits a response and receives an evaluation
**When** the learner has not successfully completed reflection
**Then** no practice completion is recorded.

### AC-018-06 — No Mastery Inference

**Given** one or more completion records exist
**When** the application prepares learner/dashboard data
**Then** it does not calculate or expose mastery, proficiency, skill score, percentage progress, streaks, or ranking from those records.

### AC-018-07 — Evaluation Unchanged

**Given** an otherwise identical response
**When** SPEC-018 is present
**Then** evaluation behaviour and evaluation content remain unchanged.

---

## 9. Testing Checklist

### Unit Tests

- [ ] Completion is created after successful reflection.
- [ ] Completion is not created when reflection fails.
- [ ] Completion references the correct activity.
- [ ] Completion records include a completion timestamp.
- [ ] Multiple completions for the same activity are supported.
- [ ] No mastery/proficiency state is inferred from completion.

### Integration Tests

- [ ] Full learner journey creates a completion after reflection.
- [ ] Dashboard recognises a previously completed activity.
- [ ] Repeating an activity creates another completion without blocking practice.
- [ ] Existing evaluation behaviour remains unchanged.

### Manual UX Verification

A learner should:

```text
Complete an activity
    ↓
Return to dashboard
    ↓
See that the activity was practised/completed
    ↓
Choose the same activity again
    ↓
Complete it again
```

The experience should communicate continuity without feeling like a scoring or mastery system.

---

## 10. Architectural Constraints

SPEC-018 must respect the existing project architecture.

In particular:

- Preserve the existing FastAPI backend approach.
- Preserve the existing HTMX/server-rendered MVP frontend approach.
- Keep the learner journey orchestration in the existing application layer.
- Do not introduce a SPA framework.
- Do not redesign the Skill domain.
- Do not make completion records responsible for calculating Skill Progress.
- Do not modify evaluation or scoring logic.
- Avoid introducing new persistence infrastructure unless necessary for the existing MVP.
- Keep the completion concept separable from future durable Progress infrastructure.

---

## 11. Future Progression

SPEC-018 intentionally creates a foundation rather than implementing the full Progress module.

Future specifications may build on this foundation to support:

- durable practice history;
- richer attempts and submissions;
- skill-level evidence;
- Skill Progress;
- mastery/proficiency models;
- progress visualisation;
- longitudinal analytics;
- recommendations or adaptive practice.

Those capabilities should be specified separately once learner validation demonstrates that they are valuable.

---

## 12. Definition of Done

SPEC-018 is complete when:

- [ ] Practice completion is recorded only after successful reflection.
- [ ] The dashboard can recognise previously completed practice.
- [ ] Repeated practice remains possible.
- [ ] No mastery, score, percentage progress, streak, ranking, or recommendation logic is introduced.
- [ ] Automated tests cover the completion lifecycle and dashboard continuity.
- [ ] Existing evaluation and feedback behaviour remains unchanged.
- [ ] The implementation follows the current lightweight MVP architecture.
- [ ] No unnecessary database or infrastructure changes are introduced.
- [ ] Architecture review approves the implementation.
- [ ] The associated GitHub issue and PR are linked to SPEC-018.

---

## 13. References

- Project Charter
- Architecture Blueprint
- Domain Language
- SPEC-009 — Reflection Domain Foundation
- SPEC-010 — Skill Domain Foundation
- SPEC-011 — Skill–Assessment Activity Association
- SPEC-012 — Learner Practice Application Flow
- SPEC-016 — Learner Experience and Visual Foundation
- SPEC-017 — Submission & Evaluation Feedback
