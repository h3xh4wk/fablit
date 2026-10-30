# SPEC-044: Learner-Requested Personalised Practice

**Status:** Proposed  
**Owner:** Fablit product  
**Related architecture:** ARCH-001, SEC-001, SPEC-021, SPEC-024, SPEC-029, SPEC-030, SPEC-032, SPEC-034, SPEC-035  
**Related roadmap:** Stage 3 — Reader-requested personalised practices

## 1. Overview and goal

Allow a learner to request a practice activity based on a learning need, topic, difficulty preference, or area they want to explore. Fablit should use the learner's own practice history as optional context to make the request more relevant, while keeping the learner in control of what is shared and what is generated.

This is a distinct learner-facing capability from SPEC-032. SPEC-032 uses AI as an internal authoring assistant and requires human review before content enters the shared curated library. SPEC-044 introduces a bounded, learner-requested, private practice journey. A generated practice is private to the requesting learner; it is not automatically approved or published to the shared library.

The experience must remain anonymous-first. It must use the existing learner identity and private history boundaries, the existing practice content and feedback contracts, and the existing provider-neutral AI architecture. It must not become an unrestricted AI tutor, open-ended chatbot, or unreviewed public content generator.

## 2. Product principles

1. **Learner intent comes first.** Generation begins only after an explicit learner request.
2. **History is context, not a profile.** Use relevant practice history to avoid repetition and support continuity; do not infer ability, motivation, personality, or future performance.
3. **Private by default.** A generated practice belongs only to the requesting learner and must not enter the shared curated library automatically.
4. **Quality boundaries remain.** Generated practice must satisfy the existing Practice Content Contract (SPEC-029) and Feedback Contract (SPEC-030), with deterministic validation before it is offered.
5. **No false assessment.** Do not introduce scores, grades, mastery labels, rankings, streaks, or unsupported claims about learner ability.
6. **Graceful failure.** A generation or provider failure must not affect the existing curated library, completed history, or normal practice journey.
7. **Bounded AI use.** The request, context, output size, retries, and generation rate must be bounded and observable.

## 3. Goals

- Let learners request a focused practice in their own words.
- Offer a small number of useful, structured request controls where they reduce ambiguity, without making the learner complete a lengthy authoring brief.
- Use a relevant, minimal subset of the current learner's practice history as optional generation context.
- Support practice areas beyond the existing creative-ability activities, with aptitude and English as candidate areas for initial coverage.
- Generate a structured practice compatible with the existing learner practice representation and journey.
- Validate generated content and its evaluation/feedback guidance before the learner starts.
- Persist generated practices privately and durably for the requesting learner.
- Let learners return to an unfinished or completed generated practice through their own history/library journey.
- Make it clear when a practice was generated on request and that it is private to that learner.

## 4. Non-goals

- Replacing the shared curated practice library or SPEC-032 authoring/review workflow.
- Automatically publishing learner-generated content to the shared library.
- An unrestricted AI tutor, chat interface, or continuous conversational agent.
- Generating practices without an explicit learner action.
- Building a learner score, ability profile, mastery model, ranking, streak, or recommendation engine.
- Inferring personal characteristics, motivation, mental state, or exam success probability.
- Requiring learner registration, email, password, or social login.
- Cross-device recovery or account linking unless introduced by a separate specification.
- Allowing arbitrary uploaded personal data to be sent to an AI provider.
- Replacing the existing practice submission, evaluation, feedback, reflection, completion, or history model.

## 5. Learner journey

The intended high-level flow is:

```
Learner opens "Request a practice"
        ↓
Learner describes what they want to practise
        ↓
Learner optionally chooses an area / format / challenge preference
        ↓
Fablit gathers minimal relevant context from this learner's history
        ↓
Bounded generation request
        ↓
Structural + content + feedback validation
        ↓
Private generated practice is persisted for this learner
        ↓
Learner reviews the brief and chooses to begin
        ↓
Existing practice journey
        ↓
Completion and private history
        ↓
Learner can return to the generated practice or request another
```

Generation and validation must complete before a practice is offered. A failed or invalid candidate must not appear as a usable practice.

## 6. Request contract

The request should be short and learner-friendly. It may include:

- A free-text description of what the learner wants to practise.
- An optional practice area (for example: creative ability, aptitude, English, visual analysis, communication, or another supported area).
- Optional examination context.
- Optional preferred response format or practice mode, where supported.
- Optional challenge preference expressed in plain language (for example: introductory, familiar, or more challenging).

Do not require every field. The free-text request should be sufficient for a reasonable default when it is clear. Ask for clarification only when the request is too ambiguous to produce a coherent and safe practice.

Validate and bound all learner input before provider invocation. Reject unsupported or excessively long input with actionable, non-technical feedback.

## 7. Use of learner history

- Resolve the learner identity through the existing anonymous learner-session boundary (SPEC-024).
- Query only the current learner's own persisted practice history.
- Use a minimal, relevant selection of prior practice context, such as recently completed activity identifiers/titles, practice areas, and concise learner-provided response/reflection context only where necessary and appropriate.
- Prefer structured summaries over transmitting full historical submissions or private artifacts.
- Never access or include another learner's history.
- Do not send sketchbook image bytes or private artifact contents as generation context.
- Make history-informed tailoring transparent in plain language and allow the learner to request a practice without using history where feasible.
- Do not infer or store a persistent learner profile, ability score, mastery state, or psychological/personality attributes.
- Define and test retention and deletion behavior for private generated practice records consistently with existing learner-history privacy boundaries.

## 8. Generation and validation

### 8.1 Architecture

