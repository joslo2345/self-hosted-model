"""Spike test (B3): send requests at a fixed rate per phase, and record over time what users saw
(time to first token, errors) next to what the system did (requests waiting, KEDA's desired
replicas, pods created and ready, alerts firing).

Arrivals are open-loop and evenly spaced: a slow server doesn't slow the senders down, as with real
users. The cluster is sampled with kubectl, vLLM's /metrics and Prometheus's alerts API.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx2 as httpx
from openai import AsyncOpenAI

PROMPT = (
    "Incident INC-2025001: GPU 3 on node gpu-h100-07 crossed 92 C, fans are at 100% and ECC errors "
    "are rising. In three short steps, what should on-call check first?"
)


@dataclass(frozen=True)
class Phase:
    seconds: float
    rps: float


@dataclass
class RequestResult:
    index: int
    sent: float  # seconds since test start
    ttft: float | None = None
    total: float | None = None
    error: str | None = None


@dataclass
class Sample:
    t: float  # seconds since test start
    waiting: float | None = None
    running: float | None = None
    desired: int | None = None  # HPA (KEDA) desired replicas
    pods: int = 0  # vLLM pods that exist (any phase)
    pending: int = 0
    ready: int = 0
    alerts: list[str] = field(default_factory=list)  # firing alert names


def parse_phases(spec: str) -> list[Phase]:
    """'60:0.05,180:0.4' -> 60 s at 0.05 requests/s, then 180 s at 0.4 requests/s."""
    phases = []
    for part in spec.split(","):
        seconds, rps = part.split(":")
        phase = Phase(float(seconds), float(rps))
        if phase.seconds <= 0 or phase.rps < 0:
            raise ValueError(f"bad phase {part!r}: seconds must be > 0 and rps >= 0")
        phases.append(phase)
    return phases


def arrival_times(phases: Sequence[Phase]) -> list[float]:
    """Evenly spaced send times; each phase starts with a request (if its rate is above zero)."""
    times: list[float] = []
    start = 0.0
    for p in phases:
        if p.rps > 0:
            n = math.floor(p.seconds * p.rps + 1e-9)
            times.extend(start + i / p.rps for i in range(n))
        start += p.seconds
    return times


def percentile(values: Sequence[float], q: float) -> float | None:
    """Nearest-rank percentile (q in 0..100); None for no values."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(ordered)))
    return ordered[rank - 1]


def parse_prometheus_text(text: str, name: str) -> float | None:
    """Sum of all samples of one metric in Prometheus text format (None if absent)."""
    total, found = 0.0, False
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        metric = line.split("{", 1)[0].split(" ", 1)[0]
        if metric == name:
            total += float(line.rsplit(" ", 1)[1])
            found = True
    return total if found else None


def parse_cluster(doc: dict[str, Any], deployment: str) -> tuple[int | None, int, int, int]:
    """From `kubectl get hpa,pods -o json`: desired replicas, pods, pending pods, ready pods."""
    desired: int | None = None
    pods = pending = ready = 0
    for item in doc.get("items", []):
        kind = item.get("kind")
        if kind == "HorizontalPodAutoscaler":
            if item["spec"]["scaleTargetRef"]["name"] == deployment:
                desired = item.get("status", {}).get("desiredReplicas")
        elif kind == "Pod":
            labels = item["metadata"].get("labels", {})
            if labels.get("app.kubernetes.io/instance") != deployment:
                continue
            if item["metadata"].get("deletionTimestamp"):
                continue
            pods += 1
            status = item.get("status", {})
            if status.get("phase") == "Pending":
                pending += 1
            conditions = status.get("conditions", [])
            if any(c["type"] == "Ready" and c["status"] == "True" for c in conditions):
                ready += 1
    return desired, pods, pending, ready


# ---- summary -------------------------------------------------------------------------------


def _first(samples: Sequence[Sample], after: float, cond: Any) -> float | None:
    return next((s.t for s in samples if s.t >= after and cond(s)), None)


