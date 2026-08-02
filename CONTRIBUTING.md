# Contributing

Thanks for contributing to Fablit! This document outlines how to set up a local development environment, run tests, and follow repository conventions.

## Getting started

1. Clone the repo

```bash
git clone https://github.com/h3xh4wk/fablit.git
cd fablit
```

2. Install dependencies with uv

```bash
uv sync --dev
```

3. Install developer Git hooks

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

4. Run project checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=app --cov-report=xml
```

## Common tasks

- Run all checks locally:

```bash
make check
```

- Format files:

```bash
make format
```

- Run tests:

```bash
make test
```

- Publish a release:

```bash
git tag vX.Y.Z
git push origin --tags
```

See `.github/workflows/release.yml` and `docs/engineering/toolchain.md` for release details.

## Environment

- Copy `.env.example` to `.env` for local environment values.
- Do not commit secrets or private keys.

## Notes

- This repository uses `uv.lock` to lock dependencies for reproducibility.
- Use GitHub Actions for CI validation; local checks should match the pipeline.
