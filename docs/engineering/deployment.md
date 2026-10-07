# Production & Learner Pilot Deployment (SPEC-014 / SPEC-034)

This document describes how Fablit is deployed and operated on Google App Engine (GAE) with durable Datastore practice history and Google Cloud Storage (GCS) artifact storage. It satisfies the deployment documentation requirements of [SPEC-014](specifications/platform/SPEC-014-learner-pilot-deployment.md) (§40) and [SPEC-034](specifications/platform/SPEC-034-google-app-engine-deployment-and-durable-artifact-storage.md) (§16).

---

## 1. Deployment Target

- **Platform:** Google App Engine (Standard Environment)
- **Runtime:** Python 3.12 (`python312`)
- **Persistence:**
  - **Practice History:** Google Cloud Datastore (`practice_history_repository="datastore"`, SPEC-021)
  - **Sketchbook Artifacts:** Google Cloud Storage (`artifact_storage_backend="gcs"`, SPEC-034)
- **Static Assets:** Handled directly via App Engine static file handlers for `/static/`
- **Application Execution:** ASGI application served by `uvicorn` (`app.main:app`)

The platform architecture satisfies all operational requirements:

| Requirement | How it is met |
| --- | --- |
| Stable public URL | `https://<project-id>.appspot.com` (or a custom domain via Cloud Domains) |
| Managed HTTPS / TLS | Google-managed TLS certificates on appspot.com and custom domains |
| Process execution | Standard container instances running `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Practice history persistence | Google Cloud Datastore via `DatastorePracticeHistoryRepository` |
| Durable sketchbook artifacts | Google Cloud Storage via `GCSArtifactStorage` |
| Static asset offloading | Native App Engine static file handlers (`app.yaml`) |
| Observability & logs | Structured JSON logs stream automatically to Google Cloud Logging |
| Zero secrets in source/config | Google Application Default Credentials (ADC) via IAM roles on the App Engine service account |

---

## 2. Required Runtime & Deployment Files

The repository root includes the deployment manifests required by Google Cloud SDK:

- **`app.yaml`**: App Engine deployment manifest:
  - Runtime: `python312`
  - Entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - Static file routing: `/static/` routes to `app/static/`
  - Production environment variables (`FABLIT_ENV=production`, `FABLIT_PRACTICE_HISTORY_REPOSITORY=datastore`, `FABLIT_ARTIFACT_STORAGE_BACKEND=gcs`)
- **`requirements.txt`**: Minimal production dependencies for App Engine buildpacks (FastAPI, Jinja2, Uvicorn, Pydantic, HTTPX, google-cloud-datastore, google-cloud-storage).
- **`.gcloudignore`**: Excludes tests, documentation, caches, virtual environments, and Git metadata from the deployed package.

---

## 3. Storage Architecture

```text
                               Web Browser (Learner)
                                        │
                         HTTPS GET /history/{id}/artifact
                                        │
                                        ▼
                            FastAPI Route (/history)
                                        │
                              Learner Authorization
                            (Cookie-scoped identity)
                                        │
                  ┌─────────────────────┴─────────────────────┐
                  ▼                                           ▼
      DatastorePracticeHistoryRepository              GCSArtifactStorage
                  │                                           │
         Metadata & Completion                      Private Object Stream
                  │                                           │
                  ▼                                           ▼
         Google Cloud Datastore                      Google Cloud Storage
         (PracticeCompletion entity)                 (Private GCS Bucket)
