# SPEC-019 — Explore Surface & Visual Practice Refinement

**Status:** Proposed
**Version:** 0.1
**Type:** Platform / Learner Experience
**Depends on:** SPEC-016, SPEC-015, SPEC-018
**Primary Module:** Learner Experience / Practice Discovery

---

## 1. Problem Statement

The current deployed Fablit experience has a calm, editorial visual language and a deliberately simple practice journey. The Explore screen is clean and readable, but its activity cards are predominantly text-based and leave substantial unused space on larger screens.

This creates a mismatch with an important part of Fablit's intended audience: learners preparing for visual and design-oriented entrance examinations. The application should feel like a place for design practice without becoming visually cluttered or turning into a generic gamified study dashboard.

Fablit already has a visual stimulus foundation through SPEC-015. SPEC-019 therefore does **not** introduce a new stimulus architecture. It refines how the existing practice catalogue communicates visually and how image-dependent activities are presented at the point of discovery.

The goal is:

> **Make Fablit feel more like a minimal design-practice studio while preserving the calmness and simplicity of the existing learner experience.**

---

## 2. Objectives

SPEC-019 shall:

1. Strengthen the visual identity of the Explore/practice-discovery experience without replacing the existing editorial design direction.
2. Give image-dependent activities a meaningful visual cue on the Explore screen.
3. Improve use of available horizontal space on desktop while preserving a clear mobile layout.
4. Preserve the existing learner journey and all current learning behaviour.
5. Keep visual treatment purposeful rather than decorative or gamified.
6. Reuse the existing stimulus/content mechanisms rather than introducing a second media architecture.

---

## 3. Scope

### In Scope

- Refinement of the Explore activity-card presentation.
- Visual previews/cues for activities that already have an appropriate bundled or configured visual asset.
- Improved desktop card-grid composition and whitespace usage.
- Responsive card behaviour for mobile and tablet layouts.
- Clear hierarchy between activity title, description, skill, continuity state, and action.
- Preservation of the current editorial typography and warm neutral visual foundation.
- Small, purposeful hover/focus treatments using the existing design-token system.
- Accessibility treatment for any newly introduced visual content.
- Automated web/UI tests for the resulting learner-facing structure.
- Manual visual verification against desktop and mobile layouts.

### Out of Scope

- New Stimulus domain or application architecture.
- New external image provider integration.
- Pixabay API integration.
- Live/random image retrieval on the Explore screen.
- Camera or scanner functionality.
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
- Changes to evaluation, feedback, reflection, or completion behaviour.
- A new frontend framework or SPA architecture.

---

## 4. Design Direction

The current visual direction established by SPEC-013 and refined by SPEC-016 should remain the foundation:

- calm;
- personal;
- spacious;
- editorial;
- warm neutral background;
- restrained accent colour;
- serif display typography with a clear sans-serif body hierarchy;
- subtle rather than elaborate interaction.

SPEC-019 should **evolve this direction, not replace it**.

Do not introduce a collection of selectable visual themes such as Bauhaus, Y2K, monochrome, or neo-brutalism as part of this specification.

The interface should communicate visual creativity through the content and composition of the experience rather than through excessive decoration.

---

## 5. Explore Card Experience

The Explore screen remains the primary practice-discovery surface.

Each activity card should clearly communicate:

```text
Visual cue (when applicable)
        ↓
Activity title
        ↓
Short invitation/description
        ↓
Skill/context
        ↓
Continuity state + Explore action
```

The card should remain scannable. A visual preview must not make the learner hunt for the activity title or action.

### 5.1 Image-dependent activities

Activities that already define or resolve a visual stimulus may expose a representative visual preview on the Explore screen.

The preview is a **discovery cue**, not necessarily the stimulus instance that will be presented when the learner starts a new practice journey.

This distinction is important:

```text
Explore preview
    ≠
Learner activity-instance stimulus
```

Starting the activity must continue to use the existing SPEC-015 stimulus lifecycle.

### 5.2 Activities without visual stimuli

Activities that do not have an appropriate visual asset should remain text-first.

Do not add decorative images merely to make every card look identical.

Consistency should come from layout and visual hierarchy, not forced imagery.

---

## 6. Visual Asset Source

SPEC-019 should reuse assets already available through the current application/content mechanisms wherever practical.

