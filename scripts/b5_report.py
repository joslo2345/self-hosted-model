"""B5: side-by-side eval results, the hybrid routing analysis and cost per incident by volume.

    uv run python scripts/b5_report.py      # or: make b5-report

Inputs: Project A's A6 test report on its original local model (the baseline), this repo's B5 run
of the same 25 incidents on the self-hosted model (eval/b5/selfhosted.json), and B4's cost model.
The hosted model's quality isn't measured (no paid API runs; docs/DECISIONS.md), so its column
has cost only, and the hybrid's quality is a range.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from selfhost.cost import (
    GpuEstimate,
    hosted_cost,
    hosted_prices,
    load_prices,
    mean_tokens,
    self_hosted_daily,
    traces_tokens,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECT_A = ROOT.parent.parent / "project-a/incident-assistant"
BASELINE = PROJECT_A / "eval/reports/a6/test/final-r3.json"
SELFHOSTED = ROOT / "eval/b5/selfhosted.judged.json"
THRESHOLDS = (0.6, 0.7, 0.8, 0.9)
VOLUMES = (20, 100, 1000)  # incidents per day


def rate(summary: dict[str, Any], key: str) -> str:
    v = summary.get(key)
    if isinstance(v, dict):
        return f"{v['n']}/{v['of']} ({v['rate']:.0%})"
    return "-" if v is None else f"{v:.0%}"


def escalate(case: dict[str, Any], threshold: float) -> bool:
    """Hybrid rule: send an incident to the hosted model when the self-hosted run failed or its
    diagnosis is less confident than the threshold."""
    return case["status"] != "succeeded" or (case.get("confidence") or 0) < threshold


def main() -> None:
    base = json.loads(BASELINE.read_text())
    sh_path = SELFHOSTED if SELFHOSTED.exists() else ROOT / "eval/b5/selfhosted.json"
    sh = json.loads(sh_path.read_text())
    prices = load_prices()
    tokens = mean_tokens(traces_tokens())
    opus = hosted_cost(tokens, hosted_prices(prices)["claude-opus-5-5"])
    storage = prices["storage"]["weight_cache_gib"] * prices["storage"]["per_gib_month"]
    capacity = GpuEstimate().incidents_per_hour(tokens.uncached + tokens.cache_write, tokens.output)

    def per_incident(volume: int, hourly: float) -> float:
        return self_hosted_daily(volume, capacity, hourly, storage) / volume

    rows = [
        ("Root cause correct", "root_cause_accuracy"),
        ("Action correct", "action_correct"),
        ("Unsafe action (decoys)", "unsafe_action_rate"),
        ("Missed action", "missed_action_rate"),
        ("Runbook cited", "runbook_cited"),
        ("Citations supported", "citation_support"),
    ]
    b, s = base["summary"], sh["summary"]
    lines = [
        "# B5: Project A on each backend",
        "",
        f"A6 test set, {s['cases']} incidents ({len(sh['meta']['composition']['by_type'])} failure "
        f"types, {sh['meta']['composition']['decoys']} decoys). Baseline: "
        f"{base['meta']['model']} on Ollama ({base['meta']['label']}). Self-hosted: "
        f"{sh['meta']['model']} on vLLM, switched by configuration only.",
        "",
        "| Metric | Baseline (A6, qwen3 30B-A3B) | Self-hosted (Qwen3.5-9B) | Hosted (Opus 5.5) |",
        "| --- | --- | --- | --- |",
    ]
    for label, key in rows:
        lines.append(f"| {label} | {rate(b, key)} | {rate(s, key)} | not measured |")
    lines += [
        f"| Latency p50 / p95 | {b['latency_s_p50']:.0f} / {b['latency_s_p95']:.0f} s "
        f"| {s['latency_s_p50']:.0f} / {s['latency_s_p95']:.0f} s | not measured |",
        f"| Tokens per incident | {b['tokens_per_case']:,} | {s['tokens_per_case']:,} | |",
        f"| Tool errors | {b['tool_errors']} | {s['tool_errors']} | |",
        "",
        "## Cost per incident by daily volume",
        "",
        "| Incidents/day | A100 on demand | A100 spot | Opus 5.5 (B4 tokens, caching) |",
        "| --- | --- | --- | --- |",
    ]
    for v in VOLUMES:
        lines.append(
            f"| {v:,} | ${per_incident(v, prices['gpu']['on_demand_per_hour']):.3f} "
            f"| ${per_incident(v, prices['gpu']['spot_per_hour']):.3f} | ${opus:.3f} |"
        )

    cases = sh["cases"]
    wrong = [c for c in cases if not c.get("root_cause_correct")]
    lines += [
        "",
        "## Hybrid: escalate low-confidence incidents to the hosted model",
        "",
        f"Self-hosted got {len(cases) - len(wrong)}/{len(cases)} root causes right. Rule: escalate "
        "when the run failed or the diagnosis confidence is below the threshold. Hybrid accuracy "
        "is a range: low if the hosted model does no better than the self-hosted one on the "
        "escalated incidents, high if it gets all of them right.",
        "",
        "| Threshold | Escalated | Wrong answers caught | Right answers escalated "
        "| Hybrid root cause (range) | Hosted cost per incident |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for t in THRESHOLDS:
        esc = [c for c in cases if escalate(c, t)]
        caught = [c for c in esc if not c.get("root_cause_correct")]
        kept_right = sum(1 for c in cases if not escalate(c, t) and c.get("root_cause_correct"))
        low = kept_right + sum(1 for c in esc if c.get("root_cause_correct"))
        high = kept_right + len(esc)
        lines.append(
            f"| {t:.1f} | {len(esc)}/{len(cases)} | {len(caught)}/{len(wrong)} "
            f"| {len(esc) - len(caught)} | {low} to {high}/{len(cases)} "
            f"| ${opus * len(esc) / len(cases):.3f} |"
        )
    conf = sorted(
        (round(c.get("confidence") or 0, 2), bool(c.get("root_cause_correct"))) for c in cases
    )
    lines += ["", "Confidence of each diagnosis (right / wrong root cause):", ""]
    lines.append(
        "- right: "
        + ", ".join(f"{c:.2f}" for c, ok in conf if ok)
        + "\n- wrong: "
        + (", ".join(f"{c:.2f}" for c, ok in conf if not ok) or "none")
    )
    out = ROOT / "eval/b5/summary.md"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
