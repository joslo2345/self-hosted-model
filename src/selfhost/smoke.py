"""Smoke test for an OpenAI-compatible endpoint: plain chat, streaming, and a tool call made with
the incident agent's real tool definitions (data/agent_tools.json, exported from Project A)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

TOOLS_FILE = Path(__file__).resolve().parents[2] / "data" / "agent_tools.json"

TOOL_PROMPT = (
    "Incident INC-2025001: GPU 3 on node gpu-h100-07 crossed 92 C at 2025-06-01T10:00:00Z. "
    "Start the investigation with one tool call."
)


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    seconds: float


def load_tools(path: Path = TOOLS_FILE) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = json.loads(path.read_text())
    return tools


def _timed(name: str, fn: Any) -> Check:
    start = time.perf_counter()
    try:
        ok, detail = fn()
    except Exception as exc:  # report any client or server error as a failed check
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    return Check(name, ok, detail, time.perf_counter() - start)


def check_chat(client: OpenAI, model: str) -> Check:
    def run() -> tuple[bool, str]:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word: ready"}],
            max_tokens=256,
        )
        text = (resp.choices[0].message.content or "").strip()
        return bool(text), text[:80]

    return _timed("chat", run)


def check_stream(client: OpenAI, model: str) -> Check:
    def run() -> tuple[bool, str]:
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Count from 1 to 5, separated by spaces."}],
            max_tokens=256,
            stream=True,
        )
        chunks = [c.choices[0].delta.content or "" for c in stream if c.choices]
        text = "".join(chunks).strip()
        n = sum(1 for c in chunks if c)
        return n > 1 and bool(text), f"{n} content chunks: {text[:60]!r}"

    return _timed("stream", run)


def validate_tool_call(name: str, arguments: str, tools: list[dict[str, Any]]) -> str | None:
    """Return a problem description, or None if the call names a known tool with valid JSON
    arguments that include every required field."""
    specs = {t["function"]["name"]: t["function"] for t in tools}
    if name not in specs:
        return f"unknown tool {name!r}"
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return f"arguments are not JSON: {arguments[:80]!r}"
    if not isinstance(args, dict):
        return "arguments are not a JSON object"
    missing = set(specs[name]["parameters"].get("required", [])) - set(args)
    if missing:
        return f"missing required arguments {sorted(missing)}"
    return None


def check_tool_call(client: OpenAI, model: str, tools: list[dict[str, Any]]) -> Check:
    def run() -> tuple[bool, str]:
        resp = client.chat.completions.create(  # type: ignore[call-overload]
            model=model,
            messages=[
                {"role": "system", "content": "You investigate GPU fleet incidents with tools."},
                {"role": "user", "content": TOOL_PROMPT},
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=1024,
        )
        calls = resp.choices[0].message.tool_calls or []
        if not calls:
            return False, "no tool call returned"
        call = calls[0]
        fn = getattr(call, "function", None)
        if fn is None:
            return False, "tool call has no function"
        problem = validate_tool_call(fn.name, fn.arguments, tools)
        return problem is None, problem or f"{fn.name}({fn.arguments})"

    return _timed("tool_call", run)


def run_smoke(base_url: str, model: str, api_key: str = "not-needed") -> list[Check]:
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=600)
    tools = load_tools()
    return [
        check_chat(client, model),
        check_stream(client, model),
        check_tool_call(client, model, tools),
    ]
