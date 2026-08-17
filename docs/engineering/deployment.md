# Learner Pilot Deployment (SPEC-014)

This document describes how the Fablit learner pilot is deployed and operated.
It satisfies the deployment documentation requirements of
[SPEC-014](specifications/platform/SPEC-014-learner-pilot-deployment.md) (§40)
and is written so another developer can understand and reproduce the pilot
environment.

> **Deploy what we have. Do not redesign what we have just because we are
> deploying it.** SPEC-014 adds an operational boundary around the existing
> SPEC-013 learner experience; it introduces no new learning capability and no
> new domain concept.

## 1. Deployment target

- **Provider:** PythonAnywhere (see [ADR-008](../adr/ADR-008-pythonanywhere-deployment.md))
- **Environment:** a dedicated pilot environment, separate from local
  development, driven entirely by environment-variable configuration
- **Plan:** a paid (inexpensive) plan with an "Always-on" option is recommended
  so the pilot stays reachable during the learner testing period; the free
  plan's sleep-on-idle behaviour interrupts the pilot

The provider supplies everything the pilot needs (§9):

| Requirement | How it is met |
| --- | --- |
| Stable public URL | `https://<username>.pythonanywhere.com` (or a custom domain) |
| HTTPS | Managed TLS — free on PythonAnywhere subdomains, Let's Encrypt for custom domains |
| Application process execution | ASGI site running uvicorn |
| Required Python/runtime dependencies | Virtualenv on the host |
| Persistent storage where required | Not required — see [Persistence](#6-persistence-behaviour) |
| Environment configuration | Environment variables |
| Basic logs | Access/error/server logs under `/var/log/` |

## 2. Required runtime

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency installation
- The application is an ASGI app: `app.main:app`, served by uvicorn
  (FastAPI, Jinja2 templates, and HTMX — all already project dependencies)

## 3. Required environment variables

All configuration comes from environment variables (`FABLIT_*`); nothing
environment-specific is hard-coded into the application, and no secrets are
committed to the repository (§12–13).

| Variable | Pilot value | Notes |
| --- | --- | --- |
| `FABLIT_ENV` | `production` | Enables the pilot safety boundary (see [Safety](#9-safety-boundary)) |
| `FABLIT_DEBUG` | `false` | Debug mode is disabled for learners |
| `FABLIT_LOG_LEVEL` | `INFO` | Basic operational logs |
| `FABLIT_LOG_FORMAT` | `json` | Structured logs for the pilot |
| `FABLIT_HOST` | `0.0.0.0` | Binds the server (uvicorn `--uds` overrides this on PythonAnywhere) |
| `FABLIT_PORT` | `8000` | Default port (uvicorn `--uds` overrides this on PythonAnywhere) |
| `FABLIT_SERVICE_NAME` | `fablit` | Service name in log records |
| `FABLIT_VERSION` | current release | Version recorded in logs at startup |
| `FABLIT_STIMULUS_PROVIDER` | `builtin` (default) | Visual stimulus source: `builtin` serves deterministic bundled images with no network; `wikimedia` retrieves images from the approved external source (see below) |

Optional stimulus settings (only needed when `FABLIT_STIMULUS_PROVIDER=wikimedia`
or when overriding the bundled fallback images):

| Variable | Default | Notes |
| --- | --- | --- |
| `FABLIT_STIMULUS_FALLBACK_IMAGES` | (none) | JSON object mapping activity title to a custom fallback image URL, overriding the bundled images without code changes |
| `FABLIT_WIKIMEDIA_ENDPOINT` | `https://commons.wikimedia.org/w/api.php` | Wikimedia Commons API endpoint |
| `FABLIT_WIKIMEDIA_TIMEOUT` | `10.0` | Retrieval timeout in seconds |
| `FABLIT_WIKIMEDIA_WIDTH` | `1200` | Requested thumbnail width |
| `FABLIT_WIKIMEDIA_LIMIT` | `5` | Candidate images searched |

**Secrets:** the pilot has no secrets to configure — there is no database and
no API key. The default `builtin` stimulus provider also needs no external
service; switching to `FABLIT_STIMULUS_PROVIDER=wikimedia` adds an outbound
dependency on the Wikimedia Commons API, which must be reachable from the
host and falls back to the bundled images when retrieval fails (§21–22 of
SPEC-015). If any secrets are ever needed, they must be set through the
provider's environment mechanism and never committed (§13).

## 4. Build / install process

```bash
# 1. Get the code (on the PythonAnywhere host, in a Bash console)
git clone https://github.com/h3xh4wk/fablit.git
cd fablit

# 2. Create the virtualenv at the location the ASGI site command expects
#    (PythonAnywhere's conventional ~/.virtualenvs/<name> path), then install
#    the project — including uvicorn — into that exact virtualenv.
#    (Using a venv at ~/.virtualenvs keeps it outside the project directory,
#    so redeploys that rewrite ~/fablit never orphan the site's interpreter.)
uv venv ~/.virtualenvs/fablit
UV_PROJECT_ENVIRONMENT=~/.virtualenvs/fablit uv sync --dev
```

## 5. Startup command

Local reference command (deterministic, documented):

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On PythonAnywhere the site is managed through the `pa` command-line tool
(ASGI sites, currently in beta). Install the tool once per account, then
create the site:

```bash
pip install --upgrade pythonanywhere
pa website create \
  --domain <username>.pythonanywhere.com \
  --command '/home/<username>/.virtualenvs/fablit/bin/uvicorn --app-dir /home/<username>/fablit --uds ${DOMAIN_SOCKET} app.main:app'
```

Set the pilot environment variables before first start (e.g. in the site
command or the host environment):

```bash
export FABLIT_ENV=production
export FABLIT_DEBUG=false
export FABLIT_LOG_LEVEL=INFO
export FABLIT_LOG_FORMAT=json
```

Once created, the site runs continuously — no developer starts a local process
after every restart (§11).

## 6. Persistence behaviour

The current application persists the learner journey **in memory only**
(`fablit.application.LearnerJourneyStore`, SPEC-012 §28). Verified for the
pilot (§15):

| Question | Answer |
| --- | --- |
| What data is persisted? | Demo activities/skills (seeded in code) and one learner journey's Submission → Evaluation → Feedback → Reflection records, all in process memory |
| Where is it persisted? | Nowhere on disk — in-memory dictionaries in the running process |
| How long does it survive? | Until the process stops or the app is restarted/redeployed |
| What happens on restart? | All journey state is lost; the next visitor starts fresh with the demo content |

**Verification:** this behaviour is acceptable for the pilot — the demo
journey is single-learner, restarts reset only in-progress state, and the
pilot does not need multi-user or durable storage. **No persistence upgrade is
introduced.** The expected data-loss risk is documented in
[§13 Known limitations](#13-known-pilot-limitations) and
[Backup and Recovery (SPEC-014 §29)].

## 7. Health check

- Endpoint: `GET /health`
- Expected: `200 OK` with `{"status": "healthy"}`

Use it to confirm the application is available (e.g. before and after a
restart, and as part of deployment verification).

## 8. Log access

The application emits structured JSON logs (startup, request completion,
significant errors) through the shared logging setup. On PythonAnywhere the
uvicorn error/server output lands in:

```text
/var/log/<username>.pythonanywhere.com.error.log
/var/log/<username>.pythonanywhere.com.server.log
/var/log/<username>.pythonanywhere.com.access.log
```

These logs let the team determine when the application started, when
significant errors occurred, which endpoint or operation failed, and whether
the application became unavailable (§21). Logs do not include learner response
content or other sensitive learner information.

## 9. Safety boundary

The pilot environment (§19, §43):

- **No development interfaces:** `/docs`, `/redoc`, and `/openapi.json` are
  disabled in the `production` environment (they remain available in
  development and testing).
- **No debug output:** `FABLIT_DEBUG` is `false`; unhandled errors render a
  learner-friendly error page (`Something went wrong.`) with no stack traces,
  file paths, environment variables, or framework debugging pages (§20). Full
  tracebacks are written to the server logs only.
- **No admin functionality:** the application exposes no administrative
  endpoints, development tools, debugging interfaces, source repositories, or
  credentials.
- **No committed secrets:** the repository contains no credentials or API keys.
- **Data minimisation:** the application collects only what the journey
  itself requires; no identity, demographic, or tracking data is collected
  (§44). Learner feedback is recorded externally per
  [the pilot feedback record](../pilot/feedback-record.md).

## 10. Restart procedure

- **Restart the app:** `pa website reload --domain <username>.pythonanywhere.com`
- **Redeploy new code:** pull the latest commit on the host, re-run
  `uv sync --dev`, then reload the site:

```bash
git pull
UV_PROJECT_ENVIRONMENT=~/.virtualenvs/fablit uv sync --dev
pa website reload --domain <username>.pythonanywhere.com
```

Every restart resets in-memory journey state (see
[§6 Persistence](#6-persistence-behaviour)).

## 11. Rollback

Deployment comes from the repository, so the rollback path is Git-based (§42):

```bash
git log --oneline -5
git checkout <last-known-good-commit-or-tag>
pa website reload --domain <username>.pythonanywhere.com
```

Alternatively, PythonAnywhere keeps the site's own server logs and the ASGI
site can be recreated from any prior commit; either way the pilot can return
to the last known-good version without manual fixes.

## 12. Deployment verification

Before inviting learners, verify the pilot through the **actual public URL**
(§23–26), not just the local server:

1. `GET /health` returns `200 OK`.
2. Complete the full journey in a real browser:
   Dashboard → choose an activity → **see the visual stimulus** → submit a
   response → receive response-aware feedback → reflect → completion → back
   to practice.
3. Repeat the journey at a mobile-sized viewport (≈390 px wide).
4. Check accessibility behaviour: keyboard navigation, visible focus, labelled
   controls, single-h1 hierarchy, skip link, and readable contrast.
5. Confirm a broken/unknown action shows the learner-friendly error page and
   that `/docs` returns 404.

The existing automated suites remain the primary regression path:
`tests/web/test_learner_flow.py`, `tests/web/test_deployment.py`, and the
opt-in Playwright journey in `tests/e2e` (`RUN_BROWSER_TESTS=1`).

## 13. Known pilot limitations

- **In-memory persistence:** all journey state is lost on restart or redeploy;
  a learner mid-journey during a deployment can lose their progress.
- **Single demo learner:** the application models one demo learner journey; it
  is not multi-user.
- **No production SLA:** the pilot is not production infrastructure (§28);
  availability is best-effort for the testing period.
- **ASGI hosting is experimental on PythonAnywhere:** the `pa` CLI and ASGI
  site support are in beta; syntax may change.
- **No authentication:** the pilot is open by design (§18). Anyone with the
  URL can use it; the URL should only be shared with invited learners.
- **No backup/recovery system:** there is no disaster-recovery process; the
  environment is recreated from the repository (§29).

## 14. Deployment checklist

- [ ] `FABLIT_ENV=production` is set on the host
- [ ] `FABLIT_DEBUG=false`, `FABLIT_LOG_LEVEL=INFO`, `FABLIT_LOG_FORMAT=json`
- [ ] `FABLIT_STIMULUS_PROVIDER` left at the default `builtin` (or set deliberately)
- [ ] `/docs`, `/redoc`, `/openapi.json` return 404 on the public URL
- [ ] `GET /health` returns `200 OK` on the public URL
- [ ] Full learner journey verified in a real browser against the public URL (visual stimulus visible, response-aware feedback shown)
- [ ] Mobile viewport and accessibility checks pass against the public URL
- [ ] Learner instructions shared with participants
  ([learner-instructions.md](../pilot/learner-instructions.md))
- [ ] Feedback-recording mechanism ready
  ([feedback-record.md](../pilot/feedback-record.md))
- [ ] Rollback commit/tag identified
