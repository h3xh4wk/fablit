# SPEC-017 — Submission & Evaluation Feedback

**Status:** Proposed
**Version:** 0.1
**Type:** UX / Interaction
**Depends on:** SPEC-016
**Primary Module:** Practice Workspace / Assessment & Feedback

---

## 1. Problem Statement

When a learner submits an answer for evaluation, there may be a short period before the evaluation result becomes visible.

During this period, the interface must clearly communicate that the learner's submission has been received and that evaluation is in progress.

Without explicit feedback, a learner may interpret the absence of an immediate result as:

* a failed submission,
* an unresponsive application,
* a lost answer, or
* a need to submit again.

This creates uncertainty in a core learner workflow.

The objective of this specification is to improve the **perceived responsiveness and clarity of the submission-to-evaluation transition** without changing the underlying evaluation logic, scoring, rubric, or content.

The project charter identifies submission as a core workflow and establishes a performance expectation for core workflows. Therefore, interaction feedback must complement—not replace—actual performance improvements where those are required.

---

## 2. Objectives

SPEC-017 shall:

1. Provide immediate visual acknowledgement when a learner submits an answer.
2. Clearly communicate when the system is processing the submission/evaluation.
3. Prevent accidental duplicate submissions while evaluation is in progress.
4. Provide an understandable transition from submission to evaluation results.
5. Provide clear feedback when evaluation cannot be completed.
6. Preserve the existing evaluation behaviour and results.
7. Maintain the lightweight MVP frontend approach.
8. Ensure the interaction remains accessible and usable without relying exclusively on animation.

---

## 3. Scope

### In Scope

* Submission button interaction.
* Submission/loading state.
* Evaluation-in-progress state.
* Duplicate-submission prevention.
* Transition to evaluation results.
* Recoverable evaluation error state.
* Accessible status messaging.
* Relevant automated tests.
* UI-level verification of the submission/evaluation flow.

### Out of Scope

* Changes to evaluation algorithms.
* Changes to scoring or rubric logic.
* Changes to question or exercise content.
* Changes to learner progress calculations.
* Changes to authentication or authorization.
* Introduction of a SPA framework.
* Artificial delays intended to make the interface appear responsive.
* Fake percentage-based progress indicators when actual evaluation progress is unknown.
* Major visual redesign of the existing practice workspace.

---

## 4. User Story

### US-017-01 — Submission Acknowledgement

**As a learner,**
I want immediate confirmation that my answer has been submitted,
**so that** I know the application has received my action.

### US-017-02 — Evaluation Feedback

**As a learner,**
I want to know when my submission is being evaluated,
**so that** I do not mistake processing time for an application failure.

### US-017-03 — Duplicate Submission Prevention

**As a learner,**
I want the submission control to prevent repeated submissions while my answer is being processed,
**so that** I do not accidentally submit the same response multiple times.

### US-017-04 — Failure Recovery

**As a learner,**
I want a clear message if evaluation fails,
**so that** I understand what happened and know whether I can retry.

---

## 5. Functional Requirements

### FR-017-01 — Immediate Submission State

When the learner submits an answer:

* The UI shall immediately enter a submission/evaluation state.
* The submission control shall provide visible acknowledgement.
* The learner shall not need to infer whether the click was registered.

The acknowledgement must occur independently of how long the backend evaluation takes.

---

### FR-017-02 — Evaluation-In-Progress State

While evaluation is being performed:

* The UI shall clearly communicate that evaluation is in progress.
* The learner shall remain on the appropriate exercise/evaluation context.
* The interface shall not appear frozen or inactive.
* The existing answer shall not be unintentionally discarded.

Suggested language:

> Evaluating your response…

The final wording may be adapted to the existing product language.

---

### FR-017-03 — Duplicate Submission Prevention

While a submission is being processed:

* The learner shall not be able to accidentally trigger another submission through repeated clicks.
* The control shall communicate its disabled/processing state.
* Once processing completes or fails, the control shall return to the appropriate state.

The implementation must not rely solely on client-side disabling if the backend requires additional protection against duplicate requests.

---

### FR-017-04 — Successful Evaluation

When evaluation completes successfully:

* The processing state shall be removed.
* The evaluation result shall become visible using the existing evaluation experience.
* No additional acknowledgement screen shall unnecessarily interrupt the learner.
* Existing evaluation content and scoring shall remain unchanged.

---

### FR-017-05 — Evaluation Failure

If evaluation cannot be completed:

* The learner shall receive a clear error message.
* The interface shall not remain indefinitely in a loading state.
* Where retrying is safe, the learner shall have an appropriate retry path.
* The learner's entered answer shall not be lost because of the evaluation failure.

