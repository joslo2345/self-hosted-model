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

## B1 · Model choice (2026-10-02)

**Chosen: Qwen3.5-9B (8-bit MLX), thinking off** (`make serve`, which now defaults to `THINK=false`).
The evidence is the 20-incident comparison in docs/RESULTS.md.

- It ties for the best root cause (20/20, against 18/20 for the baseline) and has the best runbook
  citations (18/20) and citation support (99%), with no failed runs.
- It leaves one real fault in service, against Granite's three. Its other misses are too aggressive
  (`replace_part` where the runbook says drain). On a GPU fleet, a broken GPU left serving jobs costs more
  than an unneeded part swap, so this decided Qwen over Granite.
- It's about 25% slower than Granite (p50 147 s vs 117 s, single stream). That's acceptable for an
  incident assistant; B4 measures it under load.

Rejected:
- **Granite 4.2 8B:** the fastest and steadiest, and close on accuracy. It's the runner-up, and the
  pick if latency turns out to matter more than the power-fault misses.
- **Gemma 4 E4B:** the smallest and never left a fault in service. But it had the weakest action and
  runbook scores, and with thinking on its tool calls broke.
- **Thinking on (any model):** every model did worse with it on this hardware. Revisit it on GPU
  hardware in B2–B4, where decode is several times faster.

Method choices:
- Thinking is switched on the server (`--default-chat-template-kwargs`), not in Project A, so the
  "config switch, no code change" claim holds.
- vLLM serves on port 8100 at 60% of unified memory, so Project A's Docker stack runs alongside it.
- The judge (`gemma3:12b` on Ollama) ran after the agent runs, not during them, because the two
  models don't fit in memory together. Root cause, actions and runbook scores don't use the judge.

## B1 · Precision (2026-10-02)

**8-bit** (results in docs/RESULTS.md, "Quantization").
- **4-bit rejected:** it doubled the agent's steps, overflowed the context twice and lost 3 root
  causes. The memory saving (6.0 vs 10.5 GB) isn't worth it at 36 GB.
- **bf16 not chosen for the laptop:** it was one action decision better, but needed 1.8× the memory
  (it only fits with Project A's stack at a 70% cap) and was 45% slower at p50. Re-test it on GPU
  hardware in B2, where memory is less tight and bf16 is the more usual serving format.
- AWQ and GPTQ (named in the plan) are CUDA formats; MLX's group-wise 4- and 8-bit quantization is the
  equivalent on Apple GPUs. B2 can compare AWQ against FP16 on an NVIDIA GPU if credits allow.
