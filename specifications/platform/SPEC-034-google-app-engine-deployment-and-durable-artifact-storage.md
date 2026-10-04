# SPEC-034: Google App Engine Deployment & Durable Artifact Storage

## 1. Overview & Goal

SPEC-034 establishes Google App Engine as a supported deployment environment for the current Fablit application and provides durable production storage for private sketchbook artifacts.

The current `ArtifactStorage` boundary introduced by SPEC-033 and hardened by FIX-2/FIX-3 is preserved. The local `FileArtifactStorage` implementation remains useful for local development and tests, while the supported App Engine deployment uses a durable Google Cloud Storage backend for artifact bytes.

The intended production relationship is:

```
Fablit Application
      │
      ├── Practice History
      │       ↓
      │   Google Cloud Datastore
      │
      └── Artifact Reference
              ↓
        ArtifactStorage
              ↓
      Google Cloud Storage
              ↓
       Private image bytes
```

The goal is to make the existing learner experience deployable on App Engine without changing its product semantics.

---

## 2. Product Principle

Infrastructure should support the learner experience without becoming part of it.

A learner should not need to know whether Fablit is running locally, on a single App Engine instance, or across multiple App Engine instances.

In particular:

- completed practice history must remain durable;
- private sketchbook artifacts must remain retrievable after normal instance lifecycle events;
- learner ownership and privacy must remain unchanged;
- local development should remain simple;
- production storage should use services appropriate to the deployment environment.

SPEC-034 is an infrastructure boundary, not a new learner-facing feature.

---

## 3. Scope

### In scope

- Support for Google App Engine as the deployed Fablit environment.
- A committed App Engine deployment configuration appropriate to the current Python/FastAPI application.
- Explicit production configuration for the existing Datastore practice-history repository.
- A durable Google Cloud Storage adapter implementing the existing `ArtifactStorage` boundary.
- A private GCS bucket/object layout for sketchbook artifacts.
- Configuration for selecting production artifact storage without changing application/domain semantics.
- Appropriate Google Cloud authentication and service-account/IAM configuration guidance.
- Preservation of learner-scoped artifact retrieval through the existing application route.
- Deployment documentation reflecting the actual supported deployment path.
- Automated tests for the new storage adapter and configuration.
- A deployment/smoke verification covering practice history and sketchbook artifact upload/retrieval.

### Out of scope

- Replacing Google Cloud Datastore.
- Redesigning Practice History.
- Redesigning `ArtifactStorage`.
- Changing Sketchbook Reflection behaviour.
- New learner-facing features.
- Public media URLs.
- Public or searchable GCS buckets.
- A general-purpose media-management platform.
- Authentication or account-management changes.
- AI vision or image evaluation.
- Portfolio or social sharing.
- CDN/media optimisation.
- Background processing or asynchronous media pipelines.
- Multi-region storage architecture unless required by the existing supported deployment.
- Generic cloud infrastructure unrelated to Fablit's current deployment.

---

## 4. Current Storage Boundary

SPEC-034 builds on the existing artifact architecture:

```
Practice History
      ↓
ArtifactRef / metadata
      ↓
ArtifactStorage
      ↓
artifact bytes
```

Practice History must continue to store only the artifact reference/metadata required for association and retrieval.

Raw image bytes must not be reintroduced into Datastore.

The existing `ArtifactStorage` interface remains the application boundary.

The intended adapters are:

```
ArtifactStorage
   ├── FileArtifactStorage
   │       └── local development / tests
   │
   └── GCSArtifactStorage
           └── supported App Engine deployment
```

The exact class/module naming may follow existing repository conventions.

---

## 5. Google App Engine Deployment

The repository must contain an explicit, reproducible App Engine deployment configuration for the supported Python runtime.

The deployment configuration must:

- identify the supported Python runtime;
- define the application entry/startup behaviour required by the chosen App Engine environment;
- expose the FastAPI application through the existing application entry point;
- use environment configuration rather than hard-coded deployment-specific values;
- avoid committed credentials or service-account secrets;
- preserve the existing FastAPI + server-rendered architecture;
- support the existing static/template/application layout without requiring a frontend framework change.

The configuration must be documented sufficiently that a clean deployment can be reproduced from the repository using the project's documented deployment command.

The repository's deployment documentation must no longer describe an obsolete provider as the current production deployment if App Engine is established as the supported environment.

---

## 6. Production Artifact Storage

The production artifact backend must use Google Cloud Storage rather than the App Engine instance filesystem.

