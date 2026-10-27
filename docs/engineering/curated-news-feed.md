# Curated Fashion & Design Pulse (SPEC-041)

The Fashion & Design Pulse is a small, curated feed of current fashion,
textiles, sustainability, Indian craft, design, and visual-culture stories for
all Fablit learners. It is deliberately **not** an unfiltered aggregator: a
source allowlist, deterministic checks, and AI curation keep the set relevant,
attributed, and safe.

This feature is separate from practice authoring and publication. It has its
own application workflow, its own AI port, and its own persistence boundary;
it never changes `AuthoringLlmProvider`, practice candidates, or the
practice-publication lifecycle.

## 1. Architecture

| Boundary | Location | Responsibility |
| --- | --- | --- |
| Application workflow | `fablit/application/news.py` | Allowlisting, normalization, deduplication, freshness, deterministic validation, publication decisions, batch reporting. |
| Source and URL rules | `fablit/application/news_sources.py` | Approved-source representation, HTTP(S) URL safety, publisher-host matching, fetcher port. |
| AI port | `fablit/application/news_curation.py` | Provider-neutral request/result types, controlled categories, deterministic fake provider. |
| Gemini adapter | `fablit/platform/gemini_news_curation_provider.py` | Server-side credentials, prompt construction, response parsing, provider failure translation. |
| Source fetcher | `fablit/platform/news_source_fetcher.py` | Bounded RSS/Atom retrieval, DNS/redirect safety, response-size limits, markup stripping. |
| Persistence port | `fablit/application/news.py` (`NewsRepository`) | News-specific storage contract with a deterministic in-memory implementation. |
| Datastore adapter | `fablit/platform/datastore_news_repository.py` | Durable production storage in kind `NewsStory`, namespace `news`. |
| Job lifecycle | `fablit/application/news_jobs.py` | Durable job model, job repository port with in-memory implementation, and the service that starts, executes, checkpoints, and recovers jobs. |
| Job storage adapter | `fablit/platform/datastore_news_job_repository.py` | Production job storage in kinds `NewsCurationJob` / `NewsCurationJobActive`, namespace `news`. |
| Task dispatch | `fablit/platform/cloud_tasks_dispatcher.py` | Enqueues one authenticated Cloud Tasks request per accepted job unit. |
| Task authentication | `fablit/platform/task_auth.py` | Verifies the Google-signed OIDC identity of a task request, independently of the author session. |
| Web surfaces | `app/news.py`, `app/templates/news.html`, `app/templates/authoring_news.html` | Learner feed, the protected on-demand curation page, job status routes, and the protected task handler. |

The learner route reads only persisted stories. It never calls Gemini, fetches
a source, or waits for curation, so an AI or network outage cannot break
ordinary practice or hide previously published stories.

## 2. Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `FABLIT_NEWS_REPOSITORY` | `memory` | `memory` for tests/local development, `datastore` for App Engine. |
| `FABLIT_NEWS_SOURCES` | The Guardian Fashion and Art & Design RSS feeds | JSON list of approved sources: `[{"name": "...", "feed_url": "https://...", "site_url": "https://..."}]`. `site_url` names the publisher host that story links must belong to. |
| `FABLIT_NEWS_MAX_ITEMS_PER_SOURCE` | `6` | Maximum items considered from each source in one refresh (1–50). |
| `FABLIT_NEWS_FRESHNESS_DAYS` | `14` | Oldest publication date eligible for publication. |
| `FABLIT_NEWS_MAX_SUMMARY_CHARS` | `600` | Longest curated summary accepted. |
| `FABLIT_NEWS_RELEVANCE_THRESHOLD` | `0.5` | Minimum provider relevance score (0–1). |
| `FABLIT_NEWS_FETCH_TIMEOUT` | `10.0` | Per-source fetch timeout in seconds. |
| `FABLIT_NEWS_MAX_RESPONSE_BYTES` | `512000` | Maximum bytes read from one feed. |
| `FABLIT_NEWS_MAX_SOURCES_PER_TASK` | `2` | Approved sources processed by one durable task unit (1–10). A larger batch is checkpointed and continued by further units. |
| `FABLIT_NEWS_TASK_DISPATCH` | `inline` | `inline` for local development and tests (runs the unit in the request, not durable), `cloud_tasks` in production. |
| `FABLIT_NEWS_TASK_QUEUE` | – | Full Cloud Tasks queue resource name, e.g. `projects/<project>/locations/<region>/queues/news-curation`. Required for `cloud_tasks`. |
| `FABLIT_NEWS_TASK_HANDLER_URL` | – | Absolute HTTPS URL of this application's `/tasks/news-curation` handler. Required for `cloud_tasks`. |
| `FABLIT_NEWS_TASK_SERVICE_ACCOUNT` | – | Service account Cloud Tasks uses to mint the task's OIDC token, and the only identity the handler accepts. Required for `cloud_tasks`. |
| `FABLIT_NEWS_TASK_AUDIENCE` | handler URL | Optional expected OIDC audience when it differs from the handler URL. |

