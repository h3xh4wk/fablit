# SPEC-025 — Curated Practice Continuity

**Status:** Proposed
**Area:** Practice / Learner Journey
**Depends on:** SPEC-018 — Learner Practice Continuity & Progress Foundation, SPEC-021 — Persistent Practice History & Learner Review, SPEC-022 — Optional Practice Modes & Learner Choice, SPEC-023 — Practice Library Expansion & Skill Coverage, SPEC-024 — Learner Identity & Private Practice History

## 1. Objective

Make the transition after completing a practice activity educationally meaningful by offering a deliberately curated next practice.

The learner should be able to see that one kind of design thinking can lead naturally into another:

**Observe → Interpret → Ideate → Articulate → Reflect → practise again**

The first version is authored content continuity, not personalization or an adaptive recommendation system.

## 2. Product principle

A next practice should answer:

> “What is a useful next piece of deliberate practice after this activity?”

It should not answer:

> “What does the system think this particular learner should do?”

The relationship between activities is explicitly defined by Fablit’s content/design layer.

## 3. Scope

### 3.1 Completion surface

After successful completion/reflection, the learner may see a quiet continuation section such as:

**Continue the practice**

> You just observed an object closely. Now try turning that observation into a design idea.

The continuation should identify the relationship between the completed activity and the proposed next activity where useful.

### 3.2 Curated relationships

Introduce an explicit content-level relationship between activities.

For the initial implementation:

- one completed activity may point to one curated next activity;
- relationships are authored deliberately;
- the relationship must refer to an existing Assessment Activity;
- the relationship must not depend on learner history, scores, completion count, or inferred behaviour.

The implementation should allow additional relationships to be added through content configuration without changing the practice workflow.

### 3.3 Learner choice

The learner can:

- start the curated next practice;
- return to Explore;
- leave the continuation without taking action.

The continuation must not become a forced next step.

### 3.4 Existing journey preservation

Starting a curated next activity uses the existing practice journey:

**Submission → Evaluation → Feedback → Reflection → Completion**

Practice history remains governed by SPEC-021 and learner ownership remains governed by SPEC-024.

Repeated practice remains available.

## 4. Initial curated transitions

Use the existing 12-activity library as the first content set.

Initial relationships should demonstrate meaningful movement between capabilities rather than merely similar prompts. Candidate relationships include:

- **Observation Drill — Everyday Object Study** → **Design Ideation — Transform the Object**
- **Memory Drawing Prep — Object & Proportion Detection** → **Short Ideation Sprint — Alternative Uses**
- **CAT Practice — 2D & 3D Composition Analysis** → **Visual Interpretation — Reading a Street Scene**
- **Color Theory — Mood & Atmosphere Interpretation** → **Design Articulation — Explain a Poster Concept**
- **Short Ideation Sprint — Alternative Uses** → **Design Articulation — Explain a Poster Concept**
- **Design Ideation — Transform the Object** → **Design Articulation — Explain a Poster Concept**
- **Reflection Prompt — What Did Practice Ask of You?** → a suitable next activity that returns the learner to active practice.

The implementation should validate the final chosen relationships against the actual activity content and avoid presenting a transition merely because two activities share a skill label.

## 5. Non-goals

This specification does **not** introduce:

- personalized recommendations;
- recommendation algorithms;
- adaptive learning;
- learner profiling;
- mastery or progress scoring;
- streaks, badges, points, leaderboards, or gamification;
- forced practice schedules;
- timers;
- additional learner preference/account systems;
- analytics dashboards;
- changes to authentication or cross-device identity;
- a new practice workflow;
- a new activity type.

## 6. UX requirements

The continuation should feel like part of the learning journey, not an advertisement or gamified prompt.

Requirements:

- calm and editorial presentation;
- clear relationship to the completed activity;
- no claims that the next activity is “best” or “recommended for you”;
- no pressure language;
- existing Explore and History navigation remain available;
- responsive behaviour must preserve the existing visual practice experience.

Possible language:

**Continue the practice**

*You just explored how an object is used. Now try imagining what else it could become.*

**Try the next practice →**

The exact copy should remain content-driven and may vary by transition.

## 7. Architecture guidance

Prefer a small explicit content configuration over a recommendation service.

A transition should conceptually contain:

- source activity identifier;
- target activity identifier;
- optional learner-facing transition copy.

Keep this separate from:

- learner history;
- completion records;
- evaluation;
- learner identity;
- scoring or recommendation logic.

Do not introduce a generalized graph engine unless the existing codebase makes a smaller representation impractical.

## 8. Acceptance criteria

1. Completing an activity can expose its authored next-practice transition.
2. The transition is deterministic for the same source activity and content configuration.
3. The target activity exists in the current Assessment Activity library.
4. The continuation does not depend on learner identity, history, score, or behaviour.
5. Selecting the continuation opens the existing practice journey for the target activity.
6. The target practice is persisted under the current learner identity through the existing SPEC-021/SPEC-024 boundaries.
7. The learner can ignore the continuation and continue using existing navigation.
8. No recommendation, mastery, scoring, gamification, or personalization logic is introduced.
9. Existing practice, completion, history, and review tests continue to pass.
10. Tests cover at least one authored transition and verify that a second learner receives the same content transition without sharing any history or state.

## 9. Validation

Before expanding the transition library, manually inspect whether the proposed relationship feels educationally meaningful without relying on the label “recommended.”

The primary product question is:

> Does making the connection between two practices visible encourage a natural continuation of deliberate practice?

If not, improve the content relationship/copy before introducing more sophisticated recommendation behaviour.

## 10. Design principle

**Connect practices, not learners.**

The first version should teach the learner how practices relate to one another while keeping the learner in control of what to practise next.