The GCS implementation must:

- implement the existing `ArtifactStorage` boundary;
- store artifact bytes under an opaque artifact identifier;
- preserve the existing learner/artifact association held by Practice History;
- support save/get/delete operations required by the current application;
- preserve validated content type and size metadata;
- avoid public object access;
- avoid exposing direct public bucket/object URLs;
- allow the existing learner-scoped application route to remain the only learner-facing retrieval path.

The application should treat the GCS object identifier as an internal storage detail.

Conceptually:

```
ArtifactRef
  └── opaque artifact id
          ↓
Private GCS bucket
  └── opaque object key
          ↓
image bytes
```

The implementation must not use the learner identifier as a publicly visible object key or URL component.

---

## 7. Bucket and Access Boundary

The artifact bucket must be private.

The implementation must not depend on:

- anonymous bucket access;
- public object URLs;
- client-side direct bucket access;
- exposing service-account credentials to the browser.

Artifact retrieval remains:

```
Browser
   ↓
Learner-scoped Fablit route
   ↓
Practice History ownership check
   ↓
ArtifactStorage
   ↓
Private GCS object
```

The existing ownership semantics from SPEC-024 and SPEC-033 remain authoritative.

Two anonymous learners must not be able to retrieve one another's artifacts.

The production service identity must have only the permissions required for the scoped artifact-storage operations and other existing Fablit services.

The exact IAM configuration must be documented without committing credentials or secrets.

---

## 8. Configuration

Production configuration must make the storage choices explicit.

At minimum, the deployed environment must be able to select:

- Datastore-backed Practice History;
- GCS-backed Artifact Storage;
- the target GCS bucket;
- any required deployment/project configuration through environment or platform configuration.

Configuration must remain outside domain/business logic.

Local development and tests must continue to work without production GCP credentials unless a test explicitly exercises a GCP integration boundary.

If `FABLIT_ARTIFACT_STORAGE_DIR` remains supported, it should continue to serve the file-backed local/test implementation and must not be treated as the durable production storage mechanism.

Configuration naming should remain consistent with existing Fablit conventions.

---

## 9. Artifact Lifecycle and Failure Behaviour

The existing retry-safe lifecycle from FIX-3 remains authoritative.

The GCS adapter must integrate without weakening the existing lifecycle:

```
Upload
  ↓
Validate
  ↓
Stage artifact
  ↓
Persist completion safely
  ↓
Commit artifact
  ↓
Completed Practice History
```

Where the implementation requires a different ordering because of the storage provider, it must preserve the same semantic guarantees:

- a failed completion must not falsely appear complete;
- a successfully completed practice must retain a usable artifact reference;
- retries must not unintentionally create duplicate artifacts or lose the learner's uploaded artifact;
- failed or abandoned temporary artifacts must have defined cleanup behaviour;
- missing artifact bytes must not make an existing review unusable.

The implementation should prefer provider operations that make these guarantees explicit rather than relying on process-local assumptions.

---

## 10. Existing Data

The implementation must consider records created before GCS-backed artifact storage.

Existing Practice History records may contain artifact references created by the current file-backed implementation.

The implementation must define one of the following explicitly:

- a migration strategy for existing artifacts;
- a compatibility strategy for existing file-backed artifacts;
- or a documented decision that legacy local artifacts are not migrated and existing reviews degrade gracefully when their bytes are unavailable.

No silent data corruption or invalid artifact reference should be introduced.

A migration must not be added merely for theoretical completeness if the current deployment has no durable production file-backed artifacts to migrate.

---

## 11. Local Development and Testing

The storage boundary must preserve fast, deterministic local development.

At minimum:

- `FileArtifactStorage` remains available for local development/tests;
- unit tests for application behaviour do not require GCS credentials;
- GCS adapter behaviour is independently testable;
- storage mapping and error behaviour are covered;
- tests cover learner-facing missing-artifact behaviour;
- tests cover configuration selection between file-backed and GCS-backed storage;
- production bucket names or credentials are not required by ordinary CI tests.

Where the repository's testing infrastructure supports a GCP emulator or isolated integration environment, it may be used for storage integration tests.

Do not make the complete test suite depend on a manually running external GCP service unless the repository already establishes that convention.

---

## 12. Deployment Verification

After deployment, verification must cover the existing learner journey rather than merely checking that the process starts.

At minimum verify:

