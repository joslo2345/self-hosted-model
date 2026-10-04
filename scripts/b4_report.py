"""B4: cost per incident, break-even volume and the two charts, from the load-test results
(eval/b4/<config>.json), the traces (data/b4_traces.json) and the prices (data/b4_prices.json).

    uv run python scripts/b4_report.py      # or: make cost

Writes eval/b4/cost.md, docs/img/b4-latency.png and docs/img/b4-cost.png.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from selfhost.cost import (
    GpuEstimate,
    break_even_per_day,
    hosted_cost,
    hosted_prices,
    load_prices,
    mean_tokens,
    self_hosted_daily,
    traces_tokens,
)

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval/b4"
IMG = ROOT / "docs/img"
CONFIGS = ["baseline", "no-prefix-cache", "prefill-8k"]
TARGET_CALL_P95_S = 60.0  # latency target: a 4-5 call incident in about 5 minutes

# Reference categorical palette (dataviz skill), fixed order; validated for adjacent pairs.
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MARKERS = ["o", "s", "^", "D", "v"]
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"


def _style(ax: Any) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)


def load_levels() -> dict[str, list[dict[str, Any]]]:
    out = {}
    for c in CONFIGS:
        f = EVAL / f"{c}.json"
        if f.exists():
            out[c] = [lv["summary"] for lv in json.loads(f.read_text())["levels"]]
    return out


def latency_chart(levels: dict[str, list[dict[str, Any]]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor=SURFACE, sharex=True)
    for ax, key, title in (
        (axes[0], "ttft_p95", "Time to first token, p95"),
        (axes[1], "latency_p95", "Model call, p95"),
    ):
        _style(ax)
        for i, (config, rows) in enumerate(levels.items()):
            xs = [r["concurrency"] for r in rows if r[key] is not None]
            ys = [r[key] for r in rows if r[key] is not None]
            ax.plot(xs, ys, color=COLORS[i], marker=MARKERS[i], markersize=6, linewidth=2,
                    label=config)  # fmt: skip
        ax.axhline(300, color=MUTED, linestyle="--", linewidth=1)
        ax.annotate("agent's 300 s limit per call", (1, 300), xytext=(0, 4),
                    textcoords="offset points", fontsize=8, color=MUTED)  # fmt: skip
        if key == "latency_p95":
            ax.axhline(TARGET_CALL_P95_S, color=MUTED, linestyle=":", linewidth=1)
            ax.annotate("target 60 s", (1, TARGET_CALL_P95_S), xytext=(0, 4),
                        textcoords="offset points", fontsize=8, color=MUTED)  # fmt: skip
        ax.set_xscale("log", base=2)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.set_xlabel("Concurrent agents", color=MUTED, fontsize=9)
        ax.set_ylabel("Seconds", color=MUTED, fontsize=9)
        ax.set_title(title, color=INK, fontsize=11, loc="left")
        ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="center left")
    fig.suptitle("Qwen3.5-9B on an M3 Pro, replaying Project A's agent calls "
                 "(completed calls only)", color=MUTED, fontsize=9, x=0.01, ha="left")  # fmt: skip
    fig.tight_layout()
    fig.savefig(IMG / "b4-latency.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def cost_chart(series: list[tuple[str, list[float], list[float]]]) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor=SURFACE)
    _style(ax)
    for i, (label, xs, ys) in enumerate(series):
        ax.plot(xs, ys, color=COLORS[i], linewidth=2, marker=MARKERS[i], markevery=6,
                markersize=6, label=label)  # fmt: skip
        ax.annotate(label, (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
                    fontsize=8, color=INK, va="center")  # fmt: skip
    ax.set_xscale("log")
    ax.set_yscale("log")
    money = FuncFormatter(lambda v, _: f"${v:,.0f}" if v >= 1 else f"${v:g}")
    ax.yaxis.set_major_formatter(money)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_xlabel("Incidents per day", color=MUTED, fontsize=9)
    ax.set_ylabel("Cost per 1,000 incidents", color=MUTED, fontsize=9)
    ax.set_title("Self-hosted A100 (estimated throughput) vs hosted Claude", color=INK,
                 fontsize=11, loc="left")  # fmt: skip
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="lower left")
    fig.tight_layout()
    fig.subplots_adjust(right=0.8)
    fig.savefig(IMG / "b4-cost.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    prices = load_prices()
    hosted = hosted_prices(prices)
    tokens = mean_tokens(traces_tokens())
    storage = prices["storage"]["weight_cache_gib"] * prices["storage"]["per_gib_month"]
    gpu = {"A100 on demand": prices["gpu"]["on_demand_per_hour"],
           "A100 spot": prices["gpu"]["spot_per_hour"]}  # fmt: skip
    est = GpuEstimate()
    capacity = est.incidents_per_hour(tokens.uncached + tokens.cache_write, tokens.output)
    capacity_nocache = est.incidents_per_hour(tokens.input_total, tokens.output)

    levels = load_levels()
    if levels:
        latency_chart(levels)

    per_incident = {m: hosted_cost(tokens, p) for m, p in hosted.items()}
    per_incident_think = {m: hosted_cost(tokens, p, output_factor=3) for m, p in hosted.items()}
    volumes = [10 * 10 ** (k / 20) for k in range(81)]  # 10 to 100,000 incidents/day
    series = []
    for label, hourly in gpu.items():
        ys = [self_hosted_daily(v, capacity, hourly, storage) / v * 1000 for v in volumes]
        series.append((f"{label} (self-hosted)", volumes, ys))
    for m, c in per_incident.items():
        series.append((m, volumes, [c * 1000] * len(volumes)))
    cost_chart(series)

    lines = [
        "# B4 cost model",
        "",
        f"Tokens per incident (mean of the 20 B1 runs): {tokens.input_total:,} prompt "
        f"({tokens.uncached:,} first call, {tokens.cache_write:,} new on later calls, "
        f"{tokens.cache_read:,} repeated prefix), {tokens.output:,} output.",
        "",
        "## Hosted (per incident, prompt caching on)",
        "",
        "| Model | Per incident | Per 1,000 | If thinking triples output |",
        "| --- | --- | --- | --- |",
    ]
    for m in hosted:
        lines.append(f"| {m} | ${per_incident[m]:.4f} | ${per_incident[m] * 1000:,.0f} "
                     f"| ${per_incident_think[m] * 1000:,.0f} |")  # fmt: skip
    lines += [
        "",
        "## Self-hosted A100 (estimated)",
        "",
        f"Estimated capacity of one A100: {capacity:,.0f} incidents/hour with prefix caching, "
        f"{capacity_nocache:,.0f} without (prefill {est.prefill_tps:,.0f} tok/s at "
        f"{est.mfu:.0%} MFU; decode step {est.step_s * 1000:.1f} ms at {est.bandwidth_eff:.0%} of "
        f"bandwidth; batch {est.batch}). Weight cache: ${storage:.0f}/month.",
        "",
        "| GPU | $/hour | Cost/day, 1 replica always on | Per 1,000 at full use "
        "| Break-even vs Opus 5.5 | vs Sonnet 5.5 | vs Haiku 4.5 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, hourly in gpu.items():
        daily = self_hosted_daily(0, capacity, hourly, storage)
        full = hourly / capacity * 1000
        be = [break_even_per_day(per_incident[m], capacity, hourly, storage) for m in hosted]
        cells = " | ".join("-" if v is None else f"{v:,.0f}/day" for v in be)
        lines.append(f"| {label} | ${hourly:.3f} | ${daily:,.2f} | ${full:.2f} | {cells} |")
    lines += [
        "",
        "## Laptop (measured, for scale)",
        "",
    ]
    lines += [
        f"Latency target: model call p95 <= {TARGET_CALL_P95_S:.0f} s, no timeouts.",
        "",
        "| Config | Best incidents/hour within target (agents) | Peak incidents/hour (agents) |",
        "| --- | --- | --- |",
    ]
    for config, rows in levels.items():
        ok = [
            r for r in rows if r["timeouts"] == 0 and (r["latency_p95"] or 1e9) <= TARGET_CALL_P95_S
        ]
        best = max(ok, key=lambda r: r["incidents_per_hour"], default=None)
        peak = max(rows, key=lambda r: r["incidents_per_hour"])
        within = (
            "none" if best is None else f"{best['incidents_per_hour']:.0f} ({best['concurrency']})"
        )
        lines.append(f"| {config} | {within} | {peak['incidents_per_hour']:.0f} "
                     f"({peak['concurrency']}) |")  # fmt: skip
    (EVAL / "cost.md").write_text("\n".join(lines) + "\n")
    print((EVAL / "cost.md").read_text())


if __name__ == "__main__":
    main()
