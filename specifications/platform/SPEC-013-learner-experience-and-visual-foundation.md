````markdown
# SPEC-013 — Learner Experience & Visual Foundation

**Specification ID:** SPEC-013
**Title:** Learner Experience & Visual Foundation
**Version:** 0.1.0
**Status:** Draft
**Priority:** High
**Epic:** First Learner Experience

---

## 1. Purpose

SPEC-013 establishes the first coherent learner experience and visual foundation for Fablit.

SPEC-012 established the first complete user-facing learning journey:

```text
Dashboard
    ↓
Practice
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
````

The implementation successfully demonstrates that this journey works.

However, the initial interface is intentionally minimal and primarily proves functionality.

SPEC-013 evolves that interface into a learner experience that reflects Fablit's product philosophy.

The objective is not simply to make the application more visually attractive.

The objective is to make Fablit **feel like Fablit**.

---

# 2. Product Intent

Fablit should feel like a personal space for learning.

It should not feel like:

* a school portal;
* a university learning-management system;
* an examination dashboard;
* a corporate training platform;
* a gamified scoring application.

The learner should experience:

> "This is a place where I can explore something interesting, practise, think, and learn."

The sophisticated structure underneath the experience should remain largely invisible.

---

# 3. Learner Experience Statement

The intended emotional journey is:

```text
Curiosity
    ↓
"I want to try this."
    ↓
Practice
    ↓
"I think I see something."
    ↓
Feedback
    ↓
"Now I understand something better."
    ↓
Reflection
    ↓
"I completed something meaningful."
    ↓
Accomplishment
    ↓
"What else can I try?"
```

The experience should encourage the learner to continue through curiosity rather than obligation.

---

# 4. Learner Experience Principles

SPEC-013 adopts the following principles.

These principles are product constraints and shall guide UI and interaction decisions.

---

## LEP-001 — Home, Not Institution

> **Fablit should feel like a personal space for learning, not a school or university.**

The learner should not feel surrounded by:

* curriculum hierarchies;
* institutional terminology;
* administrative metadata;
* rigid lesson structures;
* examination-oriented language.

The underlying learning architecture may remain structured.

The learner-facing experience should remain personal.

---

## LEP-002 — Structure Should Be Felt, Not Seen

> **Fablit should provide strong learning structure without making the learner feel that they are following a rigid programme.**

The platform may internally organize:

```text
Skills
    ↓
Activities
    ↓
Evaluation
    ↓
Feedback
    ↓
Reflection
```

The learner should primarily experience:

```text
Explore
    ↓
Try
    ↓
Think
    ↓
Learn
```

---

## LEP-003 — Curiosity Before Compliance

> **Fablit should invite learners to explore rather than make them feel obligated to complete a prescribed curriculum.**

Activity presentation should encourage:

> "That looks interesting."

rather than:

> "I have to complete this lesson."

---

## LEP-004 — Fun Through Discovery, Not Gamification

> **Fablit should feel enjoyable because learning is interesting, not because the platform creates artificial competition.**

The core experience shall not depend on:

* points;
* XP;
* badges;
* streaks;
* leaderboards;
* lives;
* winning;
* losing;
* achievement scores.

Fun should come from curiosity, discovery, experimentation, and accomplishment.

---

## LEP-005 — Accomplishment Before Assessment

> **Completing an activity should leave the learner feeling accomplished, not judged.**

The primary emotional outcome should be:

```text
I tried something.
        ↓
I received useful feedback.
        ↓
I understand something better.
        ↓
I completed something meaningful.
```

not:

```text
I gained points.
```

or:

```text
I lost points.
```

Numerical scoring remains outside the scope of this specification.

---

## LEP-006 — Feedback Opens the Next Door

> **Feedback should make the learner curious about what they can try next.**

Feedback should not feel like an examination verdict.

It should provide insight that naturally leads toward further practice.

The intended loop is:

```text
Curiosity
    ↓
Practice
    ↓
Feedback
    ↓
Insight
    ↓
Accomplishment
    ↓
Curiosity
    ↺
