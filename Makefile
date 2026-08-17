.PHONY: check install format lint type test e2e release

check: install
	uv run pre-commit run --all-files
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run pytest --cov=app --cov-fail-under=80

# Browser tests are skipped locally by default; they run in the CI browser
# job. This target is only for environments where Playwright/Chromium is
# genuinely available — constrained local environments (no browser download,
# no display, sandbox restrictions) should leave the tests skipped instead.
e2e: install
	uv run playwright install chromium
	RUN_BROWSER_TESTS=1 uv run pytest tests/e2e -v

install:
	uv sync --dev

format:
	uv run ruff format .

lint:
	uv run ruff check .

type:
	uv run mypy

test:
	uv run pytest

release: install
	uv run python -m build
