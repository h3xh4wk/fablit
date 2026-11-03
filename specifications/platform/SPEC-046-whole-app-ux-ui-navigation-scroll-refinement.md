# SPEC-046: Whole-App UX, UI, Navigation and Scroll Refinement

**Status:** Proposed
**Owner:** Fablit product
**Related architecture:** ARCH-001, SEC-001
**Related specifications:** SPEC-041, SPEC-042, SPEC-043, SPEC-044, SPEC-045
**Tracking issue:** To be created

## 1. Overview and goal

Conduct a systematic UX and UI review of the entire Fablit application and refine the experience so that it feels easier to understand, navigate, and use across mobile, tablet, and desktop.

The objective is not to replace Fablit's visual identity or introduce a fashionable design system for its own sake. Fablit already has a warm-neutral, editorial visual language that suits a fashion and design learning product. The work should preserve and strengthen that identity while improving hierarchy, consistency, interaction clarity, responsive behaviour, accessibility, and especially scroll continuity.

The review must cover both sides of the product:
- Learner-facing discovery, practice, reflection, history, stories, personalised practice, and Learning Guides.
- Authoring and administrative workflows for practice content, stories, and Learning Guides.

Every user-facing page and meaningful state should be inventoried and documented before implementation. Recommendations must be grounded in the actual page purpose and workflow, not applied as a generic visual refresh.

## 2. Product principles

1. **Clarity before decoration.** A learner or author should understand where they are, what they can do next, and what will happen when they act.
2. **Preserve Fablit's identity.** Retain the warm-neutral editorial direction, typography character, whitespace, and visual restraint. Improve consistency rather than replacing the brand.
3. **Design around real tasks.** Controls and layouts should reflect the decisions users actually make on each page.
4. **Reduce cognitive and interaction load.** Avoid unnecessary choices, repeated information, long undifferentiated forms, and ambiguous actions.
5. **Mobile-first, responsive by design.** Important workflows must remain comfortable on narrow screens and usable with touch, keyboard, and assistive technology.
6. **Predictable navigation and scrolling.** Page navigation, in-page actions, browser history, and dynamic updates must each have deliberate, consistent scroll behaviour.
7. **Use native controls when they are best.** Modernise presentation and interaction where useful, but do not replace accessible native controls with custom controls merely for appearance.
8. **Incremental and testable.** Prefer shared improvements and coherent implementation slices over a risky full-app rewrite.

## 3. Goals

- Establish a complete inventory of user-facing pages, page states, and primary user journeys.
- Document each page's purpose, user intent, primary and secondary actions, content hierarchy, navigation, responsive behaviour, accessibility considerations, and scroll expectations.
- Identify duplicated or inconsistent patterns in navigation, buttons, forms, filters, feedback, cards, dialogs/expanders, and status messages.
- Improve the ease of discovering and starting a practice, completing it, reviewing progress, and using supporting learning content.
- Make authoring workflows easier to scan and operate, particularly long workspaces and section-based editors.
- Investigate and resolve reproducible scroll-position loss, unexpected jumps, focus loss, and awkward long-page navigation.
- Define reusable UI patterns and acceptance checks so new features remain consistent.

## 4. Scope and page inventory

The following is the initial page inventory based on the current route and template structure. During implementation, verify it against the current default branch and include meaningful empty, error, loading, success, and validation states. Do not treat this list as proof that every route has been exhaustively browser-tested.

### 4.1 Shared application shell
- Shared base layout, header, navigation, page container, footer (where present), global notices, and responsive navigation.
- Global typography, spacing, colour, surfaces, focus indicators, buttons, form controls, and link styles.
- Navigation state, active-page indication, browser back/forward behaviour, and page-level scroll policy.

### 4.2 Learner: discovery and practice selection
- Dashboard/home.
- Practice mode selection.
- Practice activities/catalogue for a selected mode.
- Practice request form and requested-practice detail.

Review whether the next useful action is visually obvious, whether practice choices are easy to compare, and whether filters or selection controls are appropriate for the number and type of choices.

