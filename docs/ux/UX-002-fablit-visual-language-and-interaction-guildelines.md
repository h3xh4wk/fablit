# UX-002 — Fablit Visual Language & Interaction Guidelines

## Summary

Translate the principles established in UX-001 into a small, practical visual and interaction language that can guide the implementation of SPEC-016.

This issue does not introduce a new application architecture or redesign the entire product.

Its purpose is to ensure that the next learner-facing implementation feels intentionally designed rather than merely functional.

---

## Relationship to UX-001

UX-001 defines **what Fablit should feel like**.

UX-002 defines **how that feeling should begin to appear in the interface**.

```text
UX-001
Core UX philosophy
        ↓
UX-002
Visual & interaction direction
        ↓
SPEC-016
Learner experience implementation
````

---

# 1. Visual Direction

The Fablit interface should use:

* generous whitespace;
* clear visual hierarchy;
* comfortable typography;
* prominent activity imagery;
* rounded or softly shaped activity containers where appropriate;
* restrained visual accents;
* subtle interaction feedback;
* visually distinct activity, response, feedback and completion states.

The interface should feel intentionally designed rather than simply styled.

---

# 2. Visual Personality

The visual language should communicate:

* curiosity;
* warmth;
* creativity;
* calmness;
* freedom;
* accomplishment.

It should avoid creating the impression of:

* a classroom;
* an examination system;
* a corporate dashboard;
* a children's gamification product.

The desired balance is:

> **Playful, not juvenile.**

---

# 3. Visual Vocabulary

Fablit may use small icons or emoji as semantic cues.

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

These are starting points rather than a mandatory final icon set.

The implementation may replace emoji with a consistent icon system later.

---

# 4. Semantic Use of Icons

Icons and emoji should communicate meaning rather than merely fill visual space.

For example:

```text
👀 Look a little closer
💭 What's your reading?
💡 Something you noticed
🌱 Take a moment to reflect
✨ That's one done
```

Avoid excessive decoration such as:

```text
🎉🔥🚀💯🏆✨🎊
```

The interface should remain calm.

---

# 5. Icons Must Not Carry Meaning Alone

Emoji or icons must never be the only representation of important information.

For example:

```text
💡 Finding
```

is acceptable because the semantic label "Finding" is present.

A standalone:

```text
💡
```

should not be relied upon to communicate an important action or state.

This is particularly important for accessibility.

---

# 6. Dashboard Visual Direction

The dashboard should remain intentionally small.

It should provide a small collection of activities rather than exposing the entire curriculum hierarchy.

Preferred structure:

```text
Greeting
   ↓
Short invitation
   ↓
3–5 activity cards
```

Activity cards should have:

* a clear visual identity;
* short title;
* short invitation/description;
* approximate effort/time;
* an obvious interaction affordance.

Avoid:

```text
Module → Unit → Lesson → Activity
```

as the primary learner-facing navigation model.

The curriculum may exist internally without being exposed as a rigid hierarchy.

---

# 7. Activity Card Design

Activity cards should answer three questions quickly:

### What is this?

A short, memorable title.

### Why might I try it?

A short invitation rather than an academic description.

### How much effort is involved?

A small indication such as:

> ~5 min

Cards should feel like things the learner can choose to explore rather than assignments they have been given.

---

# 8. Activity Screen Hierarchy

The activity screen should follow a clear visual hierarchy:

```text
Invitation
     ↓
Stimulus
     ↓
Observation prompt
     ↓
Response
     ↓
Feedback
     ↓
Reflection
     ↓
