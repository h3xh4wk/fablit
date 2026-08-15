# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **SPEC-011 — Skill–Assessment Activity Association**: in-memory many-to-many association between `Skill` (SPEC-010) and `AssessmentActivity` (SPEC-005) under `fablit.domain`.
  - `AssessmentActivity` references zero or more Skills by stable identity (`skill_ids`), validated on construction: references must be valid identities and unique within the collection.
  - Skills and Assessment Activities remain independently valid; the association carries no relationship attributes and introduces no Progress, mastery, scoring, evaluation, curriculum, examination, or AI semantics.
  - No dedicated relationship domain entity is introduced.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-011](specifications/platform/SPEC-011-skill-assessment-activity-association.md) for details.

- **SPEC-010 — Skill Domain Foundation**: in-memory `Skill` domain model under `fablit.domain`.
  - Stable identity, a human-readable name, and a meaningful description as domain state.
  - Meaningful-content validation rejecting empty and whitespace-only names and descriptions; immutable after creation.
  - Skill remains independent of any single Assessment Activity, Evaluation criteria, Progress, mastery, scoring, hierarchy, curriculum and examination structures, and AI or external generation mechanisms.
  - Domain exception: `InvalidSkillError`.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-010](specifications/platform/SPEC-010-skill-domain-foundation.md) for details.

- **SPEC-009 — Reflection Domain Foundation**: in-memory `Reflection` domain model under `fablit.domain`.
  - Stable identity, Feedback identity reference (SPEC-008), a single general learner-authored content field, and a timezone-aware creation timestamp as domain state.
  - Meaningful-content validation rejecting empty and whitespace-only reflection; immutable after creation; creating Reflection does not modify the associated Feedback.
  - Confidence scoring, improvement goals, action plans, reflection-generation mechanisms, AI providers, Progress, and persistence are deliberately excluded from the model.
  - Domain exception: `InvalidReflectionError`.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-009](specifications/platform/SPEC-009-reflection-domain-foundation.md) for details.

- **SPEC-008 — Feedback Domain Foundation**: in-memory `Feedback` domain model under `fablit.domain`.
  - Stable identity, Evaluation identity reference (SPEC-007), a single general learner-facing content field, and a timezone-aware creation timestamp as domain state.
  - Meaningful-content validation rejecting empty and whitespace-only guidance; immutable after creation; creating Feedback does not modify the associated Evaluation.
  - Scoring, Reflection, feedback-generation mechanisms, AI providers, and persistence are deliberately excluded from the model.
  - Domain exception: `InvalidFeedbackError`.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-008](specifications/platform/SPEC-008-feedback-domain-foundation.md) for details.

- **SPEC-005 — Assessment Activity Domain Foundation**: in-memory `Assessment` and `AssessmentActivity` domain models under `fablit.domain`.
  - Stable unique identities, metadata, lifecycle status, and controlled activity types.
  - Domain validation enforcing identity, required metadata, minimum activity count, and deterministic sequential activity ordering.
  - Domain exceptions: `InvalidAssessmentError`, `InvalidActivityError`, `DuplicateActivityPositionError`.
  - Unit, composition, and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-005](specifications/platform/SPEC-005-assessment-activity-domain-foundation.md) for details.

- **SPEC-006 — Submission Domain Foundation**: in-memory `Submission` domain model under `fablit.domain`.
  - Stable identity, learner identity reference, and Assessment Activity reference (SPEC-005 identity only, without duplicating the activity).
  - Generic extensible learner response, `SubmissionStatus` lifecycle (`Draft` → `Submitted`), and timezone-aware submission timestamp as domain state.
  - Explicit `submit()` transition enforcing a non-empty response and producing an immutable Submitted Submission.
  - Domain exceptions: `InvalidSubmissionError`, `InvalidSubmissionTransitionError`.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-006](specifications/platform/SPEC-006-submission-domain-foundation.md) for details.

- **SPEC-007 — Evaluation Domain Foundation**: in-memory `Evaluation` and `EvaluationFinding` domain models under `fablit.domain`.
  - Stable identity, Submission identity reference (SPEC-006), one-or-more structured Findings with stable identities, and a timezone-aware evaluation timestamp as domain state.
  - Immutable after creation; creating an Evaluation does not modify the associated Submission.
  - Scoring, Feedback, evaluation mechanisms, AI providers, and persistence are deliberately excluded from the model.
  - Domain exceptions: `InvalidEvaluationError`, `InvalidEvaluationFindingError`.
  - Unit and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-007](specifications/platform/SPEC-007-evaluation-domain-foundation.md) for details.
