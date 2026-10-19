# SPEC-036: Optional Stimulus Images for Practice Candidates (Pexafy)

## 1. Overview & Goal

SPEC-032 generates structured practice candidates, and SPEC-035 publishes an
approved candidate into the learner library. Neither step currently supplies a
visual stimulus: the candidate has no image, and the published activity has no
stimulus or dashboard thumbnail.

SPEC-036 adds an optional image to a practice candidate at creation time. The
authoring model writes one line describing the scene to source; Pexafy's
semantic image search returns relevant, free-to-use photographs; the author
selects one or leaves the candidate without an image. A selected image follows
the approved candidate into publication as the learner stimulus and as the
practice thumbnail.

## 2. Product Principle

**Images are optional, author-chosen, and attributable.**

An image is content, not decoration. It must be reviewable by the author before
approval, must never block practice creation when image search is unavailable,
and must carry enough provenance (source, photographer, source page,
attribution) to be shown honestly to learners.

## 3. Objectives

- Let a candidate carry one optional stimulus image.
- Generate a one-line scene description with the existing authoring LLM.
- Source images from Pexafy without adding an SDK or exposing the API key.
- Keep image selection a human decision; never auto-select without review.
- Preserve candidates and publication when Pexafy is unavailable or over quota.
- Render the selected image on the learner practice page and dashboard card.
- Preserve the existing learner journey, content contract, and history.

## 4. Scope

### In scope

- An application-level image-search port and value type.
- A Pexafy adapter using the standard library with an injectable transport.
- Configuration for the image-search API key and graceful behaviour when it is
  absent.
- A one-line `stimulus_query` in the authoring generation result.
- Storing the query, a bounded set of search options, and the selected image on
  the candidate.
- An authoring action to select or clear the image.
- Publication of the selected image as the learner stimulus and thumbnail.
- Persistence in the in-memory and Datastore published stores.
- Authoring UI for reviewing and choosing an image.
- Tests, documentation, and changelog updates.

### Out of scope

- Image generation, editing, cropping, or filters.
- Downloading or re-hosting image bytes.
- Multi-image practices or galleries.
- Automatic image selection.
- Vision-model-generated alt text.
- Paid image-search plans or custom quotas.
- Using images to evaluate or grade learner responses.
- Reworking the existing stimulus provider for curated practices.

## 5. Workflow

```text
Authoring Brief (optional stimulus requirements)
        ↓
Authoring LLM returns candidate_data + stimulus_query
        ↓
Pexafy search (bounded, cached on the candidate)
        ↓
Author sees options → selects one or skips
        ↓
Candidate validation / human approval
        ↓
Explicit publication
        ↓
Learner practice image + dashboard thumbnail
```

Selecting an image is an edit of learner-facing content: it must follow the
existing edit/revalidation lifecycle and reset a prior approval. Skipping the
image leaves the candidate exactly as it is today.

## 6. Data Model

### Candidate data

`candidate_data` may include:

- `stimulus_query`: one-line plain-text scene description used for search.
- `stimulus_options`: a bounded list of image results returned by Pexafy.
- `stimulus`: the selected image, or absent/`null` when the candidate has none.

The search options are stored on the candidate so rendering the candidate page
does not spend a Pexafy request. The selected image must reference an entry from
`stimulus_options`.

### Image value

The application value carries at least:

- stable photo identity;
- display URL and thumbnail URL;
- alt text or image description;
- source library and source page URL;
- photographer name or handle;
- attribution text;
- width, height, and orientation.

Provider-specific response fields must not leak into templates or learner
routes.

### Published activity

The published learner activity carries the selected image as an authored
stimulus (image URL, alt text, attribution, source URL, and provider identity)
and exposes the same image/alt pair as its catalogue preview. A publication
without an image keeps the current representation.

## 7. Provider Boundary & Configuration

- The application depends on an image-search port, never on Pexafy directly.
- The Pexafy adapter lives in `fablit/platform/` and uses `urllib` with a
  timeout and an injectable transport for tests.
- The API key is read from server configuration only. A missing key disables
  image sourcing without affecting candidate generation.
- Pexafy is called once per generation, with a bounded result count. Search
  results are cached on the candidate.
- Authentication failures, quota errors, timeouts, and malformed responses
  become an explicit application error or an empty option list. They must not
  fail candidate creation, expose the key, or log provider payloads.
- The key must never appear in responses, logs, templates, or committed files.

## 8. Publication & Learner Experience

- Publication copies the selected image into the existing learner activity.
- The practice page shows the image with non-empty alt text and attribution.
  Existing learner copy and the practice contract are unchanged.
- The dashboard card uses the image and alt text as its preview thumbnail.
- A publication without a selected image renders exactly as it does today.
- Republishing a later approved revision replaces the image with that
  revision's selection, under the same learner activity identity.
- The image is content provenance only; it is never used to evaluate, score,
  rank, or describe learner ability.

## 9. Validation & Failure Handling

1. No image is valid.
2. A selected image must have a display URL, alt text or description, a source
   page, and attribution metadata.
3. A selection that is not in the stored options is rejected.
4. A Pexafy failure must not block generation, approval, or publication of a
   candidate without an image.
5. Image search must not be retried in a way that can exceed the configured
   quota.
6. A candidate that already has a selected image keeps it across edits that do
   not change the image.

## 10. Security & Licensing

- Continue protecting all authoring routes through SEC-001.
- Use only Pexafy's returned CDN URLs; do not proxy image bytes through Fablit.
- Store and display the source, photographer, source page, and attribution that
  Pexafy returns, even where the source library does not require attribution.
- Do not expose internal search errors, quota details, or the API key to
  learners.

## 11. Architecture Boundaries

- Keep the application layer free of Pexafy imports and HTTP details.
- Keep the domain layer free of image-search, provider, and persistence types.
- Reuse the existing candidate store, publication protocol, learner activity,
  and Datastore-unindexed payload conventions.
- Do not introduce a parallel practice model, a new database, or an image
  hosting service.
- Preserve backward compatibility for published records and candidates created
  before this specification.

## 12. Acceptance Criteria

1. With an image-search key configured, generating a candidate with a stimulus
   request yields a one-line scene description and a bounded set of relevant
   Pexafy images.
2. The author can select exactly one image or leave the candidate without one,
   and the choice survives later edits and approval.
3. Publishing a candidate with an image renders it on the learner practice page
   with alt text and attribution, and uses it as the dashboard thumbnail.
4. Publishing a candidate without an image produces the same learner experience
   as today.
5. Pexafy failures (missing key, timeout, 401, 429, malformed response) never
   block candidate generation, never leak the key, and are explained to the
   author where an action was attempted.
6. Published records round-trip the image metadata through the Datastore store,
   and records created before SPEC-036 still load.
7. The existing learner journey, practice history, evaluation, feedback, and
   reflection behaviour are unchanged.
8. All quality gates pass.

## 13. Testing Strategy

- Unit-test the Pexafy adapter with a fake transport: success, missing fields,
  401, 429, timeout, and malformed JSON.
- Unit-test the candidate stimulus selection and clearing rules.
- Web-test generation with and without image search configured.
- Web-test publication with and without an image, including the practice page
  and dashboard thumbnail.
- Persistence-test the Datastore round trip and backward compatibility.
- No live Pexafy calls in CI.

## 14. References

- SPEC-015 — visual stimulus model and provider boundary.
- SPEC-029 — practice content contract.
- SPEC-032 — AI-assisted practice authoring.
- SPEC-035 — publish approved practice candidates.
- GitHub issue #140.
