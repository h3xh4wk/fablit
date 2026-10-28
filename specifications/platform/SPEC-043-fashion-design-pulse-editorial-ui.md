# SPEC-043: Fashion & Design Pulse Editorial UI and Source Attribution

**Status:** Proposed  
**Owner:** Fablit product  
**Related architecture:** ARCH-001, SEC-001, SPEC-036, SPEC-041, SPEC-042  
**Tracking issue:** [#173 — SPEC-043: Fashion & Design Pulse Editorial UI and Source Attribution](https://github.com/h3xh4wk/fablit/issues/173)

## 1. Overview and goal

Improve the Fashion & Design Pulse experience with a more visual, editorial presentation and clear source attribution, while preserving the reliable persisted-news workflow introduced by SPEC-041 and SPEC-042.

Reuse the existing provider-neutral image-search abstraction and configured Pexafy adapter from practice authoring rather than building a parallel image-search integration. During news curation, derive a concise visual query from the story, retrieve a bounded set of candidates, and select a suitable image automatically using relevance and visual-suitability checks. Persist the selected image and its provenance with the story. Imagery is optional: if search, selection, or persistence cannot provide a safe suitable image, the story remains usable as text-only. Image search must never run when a learner opens the feed.

The learner-facing feed should use imagery to improve editorial hierarchy and scanning, provide accessible image treatment and clear source attribution, and retain a responsive layout consistent with Fablit's warm-neutral editorial design. Images must illustrate a topic without falsely implying that a generic stock image depicts a specific designer, collection, event, or product.

## 2. Context

- SPEC-041 provides curated, validated, persisted fashion/design stories and source links.
- SPEC-042 provides durable curation jobs and operational visibility.
- `fablit/application/image_search.py` defines the provider-neutral image-search port and provenance-bearing `ImageCandidate`.
- `fablit/platform/pexafy_image_search.py` provides the existing semantic stock-image search adapter used by practice authoring.
- The current `app/templates/news.html` feed is primarily text-based and does not display story imagery.

## 3. Goals

1. Improve the Stories/Pulse feed's visual hierarchy and editorial presentation on mobile, tablet, and desktop.
2. Add optional, automatically selected story imagery during curation by reusing existing image-search abstractions and configuration where practical.
3. Persist image provenance and attribution so the selected asset can be rendered consistently without live search at learner page load.
4. Keep source attribution clear, retain links to original stories, and distinguish stock illustration from imagery that documents a specific event or collection.
5. Preserve text-only rendering when imagery is missing, unsuitable, or unavailable.
6. Preserve the current FastAPI + HTMX/server-rendered architecture, design tokens, and accessibility expectations.

## 4. Functional requirements

### 4.1 Story imagery during curation

- Generate a short visual query from grounded story context; do not simply pass a sensational or overly long headline through unchanged.
- Use the existing provider-neutral image-search port and existing provider configuration. Do not add a separate Pixabay integration by default; consider another provider only if a documented capability gap justifies it.
- Keep search bounded by result count, timeout, and existing provider safeguards. Do not make image search a dependency for successful text curation.
- Select from returned candidates using relevance and visual suitability checks. A model-based judge may be used only with deterministic constraints and a conservative confidence threshold; uncertain matches must result in no image.
- Validate image metadata and URLs before persistence/rendering. Do not let untrusted provider fields control arbitrary server-side fetches or unsafe HTML.
- Persist the selected image metadata and provenance with the story through the existing news persistence boundary. Include the source/provider, original source page, creator/attribution details where available, alt text, and stable provider asset identifier where available.
- Respect the image provider's usage, caching, attribution, and storage requirements. Do not assume that a temporary provider image URL can be hotlinked indefinitely. If durable display requires downloading the image, use a bounded and safe download flow and store it in an appropriate existing durable asset mechanism; do not introduce a new media service without a separate decision.
- If image search fails, returns no results, returns unsafe/incomplete metadata, or yields no sufficiently relevant candidate, publish/retain the story without imagery and record safe diagnostic information for the operator.
- Existing published stories and learner page rendering must remain available when image search is down.
- Never run image search or AI image selection from the learner-facing page request.

### 4.2 Editorial presentation and attribution

- Improve card hierarchy so image (when available), headline, summary, categories, educational relevance, optional reflection prompt, publication date, original publisher and action are easy to scan.
- Images must be responsive, appropriately cropped, and not distort their aspect ratio.
- Provide meaningful alt text when the image conveys relevant information; use empty alt text only when it is genuinely decorative.
- Display stock-image credit/source attribution where appropriate, separate from the original-news publisher attribution.
- Do not imply that illustrative stock imagery depicts the exact designer, collection, product, event, or craft item in the story unless the source metadata supports that claim.
- Stories without imagery must retain a balanced, intentional text-first layout rather than a broken-image placeholder or empty media region.
- Preserve category filtering, empty states, unavailable states, story links, and optional practice/reflection content.
- Follow the existing warm-neutral editorial design system and responsive/accessibility conventions.

## 5. Acceptance criteria

- [ ] Stories with a suitable persisted image render a responsive, accessible image with appropriate provenance/credit.
- [ ] Stories without imagery render cleanly with no broken image or awkward empty image area.
- [ ] Image search and selection happen only within the curation workflow, never on learner page load.
- [ ] Existing image-search abstractions/provider configuration are reused; no duplicate provider stack is introduced without documented justification.
- [ ] Candidate selection is bounded, relevance-aware, and conservative; weak or uncertain matches fall back to text-only.
- [ ] Story records persist selected image metadata/provenance through the news-specific persistence boundary.
- [ ] Provider failure, timeout, empty results, invalid metadata, and persistence edge cases do not remove or block otherwise valid text stories.
- [ ] Publisher attribution and original-story links remain visible; image attribution is distinguishable from story attribution.
- [ ] Generic imagery is not presented as evidence of a specific collection, designer, event, or product.
- [ ] Desktop, tablet, and mobile layouts are visually reviewed and remain usable without horizontal scrolling.
- [ ] Keyboard focus, contrast, meaningful alt text, and existing accessible states are preserved.
- [ ] Existing curation, persistence, category-filtering, and learner journey tests continue to pass.
- [ ] Automated tests cover query derivation, candidate ranking/fallback, metadata validation, persistence/reconstruction, rendering, and provider failures.
- [ ] Full test suite passes; no learner-page network or AI dependency is introduced.

## 6. Explicit non-goals

- Building a separate Pixabay-specific integration by default.
- Live image searches while learners browse Pulse.
- Human approval of every story image in the initial implementation.
- Reproducing publisher photographs or article content without rights.
- Introducing a new media hosting service, scheduler, frontend framework, SPA, or unrelated infrastructure.
- Making imagery mandatory for every story.
- Changing SPEC-041's news relevance/grounding/publishing policy or SPEC-042's durable job lifecycle.
- Turning the reflection prompt into a mandatory practice task.

## 7. Implementation guidance

Before implementation, inspect the current main-branch versions of the news domain contract, curation use case, persistence adapter, view model, templates, CSS, and existing Pexafy image-search wiring. Keep provider-specific details behind the existing image-search port. Prefer a small number of cohesive implementation tasks with focused automated coverage, then perform manual visual review on representative image and text-only stories.
