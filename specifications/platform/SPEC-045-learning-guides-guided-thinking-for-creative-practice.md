# SPEC-045: Learning Guides — Guided Thinking for Creative Practice

**Status:** Proposed
**Owner:** Fablit product
**Related architecture:** ARCH-001, SEC-001
**Related specifications:** SPEC-032, SPEC-043, SPEC-044
**Related capabilities:** Existing practice authoring, provider-neutral image-search port, Pexafy image-search adapter

## 1. Overview and goal

Introduce **Learning Guides**: short, optional, visually engaging editorial experiences that help learners develop the thinking process behind creative practice. Guides should help learners observe, interpret, explore possibilities, and develop their own ideas without prescribing a model answer.

The learner experience should feel like a contemporary design-magazine feature combined with a creative workbook—not an online textbook, a rigid lesson, or a collection of repetitive cards.

Guides will be curated and published by authorised Fablit authors. Authors must be able to create, edit, preview, associate, and publish guides through Fablit's existing administrative experience. A guide can be associated with one or more existing practices; creating a guide must not require creating a new practice.

Reuse Fablit's existing provider-neutral image-search abstraction and configured Pexafy adapter used by practice authoring. Image search should happen during authoring, when an author adds imagery to a section. Published learner pages must render persisted, reviewed image references and attribution without performing live image searches or requiring an LLM call.

## 2. Product principles

1. **Show learners how to think, not what to think.** Guides develop observation, questioning, exploration, and creative confidence without supplying a prescribed answer.
2. **Editorial, not academic.** The experience should feel like a curated design-magazine feature.
3. **Visual, not text-heavy.** Use carefully selected imagery, examples, short text, and thoughtful prompts.
4. **Guidance, not answers.** Examples open up possibilities; they must not imply one correct creative outcome.
5. **Optional by design.** A learner can start or continue a practice without opening its guide.
6. **Human-reviewed publication.** Authors own the final content and image selection. AI-assisted drafting, if introduced later, is optional and never a publication authority.
7. **Reuse existing capabilities.** Extend existing authoring, image-search, persistence, and presentation patterns rather than introducing parallel infrastructure.

## 3. Goals

- Help learners overcome the initial difficulty of approaching open-ended creative prompts.
- Develop observation, visual thinking, ideation, visual storytelling, and design-thinking skills.
- Make selected Fablit practices more approachable without reducing their creative challenge.
- Provide a practical manual authoring and publishing workflow.
- Establish a reusable, versioned guide content model.
- Reuse the existing image-search abstraction and Pexafy adapter for section imagery.
- Create a distinctive, responsive editorial experience on mobile and desktop.
- Pilot the capability with approximately five carefully selected guides.

## 4. Non-goals

The initial release will not include:

- AI-generated video or video hosting infrastructure.
- A conversational AI tutor or real-time LLM-generated lessons.
- Automatic evaluation, scoring, grading, or assessment of guide interactions.
- Mandatory guides before starting a practice.
- A general-purpose course or lesson-management system.
- A learner certification, mastery, streak, or progress system.
- Automatically generated guides for every practice.
- Arbitrary HTML, JavaScript, or executable content in guide definitions.
- A separate image-provider integration or media-hosting service without a demonstrated gap in the existing capabilities.
- AI-assisted authoring as a dependency for manual guide creation.

## 5. Learner experience

### 5.1 Entry point

A practice card or practice detail page may offer an optional entry point when a published guide is associated with the practice:

**Explore a Learning Guide**

Supporting copy may say: *Need help getting started? Explore a few ways to approach this challenge.*

The entry point must only appear when an eligible published guide is available. It must not obstruct the primary practice action.

### 5.2 Guide structure

The common educational structure has four stages:

| Stage | Purpose |
|---|---|
| Observe | Help learners notice details, people, objects, situations, or patterns relevant to the challenge. |
| Think | Encourage interpretation, questions, and connections. |
| Explore | Introduce possible creative directions, techniques, or perspectives without prescribing an answer. |
| Create | Return the learner to the original challenge with an invitation to make their own choices. |

