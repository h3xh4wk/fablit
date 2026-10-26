# SPEC-041: Curated Fashion & Design Intelligence Feed

**Status:** Proposed  
**Owner:** Fablit product  
**Related architecture:** ARCH-001, SEC-001, SPEC-032, SPEC-035, SPEC-040

## 1. Overview and goal

Fablit learners preparing for fashion and design entrance examinations need a manageable way to connect current developments in fashion, textiles, sustainability, Indian craft traditions, and visual culture with observation, design awareness, and creative thinking.

SPEC-041 introduces a curated Fashion & Design Pulse feed for all learners. A protected, on-demand action in the existing internal authoring workspace fetches and curates a weekly batch of relevant stories using approved sources and AI. Candidates are published automatically only after deterministic validation succeeds. Learners browse the persisted feed without invoking AI.

The initial operating model is deliberately **on demand**, not a scheduled background job: an authorised operator clicks a button when they want to refresh the weekly batch. Do not introduce GitHub Actions scheduling, a separate scheduler service, or new cloud infrastructure for this feature.

## 2. Product principles

- **Curate, don't aggregate blindly.** Prefer a small, relevant set of stories with an educational connection over a high-volume stream.
- **Current events should support learning.** Explain why a story matters to fashion/design learners and, where appropriate, suggest a brief observation or reflection prompt.
- **Automatic publication follows explicit checks.** There is no per-story human approval step in the initial version, but validation failures must prevent publication.
- **Keep authoring and news separate.** Reuse useful infrastructure, not practice-authoring semantics or data models.
- **Learner browsing is independent of AI availability.** Previously published stories remain available if curation fails.
- **Respect publishers and readers.** Attribute original sources, link to them, and do not republish full articles or unlicensed imagery.

## 3. Objectives

- Offer all Fablit learners a concise, useful feed of current fashion/design news and visual-culture developments.
- Use AI to classify, summarize, assess educational relevance, and optionally propose a short reflection/practice prompt.
- Provide one protected, on-demand “Curate this week’s news” action in the existing authoring workspace.
- Automatically publish only stories that pass source, freshness, schema, relevance, and safety validation.
- Persist stories in the existing Google Cloud Datastore infrastructure through a news-specific persistence boundary.
- Keep the learner feed readable from persisted content without requiring a live AI call.
- Make source failures, invalid output, and partial refreshes observable and recoverable.

## 4. Initial content scope

Include stories relevant to one or more of:

- Fashion industry, designers, collections, retail, and fashion business.
- Textiles, fibres, materials, manufacturing, and material innovation.
- Sustainability, circular design, repair, reuse, and responsible production.
- Indian crafts, handloom, artisans, regional traditions, and contemporary craft practice.
- Product, graphic, communication, and fashion design.
- Architecture, visual culture, exhibitions, and adjacent creative developments where the educational connection is clear.

Use a configurable allowlist of sources. Start with a small set of sources whose feeds or pages can be fetched reliably and whose reuse terms are understood. Source selection must be explicit and documented; do not make arbitrary web search or an MCP service a required production dependency.

## 5. Operator workflow and publication lifecycle

### 5.1 Protected on-demand action

- Add a “Curate this week’s news” action to the existing protected internal authoring workspace, using the established SEC-001 access boundary.
- The action runs a bounded refresh operation on demand. It must not run merely because a learner opens the feed.
- Reuse the existing server-side Gemini configuration and Datastore application credentials where practical; never expose secrets to browser code or persist them in source.
- Do not add GitHub Actions workflows, scheduled automation, or a separate scheduler for this feature.
- The workflow must return a clear batch result: fetched, deduplicated, accepted/published, rejected, and failed counts, plus safe, actionable failure information. Do not expose provider credentials or raw untrusted payloads in errors.
- Protect against accidental repeated submissions and overlapping refresh operations where practical. Repeated runs must be idempotent.

### 5.2 Curation and automatic publication

The application-level workflow should perform these steps:

1. Fetch from configured, approved sources with bounded timeouts and response sizes.
2. Normalize records and canonical URLs; reject unsafe URLs and unsupported schemes.
3. Deduplicate against the current batch and persisted stories.
4. Apply deterministic checks for source allowlisting, required fields, publication-date reliability, freshness, length limits, and source attribution.
5. Send bounded, relevant source content to the provider-neutral news-curation port.
6. Validate the structured AI response and its relationship to the source evidence.
7. Reject candidates that are invalid, stale, duplicate, unsafe, insufficiently relevant, or inadequately grounded.
8. Automatically persist and publish candidates that pass every required check.
9. Report the outcome of the batch without removing existing published stories because a source or candidate failed.

