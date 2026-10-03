"""Cost model: hosted tokens with caching, self-hosted daily cost, break-even."""

from __future__ import annotations

import pytest

from selfhost.cost import (
    IncidentTokens,
    TokenPrice,
    break_even_per_day,
    hosted_cost,
    hosted_prices,
    incident_tokens,
    load_prices,
    mean_tokens,
    self_hosted_daily,
    traces_tokens,
)


def test_incident_tokens_reads_previous_prompt_and_writes_the_rest() -> None:
    t = incident_tokens([(3000, 100), (5000, 200), (9000, 300)])
    assert t == IncidentTokens(
        uncached=3000, cache_write=2000 + 4000, cache_read=3000 + 5000, output=600
    )
    assert t.input_total == 3000 + 5000 + 9000  # every prompt token is billed exactly once


def test_hosted_cost() -> None:
    p = TokenPrice(input=4, output=20, cache_write=5, cache_read=0.2)
    t = IncidentTokens(uncached=1_000_000, cache_write=0, cache_read=1_000_000, output=1_000_000)
    assert hosted_cost(t, p) == pytest.approx(5 + 0.2 + 20)
    assert hosted_cost(t, p, output_factor=2) == pytest.approx(5 + 0.2 + 40)


def test_self_hosted_daily_adds_replicas_only_past_capacity() -> None:
    one = 24 * 2.0 + 30 * 12 / 365
    assert self_hosted_daily(0, 100, 2.0, 30) == pytest.approx(one)
    assert self_hosted_daily(2400, 100, 2.0, 30) == pytest.approx(one)
    assert self_hosted_daily(2401, 100, 2.0, 30) == pytest.approx(one + 48)


def test_break_even() -> None:
    # one replica: $48/day + storage; hosted $0.10 per incident
    v = break_even_per_day(0.10, 100, 2.0, 0)
    assert v == pytest.approx(480)
    assert break_even_per_day(0.001, 100, 2.0, 0) is None  # needs 48,000/day, capacity is 2,400


def test_prices_and_traces_load() -> None:
    prices = hosted_prices(load_prices())
    assert set(prices) == {"claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"}
    assert prices["claude-opus-5-5"].cache_write == pytest.approx(
        1.25 * prices["claude-opus-5-5"].input
    )
    tokens = traces_tokens()
    assert len(tokens) == 20
    avg = mean_tokens(tokens)
    assert 30_000 < avg.input_total < 45_000
    assert avg.cache_read > avg.cache_write  # most of each prompt repeats the previous call


def test_gpu_estimate() -> None:
    from selfhost.cost import GpuEstimate

    g = GpuEstimate(params=1e9, weight_bytes=1e9, peak_flops=2e12, bandwidth=1e10, mfu=0.5,
                    bandwidth_eff=0.5, batch=10)  # fmt: skip
    assert g.prefill_tps == pytest.approx(500)  # 0.5 * 2e12 / 2e9
    assert g.step_s == pytest.approx(0.2)  # 1e9 / 5e9
    # 1000 prefill tokens = 2 s; 100 output tokens = 100 steps of 0.2 s shared by 10 = 2 s
    assert g.incidents_per_hour(1000, 100) == pytest.approx(900)