An optional reflection section may be included where it adds educational value.

These stages define the learning structure, not a rigid visual template. A guide may use different editorial compositions while retaining a coherent learning sequence.

### 5.3 Navigation and continuity

Learners should be able to:

- Read the guide as a short, focused experience.
- Understand the guide's structure and their current position.
- Navigate between sections without losing their place.
- View relevant images, captions, examples, and prompts.
- Return to the associated practice.
- Revisit the guide where supported by the existing learner journey.

Opening or leaving a guide must not reset, submit, or otherwise alter an in-progress practice.

### 5.4 Example learning guide

**Associated practice:**
*Observe the surrounding environment and consider how photography could be used to highlight unseen human effort.*

**Observe — Look beyond what is immediately visible**

A classroom is ready before students arrive. A market is organised before customers walk in. A street is clean before the city wakes up. Think about the people whose work often goes unnoticed. What details reveal the effort involved?

**Think — Can an ordinary detail tell an extraordinary story?**

- Why does this work often go unnoticed?
- What would someone normally overlook?
- Which small detail could communicate the effort involved?

**Explore — Find a different perspective**

Consider a wide shot that establishes the environment, a close-up that captures hands or tools, or light and shadow that reveal details. These are possibilities to explore, not instructions for a single correct composition.

**Create — Make the idea your own**

Choose a situation that interests you. Plan a small photographic story using your own observations and creative decisions. Consider what each image communicates and how the images work together.

**Reflect**

Does your work help someone notice something they might otherwise overlook? Does it represent the person and their work with dignity?

The objective is not simply to take a beautiful photograph. It is to make the viewer notice something they had not really noticed before.

## 6. Visual and interaction direction

### 6.1 Design concept

Use an **editorial-meets-creative-workbook** visual direction:

- Warm ivory or off-white backgrounds.
- Charcoal or dark neutral text rather than pure black.
- Expressive editorial serif typography for prominent headings.
- Clean contemporary sans-serif typography for body text.
- Restrained accents such as dusty blue, sage, or muted coral.
- Generous whitespace, subtle dividers, and restrained borders.
- Carefully selected photography, visual examples, and image compositions.

The experience should feel contemporary and appealing to design aspirants without looking childish, overly gamified, or like a conventional school worksheet. It should complement Fablit's existing warm-neutral design language.

### 6.2 Flexible editorial layouts

Do not force every guide into an identical stack of four cards. Depending on the content, supported layouts may include:

- Large editorial hero imagery.
- Photography-led sections.
- Image-and-text combinations.
- Side-by-side visual comparisons.
- Close-up and wide-shot examples.
- Highlighted questions or reflection prompts.
- Caption and annotation treatments.
- Numbered sections and editorial dividers.

A photography guide may be image-led, while a design-thinking guide may use a sequence of observations, questions, and illustrated examples.

Represent layout choices using a controlled set of presentation hints or section layout variants. Do not store arbitrary executable markup in guide content. A missing or unsupported layout hint must fall back to a safe default.

### 6.3 Responsive and accessible presentation

- Design mobile-first and support desktop and tablet.
- Use readable typography and comfortable spacing.
- Ensure images adapt to available width without distortion.
- Avoid horizontal scrolling for ordinary guide content.
- Support keyboard navigation and visible focus.
- Maintain accessible contrast.
- Provide meaningful alternative text for informative images.
- Use empty alternative text only for genuinely decorative imagery.
- Keep section navigation usable at narrow viewport widths.

## 7. Guide content model

Store guides as structured, versioned content rather than hardcoding each guide into application templates.

Each guide should support the following conceptual fields:

| Field | Description |
|---|---|
| guide_id | Stable unique identifier |
| title | Learner-facing title |
| summary | Short description of what the guide helps explore |
| status | Draft, published, or archived |
| version | Content version |
| practice_area | Relevant practice category |
| intended_learner_context | Target learner or examination context |
| sections | Ordered guide sections |
| associated_practice_ids | Stable identifiers of associated practices |
| assets | Image and other supported visual asset metadata |
| created_at / updated_at | Content timestamps |
| published_at | Publication timestamp, when applicable |

