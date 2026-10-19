# SPEC-037: Optional Sketch Evidence for Published Practices

## 1. Overview & Goal

The learner practice page can accept an optional sketch/artifact, but the
capability is currently derived from the activity type: only
`ActivityType.REFLECTION` practices expose the upload control and only they
persist an uploaded artifact.

SPEC-035 publishes authored candidates as `WRITTEN_RESPONSE` practices. Even
when such a practice presents a visual stimulus and a sketch would be natural
evidence, the learner never sees the upload option.

SPEC-037 makes sketch evidence an explicit, optional per-practice capability so
that an author can enable it for a published visual practice while leaving the
existing reflection behaviour unchanged.

## 2. Product Principle

**Sketch evidence is optional, private, and authored per practice.**

A sketch is additional evidence a learner may choose to attach. It is never
required, never evaluated or scored, and never visible to anyone but the
learner and their own review surfaces.

## 3. Objectives

- Replace activity-type checks with one shared capability check.
- Enable optional sketch upload for a published practice through an explicit
  author choice.
- Preserve the current reflection sketch behaviour exactly.
- Keep sketches private and attached to the completion, history, and export.
- Keep the change compatible with existing published records.

## 4. Scope

### In scope

- An explicit `supports_sketch_upload` capability on the learner activity
  representation, defaulting to `False`.
- A compatibility rule that keeps reflection practices sketch-enabled.
- An authoring candidate flag (for example `allow_sketch`) and candidate-page
  control.
- Publication of the flag into the learner activity.
- One capability check used by both practice start and submission.
- Persistence in the in-memory and Datastore published stores, with backward
  compatibility.
- Tests, documentation, and changelog updates.

### Out of scope

- In-browser drawing or a canvas editor.
- Evaluating, scoring, analysing, or summarising sketches with AI.
- Changing artifact storage, privacy rules, or export formats.
- Making sketches mandatory for any practice.
- Sketch-based learner profiling or recommendations.
- Changing the practice content contract or evaluation guidance.

## 5. Capability Model

The activity carries an explicit boolean capability. A shared helper answers
“may this practice accept an optional sketch?” and is used by both:

- `PracticeApplication.start_practice` when building the view; and
- `PracticeApplication.submit_response` when deciding whether to retain a
  pending artifact.

The helper returns true when the explicit capability is enabled or when the
activity type is reflection, so existing curated reflection practices keep
working without data migration.

## 6. Authoring & Publication

- An authoring candidate carries an optional author choice for sketch evidence.
- When PUBLISHING a practice that has a stimulus image, the default is enabled
  unless the author has turned it off. Candidates without a stimulus default to
  disabled.
- The candidate page explains the choice in plain language: it adds an optional
  upload for the learner and does not affect evaluation.
- Editing the choice follows the existing edit/revalidation lifecycle.
- Publication copies the resolved capability into the published learner
  activity. A missing value on an older record means disabled (except for the
  reflection compatibility rule).

## 7. Learner Experience

- A practice with the capability shows the existing optional sketch control and
  label.
- A practice without it shows no control, exactly as today.
- Submitting with or without a sketch both complete the practice.
- An uploaded sketch is stored as the existing private artifact, attached to the
  completion, and shown in review, history, and export the same way a reflection
  sketch is.
- Invalid type, size, or content handling stays unchanged.

## 8. Persistence & Compatibility

- Serialize the capability with the published practice record.
- Older records without the field load with the capability disabled; reflection
  practices remain enabled through the compatibility rule.
- The completion/artifact path must work for a non-reflection activity in both
  the in-memory and Datastore repositories.
- No learner history is rewritten or migrated.

## 9. Failure & Privacy

- A failed artifact save must not lose the learner's written response; existing
  submission failure handling stays in force.
- Artifacts remain private to the learner and must not appear on public or
  authoring routes.
- The capability affects only whether the optional control appears; it never
  gates completion.

## 10. Acceptance Criteria

1. A published visual practice with the capability enabled shows the optional
   sketch input.
2. A practice without the capability shows no sketch input.
3. Submitting with or without a sketch completes the practice.
4. An uploaded sketch is attached to the completion and is readable in review,
   history, and export.
5. Existing reflection practice sketch behaviour is unchanged.
6. The capability survives publication and storage round-trips, and older
   publication records still load.
7. All quality gates pass.

## 11. Testing Strategy

- Web-test the practice page with the capability enabled and disabled.
- Web-test submission with no sketch, a valid sketch, and an invalid upload.
- Test review/history/export for a non-reflection sketch.
- Persistence-test the Datastore published-practice round trip and backward
  compatibility.
- Re-run the existing reflection sketch tests unchanged.

## 12. References

- SPEC-027 — learner portfolio and artifact export.
- SPEC-031 — sketchbook to practice reflection.
- SPEC-032 — AI-assisted practice authoring.
- SPEC-035 — publish approved practice candidates.
- SPEC-036 — optional stimulus images for practice candidates.
- GitHub issue #141.
