"""Spike test helpers: phases, arrivals, metric parsing, cluster parsing and the summary."""

from __future__ import annotations

from typing import Any

import pytest

from selfhost.spike import (
    Phase,
    RequestResult,
    Sample,
    arrival_times,
    events,
    parse_cluster,
    parse_phases,
    parse_prometheus_text,
    percentile,
    render_markdown,
    windows,
)


def test_parse_phases() -> None:
    assert parse_phases("60:0.05,180:0.4") == [Phase(60, 0.05), Phase(180, 0.4)]
    with pytest.raises(ValueError):
        parse_phases("0:1")
    with pytest.raises(ValueError):
        parse_phases("10:-1")


def test_arrivals_are_evenly_spaced_per_phase() -> None:
    times = arrival_times([Phase(10, 0.2), Phase(2, 2), Phase(5, 0)])
    assert times == [0, 5, 10, 10.5, 11, 11.5]


def test_arrivals_count_is_rate_times_duration() -> None:
    assert len(arrival_times([Phase(180, 0.4)])) == 72
    assert len(arrival_times([Phase(60, 0.05)])) == 3


def test_percentile_nearest_rank() -> None:
    assert percentile([], 95) is None
    assert percentile([3.0], 95) == 3.0
    values = [float(v) for v in range(1, 21)]
    assert percentile(values, 50) == 10
    assert percentile(values, 95) == 19
    assert percentile(values, 100) == 20


METRICS = """# HELP vllm:num_requests_waiting Number of requests waiting to be processed.
# TYPE vllm:num_requests_waiting gauge
vllm:num_requests_waiting{engine="0",model_name="qwen3.5-9b"} 7.0
vllm:num_requests_waiting_by_reason{engine="0",reason="capacity"} 7.0
vllm:num_requests_running{engine="0",model_name="qwen3.5-9b"} 4.0
vllm:num_requests_running{engine="1",model_name="qwen3.5-9b"} 2.0
"""


def test_parse_prometheus_text_sums_one_metric_only() -> None:
    assert parse_prometheus_text(METRICS, "vllm:num_requests_waiting") == 7.0
    assert parse_prometheus_text(METRICS, "vllm:num_requests_running") == 6.0
    assert parse_prometheus_text(METRICS, "vllm:kv_cache_usage_perc") is None


def _pod(name: str, phase: str, ready: bool, instance: str = "vllm", **meta: Any) -> dict[str, Any]:
    return {
        "kind": "Pod",
        "metadata": {"name": name, "labels": {"app.kubernetes.io/instance": instance}, **meta},
        "status": {"phase": phase, "conditions": [{"type": "Ready", "status": str(ready)}]},
    }


def test_parse_cluster() -> None:
    doc = {
        "items": [
            {
                "kind": "HorizontalPodAutoscaler",
                "spec": {"scaleTargetRef": {"name": "vllm"}},
                "status": {"desiredReplicas": 2},
            },
            _pod("vllm-a", "Running", True),
            _pod("vllm-b", "Pending", False),
            _pod("vllm-old", "Running", True, deletionTimestamp="2026-10-03T00:00:00Z"),
            _pod("probe", "Running", True, instance="other"),
        ]
    }
    assert parse_cluster(doc, "vllm") == (2, 2, 1, 1)
    assert parse_cluster({}, "vllm") == (None, 0, 0, 0)


PHASES = [Phase(20, 0.1), Phase(40, 1), Phase(40, 0.1)]


def _samples() -> list[Sample]:
    s = [Sample(t, waiting=0, desired=1, pods=1, ready=1) for t in range(0, 20, 5)]
    s += [
        Sample(20, waiting=1, desired=1, pods=1, ready=1),
        Sample(25, waiting=5, desired=1, pods=1, ready=1),
        Sample(30, waiting=9, desired=2, pods=1, ready=1),
        Sample(35, waiting=12, desired=2, pods=2, pending=1, ready=1),
        Sample(50, waiting=8, desired=2, pods=2, ready=2, alerts=["VLLMTimeToFirstTokenHigh"]),
        Sample(90, waiting=0, desired=1, pods=1, ready=1, alerts=["VLLMTimeToFirstTokenHigh"]),
    ]
    return s


def test_events_measure_from_spike_start() -> None:
    ev = events(_samples(), PHASES, waiting_target=2)
    assert ev["spike_start"] == 20
    assert ev["queue_over_target"] == 25
    assert ev["keda_scale_decision"] == 30
    assert ev["new_pod_created"] == 35
    assert ev["new_pod_ready"] == 50
    assert ev["scaled_back_down"] == 90
    assert ev["alert:VLLMTimeToFirstTokenHigh"] == 50


def test_events_missing_milestones_are_none() -> None:
    samples = [Sample(t, waiting=9, desired=2, pods=2, pending=1, ready=1) for t in (0, 30)]
    samples[0] = Sample(0, waiting=0, desired=1, pods=1, ready=1)
    ev = events(samples, PHASES, waiting_target=2)
    assert ev["new_pod_ready"] is None
    assert ev["scaled_back_down"] is None


def test_windows_and_markdown() -> None:
    requests = [
        RequestResult(0, 0, ttft=1, total=2),
        RequestResult(1, 22, ttft=5, total=6),
        RequestResult(2, 25, error="APITimeoutError"),
        RequestResult(3, 35, ttft=30, total=31),
    ]
    rows = windows(requests, _samples(), 30)
    assert [r["sent"] for r in rows] == [3, 1, 0, 0]
    assert rows[0]["errors"] == 1
    assert rows[0]["ttft_p95"] == 5
    assert rows[1]["max_waiting"] == 12
    assert rows[1]["pending"] == 0  # last sample in [30, 60) is t=50: pod ready
    md = render_markdown(PHASES, requests, _samples(), waiting_target=2)
    assert "| KEDA asks for another replica | +10 s |" in md
    assert "| New pod Ready | +30 s |" in md
    assert "Alert VLLMTimeToFirstTokenHigh firing | +30 s |" in md
    assert "4 sent, 1 failed" in md
