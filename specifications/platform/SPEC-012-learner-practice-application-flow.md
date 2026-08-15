````markdown
# SPEC-012 — Learner Practice Application Flow

**Specification ID:** SPEC-012  
**Title:** Learner Practice Application Flow  
**Version:** 0.1.0  
**Status:** Draft  
**Priority:** High  
**Epic:** First Learner Experience

---

## 1. Purpose

SPEC-012 introduces the first user-facing vertical slice of Fablit.

The objective is to allow a learner to complete one meaningful learning cycle:

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
Meaningful Feedback
   ↓
Purposeful Reflection
   ↓
Completion Confirmation
   ↓
Dashboard
````

This specification introduces the minimum application and presentation-layer capabilities required to orchestrate the existing domain model into a usable learner experience.

SPEC-012 does **not** introduce a new core domain concept.

Instead, it establishes the first **Application Layer** and connects it to a minimal server-rendered user interface.

---

# 2. Background

Fablit has established the following domain foundation:

```text
Skill
   ↕
Assessment Activity
   ↓
Submission
   ↓
Evaluation
   ↓
Finding
   ↓
Feedback
   ↓
Reflection
```

The previous specifications deliberately focused on establishing these concepts and their boundaries.

SPEC-011 established that an Assessment Activity may provide an opportunity to practice and demonstrate one or more Skills, while preserving the independence of both concepts.

The domain foundation is now sufficient to support a complete learner-facing practice cycle.

The missing capability is application-level orchestration.

The application layer shall connect:

```text
User interaction
      ↓
Application use case
      ↓
Domain operation
      ↓
Application result
      ↓
User-facing representation
```

---

# 3. Architectural Decision

SPEC-012 establishes the following boundary:

```text
┌──────────────────────────────────────────────┐
│                 USER / BROWSER               │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                 WEB / UI                     │
│                                              │
│ HTMX + server-rendered HTML                  │
│ Pages / forms / fragments                    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              APPLICATION LAYER               │
│                                              │
│ Learner use cases                            │
│ Workflow orchestration                      │
│ View-model preparation                       │
│ Domain coordination                          │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                  DOMAIN                      │
│                                              │
│ Skill                                        │
│ Assessment Activity                          │
│ Submission                                   │
│ Evaluation                                   │
│ Finding                                      │
│ Feedback                                     │
│ Reflection                                   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              INFRASTRUCTURE                  │
│                                              │
│ Persistence / evaluation mechanisms           │
└──────────────────────────────────────────────┘
```

The Application Layer shall orchestrate existing domain behaviour.

It shall not become a second domain model.

---

# 4. Objectives

SPEC-012 shall:

* introduce the minimum Application Layer required for the first learner journey;
* introduce a small learner-oriented dashboard;
* display 3–5 available practice activities;
* allow a learner to start an activity;
* display the activity's associated Skill(s);
* display the activity prompt/instructions;
* allow a learner to submit a response;
* create a Submission using existing domain behaviour;
* trigger a deterministic predefined evaluation for the demo experience;
* produce an Evaluation containing at least one structured Finding;
* present meaningful feedback to the learner;
* provide a purposeful reflection prompt;
* allow the learner to submit a Reflection;
* display a completion confirmation;
* allow the learner to navigate back to the dashboard;
* preserve existing domain boundaries;
* establish an end-to-end testable learner journey.

---

# 5. North Star

SPEC-012 shall support Fablit's North Star:

> **Build skills through deliberate practice, meaningful feedback, and continuous improvement.**

The first user-facing experience shall therefore demonstrate:

```text
Practice
   ↓
Attempt
   ↓
Evaluation
   ↓
Feedback
   ↓
Reflection
   ↓
Improvement
```

The UI shall not be designed primarily around scores, rankings, gamification, or administrative concepts.

---

# 6. Scope

## 6.1 In Scope

### User-facing

* learner dashboard;
* available activity list;
* activity practice page;
* response submission;
* evaluation/feedback page;
* reflection page;
* completion confirmation;
* dashboard navigation.

### Application Layer

* dashboard retrieval use case;
* start-practice use case;
* submit-response use case;
* evaluation orchestration;
* feedback preparation;
* submit-reflection use case;
* completion result.

### Evaluation

* deterministic predefined demo evaluation;
* at least one structured Finding;
* learner-facing feedback derived from the predefined evaluation.

