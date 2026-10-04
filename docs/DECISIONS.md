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

## B2 · Kubernetes deployment (2026-10-03)

- **Separate Terraform stack for the GPU pool.** `infra/azure` looks up Project A's AKS cluster
  and adds a node pool. It has its own state, so B can be applied and destroyed without touching A,
  and Project A's code stays unchanged.
- **GPU pool:** one `Standard_NC24ads_A100_v4` (A100 80 GB), spot, autoscaling 0–1, tainted so only vLLM lands there.
  An A100 fits the bf16 weights that B1 found slightly more accurate, as well as FP8. T4s were
  rejected: no bf16 or FP8 support, and 16 GB is too small for the bf16 9B. Prices and the spot
  trade-off are B4's job. Check GPU quota in the region before applying.
- **Drivers:** AKS-managed (`gpu_driver = "Install"`) plus the NVIDIA device plugin, not the GPU
  Operator. AKS already handles the driver, so the operator would add components nothing uses.
- **Model on GPU:** `Qwen/Qwen3.5-9B` bf16 weights with `--quantization fp8` at load. That's the
  NVIDIA counterpart of B1's 8-bit choice; Qwen publishes no FP8 checkpoint of the 9B.
- **Weight cache:** a 40 Gi `managed-csi-premium` volume, kept on uninstall, filled by an init
  container. `cache.offline=true` after the first download removes the Hugging Face dependency at
  startup. Caveat: Azure disks are zonal. After scale-to-zero, the new GPU node must come up in the
  same zone to reattach the disk; otherwise the pod waits. Pin the GPU pool to that zone, or move to
  Azure Files or baked-in weights if this turns out to be a problem.
- **In-cluster only, with a key:** ClusterIP Service and no Ingress. vLLM's `--api-key` comes
  from a Secret (External Secrets in Azure). A NetworkPolicy admits only Project A's agent pod.
- **Local test on kind with a CPU stand-in:** kind on a Mac can't use the Apple GPU, and the CUDA
  image needs NVIDIA. The kind values swap in vLLM's CPU image and a 0.8B model of the same family,
  which tests the chart's plumbing but says nothing about GPU speed or accuracy.
- **Open for B5:** Project A's chart doesn't pass `AGENT_LLM_API_KEY` to the agent, so it can't
  send vLLM's key yet. Adding it is one optional `secretEnv` line in A's chart (configuration, not
  agent code).
- **Note:** Project A's own kind cluster (`incident-assistant`) won't start: Docker reports its
  container storage as broken. B2 used a separate cluster (`selfhost`). Project A's
  `make kind-up` rebuilds its cluster when it's needed.

## B3 · Autoscaling and observability (2026-10-03)

- **Scale on requests waiting, not CPU or GPU use.** vLLM's CPU use says little about load: the
  engine runs on the GPU, and one CPU core drives it whether the batch is full or not. GPU
  utilization is close to 100% with a single long request too, so it can't tell a busy replica
  from a saturated one. `vllm:num_requests_waiting` counts requests the engine couldn't fit into
  the running batch (batch size or KV cache full), which is exactly when another replica helps and
  when users start waiting. KEDA's Prometheus trigger drives the HPA with
  `sum(avg_over_time(vllm:num_requests_waiting[30s]))`, targeting 4 waiting requests per replica
  on GPU (2 on kind, where `--max-num-seqs=4`). The 30 s average keeps one burst from adding a GPU node.
- **Rejected:** CPU-based HPA (the wrong signal, see above); GPU utilization from DCGM (saturates
  early and needs the DCGM exporter); requests running (it stops at the batch limit, so it can't
  show how far over capacity the replica is); time to first token (the effect, not the cause; it
  lags and mixes in prompt length). TTFT is an alert instead.
- **Min 1 replica, max 2, no scale from zero.** With no pod there is no queue to measure, and
  the agent's request would wait minutes for a GPU node either way. Scale-to-zero stays a
  deliberate action (`kubectl scale --replicas=0`, or a KEDA cron trigger for off-hours later),
  and the GPU pool still scales to zero once no pod needs it. `gpu_max_nodes` is now 2 to match.
- **Scale up fast, scale down slowly.** No stabilization on scale-up, one replica per 30 s. On
  scale-down, a 10-minute window (2 minutes on kind): a GPU replica takes minutes to start, and
  dropping it after a short lull just to add it again costs more than keeping it.
