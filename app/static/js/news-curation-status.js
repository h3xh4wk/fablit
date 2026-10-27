/* Durable author-facing Pulse status (SPEC-042 / #166).
 *
 * Status belongs to the server-side job, not the page. Polling is read-only:
 * transient fetch errors never cancel or alter the accepted job.
 */
(() => {
  "use strict";

  const POLL_DELAYS_MS = [2500, 5000, 10000];
  const COUNTERS = {
    sources_processed: "curation-sources-processed",
    sources_configured: "curation-sources-total",
    sources_failed: "curation-sources-failed",
    items_fetched: "curation-items-fetched",
    items_deduplicated: "curation-items-deduplicated",
    items_published: "curation-items-published",
    items_rejected: "curation-items-rejected",
    items_failed: "curation-items-failed"
  };
  let activeJobId = null;
  let timerId = null;
  let requestInFlight = false;
  let pollAttempt = 0;
  let lastProgressSignature = "";

  function setText(id, value) {
    const node = document.getElementById(id);
    if (node) node.textContent = value == null ? "" : String(value);
  }

  function setHidden(id, hidden) {
    const node = document.getElementById(id);
    if (node) node.hidden = hidden;
  }

  function stopPolling() {
    if (timerId !== null) window.clearTimeout(timerId);
    timerId = null;
    activeJobId = null;
    requestInFlight = false;
  }

  function scheduleNextPoll() {
    if (!activeJobId || timerId !== null) return;
    const delay = POLL_DELAYS_MS[Math.min(pollAttempt, POLL_DELAYS_MS.length - 1)];
    pollAttempt += 1;
    timerId = window.setTimeout(() => {
      timerId = null;
      pollStatus();
    }, delay);
  }

  function updateStatus(job) {
    const panel = document.getElementById("curation-job-status");
    if (!panel) return;

    panel.dataset.jobStatus = job.status;
    panel.dataset.jobTerminal = job.is_terminal ? "true" : "false";
    setText("curation-status-label", job.status_label);
    setText("curation-status-message", job.message);

    const counters = job.counters || {};
    Object.entries(COUNTERS).forEach(([key, id]) => {
      if (!Object.prototype.hasOwnProperty.call(counters, key)) return;
      // The job is created before a worker begins. Keep the configured-source
      // total rendered by the page until the durable counter is populated.
      const current = document.getElementById(id);
      if (
        key === "sources_configured" &&
        Number(counters[key]) === 0 &&
        current &&
        Number(current.textContent) > 0
      ) {
        return;
      }
      setText(id, counters[key]);
    });

    const error = job.error && job.error.message ? job.error.message : "";
    setText("curation-error-message", error);
    setHidden("curation-error-message", !error);
    setText("curation-poll-message", "");
    setHidden("curation-poll-message", true);
  }

  function showTemporaryStatusError() {
    setText(
      "curation-poll-message",
      "Status is temporarily unavailable. The job has not been cancelled; checking again."
    );
    setHidden("curation-poll-message", false);
  }

  async function pollStatus() {
    if (!activeJobId || requestInFlight) return;
    requestInFlight = true;
    try {
      const response = await fetch(
        "/authoring/pulse/jobs/" + encodeURIComponent(activeJobId),
        {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" }
        }
      );
      if (!response.ok) throw new Error("status request failed");
      const job = await response.json();
      if (job.job_id !== activeJobId) throw new Error("status identity mismatch");
      const signature = JSON.stringify([
        job.status,
        job.stage,
        job.message,
        job.counters || {}
      ]);
      if (signature !== lastProgressSignature) {
        lastProgressSignature = signature;
        pollAttempt = 0;
      }
      updateStatus(job);

      if (job.is_terminal) {
        stopPolling();
        // Render the persisted final report and enable a new run. A full page
        // load also works when the panel was inserted by an HTMX swap.
        window.location.reload();
        return;
      }
    } catch (_error) {
      showTemporaryStatusError();
    } finally {
      requestInFlight = false;
    }
    scheduleNextPoll();
  }

  function initialize() {
    const panel = document.getElementById("curation-job-status");
    if (!panel) {
      stopPolling();
      return;
    }
    const jobId = panel.dataset.jobId;
    const terminal = panel.dataset.jobTerminal === "true";
    if (!jobId || terminal) {
      stopPolling();
      return;
    }
    if (activeJobId === jobId && (timerId !== null || requestInFlight)) return;

    stopPolling();
    activeJobId = jobId;
    pollAttempt = 0;
    lastProgressSignature = "";
    // Refresh immediately after a page/HTMX swap, then use bounded polling.
    pollStatus();
  }

  document.addEventListener("DOMContentLoaded", initialize);
  document.addEventListener("htmx:afterSwap", initialize);
  document.addEventListener("htmx:afterSettle", initialize);
  if (document.readyState !== "loading") initialize();
})();