There is no per-story human approval step in the initial release. “On demand” refers to the operator initiating a batch; it does not mean the operator must approve every story individually. The UI should make the batch result visible and distinguish published stories from rejected/failed candidates in its summary.

### 5.3 Failure behaviour

- A failed source must not prevent other configured sources from being processed.
- A provider error, malformed response, timeout, or failed validation must not publish the affected candidate.
- An empty or failed refresh must not clear the existing feed.
- Persistence errors must be reported; the UI must not claim a story was published unless its write succeeded.
- Learners continue to browse previously persisted stories if the provider or refresh operation is unavailable.

## 6. Architecture boundaries

### 6.1 Application workflow

Introduce a focused news-curation application module or equivalent service that owns orchestration, normalization, deduplication, deterministic validation, publication decisions, and batch reporting. It must not import Gemini SDKs, Datastore SDKs, FastAPI request objects, or credential-management code.

Inspect the repository's existing patterns before deciding exact modules and names. Keep business rules testable without network calls.

### 6.2 AI provider boundary

- Inspect `fablit/application/authoring_llm.py`, `fablit/platform/gemini_authoring_provider.py`, and configuration in `fablit/config.py`.
- Define a dedicated provider-neutral news-curation port and request/result types for classification, summary generation, educational relevance, and an optional reflection/practice prompt.
- Reuse compatible Gemini adapter/client/configuration infrastructure where practical, but keep news curation behind its own port.
- Do not change or overload `AuthoringLlmProvider`, `BriefDraftingRequest`, or practice-authoring result semantics merely to support news.
- Keep provider SDK usage, authentication, request construction, parsing, and provider-specific errors in the platform adapter.
- Supply a deterministic fake provider for tests and local development. Tests must not require a live Gemini API call or credentials.
- Retain provider/model and curation timestamp provenance as appropriate for operational debugging, without exposing secrets.

### 6.3 Persistence boundary

- Use the existing Google Cloud Datastore infrastructure and adapter conventions for durable production news records.
- Add a narrow, news-specific repository port in the application layer, with an in-memory implementation for tests/local development and a Datastore-backed adapter for production.
- Inspect existing Datastore repository and published-store patterns before designing keys, entities, indexes, and configuration.
- Keep news records separate from `PracticeHistoryRepository` and `PublishedPracticeStore`. Do not repurpose learner history or published-practice entities.
- Use stable story identity and canonical URL deduplication so repeated refreshes do not create duplicate stories.
- Preserve existing records when a refresh partially fails. Avoid destructive “replace the whole feed” writes.
- Use the App Engine application's existing server-side Google credentials/IAM model where applicable; do not introduce GitHub credentials or a separate identity system for this feature.

## 7. News item contract

Each persisted/published story should contain, at minimum:

- Stable story identifier.
- Headline/title.
- Canonical source URL and source/publisher name.
- Original publication timestamp when reliably available; do not invent one.
- Retrieval timestamp and curation timestamp.
- Concise AI-generated summary.
- One or more controlled categories/tags.
- Short explanation of relevance to fashion/design learners.
- Optional reflection or practice prompt.
- Curation provider/model provenance where available.
- Validation/publication status and enough metadata to support idempotency and troubleshooting.

Keep source excerpts and prompt payloads bounded. Avoid storing full article text unless the source's terms and a clear need justify it; the default should be only the minimal data needed to curate, attribute, and link the story.

## 8. Source, content, and AI safety

- Configure an explicit source allowlist and accept only expected HTTP(S) source links.
- Validate redirects and final destinations to reduce server-side request forgery risk; block private, loopback, link-local, and unsupported destinations where applicable.
- Set connection/read timeouts, response-size limits, and bounded per-source item counts.
- Treat fetched content as untrusted data, never as instructions. Delimit it in provider requests and instruct the model to ignore embedded commands.
- Require structured output with bounded field lengths and allowed categories.
- Validate summaries and educational claims against the fetched source. Do not invent names, events, dates, quotes, or facts.
- Display attribution, publisher, date when known, and a link to the original story.
- Do not reproduce complete articles, large source excerpts, publisher photos, or other copyrighted material without permission. Do not add images unless licensing and attribution are explicitly supported.
- Escape all source and model-generated text in templates; validate link targets before rendering.

## 9. Learner experience

- Add a learner-facing Fashion & Design Pulse/news feed to the existing Fablit UI, consistent with its established layout and accessibility patterns.
- Feed is available to all learners; no login, account, or personalization is introduced.
- Each story card should show headline, concise summary, source attribution, publication date if known, category, and educational relevance. Show the optional reflection/practice prompt when available.
- Display newest stories first and provide lightweight category filtering if this fits existing UI conventions.
- The feed reads only persisted approved/published news records. Rendering must not invoke Gemini, fetch external sources, or wait on the curation workflow.
- If no stories have been published yet, show a useful empty state. If the news store is temporarily unavailable, fail gracefully without breaking ordinary practice.
- The feature must not make ordinary learner practice or history dependent on the news subsystem.