def events(
    samples: Sequence[Sample], phases: Sequence[Phase], waiting_target: float
) -> dict[str, float | None]:
    """Times (s since start) of the scale-up milestones, measured from the spike phase's start.

    The spike is the phase with the highest rate. Missing milestones are None.
    """
    spike_index = max(range(len(phases)), key=lambda i: phases[i].rps)
    spike_start = sum(p.seconds for p in phases[:spike_index])
    base = samples[0] if samples else Sample(0)
    base_pods, base_ready = base.pods, base.ready
    base_desired = base.desired or 0
    out: dict[str, float | None] = {"spike_start": spike_start}
    out["queue_over_target"] = _first(
        samples, spike_start, lambda s: (s.waiting or 0) > waiting_target
    )
    out["keda_scale_decision"] = _first(
        samples, spike_start, lambda s: (s.desired or 0) > base_desired
    )
    out["new_pod_created"] = _first(samples, spike_start, lambda s: s.pods > base_pods)
    out["new_pod_ready"] = _first(samples, spike_start, lambda s: s.ready > base_ready)
    up = out["keda_scale_decision"]
    out["scaled_back_down"] = (
        None if up is None else _first(samples, up, lambda s: (s.desired or 0) <= base_desired)
    )
    for s in samples:
        for name in s.alerts:
            out.setdefault(f"alert:{name}", s.t)
    return out


def windows(
    requests: Sequence[RequestResult], samples: Sequence[Sample], width: float
) -> list[dict[str, Any]]:
    """Per time window: requests sent, errors, TTFT p50/p95 of requests sent in it, max waiting,
    and the replica counts at its end."""
    end = max([r.sent for r in requests] + [s.t for s in samples] + [0.0])
    rows = []
    for k in range(math.floor(end / width) + 1):
        lo, hi = k * width, (k + 1) * width
        sent = [r for r in requests if lo <= r.sent < hi]
        ttfts = [r.ttft for r in sent if r.ttft is not None]
        in_window = [s for s in samples if lo <= s.t < hi]
        last = in_window[-1] if in_window else None
        rows.append(
            {
                "start": lo,
                "sent": len(sent),
                "errors": sum(1 for r in sent if r.error),
                "ttft_p50": percentile(ttfts, 50),
                "ttft_p95": percentile(ttfts, 95),
                "max_waiting": max((s.waiting or 0 for s in in_window), default=None),
                "desired": last.desired if last else None,
                "ready": last.ready if last else None,
                "pending": last.pending if last else None,
            }
        )
    return rows


def _fmt(v: float | None, unit: str = "s") -> str:
    if v is None:
        return "-"
    return f"{v:.0f}{unit}" if v >= 10 else f"{v:.1f}{unit}"


