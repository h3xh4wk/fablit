# SPEC-042: Durable News Curation Jobs and Operational Visibility

**Status:** Proposed  
**Owner:** Fablit product  
**Related architecture:** ARCH-001, SEC-001, SPEC-041

## 1. Overview and goal

The Fashion & Design Pulse curation workflow currently runs synchronously inside the author's HTTP request. Although the workflow runs in a worker thread, it is not a durable background job. The page shows an in-progress label, but the author cannot reliably leave, refresh, or return later to inspect the same run. The current Gemini adapter also logs transient retry warnings; these warnings do not by themselves reveal whether the final attempt succeeded.

This SPEC makes curation a durable, observable job. An authorised author starts a run; the job continues independently of the browser request; and the author can return to see persisted status, progress, and the final batch report.

## 2. Product principles

- **The browser does not own the job.** Navigating away, refreshing, or closing the tab must not cancel accepted work.
- **Persist state, not just the final page response.** Status and progress must survive instance changes and new browser sessions.
- **Preserve publication safeguards.** Only candidates passing existing SPEC-041 validation may be published.
- **Be honest about progress.** Report observable stages and counters; do not invent a percentage when there is no reliable denominator.
- **Recover safely.** Retries and worker redelivery must not publish duplicate stories or mark unfinished work complete.
- **Keep the change proportionate.** Reuse the existing App Engine/Google Cloud deployment and Datastore patterns; do not add a separate application service or scheduler.

## 3. Current implementation findings

Repository review of main confirms:

- POST /authoring/pulse/curate calls NewsCurator.curate_batch through asyncio.to_thread, then renders the result in the same request.
- Overlapping runs are rejected with an in-process lock/error. That lock is not a durable cross-instance job coordinator.
- The last batch report is assigned to request.app.state.news_last_batch, which is process-local and can be lost on a new instance or restart.
- The authoring template uses a disabled button and HTMX indicator while the request is pending, but does not display durable job progress.
- GeminiNewsCurationProvider retries HTTP 429 and 503 responses up to three attempts, with a short backoff. The warning includes status code, attempt, and max attempts. Repeated warnings mean retries are being triggered; they do not prove the final attempt failed.

The learner feed and its existing source, grounding, freshness, URL-safety, validation, and publication checks must remain independent of this operational change.

## 4. Objectives

- Accept a curation request and return promptly with a durable job identifier.
- Run the accepted job independently of the author's HTTP connection and page lifecycle.
- Persist job state, progress counters, safe diagnostics, and the final batch result.
- Allow the author to leave the screen and later return to inspect the same job.
- Prevent accidental duplicate submissions and make task redelivery/retries safe.
- Improve visibility into Gemini throttling/service-unavailable retries without logging credentials or raw source/provider payloads.
- Preserve previously published stories and current automatic publication validation.

## 5. Author workflow

1. The authorised author opens /authoring/pulse and starts curation.
2. The server validates author access and request configuration before creating work.
3. The system persists a job record and schedules execution through a durable mechanism compatible with the existing App Engine deployment.
4. The page receives the job ID and displays a queued/running state. The author may navigate away, refresh, or close the tab.
5. When the author returns to /authoring/pulse, the page shows the latest job and provides a way to inspect its status and final report.
6. The job reports a terminal outcome: completed, completed with item/source failures, or failed. Safe failure details and existing batch counts remain available.
7. Starting another job while one is active must be explicitly handled; it must not silently create overlapping refreshes.

## 6. Job lifecycle and persistence

Introduce a news-curation job model and a news-specific persistence boundary, following existing Datastore adapter conventions. Production state must be shared across App Engine instances and survive process restarts. Tests and local development should use a deterministic in-memory implementation.

At minimum, persist:

- Stable job ID and creation/start/finish timestamps in UTC.
- Status: queued, running, succeeded, partially_succeeded, or failed.
- Progress stage and safe operator-facing message.
- Source/item counters where known: sources configured/processed/failed and items fetched/deduplicated/published/rejected/failed.
- The final safe batch report, including per-source and per-item safe reasons already supported by SPEC-041.
- Attempt/lease metadata needed to recover a worker interrupted during execution.
- A bounded error category/message; never credentials, raw provider payloads, or full untrusted article content.

Use explicit state transitions and validate them. An interrupted/stale running job must not remain running forever; provide a safe recovery/retry path. Do not delete or replace existing published stories when a job is retried or fails.

## 7. Durable execution and security

- Use a durable execution mechanism compatible with the current App Engine standard deployment and existing Google Cloud environment. Prefer managed task dispatch to a protected handler in the same application over introducing a separate worker service.
- Do not rely on a FastAPI background task, in-process thread, browser polling request, or in-memory lock as the durability guarantee.
- The task dispatch must be authenticated using an appropriate server-to-server mechanism. Do not treat caller-controlled headers alone as proof that a request came from the task service.
- Keep author-facing start/status endpoints behind SEC-001. Verify task-handler authentication independently from the author session.
- Persist the job before acknowledging acceptance. If durable dispatch fails, retain a truthful failure state and show a retryable message; never claim work was queued when it was not.
- Make execution idempotent. Duplicate task delivery must not cause duplicate stories, conflicting terminal states, or repeated finalization.
- Keep task execution bounded and compatible with platform request limits. If a batch cannot safely complete within one task, checkpoint progress and split work into bounded, resumable units rather than relying on an unlimited request.
- Do not introduce scheduled refreshes; the author still initiates each run on demand.

## 8. Progress and user interface

Replace the purely request-scoped spinner with a durable status view.

