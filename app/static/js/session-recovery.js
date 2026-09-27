/* SPEC-028: local-only practice draft recovery. */
(() => {
  "use strict";
  const DB_NAME = "fablit-session-recovery";
  const STORE = "drafts";
  const PREFIX = "fablit_draft_";
  const TTL = 24 * 60 * 60 * 1000;
  const scopeKey = "fablit_recovery_scope";
  const safe = (fn) => { try { return fn(); } catch (_) { return null; } };
  const sessionGet = (name) => safe(() => sessionStorage.getItem(name));
  const sessionSet = (name, value) => { safe(() => sessionStorage.setItem(name, value)); };
  const getScope = () => safe(() => {
    let value = localStorage.getItem(scopeKey);
    if (!value) {
      value = crypto.randomUUID ? crypto.randomUUID() : Date.now() + "-" + Math.random().toString(36).slice(2);
      localStorage.setItem(scopeKey, value);
    }
    return value;
  });
  const scope = getScope();
  if (!scope) return;
  const keyFor = (id) => PREFIX + scope + "_" + id;
  let dbPromise;
  const openDb = () => {
    if (!window.indexedDB) return Promise.reject(new Error("IndexedDB unavailable"));
    if (!dbPromise) dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = () => request.result.createObjectStore(STORE, {keyPath: "key"});
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
      const request = mode === "readonly" ? store.get(key) : value === undefined ? store.delete(key) : store.put(value);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
      tx.onabort = () => reject(tx.error || new Error("Storage transaction aborted"));
    });
  };
  const read = async (key) => {
    try { const value = await idb("readonly", key); if (value) return value; } catch (_) {}
    return safe(() => JSON.parse(localStorage.getItem(key))) || null;
  };
  const write = async (draft) => {
    try { await idb("readwrite", draft.key, draft); return true; } catch (_) {}
    return safe(() => { localStorage.setItem(draft.key, JSON.stringify(draft)); return true; }) === true;
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
        const request = tx.objectStore(STORE).openCursor();
        request.onsuccess = () => {
          const cursor = request.result;
          if (!cursor) return;
          if (!cursor.value || cursor.value.updatedAt < cutoff) cursor.delete();
          cursor.continue();
        };
        tx.oncomplete = resolve;
        tx.onerror = resolve;
      });
    } catch (_) {}
    safe(() => {
      for (let i = localStorage.length - 1; i >= 0; i--) {
        const key = localStorage.key(i);
        if (key && key.startsWith(PREFIX)) {
          try {
            const value = JSON.parse(localStorage.getItem(key));
            if (!value || value.updatedAt < cutoff) localStorage.removeItem(key);
          } catch (_) { localStorage.removeItem(key); }
        }
      }
    });
  };
  const activityId = (form, suffix) => {
    const match = form.action.match(new RegExp("/activities/([0-9a-f-]+)/" + suffix, "i"));
    return match && match[1];
  };
  const nowDraft = (key, id, fields, prior) => Object.assign({}, prior || {}, fields, {
    key, activityId: id, updatedAt: Date.now()
  });
  // Submit-time writes are async; the post-submission cleanup must land
  // after them or the write would resurrect the draft it just saved.
  // Keyed by activity ID: after a successful swap the submitting form is
  // already detached, so it cannot carry the association itself.
  const pendingWrites = new Map();
  const bindField = (form, field, key, id, name, initial) => {
    let timer;
    const save = () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const previous = await read(key);
        await write(nowDraft(key, id, {[name]: field.value}, previous));
      }, 3000);
    };
    field.addEventListener("input", save);
    field.addEventListener("blur", async () => {
      clearTimeout(timer);
      const previous = await read(key);
      await write(nowDraft(key, id, {[name]: field.value}, previous));
    });
    form.addEventListener("submit", () => clearTimeout(timer));
    if (initial !== undefined && initial !== null) field.value = initial;
  };
  const initIntention = async (form) => {
    if (form.dataset.recoveryReady) return;
    const id = activityId(form, "intention");
    // querySelector, not elements.namedItem: the skip button shares the
    // "intention" name, which would return a RadioNodeList, not the field.
    const field = form.querySelector('textarea[name="intention"]');
    if (!id || !field) return;
    form.dataset.recoveryReady = "1";
    const key = keyFor(id);
    sessionSet("fablit_active_activity", id);
    const draft = await read(key);
    if (draft && Date.now() - draft.updatedAt < TTL) field.value = draft.intention || "";
    bindField(form, field, key, id, "intention");
  };
  const initPractice = async (form) => {
    if (form.dataset.recoveryReady) return;
    const id = activityId(form, "submit");
    const field = form.querySelector('textarea[name="response"]');
    if (!id || !field) return;
    form.dataset.recoveryReady = "1";
    sessionSet("fablit_active_activity", id);
    const key = keyFor(id);
    const draft = await read(key);
    if (draft && Date.now() - draft.updatedAt < TTL && (draft.response || draft.intention || draft.reflection)) {
      const banner = document.createElement("div");
      banner.className = "practice__recovery";
      banner.setAttribute("role", "status");
      const message = document.createElement("p");
      message.textContent = "An unfinished practice was saved on this device.";
      const resume = document.createElement("button");
      resume.type = "button"; resume.className = "button"; resume.textContent = "Resume Draft";
      const discard = document.createElement("button");
      discard.type = "button"; discard.className = "button button--secondary"; discard.textContent = "Discard Draft";
      resume.addEventListener("click", () => {
        field.value = draft.response || "";
        banner.remove();
      });
      discard.addEventListener("click", async () => { await remove(key); banner.remove(); });
      banner.append(message, resume, discard);
      form.parentNode.insertBefore(banner, form);
    }
    bindField(form, field, key, id, "response");
    form.addEventListener("submit", () => {
      pendingWrites.set(
        id,
        read(key).then((previous) => write(nowDraft(key, id, {response: field.value}, previous)))
      );
    });
  };
  // htmx fires afterRequest on the requesting element, but a successful
  // submission detaches the form, so the event is re-fired on the nearest
  // still-connected ancestor instead. Identify the request by its path.
  const clearDraftAfterSubmission = async (event) => {
    const detail = event.detail;
    if (!detail || !detail.successful) return;
    const path = (detail.pathInfo && detail.pathInfo.requestPath)
      || (detail.requestConfig && detail.requestConfig.path) || "";
    const match = path.match(/\/activities\/([0-9a-f-]+)\/submit/i);
    if (!match) return;
    const id = match[1];
    const pending = pendingWrites.get(id);
    if (pending) await pending;
    pendingWrites.delete(id);
    // Only clear when the swap really replaced the response form; a failed
    // validation swap re-renders the textarea and the draft stays useful.
    const target = document.querySelector("#submission-area");
    if (target && !target.querySelector('textarea[name="response"]')) {
      await remove(keyFor(id));
    }
  };
  const initReflection = async (form) => {
    if (form.dataset.recoveryReady) return;
    const id = sessionGet("fablit_active_activity");
    // querySelector guarantees the textarea itself — the feedback page's
    // inline skip form also has a (hidden) "content" input that must not
    // be bound or restored.
    const field = form.querySelector('textarea[name="content"]');
    if (!id || !field) return;
    form.dataset.recoveryReady = "1";
    const key = keyFor(id);
    const draft = await read(key);
    if (draft && Date.now() - draft.updatedAt < TTL && draft.reflection) field.value = draft.reflection;
    bindField(form, field, key, id, "reflection");
  };
  const cleanupCompleted = async () => {
    if (location.pathname !== "/feedback" && location.pathname !== "/complete") return;
    const id = sessionGet("fablit_active_activity");
    if (id) await remove(keyFor(id));
  };
  const init = () => {
    document.querySelectorAll('form[action*="/intention"]').forEach(initIntention);
    document.querySelectorAll('form[action*="/submit"]').forEach(initPractice);
    document.querySelectorAll('form[action="/reflect"]').forEach(initReflection);
  };
  document.body.addEventListener("htmx:afterRequest", clearDraftAfterSubmission);
  document.body.addEventListener("htmx:afterSwap", init);
  purge().finally(() => { void cleanupCompleted(); init(); });
})();