Completion
```

The learner should always be able to understand what to look at and what to do next.

---

# 9. Activity Invitation

The activity should begin with an invitation rather than formal instructional language.

Prefer:

> 👀 Look a little closer

over:

> Activity: Visual Analysis

Prefer:

> Take a moment. What catches your attention?

over:

> Analyse the image and provide your answer.

The exact copy can vary, but the underlying tone should remain conversational.

---

# 10. Stimulus Presentation

For observation activities, the image should be a primary visual element.

It should not appear as a small attachment above a form.

Preferred conceptual layout:

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

The learner should immediately understand:

> **This is what I'm here to look at.**

---

# 11. Response Area

The response area should feel closer to a notebook than an examination form.

Prefer:

> 💭 What's your reading of it?

with a supporting prompt such as:

> There isn't a right answer. Tell us what you notice...

Avoid formal labels such as:

> Enter answer

or:

> Submit response for evaluation

unless required for accessibility or clarity.

---

# 12. Primary Action

The primary action should feel like continuing a conversation rather than submitting an examination.

Possible language:

> I'm ready →

or:

> Share my thought →

The exact wording can be refined during implementation.

The action should remain visually obvious without creating assessment pressure.

---

# 13. Feedback Presentation

Feedback should have its own visual identity.

Preferred conceptual structure:

```text
        💡 Something you noticed

        [Finding]

        Look again:
        [Optional invitation]
```

Avoid presenting the result as:

> Evaluation Result

or:

> Assessment Result

The learner should experience feedback as an insight rather than a grade.

---

# 14. Feedback Rhythm

Feedback should follow:

```text
Learner observation
       ↓
Specific Finding
       ↓
Small insight
       ↓
Optional invitation to look again
```

Feedback should not become a long lesson or textbook explanation.

The objective is to give the learner something useful to carry forward.

---

# 15. Completion State

Completion should feel like accomplishment without introducing reward mechanics.

Preferred direction:

> ✨ That's one done.

> You noticed.
> You thought.
> You found something.

Then provide a simple way to return to exploration:

> Back to explore →

Avoid:

* scores;
* points;
* badges;
* rankings;
* achievement percentages;
* excessive celebration animations.

---

# 16. Emotional Design

The interface should reinforce this emotional progression:

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

The interface should not create a feeling of:

```text
Question
   ↓
Test
   ↓
Correct / Incorrect
   ↓
Score
```

---

# 17. Interaction Feedback

Small interaction feedback may be used to make the interface feel alive.

Appropriate examples include:

* subtle card hover states;
* gentle transitions;
* feedback appearing smoothly;
* completion state appearing naturally;
* focus states for keyboard users.

Avoid excessive animations.

The learner should feel:

> "This interface is alive."

not:

> "This interface is trying to entertain me."

---

# 18. Colour Direction

The final colour palette does not need to be established in UX-002.

The initial direction should be:

> **Soft, warm, creative and restrained.**

Avoid using many competing bright colours.

A future design system may define the final palette after the first learner-facing refinement.

---

# 19. Typography Direction

Typography should create hierarchy without making the interface feel formal.

The visual hierarchy should generally move from:

```text
Large friendly title
        ↓
Short invitation
        ↓
Comfortable body text
        ↓
Generous response area
```

Avoid dense blocks of text.

Whitespace should be treated as part of the design.

---

# 20. Mobile Behaviour

The learner experience should remain comfortable on smaller screens.

The primary activity flow should work vertically:

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

The implementation should avoid unnecessary multi-column layouts for the core activity flow.

---

# 21. Accessibility

Visual personality must not reduce accessibility.

The implementation must retain:

* readable text;
* sufficient colour contrast;
* keyboard navigation;
* visible focus states;
* meaningful labels;
* accessible form controls;
* appropriate image alternative text;
* logical reading order.

Icons and emoji must not replace semantic text.

---

# 22. Responsive Consistency

The experience should feel like the same product across desktop and mobile.

Responsive behaviour should adapt layout rather than change the learner's mental model.

The sequence remains:

```text
Invitation
→ Stimulus
→ Prompt
→ Response
→ Feedback
→ Reflection
→ Completion
```

regardless of screen size.

---

# 23. Scope Boundary

UX-002 does not require:

* a complete redesign of Fablit;
* a new frontend framework;
* a new design system package;
* new domain models;
* new persistence;
* new evaluation architecture;
* new learner analytics;
* gamification;
* a complete dashboard rewrite.

The objective is to provide enough direction for SPEC-016 to improve the existing experience without expanding the product unnecessarily.

---

# 24. Before / After Goal

The desired transformation is:

```text
Current
Functional + minimal
        ↓
