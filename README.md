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
| B2 | Kubernetes deployment | in progress |
| B3 | Autoscaling and observability | |
| B4 | Load testing and cost | |
| B5 | Integration with Project A and recommendation | |

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
