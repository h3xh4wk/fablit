# SPEC-035: Publish Approved Practice Candidates to the Learner Library

## 1. Overview & Goal

SPEC-035 completes the handoff from Fablit's human-reviewed authoring workflow to the existing learner-facing curated practice library.

During end-to-end testing, the authoring flow worked, but it was not clear that an approved candidate could be deliberately published and then discovered and completed through the ordinary learner-facing practice journey.

Approval and publication are distinct decisions:

- **Approved** means a human reviewer has accepted the candidate's content quality.
- **Published** means the approved, reviewed content has been deliberately made available in the learner-facing curated practice library.

The authoring store currently exposes approved candidates separately from learner-library content. Approval alone must not be assumed to make content available to learners.

## 2. Product Principle

**AI proposes; a human approves; publication is an explicit curation action.**

Fablit should scale curated practice, not unreviewed content. This specification introduces the smallest safe publication boundary and preserves the existing learner experience.

The intended workflow is:

```
Authoring Brief
    ↓
Generated Candidate
    ↓
Practice Contract Validation
    ↓
Human Review / Edit
    ↓
Approved Candidate
    ↓
Explicit Publish Action
    ↓
Curated Learner Library
    ↓
Practice → Evaluation → Feedback → Reflection
```

## 3. Objectives

- Provide an explicit way to publish an approved candidate to the existing learner-facing curated library.
- Reuse existing practice/activity representations and learner routes wherever possible.
- Preserve existing practice, evaluation, feedback, reflection, and content-quality contracts.
- Keep authoring candidates isolated from learners until publication.
- Keep published content stable and traceable to its approved revision.
- Keep publication independent of monetisation or paywall work.

## 4. Scope

### In scope

- Inspect the existing practice catalogue/activity-definition architecture and identify the smallest compatible publication boundary.
- Define and implement the distinction between approved and published content.
- Add an explicit authoring action to publish an approved candidate.
- Revalidate candidate eligibility and approval state at the publication boundary.
- Convert or register published content using the existing learner-facing practice representation; do not introduce a parallel learner practice model.
- Make published practices discoverable through the current learner-facing practice-selection flow.
- Preserve the content, evaluation, feedback, reflection, practice-mode, and continuation behaviour supported by the existing model.
- Preserve a stable identity for published practice content and traceability to the source candidate/revision.
- Define minimal handling for edits, withdrawal, or replacement after publication.
- Add deterministic tests and update relevant documentation.

### Out of scope

- Payments, subscriptions, paywalls, pricing, or access tiers.
- Automatic publication or approval.
- Learner-facing AI generation or AI evaluation.
- Learner authentication or multi-author roles.
- A general-purpose CMS or extensive publishing dashboard.
- Personalised recommendations, learner profiling, scores, mastery, rankings, or gamification.
- Rebuilding the learner practice flow or redesigning the authoring UI beyond controls needed for publishing.
- Publishing rejected, unvalidated, or merely generated candidates.

## 5. Publication Rules

1. Only an explicitly approved candidate can be published.
2. Rejected, generated, invalid, unreviewed, or edited-but-not-reapproved candidates must never appear in learner-facing catalogue/routes.
3. Approval alone must not make a candidate learner-visible.
4. Publication must be an explicit human action, not a side effect of generation or approval.
5. Publication must use the latest approved revision.
6. If a candidate is edited after approval, existing lifecycle rules must require revalidation and renewed approval before that revision can be published.
7. Repeating the same publish request must not create duplicate learner practices.
8. A storage or publication failure must not be reported as success or leave a misleading partial state.
9. Internal authoring data, provider credentials, reviewer-only findings, and authoring endpoints must not be exposed to learners.
10. Ordinary learner practice must continue to work if the AI provider is unavailable.
11. Use the existing catalogue and content infrastructure. Do not add a new database or service unless repository architecture demonstrates it is necessary.

## 6. Published Content Lifecycle

The implementation should distinguish these conceptual states:

```
Generated / Validated
        ↓
      Review
        ↓
     Approved
        ↓ explicit publish action
     Published
```

Rejected candidates are not publishable. Editing an approved candidate must follow the existing edit/revalidation lifecycle and must not silently change an already published practice.

The implementation should choose the smallest representation compatible with the current architecture. A separate general-purpose workflow engine is not required.

## 7. Published Content and Learner Experience

A published candidate must be represented using the existing learner-facing practice/activity model wherever possible.

A learner should be able to:

- discover the published practice through the existing practice-selection flow;
- start and complete it through the ordinary learner journey;
- receive the evaluation/feedback and reflection experience supported by the practice contract;
- find completed practice history without depending on the authoring system or AI provider.

Authoring-only fields, internal validation diagnostics, reviewer identity, provider credentials, and internal generation details must not leak into learner-facing pages or endpoints.