def render_markdown(
    phases: Sequence[Phase],
    requests: Sequence[RequestResult],
    samples: Sequence[Sample],
    waiting_target: float,
    window: float = 30.0,
) -> str:
    ev = events(samples, phases, waiting_target)
    start = ev["spike_start"] or 0.0

    def since_spike(key: str) -> str:
        t = ev.get(key)
        return "not reached" if t is None else f"+{t - start:.0f} s"

    ttfts = [r.ttft for r in requests if r.ttft is not None]
    lines = [
        "# Spike test",
        "",
        "Phases: " + ", ".join(f"{p.seconds:.0f} s at {p.rps:g} req/s" for p in phases),
        f"Requests: {len(requests)} sent, {sum(1 for r in requests if r.error)} failed. "
        f"TTFT p50 {_fmt(percentile(ttfts, 50))}, p95 {_fmt(percentile(ttfts, 95))}, "
        f"max {_fmt(max(ttfts, default=None))}.",
        "",
        "| Milestone (from spike start) | Time |",
        "| --- | --- |",
        f"| Requests waiting above target ({waiting_target:g}) "
        f"| {since_spike('queue_over_target')} |",
        f"| KEDA asks for another replica | {since_spike('keda_scale_decision')} |",
        f"| New pod created | {since_spike('new_pod_created')} |",
        f"| New pod Ready | {since_spike('new_pod_ready')} |",
        f"| Scaled back down | {since_spike('scaled_back_down')} |",
    ]
    for key in sorted(k for k in ev if k.startswith("alert:")):
        lines.append(f"| Alert {key[6:]} firing | {since_spike(key)} |")
    lines += [
        "",
        f"Per {window:.0f} s window (TTFT of requests sent in the window):",
        "",
        "| t (s) | sent | errors | TTFT p50 | TTFT p95 | max waiting | desired | ready | pending |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for w in windows(requests, samples, window):
        lines.append(
            f"| {w['start']:.0f} | {w['sent']} | {w['errors']} | {_fmt(w['ttft_p50'])} | "
            f"{_fmt(w['ttft_p95'])} | {_fmt(w['max_waiting'], '')} | {w['desired'] or '-'} | "
            f"{'-' if w['ready'] is None else w['ready']} | "
            f"{'-' if w['pending'] is None else w['pending']} |"
        )
    return "\n".join(lines) + "\n"


# ---- running the test ----------------------------------------------------------------------


@dataclass(frozen=True)
class SpikeConfig:
    base_url: str
    model: str
    api_key: str
    phases: list[Phase]
    max_tokens: int = 64
    namespace: str = "selfhost"
    deployment: str = "vllm"
    prometheus_url: str | None = None
    sample_every: float = 2.0
    observe_after: float = 180.0  # keep sampling after the last request finishes (scale-down)
    request_timeout: float = 900.0


async def _send(client: AsyncOpenAI, cfg: SpikeConfig, result: RequestResult, t0: float) -> None:
    try:
        stream = await client.chat.completions.create(
            model=cfg.model,
            messages=[{"role": "user", "content": PROMPT}],
            max_tokens=cfg.max_tokens,
            stream=True,
            extra_body={"ignore_eos": True},  # same length every time: a steady load per request
        )
        async for chunk in stream:
            if result.ttft is None and chunk.choices and chunk.choices[0].delta.content:
                result.ttft = time.monotonic() - t0 - result.sent
        result.total = time.monotonic() - t0 - result.sent
    except Exception as exc:  # any client or server error is a failed request
        result.error = f"{type(exc).__name__}: {exc}"[:200]


async def _kubectl_json(cfg: SpikeConfig) -> dict[str, Any]:
    proc = await asyncio.create_subprocess_exec(
        "kubectl", "-n", cfg.namespace, "get", "hpa,pods", "-o", "json",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )  # fmt: skip
    out, _ = await proc.communicate()
    doc: dict[str, Any] = json.loads(out) if proc.returncode == 0 and out else {}
    return doc


async def _sample(http: httpx.AsyncClient, cfg: SpikeConfig, t: float) -> Sample:
    s = Sample(t)
    root = cfg.base_url.rstrip("/").removesuffix("/v1")
    try:
        text = (await http.get(f"{root}/metrics", timeout=5)).text
        s.waiting = parse_prometheus_text(text, "vllm:num_requests_waiting")
        s.running = parse_prometheus_text(text, "vllm:num_requests_running")
    except httpx.HTTPError:
        pass  # a busy or restarting pod: leave the queue unknown for this sample
    s.desired, s.pods, s.pending, s.ready = parse_cluster(await _kubectl_json(cfg), cfg.deployment)
    if cfg.prometheus_url:
        try:
            alerts = (await http.get(f"{cfg.prometheus_url}/api/v1/alerts", timeout=5)).json()
            firing = {
                a["labels"]["alertname"] for a in alerts["data"]["alerts"] if a["state"] == "firing"
            }
            s.alerts = sorted(firing)
        except (httpx.HTTPError, ValueError, KeyError):
            pass
    return s


async def run_spike(cfg: SpikeConfig) -> tuple[list[RequestResult], list[Sample]]:
    http = httpx.AsyncClient()
    client = AsyncOpenAI(
        base_url=cfg.base_url, api_key=cfg.api_key, timeout=cfg.request_timeout, max_retries=0
    )
    t0 = time.monotonic()
    results = [RequestResult(i, t) for i, t in enumerate(arrival_times(cfg.phases))]
    samples: list[Sample] = []
    done = asyncio.Event()

    async def sampler() -> None:
        quiet_since: float | None = None
        while True:
            now = time.monotonic() - t0
            samples.append(await _sample(http, cfg, now))
            if done.is_set():
                quiet_since = quiet_since if quiet_since is not None else now
                if now - quiet_since >= cfg.observe_after:
                    return
            await asyncio.sleep(cfg.sample_every)

    async def sender(r: RequestResult) -> None:
        await asyncio.sleep(max(0.0, r.sent - (time.monotonic() - t0)))
        await _send(client, cfg, r, t0)

    sampling = asyncio.create_task(sampler())
    await asyncio.gather(*(sender(r) for r in results))
    done.set()
    await sampling
    await http.aclose()
    await client.close()
    return results, samples


def save(
    out: Path,
    cfg: SpikeConfig,
    results: Sequence[RequestResult],
    samples: Sequence[Sample],
    waiting_target: float,
) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    config = {k: v for k, v in asdict(cfg).items() if k != "api_key"}
    doc = {
        "config": config,
        "waiting_target": waiting_target,
        "requests": [asdict(r) for r in results],
        "samples": [asdict(s) for s in samples],
    }
    out.with_suffix(".json").write_text(json.dumps(doc, indent=1) + "\n")
    md = render_markdown(cfg.phases, results, samples, waiting_target)
    out.with_suffix(".md").write_text(md)
    return md
