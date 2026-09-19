# SPEC-022 — Optional Practice Modes & Learner Choice

**Status:** Proposed
**Version:** 0.1
**Type:** Platform / Learner Experience / Practice Orchestration
**Depends on:** SPEC-018, SPEC-019, SPEC-020, SPEC-021
**Primary Modules:** Application / Learner Experience / Demo Content

---

## 1. Problem Statement

Fablit currently presents a small library of practice activities and a complete learner journey:

```
Explore
  ↓
Choose Practice
  ↓
Practice Activity
  ↓
Response
  ↓
Evaluation
  ↓
Feedback
  ↓
Reflection
  ↓
Completion
  ↓
Practice History
```

Learner feedback suggests that practice does not always happen in the same way.

For example, a learner may regard a longer activity such as sketching as the main work of a session, while sometimes wanting a short observation or writing exercise between longer practice sessions. A short drill can therefore be useful without becoming the default expectation for every learner or every session.

The product should respond to that reality by giving learners a small amount of explicit choice about **how they want to practise right now**.

The goal is:

> **Let learners choose an appropriate shape of practice without introducing forced schedules, recommendations, timers, scores, or a larger personalization system.**

The core principle is:

> **Choice before prescription.**

---

## 2. Objectives

SPEC-022 shall:

1. Introduce a lightweight practice-mode concept at the application/learner-experience boundary.
2. Let a learner explicitly choose between a short optional drill and the existing fuller practice experience.
3. Keep shorter practice genuinely optional; learners must be able to continue with the normal activity library.
4. Reuse existing Assessment Activities and learner-journey semantics rather than creating a parallel learning system.
5. Make the expected effort/time visible as guidance where useful, without enforcing a countdown.
6. Preserve the existing submission, evaluation, feedback, reflection, completion, and persistent-history behaviour.
7. Keep learner choice explicit rather than inferred from history, behaviour, or hidden personalization logic.
8. Provide a foundation that can later support additional practice shapes without introducing a generic recommendation engine.

---

## 3. Scope

### In Scope

- A small, explicit set of learner-selectable practice modes.
- An initial **Short Drill** mode intended for a compact practice session.
- The existing **Full Practice** mode representing the current standard activity journey.
- A lightweight learner-facing chooser such as:
  - "A short drill"
  - "A full practice"
- Optional indicative effort guidance, for example:
  - "A few minutes"
  - "A longer focused practice"
- Selection of existing activities appropriate to the chosen mode.
- Reuse of the existing Activity → Submission → Evaluation → Feedback → Reflection → Completion journey.
- Application/view-layer representation of mode selection where possible.
- Practice-history compatibility: completed practice remains stored and reviewable under SPEC-021.
- Learner-facing tests for mode selection and resulting practice entry.
- Documentation of the mode-selection boundary and supported mode semantics.

### Out of Scope

- A mandatory daily practice schedule.
- Countdown timers or time-enforced exams.
- Automatic recommendations based on learner history.
- AI-generated personalization.
- Adaptive learning.
- Skill mastery or proficiency.
- Scores, grades, percentages, ranks, streaks, points, badges, or gamification.
- A recommendation/ranking engine.
- A learner-profile or preference-management system.
- Authentication or account-management architecture.
- New Assessment Activity domain types solely to represent modes.
- A second submission/evaluation/reflection workflow.
- Changing evaluation criteria.
- Changing feedback semantics.
- Changing reflection semantics.
- Changing completion semantics.
- Replacing the Explore activity library.
- Portfolio, social, mentor, or peer-review capabilities.
- A new frontend framework or SPA architecture.

---

## 4. Learner Intent

The learner should be able to answer a simple question:

> **What kind of practice do I want right now?**

The initial experience should support at least two intentionally different choices.

### Short Drill

A compact practice option for moments when the learner has limited time, wants to reset attention, or wants a small exercise between longer sessions.

The initial target is approximately **5–10 minutes of learner effort**, but this is guidance rather than an enforced duration.

A Short Drill may use an existing observation or writing-oriented activity with a concise prompt and response expectation.

### Full Practice

The existing Fablit practice experience remains available as the standard path.

Full Practice continues to use the current Practice Activity presentation and learner journey established by SPEC-020 and earlier specifications.

