/* Restore the authoring candidate's reading position after an action.
 *
 * The authoring workspace uses boosted server-rendered forms and can also fall
 * back to normal full-page form submissions. Store only the current route and
 * scroll offset, and consume the saved position once the response is rendered.
 */
(() => {
  "use strict";

  const storageKey = "fablit-authoring-candidate-scroll";
  const candidatePath = (path) => /^\/authoring\/candidates\/[^/]+\/?$/.test(path);

  function rememberPosition() {
    if (!candidatePath(window.location.pathname)) return;
    try {
      window.sessionStorage.setItem(
        storageKey,
        JSON.stringify({
          path: window.location.pathname,
          scrollY: window.scrollY,
        }),
      );
    } catch (_error) {
      // Scroll restoration is a convenience; blocked storage must not break actions.
    }
  }

  function restorePosition() {
    if (!candidatePath(window.location.pathname)) return;
    try {
      const raw = window.sessionStorage.getItem(storageKey);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (saved.path !== window.location.pathname || !Number.isFinite(saved.scrollY)) {
        window.sessionStorage.removeItem(storageKey);
        return;
      }
      window.sessionStorage.removeItem(storageKey);
      window.requestAnimationFrame(() => {
        window.scrollTo({ top: saved.scrollY, left: 0, behavior: "auto" });
      });
    } catch (_error) {
      // Ignore malformed or unavailable session storage.
    }
  }

  document.addEventListener("submit", (event) => {
    if (event.target instanceof HTMLFormElement &&
        event.target.action.includes("/authoring/candidates/")) {
      rememberPosition();
    }
  }, true);

  document.addEventListener("htmx:beforeRequest", (event) => {
    const source = event.detail && event.detail.elt;
    if (source && (source.closest("form[action*='/authoring/candidates/']") ||
        source.matches("form[action*='/authoring/candidates/']"))) {
      rememberPosition();
    }
  });

  document.addEventListener("htmx:afterSettle", restorePosition);
  window.addEventListener("pageshow", restorePosition);
  document.addEventListener("DOMContentLoaded", restorePosition);
})();
