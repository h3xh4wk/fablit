/* Shared focus policy for HTMX swaps (SPEC-046 §7.3, §8 / #197).
 *
 * Focus management and scroll positioning are distinct:
 * - Boosted page navigation or full-body replacement moves focus to an
 *   explicit [data-focus-target], an enabled [autofocus] control, or the
 *   new page's main heading (#main h1, falling back to #main).
 * - Targeted #main replacement (e.g. brief drafting or Pulse curation)
 *   moves focus to [data-focus-target] within #main, or #main h1 / #main,
 *   because the triggering control inside the previous #main was replaced.
 * - Smaller targeted in-place updates move focus only when the swapped
 *   fragment explicitly declares [data-focus-target] (or on an error swap).
 *   Background status polling and unopted partial updates never steal focus.
 * - All programmatic focus calls use { preventScroll: true } so page scroll
 *   and candidate scroll restoration (authoring-scroll.js) stay intentional.
 */
(() => {
  "use strict";

  const NATIVE_FOCUSABLE =
    "a[href], button:not([disabled]), input:not([disabled]):not([type='hidden']), " +
    "select:not([disabled]), textarea:not([disabled]), summary, [tabindex]";

  function focusElement(element) {
    if (!(element instanceof HTMLElement)) return;

    const addedTabIndex = !element.matches(NATIVE_FOCUSABLE);
    if (addedTabIndex) {
      element.setAttribute("tabindex", "-1");
    }
    element.setAttribute("data-htmx-focused", "true");

    const cleanup = () => {
      element.removeAttribute("data-htmx-focused");
      if (addedTabIndex && element.getAttribute("tabindex") === "-1") {
        element.removeAttribute("tabindex");
      }
    };
    element.addEventListener("blur", cleanup, { once: true });

    try {
      element.focus({ preventScroll: true });
    } catch (_error) {
      element.focus();
    }
  }

  function resolveAnchorTarget(detail) {
    const rawAnchor =
      (detail && detail.pathInfo && detail.pathInfo.anchor) || "";
    const anchorId = rawAnchor.replace(/^#/, "");
    if (!anchorId) return null;
    return document.getElementById(anchorId);
  }

  function resolveExplicitTarget(root) {
    if (!(root instanceof Element)) return null;
    if (root.hasAttribute("data-focus-target")) return root;
    return root.querySelector("[data-focus-target]");
  }

  function resolveLiveRoot(root) {
    if (root instanceof Element && root.isConnected) {
      return root;
    }
    if (root instanceof Element && root.id) {
      const byId = document.getElementById(root.id);
      if (byId) return byId;
    }
    return document.getElementById("main") || document.body;
  }

  function resolveMainTarget(scope) {
    const liveScope = resolveLiveRoot(scope);
    const main =
      liveScope instanceof Element && liveScope.id === "main"
        ? liveScope
        : document.getElementById("main") || liveScope;
    if (!(main instanceof Element)) return null;

    const explicit = resolveExplicitTarget(main);
    if (explicit) return explicit;

    const autofocus = main.querySelector(
      "input[autofocus]:not([disabled]), textarea[autofocus]:not([disabled]), select[autofocus]:not([disabled])",
    );
    if (autofocus instanceof HTMLElement) return autofocus;

    const heading = main.querySelector("h1");
    if (heading instanceof HTMLElement) return heading;

    return main instanceof HTMLElement ? main : null;
  }

  function resolveErrorTarget(target) {
    const root = resolveLiveRoot(target);
    if (!(root instanceof Element)) return null;

    const explicit = resolveExplicitTarget(root);
    if (explicit) return explicit;

    const alert = root.querySelector('[role="alert"]');
    if (alert instanceof HTMLElement) return alert;

    const heading = root.querySelector("h1");
    if (heading instanceof HTMLElement) return heading;

    return resolveMainTarget(root);
  }

  function resolveSettledTarget(event, detail) {
    const eventTarget =
      event.target instanceof Element && event.target.isConnected
        ? event.target
        : null;
    const detailTarget =
      detail.target instanceof Element ? detail.target : null;

    if (eventTarget) return eventTarget;
    if (detailTarget && detailTarget.isConnected) return detailTarget;
    if (detailTarget && detailTarget.id) {
      const liveById = document.getElementById(detailTarget.id);
      if (liveById) return liveById;
    }
    return event.target instanceof Element ? event.target : detailTarget;
  }

  function handleAfterSettle(event) {
    const detail = event.detail || {};
    const target = resolveSettledTarget(event, detail);
    if (!target) return;

    const rawTarget =
      detail.target instanceof Element ? detail.target : target;

    const anchorTarget = resolveAnchorTarget(detail);
    if (anchorTarget) {
      focusElement(anchorTarget);
      return;
    }

    const isBodySwap =
      target === document.body || rawTarget === document.body;
    const isMainSwap = target.id === "main" || rawTarget.id === "main";
    const isFailedSwap = Boolean(detail.failed);

    if (isFailedSwap) {
      const errorTarget = resolveErrorTarget(target);
      if (errorTarget) focusElement(errorTarget);
      return;
    }

    if (isBodySwap || isMainSwap) {
      const mainTarget = resolveMainTarget(target);
      if (mainTarget) focusElement(mainTarget);
      return;
    }

    const explicitTarget = resolveExplicitTarget(target);
    if (explicitTarget) {
      focusElement(explicitTarget);
    }
  }

  document.addEventListener("htmx:afterSettle", handleAfterSettle);
})();