```

### Google Cloud Datastore (Practice History)
- Enabled by `FABLIT_PRACTICE_HISTORY_REPOSITORY=datastore`.
- Learner practice completions are stored as `PracticeCompletion` entities under the learner's namespace.
- No custom composite indexes required.
- Stored completions contain only `ArtifactRef` metadata (never binary image payloads).

### Google Cloud Storage (Private Sketchbook Artifacts)
- Enabled by `FABLIT_ARTIFACT_STORAGE_BACKEND=gcs` and `FABLIT_ARTIFACT_STORAGE_BUCKET=<bucket-name>`.
- Private learner sketchbook images uploaded during reflection practice are stored as binary blobs named by their opaque `artifact_id` (`UUID`).
- GCS blobs are stored with appropriate metadata (`artifact_id`, `filename`) and `content_type` (`image/png`, `image/jpeg`, `image/webp`).
- **No direct or public GCS URLs are ever generated or returned to learners.** Artifacts are served exclusively through the learner-scoped application route `/history/{completion_id}/artifact` with `Cache-Control: private, no-store`.

---

## 4. Security & IAM Configuration

App Engine runs under the project's App Engine default service account (`<project-id>@appspot.gserviceaccount.com`). Authentication to Google Cloud Datastore and Google Cloud Storage happens transparently through **Application Default Credentials (ADC)**.

**No service account keys, passwords, or cloud credentials are stored in code, configuration files, or environment variables.**

### Required IAM Roles

Grant the App Engine default service account the following roles:

```bash
# 1. Datastore read/write access
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<PROJECT_ID>@appspot.gserviceaccount.com" \
  --role="roles/datastore.user"

# 2. Cloud Storage object read/write/delete access on the bucket
gcloud storage buckets add-iam-policy-binding gs://<PROJECT_ID>-artifacts \
  --member="serviceAccount:<PROJECT_ID>@appspot.gserviceaccount.com" \
  --role="roles/storage.objectUser"
```

### Bucket Security Settings

Create the GCS bucket with uniform bucket-level access and public access prevention:

```bash
# Create bucket in the same region as App Engine
gcloud storage buckets create gs://<PROJECT_ID>-artifacts \
  --location=us-central1 \
  --uniform-bucket-level-access

# Enforce public access prevention
gcloud storage buckets update gs://<PROJECT_ID>-artifacts \
  --public-access-prevention