### 4.3 Learner: completing a practice
- Practice intention.
- Practice prompt/activity.
- Submission and feedback.
- Reflection.
- Completion/next-step state.

Review the end-to-end journey as one experience. Preserve entered work across navigation and validation errors. Make primary actions, optional actions, progress cues, and completion states clear without distracting from the creative task.

### 4.4 Learner: history and review
- History list and its empty state.
- Practice completion detail/review.
- Saved story-response review.
- Artifact or submitted-work viewing where available.

Review scanning, grouping, filters, return paths, and whether users can distinguish completed practices, informal story responses, and other saved work.

### 4.5 Learner: Fashion & Design Pulse
- Pulse feed, category filters, story cards, and story detail/expanded states where present.
- Story-linked “Try this” response composer and its saved/review experience.

Review editorial hierarchy, filter affordance, card actions, composer visibility, and the difference between a lightweight private response and a formal practice.

### 4.6 Learner: Learning Guides
- Guide entry point from an associated practice.
- Published guide reader, section navigation, image/caption treatment, and return-to-practice action.

Review long-form reading comfort, section navigation on mobile, anchor/focus behaviour, and preservation of the in-progress practice when entering and leaving a guide.

### 4.7 Authoring and administration
- Authoring login.
- Authoring workspace and practice brief/draft generation.
- Candidate queue/list and candidate detail/review/edit/approval/publish states.
- Pulse curation workspace and curation-job visibility.
- Learning Guide list, creation, editor, section management, image search/selection, preview, publish, and archive.

Review the authoring experience as a set of focused tasks. Reduce long, undifferentiated pages; provide clear section hierarchy and orientation; keep related actions close to the content they affect; and ensure that saves, reorders, image searches, validation, and publication do not unexpectedly displace the author.

## 5. Required UX audit and documentation

Create a page-by-page UX inventory in the repository documentation. The exact documentation location may follow existing repository conventions, but it must be discoverable and maintained alongside the relevant implementation.

For each page or distinct workflow state, document:

- Page/route and template or component responsible.
- User type and primary user intent.
- Entry points and expected exit/return paths.
- Primary action, secondary actions, and destructive or irreversible actions.
- Content hierarchy and what should be visible first.
- Existing interaction patterns and any proposed control changes.
- Loading, empty, error, success, and validation states that apply.
- Desktop, tablet, and mobile layout considerations.
- Keyboard, focus, screen-reader, contrast, touch-target, and reduced-motion considerations as relevant.
- Expected scroll behaviour for initial load, page navigation, in-page actions, dynamic updates, anchors, and browser back/forward.
- Findings, rationale, proposed change, and acceptance criteria.

The audit should distinguish:
- Confirmed defects reproduced in a browser.
- Usability concerns observed during inspection.
- Source-level risks or hypotheses that still require reproduction.
- Optional visual polish that does not materially improve task completion.

Do not describe a source-level suspicion as a confirmed runtime bug.

## 6. Interaction and visual refinement

### 6.1 Shared controls and patterns

Review and standardise the following where they occur:
- Primary, secondary, tertiary, and destructive buttons, including consistent labels and disabled/loading states.
- Text inputs, textareas, selects, checkboxes, radio groups, and validation/error messages.
- Segmented controls for short, mutually exclusive choices where appropriate.
- Filter chips/tabs with clear selected state and accessible semantics.
- Cards and selectable cards with obvious interaction affordance and selected state.
- Expand/collapse patterns for optional or advanced content.
- Save, publish, archive, approve, reject, and other workflow status feedback.
- Image candidate previews, selection, replacement, attribution, and text-only fallback.
- Confirmation for destructive or difficult-to-reverse actions where justified.

Use native HTML controls unless a custom interaction provides a clear usability benefit and can meet accessibility requirements. Avoid introducing a heavyweight UI framework without a separate architecture decision.

### 6.2 Visual hierarchy and page composition