Each section should support:

- Stable section identifier and configured order.
- Section type/stage, heading, and short instructional content.
- Optional examples, questions, and reflection prompts.
- Optional associated visual assets.
- Optional controlled presentation/layout hint.

Asset metadata should retain, where available:

- Provider and stable provider asset identifier.
- Image URL or durable asset reference, according to provider terms.
- Original source page.
- Creator/photographer name.
- Required attribution/credit text and link.
- Usage or licence information needed to respect provider terms.
- Alt text and optional caption.
- Search query and selection provenance useful for editorial traceability.

Use the existing persistence conventions and datastore abstraction. The implementation should make a guide version and its selected asset metadata reproducible after publication.

## 8. Image sourcing and section imagery

### 8.1 Reuse existing image-search capability

Image search is an authoring-time capability. Reuse:

- `fablit/application/image_search.py` and its provider-neutral image-search port / provenance-bearing candidate contract.
- `fablit/platform/pexafy_image_search.py` and the existing configured Pexafy adapter used by practice authoring.
- Existing configuration, validation, and provider safeguards where applicable.

Do not create a parallel Pexafy client, a second image-search abstraction, or a new provider integration for Learning Guides by default. First inspect and extend the existing authoring integration cleanly.

### 8.2 Authoring workflow for images

Within an individual guide section, an authorised author should be able to:

1. Request or enter a suggested visual search query.
2. Edit the query before searching.
3. Search through the existing image-search service.
4. Browse a bounded set of returned candidates.
5. Preview candidate imagery and available source/creator/attribution information.
6. Select an image for the section.
7. Review and retain the attribution and usage metadata required by the provider.
8. Add suitable alt text and an optional caption.
9. Replace or remove the selected image before publication.

A suggested query may be derived from the section heading, section content, and intended visual purpose, but it must remain editable by the author. Do not assume a generated query is accurate without author review.

Support more than one image in a section where the selected editorial layout benefits from it. Do not require an image in every section; text-only sections must remain first-class.

### 8.3 Provider terms, provenance, and safe rendering

- Respect the image provider's usage, attribution, caching, hotlinking, and storage requirements.
- Do not assume a temporary provider URL can be hotlinked indefinitely.
- If durable display requires downloading an image, use an existing safe asset mechanism and a bounded download flow; do not introduce a new media service without a separate decision.
- Validate provider metadata and URLs before persistence and rendering.
- Treat provider-supplied fields as untrusted data; they must not control arbitrary server-side fetches or unsafe HTML.
- Preserve creator, source, attribution, and licence/usage details wherever supplied or required.
- Distinguish illustrative stock imagery from evidence depicting a specific person, designer, collection, product, or event. Do not imply a generic stock image documents a particular subject or event.
- If a candidate has insufficient provenance or its usage requirements cannot be established, do not publish it.
- If image search is unavailable, returns no suitable result, or produces incomplete/unsafe metadata, allow the author to continue with a text-only section and provide a clear author-facing explanation.

### 8.4 Runtime boundary

- Search only when an author explicitly searches or requests suggestions in the authoring interface.
- Never run image search while a learner opens or reads a published guide.
- Never require an LLM call to render a published guide.
- Published guide rendering must use persisted, validated content and asset references.

## 9. Authoring and publishing workflow

### 9.1 Manual authoring

An authorised content author must be able to manage guides through Fablit's existing administrative experience. Reuse the established practice-authoring patterns and authorisation boundaries where practical; do not build an independent CMS.

The workflow should support:

1. Create a guide.
2. Enter title, summary, practice area, and intended learner context.
3. Add, edit, reorder, and remove sections.
4. Write section content, questions, examples, and reflection prompts.
5. Search for, preview, select, attribute, replace, or remove section images using the existing image-search feature.
6. Configure supported editorial presentation variants.
7. Associate the guide with one or more existing practices.
8. Preview the learner-facing experience.
9. Save and resume a draft.
10. Publish intentionally when ready.
11. Edit or archive a guide with clear versioning and publication rules.