---

## 5. Practice Mode Model

Practice mode is a **learner-experience/application concept**, not a replacement for Assessment Activity.

Conceptually:

```
Practice Mode
   ↓
selects an appropriate existing activity
   ↓
existing Assessment Activity
   ↓
existing learner journey
```

A mode may provide:

- a stable mode identifier;
- learner-facing label;
- concise description;
- optional indicative effort guidance;
- a rule or explicit configuration describing which existing activities are eligible.

The mode must not duplicate activity identity, Skill semantics, Evaluation semantics, or Completion semantics.

The initial mode set should remain deliberately small.

For example:

```
SHORT_DRILL
FULL_PRACTICE
```

Do not introduce a generic rule engine for arbitrary learner personalization.

---

## 6. Activity Eligibility

The mode selection layer should identify activities appropriate to the selected practice shape.

For the initial implementation:

### Short Drill eligibility

Prefer activities that:

- can be completed with a concise learner response;
- are useful as observation, noticing, or short writing practice;
- do not require additional infrastructure;
- fit naturally into a compact session.

### Full Practice eligibility

The existing practice library remains available without requiring a new filtering system.

Eligibility should be defined through explicit content/application configuration rather than inferred from activity titles alone.

Where practical, the mode metadata should live with demo/content configuration or an application-level view model rather than altering the core domain model.

---

## 7. Learner Choice Experience

The learner should encounter a calm, low-friction choice rather than another dashboard full of controls.

A conceptual presentation is:

```
What kind of practice feels right today?

[ A short drill ]
A few minutes to notice, write, or reset your attention.

[ A full practice ]
A longer focused activity with the complete practice journey.
```

The exact wording may evolve through UX review.

The experience should:

- make the choice explicit;
- explain the difference briefly;
- avoid pressure language;
- avoid showing a score or progress consequence for either choice;
- keep the existing Explore surface available;
- allow the learner to return to the activity library.

The mode choice should not become a gate that prevents access to ordinary activities.

---

## 8. Short Drill Experience

The Short Drill should feel lighter in **scope**, not lower in learning value.

A drill should still follow the same fundamental loop:

```
Choose Drill
   ↓
Observe / Read Prompt
   ↓
Respond
   ↓
Evaluation
   ↓
Feedback
   ↓
Reflection
   ↓
Completion
```

The Short Drill may reduce the amount of content or response expected, but it must not bypass the meaningful learning loop merely to appear faster.

The implementation should reuse:

- existing Assessment Activities;
- existing Submission;
- existing Evaluation;
- existing Feedback;
- existing Reflection;
- existing Completion;
- existing durable Practice History.

No separate "mini evaluation" architecture should be created.

---

## 9. Full Practice Preservation

The current learner journey remains authoritative for Full Practice:

```
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
History / Review
```

SPEC-022 must not make the existing journey longer, more complicated, or conditional on selecting a mode first.

A learner who ignores the mode chooser must still be able to reach the normal activity library.

---

## 10. Effort Guidance

Short Drill may display an indicative effort expectation.

For example:

- "A few minutes"
- "About 5–10 minutes"

The value is a **guide**, not a contract.

Do not introduce:

- countdown timers;
- forced completion windows;
- time-based grading;
- penalties for taking longer;
- automatic session termination.

The learner remains in control of when to stop or continue, subject only to the existing activity completion semantics.

---

## 11. Interaction With Practice History

SPEC-021 remains authoritative for persistence.

A completed Short Drill is simply completed practice.

History should continue to record:

- activity identity;
- the activity-instance stimulus/context where applicable;
- response;
- evaluation;
- feedback;
- reflection;
- completion timestamp.

The history layer may optionally retain the selected practice mode as contextual metadata **only if it is useful for later review and can be introduced without changing the meaning of PracticeCompletion**.

Mode must not become a scoring, progress, or ranking dimension.

Repeated Short Drill or Full Practice activity remains possible.

---

## 12. Learner Choice and No Hidden Personalization

SPEC-022 establishes **explicit choice**, not personalization.

The application must not silently choose a mode because:

- the learner practised recently;
- the learner has a history of short sessions;
- the learner has not practised for a period of time;
- the system estimates that the learner is tired;
- the system believes a particular activity is "better" for the learner.