- Establish consistent page titles, supporting descriptions, section headings, breadcrumbs or contextual navigation where helpful, and action placement.
- Make primary actions visually distinct without overusing high-emphasis styles.
- Break long pages into meaningful sections with clear headings and useful local navigation or progressive disclosure.
- Keep important actions visible and reachable on mobile without covering content or creating excessive sticky UI.
- Use whitespace and typography to improve scanning, not to create unnecessarily tall pages.
- Ensure cards, form groups, and editorial sections have consistent spacing and alignment.
- Preserve Fablit's warm-neutral editorial visual identity and existing design tokens unless the audit demonstrates a specific issue.

### 6.3 Learner experience

- Make the next step clear on the dashboard and at the end of each major learner journey.
- Keep practice prompts and learner-created work visually central.
- Avoid distracting controls during focused practice.
- Distinguish required from optional inputs and explain why information is requested.
- Make errors actionable and preserve user input.
- Keep Learning Guides and Pulse interactions optional and clearly separate from formal practice completion.
- Ensure practice history and saved responses are easy to distinguish and revisit.

### 6.4 Authoring experience

- Break complex authoring workspaces into clear task-oriented sections or steps where this reduces cognitive load.
- Consider a compact page outline, section navigation, collapsible advanced settings, or focused sub-pages for especially long editors.
- Keep the current item/section and its actions visually connected.
- Provide clear save/publish status and validation feedback near the affected content.
- Preserve context after save, reorder, remove, image search, image selection, preview, and other local actions.
- Do not hide essential actions behind hover-only interactions.
- Avoid unnecessary full-page reloads when a targeted update is safer and clearer.

## 7. Scroll, navigation, and focus behaviour

Scroll issues are a first-class part of this specification and must be investigated with browser-level reproduction rather than addressed by adding a generic scroll-restoration script.

Define and implement an explicit scroll policy:

1. **New page navigation:** navigation to a different page should normally begin at the top, unless the destination contains an explicit anchor or documented continuation point.
2. **In-page actions:** saving, filtering, expanding, collapsing, reordering, selecting an image, or updating a local section should preserve the user's context and avoid unexpected jumps.
3. **Targeted dynamic updates:** when content is replaced or inserted, preserve the relevant section/card position; where appropriate, move keyboard focus to the updated region or its status message.
4. **Validation errors:** bring the first invalid field or error summary into view and focus it appropriately without discarding entered data.
5. **Browser back/forward:** respect expected browser history and scroll restoration; do not override native behaviour with competing scripts.
6. **Anchor navigation:** section links should account for sticky headers, update focus/URL where appropriate, and work with keyboard and assistive technology.
7. **Long authoring pages:** local actions must not return the author to the top or a different section without an explicit reason.
8. **Mobile:** verify behaviour with touch scrolling, virtual keyboards, dynamic viewport changes, and responsive navigation.

Audit global HTMX boosting/swapping, targeted HTMX updates, browser history integration, and existing custom scroll scripts together. Avoid overlapping scroll-restoration mechanisms. Prefer targeted swaps and stable context markers over broad body replacement when feasible. Any scroll behaviour change must be covered by automated tests where practical and a documented manual browser test.

## 8. Accessibility and responsive requirements

- All interactive elements must be keyboard reachable and have visible focus.
- Controls must have programmatic labels and appropriate semantics.
- Custom segmented controls, tabs, menus, and expanders must expose correct roles and state.
- Colour must not be the only means of conveying selected, error, or status states.
- Maintain sufficient text and control contrast.
- Touch targets should be comfortable on mobile; avoid tightly packed icon-only actions.
- Content must reflow without horizontal page scrolling at supported narrow widths, except for intentionally scrollable content with an accessible alternative.
- Images require appropriate alt text; decorative images must not create redundant announcements.
- Respect reduced-motion preferences.
- Sticky headers, toolbars, and overlays must not obscure focused controls or anchor destinations.
- Forms must remain usable with mobile keyboards and screen zoom.

## 9. Technical constraints

- Preserve the existing FastAPI + HTMX/server-rendered application architecture.
- Reuse the existing CSS design tokens and shared templates where appropriate.
- Prefer small, reusable CSS/HTMX/JavaScript patterns over introducing a new frontend framework.
- Do not change business rules, persistence contracts, anonymous learner identity, privacy boundaries, or practice lifecycle semantics as part of visual refinement.
- Do not introduce new mandatory login, analytics collection, or learner tracking.
- Keep progressive enhancement and server-rendered fallbacks where the current architecture supports them.
- Avoid broad rewrites that combine unrelated workflow or domain changes with the UX work.

