#!/usr/bin/env bash
# B2: time the vLLM pod from creation to Ready on kind, with and without the weight cache.
#   cold     new, empty cache volume: download + load
#   warm     pod replaced, volume kept: load from disk (Hugging Face still checked for updates)
#   offline  as warm, with HF_HUB_OFFLINE=1: no network at all
# The node already has the image, so image pull time (measured separately) isn't included.
set -euo pipefail

NS=${NS:-selfhost}
CHART=deploy/helm/vllm
VALUES=(-f "$CHART/values-kind.yaml")

ready_seconds() {  # seconds from the current pod's creation to its Ready condition
  kubectl -n "$NS" rollout status deploy/vllm --timeout=900s >/dev/null
  local pod created ready
  pod=$(kubectl -n "$NS" get pod -l app.kubernetes.io/name=vllm -o jsonpath='{.items[0].metadata.name}')
  created=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.metadata.creationTimestamp}')
  ready=$(kubectl -n "$NS" get pod "$pod" \
    -o jsonpath='{.status.conditions[?(@.type=="Ready")].lastTransitionTime}')
  echo $(( $(date -j -u -f %Y-%m-%dT%H:%M:%SZ "$ready" +%s) - $(date -j -u -f %Y-%m-%dT%H:%M:%SZ "$created" +%s) ))
}

fetch_seconds() {  # how long the fetch-weights init container ran
  local t
  t=$(kubectl -n "$NS" get pod -l app.kubernetes.io/name=vllm \
    -o jsonpath='{.items[0].status.initContainerStatuses[0].state.terminated.startedAt} {.items[0].status.initContainerStatuses[0].state.terminated.finishedAt}')
  set -- $t
  [ $# -eq 2 ] || { echo "-"; return; }
  echo $(( $(date -j -u -f %Y-%m-%dT%H:%M:%SZ "$2" +%s) - $(date -j -u -f %Y-%m-%dT%H:%M:%SZ "$1" +%s) ))
}

restarts() {
  kubectl -n "$NS" get pod -l app.kubernetes.io/name=vllm -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}'
}

# cold: remove the release and its kept volume, then install fresh
helm -n "$NS" uninstall vllm --wait >/dev/null 2>&1 || true
kubectl -n "$NS" delete pvc vllm-cache --wait=true >/dev/null 2>&1 || true
helm -n "$NS" install vllm "$CHART" "${VALUES[@]}" >/dev/null
echo "cold     $(ready_seconds) s to Ready, of which weight fetch $(fetch_seconds) s (restarts: $(restarts))"

# warm: replace the pod, keep the volume
kubectl -n "$NS" delete pod -l app.kubernetes.io/name=vllm --wait=true >/dev/null
echo "warm     $(ready_seconds) s to Ready, of which weight fetch $(fetch_seconds) s (restarts: $(restarts))"

# offline: same, without contacting Hugging Face
helm -n "$NS" upgrade vllm "$CHART" "${VALUES[@]}" --set cache.offline=true >/dev/null
echo "offline  $(ready_seconds) s to Ready, of which weight fetch $(fetch_seconds) s (restarts: $(restarts))"
helm -n "$NS" upgrade vllm "$CHART" "${VALUES[@]}" >/dev/null
