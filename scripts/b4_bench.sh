#!/usr/bin/env bash
# B4: the whole benchmark from one script. For each configuration it starts a fresh vLLM (the chosen
# model, Qwen3.5-9B 8-bit with thinking off, on the Apple GPU), waits for it, replays the B1 agent
# conversations (data/b4_traces.json) at each concurrency level, and stops it, so no
# configuration inherits another's prefix cache.
#   baseline          the B1 serving flags (prefix caching on, 2048-token prefill chunks)
#   no-prefix-cache   --no-enable-prefix-caching
#   prefill-8k        --max-num-batched-tokens 8192
# Results: eval/b4/<config>.md and .json. Usage: scripts/b4_bench.sh [config ...] (~1 h for all three)
set -euo pipefail

# The plan's levels plus 2 and 8, where one laptop replica saturates. A level where every call
# times out ends the sweep (higher ones would too).
LEVELS=${LEVELS:-1,2,4,8,16,32,64}  # baseline
TUNE_LEVELS=${TUNE_LEVELS:-1,2,4,8}  # tuning configs
DURATION=${DURATION:-180}
PORT=8100
flags() {  # engine flags per configuration (macOS bash 3.2 has no associative arrays)
  case $1 in
    baseline) echo "" ;;
    no-prefix-cache) echo "--no-enable-prefix-caching" ;;
    prefill-8k) echo "--max-num-batched-tokens 8192" ;;
    *) echo "unknown configuration: $1" >&2; exit 1 ;;
  esac
}
if [ $# -gt 0 ]; then CONFIGS="$*"; else CONFIGS="baseline no-prefix-cache prefill-8k"; fi
mkdir -p eval/b4

stop_server() {
  pkill -f "vllm serve .* --port $PORT" 2>/dev/null || true
  while curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; do sleep 1; done
  sleep 5  # let the engine process release GPU memory
}
trap stop_server EXIT

for config in $CONFIGS; do
  extra=$(flags "$config")
  stop_server
  echo "== $config: starting vLLM $extra"
  make serve NAME=qwen3.5-9b EXTRA_ARGS="$extra" > "eval/b4/$config.serve.log" 2>&1 &
  until curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; do sleep 2; done
  uv run selfhost loadtest --base-url "http://127.0.0.1:$PORT/v1" --model qwen3.5-9b \
    --levels "$([ "$config" = baseline ] && echo "$LEVELS" || echo "$TUNE_LEVELS")" --duration "$DURATION" --label "$config"
done