The error state should distinguish between a temporary processing failure and an invalid learner submission where the existing backend can provide that distinction.

---

### FR-017-06 — Accessibility

Submission and evaluation states shall be understandable to users relying on assistive technologies.

The implementation should:

* expose meaningful status changes,
* maintain keyboard accessibility,
* provide an accessible disabled/processing state,
* avoid communicating essential information through animation alone.

---

### FR-017-07 — Performance Visibility

The implementation shall not use interaction feedback to conceal unacceptable backend performance.

Where practical, the implementation and testing should allow the team to distinguish:

1. time until the learner receives submission acknowledgement,
2. time spent waiting for evaluation, and
3. time until the final result becomes visible.

The existing project performance target remains applicable to core workflows.

---

## 6. Interaction Model

The expected state transition is:

```text
Ready
  │
  │ learner submits
  ▼
Submitting / Evaluating
  │
  ├──────────────► Success
  │                   │
  │                   ▼
  │             Evaluation Result
  │
  └──────────────► Failure
                      │
                      ▼
                 Error / Retry
```

The UI should make these transitions explicit without introducing unnecessary visual complexity.

---

## 7. UX Guidelines

### 7.1 Keep feedback immediate

The learner should receive acknowledgement as close as possible to the submission action.

### 7.2 Do not fake progress

If the system cannot determine evaluation percentage or remaining time, it should use an indeterminate processing indicator rather than a fabricated progress bar.

### 7.3 Do not over-animate

The MVP deliberately favours lightweight server-driven interaction. Feedback should therefore remain simple and consistent with the existing interface.

### 7.4 Preserve learner confidence

The learner should always be able to answer:

* Did my submission register?
* Is the system working?
* Is my answer still being processed?
* Has evaluation completed?
* What should I do if something failed?

---

## 8. Acceptance Criteria

### AC-017-01 — Submission acknowledgement

**Given** a learner has entered a valid response
**When** the learner submits it
**Then** the interface immediately provides visible acknowledgement that processing has started.

### AC-017-02 — Processing state

**Given** evaluation is taking time to complete
**When** the learner is waiting
**Then** the interface clearly indicates that evaluation is in progress.

### AC-017-03 — Duplicate prevention

**Given** evaluation is in progress
**When** the learner attempts to submit again
**Then** the application prevents an unintended duplicate submission.

### AC-017-04 — Successful evaluation

**Given** evaluation completes successfully
**When** the result is available
**Then** the processing state is removed and the existing evaluation result is displayed.

### AC-017-05 — Evaluation failure

**Given** evaluation fails
**When** the failure is returned to the learner
**Then** the interface displays a clear error state and does not remain indefinitely in the processing state.

### AC-017-06 — Answer preservation

**Given** evaluation fails
**When** the learner returns to the submission flow
**Then** the learner's response is not unexpectedly lost.

### AC-017-07 — Keyboard accessibility

**Given** a learner navigates the submission flow using a keyboard
**When** the learner submits an answer
**Then** the processing state and subsequent result/error state remain understandable and usable.

### AC-017-08 — Assistive technology

**Given** a learner uses assistive technology
**When** the submission/evaluation state changes
**Then** the state change is exposed through an appropriate accessible status mechanism.

### AC-017-09 — Evaluation behaviour unchanged

**Given** an otherwise identical submission
**When** it is evaluated before and after SPEC-017
**Then** the evaluation logic, score, rubric interpretation, and result content remain unchanged.

### AC-017-10 — No artificial waiting

**Given** evaluation completes quickly
**When** the result is returned
**Then** SPEC-017 does not introduce an unnecessary artificial delay merely to display a loading state.

---

## 9. Implementation Checklist

* [ ] Inspect the current SPEC-016 submission/evaluation flow.
* [ ] Identify the existing frontend submission mechanism.
* [ ] Identify the existing backend evaluation lifecycle.
* [ ] Implement an explicit processing state.
* [ ] Disable/prevent duplicate submission while processing.
* [ ] Preserve the existing successful evaluation path.
* [ ] Add an explicit failure state.
* [ ] Preserve learner response data during recoverable failures.
* [ ] Implement accessible status communication.
* [ ] Keep the implementation consistent with the existing HTMX/server-rendered MVP architecture.
* [ ] Avoid introducing a new frontend framework.
* [ ] Avoid changing evaluation/scoring logic.
* [ ] Avoid artificial delays.

---

## 10. Testing Checklist

### Unit Tests

