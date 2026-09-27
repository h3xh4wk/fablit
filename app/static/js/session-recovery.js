/* SPEC-028: local-only practice draft recovery. */
(() => {
  "use strict";
  const DB_NAME = "fablit-session-recovery";
  const STORE = "drafts";
  const PREFIX = "fablit_draft_";
  const TTL = 24 * 60 * 60 * 1000;
  const scopeKey = "fablit_recovery_scope";
  const safe = (fn) => { try { return fn(); } catch (_) { return null; } };
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
    const field = form.elements.namedItem("intention");
    if (!id || !field) return;
    form.dataset.recoveryReady = "1";
    const key = keyFor(id);
    try { sessionStorage.setItem("fablit_active_activity", id); } catch (_) {}
    const draft = await read(key);
    if (draft && Date.now() - draft.updatedAt < TTL) field.value = draft.intention || "";
    bindField(form, field, key, id, "intention");
  };
  const initPractice = async (form) => {
    if (form.dataset.recoveryReady) return;
    const id = activityId(form, "submit");
    const field = form.elements.namedItem("response");
    if (!id || !field) return;
    form.dataset.recoveryReady = "1";
    sessionStorage.setItem("fablit_active_activity", id);
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
      const pending = read(key).then((previous) => write(nowDraft(key, id, {response: field.value}, previous)));
      form.dataset.recoveryPending = "1";
      void pending;
    });
    document.body.addEventListener("htmx:afterRequest", async (event) => {
      if (event.detail && event.detail.elt === form && event.detail.successful) {
        const target = document.querySelector("#submission-area");
        if (target && !target.querySelector('textarea[name="response"]')) await remove(key);
      }
    });
  };
  const initReflection = async (form) => {
    if (form.dataset.recoveryReady) return;
    const id = sessionStorage.getItem("fablit_active_activity");
    const field = form.elements.namedItem("content");
    if (!id || !field) return;
    form.dataset.recoveryReady = "1";
    const key = keyFor(id);
    const draft = await read(key);
    if (draft && Date.now() - draft.updatedAt < TTL && draft.reflection) field.value = draft.reflection;
    bindField(form, field, key, id, "reflection");

  };
  const cleanupCompleted = async () => {
    if (location.pathname !== "/feedback" && location.pathname !== "/complete") return;
    let id;
    try { id = sessionStorage.getItem("fablit_active_activity"); } catch (_) { return; }
    if (id) await remove(keyFor(id));
  };
  const init = () => {
    document.querySelectorAll('form[action*="/intention"]').forEach(initIntention);
    document.querySelectorAll('form[action*="/submit"]').forEach(initPractice);
    document.querySelectorAll('form[action="/reflect"]').forEach(initReflection);
  };
  purge().finally(() => { void cleanupCompleted(); init(); });
  document.body.addEventListener("htmx:afterSwap", init);
})();