```

---

## 5. Required Environment Variables

All settings are managed via environment variables (`FABLIT_*`), configured in `app.yaml`:

| Variable | Production Value | Description |
| --- | --- | --- |
| `FABLIT_ENV` | `production` | Enables production safety boundary (hides API docs, renders clean error pages) |
| `FABLIT_DEBUG` | `false` | Disables debug mode and tracebacks |
| `FABLIT_LOG_LEVEL` | `INFO` | Emits operational logs |
| `FABLIT_LOG_FORMAT` | `json` | Emits structured JSON logs for Google Cloud Logging |
| `FABLIT_STIMULUS_PROVIDER` | `builtin` | Bundled deterministic stimulus images (zero network dependencies) |
| `FABLIT_PRACTICE_HISTORY_REPOSITORY` | `datastore` | Persists completed practice history in Google Cloud Datastore |
| `FABLIT_ARTIFACT_STORAGE_BACKEND` | `gcs` | Persists sketchbook artifact binaries in Google Cloud Storage |
| `FABLIT_ARTIFACT_STORAGE_BUCKET` | `<project-id>-artifacts` | Name of the private Google Cloud Storage bucket |
| `FABLIT_AUTHORING_SECRET` | `<shared-secret>` | Shared secret for internal AI authoring access (SEC-001). Unset disables authoring. |
| `FABLIT_AI_PROVIDER_API_KEY` | `<provider-key>` | Optional server-side API key for the AI practice authoring provider (SPEC-032 / SEC-001). Never exposed to learners or clients. |
| `FABLIT_AI_PROVIDER_MODEL` | `gemini-2.5-flash` | Gemini model used by the authoring provider adapter (ARCH-001), retained as authoring provenance. Only used when `FABLIT_AI_PROVIDER_API_KEY` is set. |
| `FABLIT_SERVICE_NAME` | `fablit` | Service name tag in structured logs |

---

## 6. Deployment Procedure

### Initial Setup
1. Ensure the Google Cloud SDK (`gcloud`) is installed and authenticated:
   ```bash
   gcloud auth login
   gcloud config set project <PROJECT_ID>
   ```
2. Enable required Google Cloud APIs:
   ```bash
   gcloud services enable appengine.googleapis.com datastore.googleapis.com storage.googleapis.com
   ```
3. Initialize the App Engine application (if not already done):
   ```bash
   gcloud app create --region=us-central1
   ```
4. Create the private GCS bucket and grant IAM permissions as shown in §4.
5. In `app.yaml`, verify that `FABLIT_ARTIFACT_STORAGE_BUCKET` matches your GCS bucket name.

### Deploying the Application
Run the standard App Engine deployment command:

```bash
gcloud app deploy app.yaml
```

The command packages the application, uploads it to App Engine buildpacks, installs dependencies from `requirements.txt`, and provisions traffic to the new version.

---

## 7. Health Check & Verification

### Automated Health Check
- **Endpoint:** `GET /health`
- **Expected:** `200 OK` with JSON `{"status": "healthy"}`

```bash
curl -f https://<PROJECT_ID>.appspot.com/health
```

### Full Deployment Smoke Test Checklist
Perform these steps against the live deployment URL:

1. **Health Verification:** Confirm `GET /health` returns `200 OK`.
2. **Safety Boundary:**
   - Confirm `/docs`, `/redoc`, and `/openapi.json` return `404 Not Found`.
   - Confirm an invalid path or trigger renders the calm error page (`Something went wrong.`) with no stack traces or server paths.
3. **Explore Dashboard:**
   - Navigate to `/`.
   - Verify practice cards render with visual previews and prompt summaries.
4. **Practice Journey & Artifact Upload:**
   - Select the reflection activity (*"Sketchbook Practice — Observational Study"* or similar reflection activity).
   - Verify stimulus, task, and response areas display properly.
   - Attach a sample sketchbook drawing (PNG or JPEG, < 5 MB).
   - Enter response notes and submit.
   - Review evaluation feedback and complete the reflection.
5. **Durable History & Review:**
   - Navigate to `/history`.
   - Verify the newly completed practice appears in history.
   - Click into the practice review.
   - Verify the written submission, evaluation, and reflection are displayed.
   - Verify the attached sketch displays correctly via `/history/{completion_id}/artifact`.
   - Inspect network headers to verify `Cache-Control: private, no-store`.
6. **Cloud Verification:**
   - Check Google Cloud Datastore console: verify a `PracticeCompletion` entity exists with metadata and no large binary blob.
   - Check Google Cloud Storage console: verify an object named after the `artifact_id` UUID exists in the bucket with `Content-Type: image/png` (or jpeg).

---

## 8. Log Access

App Engine streams container stdout and stderr to Google Cloud Logging. To tail real-time structured logs from the terminal:

```bash
gcloud app logs tail -s default
```

Or view them in the Cloud Console under **Logging > Logs Explorer**. Filter by:
```text
resource.type="gae_app"
jsonPayload.service="fablit"
```

Logs are structured JSON containing timestamps, log levels, request paths, and status codes, without sensitive learner response text.

---

## 9. Rollback & Version Management

App Engine maintains historical deployed versions:

- **List existing versions:**
  ```bash
  gcloud app versions list
  ```
- **Instantly roll back to a prior healthy version:**
  ```bash
  gcloud app versions migrate <PREVIOUS_VERSION_ID>
  ```
- **Delete broken versions:**
  ```bash
  gcloud app versions delete <BAD_VERSION_ID>
  ```

---

## 10. Legacy Artifact Operational Policy (AC-034-14)

Earlier pilot deployments hosted on PythonAnywhere or temporary local environments persisted artifacts to ephemeral filesystem directories (`FileArtifactStorage`).

**Operational Decision:** Artifacts from prior ephemeral environments are intentionally **not** migrated or backfilled into GCS.
- Existing historical Datastore records that reference missing artifact files will gracefully degrade:
  - Requesting the artifact route `/history/{completion_id}/artifact` returns an unlisted `404 Not Found`.
  - The review page `/history/{completion_id}` continues to render the full written submission, evaluation findings, feedback, and reflection notes without error.

---

## 11. Internal AI Authoring Security Boundary (SEC-001)

SPEC-032 introduces an internal AI-assisted practice authoring workflow. Because the deployed Fablit platform is publicly accessible, SEC-001 establishes a strict, server-side security boundary around authoring tools:

### Access Boundary & Endpoints

All authoring-only routes and operations are grouped under `/authoring`:
- `GET /authoring` / `GET /authoring/` — Internal authoring workspace UI.
- `GET /authoring/login` & `POST /authoring/login` — Authoring login and session establishment.
- `POST /authoring/logout` — Terminate authoring session.
- `POST /authoring/generate` — Server-side AI candidate generation.
- `GET /authoring/candidates` — Review candidate list.
- `POST /authoring/candidates/{id}/approve` & `POST /authoring/candidates/{id}/reject` — Explicit human review gates.

### Authentication & Authorization Model

1. **Shared Authoring Secret (`FABLIT_AUTHORING_SECRET`):**
   - Authentication relies on a high-entropy shared secret configured in the environment.
   - Secret verification uses constant-time comparison (`hmac.compare_digest`) in `fablit.platform.authoring_auth` to prevent timing attacks.
   - **Secure by default:** If `FABLIT_AUTHORING_SECRET` is unset or blank, authoring access is completely disabled and rejects all access attempts.
2. **Supported Credential Transports:**
   - **Interactive Browser Session:** An author visits `/authoring/login` and provides the secret. On success, the response sets an `HttpOnly`, `SameSite=Lax`, `Path=/authoring` cookie (`fablit_author_token`) with the `Secure` flag enabled in production. The cookie is never sent on public learner routes.
   - **API / Header Authentication:** Supports `Authorization: Bearer <secret>`, HTTP Basic (`Authorization: Basic <base64>`), or `X-Author-Key: <secret>`.
3. **Strict Server-Side Enforcement:**
   - Every authoring endpoint checks authorization server-side before executing handler logic.
   - Unauthorized requests to `/authoring/generate` or `/authoring/candidates` return `401 Unauthorized` (JSON) immediately without invoking the AI provider or any external service.
   - Browser navigation to `/authoring` without authentication renders the authoring login view (`401 Unauthorized`).

### Separation from Learner Surface & Secret Isolation

- **Public Learner Experience Unaffected:** Learner routes (`/`, `/practice`, `/history`, `/health`) remain completely public, anonymous, and unauthenticated. No learner accounts, passwords, or login prompts are ever introduced.
- **Provider Credentials Stay Server-Side:** Any AI provider API key (`FABLIT_AI_PROVIDER_API_KEY`) is stored strictly in server-side configuration and is never transmitted in HTML, client JavaScript, or API responses. The provider-neutral LLM port (ARCH-001) confines the key to the concrete adapter (`fablit/platform/gemini_authoring_provider.py`), which sends it only as a server-side header and translates provider failures into safe `502` responses.
- **Scope Limit:** SEC-001 is purposefully sized as the smallest secure mechanism for the current single internal author. It intentionally avoids multi-user role management (RBAC), public user registration, or external OAuth integrations.

### Operational Deployment Configuration

To enable authoring access in an App Engine deployment:

```bash
# Deploy or update environment variables with the authoring secret and AI provider key:
gcloud app deploy app.yaml --set-env-vars FABLIT_AUTHORING_SECRET="<your-strong-secret>",FABLIT_AI_PROVIDER_API_KEY="<your-ai-key>"
```

To revoke authoring access immediately, remove or clear `FABLIT_AUTHORING_SECRET`:

```bash
gcloud app deploy app.yaml --set-env-vars FABLIT_AUTHORING_SECRET=""
```
