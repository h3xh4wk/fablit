/* SPEC-028: client-only recovery for an active practice response. */
(() => {
  "use strict";
  const DB = "fablit-session-recovery";
  const STORE = "drafts";
  const TTL = 24 * 60 * 60 * 1000;
  const PREFIX = "fablit_draft_";
  const safe = (fn) => { try { return fn(); } catch (_) { return null; } };
  const browserScope = () => {
    try {
      let id = localStorage.getItem("fablit_recovery_scope");
      if (!id) {
        id = (crypto.randomUUID ? crypto.randomUUID() : Date.now() + "-" + Math.random().toString(36).slice(2));
        localStorage.setItem("fablit_recovery_scope", id);
      }
      return id;
    } catch (_) { return null; }
  };
  const scope = browserScope();
  if (!scope) return;
  const keyFor = (activity) => PREFIX + scope + "_" + activity;
  let dbPromise;
  const openDb = () => {
    if (!("indexedDB" in window)) return Promise.reject(new Error("IndexedDB unavailable"));
    if (!dbPromise) dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB, 1);
      request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: "key" });
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    return dbPromise;
  };
  const idb = async (mode, key, value) => {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode);
      const store = tx.objectStore(STORE);
      const req = mode === "readonly" ? store.get(key) : value === undefined ? store.delete(key) : store.put(value);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  };
  const read = async (key) => {
    try { const value = await idb("readonly", key); if (value) return value; } catch (_) {}
    return safe(() => JSON.parse(localStorage.getItem(key))) || null;
  };
  const write = async (draft) => {
    try { await idb("readwrite", draft.key, draft); return; } catch (_) {}
    try { localStorage.setItem(draft.key, JSON.stringify(draft)); } catch (_) {}
  };
  const remove = async (key) => {
    try { await idb("readwrite", key); } catch (_) {}
    safe(() => localStorage.removeItem(key));
  };
  const purge = async () => {
    const cutoff = Date.now() - TTL;
    try {
      const db = await openDb();
      await new Promise((resolve) => {
        const tx = db.transaction(STORE, "readwrite");
        const req = tx.objectStore(STORE).openCursor();
        req.onsuccess = () => {
          const cursor = req.result;
          if (!cursor) return;
          if (!cursor.value || cursor.value.updatedAt < cutoff) cursor.delete();
          cursor.continue();
        };
        tx.oncomplete = resolve; tx.onerror = resolve;
      });
    } catch (_) {}
    safe(() => {
      for (let i = localStorage.length - 1; i >= 0; i--) {
        const key = localStorage.key(i);
        if (key && key.startsWith(PREFIX)) {
          try { const draft = JSON.parse(localStorage.getItem(key)); if (!draft || draft.updatedAt < cutoff) localStorage.removeItem(key); } catch (_) { localStorage.removeItem(key); }
        }
      }
    });
  };
  const activityFrom = (form) => {
    const match = form.action.match(/\/activities\/([0-9a-f-]+)\/submit/i);
    return match && match[1];
  };
  const initForm = async (form) => {
    if (form.dataset.recoveryReady) return;
    const activity = activityFrom(form);
    const field = form.elements.namedItem("response");
    if (!activity || !field) return;
    form.dataset.recoveryReady = "1";
    const key = keyFor(activity);
    const banner = document.createElement("div");
    banner.className = "practice__recovery";
    banner.setAttribute("role", "status");
    banner.hidden = true;
    form.parentNode.insertBefore(banner, form);
    const existing = await read(key);
    if (existing && Date.now() - existing.updatedAt < TTL && (existing.response || "")) {
      banner.hidden = false;
      const message = document.createElement("p");
      message.textContent = "An unfinished response was saved on this device.";
      const resume = document.createElement("button");
      resume.type = "button"; resume.className = "button"; resume.textContent = "Resume Draft";
      resume.addEventListener("click", () => {
        field.value = existing.response || "";
        banner.hidden = true;
        field.dispatchEvent(new Event("input", { bubbles: true }));
      });
      const discard = document.createElement("button");
      discard.type = "button"; discard.className = "button button--secondary"; discard.textContent = "Discard Draft";
      discard.addEventListener("click", async () => { await remove(key); banner.remove(); });
      banner.append(message, resume, discard);
    }
    let timer;
    const save = () => {
      clearTimeout(timer);
      timer = setTimeout(() => write({key, activityId: activity, response: field.value, updatedAt: Date.now()}), 3000);
    };
    field.addEventListener("input", save);
    field.addEventListener("blur", () => { clearTimeout(timer); write({key, activityId: activity, response: field.value, updatedAt: Date.now()}); });
    form.addEventListener("submit", () => { clearTimeout(timer); write({key, activityId: activity, response: field.value, updatedAt: Date.now()}); });
    document.body.addEventListener("htmx:afterRequest", async (event) => {
      if (event.detail && event.detail.elt === form && event.detail.successful) {
        const target = document.querySelector("#submission-area");
        if (target && !target.querySelector('textarea[name="response"]')) await remove(key);
      }
    });
  };
  purge().finally(() => document.querySelectorAll('form[action*="/submit"]').forEach(initForm));
  document.body.addEventListener("htmx:afterSwap", (event) => {
    event.target.querySelectorAll?.('form[action*="/submit"]').forEach(initForm);
  });
})();