The first implementation should prefer:

1. existing bundled Fablit visual assets;
2. existing configured assets;
3. other already-supported local/content mechanisms.

It must not introduce a live external image request solely to render the Explore screen.

External image-provider integration, including Pixabay, remains a future capability and should be specified separately if needed.

---

## 7. Desktop Layout

The current Explore screen should use the available desktop width more effectively while retaining a comfortable reading measure.

The implementation may increase the number or width of activity cards at desktop breakpoints where this improves composition.

It should avoid:

- excessively wide text blocks;
- tiny cards created solely to fill space;
- dense dashboard-style grids;
- unnecessary statistics or widgets.

The desired result is a visually balanced practice library rather than a dashboard full of metrics.

---

## 8. Responsive Layout

The Explore experience shall remain usable across:

- mobile;
- tablet;
- desktop.

At smaller widths:

- cards may become single-column;
- visual previews should retain useful proportions;
- titles must remain readable;
- actions must remain easy to tap;
- no horizontal scrolling should be required.

The implementation should use the existing CSS architecture and design tokens.

---

## 9. Continuity State

The existing SPEC-018 `Practised` indication should remain available where applicable.

Visual refinement must not turn `Practised` into a score, progress measure, or achievement system.

The intended hierarchy remains:

```text
Activity identity
      ↓
Invitation to practise
      ↓
Quiet continuity cue
```

The continuity cue should remain visually subordinate to the activity itself.

---

## 10. Interaction

Interactions should remain subtle and purposeful.

Existing hover/focus behaviour may be refined to make cards feel responsive.

Permitted examples include:

- small elevation on hover;
- restrained image treatment on hover;
- clear keyboard focus;
- immediate visual affordance for the Explore action.

Do not introduce animated counters, streak animations, loading theatrics, or other gamification as part of SPEC-019.

Respect `prefers-reduced-motion` using the existing accessibility approach.

---

## 11. Accessibility

Any visual preview introduced by this specification must:

- have appropriate alternative text where the image conveys meaningful information;
- avoid redundant alternative text when the nearby text already communicates the same information;
- preserve keyboard accessibility;
- preserve visible focus states;
- maintain sufficient text/background contrast;
- avoid making colour the sole indicator of state.

If a preview is purely decorative, it should be exposed to assistive technology as decorative rather than creating unnecessary reading content.

---

## 12. Existing Learner Journey Preservation

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

SPEC-019 changes the **presentation of practice discovery**, not the learning model.

---

## 13. Domain and Application Constraints

SPEC-019 must not redesign the existing domain model.

In particular:

- Do not modify Skill semantics.
- Do not modify Assessment Activity semantics solely for presentation.
- Do not modify Submission behaviour.
- Do not modify Evaluation behaviour.
- Do not modify Feedback behaviour.
- Do not modify Reflection behaviour.
- Do not modify PracticeCompletion semantics.
- Do not make Explore cards responsible for resolving learner activity-instance stimuli.

Where a new view-model field is required for presentation, it should remain an application/view concern rather than leaking UI concepts into the domain.

---

## 14. Testing Requirements

### Unit/Application Tests

Where applicable:

- activity summaries expose the data required by the Explore presentation;
- activities with visual previews identify the appropriate preview asset;
- activities without visual assets remain valid;
- existing continuity state remains unchanged.

### Web Tests

Verify that:

- the Explore page renders the expected activity titles;
- visual preview markup appears for activities configured to have one;
- preview alternative-text behaviour is correct;
- activities without previews do not receive fabricated imagery;
- `Practised` remains visible for completed activities;
- Explore links remain correct;
- no evaluation/reflection/completion behaviour changes.

### Regression Tests

The existing learner journey tests must continue to pass.

### Manual UX Verification

Verify at minimum:

1. Desktop Explore screen.
2. Tablet-sized viewport.
3. Mobile viewport.
4. Keyboard navigation and visible focus.
5. Activity with a visual preview.
6. Activity without a visual preview.
7. Previously practised activity.
8. Long activity title.
9. Reduced-motion preference where practical.

The reviewer should specifically ask:

> **Does this feel more like a place for design practice without feeling busier?**

---

## 15. Acceptance Criteria

### AC-019-01 — Visual Practice Identity

