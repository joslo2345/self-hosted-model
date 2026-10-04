#!/usr/bin/env bash
# B3: spike test on kind. Needs the chart installed with values-kind.yaml and `make monitoring-up`.
# Port-forwards vLLM and Prometheus on 127.0.0.1 only, then runs `selfhost spike`:
#   baseline 60 s at 0.05 req/s, spike 180 s at 0.4 req/s (the CPU stand-in serves ~0.23 req/s),
#   recovery 120 s at 0.05 req/s, then 3 more minutes of sampling to see the scale-down.
# Results: eval/b3/spike.md (summary) and eval/b3/spike.json (every request and sample).
set -euo pipefail

NS=${NS:-selfhost}
PHASES=${PHASES:-60:0.05,180:0.4,120:0.05}
KEY=$(kubectl -n "$NS" get secret vllm-api-key -o jsonpath='{.data.api-key}' | base64 -d)
WAITING_TARGET=$(kubectl -n "$NS" get scaledobject vllm -o jsonpath='{.spec.triggers[0].metadata.threshold}')

kubectl -n "$NS" port-forward --address 127.0.0.1 svc/vllm 8101:8000 >/dev/null 2>&1 &
pf_vllm=$!
kubectl -n monitoring port-forward --address 127.0.0.1 svc/prometheus-server 9091:80 >/dev/null 2>&1 &
pf_prom=$!
trap 'kill $pf_vllm $pf_prom 2>/dev/null || true' EXIT
for _ in $(seq 1 20); do
  curl -sf http://127.0.0.1:8101/health >/dev/null && curl -sf http://127.0.0.1:9091/-/ready >/dev/null && break
  sleep 0.5
done

uv run selfhost spike --base-url http://127.0.0.1:8101/v1 --model qwen3.5-9b --api-key "$KEY" \
  --phases "$PHASES" --namespace "$NS" --prometheus-url http://127.0.0.1:9091 \
  --waiting-target "$WAITING_TARGET" --out eval/b3/spike