UX refinement
        ↓
Functional + intentional + inviting
```

Not:

```text
Current
   ↓
Complete product redesign
   ↓
New architecture
New navigation
New domain model
New platform
```

---

# 25. Design Decision Test

When considering a new UI element, ask:

> **Does this make the learner more curious, more comfortable, or more capable?**

If the answer is no, the element should probably not be added.

---

# 26. Fablit Voice

The interface should speak like a thoughtful companion.

Prefer:

> Nice. You noticed something interesting.

over:

> Congratulations! You have successfully completed Activity 3.

Prefer:

> Interesting thought. Look once more at the space around the figure.

over:

> Incorrect. Try again.

Prefer:

> What do you see?

over:

> Please provide your answer.

---

# 27. Anti-Patterns

The implementation must avoid:

* progress bars everywhere;
* points;
* badges;
* leaderboards;
* streak pressure;
* red/green correct/incorrect states;
* excessive confetti;
* classroom terminology;
* dense curriculum menus;
* long instructional paragraphs;
* generic motivational quotes;
* artificial enthusiasm;
* unnecessary decorative elements;
* visual clutter.

---

# 28. First Implementation Target

The first implementation should focus on one complete activity.

That activity should demonstrate:

```text
Dashboard
   ↓
Activity card
   ↓
Invitation
   ↓
Image
   ↓
Prompt
   ↓
Response
   ↓
Finding
   ↓
Feedback
   ↓
Reflection
   ↓
Completion
```

The purpose is to establish the visual language before applying it broadly.

---

# 29. Validation

The implementation should be reviewed from the perspective of a first-time learner.

The reviewer should be able to answer:

* Is it immediately clear where to start?
* Is the image visually prominent?
* Is the question easy to understand?
* Does the response area feel inviting?
* Is the primary action obvious?
* Does feedback feel personal?
* Does completion feel satisfying?
* Does the interface feel like learning at home rather than attending a class?
* Does the interface feel playful without feeling childish?
* Is anything visually unnecessary?

---

# 30. Acceptance Criteria

* [ ] Visual direction is reflected consistently in the implemented experience.
* [ ] Dashboard activity cards have clear visual hierarchy.
* [ ] Activity screen has clear hierarchy between invitation, stimulus, prompt and response.
* [ ] Stimulus is visually prominent.
* [ ] Response area feels conversational rather than exam-oriented.
* [ ] Primary action is visually obvious.
* [ ] Feedback has a distinct visual treatment.
* [ ] Completion has a distinct visual treatment.
* [ ] Icons/emoji are used consistently and semantically.
* [ ] Icons/emoji are not the sole carrier of meaning.
* [ ] Intentional whitespace is present.
* [ ] Typography creates clear hierarchy.
* [ ] The interface remains coherent on mobile.
* [ ] Accessibility requirements are preserved.
* [ ] No new gamification mechanics are introduced.
* [ ] No unnecessary architectural changes are introduced.
* [ ] At least one complete activity demonstrates the intended experience.
* [ ] A first-time learner can understand the next action without additional instructions.

---

# 31. Definition of Done

UX-002 is complete when the first refined Fablit activity feels:

> **Curious enough to invite exploration.**

> **Calm enough to feel comfortable.**

> **Clear enough to require little instruction.**

> **Personal enough to feel responsive.**

> **Playful enough to feel enjoyable.**

> **Simple enough to avoid feeling like school.**

and when the learner finishes with:

> **"That was interesting. I want to try another one."**

rather than:

> **"I finished my assignment."**

---

# 32. North Star

> **Fablit should feel less like opening a course and more like opening a notebook.**

The interface should make the learner want to look, think, write and explore — without making them feel that they are being tested.

```

I think this is a good **companion issue to UX-001**. Keep UX-001 as the higher-level direction, and use UX-002 as the practical bridge into **SPEC-016**.
```
