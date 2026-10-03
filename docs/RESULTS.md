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

## B1 · 20-incident comparison (2026-10-02)

Project A's eval harness (unchanged, commit `b26257a`) ran on the first 20 cases of its `test`
set against each shortlisted model, with thinking on and off. Only its provider settings pointed at
local vLLM (`scripts/compare_b1.sh`). The agent budget was Project A's default for every run,
including its 300 s limit per model call, and every model ran at a 32,768-token context like the
baseline. Citations were re-judged afterwards with the baseline's judge (`gemma3:12b`, prompt v2).
The baseline is Project A's `final-r3` test report restricted to the same 20 cases: Qwen3 30B-A3B
(`qwen3-agent`) on Ollama. Reports are in `eval/b1/`, and the table is `eval/b1/summary.json`.

| Model, thinking | Root cause | Action allowed | Fault left in service | Right runbook | Citation support | Latency p50 / p95 | Failed runs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Qwen3.5-9B, off** | **20/20** | 17/20 | 1 | **18/20** | **99%** | 147 / 222 s | 0 |
| Granite 4.2 8B, off | **20/20** | 17/20 | 3 | 17/20 | 96% | **117 / 152 s** | 0 |
| Gemma 4 E4B, off | **20/20** | 16/20 | **0** | 16/20 | 96% | 121 / 262 s | 0 |
| Qwen3.5-9B, on | 18/20 | 16/20 | **0** | 15/20 | 93% | 214 / 382 s | 2 (timeout) |
| Granite 4.2 8B, on | 13/20 | 13/20 | **0** | 12/20 | 95% | 386 / 683 s | 7 (timeout) |
| Gemma 4 E4B, on | 17/20 | 15/20 | 1 | 13/20 | 90% | 198 / 351 s | 3 |
| *Baseline: Qwen3 30B-A3B, Ollama* | 18/20 | **18/20** | 1 | 16/20 | 92.5% | 122 / 213 s | 0 |

All runs cost $0 (local hardware). The 20 cases cover six fault types: pcie 3, thermal 3, ecc 4, gpu_off_bus 4,
nvlink 3, power 3. **They include no noisy-neighbor faults and no decoys**, so unsafe-action
rate isn't measured here.

Findings:
- **Thinking off is better for every model on this laptop.** At ~11 tokens/s a single thinking turn
  can pass the agent's 300 s per-call limit (all 9 Qwen and Granite failures). Gemma with thinking on
  also wrote two tool calls as plain text (`<tool_code`), which the parser can't extract, and one
  run went over the 32,768-token context. When Granite did finish with
  thinking on, all 13 answers were right, so thinking may pay off on a faster GPU (B2–B4).
- **All three models with thinking off beat the baseline on root cause** (20/20 vs 18/20) and on
  citation support, and are within one or two cases of it on actions.
- **The action misses differ by model.** Qwen's 3 misses: `replace_part` on two gpu_off_bus cases and
  `monitor` on one power fault. Granite's 3 misses all left a power fault in service (`monitor` or `none`).
  Gemma's 4 misses: `replace_part` on two NVLink cases, `reset_gpu`, and `escalate`.

## B1 · Quantization: Qwen3.5-9B at 4-bit, 8-bit and bf16 (2026-10-02)

The same 20 cases, the same harness and judge, thinking off. All three are the `mlx-community/Qwen3.5-9B-MLX-*`
conversions of one checkpoint (revisions pinned in the Makefile as `CANDIDATE=qwen4|qwen|qwenbf16`).
MLX quantizes weights with affine group-wise quantization (group size 64). The plan's AWQ and GPTQ
are CUDA formats that vllm-metal can't load, so this is the Apple-GPU equivalent.

| Precision | Weights | Root cause | Action allowed | Fault left in service | Right runbook | Citation support | Steps per case | Tokens per case | Latency p50 / p95 | Decode tok/s | Failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4-bit | **6.0 GB** | 17/20 | 14/20 | 0 | 15/20 | 97% | 9.2 | 110,566 | 168 / 278 s | **13.5** | 2 (context overflow) |
| **8-bit (chosen)** | 10.5 GB | **20/20** | 17/20 | 1 | **18/20** | **99%** | **4.3** | 40,084 | **147 / 222 s** | 11.6 | 0 |
| bf16 | 18.8 GB | **20/20** | **18/20** | **0** | **18/20** | 96% | **4.3** | **38,935** | 214 / 324 s | 7.2 | 0 |

