# SPEC-020 — Visual Practice Experience Foundation

**Status:** Proposed
**Version:** 0.1
**Type:** Platform / Learner Experience
**Depends on:** SPEC-015, SPEC-017, SPEC-018, SPEC-019
**Primary Module:** Learner Experience / Practice Activity

---

## 1. Problem Statement

SPEC-019 strengthened the Explore experience so that Fablit feels more like a design-practice product. The next step is to improve the experience after a learner enters an activity.

The Practice Activity screen should feel like a focused space for observing, thinking, responding, and learning from feedback rather than a conventional question-and-answer form.

Fablit already has the visual stimulus foundation established by SPEC-015. SPEC-020 therefore focuses on the **presentation and interaction of the existing practice experience**, not on creating another stimulus architecture.

The goal is:

> **Make the Practice Activity screen feel like a focused design-practice workspace while preserving the existing learner journey and learning model.**

---

## 2. Objectives

SPEC-020 shall:

1. Give appropriate visual stimuli a stronger, clearer presentation within the Practice Activity experience.
2. Make the relationship between stimulus, task, and learner response immediately understandable.
3. Give text-based responses comfortable space for developing an answer.
4. Preserve the existing submission, evaluation, feedback, reflection, and completion behaviour.
5. Continue the calm, editorial, warm-neutral visual direction established by earlier learner-experience specifications.
6. Keep the implementation incremental and presentation-focused.

---

## 3. Scope

### In Scope

- Refinement of the existing Practice Activity presentation.
- Clear presentation of existing visual stimuli and fallback assets.
- Clear hierarchy between stimulus, task/instruction, response area, and submission action.
- Comfortable response area for text-based activities.
- Responsive presentation across mobile, tablet, and desktop.
- Appropriate image proportions and non-destructive presentation of meaningful visual content.
- Accessible alternative text/decorative treatment for visual stimuli.
- Keyboard focus and usable interaction states.
- Subtle interaction refinement consistent with the existing visual language.
- Preservation of SPEC-017 submission acknowledgement and duplicate-submission protection.
- Preservation of SPEC-018 completion semantics.
- Automated web/UI tests for resulting learner-facing structure.
- Manual visual verification across representative viewport sizes.

### Out of Scope

- New Stimulus domain or application architecture.
- New external image provider integration.
- Pixabay API integration.
- Live/random image retrieval.
- Camera capture.
- Learner image uploads.
- Drawing canvas.
- Image annotation.
- Portfolio/gallery features.
- Moodboards.
- Peer critique or social feeds.
- Likes, votes, rankings, or leaderboards.
- Streaks, badges, points, or gamification.
- Exam countdowns.
- Progress rings or numerical progress indicators.
- Skill mastery or proficiency.
- Changes to evaluation logic or scoring.
- Changes to feedback semantics.
- Changes to reflection or completion semantics.
- Authentication.
- A new frontend framework or SPA architecture.

---

## 4. Design Direction

The visual direction established by SPEC-013, SPEC-016, and refined through SPEC-019 remains the foundation:

- calm;
- personal;
- spacious;
- editorial;
- warm neutral background;
- restrained accent colour;
- serif display typography with clear sans-serif body hierarchy;
- subtle rather than elaborate interaction.

SPEC-020 should **evolve this direction rather than replace it**.

The practice screen should feel focused and intentional. It should not become a dense dashboard or an exam simulator filled with metrics and controls.

Visual creativity should primarily come from the stimulus content, typography, composition, and generous spacing rather than decorative effects.

---

## 5. Practice Activity Hierarchy

The Practice Activity screen should make the following relationship obvious:

```text
Stimulus
   ↓
Task / Instruction
   ↓
Learner Response
   ↓
Submit
```

The learner should be able to understand what to look at, what to do, and where to respond without searching through unrelated interface elements.

The visual hierarchy should support concentration rather than compete with the activity.

---

## 6. Visual Stimulus Presentation

The implementation shall reuse the existing SPEC-015 stimulus lifecycle and available fallback/content mechanisms.

Where an activity has an appropriate visual stimulus:

- present it clearly and at a useful scale;
- preserve meaningful proportions;
- avoid unnecessary cropping of important content;
- provide appropriate alternative text;
- keep the stimulus visually distinct from surrounding instructions and controls.

Where an activity has no suitable visual stimulus:

- do not fabricate imagery merely to make the layout look consistent;
- retain a clean text-first experience;
- keep the task and response hierarchy intact.

The actual activity-instance stimulus remains authoritative when the learner starts practice. The Explore preview introduced by SPEC-019 must not become a second stimulus lifecycle.

---

## 7. Task and Instruction Presentation

Activity instructions should be easy to locate and read in relation to the stimulus.

