#!/usr/bin/env bash
# Install the serving engine into .venv-engine: vLLM with the vllm-metal plugin (MLX on the Apple
# GPU). Versions are pinned for reproducible results; bump them together (vllm-metal declares its
# matching vLLM in .github/vllm-release-tag.commit). Homebrew's formula needs the newest Xcode,
# so this installs the same prebuilt wheels directly.
set -euo pipefail

VLLM_VERSION="0.30.0"
VLLM_METAL_VERSION="0.30.0"
VENV=".venv-engine"

vllm_wheel="https://github.com/vllm-project/vllm/releases/download/v${VLLM_VERSION}/vllm-${VLLM_VERSION}%2Bcpu-cp312-cp312-macosx_11_0_arm64.whl"
metal_wheel="https://github.com/vllm-project/vllm-metal/releases/download/v${VLLM_METAL_VERSION}/vllm_metal-${VLLM_METAL_VERSION}-cp312-cp312-macosx_15_0_arm64.whl"

uv venv --python 3.12 "$VENV"
VIRTUAL_ENV="$VENV" uv pip install "$vllm_wheel"
VIRTUAL_ENV="$VENV" uv pip install "$metal_wheel"
"$VENV/bin/vllm" --version
