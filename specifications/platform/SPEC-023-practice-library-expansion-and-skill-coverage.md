# SPEC-023 — Practice Library Expansion & Skill Coverage

**Status:** Proposed
**Type:** Product / Learning Content
**Depends on:** SPEC-005, SPEC-010, SPEC-011, SPEC-015, SPEC-017, SPEC-018, SPEC-019, SPEC-020, SPEC-021, SPEC-022

---

## 1. Context

Fablit now has a complete learner practice journey, persistent practice history, a visual practice experience, and an explicit choice between Short Drill and Full Practice.

The strongest product signal from the current pilot feedback is not a need for another learner-facing feature. It is that the current practice library is still small.

The current demo content contains a deliberately small set of Assessment Activities. SPEC-022 also currently makes only a small subset available as Short Drills. This is sufficient to validate the application flow, but not sufficient to establish Fablit as a place where a learner can practise repeatedly with meaningful variety.

Fablit's project charter and existing learning-domain architecture position the product around deliberate practice, meaningful feedback, continuous reflection, transferable skills, and Assessment Activities as the concrete unit of learner interaction.

The next step is therefore to expand the practice library while making the intended learning capability of each activity explicit enough to identify coverage and gaps.

This specification is about **building the practice content foundation**, not introducing a new learner analytics, mastery, or recommendation system.

---

## 2. Objective

Establish a sufficiently varied first practice library so that Fablit can support repeated deliberate practice across the capabilities already implied by its learning model:

- **Observe** — notice and describe meaningful visual or contextual details.
- **Interpret** — move from noticing toward meaning, mood, relationships, inference, or visual language.
- **Ideate** — transform observations or interpretations into a creative/design possibility.
- **Articulate** — communicate the thinking behind an observation, interpretation, or idea.
- **Reflect** — examine the practice attempt and identify a useful next step.

These are a **content-design lens**, not a learner mastery model.

The implementation should make it possible to answer:

> **Do the activities available in Fablit provide enough variety for a learner to repeatedly practise seeing, thinking, generating, explaining, and reflecting?**

---

## 3. Current Baseline

The current seeded demo library contains five Assessment Activities:

1. **CAT Practice — 2D & 3D Composition Analysis**
   - Written response
   - Visual Analysis
   - Composition stimulus

2. **Creative Writing — Concept Explanations for Poster Designs**
   - Written response
   - Written Communication

3. **Memory Drawing Prep — Object & Proportion Detection**
   - Observation
   - Visual Analysis + Critical Observation
   - Detail stimulus

4. **Situation Test Prep — Material & Design Process Reflection**
   - Reflection
   - Critical Observation

5. **Color Theory — Mood & Atmosphere Interpretation**
   - Written response
   - Visual Analysis
   - Colour/mood stimulus

SPEC-022 currently makes two existing activities Short Drill eligible:

- Memory Drawing Prep — Object & Proportion Detection
- Creative Writing — Concept Explanations for Poster Designs

This small library should remain a useful baseline, but it should no longer be treated as sufficient for the next stage of the product.

---

## 4. Scope

### In Scope

- Expand the Assessment Activity library with curated, high-quality activities.
- Preserve the existing Assessment Activity domain model.
- Give each new activity a clear primary practice capability using the Observe / Interpret / Ideate / Articulate / Reflect lens.
- Identify secondary capabilities where an activity genuinely exercises more than one capability.
- Increase variety within both Short Drill and Full Practice.
- Include activities relevant to design-entrance preparation, especially visual thinking, creative reasoning, design articulation, and situation/design-oriented thinking.
- Keep prompts concrete and practice-oriented rather than generic academic exercises.
- Reuse the existing Submission → Evaluation → Feedback → Reflection → Completion journey.
- Provide meaningful deterministic evaluation/feedback for the new activities within the existing evaluation architecture.
- Use existing stimulus infrastructure where a visual stimulus is appropriate.
- Keep activity content configuration-driven rather than hard-coding activity-specific application behaviour.
- Update Short Drill eligibility through explicit content configuration as the library grows.
- Add automated tests covering the expanded content and mode eligibility.
- Document the resulting practice coverage and intentional gaps.

### Out of Scope

- Learner scoring, grades, percentages, ranks, or leaderboards.
- Skill mastery or proficiency tracking.
- Adaptive learning.
- Personalized recommendations.
- A recommendation or ranking engine.
- Learner accounts or authentication.
- Analytics dashboards.
- Streaks, badges, points, or gamification.
- A new frontend framework.
- A new Assessment Activity type solely to support the expanded content.
- A parallel practice workflow.
- A curriculum engine or prescribed learning sequence.
- Replacing sketching as the learner's primary preparation activity.
- Large-scale content infrastructure or a CMS.
- External AI generation.
- Requiring external image services for every activity.

