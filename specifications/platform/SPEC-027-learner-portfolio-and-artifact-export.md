# SPEC-027: Learner Portfolio & Artifact Export

## 1. Overview & Goal

SPEC-027 introduces client-side data portability to Fablit. It enables learners to export their private practice history, system evaluation feedback, pre-practice intentions, and post-practice reflections into portable formats (Markdown and JSON). This gives learners complete ownership of their practice artifacts for offline study, personal documentation, or portfolio building, operating entirely client-side without external dependencies or cloud storage integrations.

---

## 2. Functional Requirements

### 2.1 Export Scope & Configuration

* **Access Point:** Located within the SPEC-021 Practice History surface and the SPEC-024 Learner Identity / Settings surface.
* **Export Granularity:**
* *Single Session Export:* Download a single practice attempt as a structured document.
* *Full History Bulk Export:* Download all local and remote practice history tied to the active SPEC-024 learner identity.



### 2.2 Format Specifications

#### 2.2.1 Formatted Markdown (`.md`)

Designed for human readability, markdown note-taking apps (e.g., Obsidian, Notion), and personal study portfolios.

```markdown
# Practice Log: [Activity Name]
**Date:** 2026-09-26 14:30 UTC  
**Session ID:** `sess_987654321`  
**Skill Target:** [Skill Domain Name]

## 1. Pre-Practice Intention
> "Focus on optimizing boundary condition logic."

## 2. Submitted Artifact

```

[Learner submitted code/text response]

```

## 3. System Evaluation
- **Status:** PASS
- **Feedback:** [Evaluation Domain Summary]

## 4. Learner Reflection
- **Strategy Used:** Broken down into smaller sub-problems.
- **Identified Gaps:** Need to review edge cases for empty inputs.

```

#### 2.2.2 Structured JSON (`.json`)

Designed for machine readability, backup verification, and future client restoration. Must include full schema versioning tags (`specVersion: "027"`).

### 2.3 Execution Pipeline

* **Generation:** Executed entirely within the browser DOM using `Blob` objects and dynamic `URL.createObjectURL` triggers.
* **Filenames:** Standardized naming convention:
* Single: `fablit-session-[activity-id]-[timestamp].md`
* Bulk: `fablit-history-export-[learner-id]-[date].json`



---

## 3. Security & Privacy Boundaries

* **Zero Server Overhead:** Files are constructed in browser memory; no backend export endpoints or temporary storage buckets are utilized.
* **Privacy Isolation:** Exports include *only* records associated with the active SPEC-024 private key. No global system metrics or cross-learner data may be aggregated.

---

## 4. Acceptance Criteria

* [ ] Single-session export generates a correctly formatted `.md` file containing all 4 core artifact stages (Intent, Submission, Feedback, Reflection).
* [ ] Bulk-history export produces a valid, schema-tagged `.json` payload containing all practice records for the active identity.
* [ ] File generation is completely client-side and functions cleanly in offline environments.
* [ ] No unhandled exceptions occur when exporting sessions that have skipped pre-intentions or post-reflections.