"""B4: export the B1 agent runs (Qwen3.5-9B, thinking off) from Project A's trace tables as
replayable conversations: data/b4_traces.json.

Runs in Project A's environment, read-only, because the first user message is Project A's rendering
of the incident:
    cd ../../project-a/incident-assistant
    DATABASE_URL=postgresql://... uv run --frozen python \
        ../../project-b/self-hosted-model/scripts/export_traces.py <b1 report json> <out json>

The file also holds the tool definitions the agent offered on every call. Each conversation is the
message list the agent built (system prompt, incident, then assistant turns
and tool results, in the OpenAI format Project A's openai_compat provider sends). Each model call
records how many of those messages it saw, its recorded prompt and output tokens, and its latency.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import asyncpg
from agent.data import PgFleetData
from agent.diagnosis import SUBMIT_SPEC
from agent.loop import PROMPT_SHA, SYSTEM_PROMPT, render_incident
from agent.tools import TOOLS


def tool_definitions() -> list[dict[str, Any]]:
    """The tools as the agent offers them: its tools in name order, then submit_diagnosis
    (Investigator.run), in the OpenAI format of the openai_compat provider."""
    specs = [TOOLS[n].spec for n in sorted(TOOLS)] + [SUBMIT_SPEC]
    return [
        {
            "type": "function",
            "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
        }
        for t in specs
    ]


def _tool_content(output: Any) -> tuple[str, bool]:
    """A tool step's stored result, and whether the trace clipped it (over 20,000 characters)."""
    if isinstance(output, str):
        return output, False
    if isinstance(output, dict) and output.get("truncated"):
        return str(output.get("head", "")), True
    return json.dumps(output), False


async def export(report: Path, out: Path) -> None:
    cases = json.loads(report.read_text())["cases"]
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    assert pool is not None
    fleet = PgFleetData(pool)
    conversations = []
    for case in cases:
        incident = await fleet.incident(uuid.UUID(case["incident_id"]))
        assert incident is not None, case["incident_id"]
        steps = await pool.fetch(
            "SELECT seq, kind, name, latency_ms, input::text, output::text, input_tokens, "
            "output_tokens FROM agent_steps WHERE run_id = $1 ORDER BY seq",
            uuid.UUID(case["run_id"]),
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": render_incident(incident)},
        ]
        calls, pending, clipped = [], [], 0
        for s in steps:
            output = json.loads(s["output"]) if s["output"] else None
            if s["kind"] == "model":
                calls.append(
                    {
                        "messages": len(messages),
                        "input_tokens": s["input_tokens"],
                        "output_tokens": s["output_tokens"],
                        "latency_ms": s["latency_ms"],
                    }
                )
                tool_calls = (output or {}).get("tool_calls", [])
                turn: dict[str, Any] = {
                    "role": "assistant",
                    "content": (output or {}).get("text", ""),
                }
                if tool_calls:
                    turn["tool_calls"] = [
                        {
                            "id": c["id"],
                            "type": "function",
                            "function": {
                                "name": c["name"],
                                "arguments": json.dumps(c["arguments"]),
                            },
                        }
                        for c in tool_calls
                    ]
                messages.append(turn)
                pending = [c["id"] for c in tool_calls]
            else:
                content, was_clipped = _tool_content(output)
                clipped += was_clipped
                call_id = pending.pop(0) if pending else f"unpaired_{s['seq']}"
                messages.append({"role": "tool", "tool_call_id": call_id, "content": content})
        conversations.append(
            {
                "case_id": case["case_id"],
                "run_id": case["run_id"],
                "clipped_tool_results": clipped,
                "messages": messages,
                "calls": calls,
            }
        )
    await pool.close()
    out.write_text(
        json.dumps(
            {
                "source": report.name,
                "prompt_sha": PROMPT_SHA,
                "tools": tool_definitions(),
                "conversations": conversations,
            },
            indent=1,
        )
        + "\n"
    )
    n = sum(len(c["calls"]) for c in conversations)
    print(f"{len(conversations)} conversations, {n} model calls -> {out}")


if __name__ == "__main__":
    asyncio.run(export(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()))