---

## 5. Practice Coverage Model

The five capabilities provide a lightweight editorial lens for designing and reviewing activities.

### Observe

The learner notices what is actually present.

Examples of possible activity directions:

- visual detail detection;
- proportion and spatial relationships;
- material/surface observation;
- composition;
- human or environmental details;
- unusual or overlooked visual information.

### Interpret

The learner asks what the observed information might mean.

Examples:

- mood;
- atmosphere;
- visual relationships;
- context;
- function;
- symbolism;
- alternative readings of an image or object.

### Ideate

The learner transforms observation or interpretation into a possibility.

Examples:

- design responses;
- visual concepts;
- object transformations;
- alternative uses;
- poster/concept directions;
- situation-test style ideas.

### Articulate

The learner explains their thinking.

Examples:

- explaining a design decision;
- describing why an idea works;
- communicating a concept clearly;
- connecting visual evidence to an interpretation;
- presenting a creative idea in concise language.

### Reflect

The learner looks back at the attempt.

Examples:

- identifying what was difficult;
- noticing what was overlooked;
- identifying a different approach for another attempt;
- connecting the exercise to sketching or another design activity.

An activity may exercise several capabilities, but each activity should have one **primary** capability so that the library can be reviewed for balance.

---

## 6. Content Design Requirements

Each Assessment Activity added under this specification should define, at minimum:

- learner-facing title;
- concise description;
- activity type;
- prompt/instructions;
- primary practice capability;
- optional secondary capabilities;
- associated existing Skill identities where appropriate;
- evaluation findings;
- improvement guidance;
- actionable next step;
- stimulus context where required;
- deterministic fallback stimulus where appropriate;
- whether it is eligible for Short Drill.

The content should remain understandable without requiring the learner to know the internal capability taxonomy.

The Observe / Interpret / Ideate / Articulate / Reflect labels are primarily for content design and internal review.

---

## 7. Exam-Relevance Direction

The library should move toward activities that feel recognisably useful to a design-entrance aspirant without attempting to reproduce a complete examination paper.

Priority should be given to activities that exercise:

- observation of visual details;
- composition and spatial reasoning;
- colour and mood;
- material and texture awareness;
- visual interpretation;
- transformation of an observed object or situation;
- creative ideation;
- concise design explanation;
- situation-test style thinking;
- reflection on the creative process.

The prompts should encourage the learner to **look, think, make connections, and explain**, rather than simply recall facts.

Existing exam-oriented activity labels may continue to be used where appropriate, while the underlying Skill and Assessment Activity domain remains exam-neutral.

---

## 8. Short Drill Content Strategy

Short Drill should grow from a small curated subset of the broader library.

A Short Drill candidate should generally:

- have a focused prompt;
- have a concise response expectation;
- be meaningful in approximately 5–10 minutes of learner effort;
- work naturally between longer sketching or practice sessions;
- preserve the existing Evaluation → Feedback → Reflection loop;
- not require a countdown or enforced duration.

Short Drill should include variety across the practice capabilities.

The implementation should continue to use explicit eligibility configuration, as established by SPEC-022.

Do not introduce automatic Short Drill selection based on learner history.

---

## 9. Full Practice Content Strategy

Full Practice should provide the deeper end of the library.

Activities may require:

- richer observation;
- multi-step interpretation;
- a more developed creative idea;
- explanation of design reasoning;
- more substantial reflection.

Full Practice remains the existing standard learner journey.

The expanded library must not create a second implementation of that journey.

---

## 10. Content Variety

Expansion should avoid producing many superficial variations of the same prompt.

Activities should vary across dimensions such as:

| Dimension | Examples |
|---|---|
| Stimulus | photograph, object/detail, colour, situation, text/context |
| Thinking | observe, compare, interpret, transform, generate, explain |
| Response | short text, analysis, concept explanation, reflective response |
| Context | visual composition, everyday object, fashion/design, environment, situation |
| Effort | Short Drill, Full Practice |
| Capability | Observe, Interpret, Ideate, Articulate, Reflect |

The goal is **meaningful variety**, not simply a larger activity count.

---

## 11. Suggested Initial Expansion

The implementation should add enough activities to make repeated practice plausible while keeping content quality review manageable.

A useful initial target is **at least 10–12 total activities**, including the existing five, with intentional coverage across all five capabilities.

This is a content target, not a product metric or learner goal.

The exact final activity count may be adjusted during implementation if content quality would be compromised by filling an arbitrary quota.

