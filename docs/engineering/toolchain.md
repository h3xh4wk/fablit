# Engineering Toolchain

This page documents the engineering toolchain implemented to satisfy `SPEC-002`.

## Toolchain decisions

- Dependency management: `uv` is the primary package manager, with a committed `uv.lock` to ensure reproducible dependency resolution.
- Formatting and linting: `ruff` is the primary linter and Python formatter.
- Pre-commit: `.pre-commit-config.yaml` is configured to run `ruff` and housekeeping hooks before commits.
- Type checking: `mypy` is configured in `pyproject.toml` with strict type checking.
- Testing: `pytest` is the test runner and `pytest-cov` is used for coverage reporting.
- CI: GitHub Actions executes quality checks on every pull request and push to `main`.
- Release workflow: `release.yml` builds distributions and publishes tags via PyPI token.

## Where to find things

- `pyproject.toml` — source dependency declarations and static analysis configuration.
- `uv.lock` — locked dependency graph for the project.
- `.pre-commit-config.yaml` — commit-time hooks.
- `.github/workflows/ci.yml` — continuous integration pipeline.
- `.github/workflows/release.yml` — release publishing workflow.
- `CONTRIBUTING.md` — developer onboarding and local workflow.
- `.env.example` — local environment example.
- `Makefile` — common developer tasks.

## Local workflows

Install dependencies:

```bash
uv sync --dev
```

Install Git hooks:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Run the full developer check sequence:

```bash
make check
```

Build distributions locally:

```bash
uv run python -m build
```

## Updating dependencies

The primary source of truth is `pyproject.toml`.

To update dependencies:

1. Update the desired version constraints in `pyproject.toml`.
2. Run `uv lock` to regenerate `uv.lock`.
3. Commit both `pyproject.toml` and `uv.lock` together.

## Notes

- `uv.lock` is committed to ensure consistent installs across developer machines and CI.
- Do not commit `.env`; use `.env.example` as the template.
