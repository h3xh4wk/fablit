# SPEC-016 — First Learner Experience Refinement

**Status:** Proposed  
**Type:** Product / UX Implementation  
**Depends on:** SPEC-012, SPEC-013, SPEC-014, SPEC-015  
**UX References:** UX-001, UX-002

---

## 1. Purpose

SPEC-016 is the first implementation of the learner experience direction established by UX-001 and UX-002.

The goal is not to redesign the entire Fablit application.

The goal is to take **one complete learner activity** and transform it from a functional interface into an experience that feels:

- curious;
- warm;
- approachable;
- visually intentional;
- lightly playful;
- personal;
- satisfying to complete.

The implementation should preserve the existing application architecture and learning flow established by previous specifications.

---

## 2. Product Principle

Fablit should feel less like opening a course and more like opening a notebook.

The learner should feel:

> "Something interesting caught my attention. Let me explore it."

rather than:

> "I have been given an assignment."

The interface should provide structure without making the learner feel that they are following a rigid academic structure.

---

## 3. Source of Truth

The following documents define the UX direction for this specification:

- `documents/UX-001-fablit-learner-experience-direction.md`
- `documents/UX-002-fablit-visual-language-interaction-guidelines.md`

These documents should be treated as the source of truth for:

- visual personality;
- learner emotional journey;
- visual hierarchy;
- use of icons and emoji;
- interaction language;
- accessibility expectations;
- anti-gamification principles.

Where this specification is intentionally less specific, the UX documents should guide implementation decisions.

---

# 4. Scope

## 4.1 In scope

SPEC-016 covers the visual and interaction refinement of:

1. the learner dashboard entry point;
2. one activity card;
3. one complete activity screen;
4. stimulus presentation;
5. observation prompt;
6. learner response area;
7. response submission;
8. personalized Finding/feedback presentation;
9. activity completion state;
10. responsive behaviour;
11. accessibility preservation.

---

## 4.2 Out of scope

This specification does not introduce:

- a new frontend framework;
- a new backend architecture;
- new domain models;
- new persistence requirements;
- a new evaluation architecture;
- a new stimulus provider;
- new learner analytics;
- gamification;
- points;
- badges;
- leaderboards;
- streaks;
- progress pressure;
- a complete dashboard redesign;
- a complete design-system implementation.

Existing functionality should be reused wherever possible.

---

# 5. Learner Journey

The refined activity should represent the following complete journey:

```text
Dashboard
   ↓
Activity invitation
   ↓
Stimulus
   ↓
Observation
   ↓
Learner response
   ↓
Personalized Finding
   ↓
Feedback / insight
   ↓
Completion
   ↓
Return to exploration
````

The learner should always understand what to do next without needing additional explanation.

---

# 6. Dashboard Entry Point

The existing dashboard should remain intentionally small.

The implementation should visually refine the presentation of the selected activity rather than introduce a new navigation hierarchy.

The learner should see approximately:

```text
Greeting
    ↓
Short invitation
    ↓
3–5 activity choices
```

The selected activity should be represented by a visually distinct card.

---

## 6.1 Activity Card

The activity card should communicate:

* what the activity is;
* why it may be interesting;
* approximate effort/time;
* that it can be explored voluntarily.

A conceptual example:

```text
┌───────────────────────────────┐
│ 👀 Look a little closer       │
│                               │
│ Explore visual balance        │
│                               │
│ ~ 5 min                  →    │
└───────────────────────────────┘
```

The exact visual implementation may differ.

The important requirement is clear hierarchy and invitation.

---

# 7. Activity Screen

The activity screen should be visually organized around the stimulus and the learner's observation.

The primary hierarchy should be:

```text
Invitation
     ↓
Stimulus
     ↓
Observation prompt
     ↓