* [ ] Submission enters processing state.
* [ ] Duplicate submission is prevented.
* [ ] Successful evaluation exits processing state.
* [ ] Evaluation failure exits processing state.
* [ ] Retry behaviour works where applicable.
* [ ] Learner response is preserved on recoverable failure.

### Integration Tests

* [ ] Submission request and evaluation response transition correctly.
* [ ] Successful evaluation renders the existing result.
* [ ] Failed evaluation renders the error state.
* [ ] Repeated submission does not create unintended duplicate processing.

### Accessibility Tests

* [ ] Processing state is exposed appropriately.
* [ ] Keyboard interaction remains functional.
* [ ] Disabled/processing controls have meaningful accessible state.
* [ ] Essential information is not conveyed solely through animation.

### Manual UX Verification

A learner should perform the complete flow:

```text
Open exercise
    ↓
Enter response
    ↓
Submit
    ↓
Observe immediate acknowledgement
    ↓
Observe evaluation-in-progress state
    ↓
Receive result
```

The learner should specifically verify that the application no longer feels as though it has become unresponsive after submission.

---

## 11. Non-Functional Requirements

### NFR-017-01 — Responsiveness

The interface shall acknowledge the learner's submission without unnecessary client-side delay.

### NFR-017-02 — Performance

The implementation shall not degrade the existing performance of the submission/evaluation workflow.

### NFR-017-03 — Accessibility

The interaction shall remain compatible with the project's accessibility goals for core learner workflows.

### NFR-017-04 — Maintainability

The implementation shall use the existing frontend interaction patterns wherever practical rather than introducing unnecessary client-side infrastructure.

### NFR-017-05 — Reliability

A failed evaluation request shall not leave the learner permanently trapped in a processing state.

---

## 12. Architectural Constraints

SPEC-017 must respect the existing project architecture.

In particular:

* Use the existing application architecture.
* Preserve the current FastAPI backend approach.
* Preserve the existing HTMX-oriented MVP frontend approach.
* Do not introduce React or another SPA framework.
* Do not modify the evaluation domain merely to implement UI feedback.
* Do not duplicate evaluation logic in the frontend.
* Keep submission state handling close to the existing submission/evaluation flow.
* Prefer simple, explicit state transitions over a complex client-side state-management system.

---

## 13. Observability Considerations

Where existing instrumentation permits, the implementation should make it possible to diagnose:

* submission acknowledgement latency,
* evaluation processing duration,
* total time to result,
* evaluation failures.

New observability infrastructure should only be introduced where necessary to support this specification.

---

## 14. Risks

### Risk 1 — Masking backend latency

A loading indicator may make the interface feel better without addressing an actual performance regression.

**Mitigation:** Preserve the existing performance requirement and distinguish acknowledgement time from evaluation time.

### Risk 2 — Duplicate requests

Client-side interaction alone may not prevent repeated requests in every failure or network scenario.

**Mitigation:** Review the existing request lifecycle and add appropriate protection at the correct application boundary if required.

### Risk 3 — Over-engineering

A sophisticated JavaScript state-management solution would conflict with the project's lightweight MVP architecture.

**Mitigation:** Prefer the existing HTMX/server-driven interaction model.

### Risk 4 — Lost responses

Error handling could accidentally clear the learner's submitted response.

**Mitigation:** Explicitly test response preservation during evaluation failures.

---

## 15. Definition of Done

SPEC-017 is complete when:

* [ ] All acceptance criteria pass.
* [ ] Automated tests pass.
* [ ] Accessibility checks pass for the affected interaction.
* [ ] Duplicate submission behaviour is verified.
* [ ] Success and failure states are verified.
* [ ] Existing evaluation results are unchanged.
* [ ] No artificial evaluation delay has been introduced.
* [ ] The implementation follows the existing MVP architecture.
* [ ] Documentation is updated if the interaction contract or developer-facing behaviour changed.
* [ ] Manual learner verification confirms that submission no longer appears unresponsive.
* [ ] Architecture review has approved the implementation.
* [ ] The associated GitHub issue and PR are linked to SPEC-017.

---

## 16. References

* Project Charter
* Architecture Principles
* Architecture Blueprint
* Domain Language
* SPEC-016
* Existing submission/evaluation implementation
* Existing frontend interaction patterns
* Existing test suite

---

## 17. Future Considerations

The following are intentionally deferred:

* Detailed progress reporting for long-running evaluations.
* Real-time evaluation progress percentages.
* Background job infrastructure specifically for evaluation.
* Advanced optimistic UI patterns.
* Client-side application state management.
* Performance optimisation beyond the scope required to satisfy the existing core-workflow requirements.

These may be considered in a future specification if actual evaluation latency or scale requires them.