### Frontend

* server-rendered HTML;
* HTMX-compatible interaction;
* forms;
* navigation;
* basic progressive enhancement.

### Testing

* application-layer tests;
* domain integration tests where required;
* web/route tests;
* end-to-end learner journey test.

---

## 6.2 Out of Scope

The following are explicitly excluded:

* authentication;
* user registration;
* user profiles;
* real learner identity management;
* authorization;
* Progress;
* Skill mastery;
* Skill proficiency;
* Skill scoring;
* numerical assessment scores;
* recommendations;
* personalization;
* streaks;
* leaderboards;
* gamification;
* notifications;
* Content Packs;
* NIFT-specific logic;
* examination-specific workflows;
* AI evaluation;
* external LLM providers;
* asynchronous evaluation infrastructure;
* human evaluation;
* analytics;
* dashboards containing historical learner analytics;
* adaptive learning;
* Skill analytics;
* Evidence aggregation;
* curriculum mapping;
* production persistence requirements beyond what the existing architecture requires for the vertical slice.

---

# 7. Learner Journey

The complete journey shall be:

```text
                    ┌───────────────┐
                    │   Dashboard   │
                    │   3–5 acts    │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    Practice   │
                    │ Activity      │
                    │ Skill         │
                    │ Prompt        │
                    │ Response      │
                    └───────┬───────┘
                            │
                         Submit
                            │
                            ▼
                    ┌───────────────┐
                    │  Submission   │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Demo Evaluator│
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   Feedback    │
                    │               │
                    │ Findings      │
                    │ Improvement   │
                    │ Next step     │
                    └───────┬───────┘
                            │
                         Reflect
                            │
                            ▼
                    ┌───────────────┐
                    │  Reflection   │
                    │ purposeful    │
                    │ prompt        │
                    └───────┬───────┘
                            │
                           Save
                            │
                            ▼
                    ┌───────────────┐
                    │   Completed   │
                    │       ✓       │
                    │               │
                    │ [Dashboard]   │
                    └───────────────┘
```

---

# 8. Application Use Cases

SPEC-012 shall establish the following application-level use cases.

## UC-001 — Get Practice Dashboard

Purpose:

> Provide the learner with a small set of available practice activities.

Input:

```text
Learner context
```

For the initial implementation, the learner context may be a development/demo context.

Output:

```text
Practice Dashboard View Model
```

containing:

* 3–5 activities;
* activity identifier;
* activity title;
* activity description/prompt summary;
* associated Skill(s);
* action to start the activity.

The use case shall not implement recommendation logic.

---

# 9. UC-002 — Start Practice Activity

Purpose:

> Present an Assessment Activity in a form suitable for learner practice.

Input:

```text
activity_id
```

Output:

```text
Practice Activity View Model
```

containing at minimum:

* activity identifier;
* activity title;
* activity instructions/prompt;
* associated Skill(s);
* response input configuration;
* submit action.

The Application Layer shall obtain the relevant Assessment Activity through the existing domain/infrastructure boundaries.

---

# 10. UC-003 — Submit Response

Purpose:

> Accept a learner response and create a valid Submission.

Input:

```text
activity_id
response
```

The use case shall:

1. validate the application request;
2. obtain the Assessment Activity;
3. create a Submission through the existing domain model;
4. persist or otherwise retain the Submission according to the current platform architecture;
5. initiate the evaluation step;
6. produce a learner-facing result.

The application layer shall not duplicate Submission business rules.

---

# 11. UC-004 — Evaluate Demo Submission

The first vertical slice shall use a **predefined deterministic evaluation**.

The evaluation mechanism shall be intentionally simple.

It shall not depend on:

* OpenAI;
* another LLM provider;
* external APIs;
* network services;
* asynchronous workers.

The evaluator may identify the demo activity using its stable activity identity or another implementation-appropriate mechanism.

For the selected demo activity, it shall produce a known Evaluation containing at least one structured Finding.

Example conceptual result:

```text
Evaluation
├── Finding
│   ├── observation
│   ├── improvement
│   └── next_step
```

The exact structure shall conform to the existing Evaluation and Finding domain model.

---

# 12. Demo Evaluation Behaviour

The demo evaluator shall provide meaningful feedback rather than a meaningless placeholder.

Example:

### What you did well