```

---

# 5. Visual Direction

The visual direction for Fablit shall be:

> **Calm, personal, curious, spacious, editorial, and contemporary.**

The interface should resemble the feeling of:

> **a thoughtfully designed notebook on a student's desk**

without literally becoming a notebook-themed interface.

The visual language should communicate:

* comfort;
* curiosity;
* focus;
* openness;
* creativity;
* thoughtful learning.

It should avoid communicating:

* institutional authority;
* examination pressure;
* competition;
* administrative complexity.

---

# 6. Visual Character

The interface should be:

### Calm

Avoid excessive visual noise.

### Personal

The learner should feel that the space belongs to them.

### Curious

Activities should invite exploration.

### Spacious

Content should have room to breathe.

### Contemporary

The interface should feel current without chasing visual trends.

### Editorial

Typography and layout may use editorial principles to give activities character.

### Purposeful

Every visual element should support understanding or interaction.

---

# 7. Visual Anti-Patterns

The following patterns should generally be avoided:

* dense dashboards;
* excessive tables;
* institutional navigation;
* heavy borders everywhere;
* large administrative headers;
* excessive badges;
* progress bars that imply performance scoring;
* red/green correctness systems;
* large score displays;
* competitive rankings;
* excessive animations;
* confetti;
* achievement explosions;
* countdown timers;
* decorative elements that distract from the activity.

---

# 8. Typography Direction

Typography should prioritize readability and comfort.

The system should use a simple typographic hierarchy.

At minimum:

```text
Display / Activity Heading
        ↓
Section Heading
        ↓
Body Text
        ↓
Supporting Metadata
```

Activity prompts should receive strong visual emphasis.

For example:

```text
Look a little closer.

What do you notice about the way
these elements work together?

Visual Analysis · Composition
```

The question should attract the learner's attention before secondary metadata.

---

# 9. Colour Direction

The colour system should create atmosphere rather than indicate performance.

The recommended direction is:

> **Warm neutral foundation + restrained Fablit accent.**

Colour should primarily communicate:

* focus;
* invitation;
* emphasis;
* completion;
* interaction.

Colour should not primarily communicate:

* correct;
* incorrect;
* winning;
* losing;
* good score;
* bad score.

The feedback system should not depend on a simplistic:

```text
Green = Good
Red = Bad
```

model.

---

# 10. Spacing and Layout

The interface should use generous spacing.

Content should not feel compressed.

The layout should prioritize:

1. activity/content;
2. learner response;
3. meaningful feedback;
4. actions.

Secondary metadata should remain visually subordinate.

The interface should not attempt to display every available piece of domain information.

---

# 11. Dashboard Experience

The dashboard introduced in SPEC-012 shall be visually redesigned.

The dashboard should feel like:

> **an invitation to learn**

rather than:

> **a list of assigned tasks**

The dashboard shall continue to display approximately 3–5 available activities.

---

# 12. Activity Cards

Activity cards should communicate an invitation to explore.

The conceptual structure should be:

```text
┌──────────────────────────────────┐
│                                  │
│ Look a little closer             │
│                                  │
│ Explore how composition          │
│ changes what we notice.          │
│                                  │
│ Visual Analysis                  │
│                                  │
│                         Try it → │
│                                  │
└──────────────────────────────────┘
```

The exact visual implementation may vary.

The card should prioritize:

1. activity title;
2. short invitation/description;
3. relevant Skill;
4. action.

Internal identifiers and technical metadata shall not be visible.

---

# 13. Activity Language

Where appropriate, activity titles may be written as invitations or questions rather than institutional lesson names.

Prefer:

```text
Look a little closer
```

over:

```text
Lesson 04 — Visual Analysis
```

Prefer:

```text
What happens when you change the way you look at this?
```

over:

```text
Activity: Visual Analysis Exercise
```

This does not mean every activity requires creative wording.

Clarity remains more important than cleverness.

---

# 14. Practice Experience

The practice page should become visually quieter than the dashboard.

The learner should feel:

> "Here's the thing. Take your time."

The page should prioritize:

```text
Activity
    ↓
Prompt
    ↓
Response
    ↓
Submit
```

The learner should not be distracted by unnecessary navigation or metadata.

---

# 15. Practice Page Hierarchy

The conceptual hierarchy should be:

```text
Activity title

Prompt / question

Associated Skill
        ↓
Response area
        ↓
