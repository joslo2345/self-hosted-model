"""Load test (B4): replay real agent conversations at fixed concurrency.

Each of N simulated agents works through incidents one after another, as Project A's agent does:
one model call at a time, each call sending the conversation so far (data/b4_traces.json, exported
from the B1 runs). A call asks for exactly the number of tokens the real call produced, so prompt
and output lengths match production. Agents start new calls for `duration` seconds; calls still
running then are allowed to finish, up to the agent's 300 s limit per call (slower counts as a
timeout, as it would in Project A).
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Generator, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from selfhost.spike import percentile

TRACES_FILE = Path(__file__).resolve().parents[2] / "data" / "b4_traces.json"
CALL_LIMIT_S = 300.0  # Project A's limit per model call


@dataclass(frozen=True)
class Call:
    conversation: int
    index: int  # model call within the conversation
    messages: list[dict[str, Any]]
    output_tokens: int
    recorded_input_tokens: int


@dataclass
class CallResult:
    agent: int
    conversation: int
    index: int
    started: float  # seconds since the level started
    ttft: float | None = None
    latency: float | None = None
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None


def load_tools(path: Path = TRACES_FILE) -> list[dict[str, Any]]:
    """The tool definitions the agent offered on every call (all 8, with submit_diagnosis)."""
    tools: list[dict[str, Any]] = json.loads(path.read_text())["tools"]
    return tools


def load_conversations(path: Path = TRACES_FILE) -> list[list[Call]]:
    doc = json.loads(path.read_text())
    out = []
    for i, conv in enumerate(doc["conversations"]):
        out.append(
            [
                Call(i, k, conv["messages"][: c["messages"]], c["output_tokens"], c["input_tokens"])
                for k, c in enumerate(conv["calls"])
            ]
        )
    return out


def agent_calls(
    conversations: Sequence[Sequence[Call]], agent: int, agents: int
) -> Generator[Call, bool, None]:
    """The calls one agent makes, endlessly: every recorded call in order, starting at the agent's
    own evenly spread position among all calls, so the calls made at any moment have the same mix
    as the traces. (Starting every agent at an incident's first call over-sampled short first
    prompts: 84% of calls at 64 agents.) After a failed call, the agent abandons that incident and
    starts the next one, as Project A's agent does."""
    flat = [call for conv in conversations for call in conv]
    pos = (agent * len(flat)) // max(agents, 1)
    while True:
        call = flat[pos % len(flat)]
        failed = yield call
        pos += 1
        if failed:
            while flat[pos % len(flat)].index != 0:
                pos += 1


@dataclass(frozen=True)
class LevelSummary:
    concurrency: int
    duration_s: float
    calls: int
    errors: int
    timeouts: int
    ttft_p50: float | None
    ttft_p95: float | None
    latency_p50: float | None
    latency_p95: float | None
    decode_tps_p50: float | None  # per call: output tokens / (latency - ttft)
    output_tps: float  # all agents, output tokens per second of the level
    prompt_tps: float
    calls_per_hour: float
    incidents_per_hour: float  # calls per hour / mean calls per incident


def summarize(
    results: Sequence[CallResult], concurrency: int, wall_s: float, calls_per_incident: float
) -> LevelSummary:
    ok = [r for r in results if r.error is None and r.latency is not None]
    ttfts = [r.ttft for r in ok if r.ttft is not None]
    latencies = [r.latency for r in ok if r.latency is not None]
    decode = [
        r.output_tokens / (r.latency - r.ttft)
        for r in ok
        if r.output_tokens and r.ttft is not None and r.latency is not None and r.latency > r.ttft
    ]
    out_tokens = sum(r.output_tokens or 0 for r in ok)
    prompt_tokens = sum(r.prompt_tokens or 0 for r in ok)
    per_hour = len(ok) / wall_s * 3600 if wall_s > 0 else 0.0
    return LevelSummary(
        concurrency=concurrency,
        duration_s=wall_s,
        calls=len(results),
        errors=sum(1 for r in results if r.error),
        timeouts=sum(1 for r in results if r.error == "timeout"),
        ttft_p50=percentile(ttfts, 50),
        ttft_p95=percentile(ttfts, 95),
        latency_p50=percentile(latencies, 50),
        latency_p95=percentile(latencies, 95),
        decode_tps_p50=percentile(decode, 50),
        output_tps=out_tokens / wall_s if wall_s > 0 else 0.0,
        prompt_tps=prompt_tokens / wall_s if wall_s > 0 else 0.0,
        calls_per_hour=per_hour,
        incidents_per_hour=per_hour / calls_per_incident if calls_per_incident else 0.0,
    )


