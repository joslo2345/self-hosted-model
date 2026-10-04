"""Load test helpers: the call mix agents replay, and the per-level summary."""

from __future__ import annotations

from selfhost.loadtest import Call, CallResult, agent_calls, load_conversations, summarize


def _convs(*lengths: int) -> list[list[Call]]:
    return [[Call(c, k, [], 10, 100) for k in range(n)] for c, n in enumerate(lengths)]


def test_agents_start_spread_over_all_calls() -> None:
    convs = _convs(3, 2, 5)  # 10 calls
    starts = [(c.conversation, c.index) for c in (next(agent_calls(convs, a, 5)) for a in range(5))]
    # flat positions 0, 2, 4, 6, 8
    assert starts == [(0, 0), (0, 2), (1, 1), (2, 1), (2, 3)]


def test_agent_walks_conversations_in_order_and_wraps() -> None:
    convs = _convs(2, 1)
    calls = agent_calls(convs, 0, 1)
    seq = [next(calls)] + [calls.send(False) for _ in range(4)]
    assert [(c.conversation, c.index) for c in seq] == [(0, 0), (0, 1), (1, 0), (0, 0), (0, 1)]


def test_failed_call_abandons_the_incident() -> None:
    convs = _convs(3, 2)
    calls = agent_calls(convs, 0, 1)
    assert next(calls).index == 0
    nxt = calls.send(True)  # first call of conversation 0 failed
    assert (nxt.conversation, nxt.index) == (1, 0)


def test_replayed_mix_matches_traces_at_any_concurrency() -> None:
    convs = load_conversations()
    flat = [c for conv in convs for c in conv]
    for agents in (16, 64):
        firsts = [next(agent_calls(convs, a, agents)) for a in range(agents)]
        mean = sum(c.recorded_input_tokens for c in firsts) / agents
        overall = sum(c.recorded_input_tokens for c in flat) / len(flat)
        assert abs(mean / overall - 1) < 0.15


def test_summarize() -> None:
    results = [
        CallResult(0, 0, 0, 0.0, ttft=1.0, latency=11.0, prompt_tokens=1000, output_tokens=100),
        CallResult(1, 0, 1, 0.0, ttft=3.0, latency=13.0, prompt_tokens=2000, output_tokens=100),
        CallResult(2, 1, 0, 0.0, error="timeout"),
    ]
    s = summarize(results, concurrency=3, wall_s=3600, calls_per_incident=2)
    assert (s.calls, s.errors, s.timeouts) == (3, 1, 1)
    assert s.ttft_p95 == 3.0
    assert s.decode_tps_p50 == 10.0
    assert s.calls_per_hour == 2
    assert s.incidents_per_hour == 1
