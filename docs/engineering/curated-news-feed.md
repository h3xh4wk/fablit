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
| Web surfaces | `app/news.py`, `app/templates/news.html`, `app/templates/authoring_news.html` | Learner feed and the protected on-demand curation page. |

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

## 4. Operating a weekly refresh

1. Sign in to the internal authoring workspace at `/authoring/login` with the
   configured `FABLIT_AUTHORING_SECRET`.
2. Open **Fashion & Design Pulse** in the authoring navigation
   (`/authoring/pulse`).
3. Review the configured source list and select **Curate this week's news**.
4. Read the batch summary: fetched, already known (deduplicated), published,
   rejected, and failed. Rejected/failed items list the publisher, headline,
   and a short reason; raw provider payloads and secrets are never shown.
5. Published stories appear immediately on `/pulse`.

There is **no scheduler and no GitHub Actions workflow**. The batch runs only
when an authorised operator triggers it. Repeating the action is idempotent:
a story already stored for a canonical URL is counted as a duplicate and is not
written again. Overlapping submissions are refused while a refresh is running.

## 5. Failure behaviour

- A source that cannot be read does not stop the remaining sources.
- A provider error, timeout, malformed structured result, or failed validation
  never publishes the affected candidate.
- A failed, empty, or partial refresh never clears the existing feed: the
  workflow only writes eligible stories and never deletes.
- A storage write failure is reported as failed; the UI never claims a story
  was published unless the write succeeded.
- If the news store is unavailable, `/pulse` shows a calm unavailable/empty
  state and ordinary practice, history, and authoring remain usable.

## 6. Local development and tests

The test suite and local development use the in-memory repository,
`FakeNewsSourceFetcher`, and `FakeNewsCurationProvider`. No test requires a
live feed, a Gemini call, or Google Cloud credentials.

Relevant tests:

- `tests/application/test_news_curation.py` — validation, deduplication,
  freshness, safety, grounding, partial failures, idempotency, batch counts.
- `tests/test_news_source_fetcher.py` — RSS/Atom parsing, size limits, DNS and
  redirect safety, malformed payloads.
- `tests/test_gemini_news_curation_provider.py` — prompt delimiting, parsing,
  retry, and safe failure translation.
- `tests/persistence/test_datastore_news_repository.py` — Datastore
  serialization, unindexed free text, ordering, and storage failures.
- `tests/web/test_news_feed.py` — learner rendering/filtering/empty/outage
  behaviour and SEC-001 protection of the curation action.