- Show queued/running/completed/partial/failed status in accessible text, not only animation or color.
- Show meaningful stages such as queued, fetching sources, validating candidates, curating eligible items, saving published stories, and finalizing the report, only when those stages reflect actual work.
- Display counters when available. Do not show a fabricated percentage or promise an exact completion time.
- Poll or refresh job status using a bounded, lightweight mechanism while the author is on the page; stop polling at terminal status and handle temporary status-fetch failures without cancelling the job.
- On page load, show the current/most recent job so refresh and return-to-page are safe.
- Keep a clear final report with fetched, deduplicated, published, rejected, and failed counts and safe failure reasons.
- Use accessible status announcements and respect reduced-motion preferences.
- Do not expose job details to unauthorised users or learners.

## 9. Gemini retry observability

The current adapter retries HTTP 429 and 503 responses up to three attempts and logs a warning before retrying. Improve observability while preserving safe retry behaviour:

- Retain structured status code, attempt, and maximum-attempt fields.
- Record retry counts and final outcome in job-level diagnostics or counters, without exposing provider payloads or secrets.
- Where supported and safe, respect provider retry guidance such as Retry-After and keep total waiting bounded by configured/platform limits.
- Make final exhaustion distinguishable from a transient warning that was successfully recovered.
- Do not retry non-retryable HTTP statuses indiscriminately. Add deterministic tests for 429/503 success-after-retry, exhausted retries, non-retryable errors, and safe logging.
- Do not claim the current warnings identify a single root cause: the logged status code is needed to distinguish throttling (429) from service unavailability (503).

## 10. Failure and recovery behaviour

- Browser disconnects, navigation, refreshes, or closing the tab must not cancel an accepted job.
- A temporary status endpoint failure must not change job state.
- A dispatch failure must not leave a falsely queued job.
- Task redelivery must be safe and idempotent.
- An interrupted worker must leave enough persisted information to identify and recover the job.
- A provider/source failure for one candidate/source must follow existing SPEC-041 partial-failure behaviour; other eligible work should continue where feasible.
- A failed or partial run must preserve existing stories and report actual outcomes.
- If a job fails before producing a batch report, show a safe failure state and retain enough diagnostic context for the operator to retry.
- Do not automatically retry an entire batch in a way that duplicates completed work or repeats expensive provider calls unnecessarily.

## 11. Testing and verification

Use injected task dispatchers, clocks, repositories, and provider transports; normal tests must not require live Gemini calls or production cloud credentials.

Cover at least:

- Job model validation and allowed state transitions.
- Job persistence and retrieval across separately constructed application/service instances.
- Durable enqueue success/failure and truthful API responses.
- SEC-001 author access and independent task-handler authentication.
- Browser/page lifecycle independence: accepted jobs remain available after a fresh request/application view.
- Idempotent execution under duplicate task delivery and concurrent start requests.
- Stale-running recovery and terminal-state consistency.
- Progress counter/stage updates and final batch report persistence.
- Status UI on initial load, refresh, return visit, terminal outcomes, and temporary polling failures.
- HTTP 429/503 retries, final exhaustion, non-retryable failures, and safe structured diagnostics.
- Existing SPEC-041 validation/publication safeguards, story idempotency, and preservation of existing stories.
- Existing authoring, learner feed, practice, and history regression suites.

## 12. Documentation

Update only relevant documentation to explain the durable job lifecycle, how to start/inspect a run, required Google Cloud task dispatch configuration/IAM if used, status meanings, retry behaviour, recovery, and safe failure diagnostics. Document local testing with deterministic fake dispatch and repositories.

Do not introduce unrelated UI redesign, new source providers, story images, or personalized learner practice in this SPEC.

## 13. Non-goals

- Scheduled or automatic periodic curation.
- A separate worker application/service or a new cloud platform.
- Replacing the existing SPEC-041 source allowlist, validation rules, or publication model.
- Changing practice-authoring provider semantics or practice publication.
- Learner accounts, personalization, comments, notifications, or learner-facing AI.
- Redesigning the learner Stories page or adding publisher images/source-link authoring.
- Guaranteeing zero transient provider errors; the goal is bounded retry, recovery, and accurate observability.

## 14. Acceptance criteria

1. An authorised author can initiate curation and receive a durable job ID without waiting for the entire batch.
2. Once accepted, the job continues if the author navigates away, refreshes, or closes the browser.
3. Job status, progress, counters, and final report are persisted and visible after returning to the authoring page or reaching another App Engine instance.
4. Durable execution does not depend on an in-process thread/background task or process-local state.
5. Duplicate starts and task redelivery are handled safely and idempotently.
6. Task execution is independently authenticated; learner and unauthorised requests cannot read or control jobs.
7. The UI displays honest, accessible progress and terminal outcomes without fabricated percentages.
8. Existing source checks, validation, and automatic publication gates remain unchanged; existing stories survive partial/failed runs.
9. Gemini retry diagnostics distinguish transient retries from exhausted failures, record safe structured details, and are covered by deterministic tests.
10. Tests verify job lifecycle, dispatch/recovery, security, status UI, retry behaviour, and existing regressions without live AI/cloud credentials.
11. Relevant operational documentation is updated and quality gates pass.

## 15. Definition of done

The durable job lifecycle is implemented behind existing application boundaries; production job state and dispatch are durable and authenticated; author progress survives browser and instance changes; provider retry outcomes are observable without secret leakage; deterministic tests pass; and the change is ready for the established review/deployment workflow. Deployment is not performed automatically by this SPEC.