> You identified the dominant visual elements clearly.

### Where you can improve

> Your response describes the elements separately but does not explain how they interact.

### Try this next

> Compare two elements and explain how their relationship affects the composition.

The implementation may use different wording, provided that it retains the same learning intent.

The evaluator shall remain deterministic.

The same demo response/activity combination shall produce predictable evaluation output suitable for automated tests.

---

# 13. UC-005 — Present Feedback

Purpose:

> Transform the Evaluation result into a learner-facing feedback experience.

The learner shall see feedback that communicates:

1. what was done well;
2. what could be improved;
3. what the learner can try next.

Feedback shall be actionable.

A raw score shall not be the primary feedback mechanism.

A numerical score is explicitly outside the scope of SPEC-012.

The Application Layer may prepare a view model suitable for the UI.

The domain objects shall not contain HTML or presentation-specific formatting.

---

# 14. Feedback Requirements

The feedback experience shall:

* contain at least one meaningful structured Finding;
* communicate an observable aspect of the learner's response;
* communicate an improvement opportunity;
* provide a next-step suggestion;
* remain understandable without exposing internal domain identifiers;
* avoid technical terminology;
* avoid requiring the learner to understand the Evaluation model.

The feedback experience shall prioritize learning value over scoring.

---

# 15. UC-006 — Start Reflection

After feedback, the learner shall be invited to reflect.

The first reflection prompt shall be purposeful.

Recommended prompt:

> **What will you try differently the next time you practise this skill?**

The prompt shall be presented together with the relevant feedback context.

The learner shall not be presented with an unexplained generic text field.

---

# 16. UC-007 — Submit Reflection

Input:

```text
reflection response
```

The application shall:

1. validate the request;
2. associate the reflection with the appropriate learning context according to the existing Reflection domain model;
3. create a valid Reflection;
4. persist or retain it according to the current platform architecture;
5. return a completion result.

The Application Layer shall not duplicate Reflection domain rules.

---

# 17. Completion Confirmation

After a successful Reflection submission, the learner shall see a small completion confirmation.

Example:

```text
Reflection saved ✓

You've completed this practice.

Your reflection has been recorded.

[ Back to Dashboard ]
```

The confirmation shall:

* clearly indicate successful completion;
* avoid excessive celebration or gamification;
* provide an explicit route back to the dashboard.

The learner shall not be silently redirected immediately after saving the Reflection.

---

# 18. Dashboard Requirements

The initial dashboard shall display a **small list of 3–5 available practice activities**.

The dashboard shall not implement recommendation logic.

Each activity card/list item shall provide enough information for the learner to decide whether to practice it.

At minimum:

```text
Activity title
Short description/prompt
Associated Skill(s)
Start Practice action
```

Example:

```text
Visual Analysis

Analyse the composition of this photograph.

Skill:
Visual Analysis

[ Start Practice ]
```

---

# 19. Practice Activity Requirements

The practice screen shall display:

* activity title;
* activity instructions/prompt;
* associated Skill(s);
* response input;
* submit action.

The interface shall make it clear:

> **What am I practicing?**

and:

> **What am I being asked to do?**

The response field shall be appropriate for the first demo activity.

A simple text response is sufficient.

---

# 20. Submission Requirements

The application shall reject an invalid empty response if the existing domain/application rules require a non-empty response.

The learner shall receive a useful validation message.

Example:

```text
Please enter a response before submitting.
```

The validation message shall not expose implementation details.

The application shall not create a valid Submission from an invalid response.

---

# 21. Evaluation State

The first implementation may present evaluation as an immediate step from the learner's perspective.

Conceptually:

```text
Submit
  ↓
Evaluating...
  ↓
Feedback
```

The implementation shall avoid architectural decisions that prevent future asynchronous evaluation.

The application boundary should allow the evaluation mechanism to evolve later.

SPEC-012 does not require asynchronous processing.

---

# 22. Application Layer Responsibilities

The Application Layer shall:

* orchestrate learner workflows;
* call domain behaviour;
* coordinate domain objects;
* obtain required data;
* prepare learner-facing view models;
* coordinate evaluation;
* coordinate feedback presentation;
* coordinate reflection submission;
* manage application-level workflow state.

The Application Layer shall not:

* redefine domain invariants;
* duplicate domain validation unnecessarily;
* contain HTML;
* contain CSS;
* implement Skill business rules;
* implement Submission business rules;
* implement Evaluation business rules;
* implement Reflection business rules;
* contain examination-specific rules.

---

# 23. Domain Responsibilities

The existing domain shall remain responsible for:

```text
Skill
Assessment Activity
Submission
Evaluation
Finding
Feedback
Reflection
```

SPEC-012 shall reuse these concepts rather than redefining them.

The application layer may compose these concepts into learner workflows.

---

# 24. Web / Presentation Responsibilities

The Web/UI layer shall:

* render learner-facing pages;
* receive browser requests;
* validate basic request shape;
* invoke application use cases;
* render application results;
* render validation errors;
* provide navigation;
* use HTMX where progressive enhancement is useful.

The Web/UI layer shall not contain domain business rules.

---

# 25. HTMX Requirements

The frontend shall follow the existing Fablit frontend architecture.

The MVP shall use:

* server-rendered HTML;
* HTMX for progressive enhancement where appropriate;
* small reusable fragments where useful;
* standard browser navigation where HTMX does not provide meaningful value.

The implementation shall not introduce a React/Vue/Angular SPA.

The frontend shall remain functional as a server-rendered experience without requiring client-side application state.

---

# 26. View Models

The application layer should provide learner-facing representations rather than exposing domain objects directly to templates.

Examples:

```text
PracticeActivityView
    id
    title
    description
    skills
    prompt

FeedbackView
    strengths
    improvements
    next_steps

ReflectionView
    prompt
    context

CompletionView
    message
    dashboard_url
```

The exact implementation may vary.

The important architectural rule is:

> **Presentation concerns shall not leak into domain objects.**

---

# 27. Demo Learner Context

Authentication is outside the scope of SPEC-012.

The vertical slice may therefore use a deterministic development/demo learner context.

The implementation shall avoid introducing a fake user-management domain model solely to support the demo.

The abstraction should leave room for a future authenticated learner context.

Conceptually:

```text
Current

Demo Learner
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


Future

Authenticated Learner
    ↓
Practice
    ↓
Submission
    ↓
...
```

---

# 28. Data and Persistence

SPEC-012 shall follow the repository's existing persistence architecture.

The specification does not require a specific database technology or persistence implementation.

The implementation must, however, preserve the learner journey across the operations required by the vertical slice.

Where persistence is not yet established for a particular capability, a minimal implementation may use the repository's existing appropriate mechanism.

Persistence choices shall not introduce unnecessary infrastructure complexity.

---

# 29. Error Handling

The learner shall receive understandable errors.

The UI shall not expose:

* stack traces;
* internal exception names;
* database errors;
* UUID validation details;
* implementation-specific messages.

Errors shall be mapped appropriately at the application/web boundary.

Examples:

```text
Activity not found.

Please enter a response before submitting.

We couldn't save your reflection. Please try again.
```

Exact wording may vary.

---

# 30. Navigation

The minimum navigation shall support:

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

The learner shall always have a clear route back to the dashboard.

The implementation shall not require browser history manipulation for normal navigation.

---

# 31. Accessibility

The first learner-facing implementation shall provide basic accessible HTML.

At minimum:

* form controls shall have labels;
* buttons shall have meaningful text;
* headings shall represent page structure;
* error messages shall be understandable;
* navigation shall be usable without JavaScript;
* HTMX enhancement shall not be the sole mechanism for completing the core flow.

Accessibility shall be treated as part of the user-facing feature rather than a later enhancement.

---

# 32. Testing Strategy

SPEC-012 shall introduce testing at multiple levels.

## 32.1 Application Tests

Test:

* dashboard use case;
* activity retrieval;
* submission orchestration;
* evaluation orchestration;
* feedback preparation;
* reflection submission;
* completion result.

---

## 32.2 Web Tests

Test:

* dashboard renders;
* 3–5 activities appear;
* activity page renders;
* submission form works;
* invalid response produces validation feedback;
* feedback page renders;
* reflection form renders;
* reflection submission produces completion confirmation;
* dashboard navigation works.

---

## 32.3 Domain Tests

Existing domain tests shall continue to pass.

SPEC-012 shall not weaken or bypass existing domain invariants.

---

# 33. End-to-End Acceptance Test

The most important test for SPEC-012 is the complete learner journey.

### Given

