"""The dashboard, alert rules and KEDA query only use metrics that exist, so a typo or a metric
renamed in a vLLM upgrade fails here instead of showing an empty panel or a silent alert."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "deploy/monitoring/dashboards/vllm-serving.json"
RULES = ROOT / "deploy/monitoring/alerts/vllm.rules.yaml"
SCALEDOBJECT = ROOT / "deploy/helm/vllm/templates/scaledobject.yaml"

# Exposed by vllm/vllm-openai-cpu:v0.30.0 (/metrics on the kind pod, 2026-10-03) and by
# kube-state-metrics in the prometheus chart 29.35.0. Histograms are listed by their _bucket series.
KNOWN = {
    "vllm:num_requests_running",
    "vllm:num_requests_waiting",
    "vllm:kv_cache_usage_perc",
    "vllm:num_preemptions_total",
    "vllm:prompt_tokens_total",
    "vllm:generation_tokens_total",
    "vllm:request_success_total",
    "vllm:time_to_first_token_seconds_bucket",
    "vllm:inter_token_latency_seconds_bucket",
    "vllm:request_queue_time_seconds_bucket",
    "kube_pod_status_phase",
    "kube_pod_container_status_restarts_total",
    "kube_deployment_status_replicas",
    "kube_deployment_status_replicas_available",
    "kube_horizontalpodautoscaler_status_desired_replicas",
}
METRIC = re.compile(r"\b(vllm:[a-z_]+|kube_[a-z_]+)")


def _dashboard_exprs() -> list[str]:
    dash = json.loads(DASHBOARD.read_text())
    return [t["expr"] for p in dash["panels"] for t in p["targets"]]


def test_dashboard_uses_known_metrics_and_project_a_datasource() -> None:
    dash = json.loads(DASHBOARD.read_text())
    used = {m for e in _dashboard_exprs() for m in METRIC.findall(e)}
    assert used <= KNOWN, used - KNOWN
    assert {p["datasource"]["uid"] for p in dash["panels"]} == {"prometheus"}
    assert len({p["id"] for p in dash["panels"]}) == len(dash["panels"])


def test_dashboard_covers_the_b3_signals() -> None:
    used = {m for e in _dashboard_exprs() for m in METRIC.findall(e)}
    for metric in (
        "vllm:num_requests_running",
        "vllm:num_requests_waiting",
        "vllm:time_to_first_token_seconds_bucket",
        "vllm:inter_token_latency_seconds_bucket",
        "vllm:kv_cache_usage_perc",
        "vllm:generation_tokens_total",
    ):
        assert metric in used


def test_alert_rules_use_known_metrics() -> None:
    used = set(METRIC.findall(RULES.read_text()))
    assert used <= KNOWN, used - KNOWN
    names = re.findall(r"- alert: (\w+)", RULES.read_text())
    assert names == [
        "VLLMTimeToFirstTokenHigh",
        "VLLMKVCacheNearlyFull",
        "VLLMPodRestarting",
        "VLLMReplicaPending",
    ]


def test_keda_scales_on_the_queue_the_dashboard_shows() -> None:
    query = re.search(r"query: '(.+)'", SCALEDOBJECT.read_text())
    assert query is not None
    assert METRIC.findall(query.group(1)) == ["vllm:num_requests_waiting"]
