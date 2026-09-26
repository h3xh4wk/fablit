# SPEC-028: Session Resilience & Local Practice Recovery

## 1. Overview & Goal

SPEC-028 implements a client-side transient storage layer to protect active practice sessions against accidental browser reloads, tab closures, or temporary network drops. By maintaining draft state in browser-local storage during active practice, learners can recover uncommitted submissions, intentions, and reflections without introducing complex server-side session management or background sync services.

---

## 2. Functional Requirements

### 2.1 Auto-Save Engine

* **Triggers:** Automatically write current input state to browser storage (`IndexedDB` primary, falling back to `localStorage`) on a 3-second debounce or explicit field blur event.
* **Tracked State:**
* Active activity ID and curated sequence context (SPEC-025).
* Draft pre-practice intention text.
* Active response input draft (code/text submission).
* Draft post-practice reflection text.
* Timestamp of last local mutation.



### 2.2 Session Recovery Interface

* **Detection:** When a learner navigates to a practice activity URL or re-opens the workspace, the system checks for an uncommitted draft matching the activity ID.
* **Intervention Banner:** If a valid draft exists and is less than 24 hours old, display a recovery banner:
* `Resume Draft` (Restores form inputs, intention state, and timestamp).
* `Discard Draft` (Purges local storage key and initializes a clean workspace).



### 2.3 Draft Lifecycle & Garbage Collection

* **Clear on Completion:** Once a submission is successfully processed and persisted to the Datastore boundary (SPEC-021), the corresponding local draft entry must be immediately deleted.
* **Expiration:** Drafts older than 24 hours are automatically purged on application launch to prevent storage bloat.

---

## 3. Technical Constraints & Data Boundary

* **Storage Key Format:** `fablit_draft_[learner_id]_[activity_id]`
* **No Server Footprint:** Draft states exist exclusively on the user's client device. No background auto-save network requests are made to the cloud backend.
* **Fallback Behavior:** If browser local storage is disabled or quota is exceeded, the application must degrade gracefully by disabling auto-recovery while allowing standard, uninterrupted practice.

---

## 4. Acceptance Criteria

* [ ] Typing into practice inputs or intention fields automatically saves state locally within 3 seconds.
* [ ] Reloading the browser mid-session preserves draft input text.
* [ ] Navigating back to an active activity prompts the learner with `Resume Draft` and `Discard Draft` options.
* [ ] Clicking `Resume Draft` accurately restores all draft fields to their exact pre-reload state.
* [ ] Successful activity submission completely removes the local draft key.
* [ ] Storage keys are isolated by SPEC-024 learner identity key.