Submit action
```

The prompt shall receive strong visual emphasis.

The response area shall provide sufficient space for thoughtful writing.

---

# 16. Response Input

The response field shall:

* be clearly identifiable;
* have an accessible label;
* provide sufficient writing space;
* have an obvious submit action;
* retain the existing validation behaviour.

The response field should feel like an invitation to think rather than a form field in an examination portal.

---

# 17. Feedback Experience

Feedback is a central part of Fablit's identity.

The feedback interface shall make Evaluation useful without exposing unnecessary internal domain complexity.

The learner should experience feedback as:

> **someone helping them think more deeply.**

The conceptual structure should be:

```text
A little feedback

What you noticed

What to think about

Try this next

Reflect
```

---

# 18. Feedback Language

Feedback should use encouraging and precise language.

Avoid:

* incorrect;
* failed;
* poor;
* score;
* grade;
* penalty;
* pass;
* fail.

Prefer language such as:

* you noticed;
* you identified;
* here's something to think about;
* you could explore;
* try comparing;
* next time, consider;
* here's another way to look at it.

The exact language should remain natural rather than artificially positive.

---

# 19. Structured Finding Presentation

The existing structured Finding should remain part of the domain and application architecture.

The UI shall translate the Finding into a learner-friendly presentation.

Conceptually:

```text
┌────────────────────────────────────┐
│ A little feedback                  │
│                                    │
│ You noticed something important.   │
│                                    │
│ ─────────────────────────────────  │
│                                    │
│ Here's something to think about.  │
│                                    │
│ Your response describes the        │
│ elements separately. Consider      │
│ what happens when you look at      │
│ their relationship.                │
│                                    │
│ ─────────────────────────────────  │
│                                    │
│ Try this next                      │
│                                    │
│ Compare two elements and describe  │
│ what changes when you see them     │
│ together.                          │
└────────────────────────────────────┘
```

The UI shall not expose raw domain object structures.

---

# 20. Reflection Experience

Reflection should feel like a natural continuation of feedback.

The learner should not feel that another administrative form has appeared.

The prompt should be purposeful.

The existing SPEC-012 prompt may be retained:

> **What will you try differently the next time you practise this skill?**

The reflection area should provide enough space for a thoughtful response.

---

# 21. Completion Experience

Completion should be quiet and satisfying.

The learner should receive acknowledgement without excessive celebration.

A conceptual example:

```text
That's one done.

You took a closer look,
thought about it,
and found something new.

Your reflection is saved.

Back to practice →
```

The completion experience should communicate:

* completion;
* accomplishment;
* continuity.

It should not communicate:

* victory;
* defeat;
* ranking;
* score.

---

# 22. Interaction Design

Interactions should feel:

* responsive;
* predictable;
* gentle;
* purposeful.

The interface may use:

* subtle hover states;
* focus states;
* short transitions;
* progressive disclosure;
* HTMX-enhanced fragments.

Animations shall not become the focus of the experience.

---

# 23. Animation Constraints

Animation shall:

* support comprehension;
* communicate state changes;
* provide interaction feedback;
* remain short and subtle.

Animation shall not:

* reward users through visual explosions;
* create competition;
* distract from learning;
* slow down the completion of tasks.

---

# 24. Navigation

Navigation should remain intentionally small.

The learner should primarily need to move between:

```text
Dashboard
   ↓
Practice
   ↓
Feedback
   ↓
Reflection
   ↓
Completion
   ↓