The implementation should explicitly document:

- current activities;
- newly added activities;
- primary capability for each;
- secondary capability where applicable;
- Short Drill eligibility;
- remaining coverage gaps.

---

## 12. Evaluation and Feedback

Every new activity must continue to use the existing evaluation architecture.

Evaluation should identify something concrete about the learner's response rather than merely determine correctness.

Feedback should remain:

- meaningful;
- specific;
- actionable;
- connected to the learner's response;
- consistent with the existing Fablit feedback philosophy.

Each activity should provide:

1. a plausible strength/finding;
2. an improvement opportunity;
3. a useful next step.

Do not introduce numerical scores simply because the library is expanding.

---

## 13. Stimulus Requirements

Where an activity requires a visual stimulus:

- use the existing stimulus abstraction;
- provide appropriate contextual metadata;
- preserve response-aware evaluation semantics;
- provide a deterministic bundled fallback where required by the existing architecture;
- avoid making the activity dependent on an unavailable external service.

A new external stimulus provider is not part of this specification.

---

## 14. Application Architecture

The expanded content should remain within the existing architecture:

```
Content configuration
       ↓
Assessment Activity
       ↓
Existing practice application
       ↓
Submission
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

No new domain abstraction is required merely because the library grows.

The Observe / Interpret / Ideate / Articulate / Reflect taxonomy should not become a learner-facing hierarchy or a new Skill hierarchy unless a future specification establishes that need.

---

## 15. Practice History Compatibility

All new activities must remain compatible with SPEC-021.

A completed activity should produce the same durable practice-history information as existing activities:

- activity identity;
- stimulus/context where applicable;
- learner response;
- evaluation;
- feedback;
- reflection;
- completion timestamp.

Repeated attempts remain valid.

The expanded content must not introduce:

- mastery calculations;
- completion percentages;
- activity rankings;
- progress scores;
- recommendation signals.

---

## 16. UX Requirements

The existing Fablit experience remains the foundation:

- calm;
- editorial;
- spacious;
- warm-neutral;
- restrained;
- learner-led.

Activity expansion should not result in a crowded dashboard.

The activity library should remain understandable as it grows.

If the number of activities makes the existing presentation difficult to scan, use simple information hierarchy or grouping that helps the learner understand the choices. Do not introduce a large dashboard, complex filters, or a personalization system merely to accommodate the expanded content.

The learner should still be able to choose an activity based on what looks interesting or useful in the moment.

---

## 17. Accessibility

New activities must preserve the existing accessibility expectations:

- semantic controls;
- clear labels;
- visible keyboard focus;
- sufficient contrast;
- no colour-only meaning;
- responsive layouts;
- assistive-technology compatibility;
- reduced-motion compatibility.

Visual stimuli must have meaningful alternative text where appropriate.

---

## 18. Acceptance Criteria

### AC-023-01 — Expanded Library

**Given** the current five-activity baseline
**When** SPEC-023 is implemented
**Then** the library contains a meaningfully expanded set of curated Assessment Activities, with an initial target of at least 10–12 total activities unless content-quality review justifies a smaller set.

### AC-023-02 — Capability Coverage

**Given** the expanded activity library
**When** activities are reviewed using the internal practice-capability lens
**Then** all five capabilities are represented:

- Observe
- Interpret
- Ideate
- Articulate
- Reflect

### AC-023-03 — Primary Capability

**Given** every activity in the expanded library
**When** the content inventory is reviewed
**Then** each activity has one documented primary capability.

### AC-023-04 — Meaningful Variety

**Given** the expanded library
**When** activities are compared
**Then** the library contains meaningful variation in stimulus, thinking task, response style, context, and practice effort rather than superficial prompt duplication.

### AC-023-05 — Exam-Relevant Practice

**Given** a design-entrance aspirant uses the activity library
**When** they inspect the available activities
**Then** the activities provide recognisable practice in visual thinking, creative reasoning, design articulation, observation, interpretation, ideation, or related design-entrance capabilities.

### AC-023-06 — Short Drill Variety

**Given** the Short Drill mode
**When** eligible activities are reviewed
**Then** the curated set contains more than the original two activities and provides meaningful capability variety.

### AC-023-07 — Full Practice Preservation

**Given** a learner chooses Full Practice or uses the normal activity library
**When** they start an activity
**Then** the existing practice journey remains unchanged in learning semantics.

### AC-023-08 — Existing Journey Preservation

**Given** any new activity
**When** the learner completes it
**Then** the flow remains:

```
Submission → Evaluation → Feedback → Reflection → Completion
```

### AC-023-09 — Evaluation and Feedback

**Given** a learner submits a response to a new activity
**When** evaluation completes
**Then** the learner receives a concrete finding, improvement guidance, and an actionable next step using the existing evaluation/feedback architecture.

### AC-023-10 — History Compatibility

**Given** a learner completes a new activity
**When** practice history is reviewed
**Then** the attempt is persisted and reviewable through the existing SPEC-021 capability.

### AC-023-11 — Content Configuration

**Given** a new activity is added
**When** its content definition is registered
**Then** the application does not require a new activity-specific workflow or special-case learner journey.

### AC-023-12 — No Personalization

**Given** the expanded activity library
**When** activities are presented
**Then** the application does not recommend, rank, or automatically select activities based on learner history.

### AC-023-13 — No Gamification

**Given** the expanded library
**When** the learner completes activities
**Then** no score, streak, badge, point, rank, or mastery state is introduced.

### AC-023-14 — Accessibility

**Given** a learner uses keyboard navigation or assistive technology
**When** they browse and enter the expanded activity library
**Then** activity selection, prompts, stimuli, responses, and feedback remain accessible.

### AC-023-15 — Regression Safety

**Given** the existing Fablit test suite
**When** SPEC-023 is implemented
**Then** existing tests continue to pass and new content coverage tests pass.

---

## 19. Testing Requirements

### Content Tests

Verify:

- every activity has required content fields;
- every activity references valid Skill identities;
- every activity has a primary practice capability;
- Short Drill eligibility resolves only to valid activities;
- stimulus-dependent activities have valid stimulus configuration;
- evaluation/feedback definitions are present.

### Application Tests

Verify:

- the expanded activity library is exposed;
- existing activities remain accessible;
- new activities enter the existing learner journey;
- Short Drill eligibility includes the intended curated activities;
- no history-based recommendation logic is introduced.

### Learner Journey Regression

For representative new activities, verify:

```
Activity
  ↓
