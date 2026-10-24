/* Restore the authoring candidate's reading position after an action.
 *
 * Candidate actions can be handled by HTMX or by a full-page form submission.
 * Remember the candidate identity and scroll offset, then restore only when the
 * response still belongs to that candidate.
 */
(() => {
  "use strict";

  const storageKey = "fablit-authoring-candidate-scroll";
  const candidateId = (path) =>
    path.match(/^\/authoring\/candidates\/([^/]+)(?:\/.*)?\/?$/)?.[1] ?? null;

  function rememberPosition() {
    const id = candidateId(window.location.pathname);
    if (!id) return;
    try {
      window.sessionStorage.setItem(
        storageKey,
        JSON.stringify({ candidateId: id, scrollY: window.scrollY }),
      );
    } catch (_error) {
      // Scroll restoration is a convenience; blocked storage must not break actions.
    }
  }

  function restorePosition() {
    const id = candidateId(window.location.pathname);
    if (!id) return;
    try {
      const raw = window.sessionStorage.getItem(storageKey);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (saved.candidateId !== id || !Number.isFinite(saved.scrollY)) {
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
