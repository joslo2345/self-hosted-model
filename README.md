# Self-hosted model deployment

Should the GPU-fleet incident assistant ([Project A](https://github.com/joslo2345/incident-assistant))
run on its own open model instead of a hosted API? This repo deploys an open model behind an
OpenAI-compatible endpoint, measures it, plugs it into Project A through config only, and ends
with a data-backed recommendation.

Constraint: **$0 spend.** Everything runs on one laptop (Apple M3 Pro, 36 GB). Cloud pieces are
written and validated but never applied; cloud costs are calculated from published prices.

| Package | Focus | Status |
| --- | --- | --- |
| B1 | Model selection and local vLLM | done: Qwen3.5-9B 8-bit, thinking off |
| B2 | Kubernetes deployment | done: AKS GPU pool (validated) + Helm chart tested on kind |
| B3 | Autoscaling and observability | done: KEDA on queue depth (40 s to scale decision), dashboard, alerts |
| B4 | Load testing and cost | done: replayed agent traces, cost per 1,000 incidents, break-even |
| B5 | Integration with Project A and recommendation | done: config-only switch, fallback tested, [recommendation](docs/RECOMMENDATION.md) |

Design choices: [docs/DECISIONS.md](docs/DECISIONS.md). Numbers: [docs/RESULTS.md](docs/RESULTS.md).

## Checks

There is no hosted CI (to keep GitHub Actions minutes at zero). Run before every push:

```bash
make check   # ruff, mypy --strict, pytest
```

## Serve a model locally (B1)

```bash
make engine                     # once: pinned vLLM + vllm-metal in .venv-engine
make serve                      # chosen model (Qwen3.5-9B, thinking off) on 127.0.0.1:8100
make serve CANDIDATE=granite THINK=true   # other shortlisted models, thinking on
make smoke                      # chat, streaming and tool-call checks against the endpoint
```

Why Qwen3.5-9B with thinking off: [docs/DECISIONS.md](docs/DECISIONS.md). To rerun the 20-incident
comparison against Project A's eval harness (its stack must be up): `scripts/compare_b1.sh`.

## Kubernetes (B2)

The GPU target is a scale-to-zero spot node pool on Project A's AKS cluster (`infra/azure`, never
applied: $0). The same Helm chart runs locally on kind with vLLM's CPU image and a small stand-in model.

```bash
make deploy-check     # terraform fmt + validate, helm lint (no Azure access needed)
make kind-up          # local kind cluster with Calico (NetworkPolicy enforced)
kubectl create namespace selfhost && kubectl create namespace ia
kubectl -n selfhost create secret generic vllm-api-key --from-literal=api-key="$(openssl rand -hex 24)"
helm install vllm deploy/helm/vllm -n selfhost -f deploy/helm/vllm/values-kind.yaml
make kind-check       # auth, NetworkPolicy, streaming
make cold-start       # pod-to-Ready time: empty cache, cached, cached + offline
```

On AKS: `terraform apply` in `infra/azure`, then install the NVIDIA device plugin
(`deploy/gpu/nvidia-device-plugin-values.yaml`), and then the chart with its default values.

## Autoscaling and observability (B3)

KEDA scales vLLM on requests waiting in its queue (not CPU), read from Prometheus. The serving
dashboard and alert rules are files in `deploy/monitoring`; why queue depth: [docs/DECISIONS.md](docs/DECISIONS.md).

```bash
make monitoring-up    # Prometheus + alert rules, Grafana + serving dashboard, KEDA (on kind)
helm upgrade vllm deploy/helm/vllm -n selfhost -f deploy/helm/vllm/values-kind.yaml
make rules-check      # promtool: alert rules and their unit tests (Docker)
make grafana          # dashboard on http://127.0.0.1:3100 ("Self-hosted model" folder)
make prometheus       # Prometheus on http://127.0.0.1:9091 (alerts tab)
make spike            # spike test: TTFT, queue, replicas and alerts over time -> eval/b3/
```

Port-forwards listen on 127.0.0.1 only. On kind, Docker Desktop's VM fits one CPU replica, so the
second replica KEDA asks for stays Pending, which is what a pod waiting for a GPU node looks like.

## Load test and cost (B4)

The load test replays Project A's real agent conversations (the 20 B1 runs, exported from A's trace
tables) at increasing concurrency against the local model, then a cost model compares an A100 on
Azure with hosted Claude models. Results: [docs/RESULTS.md](docs/RESULTS.md).

```bash
make bench    # fresh vLLM per config: baseline (1-64 agents), no prefix cache, 8k prefill chunks (~1 h)
make cost     # cost per incident, break-even volume, charts -> eval/b4/cost.md, docs/img/
```

To re-export the traces (needs Project A's database running), see `scripts/export_traces.py`.

## Integration with Project A (B5)

Project A runs on the self-hosted model through configuration only: environment variables locally,
`deploy/helm/values-selfhosted.yaml` (in Project A) on Kubernetes, with the hosted API as automatic
fallback. Recommendation memo: [docs/RECOMMENDATION.md](docs/RECOMMENDATION.md).

```bash
make b5-eval       # Project A's full A6 eval on the self-hosted model (~1 h; Project A stack up)
make b5-fallback   # kill vLLM mid-run; the agent must finish on the fallback model
make b5-report     # side-by-side results, hybrid analysis, cost by volume -> eval/b5/summary.md
```