Submission
  ↓
Evaluation
  ↓
Feedback
  ↓
Reflection
  ↓
Completion
  ↓
History
```

### Manual Content Review

Review every new activity for:

1. prompt clarity;
2. design-entrance relevance;
3. meaningful thinking demand;
4. capability assignment;
5. response expectation;
6. evaluation quality;
7. feedback usefulness;
8. reflection quality;
9. Short Drill suitability where applicable;
10. stimulus quality and accessibility.

---

## 20. Definition of Done

SPEC-023 is complete when:

- [ ] The practice library has been meaningfully expanded from the current five-activity baseline.
- [ ] The initial target of 10–12 total activities is reached, or a documented content-quality decision justifies a smaller set.
- [ ] All five practice capabilities are represented.
- [ ] Every activity has a documented primary capability.
- [ ] Activities provide meaningful variety rather than superficial duplication.
- [ ] New activities are relevant to design-entrance preparation.
- [ ] Short Drill eligibility has been expanded through explicit configuration.
- [ ] Full Practice remains available through the existing activity library.
- [ ] Existing Submission → Evaluation → Feedback → Reflection → Completion semantics are preserved.
- [ ] New activities work with SPEC-021 practice history.
- [ ] New content uses the existing stimulus/evaluation architecture.
- [ ] No scoring, mastery, recommendation, analytics, or gamification is introduced.
- [ ] Automated tests pass.
- [ ] Manual content and UX review is complete.
- [ ] FastAPI + HTMX architecture is preserved.
- [ ] Remaining content-coverage gaps are documented for the next iteration.

---

## 21. Future Progression

This specification deliberately establishes the **content foundation**, not a larger learning-management system.

After implementation, the next decision should be based on the actual expanded library and observed learner behaviour.

Potential future work may include:

- additional activity families;
- richer activity metadata;
- more visual observation drills;
- sketch-adjacent warm-ups;
- learner-defined practice preferences;
- authenticated learner continuity;
- evidence-based recommendations, if later validated.

These should not be assumed necessary before the expanded practice library has been exercised.

---

## 22. References

- Project Charter
- Architecture Blueprint
- SPEC-005 — Assessment Activity Domain Foundation
- SPEC-010 — Skill Domain Foundation
- SPEC-011 — Skill–Assessment Activity Association
- SPEC-015 — Contextual Visual Stimulus & Response-Aware Evaluation
- SPEC-017 — Submission & Evaluation Feedback
- SPEC-018 — Learner Practice Continuity & Progress Foundation
- SPEC-019 — Explore Surface & Visual Practice Refinement
- SPEC-020 — Visual Practice Experience Foundation
- SPEC-021 — Persistent Practice History & Learner Review
- SPEC-022 — Optional Practice Modes & Learner Choice