@dataclass
class RequestTiming:
    first: float | None = None
    prompt_tokens: int | None = None
    output_tokens: int | None = None


async def _call(
    client: AsyncOpenAI,
    model: str,
    tools: list[dict[str, Any]],
    call: Call,
    result: RequestTiming,
) -> None:
    stream = await client.chat.completions.create(  # type: ignore[call-overload]
        model=model,
        messages=call.messages,
        tools=tools,
        # tool_choice stays "auto", as in Project A: with "none", vllm-metal streams no content.
        max_tokens=call.output_tokens,
        stream=True,
        stream_options={"include_usage": True},
        # Exactly the recorded output length, whatever this run's text turns out to be.
        # (min_tokens would do the same, but vllm-metal rejects it.)
        extra_body={"ignore_eos": True},
    )
    async for chunk in stream:
        if result.first is None and chunk.choices:
            delta = chunk.choices[0].delta
            if delta.content or delta.tool_calls:  # the parser streams tool-call deltas too
                result.first = time.monotonic()
        if chunk.usage:
            result.prompt_tokens = chunk.usage.prompt_tokens
            result.output_tokens = chunk.usage.completion_tokens


async def run_level(
    base_url: str,
    model: str,
    api_key: str,
    conversations: Sequence[Sequence[Call]],
    concurrency: int,
    duration: float,
    call_limit: float = CALL_LIMIT_S,
) -> tuple[list[CallResult], float]:
    """Run `concurrency` agents for `duration` seconds; returns every call and the wall time."""
    client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=call_limit + 30, max_retries=0)
    tools = load_tools()
    results: list[CallResult] = []
    t0 = time.monotonic()

    def failing() -> bool:  # a systematic error: stop instead of hammering the server
        errors = sum(1 for r in results if r.error and r.error != "timeout")
        return errors >= 20 and not any(r.latency is not None for r in results)

    async def agent(a: int) -> None:
        calls = agent_calls(conversations, a, concurrency)
        call = next(calls)
        while time.monotonic() - t0 < duration and not failing():
            start = time.monotonic()
            r = CallResult(a, call.conversation, call.index, start - t0)
            results.append(r)
            timing = RequestTiming()
            try:
                await asyncio.wait_for(_call(client, model, tools, call, timing), call_limit)
                r.latency = time.monotonic() - start
                r.ttft = None if timing.first is None else timing.first - start
                r.prompt_tokens, r.output_tokens = timing.prompt_tokens, timing.output_tokens
            except TimeoutError:
                r.error = "timeout"
            except Exception as exc:  # any client or server error fails the call
                r.error = f"{type(exc).__name__}: {exc}"[:200]
            call = calls.send(r.error is not None)

    await asyncio.gather(*(agent(a) for a in range(concurrency)))
    wall = time.monotonic() - t0
    await client.close()
    return results, wall


def render_markdown(levels: Sequence[LevelSummary], label: str) -> str:
    def f(v: float | None, digits: int = 1) -> str:
        return "-" if v is None else f"{v:.{digits}f}"

    lines = [
        f"# Load test: {label}",
        "",
        "| Agents | Calls | Errors (timeouts) | TTFT p50 | TTFT p95 | Call p50 | Call p95 "
        "| Decode tok/s per call | Output tok/s | Prompt tok/s | Incidents/hour |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in levels:
        lines.append(
            f"| {s.concurrency} | {s.calls} | {s.errors} ({s.timeouts}) | {f(s.ttft_p50)} s "
            f"| {f(s.ttft_p95)} s | {f(s.latency_p50)} s | {f(s.latency_p95)} s "
            f"| {f(s.decode_tps_p50)} | {f(s.output_tps)} | {f(s.prompt_tps, 0)} "
            f"| {f(s.incidents_per_hour)} |"
        )
    return "\n".join(lines) + "\n"


def save(out: Path, label: str, config: dict[str, Any], levels: list[dict[str, Any]]) -> str:
    """levels: [{"summary": LevelSummary, "calls": [CallResult, ...]}, ...]"""
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "label": label,
        "config": config,
        "levels": [
            {"summary": asdict(lv["summary"]), "calls": [asdict(c) for c in lv["calls"]]}
            for lv in levels
        ],
    }
    out.with_suffix(".json").write_text(json.dumps(doc, indent=1) + "\n")
    md = render_markdown([lv["summary"] for lv in levels], label)
    out.with_suffix(".md").write_text(md)
    return md
