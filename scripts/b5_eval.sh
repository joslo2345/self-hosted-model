#!/usr/bin/env bash
# B5: Project A's full A6 eval (test set, 25 incidents) on the self-hosted model. Project A's code is
# unchanged: only its provider settings point at the local vLLM server (the config-only switch).
# Needs Project A's stack running (`make up` there). The citation judge needs Ollama's memory, so
# it runs afterwards with `evaluate rejudge` (see README).
set -euo pipefail

HERE=$(cd "$(dirname "$0")/.." && pwd)
PROJECT_A=${PROJECT_A:-$(cd "$HERE/../../project-a/incident-assistant" && pwd)}
OUT=$HERE/eval/b5
LABEL=${LABEL:-selfhosted}
PORT=8100
mkdir -p "$OUT/logs"

stop_server() {
  pkill -f "vllm serve .* --port $PORT" 2>/dev/null || true
  while curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; do sleep 1; done
}
trap stop_server EXIT

stop_server
make -C "$HERE" serve NAME=qwen3.5-9b > "$OUT/logs/$LABEL.serve.log" 2>&1 &
until curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; do sleep 2; done
echo "$(date +%T) running the test set"
(cd "$PROJECT_A" && AGENT_PROVIDER=openai_compat AGENT_BASE_URL="http://127.0.0.1:$PORT/v1" \
  AGENT_MODEL=qwen3.5-9b uv run --frozen evaluate run --set test --label "$LABEL" --out "$OUT") \
  > "$OUT/logs/$LABEL.eval.log" 2>&1
echo "$(date +%T) done"
