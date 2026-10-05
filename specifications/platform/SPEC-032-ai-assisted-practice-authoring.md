# SPEC-032: AI-Assisted Practice Authoring

## 1. Overview & Goal

SPEC-032 establishes an internal workflow for using AI to assist Fablit in creating candidate practice activities.

The purpose is to increase the quality and breadth of Fablit's curated practice library without turning the learner experience into an automatically generated question stream.

The core workflow is:

```
Authoring Brief
      ↓
AI Candidate
      ↓
Practice Contract Validation
      ↓
Human Review
      ↓
Approved Practice
      ↓
Fablit Library
```

AI is an authoring assistant.

It is not the product's authority on educational quality, and it does not publish directly to learners.

---

## 2. Product Principle

Fablit should scale **curated practice**, not unreviewed content.

AI can help a content author:

- explore practice ideas;
- generate alternative prompts;
- vary stimuli and contexts;
- draft evaluation and feedback guidance;
- identify gaps in the practice library;
- convert an approved authoring brief into a structured candidate.

The human author remains responsible for deciding whether a practice belongs in Fablit.

The Practice Content Contract from SPEC-029 and Feedback Contract from SPEC-030 remain the quality boundaries.

---

## 3. Scope

### In scope

- A structured practice-authoring brief.
- AI-generated candidate practices.
- Structured candidate output compatible with SPEC-029.
- Feedback/evaluation authoring guidance compatible with SPEC-030.
- Validation of generated candidates.
- Human review and approval.
- Revision/rejection of candidates.
- Traceability from candidate to approved practice.
- Authoring documentation and workflow.

### Out of scope

- AI-generated practices shown directly to learners.
- Per-learner practice generation.
- AI tutor/chat.
- Automatic publication.
- Automatic approval.
- AI-based learner evaluation.
- AI image judging.
- Personalized recommendation.
- Learner profiling.
- Scores, mastery, ranking, or gamification.
- A general-purpose CMS unless explicitly required by implementation.

---

## 4. Authoring Brief

An authoring brief defines what the author wants the AI to produce.

At minimum it should be possible to specify:

- Practice area.
- Intended learner context.
- Optional examination context.
- Primary creative-thinking lens where applicable.
- Practice purpose.
- Intended mode.
- Desired response form.
- Constraints.
- Stimulus/context requirements.
- Evaluation intent.
- Feedback intent.
- Reflection intent.
- Optional continuation intent.

The brief should describe educational intent rather than merely requesting:

> "Generate a NIFT question."

Exam names alone are not sufficient authoring instructions.

---

## 5. Candidate Practice Contract

Every AI-generated candidate must be structured so that it can be reviewed against SPEC-029.

A candidate should contain, as applicable:

- learner-facing title;
- learner-facing description;
- practice purpose;
- primary creative-thinking lens;
- secondary lens;
- learner task;
- expected thinking;
- response contract;
- evaluation intent;
- feedback intent;
- reflection intent;
- continuation intent;
- practice mode;
- examination/context relevance;
- stimulus requirements.

The exact implementation representation may reuse the existing practice-definition structure.

Do not create a parallel learner-facing practice model solely for AI candidates.

---

## 6. Feedback Candidate Contract

Where the AI produces evaluation or feedback guidance, it must be reviewed against SPEC-030.

Generated guidance should identify:

- observable evidence;
- why that evidence matters;
- meaningful improvement opportunities;
- possible actionable next steps;
- reflection handoff.

Generated feedback must not:

- assign grades;
- infer learner ability;
- infer motivation or effort;
- claim mastery;
- make unsupported predictions;
- create rankings;
- introduce learner labels.

---

## 7. Validation

AI output must pass structural and content validation before it can be presented for approval.

### Structural validation

Validate at minimum:

- required fields are present;
- values use supported practice modes;
- primary lens is valid where applicable;
- response requirements are coherent;
- no unsupported fields are silently accepted;
- generated content can be represented by the existing application architecture.

### Content validation

Review or validate:

- purpose specificity;
- learner-task clarity;
- response suitability;
- mode suitability;
- evaluation opportunity;
- feedback opportunity;
- reflection opportunity;
- continuity opportunity where provided;
- alignment with the requested practice area/context.

