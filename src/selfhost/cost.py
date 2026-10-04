"""Cost model (B4): self-hosted vLLM on an Azure A100 against hosted Claude models, per incident.

Self-hosted cost is time: a GPU node costs the same per hour whether it serves one incident or a
thousand, so cost per incident depends on daily volume. Hosted cost is tokens: the same per incident
at any volume. Their crossing point is the break-even volume.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data"
PRICES_FILE = DATA / "b4_prices.json"
HOURS_PER_MONTH = 730


@dataclass(frozen=True)
class TokenPrice:
    """US dollars per million tokens."""

    input: float
    output: float
    cache_write: float
    cache_read: float


@dataclass(frozen=True)
class IncidentTokens:
    """Tokens one incident costs on a hosted API with prompt caching: each call reads the previous
    call's prompt from the cache and writes only what's new (Project A's agent appends to one
    conversation, so consecutive calls share their prefix)."""

    uncached: int  # first call of the incident: nothing cached yet (written to the cache)
    cache_write: int  # new tokens on later calls
    cache_read: int
    output: int

    @property
    def input_total(self) -> int:
        return self.uncached + self.cache_write + self.cache_read


def incident_tokens(calls: Sequence[tuple[int, int]]) -> IncidentTokens:
    """From one incident's (prompt tokens, output tokens) per model call, in order."""
    write = read = 0
    for (prev_in, _), (cur_in, _) in pairwise(calls):
        read += prev_in
        write += max(0, cur_in - prev_in)
    return IncidentTokens(
        uncached=calls[0][0] if calls else 0,
        cache_write=write,
        cache_read=read,
        output=sum(o for _, o in calls),
    )


def hosted_cost(t: IncidentTokens, p: TokenPrice, output_factor: float = 1.0) -> float:
    """Dollars per incident. The first call's prompt is a cache write (it seeds the cache).
    output_factor scales output tokens, e.g. for thinking tokens a model can't turn off."""
    return (
        (t.uncached + t.cache_write) * p.cache_write
        + t.cache_read * p.cache_read
        + t.output * output_factor * p.output
    ) / 1e6


def self_hosted_daily(
    incidents_per_day: float,
    capacity_per_hour: float,
    gpu_per_hour: float,
    storage_per_month: float,
    min_replicas: int = 1,
) -> float:
    """Dollars per day: enough always-on GPU replicas for the volume (at least min_replicas, as in
    B3's autoscaling), plus the weight cache."""
    replicas = max(min_replicas, math.ceil(incidents_per_day / (capacity_per_hour * 24)))
    return replicas * gpu_per_hour * 24 + storage_per_month * 12 / 365


def break_even_per_day(
    hosted_per_incident: float,
    capacity_per_hour: float,
    gpu_per_hour: float,
    storage_per_month: float,
) -> float | None:
    """Smallest daily volume at which one self-hosted replica costs less than the hosted API, or
    None if one replica's capacity runs out first."""
    fixed = self_hosted_daily(0, capacity_per_hour, gpu_per_hour, storage_per_month)
    volume = fixed / hosted_per_incident
    return volume if volume <= capacity_per_hour * 24 else None


@dataclass(frozen=True)
class GpuEstimate:
    """First-principles throughput of one GPU for this workload; every input is stated so the
    estimate can be checked and redone with measured numbers (nothing here was run on an A100).

    Prefill is compute-bound: 2 FLOPs per parameter per token, at a fraction (MFU) of peak.
    Decode is memory-bound: each engine step reads the weights once and yields one token per
    running request.
    """

    params: float = 9.0e9  # Qwen3.5-9B
    weight_bytes: float = 9.5e9  # FP8 weights (8-bit)
    peak_flops: float = 312e12  # A100 dense bf16 tensor throughput (FP8 weights are upcast)
    bandwidth: float = 1.935e12  # A100 80 GB PCIe HBM2e, bytes/s
    mfu: float = 0.40  # share of peak FLOPs reached in prefill
    bandwidth_eff: float = 0.70  # share of bandwidth reached in decode
    batch: int = 16  # requests decoding together at the latency target

    @property
    def prefill_tps(self) -> float:
        return self.mfu * self.peak_flops / (2 * self.params)

    @property
    def step_s(self) -> float:
        return self.weight_bytes / (self.bandwidth_eff * self.bandwidth)

    def incidents_per_hour(self, prefill_tokens: float, output_tokens: float) -> float:
        """GPU-seconds per incident: its prefill, plus its share of batched decode steps."""
        seconds = prefill_tokens / self.prefill_tps + output_tokens * self.step_s / self.batch
        return 3600 / seconds


def load_prices(path: Path = PRICES_FILE) -> dict[str, Any]:
    prices: dict[str, Any] = json.loads(path.read_text())
    return prices


def hosted_prices(prices: dict[str, Any]) -> dict[str, TokenPrice]:
    return {name: TokenPrice(**p) for name, p in prices["hosted"]["models"].items()}


def traces_tokens(path: Path = DATA / "b4_traces.json") -> list[IncidentTokens]:
    doc = json.loads(path.read_text())
    return [
        incident_tokens([(c["input_tokens"], c["output_tokens"]) for c in conv["calls"]])
        for conv in doc["conversations"]
    ]


def mean_tokens(incidents: Sequence[IncidentTokens]) -> IncidentTokens:
    n = len(incidents)
    return IncidentTokens(
        uncached=round(sum(i.uncached for i in incidents) / n),
        cache_write=round(sum(i.cache_write for i in incidents) / n),
        cache_read=round(sum(i.cache_read for i in incidents) / n),
        output=round(sum(i.output for i in incidents) / n),
    )
