# Results

Every package records at least one measured number here. Hardware: Apple M3 Pro, 36 GB.

## B1 · Local serving smoke test (2026-10-02)

Engine: vLLM 0.30.0 + vllm-metal 0.30.0 (MLX, Apple GPU). Model: `mlx-community/Qwen3.5-9B-MLX-8bit`
at revision `84f7c2deea248d8df56240f88102def51c7ed5d6`, served with
`--tool-call-parser qwen3_coder --reasoning-parser qwen3 --max-model-len 32768`.

| Measure | Value |
| --- | --- |
| Weights on disk | 10.5 GB |
| Engine start to ready (warm cache) | ~55 s (engine init 20 s) |
| KV + state cache allocated | 15.05 GiB |
| Decode speed, one request | ~11 tokens/s |
| `make smoke`: chat / stream / tool call | PASS 19.1 s / PASS 15.1 s / PASS 64.6 s |
| "Reply with one word" request | 110 completion tokens, 106 of them reasoning |

Thinking mode is on by default and accounts for nearly all of the latency. The decode speed is
close to the memory-bandwidth limit for ~10 GB of weights on an M3 Pro (150 GB/s), so the
comparison runs have to control thinking. Quantization alone won't fix it.

## B1 · Shortlist smoke tests (2026-10-02)

Each model was served alone with `make serve CANDIDATE=...` (pinned revision, parsers per
docs/DECISIONS.md), then checked with `make smoke` and a one-word prompt. Engine and hardware are the same as above.

| | Qwen3.5-9B 8-bit | Granite 4.2 8B q8 | Gemma 4 E4B 8-bit |
| --- | --- | --- | --- |
| Weights | 10.5 GB | 9.3 GB | 8.9 GB |
| Start to ready (warm cache) | ~55 s | 23 s | 43 s |
| Smoke chat / stream / tool call | PASS 19.1 / 15.1 / 64.6 s | PASS 5.8 / 5.6 / 50.8 s | PASS 3.6 / 0.7 / 2.5 s |
| First tool chosen | `get_metrics` | `get_incident` | `get_incident` |
| Thinking by default | on | on | off |
| "ready" prompt: completion / reasoning tokens | 110 / 106 | 39 / 35 | 2 / 0 |
| Thinking can be turned off per request | (to test) | yes (`enable_thinking: false`) | yes (`enable_thinking: true` turns it on) |
| Decode speed, one request | ~11 tok/s (server log) | ~11.4 tok/s (server log) | ~16 tok/s (400-token answer, end to end) |

These are latency and tool-calling plumbing checks, not accuracy. Quality is measured by the
20-incident comparison against the A6 baseline. Qwen and Granite decode at the same speed
because both are memory-bandwidth bound at ~10 GB. Gemma's smaller per-token compute buys
~40% more speed. Its latency lead in the smoke tests mostly comes from not thinking by default.
