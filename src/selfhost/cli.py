"""Command-line entry point.

    selfhost smoke --base-url http://127.0.0.1:8000/v1 --model <served-model-name>
"""

from __future__ import annotations

import argparse
import sys

from selfhost.smoke import run_smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="selfhost")
    sub = parser.add_subparsers(dest="command", required=True)

    smoke = sub.add_parser("smoke", help="chat, streaming and tool-call checks on an endpoint")
    smoke.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    smoke.add_argument("--model", required=True)
    smoke.add_argument("--api-key", default="not-needed")

    args = parser.parse_args(argv)
    checks = run_smoke(args.base_url, args.model, args.api_key)
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}  {c.name:<10} {c.seconds:6.1f}s  {c.detail}")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