Response
```

The interface should not resemble a conventional examination form.

---

# 8. Activity Invitation

The activity should begin with a short, conversational invitation.

Preferred style:

> 👀 Look a little closer

followed by:

> Take a moment. What catches your attention?

Avoid unnecessarily formal language such as:

> Activity: Visual Analysis

or:

> Analyse the following image and submit your answer.

The exact copy may be adapted to the activity.

---

# 9. Stimulus Presentation

The stimulus should be a prominent visual element.

The learner should immediately understand that the image is the object of observation.

Conceptual structure:

```text
        👀 Look a little closer

        ┌─────────────────────┐
        │                     │
        │                     │
        │       IMAGE         │
        │                     │
        │                     │
        └─────────────────────┘

        What do you notice?
```

---

## 9.1 Stimulus Requirements

The implementation should:

* preserve the existing SPEC-015 stimulus mechanism;
* display the resolved stimulus prominently;
* preserve attribution/source information where applicable;
* preserve meaningful alternative text;
* prevent image overflow;
* remain responsive;
* avoid unnecessary visual clutter around the image.

No new stimulus architecture should be introduced.

---

# 10. Observation Prompt

The prompt should encourage observation rather than demand a correct answer.

Examples of appropriate direction:

> What do you notice?

> What catches your attention?

> What stands out to you?

The exact wording should be appropriate to the activity.

The prompt should not imply that there is necessarily one correct answer.

---

# 11. Response Area

The response area should feel like a notebook rather than an examination form.

Preferred conceptual treatment:

```text
💭 What's your reading of it?

┌───────────────────────────────┐
│ There isn't a right answer.   │
│ Tell us what you notice...    │
│                               │
│                               │
└───────────────────────────────┘
```

The implementation should provide enough visual space for the learner to comfortably express an observation.

---

## 11.1 Response Guidance

Where appropriate, the interface may communicate:

> There isn't a right answer. Tell us what you notice...

This should reduce assessment anxiety.

The guidance should remain concise.

---

# 12. Primary Action

The primary action should feel like continuing a conversation rather than submitting an examination.

Possible wording includes:

> I'm ready →

or:

> Share my thought →

The exact wording may be selected during implementation based on the activity.

The action must remain visually obvious.

---

# 13. Submission Behaviour

Submission should preserve the existing evaluation flow from SPEC-015.

The implementation must not introduce a new evaluation mechanism.

After submission:

```text
Learner response
       ↓
Existing evaluator
       ↓
Finding
       ↓
Feedback
```

The learner should receive clear visual feedback that their response has been processed.

---

# 14. Personalized Finding

The Finding produced by the existing evaluation mechanism should receive a visually distinct presentation.

Preferred conceptual structure:

```text
💡 Something you noticed

[Finding]

[Optional supporting insight]
```

The interface should make it clear that the feedback relates to what the learner actually submitted.

---

# 15. Feedback Tone

Feedback should feel like an insight rather than a grade.

Prefer:

> Nice. You noticed something interesting.

or:

> Interesting thought. Look once more at the space around the figure.

Avoid:

> Correct.

> Incorrect.

> You scored 8/10.

> Congratulations! You successfully passed the activity.

The feedback should remain concise.

---

# 16. Feedback Length

The UI should not encourage excessively long feedback.

The preferred rhythm is:

```text
Learner observation
       ↓
Specific Finding
       ↓
Small insight
       ↓
Optional invitation to look again
```

The purpose is to help the learner notice something useful, not to turn every activity into a lecture.

---

# 17. Icons and Emoji

The implementation may use semantic icons or emoji to establish Fablit's visual vocabulary.

Initial vocabulary:

| Purpose    | Suggested cue |
| ---------- | ------------- |
| Curiosity  | 👀            |
| Explore    | 🔎            |
| Think      | 💭            |
| Respond    | ✍️            |
| Insight    | 💡            |
| Reflection | 🌱            |
| Completion | ✨             |

These are suggestions rather than a requirement to use emoji literally.

A consistent icon library may be used instead if it produces a more cohesive visual result.

---

## 17.1 Icon Rules

Icons should:

* communicate meaning;
* support visual hierarchy;
* remain consistent;
* avoid visual clutter.

Icons should not:

* be used purely as decoration;
* dominate the content;
* replace semantic labels;
* create a childish visual tone.

---

# 18. Completion State

Completion should provide a small feeling of accomplishment without creating a reward system.

Preferred direction:

```text
✨ That's one done.