- Use the existing provider-neutral AI/LLM port and server-side provider configuration.
- Keep provider-specific request/response handling in platform adapters.
- Keep generation orchestration, request validation, context selection, and candidate validation in the application layer.
- Do not place provider credentials or direct provider calls in browser code.
- Do not make the learner-facing request depend on the internal authoring UI or expose authoring credentials/workflows.

### 8.2 Generated practice contract

A generated practice must map to the existing learner-facing practice representation. It must define, as applicable:

- title and concise purpose;
- clear learner-facing task;
- practice area and relevant examination context;
- intended response form and bounded response requirements;
- stimulus/context requirements and validated stimulus reference if needed;
- expected thinking or observable response evidence;
- evaluation intent and feedback guidance;
- reflection intent and optional continuation guidance;
- supported practice mode.

Do not create a parallel learner practice model if the existing content contract can represent the activity. If the current contract cannot safely represent a requested area (for example, a new aptitude or English task type), document the precise gap and extend the shared contract deliberately rather than bypassing validation.

### 8.3 Validation gates

Before persistence and learner access, validate:

- required fields, supported types, modes, and bounded lengths;
- coherence between learner request, practice area, task, response form, and evaluation;
- actionable and fair evaluation/feedback guidance aligned with SPEC-030;
- suitability for the learner's stated context without unsupported assumptions;
- safe external links and stimulus metadata, where applicable;
- absence of prohibited grading, scoring, mastery, ranking, or ability claims;
- output size and provider response constraints.

Invalid output must be rejected safely. Do not silently repair materially invalid content into a learner-facing practice.

## 9. Private persistence and lifecycle

- Introduce a learner-scoped persistence boundary for generated practices, or extend an existing boundary only where its semantics remain clear.
- Store ownership using the existing opaque `learner_id`; never put learner identity or private content into public URLs.
- Persist enough validated content and provenance to reproduce the exact practice the learner was offered, even if the generation provider later changes or becomes unavailable.
- Record safe provenance such as request time, provider/model identifier, validation outcome, and source request identifier; do not persist secrets or raw provider payloads.
- Make generation retries idempotent or otherwise prevent duplicate private practices when a request is retried.
- Define lifecycle states sufficient to distinguish requested/generating, ready, failed, started, and completed where needed. Avoid a large workflow engine for a single bounded interaction.
- A generated practice must not be visible to other learners, discoverable in the shared library, or publishable without a separate explicit authoring/review process.
- Persist and resume a generated practice using the same learner journey and completion/history boundaries as other practices.
- A learner must be able to return to the same generated practice without regenerating it.

## 10. Learner experience

- Add a clear entry point from the existing learner experience without obscuring the curated practice library.
- Keep the request flow short and mobile-friendly.
- Explain that generation may take a short time and provide a useful retry path when it fails.
- Show the generated practice brief before the learner starts; generation must not automatically begin a timed or active practice.
- Identify it as a learner-requested practice and explain that it is private to the learner.
- Provide an intentional empty state and a clear return path for previously generated practices.
- Preserve the current warm-neutral editorial visual language and accessibility conventions.
- Do not use gamification or pressure-oriented copy.

## 11. Reliability, security, and operations

- Bound provider calls by timeout, output tokens/size, retry count, and per-learner request rate.
- Apply abuse protection without requiring registration or exposing internal learner identifiers.
- Treat learner text and model output as untrusted input; escape rendered content and validate links/stimuli.
- Do not expose prompts, provider payloads, API keys, or internal exception details to learners.
- Log operational outcomes with correlation identifiers and safe failure categories, not full learner submissions or sensitive context.
- A provider outage must leave curated practices, Pulse, and existing history usable.
- Ensure persistence failures are reported honestly; do not tell a learner a practice is saved when it is not.
- Follow existing SEC-001 and privacy conventions for protected internal authoring routes; learner routes remain anonymous and public.

## 12. Acceptance criteria

- [ ] A learner can submit a concise request without completing a long authoring form.
- [ ] Optional request fields have safe defaults and unsupported combinations receive actionable feedback.
- [ ] Generation starts only from an explicit learner action.
- [ ] History context is restricted to the current learner and is minimal/relevant.
- [ ] The learner can opt out of history-informed context where feasible.
- [ ] No cross-learner history or private artifact content is exposed to the generation workflow.
- [ ] Generated content passes deterministic structural and content validation before it is offered.
- [ ] Feedback/evaluation guidance aligns with SPEC-030 and does not assign grades or infer ability.
- [ ] A generated practice uses the existing learner practice journey and compatible content representation.
- [ ] A validated generated practice is durably persisted and private to its requesting learner.
- [ ] Retrying a request does not create unintended duplicate records.
- [ ] The learner can return to the exact generated practice without regenerating it.
- [ ] Generated practices do not enter the shared curated library or become visible to other learners.
- [ ] Provider failure, invalid output, timeout, and persistence failure are handled without disrupting normal practice.
- [ ] Request limits, output bounds, safe diagnostics, and server-side credentials are covered by tests.
- [ ] Tests cover two learners, history isolation, history opt-out, generation validation, persistence/reconstruction, retry/idempotency, and the complete learner journey.
- [ ] Existing curated-library, practice-history, and authoring workflows continue to pass their regression suites.
- [ ] The experience is manually reviewed on mobile and desktop and is accessible by keyboard.

## 13. Implementation guidance

Begin with a focused architecture review of the current practice content contract, learner-session registry, history repository, published-practice catalogue, AI provider port, and learner routes. Decide whether generated private practices can be represented as a distinct source in the existing learner catalogue or require a narrow learner-private repository. Keep shared publication and private learner generation explicitly separate.

Implement in vertical slices: request UX and validation; context selection; generation and validation; private persistence and retrieval; integration with the existing practice journey; operational safeguards and end-to-end tests. Do not expand into cross-device identity, general chat, broad learner analytics, or a new content-management system within this specification.