The presentation should support a simple sequence:

1. Observe the material.
2. Understand the task.
3. Develop a response.
4. Submit the response.

Do not introduce additional instructional systems, timers, scoring indicators, or progress widgets as part of this specification.

---

## 8. Response Experience

For text-based activities, the response area should provide enough visual and physical space for a learner to formulate a thoughtful answer.

The implementation should:

- preserve the learner's response when validation or evaluation fails;
- make the response field visually identifiable;
- keep the submission action obvious;
- maintain keyboard accessibility;
- preserve the existing submission feedback from SPEC-017.

SPEC-020 does not introduce drawing or image-response functionality.

---

## 9. Submission and Evaluation Continuity

The existing interaction remains authoritative:

```text
Submit Response
      ↓
Evaluation
      ↓
Meaningful Feedback
      ↓
Reflection
      ↓
Completion
```

SPEC-020 must not change evaluation criteria, evaluator behaviour, scoring, or feedback semantics.

The immediate submission acknowledgement and duplicate-submission protection introduced by SPEC-017 must remain intact.

No artificial delay should be introduced for visual effect.

---

## 10. Responsive Behaviour

The Practice Activity experience shall remain usable across:

- mobile;
- tablet;
- desktop.

At smaller widths:

- stimulus content must remain readable;
- response controls must remain comfortable to use;
- task text must remain legible;
- submission controls must remain easy to tap;
- no horizontal scrolling should be required.

At larger widths:

- use available space to create a focused composition;
- avoid excessively wide reading measures;
- avoid filling empty space with unnecessary widgets.

The implementation should use the existing CSS architecture and design tokens.

---

## 11. Interaction

Interaction should remain subtle and purposeful.

Permitted refinements include:

- clearer focus states;
- restrained hover treatment where appropriate;
- clear visual affordance for the primary submission action;
- subtle state transitions already compatible with the existing accessibility approach.

Respect `prefers-reduced-motion`.

Do not introduce animated counters, celebration effects, streak animations, or other gamification.

---

## 12. Accessibility

Any visual stimulus introduced or refined by this specification must:

- have meaningful alternative text when it conveys information;
- be treated as decorative when nearby text already communicates the same information;
- preserve keyboard accessibility;
- preserve visible focus states;
- maintain sufficient text/background contrast;
- avoid using colour as the sole indicator of state.

Form controls and submission states must remain understandable to keyboard and assistive-technology users.

---

## 13. Existing Learner Journey Preservation

The existing journey remains unchanged:

```text
Dashboard / Explore
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
Dashboard / Explore
```

SPEC-020 changes the **practice presentation and response experience**, not the learning model.

---

## 14. Domain and Application Constraints

SPEC-020 must not redesign the existing domain model.

In particular:

- Do not modify Skill semantics.
- Do not modify Assessment Activity semantics solely for presentation.
- Do not modify Submission behaviour except where required to preserve the existing UI interaction.
- Do not modify Evaluation behaviour.
- Do not modify Feedback behaviour.
- Do not modify Reflection behaviour.
- Do not modify PracticeCompletion semantics.
- Do not make the Practice template responsible for inventing or replacing activity-instance stimuli.

Presentation-specific fields should remain in the application/view layer where possible.

---

## 15. Testing Requirements

### Unit/Application Tests

Where applicable:

- activity views expose the data required for practice presentation;
- activities with visual stimuli resolve the expected presentation data;
- activities without visual stimuli remain valid;
- existing completion/continuity state remains unchanged.

### Web Tests

Verify that:

- the Practice page renders the expected activity title/instruction;
- visual stimulus markup appears when configured;
- stimulus alternative-text/decorative behaviour is correct;
- activities without visual stimuli remain functional without fabricated imagery;
- the response control is present and usable;
- learner-entered text is preserved on failed submission/evaluation;
- successful submission continues through the existing evaluation flow;
- submission acknowledgement remains visible;
- duplicate in-flight submission protection remains intact;
- feedback, reflection, and completion continue to work.

### Regression Tests

The existing end-to-end learner journey must continue to pass without changes to learning semantics.

### Manual UX Verification

Verify at minimum:

1. Desktop activity with a visual stimulus.
2. Mobile activity with a visual stimulus.
3. Activity without a visual stimulus.
4. Text response with a short answer.
5. Text response with a longer answer.
6. Failed submission/evaluation with response preservation.
7. Successful submission and evaluation.
8. Keyboard navigation and visible focus.
9. Reduced-motion preference where practical.

The reviewer should specifically ask:

> **Does this feel like a focused place to practise design rather than simply a form to complete?**

---

## 16. Acceptance Criteria

### AC-020-01 — Focused Practice Identity