A demo learner opens Fablit.

### And

The system has 3–5 available practice activities.

### When

The learner selects an activity.

### Then

The learner sees:

* activity title;
* prompt/instructions;
* associated Skill(s);
* response field.

### When

The learner submits a valid response.

### Then

A Submission is created.

### And

The deterministic demo evaluator produces an Evaluation.

### And

The Evaluation contains at least one structured Finding.

### And

Meaningful feedback is presented.

### When

The learner selects reflection.

### Then

The learner sees a purposeful reflection prompt.

### When

The learner submits the reflection.

### Then

A valid Reflection is created.

### And

The learner sees a completion confirmation.

### And

The learner can navigate back to the dashboard.

---

# 34. Functional Requirements

## FR-001 — Dashboard

The system shall provide a learner-facing dashboard.

## FR-002 — Activity List

The dashboard shall display 3–5 available Assessment Activities.

## FR-003 — Activity Information

Each displayed activity shall show sufficient information for the learner to understand the practice opportunity.

## FR-004 — Skill Display

The practice experience shall display the Skill(s) associated with the activity.

## FR-005 — Start Practice

The learner shall be able to start an available activity.

## FR-006 — Response

The learner shall be able to provide a response.

## FR-007 — Submission

The system shall create a valid Submission from a valid learner response.

## FR-008 — Invalid Submission

The system shall prevent invalid responses from creating invalid Submissions.

## FR-009 — Demo Evaluation

The system shall evaluate the demo activity using predefined deterministic evaluation behaviour.

## FR-010 — Structured Finding

The Evaluation shall contain at least one structured Finding.

## FR-011 — Meaningful Feedback

The learner shall receive actionable feedback derived from the Evaluation.

## FR-012 — Improvement Guidance

Feedback shall identify an improvement opportunity.

## FR-013 — Next Step

Feedback shall provide a suggested next step.

## FR-014 — Reflection

The learner shall receive a purposeful reflection prompt.

## FR-015 — Reflection Submission

The learner shall be able to submit a Reflection.

## FR-016 — Completion

The system shall display a completion confirmation after successful Reflection submission.

## FR-017 — Dashboard Navigation

The learner shall be able to navigate from completion back to the dashboard.

## FR-018 — Server Rendering

The core experience shall function using server-rendered HTML.

## FR-019 — Progressive Enhancement

HTMX may enhance the experience but shall not be required for the core learning journey.

## FR-020 — No Authentication Dependency

The first vertical slice shall not require authentication.

---

# 35. Domain Rules Preserved

SPEC-012 shall preserve the existing domain rules established by previous specifications.

In particular:

* Assessment Activities remain independent of Skills;
* Skills remain independently meaningful;
* Submissions remain associated with Assessment Activities;
* Evaluations remain separate from Submissions;
* Evaluations contain structured Findings;
* Feedback remains distinct from Evaluation;
* Reflection remains distinct from Feedback;
* no Progress state is introduced;
* no Skill mastery is introduced;
* no scoring is introduced.

---

# 36. Architectural Constraints

SPEC-012 shall comply with the existing Architecture Principles.

## AC-001 — Platform Before Content

The vertical slice shall not introduce examination-specific or NIFT-specific logic.

## AC-002 — Modular by Default

The Application Layer shall remain separate from the Domain Layer and Presentation Layer.

## AC-003 — Simplicity Over Complexity

The first learner experience shall remain deliberately small.

## AC-004 — Testability is a Feature

The complete learner journey shall be automatically testable.

## AC-005 — Documentation is Part of the Product

Architecture and Domain Language documentation shall be updated where the implementation introduces a new architectural boundary.

## AC-006 — AI as a Collaborator

The demo evaluation shall not require AI.

Future AI evaluation mechanisms shall be able to replace the deterministic evaluator without changing the learner-facing domain concepts.

## AC-007 — Specification Before Implementation

Implementation shall follow approval of SPEC-012 and creation of the corresponding GitHub Issue.

---

# 37. Non-Goals

SPEC-012 is explicitly not intended to prove:

* that Fablit can authenticate users;
* that Fablit can recommend activities;
* that Fablit can calculate learner Progress;
* that Fablit can determine Skill mastery;
* that Fablit can score learners;
* that Fablit can evaluate arbitrary learner responses using AI;
* that Fablit can support production-scale persistence;
* that Fablit can support multiple examination systems;
* that Fablit can provide analytics.

