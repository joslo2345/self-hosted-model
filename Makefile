.DEFAULT_GOAL := help
.PHONY: help install check lint typecheck test engine serve smoke

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

# ---- B1: local serving (vLLM + vllm-metal on the Apple GPU) ----
MODEL ?= mlx-community/Qwen3.5-9B-MLX-8bit
NAME ?= candidate
PORT ?= 8000
SERVE_ARGS ?=

engine:  ## Install pinned vLLM + vllm-metal into .venv-engine
	./scripts/install_engine.sh

serve:  ## Serve MODEL on 127.0.0.1:PORT as NAME (OpenAI-compatible; SERVE_ARGS for parser flags)
	.venv-engine/bin/vllm serve $(MODEL) --served-model-name $(NAME) --host 127.0.0.1 --port $(PORT) \
	  --max-model-len 32768 --enable-auto-tool-choice $(SERVE_ARGS)

smoke:  ## Chat, streaming and tool-call checks against the running endpoint
	uv run selfhost smoke --base-url http://127.0.0.1:$(PORT)/v1 --model $(NAME)