You noticed.
You thought.
You found something.

[ Back to explore → ]
```

The exact wording may vary.

The completion state should clearly communicate that the activity is finished.

---

# 19. Return Navigation

The learner should have a clear option to return to the dashboard/exploration area after completion.

This preserves the learner journey established by previous specifications.

The learner should not be trapped inside the activity.

---

# 20. Emotional Design

The interface should support:

```text
👀 Curiosity
      ↓
🔎 Exploration
      ↓
💭 Thinking
      ↓
✍️ Expression
      ↓
💡 Insight
      ↓
🌱 Reflection
      ↓
✨ Accomplishment
```

It should avoid:

```text
Question
   ↓
Test
   ↓
Correct / Incorrect
   ↓
Score
```

The learner should leave the activity with a sense of accomplishment rather than gain/loss.

---

# 21. Visual Personality

The implementation should feel:

* warm;
* lightweight;
* creative;
* calm;
* approachable;
* contemporary;
* slightly playful.

It should not feel:

* institutional;
* corporate;
* exam-oriented;
* overly formal;
* childish;
* excessively gamified.

The desired balance is:

> **Playful, not juvenile.**

---

# 22. Layout

The layout should use intentional whitespace.

The learner should not encounter a dense collection of:

* labels;
* borders;
* controls;
* paragraphs;
* buttons.

The important elements should have room to breathe.

Visual hierarchy should make the next action obvious.

---

# 23. Typography

Typography should provide clear hierarchy without making the interface feel academic.

The hierarchy should generally be:

```text
Large activity title
        ↓
Short invitation
        ↓
Stimulus
        ↓
Observation prompt
        ↓
Response
        ↓
Finding
        ↓
Completion
```

Avoid dense text blocks.

---

# 24. Colour

SPEC-016 should establish the visual direction without requiring a final Fablit-wide colour system.

The visual treatment should be:

> Soft, warm, creative and restrained.

Avoid excessive use of bright competing colours.

Colour should support hierarchy and state rather than become decoration.

---

# 25. Interaction Feedback

Small interactions may be used to make the experience feel responsive.

Appropriate examples include:

* activity card hover state;
* button hover/focus state;
* subtle transitions;
* smooth feedback appearance;
* natural completion transition.

Animations should remain subtle.

The goal is:

> "The interface feels alive."

not:

> "The interface is trying to entertain me."

---

# 26. Responsive Behaviour

The activity must remain usable on smaller screens.

The primary mobile flow should remain:

```text
Title
 ↓
Image
 ↓
Prompt
 ↓
Response
 ↓
Feedback
 ↓
