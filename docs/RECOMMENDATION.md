# Recommendation: hosted or self-hosted model for the incident assistant

*October 2026. For the team running the GPU-fleet incident assistant (Project A). Evidence: this
repo's B1–B5 results; numbers in [RESULTS.md](RESULTS.md), reasoning in [DECISIONS.md](DECISIONS.md).*

## Summary

**Use a hosted model today; keep the self-hosted path ready.** At the volume a GPU fleet produces
(tens of incidents a day), a hosted API costs about **$0.10 per incident**, while an always-on A100
costs **$0.84–$4.43 per incident** at 20 a day, before anyone's time to run it. Self-hosting pays
off above **~170 incidents/day on a spot GPU** (with the hosted API as fallback) or **~900/day on
demand**, or sooner if incident data must not leave your cloud tenant. The switch is now a Helm
values file, with automatic fallback to the hosted API, so it can be made when one of those
becomes true, not before.

## What we measured

| | Self-hosted Qwen3.5-9B (8-bit, vLLM) | Hosted Claude Opus 5.5 |
| --- | --- | --- |
| Root cause correct (25 test incidents) | 23/25 (92%) | not measured* |
| Right action | 20/25 (80%) | not measured* |
| Unsafe action on false alarms | 0/3 | not measured* |
| Citations supported by the evidence | 97% | not measured* |
| Cost per incident at 20/day | $4.43 (on demand) / $0.84 (spot) | $0.10 |
| Cost per incident at 1,000/day | $0.09 / $0.02 | $0.10 |
| Data leaves your tenant | no | yes (to Anthropic) |

\*The project ran at $0 by choice, so no paid API runs were made. One full eval run on the
hosted model costs about $3–4 and should be done before committing either way.

The self-hosted model is good enough to run the assistant: it beat the earlier local baseline on
root causes (23 vs 22 of 25) and citations (97% vs 88%), made no unsafe recommendations, and had
no tool errors. Its weak spot is the action: three times it named the wrong one with high
confidence, once leaving a faulty node in service. Keep human approval on hardware actions
(already the default) if you self-host.

## Recommendation by situation

| Your situation | Choose | Why |
| --- | --- | --- |
| Under ~100 incidents/day, no data restrictions | **Hosted** | At 20/day, 8–44x cheaper per incident than a spot or on-demand GPU; no GPU to operate |
| Incident data (telemetry, logs, node names) must stay in your tenant | **Self-hosted**, with on-demand GPU | The only option that keeps data in your AKS cluster; costs ~$89/day per GPU |
| Over ~170/day and fine with occasional slower answers | **Self-hosted on spot + hosted fallback** | ~$17/day for the GPU; the fallback covers spot evictions |
| Over ~900/day | **Self-hosted, on demand** | One A100 serves an estimated ~35,000 incidents/day; $0.02–0.09 per incident |

If you self-host, run it as tested: **self-hosted first, hosted API as fallback**. The fallback
was tested by killing the model mid-investigation: the conversation moved to the backup model
without repeating any tool calls, and all 4 incidents finished correctly. Also send **failed runs**
to the hosted model (8% of incidents in our test, about $0.01 per incident on average). The
model's own confidence didn't help pick out which answers to double-check.

## Data residency

Self-hosted keeps prompts, telemetry and logs inside your AKS cluster: the model endpoint has no
ingress, needs an API key, and accepts traffic only from the agent pod. With the hosted API,
incident context goes to Anthropic for each call. If that's acceptable under your policies, it
isn't a reason to self-host. If it isn't, self-hosting is the answer at any volume, and the
fallback must be off or pointed at another in-tenant endpoint.

## Operating burden of self-hosting

- A GPU node pool (Terraform written and validated), the vLLM chart, the NVIDIA device plugin,
  and the weight cache (a $16/month file share).
- Autoscaling on queue depth reacts in ~40 s, but a new GPU node takes an estimated 5–10 minutes,
  so a sudden spike queues: in the spike test, wait times reached 200 s, close to the agent's 300 s
  limit. Size the minimum replicas for your normal peak.
- Four alerts and a serving dashboard are in place (slow responses, cache pressure, restarts,
  stuck replicas); someone has to answer them.
- Model upgrades need a re-run of the eval (about an hour, automated) before rollout.

## Risks and open items

- **Hosted quality not measured.** Run the A6 eval on Opus 5.5 (~$3–4) and on Sonnet 5.5
  (~$2) before deciding. If a cheaper hosted model matches, the hosted case gets stronger.
- **A100 throughput is an estimate** (±2x). A one-hour A100 test (~$4) would replace it. The
  break-even volumes move less than that: the GPU's daily cost doesn't change.
- **Spot capacity** isn't guaranteed; without the fallback, a spot eviction means minutes of
  queued incidents.
- **The 9B model fails on some long investigations** (2 of 25 runs). The fallback and the
  failed-run escalation cover this; the memo's costs include it.
