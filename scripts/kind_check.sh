#!/usr/bin/env bash
# B2: check the vLLM chart on kind (make kind-up, then helm install with values-kind.yaml).
#   1. auth: /health is open, the API needs the key
#   2. NetworkPolicy: only Project A's agent pod (namespace ia, app.kubernetes.io/name=agent) connects
#   3. streaming works at the protocol level (several SSE chunks, then [DONE])
#   4. the B1 smoke test, for information only: the 0.8B stand-in's answers vary from run to run,
#      so its content checks don't gate this script (the real model's smoke result is in B1)
set -euo pipefail

NS=${NS:-selfhost}
URL="http://vllm.$NS.svc:8000"
CURL_IMAGE=curlimages/curl:8.16.0
KEY=$(kubectl -n "$NS" get secret vllm-api-key -o jsonpath='{.data.api-key}' | base64 -d)
fail=0

# Prints the HTTP status, or "000" when the connection is refused or times out (NetworkPolicy drop).
probe() {  # namespace, pod label, path, [key]
  local auth=()
  [ -n "${4:-}" ] && auth=(-H "Authorization: Bearer $4")
  local pod="probe-$RANDOM"
  # Run to completion and read the logs: `kubectl run --rm -i` loses the output of pods that
  # finish before it attaches.
  kubectl -n "$1" run "$pod" --image="$CURL_IMAGE" --labels="app.kubernetes.io/name=$2" \
    --restart=Never --command -- \
    curl -s -o /dev/null -w '%{http_code}' --max-time 8 ${auth[@]+"${auth[@]}"} "$URL$3" >/dev/null
  kubectl -n "$1" wait "pod/$pod" --for=jsonpath='{.status.phase}'=Succeeded --timeout=60s >/dev/null 2>&1 ||
    kubectl -n "$1" wait "pod/$pod" --for=jsonpath='{.status.phase}'=Failed --timeout=5s >/dev/null 2>&1 || true
  kubectl -n "$1" logs "$pod" 2>/dev/null || true
  kubectl -n "$1" delete pod "$pod" --wait=false >/dev/null 2>&1 || true
}

check() {  # name, expected, got
  if [ "$3" = "$2" ]; then echo "PASS  $1 ($3)"; else echo "FAIL  $1: expected $2, got $3"; fail=1; fi
}

check "agent pod, /health without key" 200 "$(probe ia agent /health)"
check "agent pod, /v1/models without key" 401 "$(probe ia agent /v1/models)"
check "agent pod, /v1/models with key" 200 "$(probe ia agent /v1/models "$KEY")"
check "other pod in ia, with key (blocked)" 000 "$(probe ia web /v1/models "$KEY")"
check "pod in $NS, with key (blocked)" 000 "$(probe "$NS" debug /v1/models "$KEY")"

# Smoke test through a port-forward (kubectl's tunnel isn't subject to NetworkPolicy, which the
# probes above cover).
kubectl -n "$NS" port-forward svc/vllm 8101:8000 >/dev/null 2>&1 &
pf=$!
trap 'kill $pf 2>/dev/null || true' EXIT
for _ in $(seq 1 20); do curl -sf http://127.0.0.1:8101/health >/dev/null && break; sleep 0.5; done
chunks=$(curl -sN --max-time 60 http://127.0.0.1:8101/v1/chat/completions -H "Authorization: Bearer $KEY" \
  -H 'content-type: application/json' \
  -d '{"model":"qwen3.5-9b","stream":true,"max_tokens":32,"messages":[{"role":"user","content":"Say hello."}]}' |
  grep -c '^data: ' || true)
done_line=$(curl -sN --max-time 60 http://127.0.0.1:8101/v1/chat/completions -H "Authorization: Bearer $KEY" \
  -H 'content-type: application/json' \
  -d '{"model":"qwen3.5-9b","stream":true,"max_tokens":8,"messages":[{"role":"user","content":"Hi"}]}' |
  grep -c '^data: \[DONE\]' || true)
if [ "$chunks" -ge 3 ] && [ "$done_line" -eq 1 ]; then echo "PASS  streaming ($chunks SSE chunks, [DONE])"
else echo "FAIL  streaming: $chunks chunks, [DONE] seen $done_line time(s)"; fail=1; fi

echo "info: B1 smoke test against the 0.8B stand-in (not gating):"
uv run selfhost smoke --base-url http://127.0.0.1:8101/v1 --model qwen3.5-9b --api-key "$KEY" || true

exit $fail