Decode speed is the median of vLLM's 10-second throughput log while serving one request. Those windows include
some prompt processing, so read the speeds as relative rather than as peak decode. bf16 ran at
`GPU_MEM=0.7`, because at 0.6 vLLM computed a negative cache budget (-1.6 GB) and refused to start. The
other two ran at 0.6. Swap fell during the bf16 run (9.5 → 7.3 GB), so memory pressure didn't
affect its latency.

Findings:
- **4-bit breaks the agent loop.** It took twice as many steps (9.2 vs 4.3) and 2.8× the tokens.
  Two runs looped until they overflowed the 32k context, and it misread one gpu_off_bus fault as
  pcie_degradation. Its faster decode doesn't make up for the extra steps.
- **8-bit loses one action decision against bf16** (17 vs 18; a power fault left on `monitor`). It
  matches bf16 on root cause and runbook, uses 56% of the memory, and is 31% faster at p50.
- **bf16 is the most accurate run in B1.** It's also the only one to match the baseline's 18/20 on
  actions. On a GPU with memory to spare (B2), it's worth re-testing.

## B2 · Kubernetes deployment (2026-10-03)

The chart (`deploy/helm/vllm`) was tested on a local kind cluster with Calico, using vLLM's CPU
image (`vllm/vllm-openai-cpu:v0.30.0`) and `Qwen/Qwen3.5-0.8B` as a stand-in for the GPU model. The
AKS GPU pool (`infra/azure`) passes `terraform validate` against the azurerm 5.8 provider. Nothing
was applied in Azure ($0).

**Chart checks on kind** (`make kind-check`, all passing):

| Check | Result |
| --- | --- |
| `/health` without a key (used by the probes) | 200 |
| API without a key / with the key | 401 / 200 |
| From Project A's agent pod (namespace `ia`, `app.kubernetes.io/name=agent`) | allowed |
| From another pod in `ia`, or from a pod in vLLM's own namespace, with the key | blocked by NetworkPolicy |
| Streaming (protocol level) | 34 SSE chunks, then `[DONE]` |

**Cold start on kind**, from pod created to Ready (`make cold-start`, image already on the node):

| Start | Pod to Ready | Weight fetch (init container) |
| --- | --- | --- |
| Empty cache volume | 65 s | 21 s |
| Cached weights | 43 s | 1 s |
| Cached + `HF_HUB_OFFLINE` | **31 s** | 1 s |

The image pull added 30 s on first use (1.3 GB CPU image). The weight cache plus offline mode cut
startup by about half (65 → 31 s). The download share grows with model size: the 0.8B weights
(1.6 GB) took 21 s, about 80 MB/s. At that rate the GPU model's bf16 weights (19 GB) would take
about 4 minutes, which is the step the cache volume removes on every restart after the first.

Not measured, because doing so costs money: GPU node scale-up time, and model load time on an A100.
The plan's "time from node scale-up to first token" needs a real GPU node; B4 can measure it if
cloud credits are available.

Problems the kind test caught before any cloud run:
- **Service links broke vLLM.** A Service named `vllm` makes Kubernetes inject `VLLM_PORT=tcp://…`,
  which vLLM reads as its own setting and refuses to start. Fixed with `enableServiceLinks: false`.
  The GPU deployment would have failed the same way.
- **Download and load in one process ran out of memory.** On the first start vLLM downloaded and
  loaded the weights in the same process, and the memory peak OOM-killed it. Fixed with a
  `fetch-weights` init container that downloads to the cache volume first. Download retries no
  longer restart the engine, and the startup probe only has to cover loading.
- **The vision encoder was loaded for nothing.** Qwen3.5 loads it by default. The agent is text-only,
  so both value sets set `--limit-mm-per-prompt` to zero images and video.