**Given** the learner opens a Practice Activity
**When** the activity is displayed
**Then** the presentation communicates a focused design-practice experience while preserving the existing editorial visual language.

### AC-020-02 — Stimulus Presentation

**Given** an activity has an appropriate existing visual stimulus
**When** the learner opens the activity
**Then** the stimulus is presented clearly, accessibly, and at a useful scale.

### AC-020-03 — Text-First Activities

**Given** an activity has no suitable visual stimulus
**When** the learner opens the activity
**Then** the activity remains clean, readable, and fully usable without fabricated imagery.

### AC-020-04 — Practice Hierarchy

**Given** the learner opens an activity
**When** the Practice screen renders
**Then** the stimulus, task/instruction, response area, and submission action are visually distinguishable and easy to follow.

### AC-020-05 — Response Space

**Given** the activity expects a text response
**When** the learner develops an answer
**Then** the response area provides comfortable space and remains accessible.

### AC-020-06 — Response Preservation

**Given** the learner has entered a response
**When** submission/evaluation fails
**Then** the learner's response is not unnecessarily discarded.

### AC-020-07 — Submission Continuity

**Given** the learner submits a response
**When** evaluation begins
**Then** the existing SPEC-017 submission acknowledgement and duplicate-submission protection remain intact.

### AC-020-08 — Evaluation Continuity

**Given** a response is successfully evaluated
**When** the evaluation completes
**Then** the existing feedback and reflection journey remains unchanged.

### AC-020-09 — Completion Continuity

**Given** the learner successfully completes reflection
**When** completion is recorded
**Then** SPEC-018 completion semantics remain unchanged.

### AC-020-10 — Responsive Practice

**Given** a mobile, tablet, or desktop viewport
**When** the Practice Activity is displayed
**Then** the experience remains readable and usable without horizontal scrolling.

### AC-020-11 — Accessibility

**Given** the Practice Activity contains visual and interactive content
**When** the learner uses keyboard navigation or assistive technology
**Then** focus, alternative-text/decorative treatment, controls, and submission states remain accessible.

### AC-020-12 — No New External Image Dependency

**Given** the learner opens a Practice Activity
**When** its visual stimulus is rendered
**Then** the implementation does not introduce a new live external image-provider dependency solely for this specification.

---

## 17. Architectural Constraints

- Preserve FastAPI.
- Preserve HTMX/server-rendered frontend.
- Preserve the existing CSS/design-token architecture.
- Reuse SPEC-015's existing visual stimulus/content mechanisms.
- Do not introduce a SPA framework.
- Do not introduce a new media service.
- Do not introduce a database migration solely for presentation.
- Do not add external runtime dependencies solely for visual presentation.
- Keep presentation-specific data in the application/view layer.
- Keep domain concepts independent of browser rendering and CSS concerns.

---

## 18. Future Progression

SPEC-020 intentionally stops at the foundation of a stronger visual practice experience.

Future specifications may separately introduce:

- richer visual stimulus sourcing;
- Pixabay or another approved image provider;
- visual response/upload workflows;
- drawing/photo practice;
- richer Content Packs;
- portfolio presentation;
- mentor/peer critique;
- broader Progress capabilities.

Each should be evaluated separately against learner validation evidence.

---

## 19. Definition of Done

SPEC-020 is complete when:

- [ ] Practice Activity has a stronger visual/design-practice presentation.
- [ ] Existing visual stimuli are presented clearly where appropriate.
- [ ] Activities without suitable imagery remain clean and valid.
- [ ] Stimulus, task, response, and submission have clear hierarchy.
- [ ] Text responses have a comfortable response area.
- [ ] Failed submission/evaluation preserves learner input where applicable.
- [ ] Existing submission/evaluation/feedback/reflection/completion behaviour remains unchanged.
- [ ] Mobile, tablet, and desktop layouts remain usable.
- [ ] Accessibility requirements are covered.
- [ ] Automated tests cover the new presentation behaviour.
- [ ] Full test suite passes.
- [ ] FastAPI + HTMX architecture is preserved.
- [ ] No new external runtime image dependency is introduced.
- [ ] Manual UX review approves representative activity screens.
- [ ] Architecture review approves the implementation.

---

## 20. References

- Project Charter
- UX-001 — Fablit Experience
- Architecture Blueprint
- SPEC-013 — Learner Experience & Visual Foundation
- SPEC-015 — Contextual Visual Stimulus & Response-Aware Evaluation
- SPEC-016 — First Learner Experience Refinement
- SPEC-017 — Submission & Evaluation Feedback
- SPEC-018 — Learner Practice Continuity & Progress Foundation
- SPEC-019 — Explore Surface & Visual Practice Refinement