Creating a guide must not require creating a new practice. A guide may be associated with multiple practices where its educational content genuinely applies.

### 9.2 Preview and review

The author must be able to preview the guide using the actual learner-facing presentation before publishing.

Preview should help identify:

- Long or difficult-to-read content.
- Poor image placement, cropping, or aspect ratios.
- Missing or incomplete attribution.
- Incorrect section ordering.
- Unsupported layout variants.
- Missing or broken assets.
- Mobile and desktop layout issues.

The preview must clearly distinguish draft preview from the published learner experience. Publication must remain an intentional author action.

### 9.3 Publication and versioning

- Only published guides are visible to learners.
- Draft and archived guides must not appear in learner-facing practice pages.
- Saving a draft must never make it visible to learners.
- Updating published content must follow an explicit versioning/republishing process.
- The guide version and selected asset provenance used for publication should be identifiable.
- Guide edits must not alter, reset, or invalidate learner practice progress.
- Missing or archived associations must fail gracefully without breaking the practice journey.

### 9.4 Optional AI-assisted authoring (future enhancement)

An optional authoring assistant may later draft section content or suggest visual search queries from a practice prompt, learner context, and intended skill. This is not required for the initial release.

Any AI-generated content must remain editable and require human review before publication. Manual authoring must work without AI, and learner guide rendering must never depend on AI generation.

## 10. Technical and architectural requirements

- Preserve the existing FastAPI and HTMX/server-rendered application architecture.
- Reuse existing administrative authorisation and practice-authoring patterns.
- Use existing persistence conventions and datastore abstractions.
- Keep guide content independent of the AI provider.
- Reuse the existing provider-neutral image-search port and Pexafy adapter.
- Keep provider-specific image-search behavior behind the existing port.
- Render published guide content without an LLM call or external image search.
- Avoid external network dependencies on learner page loads where the provider's terms and existing asset architecture permit durable references.
- Associate guides with practices through stable identifiers, not titles.
- Support explicit content versioning.
- Keep guide content separate from learner practice submissions, evaluation, and private history data.
- Follow existing anonymous learner access and privacy conventions.
- Validate and safely escape all authored and provider-supplied content.
- Keep layout variants controlled and maintainable; do not introduce arbitrary executable markup.
- Missing guide data or assets must not break existing practice pages.

## 11. Analytics and success measures

Collect only lightweight product signals needed to understand whether guides are useful.

Suggested events:

- `learning_guide_opened`
- `learning_guide_section_viewed`
- `learning_guide_returned_to_practice`

Where practical, events may include guide ID, version, and associated practice ID. Do not collect learner-written creative work or use guide engagement as a measure of creative ability.

Initial success indicators:

- Learners open guides when they are available.
- Learners return to the associated practice after opening a guide.
- Guides are used across more than one practice area.
- Qualitative feedback indicates that guides help learners get started or explore ideas.

Avoid intrusive tracking and mandatory feedback prompts.

## 12. Initial pilot

Start with approximately five carefully selected guides:

1. **Finding Stories in Everyday Surroundings** — observation and photography.
2. **Learning to Notice Details** — observation and visual awareness.
3. **Telling a Story Through Three Frames** — visual storytelling and sequencing.
4. **Turning Everyday Problems into Design Opportunities** — design thinking.
5. **Finding Multiple Ideas in One Ordinary Object** — ideation and creative exploration.

The pilot should cover different kinds of creative thinking, not photography alone. It should demonstrate more than one supported editorial layout while retaining the common Observe–Think–Explore–Create learning structure.

## 13. Acceptance criteria

### Learner experience and presentation