News curation reuses the server-side Gemini configuration used by practice
authoring: `FABLIT_AI_PROVIDER_API_KEY` and `FABLIT_AI_PROVIDER_MODEL`. Without
an API key the curation action is unavailable, while the learner feed continues
to show persisted stories. No credential is ever exposed to browser code.

Set the source list explicitly in production to pin the publishers you have
reviewed:

```bash
gcloud app deploy app.yaml --set-env-vars \
  FABLIT_NEWS_SOURCES='[{"name":"The Guardian — Fashion","feed_url":"https://www.theguardian.com/fashion/rss","site_url":"https://www.theguardian.com"}]'
```

Empty `FABLIT_NEWS_SOURCES` disables fetching without deleting published
stories.

## 3. Source and content policy

- Only **absolute HTTP(S)** story links are accepted. URL credentials,
  non-default ports, loopback/private/link-local hosts, and local-only
  hostnames are refused.
- A story link must belong to the publisher host of the source that supplied
  it (or one of its subdomains). A feed cannot inject links for another site.
- Fetches are bounded by timeout and response size, and redirects are
  revalidated before they are followed.
- Each story keeps attribution (publisher name), a canonical link, the
  publication date when the source supplies one, a concise summary, controlled
  categories, a short educational-relevance note, and an optional reflection
  prompt.
- Only the minimal data needed to curate, attribute, and link a story is
  stored. Full article text, images, and large source excerpts are not
  persisted or rendered.
- Source content is untrusted. It is delimited in the provider prompt and the
  model is asked to ignore embedded instructions. Provider output is validated
  before publication.
- Stories with a missing, future, or stale publication date are rejected;
  Fablit never invents a date.
- AI summaries are rejected if their grounding terms do not occur in the
  fetched title/excerpt, if the category is outside the controlled set, if the
  relevance score is below the threshold, or if the copy uses learner
  measurement language (score, grade, mastery, streak, rank, urgency).

## 4. Durable curation jobs

Starting a refresh no longer runs the batch inside the author's request. The
server persists a **job** and returns its identity; a managed task then runs
the job. The browser does not own the work: navigating away, refreshing, or
closing the tab cannot cancel an accepted job.

### Lifecycle

| Status | Meaning |
| --- | --- |
| `queued` | Persisted and dispatched, waiting for a worker (or continuing after a checkpointed unit). |
| `running` | Leased to one worker, with a live lease and a reported stage. |
| `succeeded` | Finished; the batch report is persisted. |
| `partially_succeeded` | Finished; at least one source or candidate failed, and the report says which. |
| `failed` | The job could not run or was interrupted. A bounded, safe diagnostic is retained. |

Stages are reported only once the workflow reaches them: `queued`,
`fetching_sources`, `curating_items`, `finalizing_report`, then `done` or
`failed`. There is no invented percentage and no promised completion time.

Each job persists counters (sources configured/processed/failed, items
fetched/deduplicated/published/rejected/failed), the accumulated batch report
with its per-source and per-item safe reasons, and the attempt number.

### Execution and idempotency

- `POST /authoring/pulse/curate` persists the job **before** it is
  acknowledged and then dispatches it. A dispatch failure is persisted as a
  failed job and reported to the author; work is never reported as queued when
  it was not.
