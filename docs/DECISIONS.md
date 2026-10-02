# Decisions

What was chosen, what was rejected, and why. Newest package last.

## Project setup (2026-10-02)

- **Separate repo from Project A.** Project B talks to Project A only through the agent's
  OpenAI-compatible provider settings (`AGENT_BASE_URL`, `AGENT_MODEL`, `AGENT_LLM_API_KEY`).
  Keeping the repos apart proves the "config switch, no code change" claim.
- **$0 spend.** No cloud GPUs, no paid API. Cloud infrastructure is written and validated, never
  applied; cloud and hosted-API costs are calculated from published prices.
- **No hosted CI.** `make check` runs locally before every push, so the repo uses no GitHub
  Actions minutes.

## B1 · Serving flags (2026-10-02)

- **Parsers:** Qwen3.5 emits tool calls in the Qwen3-Coder XML format, so serving uses
  `--tool-call-parser qwen3_coder` (not `hermes`) plus `--reasoning-parser qwen3`, which keeps
  the thinking text out of `content`. These are the Makefile defaults; override `SERVE_ARGS`
  for other candidates.
- **Pinned revision:** `make serve` passes `--revision` so results are reproducible.

## B1 · Shortlist (2026-10-02)

Criteria: instruction-tuned, native tool calling, permissive license (Apache-2.0 or MIT), an 8-bit
MLX build that vllm-metal can load, and under ~11 GB of weights so it fits next to the KV cache
in 36 GB of unified memory. Sizes and licenses were checked on the Hugging Face API, and engine support in the
installed vLLM 0.30.0 / mlx-lm.

| Model | Params | License | 8-bit weights | Why it's on the list |
| --- | --- | --- | --- | --- |
| `mlx-community/Qwen3.5-9B-MLX-8bit` | 9B, hybrid attention | Apache-2.0 | 10.5 GB | Current default; strong tool calling; same family as the A6 baseline (`qwen3-agent`) |
| `ibm-granite/granite-4.2-8b-q8-mlx` | 8B dense | Apache-2.0 | 9.3 GB | Released 2026-09-01 with an MLX build from IBM; aimed at enterprise tool use and JSON output; a different vendor |
| `mlx-community/gemma-4-e4b-it-8bit` | ~4B effective (8B with per-layer embeddings) | Apache-2.0 upstream | 8.9 GB | Smallest compute per token, so the fastest decode; a third model family |

All three have thinking on by default. The comparison has to run each with thinking both on and
off (or set to low effort), because B1 smoke numbers show thinking dominates latency.

Rejected:
- **Llama 3.1 8B:** Llama Community License, not permissive; 2024-era tool calling.
- **Phi-4-mini (3.8B, MIT):** February 2025 release; weaker multi-step tool use than the newer models.
- **Gemma 4 12B:** 12.7 GB at 8-bit, over budget; it also loads through the mlx-vlm path, which
  vllm-metal flags as less reliable for Gemma 4.
- **Qwen3.5-4B:** same family as the 9B. It stays in reserve as the "smaller Qwen" for the
  size and accuracy trade-off.
- **Granite 4.0-H-Tiny:** superseded by 4.2. **SmolLM3-3B:** weak tool calling. **LFM2.5:** license isn't permissive.

Parsers per model (`make serve CANDIDATE=...`): Qwen uses `qwen3_coder` + `qwen3`. Granite uses
`qwen3_coder` + `nemotron_v3`; the model card names both as compatible, and its custom
`granite_thinking_parser` plugin was skipped to keep the engine stock. Gemma uses `gemma4` + `gemma4`.