1. Fablit starts successfully on App Engine.
2. Practice Explore/selection works.
3. A normal practice can be completed.
4. Practice History persists through a new application instance/redeployment boundary where practical.
5. Sketchbook Reflection accepts a valid supported image.
6. The artifact is stored outside Datastore.
7. The completed practice remains reviewable.
8. The artifact can be retrieved through the learner-scoped application route.
9. A missing artifact does not break the review page.
10. A different anonymous learner cannot retrieve the artifact.
11. Invalid/oversized uploads remain rejected.
12. Existing non-sketchbook practices remain unaffected.

Deployment verification should be documented as a repeatable smoke test rather than relying only on CI.

---

## 13. Architecture Boundaries

Implementation must preserve:

- FastAPI;
- server-rendered HTML + HTMX;
- Python 3.12 project conventions;
- existing Assessment Activity model;
- existing Submission → Evaluation → Feedback → Reflection → Completion journey;
- existing Practice History model;
- existing anonymous learner identity;
- existing `ArtifactStorage` abstraction;
- existing Short Drill / Full Practice behaviour;
- existing feedback contract.

Do not:

- move Practice History to another database;
- put artifact bytes back into Datastore;
- expose GCS objects publicly;
- introduce a new frontend framework;
- introduce authentication;
- introduce a generic media platform;
- introduce AI image evaluation;
- introduce new learner-facing infrastructure controls;
- redesign unrelated application architecture.

---

## 14. Acceptance Criteria

### AC-034-01 — App Engine Configuration

**Given** the Fablit repository is checked out
**When** the documented deployment process is followed
**Then** the application has an explicit App Engine deployment configuration capable of deploying the current FastAPI application.

### AC-034-02 — Production Datastore

**Given** Fablit is deployed to the supported App Engine environment
**When** a learner completes practice
**Then** Practice History continues to use Google Cloud Datastore as the durable persistence mechanism.

### AC-034-03 — Production Artifact Backend

**Given** Fablit is deployed to the supported App Engine environment
**When** a learner uploads a Sketchbook Reflection artifact
**Then** the artifact bytes are stored in the configured private Google Cloud Storage bucket rather than the App Engine instance filesystem.

### AC-034-04 — Artifact Boundary

**Given** a completed Sketchbook Reflection exists
**When** Practice History is persisted
**Then** the history record contains artifact reference/metadata but not the raw image bytes.

### AC-034-05 — Private Retrieval

**Given** a learner owns a completed Sketchbook Reflection
**When** the learner opens its artifact through Fablit
**Then** the application verifies ownership and retrieves the bytes through the private storage boundary.

### AC-034-06 — Cross-Learner Isolation

**Given** learner A owns an artifact
**When** learner B attempts to retrieve that artifact by changing identifiers or URLs
**Then** the artifact is not disclosed.

### AC-034-07 — Durable Artifact

**Given** a learner has completed Sketchbook Reflection successfully
**When** the App Engine instance handling the original request is no longer available
**Then** the artifact remains retrievable from the durable production storage backend.

### AC-034-08 — Retry Safety

**Given** artifact persistence or completion processing is interrupted
**When** the learner retries the operation
**Then** the application preserves the existing FIX-3 retry guarantees and does not falsely report completion or unintentionally duplicate artifacts.

### AC-034-09 — Local/Test Storage

**Given** Fablit is running in local development or ordinary unit tests
**When** artifact storage is exercised
**Then** the existing file-backed storage implementation remains usable without production GCP credentials.

### AC-034-10 — Missing Artifact

**Given** a Practice History record references an unavailable artifact
**When** the learner opens the review
**Then** the written reflection and other practice-history evidence remain usable.

### AC-034-11 — Deployment Documentation

**Given** App Engine is the supported deployment environment
**When** a contributor reads the deployment documentation
**Then** the documented provider, configuration, deployment command, required environment configuration, and artifact-storage architecture match the actual implementation.

### AC-034-12 — No Public Media Access

**Given** an artifact is stored in production
**When** a user attempts to access the GCS object directly without application authorization
**Then** the object is not publicly accessible.

### AC-034-13 — Existing Journey Preservation

**Given** SPEC-034 is enabled
**When** a learner uses ordinary Fablit practices
**Then** the existing learner journey and practice semantics remain unchanged.

### AC-034-14 — Regression Safety

**Given** the implementation is complete
**When** the full CI/check suite runs
**Then** formatting, linting, type checking, tests, and coverage requirements continue to pass.

---

## 15. Testing Requirements

### Unit / Application Tests

Cover at minimum:

- GCS artifact-storage adapter contract;
- save/get/delete behaviour;
- content metadata preservation;
- storage error mapping;
- missing object behaviour;
- configuration selection;
- local file-storage compatibility;
- existing retry-safe artifact lifecycle.

### Persistence / Integration Tests

Where supported by the repository's infrastructure, cover:

- GCS object creation and retrieval;
- private object access;
- object deletion;
- artifact reference consistency;
- Datastore record containing metadata/reference but no raw bytes;
- completed history reconstruction.

### Web / UI Tests

Verify:

- normal practice completion remains unchanged;
- Sketchbook Reflection upload remains optional;
- valid artifacts can be reviewed;
- missing artifacts degrade gracefully;
- learner ownership remains enforced.

### Deployment Smoke Test

Verify the production journey against the deployed App Engine service, including:

- practice completion;
- durable Practice History;
- sketch upload;
- artifact retrieval after instance lifecycle change where practical;
- cross-learner isolation.

---

## 16. Documentation Requirements

Update only documentation directly affected by the deployment change.

At minimum, document:

- supported App Engine runtime/deployment configuration;
- deployment command/process;
- required production configuration;
- Datastore production setting;
- GCS artifact bucket configuration;
- required IAM/service identity permissions at an appropriate level;
- local/test storage behaviour;
- artifact storage architecture;
- any decision regarding legacy file-backed artifacts;
- deployment smoke-test procedure.

The documentation must not contain:

- credentials;
- private keys;
- service-account JSON;
- secrets;
- learner data.

---

## 17. Relationship to Existing Specifications

SPEC-034 builds on:

- SPEC-021 — Persistent Practice History & Learner Review.
- SPEC-024 — Learner Identity & Private Practice History.
- SPEC-029 — Practice Content Model & Learning Contract.
- SPEC-030 — Practice Feedback Quality.
- SPEC-031 — Sketchbook-to-Practice Reflection.
- SPEC-033 — Complete Sketchbook Reflection with Private Artifact Support.
- FIX-2 — Move Sketchbook Artifact Bytes Outside Practice History Storage.
- FIX-3 — Make Sketchbook Artifact Persistence Retry-Safe and Validate MIME Consistency.

SPEC-034 does not replace these specifications.

It provides the deployment/storage environment required for their production guarantees to remain valid when Fablit runs on App Engine.

---

## 18. Non-Goals

SPEC-034 does not:

- change learner-facing product functionality;
- introduce authentication;
- introduce account recovery;
- introduce a public portfolio;
- introduce social sharing;
- evaluate uploaded sketches;
- introduce AI vision;
- introduce scores or mastery;
- introduce recommendation logic;
- replace Datastore;
- create a generic cloud abstraction layer;
- require a new frontend framework;
- optimise Fablit for large-scale traffic beyond the current deployment needs.

---

## 19. Definition of Done

SPEC-034 is complete when:

- [ ] App Engine deployment configuration is committed and documented.
- [ ] The current FastAPI application deploys successfully to the supported App Engine environment.
- [ ] Practice History continues to use Google Cloud Datastore in production.
- [ ] Production sketchbook artifacts use a durable private GCS-backed storage adapter.
- [ ] `FileArtifactStorage` remains available for local development/tests.
- [ ] Raw artifact bytes remain outside Practice History.
- [ ] Existing learner ownership and privacy checks remain intact.
- [ ] Existing FIX-3 retry guarantees remain intact.
- [ ] Missing artifacts degrade gracefully.
- [ ] Legacy artifact behaviour is explicitly documented.
- [ ] Required configuration and IAM guidance is documented without secrets.
- [ ] Deployment smoke tests cover practice history and artifact retrieval.
- [ ] Full CI/check suite passes.
- [ ] Existing learner journey semantics remain unchanged.
- [ ] Architecture review approves the implementation.

---

## 20. References

- Project Charter
- Architecture Principles
- Architecture Blueprint
- Domain Language
- SPEC-021 — Persistent Practice History & Learner Review
- SPEC-024 — Learner Identity & Private Practice History
- SPEC-029 — Practice Content Model & Learning Contract
- SPEC-030 — Practice Feedback Quality
- SPEC-031 — Sketchbook-to-Practice Reflection
- SPEC-033 — Complete Sketchbook Reflection with Private Artifact Support
- FIX-2 — Move Sketchbook Artifact Bytes Outside Practice History Storage
- FIX-3 — Make Sketchbook Artifact Persistence Retry-Safe and Validate MIME Consistency
