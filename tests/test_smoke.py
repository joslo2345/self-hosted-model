"""Smoke checks against a fake OpenAI-compatible server (httpx MockTransport)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx2 as httpx
from openai import OpenAI

from selfhost.smoke import (
    check_chat,
    check_stream,
    check_tool_call,
    load_tools,
    validate_tool_call,
)

TOOLS = load_tools()


def _completion(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "c1",
        "object": "chat.completion",
        "created": 0,
        "model": "m",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
    }


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> OpenAI:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAI(base_url="http://fake/v1", api_key="x", http_client=http, max_retries=0)


def test_exported_tools_match_project_a() -> None:
    names = {t["function"]["name"] for t in TOOLS}
    assert {"get_incident", "get_metrics", "search_runbooks", "drain_node"} <= names


def test_chat_passes_on_text() -> None:
    client = _client(
        lambda r: httpx.Response(200, json=_completion({"role": "assistant", "content": "ready"}))
    )
    check = check_chat(client, "m")
    assert check.ok
    assert check.detail == "ready"


def test_chat_fails_on_server_error() -> None:
    client = _client(lambda r: httpx.Response(500, json={"error": {"message": "boom"}}))
    check = check_chat(client, "m")
    assert not check.ok
    assert "InternalServerError" in check.detail


def test_stream_needs_several_chunks() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        events = []
        for piece in ["1 ", "2 ", "3"]:
            chunk = {
                "id": "c1",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": "m",
                "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
            }
            events.append(f"data: {json.dumps(chunk)}\n\n")
        events.append("data: [DONE]\n\n")
        return httpx.Response(
            200, text="".join(events), headers={"content-type": "text/event-stream"}
        )

    check = check_stream(_client(handler), "m")
    assert check.ok, check.detail
    assert "3 content chunks" in check.detail


def _tool_reply(name: str, arguments: str) -> Callable[[httpx.Request], httpx.Response]:
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": "t1", "type": "function", "function": {"name": name, "arguments": arguments}}
        ],
    }
    return lambda r: httpx.Response(200, json=_completion(message))


def test_tool_call_sends_agent_tools_and_accepts_valid_call() -> None:
    seen: dict[str, Any] = {}
    reply = _tool_reply("get_incident", json.dumps({"incident_id": "INC-2025001"}))

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return reply(request)

    check = check_tool_call(_client(handler), "m", TOOLS)
    assert len(seen["tools"]) == len(TOOLS)
    assert check.ok, check.detail
    assert check.detail.startswith("get_incident(")


def test_tool_call_fails_without_call() -> None:
    client = _client(
        lambda r: httpx.Response(200, json=_completion({"role": "assistant", "content": "hmm"}))
    )
    check = check_tool_call(client, "m", TOOLS)
    assert not check.ok
    assert check.detail == "no tool call returned"


def test_validate_tool_call_problems() -> None:
    assert validate_tool_call("rm_rf", "{}", TOOLS) == "unknown tool 'rm_rf'"
    assert "not JSON" in (validate_tool_call("get_incident", "{oops", TOOLS) or "")
    assert validate_tool_call("get_incident", "[]", TOOLS) == "arguments are not a JSON object"
    get_metrics = next(t for t in TOOLS if t["function"]["name"] == "get_metrics")["function"]
    if get_metrics["parameters"].get("required"):
        assert "missing required" in (validate_tool_call("get_metrics", "{}", TOOLS) or "")