## 10. Implementation approach

Deliver in reviewable slices. The exact issue/PR breakdown can be refined after the audit, but the recommended sequence is:

1. **Audit and shared foundation:** complete page inventory, interaction pattern inventory, responsive/accessibility baseline, and shared shell/control improvements.
2. **Core learner journeys:** dashboard, discovery, practice selection, practice completion, feedback, reflection, and completion.
3. **Learning and revisit journeys:** history/review, Pulse/story responses, personalised practice, and Learning Guides.
4. **Authoring workflows:** workspace/candidate review, Pulse curation, and Learning Guide authoring.
5. **Navigation, scroll, and regression hardening:** resolve reproduced issues, test browser history and focus, and complete cross-device checks.

The audit may reorder slices based on severity and shared dependencies. Fixes that prevent loss of learner input or authoring context should be prioritised over cosmetic changes.

## 11. Testing and verification

- Add or update template/rendering tests for shared controls, labels, active states, empty/error/success states, and responsive class/structure where appropriate.
- Add browser-level tests for critical learner and authoring journeys.
- Test page navigation versus local HTMX actions separately.
- Test save/reorder/image-search actions on long authoring pages and verify the same section remains in context.
- Test validation failures preserve user input and expose the first actionable error.
- Test browser back/forward and explicit anchor navigation.
- Check keyboard-only operation, focus visibility/order, and screen-reader semantics for custom controls.
- Verify representative narrow mobile, tablet, and desktop viewports.
- Respect reduced-motion settings.
- Record manual checks where automation is not practical. Do not mark a scroll issue resolved based only on code inspection.

## 12. Acceptance criteria

- [ ] A discoverable, maintained page-by-page UX inventory covers all current learner and authoring routes and meaningful states.
- [ ] Each page entry documents purpose, user intent, actions, hierarchy, responsive/accessibility concerns, and expected scroll behaviour.
- [ ] The audit labels findings as reproduced defects, observed usability concerns, unverified source-level risks, or optional polish.
- [ ] Shared controls and interaction patterns are more consistent without replacing Fablit's existing editorial visual identity.
- [ ] Learner journeys make the next action clear and preserve learner input through validation and navigation.
- [ ] Authoring workflows are easier to scan and local actions preserve the author's working context.
- [ ] Scroll policy is explicit and implemented consistently for navigation, local updates, validation, anchors, and browser history.
- [ ] Reproduced scroll/focus issues have regression coverage or documented manual verification.
- [ ] Responsive layouts work at representative mobile, tablet, and desktop widths without unintended horizontal overflow.
- [ ] Keyboard navigation, focus indicators, labels, contrast, touch targets, and reduced-motion behaviour are checked.
- [ ] No business rules, privacy boundaries, anonymous identity behaviour, or persistence contracts are changed unintentionally.
- [ ] Implementation is delivered in reviewable slices with tests and updated documentation.

## 13. Out of scope

- Rebranding or replacing the visual identity.
- Rewriting the application in React, Vue, or another frontend framework.
- Introducing a large component library solely for visual novelty.
- Adding unrelated product capabilities or changing learning methodology.
- Adding analytics or tracking beyond existing approved mechanisms.
- Fixing unrelated backend defects unless they directly prevent the documented UX requirement; such work should be tracked separately.

## 14. Open decisions

The audit should make evidence-based recommendations on:
- Which pages benefit from local section navigation versus progressive disclosure.
- Which controls should become segmented controls, chips, or selectable cards, and where native controls remain preferable.
- Whether any authoring workflow should be split into focused sub-pages.
- Which scroll defects are caused by HTMX swap strategy, browser history handling, custom scripts, or individual page structure.
- Which improvements should be shared foundation work versus page-specific refinements.

These decisions should be recorded in the page inventory and implementation plan before broad changes are made.