**Given** the learner opens Explore
**When** the activity catalogue is displayed
**Then** the presentation communicates a stronger visual/design-practice identity while preserving the existing editorial visual language.

### AC-019-02 — Visual Preview

**Given** an activity already has an appropriate visual asset
**When** the activity appears on Explore
**Then** the learner can see a meaningful visual preview/cue associated with that activity.

### AC-019-03 — No Forced Imagery

**Given** an activity has no appropriate visual asset
**When** it appears on Explore
**Then** the card remains valid without fabricated or purely decorative imagery being introduced solely for consistency.

### AC-019-04 — Preview vs Stimulus Separation

**Given** an activity has an Explore preview
**When** the learner starts the activity
**Then** the existing SPEC-015 stimulus lifecycle remains authoritative for the learner activity instance.

### AC-019-05 — Desktop Composition

**Given** a desktop viewport with sufficient horizontal space
**When** Explore is displayed
**Then** the activity cards use the available space more effectively without becoming cramped or excessively wide.

### AC-019-06 — Responsive Behaviour

**Given** a mobile or tablet viewport
**When** Explore is displayed
**Then** cards remain readable, usable, and free of horizontal scrolling.

### AC-019-07 — Continuity Preservation

**Given** an activity has previously been completed
**When** Explore is displayed
**Then** the existing quiet `Practised` continuity cue remains available without introducing scores or progress measures.

### AC-019-08 — Accessibility

**Given** an activity card contains a visual preview
**When** the page is used with keyboard navigation or assistive technology
**Then** focus, alternative text/decorative treatment, and interaction remain accessible.

### AC-019-09 — Existing Journey Unchanged

**Given** a learner selects any activity
**When** the learner completes the existing practice journey
**Then** submission, evaluation, feedback, reflection, and completion behaviour remain unchanged.

### AC-019-10 — No External Runtime Image Dependency

**Given** the learner opens Explore
**When** activity cards are rendered
**Then** the Explore screen does not require a new live external image-provider request solely to display card previews.

---

## 16. Architectural Constraints

- Preserve FastAPI.
- Preserve HTMX/server-rendered frontend.
- Preserve the existing CSS/design-token architecture.
- Reuse existing visual stimulus/content mechanisms.
- Do not introduce a SPA framework.
- Do not introduce a new media service.
- Do not introduce a database migration solely for Explore presentation.
- Do not add external runtime dependencies solely for card previews.
- Keep presentation-specific data in the application/view layer.
- Keep the domain independent of browser rendering and CSS concerns.

---

## 17. Future Progression

SPEC-019 intentionally stops at practice-discovery and presentation refinement.

Future specifications may introduce:

- richer visual stimulus sourcing;
- Pixabay or another approved image provider;
- visual submission/upload;
- drawing/photo workflows;
- richer Content Packs;
- portfolio presentation;
- mentor/peer critique;
- broader Progress capabilities.

Each should be evaluated separately against learner validation evidence.

---

## 18. Definition of Done

SPEC-019 is complete when:

- [ ] Explore has a stronger visual/design-practice presentation.
- [ ] Appropriate existing visual assets can appear as activity previews where useful.
- [ ] Activities without appropriate imagery remain clean and valid.
- [ ] Desktop whitespace/composition is improved without creating a dense dashboard.
- [ ] Mobile and tablet layouts remain usable.
- [ ] Existing editorial typography and warm neutral visual foundation are preserved.
- [ ] `Practised` continuity remains quiet and non-measurable.
- [ ] Accessibility requirements are covered.
- [ ] Automated tests cover the new presentation behaviour.
- [ ] Full test suite passes.
- [ ] FastAPI + HTMX architecture is preserved.
- [ ] No new external runtime image dependency is introduced.
- [ ] Manual visual review approves desktop and mobile presentation.
- [ ] Architecture review approves the implementation.

---

## 19. References

- Project Charter
- UX-001 — Fablit Experience
- Architecture Blueprint
- SPEC-013 — Learner Experience & Visual Foundation
- SPEC-015 — Contextual Visual Stimulus & Response-Aware Evaluation
- SPEC-016 — First Learner Experience Refinement
- SPEC-017 — Submission & Evaluation Feedback
- SPEC-018 — Learner Practice Continuity & Progress Foundation