## 10. Configuration and operations

Inspect current configuration conventions and add only settings that are necessary, such as:

- News feature enablement and source allowlist.
- Maximum items per source/batch, freshness window, field/response limits, and relevance threshold.
- News-curation provider/model selection where it cannot safely reuse existing provider configuration.
- News repository backend selection following existing memory/Datastore conventions.

Document required source configuration, server-side Gemini configuration, Datastore permissions, how to access the protected authoring action, how to trigger a weekly refresh manually, and how to interpret the batch result. Avoid adding an independent credentials-management mechanism.

## 11. Testing and verification

Use deterministic fakes and injected transports; no live sources, Gemini calls, or production cloud credentials in the normal test suite.

Cover at least:

- Source normalization, allowlisting, URL safety, timeout/size limits, malformed responses, and partial source failures.
- Canonical URL and content deduplication across repeated runs.
- Freshness/date handling and rejection of missing or unreliable metadata according to policy.
- Provider schema validation, grounding/relevance checks, and malicious instructions embedded in source content.
- In-memory and Datastore repository contract behaviour, serialization/backward compatibility if relevant, and persistence failures.
- Idempotent refresh and prevention/handling of repeated or overlapping operator actions.
- Only validated candidates are published; failed candidates never leak into the learner feed.
- A failed/empty batch preserves existing published stories.
- SEC-001 blocks unauthorised curation before any network or AI call.
- Learner feed rendering, category filtering, safe link rendering, empty state, and graceful store/provider outage behaviour.
- Existing authoring, practice publication, learner practice, and history tests remain unchanged and pass.

## 12. Documentation

Update relevant documentation, based on repository conventions, to describe:

- The feature and its separation from practice authoring/publication.
- The provider-neutral news-curation port and Gemini adapter.
- The news-specific persistence boundary and Datastore configuration.
- Source allowlist, content attribution, and safety expectations.
- The protected on-demand weekly workflow and operational batch results.
- Local testing using fakes and production prerequisites.

Do not update unrelated documentation or introduce a separate architecture service unless repository inspection demonstrates it is necessary.

## 13. Non-goals

- GitHub Actions scheduling or any scheduled background job.
- A separate scheduler, worker service, queue, or new cloud platform.
- Mandatory MCP integration or a mandatory external search API.
- A full content-management/editorial system.
- Human approval of every individual story.
- Reposting full publisher articles or unlicensed images.
- Learner accounts, personalization, social features, comments, or notifications.
- Real-time/breaking-news guarantees.
- A learner-facing chatbot or live AI interactions.
- Changes to practice-authoring provider semantics, candidate approval, or practice publication lifecycle.
- Changes to production deployment or the established offline production publishing process beyond the explicitly approved, SEC-001-protected news operation.

## 14. Acceptance criteria

1. An authorised operator can initiate a bounded weekly news-curation batch from the existing protected authoring workspace.
2. The operation is on demand; no GitHub Actions schedule or separate scheduler is introduced.
3. The application layer owns the workflow and depends on a dedicated provider-neutral news-curation port.
4. The existing practice-authoring provider contract remains unchanged.
5. Gemini is reused behind the new curation port where practical, with credentials and provider details server-side.
6. Stories are automatically published only after all required source, safety, freshness, schema, grounding, and relevance checks pass.
7. A batch summary accurately reports fetched, deduplicated, published, rejected, and failed counts without leaking secrets or untrusted raw payloads.
8. Stories are persisted through a news-specific repository port using existing Datastore infrastructure in production and an in-memory fake for tests/local development.
9. Repeated runs are idempotent and existing published stories survive failed or empty refreshes.
10. The learner feed displays persisted, attributed stories and remains usable when curation/AI is unavailable.
11. Unauthorised requests cannot initiate fetching or AI calls; all authoring operations remain behind SEC-001.
12. Tests cover the required success, failure, safety, persistence, and learner-facing behaviours without live network/AI/cloud credentials.
13. Required configuration and operational documentation are updated, and existing quality gates pass.

## 15. Definition of done

- Implementation follows the repository's established application/adapter boundaries.
- New tests are deterministic and existing regression tests pass.
- Source, attribution, and AI safety requirements are enforced before publication.
- Documentation describes setup, operation, and failure behaviour.
- The feature is ready for the existing review and deployment workflow; deployment is not performed automatically by this specification.
