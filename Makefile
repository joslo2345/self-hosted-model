.DEFAULT_GOAL := help
.PHONY: help install check lint typecheck test

help:  ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

install:  ## Install the package and dev tools
	uv sync

lint:  ## Ruff lint and format check
	uv run ruff check .
	uv run ruff format --check .

typecheck:  ## Strict mypy
	uv run mypy

test:  ## Unit tests
	uv run pytest -q

check: lint typecheck test  ## Everything to run before a push (there is no hosted CI)
