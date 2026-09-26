# SPEC-026: Metacognitive Practice & Reflection Integration

## 1. Overview & Goal

The objective of SPEC-026 is to deeply integrate metacognitive practice into the core learner workflow by embedding pre-practice goal setting and post-practice self-reflection into the active practice execution path. While SPEC-009 established the `ReflectionDomain` foundation, reflection remains disconnected from active submission cycles. This specification links intent, practice execution, evaluation feedback, and self-assessment into a singular, continuous learning loop without introducing automated grading, AI analysis, or external dependencies.

---

## 2. Functional Requirements

### 2.1 Pre-Practice Intention Prompt

* **Timing:** Displayed immediately after a learner selects a practice activity (via SPEC-019 or SPEC-025) and prior to entering the active workspace.
* **Behavior:** Present an optional, single-input prompt asking the learner to state a specific focus for the upcoming session (e.g., *"Focus on explicit variable naming"* or *"Verify boundary cases before submitting"*).
* **Controls:**
* `Continue with Intention` button.
* `Skip Intention` action (moves directly to practice without blocking).


* **Persistence:** The intention string is captured in the active session context state.

### 2.2 Post-Evaluation Qualitative Reflection

* **Timing:** Triggered immediately after the learner reviews their evaluation feedback (SPEC-017).
* **Behavior:** Display a structured, optional reflection panel containing up to two open-ended qualitative prompts:
1. *Strategy Assessment:* "What strategy or mental model did you use to complete this activity?"
2. *Gap Analysis:* "What was the primary friction point or misconception you encountered?"


* **Controls:**
* `Save Reflection` action.
* `Skip Reflection` action.


* **Validation:** All fields are optional. Submission with empty fields must be accepted gracefully.

### 2.3 History View Extensions

* **Integration:** Update the SPEC-021 practice history detail view to present session records as complete learning artifacts.
* **Layout:** Render pre-practice intention, submitted response, automated evaluation feedback, and post-practice reflection in chronological order within the session detail container.

---

## 3. Data Model Extensions

Extend the internal domain schema (mapping to SPEC-009 and SPEC-021 Datastore models) with the following structure:

```typescript
interface MetacognitiveSessionRecord {
  sessionId: string;
  learnerId: string; // SPEC-024 identity boundary
  activityId: string;
  prePracticeIntention?: string;
  postPracticeReflection?: {
    strategyAssessment?: string;
    gapAnalysis?: string;
    createdAt: string; // ISO 8601
  };
  submittedAt: string;
}

```

---

## 4. Architectural Boundaries & Non-Goals

* **No Scoring or Analytics:** Reflections are strictly qualitative artifacts for the learner. No quantitative score, mastery level, or completion metric is derived from reflections.
* **No Automated Feedback on Reflections:** The system will not process, evaluate, or critique the text written in reflection prompts.
* **Identity Isolation:** All stored intentions and reflections remain bound strictly to the SPEC-024 local private identity key and GCP Datastore boundary.

---

## 5. Acceptance Criteria

* [ ] Learners can submit or skip an optional pre-practice intention before entering a practice activity.
* [ ] Pre-practice intention is correctly attached to the active session payload.
* [ ] Post-evaluation reflection prompts appear immediately following evaluation rendering.
* [ ] Post-practice reflections are saved into the `ReflectionDomain` and associated with the practice session.
* [ ] Skipping either pre- or post-reflections does not block practice completion or history persistence.
* [ ] Historical practice records (SPEC-021) display both intention and reflection data alongside evaluation results.
