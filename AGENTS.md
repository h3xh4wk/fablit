# AGENTS.md — Fablit

Fast facts so you don't have to rediscover them. For spec/issue implementation
workflow, load the `fablit-issue-playbook` skill — this file does not duplicate it.

## Stack & toolchain

- Python 3.12, FastAPI + Jinja2, hexagonal architecture: `fablit/domain/` (pure,
  infrastructure-free) → `fablit/application/` → `fablit/platform/` + `app/` (web).
- **Always `uv`, never pip/npm**: `uv run pytest`, `uv run ruff check .`, `uv run mypy`.
- mypy is strict and type-checks `tests/` too. Ruff line length 88, py312 target.

## Quality gates (run all before finishing any change)

```bash
uv run pre-commit run --all-files
uv run ruff format --check .   # auto-fix: uv run ruff format <file>
uv run ruff check .
uv run mypy
uv run pytest --cov=app --cov-report=xml --cov-fail-under=80
```

Or `make check` for the consolidated run. New/changed files often need
`uv run ruff format <path>` — the check gate is strict.

## Tests

- Layout: `tests/domain/`, `tests/application/`, `tests/persistence/`, `tests/web/`,
  `tests/e2e/` (Playwright). Domain helpers: `make_<model>(**overrides)` in
  `tests/domain/helpers.py`.
- **Web test gotcha:** many `tests/web/*` files carry their own
  `_first_activity_href()` / `_activity_hrefs()` helper that parses card links out
  of the dashboard HTML. If you change a navigation href in `app/templates/`, grep
  `href="/activities/` under `tests/` and update those helpers in the same change.
- **Browser tests are opt-in:** skipped unless `RUN_BROWSER_TESTS=1`. CI runs them
  in a dedicated job. Local run with a system browser:
  `RUN_BROWSER_TESTS=1 PLAYWRIGHT_EXECUTABLE_PATH=/usr/bin/chromium PLAYWRIGHT_NO_SANDBOX=1 uv run pytest tests/e2e`
  (~2 min). Don't block on them locally; CI covers them.
- Coverage: 100% for `fablit.domain`, 80% overall gate on `app`.

## Workflow conventions

- Sequence: SPEC doc under `specifications/platform/SPEC-NNN-*.md` → GitHub issue
  (Objective / Scope / Non-goals / Acceptance criteria, reference the SPEC) →
  implementation on a branch.
- Branches: `spec-0NN/<short-slug>`. Commit messages historically: `implement issue #N`.
- Issues/PRs: repo `h3xh4wk/fablit`, `gh` CLI authenticated.
- Documentation checklist per implemented spec (domain_language, blueprint, README,
  CHANGELOG) lives in the `fablit-issue-playbook` skill §5 — follow it.

## Non-negotiables

- Domain layer stays pure: no fastapi/pydantic/persistence imports; frozen
  dataclasses; invariants in `__post_init__`. Enforced by `tests/domain/test_domain_independence.py`.
- Learner-facing copy never uses score/grade/mastery/streak/urgency language.
- Reflections/intentions are qualitative artifacts: never scored, analysed, or graded.