Dashboard
```

The UI should not introduce a large institutional navigation hierarchy.

---

# 25. Mobile Experience

The learner experience shall support mobile screens as a first-class environment.

The UI shall adapt to small screens without simply shrinking the desktop layout.

On mobile:

* activity cards may stack vertically;
* text shall remain readable;
* response fields shall remain comfortable to use;
* actions shall remain easy to tap;
* navigation shall remain simple;
* feedback shall remain readable;
* excessive horizontal layouts shall be avoided.

---

# 26. Responsive Behaviour

The layout shall support at minimum:

* mobile;
* tablet;
* desktop.

The exact breakpoints are an implementation decision.

The specification requires that the learner experience remain coherent across screen sizes.

---

# 27. Accessibility

The visual redesign shall preserve and improve accessibility.

At minimum:

* semantic HTML shall be used;
* headings shall reflect document hierarchy;
* form fields shall have accessible labels;
* buttons shall have meaningful labels;
* links shall have meaningful text;
* keyboard navigation shall remain usable;
* focus states shall be visible;
* colour shall not be the sole indicator of meaning;
* sufficient text contrast shall be maintained;
* reduced-motion preferences should be respected where animation is introduced.

Accessibility is part of the learner experience, not a later enhancement.

---

# 28. Design System Foundation

SPEC-013 shall introduce the minimum reusable visual foundation required for consistency.

The implementation should establish reusable primitives for concepts such as:

* page container;
* typography hierarchy;
* buttons;
* links;
* cards;
* forms;
* field errors;
* feedback sections;
* completion messages.

The implementation should avoid creating a large component framework unnecessarily.

The design system should remain small and understandable.

---

# 29. Design Tokens

Where appropriate, visual values should be centralized.

Potential categories include:

```text
Typography
Spacing
Colours
Border radius
Shadows
Transitions
Container widths
```

The exact token names and values are implementation decisions.

The purpose is consistency and maintainability.

---

# 30. Frontend Architecture

SPEC-013 shall preserve the existing frontend architecture.

The preferred approach remains:

```text
Server-rendered HTML
        +
HTMX progressive enhancement
        +
Small reusable visual components
```

The specification does not introduce:

* React;
* Vue;
* Angular;
* a client-side SPA;
* a frontend state-management framework.

---

# 31. Application Boundary Preservation

The redesign shall not change the Application Layer introduced by SPEC-012 unless a genuine application requirement is discovered.

The preferred architecture remains:

```text
Browser
   ↓
Web/UI
   ↓
Application
   ↓
Domain
   ↓
Infrastructure
```

Visual changes should primarily occur in:

```text
Web/UI
Templates
Styles
Reusable presentation components
```

The domain model should remain unaffected by visual requirements.

---

# 32. Domain Preservation

SPEC-013 shall not introduce new domain concepts solely for visual presentation.

The following remain unchanged:

* Skill;
* Assessment Activity;
* Submission;
* Evaluation;
* Finding;
* Feedback;
* Reflection.

The UI may provide a different representation of these concepts without modifying their meaning.

---

# 33. No Gamification

SPEC-013 explicitly does not introduce:

* points;
* XP;
* badges;
* streaks;
* leaderboards;
* levels;
* lives;
* competitive rankings;
* win/loss states.

The product shall rely on curiosity, learning, feedback, and accomplishment.

---

# 34. No Scoring

Numerical scores remain outside the scope.

The redesigned feedback experience shall not introduce:

* percentages;
* grades;
* marks;
* pass/fail;
* ranking indicators.

Future specifications may revisit assessment measurement if justified by product evidence.

---

# 35. No Progress Domain

SPEC-013 shall not introduce a Progress domain model.

A visual interaction indicator may be used where necessary for navigation or workflow clarity, but it shall not imply learner mastery or performance.

For example:

```text
Activity
    ↓
Feedback
    ↓
Reflection
```

may be visually represented as a workflow.

It must not become:

```text
Progress: 72%
```

---

# 36. Content Boundaries

SPEC-013 shall use the existing demo content from SPEC-012.

The specification does not require:

* a large content library;
* NIFT-specific curriculum;
* new assessment domains;
* new evaluation datasets.

The focus is presentation and learner experience.

---

# 37. User Feedback Readiness

SPEC-013 should make the application suitable for a small group of real learners to use.

The objective is not production-scale launch.

The objective is:

> **Create a sufficiently coherent and pleasant experience that real students can use Fablit and provide meaningful feedback.**

The resulting feedback shall inform later product specifications.

---

# 38. Observability for Learning

The initial learner group should be observed primarily through qualitative feedback.

SPEC-013 does not introduce a full analytics platform.

The team should be able to learn:

* where learners hesitate;
* which activities attract attention;
* whether prompts are understandable;
* whether feedback feels useful;
* whether reflection feels purposeful;
* whether completion feels satisfying;
* whether the learner understands what to do next.

These observations may be collected manually during the initial validation phase.

---

# 39. Testing Strategy

The redesign shall preserve all existing functional tests.

Visual work shall not break:

* application tests;
* domain tests;
* route tests;
* end-to-end learner journey tests.

Additional tests should cover where practical:

* dashboard rendering;
* activity card rendering;
* responsive layout behaviour;
* accessible form controls;
* feedback presentation;
* completion state;
* keyboard navigation for core interactions.

---

# 40. End-to-End Learner Acceptance Test

The existing SPEC-012 learner journey shall continue to work:

```text
Open Dashboard
    ↓
