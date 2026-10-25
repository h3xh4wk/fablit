# SPEC-040: AI-Assisted Authoring Brief Creation

## 1. Overview & Goal

The SPEC-032 authoring workflow expects an author to provide a structured brief before AI can generate a practice candidate. The current brief contains required and optional fields covering the practice area, learner context, purpose, response form, evaluation, feedback, reflection, and examination context.

Some potential authors have only rough notes from a meeting, a bulletin board, a conversation, or a short topic description. They may know what they want learners to practise but lack the instructional-design vocabulary to complete every field.

SPEC-040 lets an authorised author turn incomplete source notes into an editable draft of the existing authoring brief. It lowers the entry barrier without replacing author judgement or changing the candidate review and publication lifecycle.

## 2. Product Principle

**AI helps express the author's intent; it must not invent the author's evidence or make decisions invisible.**

The source notes remain the authority for user-provided facts. AI-proposed instructional choices are suggestions until the author reviews and accepts them.

## 3. Objectives

- Allow an author to start from rough notes, copied source text, or a short topic description.
- Draft values for the existing authoring brief fields using the current provider-neutral authoring boundary where practical.
- Make suggestions understandable and editable by a non-expert.
- Distinguish facts supported by the supplied notes from AI-proposed choices and unresolved assumptions.
- Preserve the author's inputs and edits when generation fails or a field is regenerated.
- Hand the reviewed brief into the existing SPEC-032 candidate-generation workflow.

## 4. Scope

### In scope

- An entry point in the existing internal authoring workspace to provide rough notes/source text.
- A structured AI operation that proposes values for the current brief fields, including the existing required and optional fields.
- A review experience that presents the generated values in the existing editable brief form.
- Field-level regeneration, plus whole-brief regeneration, without silently discarding the original notes or other user edits.
- Clear presentation of AI suggestions, missing information, and assumptions that need author confirmation.
- Server-side validation of the structured result and safe handling of provider errors or unusable output.
- Focused tests and updates to relevant authoring documentation and changelog.

### Out of scope

- Replacing or redesigning the full authoring-candidate lifecycle.
- Automatic candidate generation, approval, or publication immediately after brief generation.
- Bypassing the SPEC-032 validation and human-review gates or the SPEC-035 publication gate.
- Creating a separate authoring system, new database, general-purpose prompt library, or multi-step wizard unless repository inspection demonstrates a necessary architectural reason.
- Requiring users to provide every brief field before AI assistance can start.
- Treating generated examination context as official exam guidance without supporting source material.
- Learner-facing AI, learner accounts, learner profiling, scoring, or personalised recommendations.

## 5. User Workflow

1. An authorised author chooses **Help me write the brief** in the existing authoring workspace.
2. The author enters rough notes, pastes relevant source text, or provides a short topic description. Additional known constraints (for example, learner group or duration) can be included if available. Partial input is valid.
3. The author asks AI to draft the brief.
4. Fablit displays proposed values in the existing brief fields, with concise indications of which details are grounded in the supplied notes, which are AI suggestions, and which assumptions or gaps need confirmation.
5. The author edits any field, regenerates one field, or regenerates the whole draft.
6. The author explicitly confirms the brief and proceeds through the existing candidate-generation flow.

Brief drafting and candidate generation are separate actions. Generating a brief must not silently generate, approve, or publish a candidate.

## 6. Field Behaviour

- Use the current brief schema and field names as the source of truth; do not create a parallel brief model.
- Draft all fields that can reasonably be proposed from the available information, including optional fields where useful. Optional fields may remain empty when a suggestion would be speculative or add no value.
- Required fields may receive proposed defaults, but those defaults must remain editable and must not be represented as user-supplied facts.
- Preserve the existing allowed values for controlled fields such as intended practice mode and primary creative-thinking lens. AI output outside the allowed values must be rejected or safely mapped with a clear indication; it must not silently introduce new enum values.
- Keep field content concise, concrete, learner-appropriate, and consistent across the brief.
- The response form should describe what the learner will actually do and produce. Evaluation, feedback, and reflection intent should be actionable and aligned with that response form.
- Do not invent official examination requirements, institutional rules, dates, durations, eligibility conditions, or claims that a task is an official past paper. If the source does not establish these details, label them as unconfirmed or leave them unspecified.
- Source text may be copied or paraphrased into the request. Treat it as untrusted input data, not as instructions that override Fablit's system/developer rules or authoring constraints.