- [ ] A published guide can be associated with an existing practice.
- [ ] A practice displays an optional guide entry point only when a published guide is available.
- [ ] A learner can open and read a guide without starting or submitting the practice.
- [ ] A learner can return to the associated practice without losing existing practice progress.
- [ ] Guide sections render in their configured order.
- [ ] Different guides can use supported editorial layout variations.
- [ ] The visual treatment follows the editorial-meets-creative-workbook direction and existing Fablit design language.
- [ ] The experience is responsive and usable on mobile and desktop.
- [ ] Keyboard navigation, visible focus, contrast, and meaningful image alternatives are supported.
- [ ] Optional visual assets display with appropriate attribution and do not falsely imply documentary evidence.
- [ ] A guide remains readable when an optional asset is unavailable.
- [ ] Learners can access guides through the existing anonymous learner journey.

### Authoring and publication

- [ ] An authorised author can create and edit a guide through the administrative interface.
- [ ] Authors can add, edit, reorder, and remove guide sections.
- [ ] Guide content can be saved as a draft and resumed.
- [ ] An author can preview the learner-facing guide before publication.
- [ ] Creating a guide does not require creating a practice.
- [ ] A guide can be associated with multiple practices where appropriate.
- [ ] Draft, published, and archived states are supported.
- [ ] Only published guides are visible to learners.
- [ ] Published content changes follow explicit versioning/republishing rules.
- [ ] Guide content is stored independently of application templates.

### Image sourcing and provenance

- [ ] Section image search reuses the existing provider-neutral image-search port and configured Pexafy adapter.
- [ ] Authors can search from an individual section using an editable query.
- [ ] Authors can preview a bounded set of image candidates and select, replace, or remove a selection.
- [ ] Selected image metadata, provenance, creator/source, attribution, and usage details are retained as available/required.
- [ ] Authors can add meaningful alt text and optional captions.
- [ ] Sections can be published without images.
- [ ] Unsafe, unsuitable, or inadequately attributed candidates cannot be published.
- [ ] Provider usage, caching, hotlinking, and storage requirements are respected.
- [ ] Image search never runs on learner page loads.

### Architecture, reliability, and privacy

- [ ] Published guide rendering does not require an LLM call.
- [ ] Existing FastAPI, HTMX, persistence, authorisation, and image-search conventions are followed.
- [ ] Missing or unavailable guide content/assets do not break the practice journey.
- [ ] Guide content and assets are safely validated and rendered.
- [ ] Guide data and analytics do not capture learner-written creative responses.
- [ ] Tests cover guide retrieval, publication visibility, authorisation, practice association, section ordering, layout fallback, image-search reuse, image provenance, and learner access.
- [ ] Provider failures, empty results, and unsuitable image candidates allow text-only authoring.
- [ ] Existing practice-authoring, image-search, and learner journeys continue to pass regression tests.

### Measurement

- [ ] Guide-open and return-to-practice events can be recorded.
- [ ] Analytics do not capture learner-written creative responses.
- [ ] The pilot can be evaluated without mandatory learner feedback.

## 14. Implementation guidance

Begin with a focused review of the current main-branch implementation of:

- Practice authoring and its administrative routes/templates.
- Existing authorisation boundaries for content authors.
- Practice persistence and stable practice identifiers.
- `fablit/application/image_search.py`.
- `fablit/platform/pexafy_image_search.py`.
- Existing image-search usage in practice authoring, including configuration and asset/provenance handling.
- Existing design tokens, templates, and responsive/accessibility conventions.

Implement the capability in cohesive vertical slices:

1. Guide domain/content contract, persistence, versioning, and practice association.
2. Authoring UI for guide metadata and section management, including draft save/resume.
3. Section image search by reusing the existing image-search port and Pexafy adapter; selection, provenance, attribution, and text-only fallback.
4. Learner-facing editorial rendering with controlled layout variants and responsive behavior.
5. Preview, publication/archive lifecycle, and integration with practice entry points.
6. Lightweight analytics and end-to-end/regression coverage.

Do not introduce a new image provider, media service, frontend framework, course platform, AI tutor, or unrelated infrastructure without documenting a concrete gap and obtaining a separate product decision.

The initial release is complete when an authorised author can manually create, preview, publish, and associate a visually rich guide using existing image-search capabilities, and a learner can optionally open that guide and return to the practice without disrupting the existing journey.