- The task handler (`POST /tasks/news-curation`) accepts only a Google-signed
  OIDC token issued to the configured task service account for this handler's
  audience. Author sessions and learner cookies are irrelevant there; an
  authenticated task cannot be started by a browser.
- A worker claims the job with a lease. A duplicate delivery while the lease
  is live is an accepted no-op, and a delivery after a terminal outcome
  returns the finished job without running anything again.
- Only one job may be queued or running at a time. A second start is refused
  while the current job is active.
- Execution is bounded: at most `FABLIT_NEWS_MAX_SOURCES_PER_TASK` sources per
  task unit. A larger batch is checkpointed (report, counters, next source
  index) and continued by a fresh unit, so no single request has to finish the
  whole batch.

### Recovery

- If a worker dies mid-unit, its lease expires and the next task delivery (or
  a retry) may take the job over; published stories are already idempotent by
  canonical URL, so no duplicate story is created.
- A running job whose lease has expired, and a queued job that has waited
  thirty minutes, no longer block a new start: the next start closes it as
  `interrupted` and accepts the new job.
- A failed or partial job never deletes or replaces existing stories.

### Cloud Tasks setup

1. Create the queue once:

   ```bash
   gcloud tasks queues create news-curation --location=europe-west1
   ```

2. Allow the App Engine runtime service account to enqueue:

   ```bash
   gcloud projects add-iam-policy-binding <project> \
     --member=serviceAccount:<project>@appspot.gserviceaccount.com \
     --role=roles/cloudtasks.enqueuer
   ```

3. Create (or reuse) a service account Cloud Tasks uses to sign task
   requests, and allow it to receive App Engine traffic:

   ```bash
   gcloud iam service-accounts create news-tasks --display-name="Fablit news tasks"
   ```

4. Set the deployment environment:

   ```bash
   gcloud app deploy app.yaml --set-env-vars \
     FABLIT_NEWS_TASK_DISPATCH=cloud_tasks \
     FABLIT_NEWS_TASK_QUEUE=projects/<project>/locations/europe-west1/queues/news-curation \
     FABLIT_NEWS_TASK_HANDLER_URL=https://<project>.appspot.com/tasks/news-curation \
     FABLIT_NEWS_TASK_SERVICE_ACCOUNT=news-tasks@<project>.iam.gserviceaccount.com
   ```

The handler rejects every request unless the configured audience and service
account are present, so an incomplete configuration fails closed rather than
running unauthenticated work. `cloud_tasks` mode also refuses to start without
the three required settings rather than silently falling back to in-request
execution.

## 5. Operating a weekly refresh

1. Sign in to the internal authoring workspace at `/authoring/login` with the
   configured `FABLIT_AUTHORING_SECRET`.
2. Open **Fashion & Design Pulse** in the authoring navigation
   (`/authoring/pulse`).
3. Review the configured source list and select **Curate this week's news**.
   The server returns a job identity and persists its status.
4. Leave, refresh, or return later. `/authoring/pulse` shows the current or
   most recent job; `GET /authoring/pulse/jobs/latest` and
   `GET /authoring/pulse/jobs/<job-id>` return the same persisted state as
   JSON. Both routes require the author credential.
5. Read the final report: fetched, already known (deduplicated), published,
   rejected, and failed. Rejected/failed items list the publisher, headline,
   and a short reason; raw provider payloads and secrets are never shown.
6. Published stories appear on `/pulse` as each eligible story is saved.

There is **no scheduler and no GitHub Actions workflow**. The batch runs only
when an authorised operator triggers it. Repeating the action is idempotent:
a story already stored for a canonical URL is counted as a duplicate and is not
written again. An overlapping start is refused while a job is queued or
running.

## 6. Failure behaviour

- A dispatch failure leaves a failed job and an honest message; nothing is
  reported as queued.
- A duplicate task delivery after a terminal outcome does nothing; a delivery
  during a live lease is a no-op. Only the lease holder executes.
- An interrupted worker is recovered once its lease expires, or closed as
  interrupted by the next start, so a job never stays running forever.
- A source that cannot be read does not stop the remaining sources.
- A provider error, timeout, malformed structured result, or failed validation
  never publishes the affected candidate.
- A failed, empty, or partial refresh never clears the existing feed: the
  workflow only writes eligible stories and never deletes.
