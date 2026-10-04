#!/usr/bin/env bash
# B1 comparison: run Project A's eval harness on the first N cases of its test set against each
# shortlisted model, with thinking on and off. Project A's code is unchanged; only its provider
# settings (AGENT_BASE_URL, AGENT_MODEL) point at the local vLLM server.
#
# Needs Project A's stack running (`make up` there). The judge is skipped here because it can't
# share memory with vLLM; re-judge the reports afterwards with `evaluate rejudge`.
#
# usage: scripts/compare_b1.sh [config ...]   config = <candidate>-<think|nothink>
set -euo pipefail

HERE=$(cd "$(dirname "$0")/.." && pwd)
PROJECT_A=${PROJECT_A:-$(cd "$HERE/../../project-a/incident-assistant" && pwd)}
OUT=${OUT:-$HERE/eval/b1}
LIMIT=${LIMIT:-20}
PORT=${PORT:-8100}
CONFIGS=("$@")
[ ${#CONFIGS[@]} -gt 0 ] || CONFIGS=(gemma-nothink gemma-think granite-nothink granite-think qwen-nothink qwen-think)

mkdir -p "$OUT/logs"

stop_server() {
  local pid
  pid=$(lsof -ti "tcp:$PORT" -sTCP:LISTEN || true)
  [ -z "$pid" ] && return 0
  kill "$pid"
  for _ in $(seq 1 60); do pgrep -f 'vllm serve' >/dev/null || return 0; sleep 1; done
  echo "vLLM did not exit" >&2
  return 1
}

for config in "${CONFIGS[@]}"; do
  candidate=${config%-*}
  case ${config##*-} in think) think=true ;; nothink) think=false ;; *) echo "bad config $config" >&2; exit 2 ;; esac
  if [ -f "$OUT/$config.json" ]; then echo "$config: report exists, skipping"; continue; fi

  stop_server
  echo "$(date +%T) $config: starting vLLM"
  make -C "$HERE" serve CANDIDATE="$candidate" THINK="$think" PORT="$PORT" >"$OUT/logs/$config.serve.log" 2>&1 &
  for _ in $(seq 1 300); do
    curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null && break
    if ! kill -0 $! 2>/dev/null; then echo "$config: vLLM exited, see logs/$config.serve.log" >&2; exit 1; fi
    sleep 2
  done

  echo "$(date +%T) $config: running $LIMIT cases"
  (cd "$PROJECT_A" && AGENT_PROVIDER=openai_compat AGENT_BASE_URL="http://127.0.0.1:$PORT/v1" \
    AGENT_MODEL=candidate uv run evaluate run --set test --limit "$LIMIT" --label "$config" --out "$OUT") \
    >"$OUT/logs/$config.eval.log" 2>&1 || echo "$config: eval failed, see logs/$config.eval.log" >&2
  echo "$(date +%T) $config: done"
done
stop_server