Completion
```

Avoid unnecessary multi-column layouts for the core activity.

The learner should not need to zoom or horizontally scroll.

---

# 27. Accessibility

The visual refinement must preserve or improve accessibility.

The implementation must retain:

* readable text;
* sufficient contrast;
* keyboard navigation;
* visible focus states;
* meaningful labels;
* accessible form controls;
* appropriate image alternative text;
* logical reading order.

Emoji and icons must never be the sole carrier of meaning.

---

# 28. Existing Architecture

SPEC-016 should work with the architecture established by previous specifications.

In particular:

* reuse existing activity models;
* reuse existing stimulus handling;
* reuse existing evaluation;
* reuse existing Finding/feedback structures;
* reuse existing persistence;
* reuse existing navigation where possible.

The implementation should prefer frontend composition and styling changes over backend changes.

---

# 29. Backward Compatibility

Existing activities and application behaviour should continue to work.

Where the new UX is introduced, it should not break:

* existing activity submission;
* stimulus retrieval;
* fallback behaviour;
* evaluation;
* Finding generation;
* persistence;
* navigation.

---

# 30. Testing Requirements

Automated tests should verify the existing behaviour remains intact.

At minimum, the implementation should cover:

### Activity rendering

* activity title is displayed;
* stimulus is displayed;
* observation prompt is displayed;
* response control is displayed.

### Submission

* learner can submit a response;
* existing evaluation flow is invoked;
* Finding is displayed after evaluation.

### Completion

* completion state is displayed;
* return navigation is available.

### Responsive behaviour

The primary activity flow should remain usable at mobile viewport sizes.

### Accessibility

The implementation should verify:

* meaningful labels;
* keyboard accessibility;
* visible focus;
* image alternative text;
* appropriate semantic structure.

---

# 31. UX Validation Checklist

Before considering the implementation complete, review the activity as a first-time learner.

Ask:

* Is it immediately clear where to start?
* Is the image visually prominent?
* Is the activity invitation inviting?
* Is the question easy to understand?
* Does the response area feel comfortable?
* Does the primary action feel conversational?
* Does the feedback feel related to my answer?
* Does the Finding feel like an insight rather than a grade?
* Does completion feel satisfying?
* Can I easily return to exploration?
* Does the interface feel like learning at home?
* Does it feel playful without feeling childish?
* Is there anything visually unnecessary?

---

# 32. Before / After Goal

The desired transformation is:

```text
Current experience
Functional + minimal
        ↓
SPEC-016
        ↓
Functional + intentional + inviting
```

SPEC-016 is successful when the learner experience is visibly improved without unnecessary architectural complexity.

---

# 33. Definition of Done

SPEC-016 is complete when:

* [ ] One complete activity has been visually refined.
* [ ] The dashboard entry point reflects the new visual direction.
* [ ] The activity card has clear visual hierarchy.
* [ ] The activity invitation feels conversational.
* [ ] The stimulus is visually prominent.
* [ ] The observation prompt is clear.
* [ ] The response area feels notebook-like rather than exam-like.
* [ ] The primary action is obvious and conversational.
* [ ] Existing response evaluation continues to work.
* [ ] Personalized Finding is clearly presented.
* [ ] Feedback feels like an insight rather than an assessment.
* [ ] Completion has a distinct visual state.
* [ ] The learner can easily return to the dashboard.
* [ ] Icons/emoji or an equivalent semantic icon system are used consistently.
* [ ] Visual whitespace and hierarchy are intentional.
* [ ] Responsive behaviour works on mobile.
* [ ] Accessibility requirements remain satisfied.
* [ ] Existing SPEC-015 stimulus behaviour remains intact.
* [ ] Existing evaluation and persistence behaviour remains intact.
* [ ] No gamification mechanics have been introduced.
* [ ] No unnecessary backend/domain architecture has been introduced.
* [ ] Automated tests pass.
* [ ] The resulting experience passes the UX validation checklist.

---

# 34. Non-Goals

The following should explicitly not be solved as part of SPEC-016:

* defining the complete Fablit design system;
* redesigning every existing activity;
* implementing a full learner profile;
* implementing progress tracking;
* implementing gamification;
* implementing achievement systems;
* introducing AI-generated feedback;
* replacing the current evaluator;
* introducing new external stimulus providers;
* building learner analytics;
* redesigning the complete application navigation.

These can be considered later based on learner feedback.

---

# 35. Future Direction

After SPEC-016 is implemented, the refined activity should be evaluated before applying the visual language broadly.

The next decision should be based on actual learner experience.

Potential outcomes include:

```text
SPEC-016
    ↓
Internal review
    ↓
Learner feedback
    ↓
┌──────────────────────────────┐
│                              │
▼                              ▼
Successful                 Needs refinement
│                              │
▼                              ▼
Apply pattern               UX iteration
to other activities
```

No assumption should be made that every visual decision in SPEC-016 is final.

---

# 36. North Star

> **Fablit should feel less like opening a course and more like opening a notebook.**

The learner should want to:

**look, think, write, discover, and explore.**

And when the activity ends, the desired feeling is:

> **"That was interesting. I want to try another one."**

