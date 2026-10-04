# Self-hosted model deployment

Should the GPU-fleet incident assistant ([Project A](https://github.com/joslo2345/incident-assistant))
run on its own open model instead of a hosted API? This repo deploys an open model behind an
OpenAI-compatible endpoint, measures it, plugs it into Project A through config only, and ends
with a data-backed recommendation.

Constraint: **$0 spend.** Everything runs on one laptop (Apple M3 Pro, 36 GB). Cloud pieces are
written and validated but never applied; cloud costs are calculated from published prices.

| Package | Focus | Status |
| --- | --- | --- |
| B1 | Model selection and local vLLM | in progress |
| B2 | Kubernetes deployment | |
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