A future recommendation system may use learner evidence separately, but that is outside this specification.

The learner's explicit selection is authoritative for the current practice entry.

---

## 13. Content Strategy

SPEC-022 should validate the usefulness of different practice shapes before expanding the content library substantially.

The initial implementation should therefore favour **curated reuse** of existing activities.

For example:

```
Short Drill
   ├── concise observation activity
   └── concise writing activity

Full Practice
   └── existing activity library
```

Do not create a large set of new activities solely to populate the new chooser.

The implementation should be able to grow later through content configuration rather than requiring application logic changes for every new activity.

---

## 14. Application Architecture

The intended layering is:

```
Learner Experience
        ↓
Practice Choice / Application Layer
        ↓
Existing Assessment Activity
        ↓
Existing Learner Journey
        ↓
Persistence / History
```

Practice mode selection should remain outside the domain model unless later evidence establishes a genuine domain requirement.

The application layer is responsible for:

- presenting the available modes;
- accepting explicit mode selection;
- resolving an eligible existing activity;
- starting the normal practice journey.

The domain remains responsible for:

- Assessment Activity semantics;
- Submission;
- Evaluation;
- Feedback;
- Reflection.

Persistence remains responsible for durable practice history under SPEC-021.

---

## 15. UX Direction

The existing Fablit visual direction remains the foundation:

- calm;
- editorial;
- spacious;
- warm-neutral;
- restrained;
- personal rather than gamified.

The mode chooser should feel like a small invitation rather than a settings screen.

Avoid:

- progress bars;
- decision trees;
- dashboards full of options;
- modal-heavy interactions;
- "streak" language;
- urgency language;
- competitive framing.

The learner should be able to understand the choice in seconds.

---

## 16. Accessibility

The practice-mode chooser must:

- use semantic interactive controls;
- have clear accessible names;
- preserve visible keyboard focus;
- maintain sufficient contrast;
- avoid colour-only differentiation;
- work at mobile, tablet, and desktop widths;
- remain understandable with assistive technology;
- respect the existing reduced-motion behaviour.

Indicative effort text must not be conveyed by visual styling alone.

---

## 17. Acceptance Criteria

### AC-022-01 — Explicit Practice Choice

**Given** the learner enters the practice-choice experience
**When** the available modes are presented
**Then** the learner can explicitly choose between Short Drill and Full Practice.

### AC-022-02 — Optional Short Drill

**Given** the learner does not want a short drill
**When** they enter practice
**Then** they can continue directly to the normal activity library without being forced into Short Drill.

### AC-022-03 — Short Drill Entry

**Given** the learner chooses Short Drill
**When** a drill is selected
**Then** the learner enters an existing compatible Assessment Activity using the normal practice journey.

### AC-022-04 — Full Practice Entry

**Given** the learner chooses Full Practice
**When** practice begins
**Then** the existing Practice Activity experience remains unchanged in learning semantics.

### AC-022-05 — Existing Journey Preservation

**Given** a learner starts either mode
**When** they complete the activity
**Then** the existing Submission → Evaluation → Feedback → Reflection → Completion journey remains intact.

### AC-022-06 — No Countdown

**Given** the learner starts Short Drill
**When** an indicative effort/time message is displayed
**Then** no countdown or forced time limit is imposed.

### AC-022-07 — Curated Eligibility

**Given** a Short Drill is requested
**When** the application selects an activity
**Then** the activity comes from explicit supported mode configuration rather than title-string inference or hidden personalization.

### AC-022-08 — Explicit Learner Intent

**Given** the learner chooses a practice mode
**When** practice begins
**Then** the selected mode determines the practice entry for that interaction.

### AC-022-09 — History Compatibility

**Given** the learner completes a Short Drill
**When** practice history is viewed
**Then** the completed practice is available through the existing SPEC-021 history/review capability.

### AC-022-10 — No Recommendation Engine

**Given** the learner opens the practice-choice experience
**When** modes are displayed
**Then** the system does not recommend or rank a mode using learner history or inferred behaviour.

### AC-022-11 — Accessibility

**Given** the learner uses keyboard navigation or assistive technology
**When** they interact with the mode chooser
**Then** the mode choices, descriptions, focus states, and resulting navigation remain accessible.

