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
# Shortlisted models, pinned to a revision with the parsers each one needs (docs/DECISIONS.md).
CANDIDATE ?= qwen
ifeq ($(CANDIDATE),qwen)
MODEL ?= mlx-community/Qwen3.5-9B-MLX-8bit
REVISION ?= 84f7c2deea248d8df56240f88102def51c7ed5d6
SERVE_ARGS ?= --tool-call-parser qwen3_coder --reasoning-parser qwen3
else ifeq ($(CANDIDATE),qwen4)
MODEL ?= mlx-community/Qwen3.5-9B-MLX-4bit
REVISION ?= 938d8919941c6e7efd3c7150eff7fe9d12afa631
SERVE_ARGS ?= --tool-call-parser qwen3_coder --reasoning-parser qwen3
else ifeq ($(CANDIDATE),qwenbf16)
MODEL ?= mlx-community/Qwen3.5-9B-MLX-bf16
REVISION ?= d3b9dc1f346d744d22c6a22fcfcf03702cbe0124
SERVE_ARGS ?= --tool-call-parser qwen3_coder --reasoning-parser qwen3
else ifeq ($(CANDIDATE),granite)
MODEL ?= ibm-granite/granite-4.2-8b-q8-mlx
REVISION ?= a60999a162a4799c52a7bd6ec65c780d6138cfcf
SERVE_ARGS ?= --tool-call-parser qwen3_coder --reasoning-parser nemotron_v3
else ifeq ($(CANDIDATE),gemma)
MODEL ?= mlx-community/gemma-4-e4b-it-8bit
REVISION ?= 4255b21bd9a9d3fc807ef7abd80373f5e3a52a73
SERVE_ARGS ?= --tool-call-parser gemma4 --reasoning-parser gemma4
else
$(error CANDIDATE must be qwen, qwen4, qwenbf16, granite or gemma)
endif
NAME ?= candidate
# Thinking off by default: it was better for every model in the B1 comparison (docs/RESULTS.md).
THINK ?= false
# 8100, because Project A's local stack uses 8000.
PORT ?= 8100
# Share of unified memory vLLM may use; 0.6 leaves room for Project A's Docker stack.
GPU_MEM ?= 0.6

engine:  ## Install pinned vLLM + vllm-metal into .venv-engine
	./scripts/install_engine.sh

serve:  ## Serve a shortlisted model on 127.0.0.1:PORT (CANDIDATE=qwen|qwen4|qwenbf16|granite|gemma, THINK=true|false)
	.venv-engine/bin/vllm serve $(MODEL) --revision $(REVISION) --served-model-name $(NAME) --host 127.0.0.1 --port $(PORT) \
	  --max-model-len 32768 --gpu-memory-utilization $(GPU_MEM) --enable-auto-tool-choice $(SERVE_ARGS) \
	  $(if $(THINK),--default-chat-template-kwargs '{"enable_thinking": $(THINK)}')

smoke:  ## Chat, streaming and tool-call checks against the running endpoint
	uv run selfhost smoke --base-url http://127.0.0.1:$(PORT)/v1 --model $(NAME)