Publication must not require changes to learner identity or learner history merely to support authoring.

## 8. Identity, Provenance, and Revisions

Published content must have a stable identity suitable for the existing catalogue and practice-history architecture.

Where supported by the existing data model, retain internal traceability to:

- source authoring candidate;
- approved candidate revision;
- publication event/time;
- any subsequent replacement or withdrawal.

Do not expose internal authoring provenance to ordinary learners unless a future specification explicitly requires it.

An already published version must not be silently overwritten by editing its source candidate. Define the smallest safe policy for replacement or withdrawal. Completed learner history must remain readable and must not be corrupted if a practice is withdrawn or replaced.

## 9. Failure and Idempotency

- An invalid state transition must fail safely and explain the problem to the author.
- A persistence/publication failure must not report success.
- Repeating publication for the same candidate/revision must be idempotent and must not create duplicate catalogue entries.
- If publication spans more than one persistence operation, use an approach that avoids or recovers from a misleading partial publication state, consistent with existing repository patterns.
- The authoring workflow and its availability must not become a dependency of ordinary learner practice.

## 10. Security Boundary

- Continue protecting every authoring operation through SEC-001.
- Only authorised authors can invoke publication actions.
- Learner-facing routes must not list or retrieve unapproved authoring candidates.
- Learner routes should expose only the intended published practice content.
- Do not expose provider secrets, reviewer-only diagnostics, or internal authoring endpoints.

## 11. Architecture Boundaries

Implementation must preserve the existing FastAPI + HTMX learner-facing architecture, practice/activity model, practice history, practice modes, feedback, reflection, and deployment/persistence conventions.

Reuse the existing catalogue and persistence patterns. Avoid introducing a parallel practice model, a new database, a payment provider, or a general-purpose CMS unless the existing architecture makes a smaller solution infeasible.

## 12. Acceptance Criteria

- [ ] An authorised author can explicitly publish a valid, approved candidate.
- [ ] Approved-but-unpublished candidates remain invisible to learners.
- [ ] Generated, invalid, edited-but-not-reapproved, and rejected candidates cannot be published.
- [ ] Published content appears in the existing learner-facing discovery/selection flow.
- [ ] A learner can start and complete a published practice using the existing practice journey, including evaluation, feedback, and reflection where supported by the content contract.
- [ ] Publishing the same candidate/revision repeatedly does not create duplicate catalogue entries.
- [ ] Published content has a stable identity and traceable source candidate/revision.
- [ ] Editing a candidate after approval invalidates the previous approval eligibility as required; an already published version is not silently overwritten.
- [ ] A minimal, explicit policy exists for withdrawal or replacement of published content, preserving completed learner history.
- [ ] Authoring and learner-facing access boundaries remain separate; SEC-001 continues to protect authoring actions.
- [ ] Storage errors and invalid state transitions fail safely and visibly.
- [ ] Tests prove both allowed and forbidden publication transitions.
- [ ] Documentation explains the distinction between approval and publication and how to verify a published practice end to end.
- [ ] Existing learner behaviour and regression tests remain green.

## 13. Testing Requirements

Tests should cover:

- a valid approved candidate can be published;
- approved-but-unpublished content remains hidden from learner routes;
- generated, invalid, rejected, and edited-but-not-reapproved candidates cannot be published;
- a published practice appears in the existing learner catalogue;
- the learner can complete the practice through the ordinary practice, feedback, and reflection journey;
- repeated publication is idempotent;
- publication/storage failure does not falsely report success;
- withdrawal/replacement does not corrupt completed learner history;
- authoring endpoints and metadata remain inaccessible from learner routes;
- existing hand-authored practices continue to work unchanged;
- tests do not require live Gemini calls or cloud credentials unless an existing integration-test convention explicitly requires them.

## 14. Definition of Done

An authorised author can generate and review a candidate, explicitly approve it, explicitly publish it to Fablit's curated learner library, and verify that learners can discover and complete it through the existing practice experience.

No unapproved content becomes learner-facing, published content remains traceable and stable, and the existing learner journey remains intact.

## 15. Relationship to Other Specifications

- **SPEC-029 — Practice Content Model & Learning Contract:** defines what makes a practice worth practising.
- **SPEC-030 — Practice Feedback Quality:** defines what makes feedback worth learning from.
- **SPEC-032 — AI-Assisted Practice Authoring:** creates and reviews candidates; this specification completes the publication handoff.
- **SEC-001 — Internal AI Authoring Security Boundary:** protects authoring operations.
- **FIX-7 / #132:** provides shared candidate state for production authoring.
- **FIX-8 / #134:** documents and verifies Datastore-backed candidate storage.

SPEC-035 does not introduce a paywall or make any decision about future monetisation.