- A storage write failure is reported as failed; the UI never claims a story
  was published unless the write succeeded.
- If the news store is unavailable, `/pulse` shows a calm unavailable/empty
  state and ordinary practice, history, and authoring remain usable.

### Gemini retry observability and safe diagnostics

When curating news with Gemini, transient failures (HTTP 429 Too Many Requests,
HTTP 503 Service Unavailable) are retried with exponential backoff and jitter,
honouring `Retry-After` headers bounded by `MAX_RETRY_DELAY_SECONDS` (10 seconds).
Non-retryable provider errors (such as HTTP 400 Bad Request or HTTP 401/403
authentication/permission errors) fail immediately without retrying.

The batch report and job status distinguish between transient retries and
terminal failure:

- **Provider outcomes**:
  - `ok`: All curated items succeeded without any retries.
  - `recovered`: Transient failures were encountered, but succeeded on a subsequent
    retry attempt.
  - `retries_exhausted`: One or more items exhausted their retry attempts on
    transient errors (HTTP 429 or 503).
  - `failed`: The provider failed with a non-retryable error (e.g. HTTP 400).
- **Retry counters and diagnostics**:
  - The job counters and batch report track `provider_retries` (the total count of
    retry attempts made across all items in the batch).
  - Structured `NewsCurationDiagnostics` report the provider identity, model,
    total `provider_retries`, `transient_retries_recovered`, `exhausted_retries`,
    `provider_outcome`, and the `last_status_code` seen on provider failure.
- **Leak prevention**:
  - Structured diagnostics and structured log entries strictly omit API keys,
    secrets, full prompt texts, and raw model payloads.
  - Failure summaries in reports and authoring copy remain bounded, high-level
    reasons (e.g. `curation provider retries exhausted (HTTP 429)` or `curation provider failed (HTTP 400)`).
- **Safe operator interpretation**:
  - When `provider_retries > 0` with `provider_outcome: recovered`, transient
    throttling or brief service interruptions were safely handled and the batch
    completed; no manual intervention is needed.
  - If `provider_outcome: retries_exhausted` (typically with HTTP 429), check
    Gemini quota and rate limits before initiating another refresh.
  - If `provider_outcome: failed` (with HTTP 400 or 401/403), check model
    configuration (`FABLIT_AI_PROVIDER_MODEL`) or API key validity
    (`FABLIT_AI_PROVIDER_API_KEY`).

## 7. Local development and tests

The test suite and local development use the in-memory story and job
repositories, the inline task dispatcher (which runs a task unit in the
request and is **not** a durability mechanism), `FakeNewsSourceFetcher`, and
`FakeNewsCurationProvider`. Task authentication is exercised through an
injected OIDC verifier. No test requires a live feed, a Gemini call, Cloud
Tasks, or Google Cloud credentials.

Relevant tests:

- `tests/application/test_news_curation.py` — validation, deduplication,
  freshness, safety, grounding, partial failures, idempotency, batch counts.
- `tests/test_news_source_fetcher.py` — RSS/Atom parsing, size limits, DNS and
  redirect safety, malformed payloads.
- `tests/test_gemini_news_curation_provider.py` — prompt delimiting, parsing,
  retry, and safe failure translation.
- `tests/application/test_news_jobs.py` — job invariants and transitions,
  atomic start/claim, dispatch success/failure, duplicate delivery, stale-lease
  takeover, bounded checkpoint/continuation, and safe failure diagnostics.
- `tests/persistence/test_datastore_news_job_repository.py` — job
  serialization, the active-job pointer, transactional claim, unindexed report
  storage, and storage failures.
- `tests/test_cloud_tasks_dispatcher.py` — task payload shape, OIDC token
  request, and safe failure translation.
- `tests/test_task_auth.py` — refused/unconfigured identities, audience and
  service-account checks, and non-leaking failures.
- `tests/persistence/test_datastore_news_repository.py` — Datastore
  serialization, unindexed free text, ordering, and storage failures.
- `tests/web/test_news_feed.py` — learner rendering/filtering/empty/outage
  behaviour and SEC-001 protection of the curation action.
- `tests/web/test_news_jobs_web.py` — durable start, job status, cross-instance
  visibility, and independent task-handler authentication.