Choose Activity
    ↓
Read Prompt
    ↓
Submit Response
    ↓
Receive Feedback
    ↓
Reflect
    ↓
Complete
    ↓
Return to Dashboard
```

The redesigned experience should make this journey visually coherent from beginning to end.

---

# 41. Learner Experience Acceptance Criteria

SPEC-013 is complete when:

* [ ] The dashboard feels like a personal learning space.
* [ ] The dashboard does not resemble an institutional LMS.
* [ ] 3–5 activities remain available.
* [ ] Activities feel like invitations rather than administrative tasks.
* [ ] Activity cards have clear visual hierarchy.
* [ ] Activity prompts receive appropriate emphasis.
* [ ] The practice experience is visually quieter than the dashboard.
* [ ] The response experience feels comfortable for thoughtful writing.
* [ ] Feedback is presented conversationally.
* [ ] Structured Findings are translated into understandable learner-facing feedback.
* [ ] Feedback does not rely on scores.
* [ ] Feedback identifies an improvement opportunity.
* [ ] Feedback provides a useful next step.
* [ ] Reflection feels like a continuation of learning.
* [ ] Completion communicates accomplishment without gamification.
* [ ] The learner has a clear route back to practice.
* [ ] The interface works on mobile.
* [ ] The interface works on desktop.
* [ ] Keyboard navigation remains usable.
* [ ] Focus states are visible.
* [ ] Colour is not the sole means of communicating meaning.
* [ ] The core journey remains usable without JavaScript.
* [ ] HTMX continues to function as progressive enhancement.
* [ ] Existing SPEC-012 automated tests pass.
* [ ] Existing domain tests pass.
* [ ] Existing application tests pass.
* [ ] No scoring is introduced.
* [ ] No gamification is introduced.
* [ ] No Progress domain is introduced.
* [ ] No authentication is introduced.
* [ ] No recommendation engine is introduced.
* [ ] No AI evaluation dependency is introduced.
* [ ] No examination-specific logic is introduced.

---

# 42. Definition of Done

SPEC-013 is complete when the Fablit application can be placed in front of a small group of learners and the team can reasonably ask:

> **"Does this feel like a place where you would enjoy learning on your own?"**

The implementation must demonstrate:

```text
Open Fablit
    ↓
Feel invited rather than instructed
    ↓
Choose something interesting
    ↓
Practice without distraction
    ↓
Receive useful feedback
    ↓
Reflect naturally
    ↓
Feel accomplished
    ↓
Want to explore another activity
```

The answer does not need to be perfect.

The purpose of SPEC-013 is to establish a coherent first experience that is good enough for real learner feedback.

---

# 43. Architectural Outcome

SPEC-013 does not fundamentally change Fablit's domain architecture.

Instead, it establishes the first coherent presentation layer around the existing architecture:

```text
                    Learner
                       │
                       ▼
                Fablit Experience
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Dashboard     Practice     Feedback
          │            │            │
          └────────────┼────────────┘
                       ▼
                   Reflection
                       │
                       ▼
                 Accomplishment
                       │
                       ▼
                    Explore
                       ↺
```

The underlying architecture remains:

```text
Web/UI
   ↓
Application
   ↓
Domain
   ↓
Infrastructure
```

The purpose of SPEC-013 is to make that architecture accessible through an experience that feels human, personal, and inviting.

---

# 44. Product Philosophy

SPEC-013 establishes the following product philosophy:

> **Fablit should not make learning feel like following a curriculum.**

> **It should make learning feel like discovering something.**

The learner should not leave an activity primarily thinking:

> "What did I score?"

They should leave thinking:

> **"I understand something now that I didn't understand before."**

And ideally:

> **"What should I try next?"**

---

# 45. North Star Statement

The first Fablit experience should make a learner feel:

> **"This feels like my own place to learn. I can explore something interesting, try it without pressure, learn from the feedback, and finish feeling that I've accomplished something."**

That feeling is the primary success criterion for the learner experience introduced by SPEC-013.