Validation is a gate for authoring workflow quality, not an automatic approval mechanism.

---

## 8. Human Review Gate

No AI-generated candidate may become learner-facing Fablit content without human approval.

The reviewer should be able to:

1. Inspect the complete candidate.
2. Compare it with the authoring brief.
3. Check SPEC-029 alignment.
4. Check SPEC-030 feedback alignment.
5. Edit the candidate.
6. Reject the candidate.
7. Approve the candidate for inclusion in the curated library.

Approval should be an explicit human action.

---

## 9. Candidate Status

The authoring workflow should distinguish candidate states conceptually:

```
Draft
  ↓
Generated
  ↓
Validated
  ↓
Under Review
  ↓
Approved
  ↓
Curated Library
```

A candidate may instead be:

- Rejected.
- Returned for revision.

These states are authoring workflow states, not learner progress states.

The implementation should use the smallest representation necessary for the current authoring workflow.

---

## 10. Traceability

An approved practice created with AI assistance should be traceable to its authoring source.

Where practical, retain:

- authoring brief;
- generation date/time;
- generation model/provider identifier;
- candidate version;
- human reviewer;
- approval/rejection status;
- revision history or approved version.

Traceability should support content quality and maintenance.

Do not expose internal generation metadata to ordinary learners unless a future specification explicitly requires it.

---

## 11. Human Editing

AI output should be treated as a draft.

The author must be able to change:

- wording;
- task constraints;
- practice mode;
- evaluation intent;
- feedback intent;
- reflection prompt;
- continuation relationship;
- stimulus/context.

The approved practice must be treated as authored Fablit content, not as immutable AI output.

---

## 12. Quality Principles

### AA-001 — AI proposes, humans decide

AI may generate candidates, but publication requires explicit human approval.

### AA-002 — Contract before generation

Generation should be guided by the Practice Content Contract rather than free-form prompting alone.

### AA-003 — Feedback remains grounded

Generated evaluation and feedback guidance must follow SPEC-030.

### AA-004 — No content inflation

AI must not be used simply to increase the number of practices.

### AA-005 — Practice diversity

Generated candidates should avoid superficial variations of the same prompt.

Variation should be meaningful in task, context, stimulus, or thinking demanded.

### AA-006 — Exam relevance is explicit

Where exam context is requested, the candidate should explain the relevant type of thinking or response rather than relying on the exam name as evidence of relevance.

### AA-007 — No hidden learner model

The authoring system must not generate content based on inferred individual learner traits.

### AA-008 — Approved content remains curated

Only approved candidates enter the learner-facing practice library.

---

## 13. Library Coverage

The authoring workflow may be used to identify and address gaps in the practice library.

Useful dimensions include:

- practice area;
- creative-thinking lens;
- practice mode;
- stimulus/context;
- exam relevance;
- response form;
- existing practice relationships.

These dimensions are authoring and curation aids.

They must not automatically become learner-facing progress categories.

---

## 14. Content Safety and Quality Review

AI-generated candidates require human review for:

- factual accuracy where factual claims are present;
- inappropriate or inaccessible content;
- ambiguous instructions;
- culturally narrow assumptions;
- unnecessary complexity;
- accidental duplication;
- misleading exam claims;
- inappropriate evaluation criteria;
- unsupported feedback claims.

The authoring workflow should favour simple, observable, practice-relevant tasks.

---

## 15. Architecture Boundaries

Implementation must preserve:

- FastAPI + HTMX application architecture for the learner-facing product.
- Existing Assessment Activity model.
- SPEC-021 Practice History.
- SPEC-022 Practice Modes.
- SPEC-023 internal Practice Capability Lens.
- SPEC-024 Learner Identity.
- SPEC-025 authored Practice Transitions.
- SPEC-026 Pre-Practice Intention.
- SPEC-027 learner artifact export.
- SPEC-028 Local Practice Draft.
- SPEC-029 Practice Content Model & Learning Contract.
- SPEC-030 Practice Feedback Quality.
- SPEC-031 Sketchbook-to-Practice Reflection.
- SPEC-033 private artifact support.
- SPEC-034 Google App Engine deployment and durable artifact storage.
- SEC-001 Internal AI Authoring Security Boundary.