- **Shared weight cache:** replicas on different nodes can't share a ReadWriteOnce Azure disk, so
  the GPU values now use a 100 GiB premium Azure file share (`azurefile-csi-premium`,
  ReadWriteMany). That also removes B2's caveat about zonal disks after scale-to-zero, and by
  Azure's published limits a 100 GiB premium share (~110 MiB/s) reads faster than the 40 GiB
  premium disk it replaces (a P6, 50 MB/s). B4 should check load times and cost. The chart refuses
  `maxReplicas > 1` with a ReadWriteOnce cache on GPU nodes.
- **Monitoring stack on kind:** the community `prometheus` chart (server + kube-state-metrics),
  Grafana, KEDA. Not kube-prometheus-stack: its operator, node exporter and Alertmanager don't fit
  next to the vLLM pod in Docker Desktop's 7.75 GB VM. Even the trimmed stack did not fit at first:
  with the API server, node and cAdvisor scrape jobs on, the node swapped and vLLM's engine hung on
  its first request (a 6-minute timeout, then a restart). Turning those jobs off took Prometheus
  from 351 to 95 MiB.
- **On AKS:** Azure Managed Prometheus and Managed Grafana read the same pod annotations, rule file and
  dashboard JSON, so nothing in-cluster beyond KEDA (an AKS add-on) is needed. KEDA would then need
  workload identity to query the managed Prometheus endpoint (`autoscaling.prometheusAddress`).
- **Alerts** (`deploy/monitoring/alerts/vllm.rules.yaml`, unit tested with promtool):
  p95 TTFT above 2 s for 5 min (it includes queue time, so it is what an agent step feels);
  KV cache above 90% for 5 min; any vLLM container restart; a replica Pending for 10 min (on
  AKS: no spot GPU capacity). Routing them to a pager belongs to Project A's on-call setup.
  The 2 s target is a starting point for an A100; B4's load test should confirm or move it.
- **Dashboard** (`deploy/monitoring/dashboards/vllm-serving.json`) uses Project A's datasource uid,
  so it loads next to A's fleet and system dashboards unchanged. A test checks that every metric
  the dashboard, alerts and KEDA query use exists in vLLM 0.30 or kube-state-metrics.
- **Spike test goes through the Service** (follow-up): an in-cluster TCP proxy, labeled as Project
  A's agent so vLLM's NetworkPolicy admits it, forwards each connection to vLLM's Service, so new
  replicas get traffic. The full scale-up run showed queued requests don't move to a new replica,
  which is why the minimum replica count, not autoscaling, has to cover the normal peak.
- **Prometheus may reach vLLM's port** (a second NetworkPolicy rule) for `/metrics`, which needs
  no key; the API on the same port still requires it.

## B4 · Load testing and cost (2026-10-03)

- **Load from real agent traces, replayed exactly.** `scripts/export_traces.py` rebuilds the 20 B1
  Qwen runs (87 model calls) from Project A's trace tables, using A's own system prompt, incident
  rendering and tool list. Replayed prompts match the recorded token counts exactly (checked on 26
  calls). Each call asks for the recorded output length (`ignore_eos`), so prompt and output sizes
  match production: 8,877 prompt and 338 output tokens per call on average, 4.35 calls per
  incident. Rejected: Locust/k6 with synthetic prompts (wrong lengths and no shared prefixes) and
  vLLM's benchmark scripts (no multi-turn agent conversations).
- **Closed-loop agents, not a request rate.** An agent makes one call at a time, as Project A's
  does, so concurrency = agents working incidents at once. A call over the agent's 300 s limit
  counts as a timeout, and the agent abandons that incident.
- **Call mix must match the traces at every level.** The first version started every agent at an
  incident's first call. At high concurrency each agent finished only one or two calls, so 84% of
  calls at 64 agents were short first calls (3,460 prompt tokens against 8,877), and throughput
  read ~7x too high (210 incidents/hour, against all calls timing out once fixed). Agents now
  start at evenly spread positions among all 87 calls; a test checks the mix at 16 and 64 agents.
- **Latency target: model call p95 <= 60 s, no timeouts**, so a typical incident (4-5 calls)
  finishes in about 5 minutes. The A6 baseline's incidents took 125 s p50 / 287 s p95 end to end.
