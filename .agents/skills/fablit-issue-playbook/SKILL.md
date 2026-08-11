---
name: fablit-issue-playbook
description: Fablit project conventions for implementing learning-domain issues quickly and consistently.
---

# Fablit Issue Playbook

Use this playbook whenever implementing a Fablit issue. It captures the project
conventions so you do not need to re-derive them from scratch each time.

## 1. Read order

1. The GitHub issue — fetch with `gh api repos/h3xh4wk/fablit/issues/<N> --jq '{title, body}'` (or `gh issue view <N> --repo h3xh4wk/fablit`).
2. The associated specification under `specifications/platform/SPEC-NNN-*.md`.
3. `docs/architecture/domain_language.md` and `docs/architecture/architecture_blueprint.md`.
4. The existing domain models and tests for the pattern (see section 3).

## 2. Repository layout

- `fablit/domain/` — learning-domain models (in-memory, infrastructure-free)
- `fablit/platform/` — shared platform services (config, logging, metrics, auth, resilience, health)
- `app/` — FastAPI application
- `tests/domain/` — domain unit tests + `helpers.py` construction helpers
- `specifications/platform/` — SPEC-NNN specs (authoritative requirements)
- `docs/` — project charter, architecture, agents/roles, ADRs
- `docs/agents/*.md` — AI agent role definitions; mirror any needed role into `.agents/skills/<role>/SKILL.md` (add YAML frontmatter `name` + `description`) to make it loadable in this runtime

## 3. Domain model conventions (SPEC-005/006/007 pattern)

Every domain model in `fablit/domain/` must follow this pattern:

- **Frozen dataclasses** with `from __future__ import annotations`, `@dataclass(frozen=True)`.
- **UUID identity**: `id: UUID = field(default_factory=uuid4)`, validated with `isinstance` in `__post_init__`.
- **References by identity only** (UUID), never duplicating the referenced aggregate (e.g. `Evaluation.submission_id`, `Submission.activity_id`, `Submission.learner_id`).
- **All invariants validated in `__post_init__`** with precise, lowercase error messages that include the offending value.
- **Immutability**: no mutators; enforce at-least-one collection invariants; use tuples for immutable collections; reject empty/blank strings for required text.
- **Timezone-aware datetimes** (`datetime.now(UTC)` / `from datetime import UTC, datetime`) for timestamps; reject naive datetimes and `None`.
- **Domain errors in `fablit/domain/types.py`**, extending `DomainError` (e.g. `InvalidXError`), with specialized subclasses where relevant (e.g. `InvalidEvaluationFindingError(InvalidEvaluationError)`).
- **Controlled terminology**: `StrEnum` types live in `types.py`.
- **Export everything** from `fablit/domain/__init__.py` (models + errors) with an explicit `__all__`.

### Must NOT appear in domain code

- persistence imports (`sqlalchemy`, `psycopg`, `redis`, `sqlite3`, `motor`)
- framework imports (`fastapi`, `pydantic`, `uvicorn`)
- examination-specific terms (`nift`, `nid`, `ceed`) — enforced by `tests/domain/test_domain_independence.py`
- score/grading/AI-provider/feedback concepts unless the SPEC introduces them

## 4. Test conventions

- Helpers in `tests/domain/helpers.py`: one `make_<model>(**overrides)` per model with sensible defaults; tests override via kwargs.
- New tests in `tests/domain/test_<model>.py`, mirroring `test_submission.py` / `test_evaluation.py` structure:
  - creation & identity, association, invariants, timestamps, immutability (`FrozenInstanceError`, `dataclasses.replace`), boundaries, and **source-independence tests** (read the module source with `Path(module.__file__).read_text()` and assert forbidden imports/terms absent).
- When a spec lands, update `tests/domain/test_domain_independence.py` if it asserted that the new concept was absent (e.g. remove the `class Evaluation` absence assertion but keep `class Feedback`).
- Coverage target: 100% for `fablit.domain`; CI gate is 80% overall on `app`.

## 5. Documentation checklist (every implemented spec)

Update ALL of these:

1. `docs/architecture/domain_language.md` — add a "«Concept» Domain Model (SPEC-NNN)" section with relationship diagram + DR table; bump version + Last Updated.
2. `docs/architecture/architecture_blueprint.md` — align the concept's section with what was implemented.
3. `README.md` — update the implemented-specs list, the learning-domain bullets, and the "deferred behaviour" sentence.
4. `CHANGELOG.md` — add a "SPEC-NNN — ..." entry under `[Unreleased]` → `### Added`.

## 6. Quality gates (run all before finishing)

```bash
uv run pre-commit run --all-files
uv run ruff format --check .        # auto-fix with: uv run ruff format <file>
uv run ruff check .
uv run mypy
uv run pytest --cov=app --cov-report=xml --cov-fail-under=80
```

Known gotchas:
- New/changed files often need `uv run ruff format <path>` — the `--check` gate is strict.
- `mypy` is strict (`py312`, `packages = ["app", "fablit", "tests"]`) — tests are type-checked too.

## 7. Workflow

1. Read the issue + spec (section 1).
2. Route by concern: backend → backend-engineer, frontend → front-engineer, architecture → architect, testing → qa-engineer, release → release-manager. Load the role skill if saved.
3. Implement with minimal changes; lean on existing models; never add dependencies without issue justification.
4. Write/extend tests + helpers.
5. Update docs per section 5.
6. Run all gates (section 6); fix until green.
7. Have a code-reviewer review the diff before summarizing.