The purpose is narrower:

> **Prove that a learner can complete a meaningful practice → feedback → reflection cycle.**

---

# 38. Acceptance Criteria

SPEC-012 is complete when:

* [ ] A learner can open the Fablit dashboard.
* [ ] The dashboard displays 3–5 available practice activities.
* [ ] Each activity identifies its associated Skill(s).
* [ ] A learner can start an activity.
* [ ] The learner sees the activity prompt/instructions.
* [ ] The learner can submit a response.
* [ ] Invalid responses are rejected appropriately.
* [ ] A valid Submission is created.
* [ ] The demo evaluator produces a deterministic Evaluation.
* [ ] The Evaluation contains at least one structured Finding.
* [ ] Feedback is presented in learner-friendly language.
* [ ] Feedback communicates a strength or useful observation.
* [ ] Feedback communicates an improvement opportunity.
* [ ] Feedback provides a next step.
* [ ] The learner receives a purposeful reflection prompt.
* [ ] The learner can submit a Reflection.
* [ ] A valid Reflection is created.
* [ ] The learner sees a completion confirmation.
* [ ] The completion screen provides a dashboard navigation option.
* [ ] The complete learner journey has automated test coverage.
* [ ] Existing domain tests continue to pass.
* [ ] Existing platform tests continue to pass.
* [ ] CI quality gates continue to pass.
* [ ] The Application Layer remains separate from the Domain Layer.
* [ ] Presentation concerns do not enter domain objects.
* [ ] Authentication is not introduced.
* [ ] Progress is not introduced.
* [ ] Skill mastery is not introduced.
* [ ] Numerical scoring is not introduced.
* [ ] AI provider dependencies are not introduced.
* [ ] Recommendation logic is not introduced.
* [ ] Examination-specific logic is not introduced.
* [ ] Architecture documentation is updated where required.
* [ ] Domain Language remains aligned with the implementation.
* [ ] README/documentation reflects the first user-facing capability where appropriate.

---

# 39. Definition of Done

SPEC-012 is considered complete when a developer can demonstrate the following complete flow:

```text
Open Fablit
    ↓
See 3–5 practice activities
    ↓
Choose one
    ↓
See Skill + Activity + Prompt
    ↓
Submit response
    ↓
Submission created
    ↓
Demo Evaluation executed
    ↓
Structured Finding produced
    ↓
Meaningful Feedback displayed
    ↓
Purposeful Reflection requested
    ↓
Reflection submitted
    ↓
Completion confirmation displayed
    ↓
Return to Dashboard
```

The implementation must demonstrate this journey through automated tests.

---

# 40. Future Evolution

SPEC-012 intentionally creates a foundation for future capabilities.

Future specifications may replace or extend the demo implementation with:

```text
Authentication
      ↓
Learner Identity
      ↓
Personalized Practice
      ↓
Progress
      ↓
Evidence
      ↓
Skill Development
      ↓
Adaptive Practice
```

The deterministic evaluator may eventually be replaced by:

```text
Evaluation Mechanism
       │
       ├── Deterministic rules
       ├── Human evaluation
       └── AI-assisted evaluation
```

The learner-facing experience should not need to fundamentally change when the evaluation mechanism evolves.

---

# 41. Architectural Outcome

SPEC-012 establishes the first application-layer boundary in Fablit:

```text
                 Learner
                    │
                    ▼
             HTMX / Web UI
                    │
                    ▼
            Application Layer
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
     Activity   Submission   Reflection
                    │
                    ▼
                Evaluation
                    │
                    ▼
                 Finding
                    │
                    ▼
                 Feedback
```

The significance of SPEC-012 is therefore not the number of screens introduced.

Its significance is that Fablit will demonstrate its first complete learner-facing learning loop using the domain foundation already established.

---

# 42. North Star Acceptance Statement

At the completion of SPEC-012, Fablit shall be able to demonstrate:

> **A learner can choose a practice opportunity, attempt it, receive meaningful feedback grounded in a structured evaluation, reflect on what they will do differently, and return to practice.**

This is the first user-facing proof of Fablit's core learning philosophy:

```text
Practice
   ↓
Feedback
   ↓
Reflection
   ↓
Improvement
```

No additional complexity is required to prove this capability.