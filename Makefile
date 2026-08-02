.PHONY: check install format lint type test release

check: install
	uv run pre-commit run --all-files
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run pytest --cov=app --cov-fail-under=80

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