### AC-022-12 — Responsive Experience

**Given** a mobile, tablet, or desktop viewport
**When** the practice-choice experience is displayed
**Then** the learner can understand and select a mode without horizontal scrolling.

---

## 18. Testing Requirements

### Application Tests

Cover:

- available practice modes;
- explicit mode selection;
- eligible activity resolution;
- Short Drill and Full Practice entry;
- unsupported/empty eligibility configuration where applicable;
- no hidden history-based mode selection;
- preservation of the existing practice journey.

### Web/UI Tests

Verify:

- mode chooser rendering;
- accessible labels and keyboard focus;
- Short Drill entry;
- Full Practice entry;
- return to the normal Explore/activity library path;
- responsive presentation;
- absence of countdown or scoring language.

### Learner Journey Regression

Verify that both selected paths continue through:

```
Activity → Submission → Evaluation → Feedback → Reflection → Completion → History
```

The current learner journey and SPEC-021 history/review tests must continue to pass.

### Manual UX Review

Review at minimum:

1. Desktop mode chooser.
2. Mobile mode chooser.
3. Short Drill activity.
4. Full Practice activity.
5. A learner who bypasses the mode chooser and uses the normal activity library.
6. Keyboard navigation.

The key validation question is:

> **Does the learner feel invited to choose the kind of practice that fits the moment, without feeling that the product is prescribing how they should learn?**

---

## 19. Architectural Constraints

- Preserve FastAPI.
- Preserve HTMX/server-rendered frontend.
- Preserve the existing application/domain boundaries.
- Preserve SPEC-015 stimulus semantics.
- Preserve SPEC-017 submission/evaluation interaction semantics.
- Preserve SPEC-018 completion semantics.
- Preserve SPEC-020 practice presentation.
- Preserve SPEC-021 persistence/history semantics.
- Keep practice modes outside the core domain unless future evidence requires otherwise.
- Reuse existing Assessment Activities.
- Do not introduce a recommendation engine.
- Do not introduce hidden personalization.
- Do not introduce timers or countdowns.
- Do not introduce scores, mastery, analytics, or gamification.
- Do not introduce a new frontend framework.
- Do not create a parallel learner journey.

---

## 20. Future Progression

SPEC-022 intentionally establishes only the smallest useful practice-choice foundation.

Future specifications may separately explore:

- additional short-drill formats;
- visual observation mini-practice;
- writing micro-practice;
- drawing warm-ups;
- learner-defined practice preferences;
- richer activity metadata for content curation;
- optional session collections;
- authenticated learner preferences;
- evidence-based recommendations, if validated later.

Those capabilities should build on explicit learner choice and observed usage rather than introducing personalization speculatively.

---

## 21. Definition of Done

SPEC-022 is complete when:

- [ ] A lightweight practice-mode concept exists at the application/learner-experience boundary.
- [ ] Short Drill and Full Practice are explicitly selectable.
- [ ] Short Drill remains optional.
- [ ] Short Drill reuses existing Assessment Activities and the existing learner journey.
- [ ] Full Practice behaviour remains semantically unchanged.
- [ ] Indicative effort guidance does not introduce a countdown or enforced time limit.
- [ ] Activity eligibility is explicit and configuration/content-driven.
- [ ] No hidden personalization or recommendation logic is introduced.
- [ ] Completed Short Drill practice is compatible with SPEC-021 history/review.
- [ ] Accessibility requirements are covered.
- [ ] Mobile, tablet, and desktop layouts remain usable.
- [ ] Automated application and web/UI tests pass.
- [ ] Existing learner journey regression tests pass.
- [ ] FastAPI + HTMX architecture is preserved.
- [ ] No scoring, mastery, analytics, gamification, or new frontend framework is introduced.
- [ ] Manual UX review confirms that practice choice feels optional and learner-led.
- [ ] Architecture review approves the implementation.

---

## 22. References

- Project Charter
- UX-001 — Fablit Experience
- Architecture Blueprint
- SPEC-018 — Learner Practice Continuity & Progress Foundation
- SPEC-019 — Explore Surface & Visual Practice Refinement
- SPEC-020 — Visual Practice Experience Foundation
- SPEC-021 — Persistent Practice History & Learner Review