- **Tuning changes measured:** prefix caching off (it's on by default: does reusing each call's
  growing conversation pay?) and prefill chunks of 8,192 tokens instead of 2,048 (this workload is
  96% prompt tokens). Quantization was already measured in B1 (8-bit kept).
- **A100 numbers are estimated, not measured ($0).** `GpuEstimate` in `src/selfhost/cost.py`:
  prefill at 40% of the A100's 312 TFLOPS, decode reading the 9.5 GB of FP8 weights per step at 70%
  of its 1,935 GB/s, 16 requests decoding together. The 70% is backed by the laptop: 13 tok/s
  single-stream decode x 9.5 GB is ~120 GB/s of the M3 Pro's 150 GB/s. Treat the result as ±2x;
  a one-hour A100 run (~$4 on demand) would replace it with a measurement.
- **Hosted cost** uses the same traces: each call reads the previous call's prompt from Claude's
  prompt cache and writes only the new part (5-minute TTL; calls are seconds apart). Token counts
  are Qwen's; Claude's tokenizer and Opus 5.5's always-on thinking raise them, so the hosted
  figures are lower bounds (the report also shows output x3).
- **Prices** (`data/b4_prices.json`, retrieved 2026-10-03): Azure Retail Prices API for
  `Standard_NC24ads_A100_v4` in westus2 ($3.673/h on demand, $0.679/h spot) and Premium Files
  ($0.16/GiB-month); Claude prices from Anthropic's published rates.
- **Results, decided:** keep prefix caching on (0.4-0.6x throughput without it) and the default
  2,048-token prefill chunks (8,192 changed nothing measurable on vllm-metal). Size self-hosting by
  volume: below ~170 incidents/day (spot) or ~900/day (on demand), the hosted API costs less than
  an always-on A100, before counting operations. B5 makes the recommendation with quality included.

## B5 · Integration with Project A (2026-10-03)

- **Backend switch is configuration only.** The full A6 eval ran on Project A's unchanged `main`
  with `AGENT_PROVIDER=openai_compat`, `AGENT_BASE_URL` and `AGENT_MODEL` pointing at vLLM. On
  Kubernetes, `deploy/helm/values-selfhosted.yaml` (Project A, branch `b5-fallback`) does the same
  through Helm values; removing that file from the command switches back. The chart now passes
  `AGENT_LLM_API_KEY` (vLLM's key, the B2 gap) and can sync optional keys from Key Vault.
- **Fallback is new code in Project A, enabled by configuration** (`AGENT_FALLBACK_PROVIDER` and
  friends). Kubernetes and B3's autoscaling can't help in the minutes a GPU node takes to come
  back, so the agent itself moves a conversation to the hosted API when a call to the
  self-hosted model fails or takes longer than 120 s:
  - It **continues** the conversation instead of restarting the incident: the hosted model gets
    the same prompt and every turn and tool result so far. Restarting would repeat tool calls,
    including approval requests for `drain_node`.
  - After a failure, new incidents skip the self-hosted model for 60 s (cooldown), so they don't
    each wait out the timeout; afterwards it's tried again.
  - Each turn is priced by the model that produced it, so run cost stays right.
  - Rejected: retrying the primary (a dead pod stays dead for minutes); a proxy such as LiteLLM in
    front of both (another service to run, and it can't replay a conversation across APIs that
    keep different transcript formats); failing over the whole run (repeats tool calls).
- **$0 for B5 too (user decision, 2026-10-03):** no paid hosted runs. So the hosted model's
  quality isn't measured; the memo compares it on cost and says so. The fallback test uses local
  Ollama in the hosted API's place: the same code path, a different endpoint. Claude-specific
  replay (tool-use id format, no thinking blocks on replayed turns) is covered by unit tests.
- **Hybrid measured from the self-hosted run, not run live:** without hosted runs, what can be
  measured is whether the self-hosted model's confidence separates its right answers from its
  wrong ones, which decides whether "escalate when unsure" can work at all.
- **Results, decided:** recommend the hosted API at today's volume and keep the self-hosted path
  ready (docs/RECOMMENDATION.md). If self-hosting: self-hosted first, hosted fallback, escalate
  failed runs. Don't escalate on the model's confidence: every completed diagnosis reported
  0.85-0.95, including the wrong actions, so it doesn't separate good answers from bad ones.
