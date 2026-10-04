# B5: Project A on each backend

A6 test set, 25 incidents (7 failure types, 3 decoys). Baseline: qwen3-agent on Ollama (final-r3). Self-hosted: qwen3.5-9b on vLLM, switched by configuration only.

| Metric | Baseline (A6, qwen3 30B-A3B) | Self-hosted (Qwen3.5-9B) | Hosted (Opus 5.5) |
| --- | --- | --- | --- |
| Root cause correct | 22/25 (88%) | 23/25 (92%) | not measured |
| Action correct | 23/25 (92%) | 20/25 (80%) | not measured |
| Unsafe action (decoys) | 0/3 (0%) | 0/3 (0%) | not measured |
| Missed action | 1/22 (4%) | 1/22 (4%) | not measured |
| Runbook cited | 19/25 (76%) | 20/25 (80%) | not measured |
| Citations supported | 88% | 97% | not measured |
| Latency p50 / p95 | 125 / 287 s | 158 / 390 s | not measured |
| Tokens per incident | 27,458 | 47,547 | |
| Tool errors | 18 | 0 | |

## Cost per incident by daily volume

| Incidents/day | A100 on demand | A100 spot | Opus 5.5 (B4 tokens, caching) |
| --- | --- | --- | --- |
| 20 | $4.434 | $0.841 | $0.097 |
| 100 | $0.887 | $0.168 | $0.097 |
| 1,000 | $0.089 | $0.017 | $0.097 |

## Hybrid: escalate low-confidence incidents to the hosted model

Self-hosted got 23/25 root causes right. Rule: escalate when the run failed or the diagnosis confidence is below the threshold. Hybrid accuracy is a range: low if the hosted model does no better than the self-hosted one on the escalated incidents, high if it gets all of them right.

| Threshold | Escalated | Wrong answers caught | Right answers escalated | Hybrid root cause (range) | Hosted cost per incident |
| --- | --- | --- | --- | --- | --- |
| 0.6 | 2/25 | 2/2 | 0 | 23 to 25/25 | $0.008 |
| 0.7 | 2/25 | 2/2 | 0 | 23 to 25/25 | $0.008 |
| 0.8 | 2/25 | 2/2 | 0 | 23 to 25/25 | $0.008 |
| 0.9 | 3/25 | 2/2 | 1 | 23 to 25/25 | $0.012 |

Confidence of each diagnosis (right / wrong root cause):

- right: 0.85, 0.90, 0.90, 0.90, 0.90, 0.90, 0.90, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95
- wrong: 0.00, 0.00