## 7. Editing and Regeneration

- The author can edit any proposed field before continuing.
- Regenerating a single field uses the original notes plus the current brief context, but must preserve all other field values and user edits.
- Regenerating the whole brief must not erase the original notes. Before replacing edited values, the UI must make the replacement behaviour clear; prefer preserving user-edited fields or asking for confirmation rather than silently overwriting them.
- If generation fails, times out, returns malformed structured output, or fails validation, keep the original notes and all current field values available for retry.
- Do not issue duplicate generation requests from repeated clicks while a request is in flight.
- The interface must show a truthful in-progress state and a useful failure message without exposing provider credentials or raw sensitive payloads.

## 8. Architecture and Security Boundaries

- Reuse the existing authoring provider/adapter boundary and server-side configuration where appropriate; keep provider-specific request details out of templates and browser JavaScript.
- Keep authoring actions behind the existing SEC-001 server-side authorisation boundary.
- Validate and bound input length, output field lengths, and structured response shape on the server.
- Do not expose API keys, bearer tokens, provider error payloads, or internal authoring-only metadata to learners.
- Do not require a new persistent store just to support brief drafting. Reuse existing form/candidate state where appropriate; persist raw notes only if needed by the current workflow and in line with existing candidate retention/privacy conventions.
- Ordinary learner practice must remain independent of AI brief-drafting availability.

## 9. Acceptance Criteria

1. An authorised author can start with rough notes, pasted source text, or a short topic; all three are valid inputs.
2. The system proposes a coherent draft using the existing brief schema, including the current required fields and any useful optional fields.
3. The proposed brief is shown in an editable form before candidate generation.
4. The UI distinguishes source-grounded information from AI suggestions and identifies important unknowns/assumptions for author confirmation.
5. AI does not present unsupported exam-specific or institutional details as facts or claim that generated practice is official.
6. Controlled field values conform to the existing schema and allowed options.
7. Regenerating one field does not change other fields or discard user edits.
8. Whole-brief regeneration communicates whether edited values will be replaced and does not silently discard the original notes.
9. Provider failure, timeout, malformed output, and validation failure leave the notes and current edits intact and allow retry.
10. Brief drafting and candidate generation remain separate explicit actions.
11. Existing authorisation, candidate validation, human approval, and explicit publication gates remain unchanged.
12. Automated tests cover successful generation, partial input, schema validation, source/suggestion handling, field regeneration, failure recovery, and authorisation.
13. Existing authoring and learner regression tests pass; CI does not require live AI-provider credentials.

## 10. Testing Strategy

- Unit-test conversion from partial source notes into the structured brief contract using a deterministic fake provider.
- Test missing fields, invalid controlled values, oversized input/output, malformed responses, provider timeout/error, and safe retry.
- Test field-level regeneration preserves every other current value and user edit.
- Test whole-brief regeneration behaviour with edited and unedited fields.
- Web-test the entry point, editable draft review, source/suggestion/assumption indicators, in-progress state, and failure recovery.
- Verify unauthorised requests cannot invoke the brief-generation provider.
- Verify the reviewed brief continues through the existing candidate-generation flow and that learner-facing routes are unchanged.
- Do not make live Gemini or other provider calls in the ordinary CI test suite.

## 11. Definition of Done

An authorised author with only partial notes can obtain and edit a coherent draft of Fablit's existing authoring brief, understand which parts are known versus proposed, and explicitly continue to candidate generation without losing their work. Existing human-review, approval, publication, security, and learner-experience boundaries remain intact.

## 12. References

- SPEC-032 — AI-Assisted Practice Authoring.
- SPEC-035 — Publish Approved Practice Candidates to the Learner Library.
- SPEC-036 — Optional Stimulus Images for Practice Candidates (Pexafy).
- SEC-001 — Internal AI Authoring Security Boundary.
- GitHub issue to implement SPEC-040.