The authoring workflow should not require changes to learner identity, learner history, or learner-facing practice selection merely to support AI authoring.

If an authoring interface is introduced, it should remain separate from the learner-facing experience and protected server-side under the SEC-001 access boundary (`FABLIT_AUTHORING_SECRET`).

---

## 16. Data and Secrets

Any AI provider integration must:

- keep credentials server-side or in the project's approved secret mechanism;
- never expose provider credentials to learners;
- avoid sending learner personal data to the generation service;
- use synthetic or author-provided content during authoring unless a future specification explicitly defines another privacy boundary.

Generated candidates should not contain personal learner information.

---

## 17. Failure and Degraded Behaviour

The authoring workflow must fail safely.

Examples:

- AI provider unavailable → author can retry or create content manually;
- malformed AI output → candidate is rejected from approval flow;
- validation failure → candidate remains non-publishable;
- duplicate/similar candidate detected → reviewer is informed rather than automatically publishing;
- generation timeout → no partial learner-facing content is created.

AI availability must never become a dependency for ordinary learner practice.

---

## 18. Learner-Facing Boundary

AI-assisted authoring must be invisible to the ordinary practice journey unless a future specification explicitly changes that boundary.

A learner should experience:

```
Curated Practice
    ↓
Practice
    ↓
Evaluation
    ↓
Feedback
    ↓
Reflection
```

not:

```
AI Generated Question
    ↓
AI Generated Answer
    ↓
AI Generated Score
```

---

## 19. Non-Goals

SPEC-032 does not:

- generate a practice separately for each learner;
- automatically publish generated content;
- create an AI tutor;
- create AI evaluation;
- create AI image analysis;
- create personalized recommendations;
- infer learner personality or ability;
- introduce scoring or mastery;
- expose AI-generation controls to learners;
- replace human content review;
- require a large CMS;
- require a specific AI vendor.

---

## 20. Acceptance Criteria

- [ ] A structured authoring brief can describe a desired practice.
- [ ] AI-generated candidates can be represented using the SPEC-029 Practice Content Contract.
- [ ] Candidate feedback/evaluation guidance can be reviewed against SPEC-030.
- [ ] Structural validation prevents malformed candidates from entering approval.
- [ ] Human approval is required before learner-facing publication.
- [ ] Candidates can be edited or rejected.
- [ ] Approved content is distinguishable from unapproved candidates.
- [ ] Authoring provenance is retained where practical.
- [ ] AI provider credentials are not exposed to learners.
- [ ] Learner personal data is not required for ordinary authoring.
- [ ] AI availability does not affect ordinary learner practice.
- [ ] Generated content does not automatically become a recommendation or learner-specific practice.
- [ ] Automated tests cover validation and publication boundaries.
- [ ] Documentation explains the authoring workflow and human-review gate.
- [ ] The implementation remains compatible with the existing application architecture.

---

## 21. Definition of Done

SPEC-032 is complete when an authorized content author can use AI to produce structured practice candidates, validate and edit them against Fablit's content and feedback contracts, explicitly approve suitable candidates, and place only approved content into the curated practice library.

The result should make content creation more efficient without weakening Fablit's central principle:

> **AI can help create practices. Humans decide what is worth practising.**

---

## 22. Relationship to Previous Specifications

SPEC-029 defines:

> **What makes a practice worth practising?**

SPEC-030 defines:

> **What makes feedback worth learning from?**

SPEC-031 defines:

> **How can Fablit connect existing sketchbook work to deliberate reflection?**

SPEC-034 defines:

> **How can the production platform safely support durable learner artifacts on App Engine?**

SPEC-032 defines:

> **How can Fablit scale the creation of high-quality practices without surrendering curation to AI?**

Together:

```
Practice Contract
      ↓
Feedback Contract
      ↓
Sketchbook / Practice Experience
      ↓
Durable Production Infrastructure
      ↓
AI-Assisted Authoring
      ↓
Human Review
      ↓
Curated Practice Library
```
