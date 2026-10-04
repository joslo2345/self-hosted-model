#!/usr/bin/env bash
# B5: kill the self-hosted model mid-run and check the agent finishes on the fallback.
# Runs Project A's eval (first LIMIT test incidents) from a checkout with the fallback provider
# (PROJECT_A_FALLBACK, branch b5-fallback), configured through environment only:
#   primary   vLLM, Qwen3.5-9B (this repo's `make serve`)
#   fallback  local Ollama qwen3-agent, standing in for the hosted API ($0; same code path,
#             only the endpoint differs)
# KILL_AFTER seconds into the run, vLLM is killed. Needs Project A's stack (`make up`) and Ollama.
set -euo pipefail

HERE=$(cd "$(dirname "$0")/.." && pwd)
PROJECT_A=${PROJECT_A_FALLBACK:-$(cd "$HERE/../../project-a/incident-assistant-b5" && pwd)}
OUT=$HERE/eval/b5
LIMIT=${LIMIT:-4}
KILL_AFTER=${KILL_AFTER:-90}
PORT=8100
mkdir -p "$OUT/logs"

pkill -f "vllm serve .* --port $PORT" 2>/dev/null || true
make -C "$HERE" serve NAME=qwen3.5-9b > "$OUT/logs/fallback.serve.log" 2>&1 &
until curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; do sleep 2; done
curl -sf http://127.0.0.1:11434/api/version >/dev/null || { echo "start Ollama first" >&2; exit 1; }

echo "$(date +%T) running $LIMIT incidents; vLLM is killed after ${KILL_AFTER}s"
(cd "$PROJECT_A" && AGENT_PROVIDER=openai_compat AGENT_BASE_URL="http://127.0.0.1:$PORT/v1" \
  AGENT_MODEL=qwen3.5-9b AGENT_FALLBACK_PROVIDER=openai_compat \
  AGENT_FALLBACK_BASE_URL=http://127.0.0.1:11434/v1 AGENT_FALLBACK_MODEL=qwen3-agent \
  AGENT_FALLBACK_AFTER_S=120 \
  uv run --frozen evaluate run --set test --limit "$LIMIT" --label fallback --out "$OUT") \
  > "$OUT/logs/fallback.eval.log" 2>&1 &
eval_pid=$!
sleep "$KILL_AFTER"
echo "$(date +%T) killing vLLM"
pkill -9 -f "$HERE/.venv-engine" || true  # the server and its engine processes
wait $eval_pid
echo "$(date +%T) eval finished"
