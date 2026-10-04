"""Command-line entry point.

selfhost smoke --base-url http://127.0.0.1:8100/v1 --model <served-model-name>
selfhost loadtest --model qwen3.5-9b --levels 1,4,16 --duration 240 --label baseline
selfhost spike --base-url http://127.0.0.1:8101/v1 --model qwen3.5-9b --phases 60:0.05,180:0.4
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from selfhost import loadtest
from selfhost.smoke import run_smoke
from selfhost.spike import SpikeConfig, parse_phases, run_spike, save


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="selfhost")
    sub = parser.add_subparsers(dest="command", required=True)

    smoke = sub.add_parser("smoke", help="chat, streaming and tool-call checks on an endpoint")
    smoke.add_argument("--base-url", default="http://127.0.0.1:8100/v1")
    smoke.add_argument("--model", required=True)
    smoke.add_argument("--api-key", default="not-needed")

    spike = sub.add_parser("spike", help="spike test: latency, queue and scale-up over time")
    spike.add_argument("--base-url", default="http://127.0.0.1:8101/v1")
    spike.add_argument("--model", required=True)
    spike.add_argument("--api-key", default="not-needed")
    spike.add_argument("--phases", required=True, help="seconds:req_per_s,... e.g. 60:0.05,180:0.4")
    spike.add_argument("--max-tokens", type=int, default=64)
    spike.add_argument("--namespace", default="selfhost")
    spike.add_argument("--deployment", default="vllm")
    spike.add_argument("--prometheus-url", default=None)
    spike.add_argument("--waiting-target", type=float, default=2.0, help="KEDA's waiting/replica")
    spike.add_argument("--observe-after", type=float, default=180.0)
    spike.add_argument("--out", type=Path, default=Path("eval/b3/spike"))

    load = sub.add_parser("loadtest", help="replay agent conversations at increasing concurrency")
    load.add_argument("--base-url", default="http://127.0.0.1:8100/v1")
    load.add_argument("--model", required=True)
    load.add_argument("--api-key", default="not-needed")
    load.add_argument("--levels", default="1,4,16,32,64", help="concurrent agents per level")
    load.add_argument("--duration", type=float, default=240.0, help="seconds per level")
    load.add_argument("--label", required=True, help="configuration name, e.g. baseline")
    load.add_argument("--out", type=Path, default=None, help="default: eval/b4/<label>")

    args = parser.parse_args(argv)
    if args.command == "loadtest":
        return _loadtest(args)
    if args.command == "spike":
        cfg = SpikeConfig(
            base_url=args.base_url,
            model=args.model,
            api_key=args.api_key,
            phases=parse_phases(args.phases),
            max_tokens=args.max_tokens,
            namespace=args.namespace,
            deployment=args.deployment,
            prometheus_url=args.prometheus_url,
            observe_after=args.observe_after,
        )
        results, samples = asyncio.run(run_spike(cfg))
        print(save(args.out, cfg, results, samples, args.waiting_target))
        return 0

    checks = run_smoke(args.base_url, args.model, args.api_key)
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}  {c.name:<10} {c.seconds:6.1f}s  {c.detail}")
    return 0 if all(c.ok for c in checks) else 1


def _loadtest(args: argparse.Namespace) -> int:
    conversations = loadtest.load_conversations()
    per_incident = sum(len(c) for c in conversations) / len(conversations)
    levels = []
    for n in (int(x) for x in args.levels.split(",")):
        calls, wall = asyncio.run(
            loadtest.run_level(
                args.base_url, args.model, args.api_key, conversations, n, args.duration
            )
        )
        summary = loadtest.summarize(calls, n, wall, per_incident)
        levels.append({"summary": summary, "calls": calls})
        print(loadtest.render_markdown([summary], args.label).splitlines()[-1], flush=True)
        if summary.calls and summary.timeouts == summary.calls:
            print(f"every call timed out at {n} agents: higher levels skipped", flush=True)
            break
    config = {"base_url": args.base_url, "model": args.model, "duration_s": args.duration,
              "calls_per_incident": per_incident}  # fmt: skip
    out = args.out or Path("eval/b4") / args.label
    print(loadtest.save(out, args.label, config, levels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
