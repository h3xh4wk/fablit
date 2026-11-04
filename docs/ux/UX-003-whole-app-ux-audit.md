# UX-003 — Whole-App UX, UI, Navigation and Scroll Audit

**Document ID:** UX-003
**Status:** Audit complete — implementation not started
**Date:** 2026-11-04
**Specification:** [SPEC-046 — Whole-App UX, UI, Navigation and Scroll Refinement](../../specifications/platform/SPEC-046-whole-app-ux-ui-navigation-scroll-refinement.md)
**Tracking issue:** [#195 — SPEC-046 Phase 1: Audit and document the whole-app UX](https://github.com/h3xh4wk/fablit/issues/195)
**Audited tree:** `fix/issue-195` at `8021f26` (`docs: add SPEC-046 whole-app UX and UI refinement`), current default-branch tip at audit time
**Related documents:** [UX-001 — Fablit Learner Experience Direction](../UX-001-fablit-experience.md), [UX-002 — Visual Language & Interaction Guidelines](UX-002-fablit-visual-language-and-interaction-guildelines.md), [Architecture Blueprint](../architecture/architecture_blueprint.md)

---

## 1. Purpose, scope and method

This document is the Phase 1 discovery baseline for SPEC-046. It inventories every
current user-facing route, template, and meaningful workflow state, then records what
each page is for, how it behaves, and where navigation, focus, scroll, responsiveness,
or accessibility need attention.

**Scope covered**

- Learner discovery, practice selection, the full practice journey, history/review,
  Fashion & Design Pulse, and Learning Guides.
- Internal authoring login, practice authoring/candidate review, Pulse curation, and
  Learning Guide authoring.
- The shared application shell, interaction patterns, HTMX behaviour, browser history,
  and existing client-side scripts.

**Out of scope**

- Application code, template, CSS, route, JavaScript, or runtime changes.
- Redesigns and new controls.
- Changes to business rules, learner identity/privacy, persistence contracts, or
  practice lifecycle semantics.
- A frontend rewrite or new component library.

### 1.1 Evidence status

| Evidence type | Performed? | Notes |
| --- | --- | --- |
| Static route inspection | Yes | Every route below was cross-checked against `app/main.py`, `app/learner_request.py`, `app/news.py`, `app/authoring.py`, and `app/guides.py`. |
| Template/partial inspection | Yes | All 27 templates and partials under `app/templates/` were read. |
| CSS/JS inspection | Yes | `app/static/css/fablit.css` and all four scripts under `app/static/js/` were inspected; the vendored HTMX 2.0.10 behaviour referenced below was read from `app/static/htmx.min.js`. |
| Runtime browser verification | **No** | No browser session, screenshots, or Playwright run was performed for this audit. Linux and Chrome are present in the working environment, but no browser-level checks were executed. |
| Automated CI tests | Yes | The existing CI test suite and Playwright browser learner-journey suite ran successfully for PR #196. These are regression checks; they do not constitute a dedicated browser walkthrough of the 22 scenarios in this audit. |

Because no dedicated browser walkthrough of the audit scenarios was performed,
**this audit contains no "reproduced defect" entries.** The passing CI test and
Playwright learner-journey suites provide regression evidence, but they do not verify
the 22 individual scenarios in §8 or establish that any finding has been reproduced
or cleared. Everything that depends on runtime layout, actual focus movement, browser
history, or scroll position is recorded as an **unverified source-level
risk/hypothesis** with a manual reproduction plan in §8. Usability concerns inferred
directly from templates and routes are labelled **observed usability concern**.

### 1.2 Finding classifications

| Code | Meaning |
| --- | --- |
| **RD** | Reproduced defect — verified in a browser with steps and environment. *None in this audit.* |
| **UC** | Observed usability concern — evident from static inspection of routes, templates, or copy. |
| **UR** | Unverified source-level risk/hypothesis — plausible from code/HTMX behaviour, but not browser-confirmed. |
| **OP** | Optional visual polish — does not materially block task completion. |

---

## 2. Verified route and template inventory

The inventory below was checked against the route decorators and the template names
passed to `TemplateResponse`. "Page" routes are user-facing; "support" routes are
included where they affect a visible state (errors, exports, JSON polling).

### 2.1 Shared shell

| Item | Source | Notes |
| --- | --- | --- |
| Base layout | `app/templates/base.html` | One `<main id="main">`, skip link, brand, primary nav, vendored HTMX, `export.js`, `session-recovery.js`, `authoring-scroll.js`, `htmx-focus.js`. |
| Global stylesheet | `app/static/css/fablit.css` | Central tokens, warm-neutral palette, editorial serif display type, focus styles, reduced-motion rule. |
| Primary learner nav | `base.html` | Practice (`/`), Stories (`/pulse`), Your practice (`/history`); active state via `aria-current="page"`. |
| Authoring nav partial | `app/templates/_authoring_nav.html` | Learner practice, Candidate workspace, Learning Guides, Pulse, Log out; active section marked via `aria-current="page"` (`authoring_section`, Slice 1 / #197). |
| Learner error page | `app/templates/error.html` | Message (`data-focus-target`) + optional description + "Back to practice". |
| Authoring error page | `app/templates/authoring_error.html` | Message (`data-focus-target`) + description + "Back to the authoring workspace". |
| Authoring login page | `app/templates/authoring_login.html` | Also used by the 401 handler for authoring navigation. |

### 2.2 Learner routes

| Route | Methods | Template / output | Purpose |
| --- | --- | --- | --- |
| `/` | GET | `dashboard.html` | Explore the activity library. |
| `/practice` | GET | `practice_mode_choice.html` | Choose a practice shape. |
| `/practice/{mode_id}` | GET | `practice_mode_activities.html` | Activities for the chosen mode; empty state. |
| `/practice/request` | GET, POST | `practice_request.html` | Compose a private requested practice; list this learner's requested practices. |
| `/practice/request/{practice_id}` | GET | `requested_practice.html` | Review a generated brief before beginning. |
| `/activities/{activity_id}/intention` | GET, POST | `intention.html` | Optional pre-practice intention, or skip. |
| `/activities/{activity_id}` | GET | `practice.html` + `_practice_partial.html` | Practice workspace: guide invitation, stimulus, task, response. |
| `/activities/{activity_id}/submit` | POST | `_practice_partial.html` (HTMX) or `_feedback_partial.html` (HTMX success) or full page | Accept response/artifact. |
| `/feedback` | GET | `feedback.html` | Feedback, reflection invitation, Save/Skip. |
| `/reflect` | GET, POST | `reflection.html` | Reflection entry; blank submission skips. |
| `/complete` | GET | `complete.html` | Completion, optional continuation, history/back paths. |
| `/history` | GET | `history.html` | Completed practice, private story responses, export, empty/outage states. |
| `/history/{completion_id}` | GET | `review.html` | One completed practice, with export. |
| `/history/{completion_id}/artifact` | GET | Binary image response | Private sketch bytes; 404 when absent. |
| `/history/story-responses/{response_id}` | GET | `story_response_review.html` | One private story response with provenance. |
| `/pulse` | GET | `news.html` | Curated Fashion & Design Pulse feed and category filters. |
| `/pulse/stories/{story_id}/responses` | POST | `news.html` | Save a private story response. |
| `/guides/{guide_id}` | GET | `guide.html` | Published guide reader. |
| `/guides/{guide_id}/return-to-practice` | GET | 303 redirect | Return to an associated practice. |

### 2.3 Authoring routes

| Route | Methods | Template / output | Purpose |
| --- | --- | --- | --- |
| `/authoring/login` | GET, POST | `authoring_login.html` / redirect | Authoring access. |
| `/authoring/logout` | POST | redirect `/` | Clear author session. |
| `/authoring`, `/authoring/` | GET | `authoring.html` | Brief, AI draft, generate, Pulse action, candidate queue. |
| `/authoring/brief/draft` | POST | `authoring.html` full page or `#main` fragment | Draft one field or the whole brief. |
| `/authoring/generate` | POST | `authoring_candidate.html` or `authoring.html` error view | Generate a candidate. |
| `/authoring/candidates` | GET | JSON | Candidate list API. |
| `/authoring/candidates/{id}` | GET | `authoring_candidate.html` or JSON | Candidate review. |
| `/authoring/candidates/{id}/stimulus` | POST | `authoring_candidate.html` or JSON | Select/remove stimulus image. |
| `/authoring/candidates/{id}/approve` | POST | `authoring_candidate.html`, workspace, or JSON | Approve. |
| `/authoring/candidates/{id}/reject` | POST | `authoring_candidate.html`, workspace, or JSON | Reject. |
| `/authoring/candidates/{id}/edit` | POST | `authoring_candidate.html` or JSON | Save a revision. |
| `/authoring/candidates/{id}/publish` | POST | `authoring_candidate.html` or JSON | Publish to learner library. |
| `/authoring/candidates/{id}/withdraw` | POST | `authoring_candidate.html` or JSON | Withdraw from learner library. |
| `/authoring/pulse` | GET | `authoring_news.html` | Sources, curation action, job status, latest report. |
| `/authoring/pulse/curate` | POST | `authoring_news.html` or JSON | Start a durable curation job. |
| `/authoring/pulse/jobs/latest` | GET | JSON | Latest job status. |
| `/authoring/pulse/jobs/{job_id}` | GET | JSON | One job status. |
| `/authoring/guides` | GET, POST | `authoring_guides.html` / redirect to editor | Guide list and draft creation. |
| `/authoring/guides/pilot` | POST | `authoring_guides.html` | Seed pilot guides. |
| `/authoring/guides/{id}` | GET | `authoring_guide.html` | Guide editor. |
| `/authoring/guides/{id}/details` | POST | `authoring_guide.html` | Save metadata and associations. |
| `/authoring/guides/{id}/sections` | POST | `authoring_guide.html` | Add a section. |
| `/authoring/guides/{id}/sections/{sid}` | POST | `authoring_guide.html` | Save a section. |
| `/authoring/guides/{id}/sections/{sid}/move` | POST | `authoring_guide.html` | Reorder. |
| `/authoring/guides/{id}/sections/{sid}/remove` | POST | `authoring_guide.html` | Remove a section. |
| `/authoring/guides/{id}/sections/{sid}/images/search` | POST | `_guide_image_candidates.html` fragment | Search images for one section. |
| `/authoring/guides/{id}/sections/{sid}/images` | POST | `authoring_guide.html` | Add/replace an image. |
| `/authoring/guides/{id}/sections/{sid}/images/update` | POST | `authoring_guide.html` | Update alt text/caption. |
| `/authoring/guides/{id}/sections/{sid}/images/remove` | POST | `authoring_guide.html` | Remove an image. |
| `/authoring/guides/{id}/preview` | GET | `guide.html` with preview banner | Preview learner presentation. |
| `/authoring/guides/{id}/publish` | POST | `authoring_guide.html` | Publish or explain validation failure. |
| `/authoring/guides/{id}/archive` | POST | `authoring_guide.html` | Archive. |

### 2.4 Non-UI and operational routes

`GET /health`, `GET /metrics`, `POST /tasks/news-curation`, and the development-only
`/docs`, `/redoc`, and `/openapi.json` are not user-facing pages. They are excluded from
the page inventory. `GET /history/{completion_id}/artifact` is a binary support endpoint
but is documented with its review page because access failures are learner-visible.

---

## 3. Shared interaction-pattern audit

### 3.1 Navigation shell

- **Observed: consistent primary navigation.** All learner pages use the same three
  destinations and mark the current section with `aria-current="page"`. The dashboard
  ("Practice") stays reachable, and Stories/History are visible on every page.
- **Resolved in Slice 1 (#197): current-page state in authoring navigation.** `_authoring_nav.html`
  initially linked to the candidate workspace, Learning Guides, and Pulse without setting
  `aria-current`. Slice 1 passes an explicit `authoring_section` (`workspace`, `guides`,
  `pulse`) from every authoring route and error handler so the active destination carries
  `aria-current="page"` (and matching `.subnav a[aria-current="page"]` visual styling)
  without fragile prefix matching across `/authoring`, `/authoring/candidates/{id}`,
  `/authoring/guides`, `/authoring/guides/{id}`, and `/authoring/pulse`.
- **Observed: no sticky header.** There is no `position: sticky` header or toolbar in
  the stylesheet, so anchor destinations are not currently obscured by a fixed header.
- **Observed: skip link.** The first tab stop is "Skip to content", it targets
  `#main`, and it is explicitly excluded from HTMX boosting with `hx-boost="false"`.

### 3.2 HTMX boosting, history and scroll

The shell sets `<body hx-boost="true">`. The vendored HTMX 2.0.10 configuration is
default except for response handling in `base.html` (`4xx`/`5xx` responses swap).
Reading the vendored library establishes the following source-level baseline:

- Boosted anchors and forms replace the body (`innerHTML`) and, by default, set
  `show: top`; a hash-only anchor (`href="#..."`) is not boosted.
- A boosted element that also has an explicit `hx-post`/`hx-get` is processed as a
  normal targeted request, not as a boosted page request, so it does not automatically
  scroll to top or push history.
- Boosted requests push the final request path into history. HTMX's history cache
  (`historyCacheSize: 10`) and native browser history are expected to restore scroll
  on back/forward.
- **Resolved in Slice 1 (#197): shared post-swap focus policy (`app/static/js/htmx-focus.js`).**
  Focus management and scroll positioning are handled separately on `htmx:afterSettle`:
  - **Anchor target:** if the request path carries a `#fragment`, focus moves to the
    matching element ID.
  - **Failed (`4xx`/`5xx`) swaps:** focus moves to `[data-focus-target]`, `[role="alert"]`,
    `h1`, or `#main` inside the swapped target.
  - **Boosted page navigation (`target === document.body`) and targeted `#main` swaps
    (`target.id === "main"`):** focus moves to `[data-focus-target]` within `#main`, an
    enabled `[autofocus]` control, `#main h1`, or `#main`.
  - **Smaller targeted partial swaps:** focus moves *only* when the swapped fragment
    explicitly declares `[data-focus-target]` (or on a failed swap). Background JSON
    polling (`news-curation-status.js`) and unopted partial updates never steal focus.
  - **Temporary `tabindex="-1"` and `{ preventScroll: true }`:** non-focusable headings
    or status panels receive `tabindex="-1"` and `data-htmx-focused="true"` only while
    focused (cleaned up on `blur`), and every programmatic `.focus({ preventScroll: true })`
    call preserves page scroll and `authoring-scroll.js` candidate scroll restoration.

**Observed source-level page policies**

| Navigation type | Current mechanism | Intended policy |
| --- | --- | --- |
| Link to a different page | Boosted anchor, `show: top` | Start at page top. |
| Hash-only link (guide TOC) | Not boosted | Native fragment scroll. |
| Practice submit | Explicit `hx-post`, target `#submission-area` | Preserve page position; show feedback in place. |
| Practice request submit | Boosted form | Full-page result at top, with values preserved on error. |
| Pulse response | Boosted form | Full-page result; success URL contains `#story-...`. |
| Story filter | Boosted category link | Feed top, active filter visible. |
| Authoring brief draft / curate | Explicit `hx-post` with `#main` target | Replace main content without a full page reload. |
| Guide image search | Explicit `hx-post` with section target | Replace candidates only, no page jump. |
| Guide save/reorder/remove/publish | Plain full-page POST | Full page reload; no app scroll restoration. |
| Candidate actions | Plain full-page POST | Full page reload; `authoring-scroll.js` restores scroll for candidate URLs. |

### 3.3 Buttons, links and actions

- **Primary button:** `.button` — accent background, light text, generous padding;
  used for the expected next step.
- **Secondary button:** `.button--secondary` — surface background, rule border; used
  for alternatives, skips, archive, move, and other quieter actions.
- **Destructive actions are not visually distinguished.** Reject, withdraw, remove
  section, remove image, and archive all use the secondary style. No confirmation
  step exists for any of them. This is an **observed usability concern** (F-14).
- **Card actions are text links**, not whole-card links. On mobile the actionable
  target is the "Explore" link only. The card itself has no hover/focus affordance.
- **Disabled states:** `.button:disabled` reduces opacity and changes the cursor;
  forms use `hx-disabled-elt` during HTMX requests and show a text indicator.

### 3.4 Forms and validation

- Inputs and textareas use visible `<label for>` elements, shared `.form-control`
  styling, a minimum 3rem height, and a visible focus outline.
- Field errors use `role="alert"`; successful saves use either `role="status"` or
  plain text in a panel.
- Learner validation paths preserve submitted text: practice submissions re-render
  `_practice_partial.html` with `submitted_response`; reflection re-renders with
  `submitted_content`; practice requests re-render all selected values; Pulse
  re-renders the draft and reopens the relevant composer.
- **Observed:** the feedback page nests a `<form>` inside a `<p class="form-actions">`
  for Skip. A form is not permitted inside a paragraph, so the browser is expected to
  close the paragraph before the form. This can separate the Skip control from the
  intended action row (F-08; runtime effect unverified).
- **Observed:** the reflection page marks the textarea `required` and has no visible
  Skip button, while the feedback panel offers an explicit Skip. The server accepts a
  blank reflection. This is an inconsistency in the optionality message (F-09).

### 3.5 Cards, filters, expanders and image selection

- **Cards:** one shared `.card` pattern; dashboard/mode cards show optional preview
  image, title, "Practised" continuity cue, description, skills, and an Explore link.
  Pulse cards show image/credit, categories, headline, summary, relevance note,
  optional prompt, "Try this" details composer, practice link, source, and date.
- **Filter chips:** `<ul class="filter-tabs" aria-label="...">` with links and
  `aria-current="true"` for the active item. Used for Pulse categories and the
  authoring candidate queue. Semantics are link-based rather than tab-based; this is
  understandable but has no tab/list current-state semantics beyond `aria-current`.
- **Expanders:** native `<details>/<summary>` for Pulse "Try this", candidate workflow
  details, generated content, brief, revision history, and optional authoring fields.
  Native keyboard and screen-reader behaviour is preserved. Focus styles on summary
  elements are provided.
- **Notices:** `.validation-panel` variants (`error`, `caution`, `ok`) with `role`
  values chosen per surface. Not all panels that appear after an action have a live
  role (F-17).
- **Image selection:** image candidates are a grid of cards with preview, attribution,
  alt text input, optional caption, replace selector, and a submit button. Missing
  creator/source is called out as unpublishable. Removed/selected images remain in the
  page flow; there is no modal.

### 3.6 Accessibility baseline

- One `<h1>` per page; semantic landmarks (`header`, `nav`, `main`, `article`,
  `section`); labelled navigation regions.
- Global `:focus-visible` outline; skip link; reduced-motion rule that removes
  transitions/animations.
- Images carry alt text; decorative emoji are usually `aria-hidden`, but several
  headings/labels include emoji directly (semantic text is still present).
- Touch targets: buttons and inputs are comfortably padded; card action links and
  inline "Source" links are text-sized and may be small on touch (optional polish).
- No horizontal-scroll suppression beyond the card and story-grid rules; mobile
  reflow has not been measured in a browser.

---

## 4. Page-by-page inventory

Each entry covers the fields required by SPEC-046 §5. "Not applicable" is stated where
a field does not apply rather than omitted.

### 4.1 Dashboard — `GET /`

- **Route / template:** `/` → `dashboard.html` (extends `base.html`).
- **User and primary intent:** Learner; find something interesting to practise now.
- **Entry and exit paths:** Entry from brand, "Practice" nav, completion page, error
  pages, and authoring logout. Exit to intention (`/activities/{id}/intention`), mode
  chooser (`/practice`), request composer (`/practice/request`), Stories, or History.
- **Actions:** Primary — "Explore" on an activity card. Secondary — "Choose how you'd
  like to practise", "Request a practice". Destructive/irreversible — none.
- **Content hierarchy:** Display heading, lede, two quiet invitations, then the card
  grid (image, title, "Practised" cue, description, skills, action). The next useful
  action is the first card's Explore link.
- **States:** No loading state (server-rendered). Empty state is not rendered: with no
  activities the grid would be empty (demo content normally prevents this). Error state
  for an unhandled failure uses the learner error page. No success/validation state.
- **Responsive:** One column below 40rem, auto-fit cards at ≥40rem. Card image is
  full-width and `height: auto`. Header nav wraps.
- **Accessibility:** Single h1; cards are list items with h2 titles; Explore links have
  accessible names; preview images use the activity alt text. Card is not a link, so
  focus is limited to the Explore link.
- **Scroll and focus:** Boosted page navigation starts at top. No in-page dynamic
  updates. Returning from History/completion via boosted links starts at top.
- **Findings:** F-18 (no empty state; low impact), F-20 (boosted navigation focus
  resets to document). Card affordance is otherwise clear.

### 4.2 Practice mode choice — `GET /practice`

- **Route / template:** `/practice` → `practice_mode_choice.html`.
- **User and primary intent:** Learner; choose a practice shape that fits the moment.
- **Entry and exit paths:** Entry from the dashboard invitation and Practice nav. Exit
  to `/practice/{mode_id}`, request composer, dashboard ("Skip this and go to explore"),
  or Explore via the brand/nav.
- **Actions:** Primary — "Begin" on each mode card. Secondary — request a practice,
  skip to Explore. Destructive — none.
- **Content hierarchy:** Question heading, lede, mode list (label, description, effort
  guidance, Begin), then the request invitation and skip link. No mode is preselected.
- **States:** No loading/empty/error state in the template; modes come from
  configuration. Server errors use the learner error page.
- **Responsive:** Single column; two-column auto-fit at ≥40rem. Mode option is a full
  card-shaped link with a large target.
- **Accessibility:** The whole option is a link, so the label, description, and effort
  are all part of its accessible name (verbose but informative). No selected state.
- **Scroll and focus:** Boosted navigation to top; no local updates.
- **Findings:** No unique finding. The mode cards are a good example of a comfortable
  mobile target and could be reused for other selectable-card needs.

### 4.3 Mode activities — `GET /practice/{mode_id}`

- **Route / template:** `/practice/{mode_id}` → `practice_mode_activities.html`.
- **User and primary intent:** Learner; pick an activity within the chosen mode.
- **Entry and exit paths:** Entry from `/practice`. Exit to intention for an activity,
  "Change practice choice" (`/practice`), or Explore.
- **Actions:** Primary — Explore an activity. Secondary — change practice choice, go to
  Explore. Destructive — none.
- **Content hierarchy:** Back subnav, mode label/description/effort, then activity
  cards or the empty panel.
- **States:** Empty state present ("Nothing here yet") with a link to Explore. No
  loading state. Unknown mode renders the learner error page. No success/validation
  state.
- **Responsive:** Shared card grid: one column, auto-fit at ≥40rem. Empty panel is
  centred and padded.
- **Accessibility:** Back link has an aria-label on its nav; activity cards match the
  dashboard pattern. Empty panel has an h2 and explanatory text plus a clear action.
- **Scroll and focus:** Boosted navigation to top; no local updates.
- **Findings:** No unique finding. The empty state is a useful reference pattern for
  F-18.

### 4.4 Practice request composer — `GET` and `POST /practice/request`

- **Route / template:** `/practice/request` → `practice_request.html`.
- **User and primary intent:** Learner; describe a private practice they want Fablit to
  make, or reopen a previously requested practice.
- **Entry and exit paths:** Entry from the dashboard, mode chooser, requested-brief
  page, Pulse "Make this a practice", and header nav (via dashboard). Exit to
  `/practice/request/{practice_id}` on success; stays on the form on validation,
  rate-limit, provider, or persistence failure.
- **Actions:** Primary — "Make this practice". Secondary — edit area/challenge/response
  form, opt into recent-practice context, open a previous requested practice, back to
  Explore. Destructive/irreversible — none; the opt-in is reversible by unchecking.
- **Content hierarchy:** Heading, explanation that the brief is shown before beginning,
  status/error panels, optional story-context panel, request textarea, three selects,
  optional examination context, optional history checkbox with privacy explanation,
  submit, then "Practices you requested" or its empty note, then back to Explore.
- **States:** Availability notice when generation is unavailable; inline error panel
  (validation, rate limit, generation failure, persistence failure); disabled submit
  and a "Making your practice…" progress label; loading indicator; empty list note;
  success redirect to the brief. Submitted values are preserved on every error path.
  `Retry-After` is returned on 429.
- **Responsive:** Form fields stack; the area/challenge row is a two-column grid at
  wider widths. Long labels/hints wrap.
- **Accessibility:** Labelled controls; privacy explanation is programmatically inside
  the checkbox label; error panel `role="alert"`; status panel `role="status"`;
  loading indicator `role="status" aria-live="polite"`; disabled button explains
  unavailability through the adjacent status panel.
- **Scroll and focus:** The form is boosted (no explicit `hx-post`), so errors and
  success swap the body and scroll to top. There is no explicit focus move to the
  error panel or to the generated-brief heading. The story-context link to the Pulse
  anchor is a normal link.
- **Findings:** F-20 (focus after boosted error/success); otherwise the strongest
  input-preservation pattern in the app. The story-context panel should be kept as the
  reference for explaining prefilled values.

### 4.5 Requested practice brief — `GET /practice/request/{practice_id}`

- **Route / template:** `/practice/request/{practice_id}` → `requested_practice.html`.
- **User and primary intent:** Learner; understand a generated brief before deciding
  whether to begin.
- **Entry and exit paths:** Entry after generation or from the requested-practices
  list. Exit to intention ("Begin this practice" / "Practise again"), request composer
  ("Request another"), or dashboard via nav.
- **Actions:** Primary — begin/practise again. Secondary — request another. Destructive
  — none.
- **Content hierarchy:** Breadcrumb, title, description, privacy/availability panel,
  "What you will do", "Why this practice", "What to think about", "How to respond",
  metadata, then Begin/Request another.
- **States:** 404 learner error page for an invalid/unknown/other learner's practice.
  No loading/empty/validation state. The privacy panel is always shown.
- **Responsive:** Single reading column; sections stack; nav buttons wrap.
- **Accessibility:** Breadcrumb link returns to composer; section headings are h2;
  evidence blocks preserve whitespace. Buttons are clearly labelled.
- **Scroll and focus:** Boosted navigation to top; no local updates. Returning from the
  practice via boost starts at top.
- **Findings:** No unique finding. The brief has a clear primary action and honest
  provenance copy.

### 4.6 Intention — `GET` and `POST /activities/{activity_id}/intention`

- **Route / template:** `/activities/{activity_id}/intention` → `intention.html`.
- **User and primary intent:** Learner; optionally name what they want to focus on
  before starting.
- **Entry and exit paths:** Entry from dashboard/mode cards, completion continuation,
  and requested-practice brief. Exit to the practice workspace on submit or skip, or
  back to all activities.
- **Actions:** Primary — configured action label (continue with intention). Secondary —
  Skip. Destructive — none. Both buttons submit the same form; Skip sends an empty
  `intention` value.
- **Content hierarchy:** Back subnav, heading, activity title, prompt, optional
  textarea, action row.
- **States:** Empty/blank intention is accepted and simply proceeds. Invalid activity
  renders the learner error page. No loading/validation/success state.
- **Responsive:** Single narrow reading column; textarea and action row stack naturally.
- **Accessibility:** Labelled textarea; prompt is separate text; two submit buttons are
  distinguishable by name. `session-recovery.js` restores local drafts and saves on
  input/blur.
- **Scroll and focus:** Plain form submission (boosted) → workspace at top. No focus
  move into the practice workspace. If a draft recovery banner appears on the practice
  page it is a `role="status"` region.
- **Findings:** No unique finding. The optionality is clear, but F-09 shows that the
  reflection step does not mirror this explicit skip pattern.

### 4.7 Practice workspace — `GET /activities/{activity_id}` and `POST .../submit`

- **Route / template:** `/activities/{activity_id}` → `practice.html`, with
  `_practice_partial.html` inside `#submission-area`; successful HTMX submission swaps
  in `_feedback_partial.html`.
- **User and primary intent:** Learner; observe the stimulus, read the task, and write
  (or sketch) a response.
- **Entry and exit paths:** Entry from intention, requested brief, completion
  continuation, or an existing practice link. Exit on submit to feedback (in-place via
  HTMX or `/feedback` without HTMX), back to Explore, or into an optional guide and
  back.
- **Actions:** Primary — "I'm ready". Secondary — add an optional sketch, open a
  Learning Guide, back to activities. Destructive/irreversible — none in the page,
  though submitting ends the response-editing state.
- **Content hierarchy:** Back subnav, invitation line, title, skills, intention echo,
  optional guide invitation, "Observe" stimulus with attribution, "Your task" with
  optional details, "Your response" form.
- **States:** Validation/evaluation failure error in `_practice_partial` with the
  response preserved; HTMX loading indicator; disabled button during request; optional
  artifact upload with file-type/size hints; local draft recovery banner
  ("An unfinished practice was saved on this device") with Resume/Discard; guide lookup
  failure silently omits the guide and keeps practice usable.
- **Responsive:** Single column; stimulus image is fluid; textarea is tall (12 rows);
  action row wraps. The guide links wrap.
- **Accessibility:** Labelled response textarea with hint and placeholder; required
  response; error `role="alert"`; loading status live region; stimulus alt text and
  source link; task detail is an h3; guide section has its own h2. Focus management
  after the in-place success swap is the main gap (F-03).
- **Scroll and focus:** Before submit, the form is a normal part of the page. The
  submit form has an explicit `hx-post` and target, so HTMX does **not** treat it as a
  boosted page request: it is expected to swap `#submission-area` and leave the URL
  and scroll position alone. On success, the form (and the focused button) is removed;
  no handler moves focus to the feedback region. On error, the error is rendered above
  the form but focus would stay on the replaced/removed area unless the browser
  intervenes.
- **Findings:** F-03 (focus/announcement after swap), F-04 (feedback may appear below
  the viewport), F-05 (URL/history does not reflect the in-place feedback state).

### 4.8 Feedback (full page and in-place partial) — `GET /feedback`

- **Route / template:** `/feedback` → `feedback.html`; HTMX success renders
  `_feedback_partial.html` into `#submission-area`.
- **User and primary intent:** Learner; read what was noticed, what to think about, and
  what to try next, then continue to reflection.
- **Entry and exit paths:** Entry from the practice submit (in place) or `/feedback`
  after a no-JS submit. Exit to `/reflect` via Save, or POST `/reflect` with an empty
  value via Skip; back to activities.
- **Actions:** Primary — "Save reflection" (link to `/reflect`). Secondary — "Skip
  reflection" (form post with blank content), back to activities. Destructive — none.
- **Content hierarchy:** Back subnav, h1, activity title, three feedback sections,
  reflection panel with prompt, intention echo, reflection questions, Save/Skip.
- **States:** In-place success; full-page success; no explicit loading state on the
  page because feedback is already rendered; missing feedback redirects to `/`.
  Persistence errors occur on the reflection POST, not here.
- **Responsive:** Single reading column; feedback lists stack; action row wraps.
- **Accessibility:** Section headings, list semantics, labelled action links/buttons.
  The Skip `<form>` is nested in a `<p>` (F-08). The h2 `id="reflect-heading"` is used
  for the section, but after an in-place swap there is no focus/live announcement.
- **Scroll and focus:** On the full page, boosted navigation starts at top. On the
  in-place HTMX path, the feedback is expected to replace the response form at the
  bottom of the practice page without changing URL or scroll; the user may need to
  scroll to see the start of the feedback, and keyboard focus is expected to be lost
  (F-03/F-04).
- **Findings:** F-03, F-04, F-05, F-08. The feedback copy and hierarchy are otherwise
  aligned with UX-001.

### 4.9 Reflection — `GET` and `POST /reflect`

- **Route / template:** `/reflect` → `reflection.html`.
- **User and primary intent:** Learner; write a short reflection carrying the feedback
  forward, or skip.
- **Entry and exit paths:** Entry from feedback Save. Exit on success to `/complete`;
  stays on the page on validation or persistence failure.
- **Actions:** Primary — Continue. Secondary — none visible (the server accepts a blank
  reflection as a skip). Destructive — none.
- **Content hierarchy:** Back subnav, h1, lede, optional intention echo, prompt,
  optional reflection questions, error panel, labelled textarea, Continue.
- **States:** Validation error and persistence error both re-render with the submitted
  content and `role="alert"`; persistence error returns HTTP 500. Blank/whitespace
  content is accepted by the application. No loading state.
- **Responsive:** Single narrow column; textarea 8 rows; action row simple.
- **Accessibility:** Labelled required textarea; error before the form. A required
  textarea prevents an intentionally empty submission in the browser even though the
  application accepts it (F-09).
- **Scroll and focus:** Boosted POST swaps the page. Errors render above the form and
  the page starts at top; content is preserved but focus is not moved to the error or
  textarea. Success redirects to `/complete` at top.
- **Findings:** F-09 (missing explicit skip / contradictory optionality), F-20 (focus
  after boosted error).

### 4.10 Completion — `GET /complete`

- **Route / template:** `/complete` → `complete.html`.
- **User and primary intent:** Learner; acknowledge completion and choose what next.
- **Entry and exit paths:** Entry after a successful reflection. Exit to a continuation
  activity intention, History, or Explore. Direct access without a completion redirects
  to `/`.
- **Actions:** Primary — continuation action when configured, otherwise History. Also
  "See your practice history" and "Back to explore". Destructive — none.
- **Content hierarchy:** h1, short completion note, detail message, optional
  continuation section (heading, transition copy, target title, action), then History
  and Explore actions.
- **States:** Continuation optional; no completion redirects to `/`. No loading, error,
  or validation state.
- **Responsive:** Single column; actions wrap; no confetti or progress mechanics.
- **Accessibility:** h1/h2 hierarchy; continuation section is labelled; buttons are
  links with clear names.
- **Scroll and focus:** Boosted navigation to top. No local updates.
- **Findings:** No unique finding. It is a strong reference for quiet completion copy.

### 4.11 History — `GET /history`

- **Route / template:** `/history` → `history.html`.
- **User and primary intent:** Learner; see what they have practised recently and
  revisit it.
- **Entry and exit paths:** Entry from the header nav, completion, review pages, Pulse
  saved notice, and story response review. Exit to `/history/{completion_id}`,
  `/history/story-responses/{response_id}`, Explore, or a JSON export download.
- **Actions:** Primary — open a completed practice. Secondary — open a story response,
  export history as JSON, back to Explore. Destructive — export is not destructive;
  no delete action.
- **Content hierarchy:** h1, lede, empty state or completed-practice list (title, date,
  preview, "Review this practice"), story responses section, export section, back to
  Explore.
- **States:** Empty completed practice with or without story responses; story-response
  storage unavailable notice; completed-practice loading failure renders the learner
  error page (500); no loading indicator; export data embedded as JSON and rendered by
  `export.js` on click.
- **Responsive:** One narrow reading column; list items stack; dates and previews wrap.
- **Accessibility:** Each list item is a full-card link with an h2/h3 title and date;
  story responses are distinguished by a labelled section and explanatory text. Export
  button is a real button. No pagination or filtering.
- **Scroll and focus:** Boosted navigation to top; export is a client download and
  does not navigate. Returning from review starts at top.
- **Findings:** F-19 (long undifferentiated list as history grows; optional but worth a
  decision), F-20 (focus after boosted navigation).

### 4.12 Practice review — `GET /history/{completion_id}`

- **Route / template:** `/history/{completion_id}` → `review.html`.
- **User and primary intent:** Learner; revisit the meaningful parts of one completed
  practice.
- **Entry and exit paths:** Entry from History. Exit to History, Explore, or the
  artifact binary route used by the sketch `<img>`. Invalid/unknown/other learner's
  completion renders the learner error page.
- **Actions:** Primary — "Back to your practice" (History). Secondary — "Go to
  explore", "Export this practice". Destructive — none.
- **Content hierarchy:** Breadcrumb, activity title, completion timestamp, observed
  stimulus, intention, sketch, response, feedback, reflection, export, navigation.
- **States:** Optional sections are omitted when absent. Persistence failure renders
  the learner error page; missing artifact bytes render a 404 page if navigated
  directly, while the review page renders the artifact section only when a reference
  exists. No loading/validation state.
- **Responsive:** Single reading column; stimulus and sketch images are fluid;
  navigation wraps; evidence blocks preserve whitespace and break long words.
- **Accessibility:** Section h2s, breadcrumb link, meaningful image alt text for
  stimulus; sketch alt is generic ("Uploaded sketch for this practice") and could be
  improved. Export button is a real button.
- **Scroll and focus:** Boosted navigation to top. Export is in-page. No local updates.
- **Findings:** F-19 (review is clear but History remains the only path back besides
  Explore), optional sketch alt-text polish.

### 4.13 Story response review — `GET /history/story-responses/{response_id}`

- **Route / template:** `/history/story-responses/{response_id}` →
  `story_response_review.html`.
- **User and primary intent:** Learner; revisit a private note saved from a Pulse story
  with its original context.
- **Entry and exit paths:** Entry from History. Exit to History or Pulse. Invalid UUID,
  missing repository, persistent failure, unknown response, and another learner's
  response all produce a learner error page (503 for unavailable storage, 404
  otherwise).
- **Actions:** Primary — back to History. Secondary — "More stories" (Pulse), "Read the
  original story" (external, only when a safe canonical URL exists). Destructive —
  none.
- **Content hierarchy:** Breadcrumb, story headline, saved timestamp, "What to try",
  "Your response", "Where this came from" (source and optional original link), privacy
  note, navigation.
- **States:** Error states as above; no loading/empty/validation state. The privacy
  note distinguishes a note from a completed practice.
- **Responsive:** Single reading column; evidence blocks wrap; nav buttons wrap.
- **Accessibility:** Clear headings, labelled nav, external link declares the new
  context through visible text. No score/grading language.
- **Scroll and focus:** Boosted navigation to top; no local updates.
- **Findings:** No unique finding. This is a strong model for distinguishing informal
  notes from formal practice.

### 4.14 Fashion & Design Pulse — `GET /pulse` and `POST /pulse/stories/{id}/responses`

- **Route / template:** `/pulse` → `news.html`; response POST re-renders `news.html`
  on error and redirects to `/pulse?saved=...#story-{id}` on success.
- **User and primary intent:** Learner; browse current curated stories, optionally
  save a private note to a "What to try" prompt, or turn a story prompt into a
  practice.
- **Entry and exit paths:** Entry from Stories nav, History notice, story response
  review ("More stories"), and story-linked practice requests. Exit to the original
  story (external), "Make this a practice" (`/practice/request?story=...`), a saved
  response in History, or the category filter URLs.
- **Actions:** Primary — read a story / save a response. Secondary — filter by
  category, open "Try this", "Make this a practice", read the original, revisit saved
  response. Destructive/irreversible — none.
- **Content hierarchy:** h1, lede, unavailable/saved notices, category chips with
  counts, story cards (image/credit, categories, headline, summary, relevance,
  optional prompt, "Try this" composer, practice link, source/date), empty panel.
- **States:** Feed unavailable (`role="status"` with "The Pulse is resting"), saved
  confirmation with a History link, category-empty state with a link to all stories,
  no-stories state, response validation/persistence error with the draft preserved and
  the composer reopened, loading/saving indicator, disabled submit during request.
  Story images are optional; missing images yield text-only cards.
- **Responsive:** Cards are one centred column below 56rem and two columns above; images
  are full-width with intrinsic dimensions; filter chips wrap; composer is a native
  `<details>`; practice/source actions wrap.
- **Accessibility:** Category chips use `aria-current="true"`; images have alt text and
  separate illustrative/source credit; external links use `rel="noopener noreferrer
  nofollow"`; composer is labelled; error is `role="alert"`; saving status is live.
  The selected filter state is conveyed by more than colour (weight/background/border).
- **Scroll and focus:** Category links are boosted page navigation → top. The response
  form is boosted (no explicit `hx-post`), so success is expected to swap the body and
  scroll to top; the redirect includes `#story-{id}`, but HTMX's boosted-form
  `show: top` is expected to win over the fragment. An error is expected to swap the
  body and return to top as well, even though the composer is reopened.
- **Findings:** F-06 (saved anchor likely not honoured), F-07 (error loses feed
  position), F-20 (focus after boosted navigation).

### 4.15 Learning guide reader — `GET /guides/{guide_id}` and return route

- **Route / template:** `/guides/{guide_id}` → `guide.html`; preview uses the same
  template with `preview=True`.
- **User and primary intent:** Learner; read an optional long-form guide associated with
  a practice, then return to the practice.
- **Entry and exit paths:** Entry from the practice guide invitation
  (`/guides/{id}?practice_id=...`), a direct link to a published guide, or the
  authoring preview. Exit via "Return to the practice"
  (`/guides/{id}/return-to-practice?practice_id=...`), the editor (preview only), or the
  primary nav. An unpublish/unknown guide produces a 404 learner error page.
- **Actions:** Primary — return to the practice (when associated). Secondary — jump to
  a section via the TOC, open external image sources, read the guide. Destructive —
  none.
- **Content hierarchy:** Optional subnav, guide header (eyebrow, title, summary,
  intended learner context), TOC with stage labels, sections (stage, heading, body,
  questions, possibilities, figures with captions/credits, reflection blockquote),
  footer return action.
- **States:** Published reader; preview banner when authoring; no loading/validation/
  empty state. A guide with no sections renders only the header/footer. Preview may
  show a return link even when the guide is not published (F-02).
- **Responsive:** Reading column; split layout for `guide-section--split` at ≥48rem;
  figures fluid and lazy-loaded; TOC links wrap; quote sections use display type.
- **Accessibility:** TOC nav is labelled and uses an ordered list; section headings are
  h2 with a stage line; images have alt text and source/creator credits; external
  credits open in a new tab with rel; anchor IDs are on sections. The TOC anchor
  scroll does not move focus to the section heading; this is a reading-position
  concern, not a broken link.
- **Scroll and focus:** Hash-only TOC links are not boosted (HTMX's boost rule
  excludes `href="#..."`), so native fragment scrolling applies. There is no sticky
  header, but there is also no `scroll-margin-top` on guide sections; a future sticky
  header would obscure anchor headings. Return-to-practice is a boosted GET that
  redirects to the practice page; it starts at the practice top and does not preserve
  any prior scroll position.
- **Findings:** F-02 (preview return link can 404 for a draft), F-20 (focus after
  boosted return), optional TOC focus/`scroll-margin` polish.

### 4.16 Authoring login — `GET` and `POST /authoring/login`

- **Route / template:** `/authoring/login` → `authoring_login.html`.
- **User and primary intent:** Internal author; authenticate to the protected
  workspace.
- **Entry and exit paths:** Entry from a direct link or a 401 on an authoring route.
  Exit to `/authoring` on success; stays on the page on an invalid secret.
- **Actions:** Primary — "Access Authoring Workspace". Secondary — back to practice.
  Destructive — none.
- **Content hierarchy:** Back subnav, h1, "Protected Practice Authoring (SEC-001)",
  explanation, error panel, labelled password input, submit.
- **States:** Invalid secret → 401 with `role="alert"`; already authenticated → redirect
  to workspace. No loading/empty/success state (success navigates).
- **Responsive:** Single narrow column; password input full width; button simple.
- **Accessibility:** `autofocus` on the secret field; `autocomplete="current-password"`;
  label and error; no CAPTCHA or multi-step confusion.
- **Scroll and focus:** Boosted form; an error is expected to swap the body and start
  at top. The secret field carries `autofocus`, but whether autofocus is honoured after
  an HTMX-inserted body swap is unverified. If it is, this is a useful reference for a
  post-error focus target.
- **Findings:** No unique finding. The `autofocus` pattern is a candidate reference for
  validation focus work.

### 4.17 Authoring workspace — `GET /authoring` and brief/generate actions

- **Route / template:** `/authoring` and `/authoring/` → `authoring.html`.
- **User and primary intent:** Internal author; draft a brief, generate candidate
  practices, see the candidate queue, and start Pulse curation.
- **Entry and exit paths:** Entry after login or nav. Exit to a generated candidate
  (`/authoring/candidates/{id}`), the Pulse page (`/authoring/pulse`), candidate queue
  filters (`/authoring?stage=...`), Learning Guides, or learner practice. Generation and
  draft errors stay on the workspace with values preserved.
- **Actions:** Primary — "Generate candidate practice". Secondary — draft the brief or
  one field, curate the Pulse, filter the queue, open a candidate. Destructive —
  none on this page (candidate actions live on the candidate page).
- **Content hierarchy:** Authoring nav, h1, lede, explanation of approval vs
  publication, error/outcome panels, Pulse section, authoring brief (AI draft, three
  required-field steps, optional details), candidate queue with stage filters and rows.
- **States:** Error `role="alert"`; success/outcome `role="status"`; draft
  assumptions/warnings caution panel (no live role); generation loading labels and
  live indicator; empty queue copy; filtered-empty queue with "Show all"; persistence
  outage message; AI-unavailable/generation failures preserve the brief.
- **Responsive:** Single column; required fields group into form sections; optional
  fields collapse into `<details>`; queue rows and filter chips wrap.
- **Accessibility:** Fieldsets/legends for brief steps; required labels include a
  visible "Required" marker; hints are linked with `aria-describedby` for some fields;
  per-field draft buttons are inside the field; filter chips use `aria-current`.
  The draft result has no live announcement (F-17). The AI-assist buttons rely on
  their visible labels and a text progress state.
- **Scroll and focus:** Page navigation is boosted → top. Brief draft and Pulse curate
  use explicit `hx-post` with `hx-target="#main" hx-select="#main"
  hx-swap="outerHTML"`, so they replace the main content without a full reload and
  without automatic top-scroll; the focused button is removed. Generate (no explicit
  `hx-post`) is boosted → success navigates to the candidate page at top, and errors
  swap the page at top. Queue filter links are boosted → top.
- **Findings:** F-10 (queue stage not preserved across draft/generate errors), F-11
  (Pulse curation target/URL mismatch), F-12 (authoring nav current state), F-17
  (draft result announcement), F-20 (focus after `#main` replacement).

### 4.18 Candidate detail — `GET /authoring/candidates/{id}` and candidate actions

- **Route / template:** `/authoring/candidates/{id}` → `authoring_candidate.html`.
- **User and primary intent:** Internal author; understand a candidate's state, review
  its content and checks, optionally revise it or select a stimulus, then approve,
  reject, publish, or withdraw.
- **Entry and exit paths:** Entry from the workspace queue or after generation. Exit to
  the candidate queue (`view.queue_url`), another candidate, or the workspace via
  authoring nav; JSON clients receive payloads instead of pages. Unknown candidate
  renders an authoring error page (404); storage failure renders 503.
- **Actions:** Primary — Approve for Library or Publish to Learner Library (depending
  on state). Secondary — edit draft, choose/remove stimulus, reject, withdraw, open
  revision history, back to queue. Destructive/irreversible — reject and withdraw are
  consequential and have no confirmation (F-14).
- **Content hierarchy:** Authoring nav, back to queue, title/status, error/outcome,
  "Where this candidate stands" (collapsed workflow details), content checks,
  generated content (preview + collapsed full content/brief), "Next step" actions,
  optional stimulus, "Revise this candidate" (collapsed edit form + history).
- **States:** Approvable/not approvable validation panels; content warnings; success
  messages after approve/reject/edit/stimulus/publish/withdraw; disabled Approve when
  validation fails; error pages for conflicts, invalid content, and storage failure;
  no explicit loading state (full-page submit). Stimulus section is absent when there
  is neither a stimulus nor a query; no-image note when search yields nothing.
- **Responsive:** Single column; details/summary sections; action group wraps; image
  option grid is auto-fit; definition lists wrap.
- **Accessibility:** Status tags, labelled sections, native details, checks use
  `role="alert"`/`role="status"` where appropriate. The "Next step" section carries
  `id="candidate-next-step"` and `scroll-margin-top`, but nothing links to it. The
  disabled Approve uses a `title` explanation, which is not reliably announced.
- **Scroll and focus:** All actions are plain full-page POSTs. `authoring-scroll.js`
  remembers the candidate URL and scroll offset before submit and restores it after
  the full page renders (also on `pageshow`/`DOMContentLoaded`), but it does not
  restore focus or the open/closed state of `<details>`. The edit form is inside a
  closed `<details>`; after a save the page re-renders with it collapsed again (F-13).
  Success/error messages render near the top, so with scroll restoration they may not
  be visible.
- **Findings:** F-12, F-13, F-14, F-20. The scroll script is a useful reference for
  targeted authoring context, but it is candidate-route-specific.

### 4.19 Authoring Pulse — `GET /authoring/pulse` and curation actions

- **Route / template:** `/authoring/pulse` → `authoring_news.html` with
  `news-curation-status.js`; the workspace also starts curation through
  `POST /authoring/pulse/curate`.
- **User and primary intent:** Internal author; review approved sources, start a
  curation batch, and read the durable job status and latest report.
- **Entry and exit paths:** Entry from authoring nav or the workspace Pulse action.
  Exit to learner Pulse, authoring nav, or a new curation run when the job is terminal.
- **Actions:** Primary — "Curate this week's news". Secondary — open a source, read the
  job report, navigate to learner Pulse. Destructive/irreversible — none; repeated runs
  are refused while a job is active.
- **Content hierarchy:** Authoring nav, h1, lede, explanation, error/availability
  panels, source list, curate button, job status panel with counters, latest report,
  diagnostics, source failures, rejections, failures.
- **States:** No sources configured; AI not configured; curation already in progress;
  dispatch/persistence failures; job status queued/running/succeeded/partially
  succeeded/failed/interrupted; temporary polling failure notice; counters updating;
  disabled button while active; job and report sections absent when not applicable.
- **Responsive:** Single column; counters use a responsive grid; definitions and lists
  wrap; long source URLs wrap.
- **Accessibility:** Job status uses `role="status" aria-live="polite"
  aria-atomic="true"`; progress counters are labelled by text; polling errors are shown
  in a hint region. The curation button has a text progress state. No estimated
  completion time is promised.
- **Scroll and focus:** `news-curation-status.js` polls with bounded delays and calls
  `window.location.reload()` when the job reaches a terminal state, which is expected
  to return the author to the top of the page; the report may be below the fold
  (F-16). From the workspace, the curation form uses `hx-target="#main"
  hx-select="#main" hx-swap="outerHTML"` but the returned document is the Pulse page,
  so the URL is expected to remain `/authoring` while the content becomes the Pulse
  page (F-11).
- **Findings:** F-11, F-12, F-16, F-20.

### 4.20 Learning Guides list — `GET /authoring/guides`

- **Route / template:** `/authoring/guides` → `authoring_guides.html`.
- **User and primary intent:** Internal author; create a guide, load pilot guides, and
  open an existing guide.
- **Entry and exit paths:** Entry from authoring nav. Exit to a new draft's editor via
  redirect, an existing editor, or another authoring area.
- **Actions:** Primary — "Create draft guide". Secondary — load initial pilot guides,
  open a guide. Destructive — none.
- **Content hierarchy:** Authoring nav, h1, lede, explanation that a guide never blocks
  a practice, error/outcome panels, create form, pilot action, guide list (title,
  status, version, section count, practice count), empty list.
- **States:** Empty list ("No learning guides yet"); store unavailable error; pilot
  seed success message or "already in the library"; required title validation by the
  browser; no loading state.
- **Responsive:** Single column; list rows wrap; forms stack.
- **Accessibility:** Labelled inputs and hints; real buttons; list links have clear
  names. The "Load initial pilot guides" action is adjacent to creation and could be
  mistaken for a routine step; it is described by the generic secondary button style.
- **Scroll and focus:** Boosted page navigation to top; create redirects to the editor
  at top; pilot seed re-renders the list at top.
- **Findings:** F-12 (no authoring current state), optional explanation of the pilot
  action's effect.

### 4.21 Guide editor — `GET /authoring/guides/{id}` and section/image actions

- **Route / template:** `/authoring/guides/{id}` → `authoring_guide.html`; image search
  returns `_guide_image_candidates.html` into `#candidates-{section_id}`.
- **User and primary intent:** Internal author; edit guide metadata and associations,
  manage ordered sections, attach attributed images, preview, publish, or archive.
- **Entry and exit paths:** Entry from the guide list or after creation. Exit to the
  list, learner preview, learner practice (preview return), or other authoring areas.
  Validation failures stay on the editor with errors.
- **Actions:** Primary — "Publish guide" (from the publication section). Secondary —
  save details, save section, add section, move up/down, remove section, search
  images, use image, save image details, remove image, preview, archive. Destructive/
  irreversible — remove section, remove image, archive; no confirmation (F-14).
- **Content hierarchy:** Authoring nav, guide nav (back to list, preview), title/status/
  version, error/outcome panels, validation errors/warnings, guide details and practice
  associations, sections in an ordered list (index/stage, heading, body, stage, layout,
  questions, examples, reflection prompt, save, reorder/remove, images, search),
  add-section form, publication actions.
- **States:** Draft/published/archived status; validation errors/warnings; save success
  messages; image search error/candidates/no-candidates; missing attribution blocks
  publication; publish failure 422; store failure 503; no loading state for most
  full-page actions, but image search is an in-place HTMX request.
- **Responsive:** Single column; sections are cards; image candidates auto-fit; action
  rows wrap; long textareas and lists stack.
- **Accessibility:** Fieldsets/legends for image/practice groups; labelled fields;
  status/validation panels use alert/status roles where provided; move up/down buttons
  are text, not icons. The page is long and has no outline or local section navigation;
  repeated "Save section" buttons are visually identical, so the current section relies
  on the surrounding card.
- **Scroll and focus:** All saves, moves, removes, image add/update/remove, publish,
  and archive are plain full-page POSTs. No scroll restoration applies (the script only
  matches candidate URLs), so each action is expected to reload the editor at the top
  despite the author working far down the page (F-01). Image search is the exception: it targets
  the section's candidate container, so the page should not jump and the search button
  remains. Publish validation errors render at the top, away from the publication
  section.
- **Findings:** F-01, F-02 (preview path), F-12, F-14, F-15, F-20.

### 4.22 Guide preview — `GET /authoring/guides/{id}/preview`

- **Route / template:** `/authoring/guides/{id}/preview` → `guide.html` with
  `preview=True`.
- **User and primary intent:** Internal author; see the learner presentation before
  publishing.
- **Entry and exit paths:** Entry from the editor. Exit to the editor via "Back to the
  guide editor" (subnav and footer), or to a practice via "Return to the practice"
  when the guide has associations.
- **Actions:** Primary — back to editor. Secondary — return to an associated practice,
  read sections via TOC. Destructive — none.
- **Content hierarchy:** Preview banner ("Draft preview..."), guide header, TOC,
  sections, footer back-to-editor.
- **States:** Preview banner is always shown; draft guides are explicitly not
  published; no validation/loading state. The return-to-practice link is rendered for
  any associated practice, even for a draft.
- **Responsive:** Same as the learner guide reader, in authoring context.
- **Accessibility:** Preview banner uses `role="status"`; the guide itself keeps learner
  semantics. Two "Back to the guide editor" links are harmless but redundant.
- **Scroll and focus:** Boosted navigation to top; TOC anchors are native. The
  return-to-practice link points at `/guides/{id}/return-to-practice`, which rejects
  unpublished guides with 404 (F-02).
- **Findings:** F-02.

### 4.23 Error pages — learner, authoring, and authentication

- **Route / template:** Handler-driven → `error.html` for learner routes,
  `authoring_error.html` for authoring routes, `authoring_login.html` for authoring
  401s; login page for unauthenticated authoring navigation.
- **User and primary intent:** Any user; understand that an action failed and recover.
- **Entry and exit paths:** Unknown activity/completion/guide/story/practice, storage
  failure, unhandled exception, authoring conflict/validation/storage failure. Exit to
  practice (learner) or the authoring workspace (author).
- **Actions:** Primary — "Back to practice" or "Back to the authoring workspace".
  Secondary — none. Destructive — none.
- **Content hierarchy:** h1 message, optional description, one recovery action.
- **States:** 400/401/404/409/422/429/500/502/503 depending on the route; the base HTMX
  config swaps 4xx/5xx responses, so boosted actions show the error page rather than
  leaving stale content.
- **Responsive:** Single column; same shell.
- **Accessibility:** One h1, one clear action, no stack traces; message and description
  are programmatic text (not automatically live-announced).
- **Scroll and focus:** Boosted errors are expected to swap the body and start at top;
  there is no focus move to the h1/error. A learner hitting an authoring route gets the
  login page instead of a learner error.
- **Findings:** F-20 (focus after error swap). Messages are honest and free of internal
  detail.

---

## 5. Findings register and priority

Priority reflects user impact and implementation dependency, following SPEC-046 §10:
input/context preservation, navigation clarity, accessibility, and reproducible
scroll/focus issues come before cosmetic polish.

| ID | Finding | Class | Priority | Affected surfaces |
| --- | --- | --- | --- | --- |
| F-01 | Guide editor saves, reorders, removes, and image changes are full-page POSTs with no scroll restoration; the author returns to the top of a long editor. | UR (high confidence) | P1 | `/authoring/guides/{id}` |
| F-02 | Guide preview renders "Return to the practice" for associated practices, but the return route 404s for an unpublished guide. | UR (high confidence source defect) | P1 | `/authoring/guides/{id}/preview`, `/guides/{id}/return-to-practice` |
| F-03 | Successful in-place practice feedback removes the focused submit button and does not move focus to the feedback heading/status. | UR (accessibility) | P1 | `/activities/{id}` + `/activities/{id}/submit` |
| F-04 | Successful submission replaces the response form inside `#submission-area` with the feedback partial. Because this is a targeted, non-boosted HTMX request, the browser retains the existing scroll position, which may leave the beginning of the feedback outside the viewport. | UR | P1 | `/activities/{id}/submit` |
| F-05 | The HTMX feedback state is not reflected in the URL/history; back/forward and refresh do not return to that feedback view. | UR | P2 | `/activities/{id}/submit` |
| F-06 | Pulse success redirects to `/pulse?saved=...#story-{id}`, but the response form is boosted and HTMX sets `show: top`; the saved story may not be brought into view. | UR | P2 | `/pulse` |
| F-07 | Pulse response validation/persistence errors re-render the whole feed and scroll to top; the reopened composer can be far from the learner's place in a long feed. | UR | P2 | `/pulse` |
| F-08 | Feedback Save/Skip row nests a `<form>` inside `<p class="form-actions">`, which is invalid HTML and may separate the Skip control from the action row. | UC / UR | P2 | `feedback.html`, `_feedback_partial.html` |
| F-09 | Reflection is optional server-side and the feedback page offers Skip, but the reflection page has no visible Skip and marks the textarea `required`, so the optionality is inconsistent. | UC | P2 | `/reflect` |
| F-10 | Workspace draft/generate actions do not preserve the active candidate-queue stage; `_render_workspace` reads only the request's `stage` query parameter and the forms do not carry it. | UR | P2 | `/authoring` |
| F-11 | The workspace "Curate this week's news" form targets `#main` but receives the Pulse page, so content changes while the URL stays `/authoring`; back/refresh do not match the visible page. | UR | P2 | `/authoring` → `/authoring/pulse/curate` |
| F-12 | Authoring navigation has no `aria-current`/current-section indication. *(Resolved in Slice 1 / #197 via explicit `authoring_section` and `aria-current="page"`.)* | Resolved (#197) | P2 | `_authoring_nav.html` |
| F-13 | Candidate edit and revision-history `<details>` re-render collapsed after save; scroll is restored but the working disclosure and focus are not. | UC / UR | P2 | `/authoring/candidates/{id}` |
| F-14 | Reject, withdraw, remove section, remove image, and archive have no confirmation and use the same quiet secondary style as non-destructive actions. | UC | P2 | Candidate and guide authoring |
| F-15 | The guide editor is one very long page with no outline, section navigation, or compact section summary. | UC | P2 | `/authoring/guides/{id}` |
| F-16 | Terminal Pulse job status triggers a full `window.location.reload()`, returning the author to the top; the final report can be below the fold. | UR | P2 | `/authoring/pulse` |
| F-17 | AI brief draft assumptions/warnings are rendered in a caution panel without a live role; draft completion has no status announcement. *(Resolved in Slice 1 / #197: caution panel carries `role="status"` and `.authoring-outcome` carries `data-focus-target role="status"`.)* | Resolved (#197) | P3 | `/authoring` |
| F-18 | Dashboard and mode-choice pages have no empty state if no activities are available (demo content normally prevents this). | OP / UC | P3 | `/`, `/practice` |
| F-19 | History is a single undifferentiated list with no grouping or filters as it grows; review has only History/Explore exits. | OP / UC | P3 | `/history` |
| F-20 | Boosted page navigation and boosted error swaps remove the focused element and do not move focus to the new page's h1/main; keyboard and screen-reader users may lose their place. *(Resolved in Slice 1 / #197 via `app/static/js/htmx-focus.js` and `[data-focus-target]` markers.)* | Resolved (#197) | P1 | Shared shell, all pages |
| F-21 | The review sketch image uses a generic alt text ("Uploaded sketch for this practice.") rather than describing the image. | OP | P3 | `/history/{completion_id}` |

### 5.1 What is intentionally not a finding

- No sticky header currently obstructs anchors; do not add `scroll-margin-top` broadly
  until a sticky element is introduced.
- No smooth-scroll or generic scroll-restoration script is present. That is good:
  SPEC-046 §7 warns against adding a generic restoration script to mask page-level
  causes.
- The practice response textarea, practice request form, and Pulse composer already
  preserve learner input on validation errors. That behaviour should be protected in
  every follow-up slice.
- Score/grade/mastery/streak language was not found in learner-facing templates.

---

## 6. Shared-pattern decisions recommended by this audit

These answer the open decisions in SPEC-046 §14. They are recommendations for
follow-up issues, not changes made here.

| Decision | Recommendation | Evidence |
| --- | --- | --- |
| Local section navigation vs progressive disclosure | **Both, by page purpose.** Guide editor: add a compact section outline and jump links; keep sections as cards rather than splitting into sub-pages yet. Candidate page: keep existing `<details>` but preserve open state across saves. Workspace brief: keep the current three-step fieldsets and optional disclosure. | F-01, F-13, F-15 |
| Segmented controls vs chips vs native controls | Keep **native selects** for the practice request (area, challenge, response form). Keep **link chips** for filters, but add an explicit selected-state pattern and preserve `aria-current`. Do not introduce custom segmented controls until a browser audit shows the native controls are the problem. | §3.5, §4.4, §4.14 |
| Whether an authoring workflow should be split into sub-pages | Not yet. First fix context preservation (scroll/focus/open state) and add local navigation. Splitting the guide editor is a larger decision that should follow evidence from the targeted fixes. | F-01, F-15 |
| Whether to add a shared scroll-restoration script | **No generic script.** Define a small shared HTMX focus/announcement policy, extend the existing candidate scroll pattern only where a full-page editor cannot be converted to a targeted swap, and cover each behaviour with tests. | F-03, F-05, F-20, `authoring-scroll.js` |
| Shared foundation vs page-specific | Shared: focus/status after swaps, current-nav state, destructive-action treatment, error focus, empty states. Page-specific: practice feedback handoff, Pulse anchor/return, guide editor outline, history grouping. | §5 |

---

## 7. Proposed implementation breakdown (mapped to SPEC-046)

Each slice should be a separate reviewable issue/PR with template tests and, where
practical, Playwright coverage.

### Slice 1 — Shared navigation, focus and status foundation (Implemented in #197)

**Covers:** F-20, F-12, F-03 (shared mechanism), F-17.
**SPEC-046:** §6.1, §6.2, §6.4, §6.5, §7.3, §8, §11.
**Implemented:**
- Added `app/static/js/htmx-focus.js` (loaded from `base.html`) to manage focus on `htmx:afterSettle` using `{ preventScroll: true }` and temporary `tabindex="-1"` cleanup on `blur`.
- Added explicit `authoring_section` (`workspace`, `guides`, `pulse`) and `aria-current="page"` in `app/templates/_authoring_nav.html` across `/authoring`, `/authoring/candidates/{id}`, `/authoring/guides`, `/authoring/guides/{id}`, `/authoring/pulse`, and authoring error pages.
- Added `data-focus-target` to authoring/learner error headings and authoring outcome/validation banners, and added `role="status"` to the brief draft assumptions/warnings caution panel (F-17), candidate content warnings panel, and practice `.loading-indicator`.
- Added web regression tests (`tests/web/test_ux_navigation_and_focus.py`, `tests/web/test_authoring_brief_draft.py`) and opt-in Playwright e2e coverage (`tests/e2e/test_htmx_focus_and_authoring_nav.py`) for desktop (`1280×800`) and mobile (`390×844`) viewports.

### Slice 2 — Practice input preservation and feedback handoff

**Covers:** F-03, F-04, F-05, F-08, F-09.
**SPEC-046:** §4.3, §6.3, §7.2–§7.4.
**Scope:** Keep the response in place on validation, move focus/announcement to the
error or feedback heading, bring the first feedback section into view without
discarding scroll context, fix the feedback Save/Skip row markup, and give the
reflection page an explicit Skip path consistent with the feedback panel. Acceptance:
a learner never loses typed work; a successful submission makes feedback immediately
visible; back/forward behaviour is documented and tested.

### Slice 3 — Discovery and practice selection clarity

**Covers:** F-18 and card affordance observations.
**SPEC-046:** §4.2, §6.3.
**Scope:** Add empty states where content can be absent, make the card's clickable
affordance unambiguous without turning the whole card into a control if that harms
screen-reader semantics, and keep the next action first on narrow screens. Acceptance:
dashboard and mode pages remain understandable with zero activities and on a 390px
viewport.

### Slice 4 — History and review scanning

**Covers:** F-19 and the review exit paths.
**SPEC-046:** §4.4, §6.3.
**Scope:** Add lightweight grouping or a filter/decision (not a gamified dashboard),
distinguish completed practice from story responses, and improve long-list scanning on
mobile. Acceptance: a learner with many completions can find a recent practice without
scrolling the entire list; the review still opens the same evidence.

### Slice 5 — Pulse and story-response continuity

**Covers:** F-06, F-07.
**SPEC-046:** §4.5, §6.3, §7.2.
**Scope:** Make the saved-response anchor a deliberate target (or replace it with an
in-place update that preserves feed position), keep the composer's place on
validation, and verify filter navigation. Acceptance: saving a response shows the
confirmation and the saved story together; a failed save keeps the learner at the same
card with the draft intact.

### Slice 6 — Learning Guide reading and return

**Covers:** F-02 (with Slice 8), TOC focus/scroll observations.
**SPEC-046:** §4.6, §6.2, §7.6.
**Scope:** Verify TOC anchors and focus/reading position on mobile; make the return
path explicit; ensure the guide remains optional and does not disturb in-progress
practice. Acceptance: a learner can move between sections and back to the practice
without losing context; anchor destinations are not obscured by future sticky UI.

### Slice 7 — Authoring workspace and candidate review

**Covers:** F-10, F-11, F-13, F-14 (candidate actions), F-17.
**SPEC-046:** §4.7, §6.4, §7.2, §7.7.
**Scope:** Preserve queue stage through draft/generate errors, make the Pulse action
navigate to a matching URL, preserve disclosure/focus around candidate saves, add
confirmation for consequential actions, and announce draft results. Acceptance: an
author can draft, generate, filter, and act on a candidate without losing the working
context or URL.

### Slice 8 — Learning Guide authoring

**Covers:** F-01, F-02, F-14 (guide actions), F-15.
**SPEC-046:** §4.7, §6.4, §7.7.
**Scope:** Add a compact guide outline/jump links and section summaries; preserve
scroll and focus across section saves, reorders, removals, image changes, and
publication; fix the preview return path; add confirmation for archive/remove.
Acceptance: every local save keeps the same section in view; preview never offers a
destination that 404s; publication errors are visible near the publication controls.

### Slice 9 — Cross-device and regression hardening

**Covers:** all scroll/navigation/focus scenarios in §8.
**SPEC-046:** §7, §11.
**Scope:** Add Playwright coverage for boosted navigation, back/forward, in-place
updates, validation focus/scroll, authoring local actions, and representative mobile/
tablet/desktop viewports; record manual checks for touch/keyboard/screen-reader and
reduced motion. Acceptance: no scroll/focus issue is marked resolved on code inspection
alone; each fix has either an automated regression test or a recorded manual check.

---

## 8. Browser verification plan

**Status:** not performed. No browser was launched for this audit, and no result below
should be read as confirmed. The environment has Linux and Chrome available; a
follow-up verification or Playwright task should run these scenarios and update the
classification to RD where a defect is confirmed.

### 8.1 Environment matrix

- Desktop: Chrome (current stable) at 1280×800 and 1440×900.
- Tablet: 768×1024, touch emulation.
- Mobile: 390×844 and 360×800, touch emulation, virtual keyboard visible when editing.
- Keyboard-only: Tab/Shift+Tab, Enter/Space, Escape where applicable.
- Zoom: 200% browser zoom; verify reflow and no horizontal page scroll.
- Motion: `prefers-reduced-motion: reduce`.
- Assistive technology: at minimum a screen-reader smoke check for headings, live
  regions, labels, and focus order.

### 8.2 Scenario register

| ID | Scenario | Expected | Current classification | Reproduction / check |
| --- | --- | --- | --- | --- |
| S1 | Scroll to the bottom of Explore, then activate a boosted link to an activity. | Destination starts at the top; focus is on the destination content or a sensible heading. | UR (F-20) | `page.goto("/")`; scroll to bottom; click "Explore"; record `window.scrollY`, `document.activeElement`, URL. |
| S2 | Navigate Practice → Stories → History, then use browser Back twice and Forward twice. | URL, scroll, and focus follow normal browser expectations; history cache does not show a stale state. | UR (F-20) | Record scroll positions and focused element after each back/forward; compare with a full reload. |
| S3 | Complete a practice response on the workspace and submit without JS disabled. | Feedback appears in place; the first feedback section is visible; focus lands on the feedback heading or status. | UR (F-03/F-04) | Submit; record `scrollY`, feedback bounding box, active element, URL, history length. |
| S4 | Submit an invalid/empty practice response; then a valid one with a server-side failure. | Error is visible near the response, the typed text survives, focus moves to the error or textarea, page does not jump to top. | UR (F-03) | Use whitespace-only or over-limit response; record active element/scroll and textarea value. |
| S5 | From Feedback, activate Skip reflection. | Completion page loads at top; no false error; URL is `/complete`. | UR | Submit the Skip form; record URL/scroll/focus. |
| S6 | Submit a reflection that triggers validation or persistence failure. | Error visible, content preserved, focus at the error/textarea, no unexpected top jump. | UR (F-20) | Force validation with invalid content or simulate persistence failure in a test app; record. |
| S7 | From the middle of a long Pulse feed, select a category filter. | Feed starts at top; active filter is announced; back returns to the previous scroll position. | UR | Scroll, click a filter chip, record scroll/focus; press Back. |
| S8 | Save a story response successfully. | Confirmation is visible and the saved story is brought into view; draft composer is closed/cleared consistently. | UR (F-06) | Save; record URL fragment, scroll, saved-story bounding box, active element. |
| S9 | Submit an empty/over-limit story response. | Error visible in the same card, composer remains open, draft preserved, card stays in view. | UR (F-07) | Submit invalid text; record card position, open state, scroll. |
| S10 | Open a guide, use each TOC link, and use Back. | Section heading is at the top (not under a sticky element), hash updates, focus is usable; Back restores reading position. | UR (TOC focus) | Click each TOC link; record `scrollY`, hash, active element; press Back. |
| S11 | Open a guide from a practice and return. | Practice page returns at the top; any in-progress draft is still available; the guide does not complete or skip practice. | UR (F-20) | Start practice, open guide, return; record URL, scroll, draft state. |
| S12 | Save a guide section that is far down the editor. | The same section remains in view; focus lands on the saved section or its status; no top jump. | UR (F-01) | Scroll to section 3, edit body, Save; record scroll, active element, status visibility. |
| S13 | Move a guide section up/down and remove a section. | The affected section/neighbour stays in view; confirmation is required for remove; status is announced. | UR (F-01/F-14) | Act on a middle section; record scroll/focus and confirmation. |
| S14 | Search images for a section. | Candidates replace only the target region; search button keeps focus; no page jump. | UR | Search; record scroll, focus, candidates region. |
| S15 | Publish a guide with validation errors. | Errors are visible near the publication controls or focused; the author is not returned to an unrelated top section. | UR (F-01) | Remove required content, Publish; record scroll/focus/error position. |
| S16 | Approve, reject, edit, and select a stimulus on a candidate. | Scroll returns to the same candidate region; success/error is announced; edit disclosure state is predictable. | UR (F-13/F-14) | For each action, record scroll, active element, message visibility, details open state. |
| S17 | Draft the brief/one field, then generate a candidate with an error. | Fields update/preserve; active queue stage survives; error is announced; page does not lose the brief. | UR (F-10/F-17) | Draft, select a stage, submit invalid generation; record stage, values, scroll/focus. |
| S18 | Start Pulse curation from the workspace, then use Back/Forward. | Visible page and URL match; Back returns to the workspace; the accepted job is not lost. | UR (F-11) | Click Curate from `/authoring`; record URL/content; use Back/Forward. |
| S19 | Leave the Pulse page while a job runs, return later, and let it finish. | Job status is retrieved; terminal report is visible without losing the author's place unnecessarily. | UR (F-16) | Start job, navigate away/back, wait for terminal state; record reload/scroll/focus/report. |
| S20 | On mobile, focus the practice textarea, request textarea, and guide editor fields with the keyboard open. | The field and submit action remain reachable; no horizontal overflow; viewport changes do not jump. | UR | Emulate 390×844 and 360×800; record scroll, element visibility, `document.documentElement.scrollWidth`. |
| S21 | Keyboard-only tour of the shared shell and each page's primary action. | Skip link, nav, cards, forms, details, filters, and actions are reachable with visible focus in a sensible order. | UR | Tab through; record focus order and any traps. |
| S22 | Reduced motion and 200% zoom. | No motion beyond the reduced-motion rule; content reflows without horizontal page scroll; anchors/focus remain usable. | UR | Emulate media query and zoom; record overflow and focus visibility. |

### 8.3 Recording rules

- Record browser, version, viewport, input type, and whether JavaScript/HTMX was
  enabled.
- Record `window.scrollY`, `document.activeElement`, URL, and the bounding box of the
  updated region before and after each action.
- Only mark an entry RD when the observed behaviour contradicts the expected behaviour
  in a real browser with reproducible steps.
- Update this document's finding register and the relevant follow-up issue with the
  result; do not add a generic scroll fix before the cause is known.

---

## 9. Coverage and acceptance mapping

| Issue #195 acceptance criterion | Where it is covered |
| --- | --- |
| Current routes and templates verified against the default branch | §2 (route/template inventory; HEAD recorded in the header) |
| Learner and authoring/admin experiences both covered | §2.2, §2.3, §4.1–§4.23 |
| Every page/state has the required fields, with N/A marked | §4 (each entry lists all fields; absent states are stated explicitly) |
| Shared interaction patterns and inconsistencies documented | §3, §5, §6 |
| Scroll/navigation/focus described and potential defects classified | §3.2, §4 (per page), §5, §8 |
| Browser verification status and environment recorded honestly | §1.1, §8.1 |
| Findings prioritised by user impact and dependency | §5, §7 |
| Practical sequence of follow-up slices | §7 |
| No application behaviour or styling changed | This change adds only documentation files; see §10 |

### 9.1 What changed in this issue

- Added `docs/ux/UX-003-whole-app-ux-audit.md` (this document).
- Added a discoverability link from `docs/index.md`.
- Updated SPEC-046's tracking-issue reference to issue #195.

No route, template, stylesheet, script, test, or runtime behaviour was changed.

---

## 10. Follow-up issue seeds

The following titles are ready to become GitHub issues after review. Each should
reference this document and the relevant SPEC-046 section.

1. **Define the shared post-swap focus and status policy**
2. **Keep practice feedback visible and keyboard-accessible after submission**
3. **Make reflection's optional skip path explicit and consistent**
4. **Preserve the author's position across Learning Guide editor saves**
5. **Fix the draft-guide preview return path**
6. **Preserve the candidate queue stage across workspace draft/generate errors**
7. **Add confirmation and status feedback for consequential authoring actions**
8. **Add a compact outline and section navigation to the guide editor**
9. **Honour the saved-story anchor on the Pulse**
10. **Add browser regression coverage for navigation, history, focus, and local authoring actions**

Each seed should be scoped independently; do not combine domain/persistence changes
with these presentation fixes.

---

## 11. Links

- [SPEC-046 — Whole-App UX, UI, Navigation and Scroll Refinement](../../specifications/platform/SPEC-046-whole-app-ux-ui-navigation-scroll-refinement.md)
- [Issue #195 — SPEC-046 Phase 1: Audit and document the whole-app UX](https://github.com/h3xh4wk/fablit/issues/195)
- [UX-001 — Fablit Learner Experience Direction](../UX-001-fablit-experience.md)
- [UX-002 — Fablit Visual Language & Interaction Guidelines](UX-002-fablit-visual-language-and-interaction-guildelines.md)
- [Architecture Blueprint](../architecture/architecture_blueprint.md)
