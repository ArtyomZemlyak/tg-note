#!/bin/bash
# LM Studio CLI helper for downloading and loading the mem-agent model
# Requires: macOS on Apple Silicon (arm64), LM Studio installed and launched once to enable lms CLI

set -euo pipefail

OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"

if [[ "$OS_NAME" != "Darwin" || "$ARCH_NAME" != "arm64" ]]; then
  echo "This script is intended for macOS on Apple Silicon (arm64)."
  echo "Detected: ${OS_NAME} ${ARCH_NAME}"
  exit 1
fi

# Defaults
LMS_MODEL_ID="${LMS_MODEL_ID:-driaforall/mem-agent-mlx-4bit}"
LMS_LOAD_NAME="${LMS_LOAD_NAME:-mem-agent-mlx}"
LMSTUDIO_HOST="${LMSTUDIO_HOST:-127.0.0.1}"
LMSTUDIO_PORT="${LMSTUDIO_PORT:-1234}"
BASE_URL="http://${LMSTUDIO_HOST}:${LMSTUDIO_PORT}/v1"

# Parse args: --model and --load-name override env defaults
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      shift; LMS_MODEL_ID="${1:-$LMS_MODEL_ID}";;
    --load-name)
      shift; LMS_LOAD_NAME="${1:-$LMS_LOAD_NAME}";;
    --host)
      shift; LMSTUDIO_HOST="${1:-$LMSTUDIO_HOST}"; BASE_URL="http://${LMSTUDIO_HOST}:${LMSTUDIO_PORT}/v1";;
    --port)
      shift; LMSTUDIO_PORT="${1:-$LMSTUDIO_PORT}"; BASE_URL="http://${LMSTUDIO_HOST}:${LMSTUDIO_PORT}/v1";;
    -h|--help)
      echo "Usage: $0 [--model driaforall/mem-agent-mlx-4bit] [--load-name mem-agent-mlx] [--host 127.0.0.1] [--port 1234]"; exit 0;;
    *) echo "Unknown argument: $1"; exit 1;;
  esac
  shift
done

# Ensure lms CLI is available
if ! command -v lms >/dev/null 2>&1; then
  echo "The 'lms' CLI is not available. Launch LM Studio once to enable it."
  echo "Opening LM Studio..."
  open -a "LM Studio" >/dev/null 2>&1 || true
  exit 1
fi

# Open LM Studio (non-fatal) to ensure background services are up
open -a "LM Studio" >/dev/null 2>&1 || true

# Download the model (non-fatal if already present)
echo "Downloading model: ${LMS_MODEL_ID}"
if ! lms get "${LMS_MODEL_ID}"; then
  echo "Continuing even if download step reports already downloaded."
fi

# Load the model into LM Studio
# Try canonical ID, then slug fallback (basename), then provided load name
MODEL_BASENAME="${LMS_MODEL_ID##*/}"
if ! lms load "${LMS_MODEL_ID}"; then
  if ! lms load "${MODEL_BASENAME}"; then
    lms load "${LMS_LOAD_NAME}"
  fi
fi

echo "Setting environment for mem-agent:"
export MEM_AGENT_BASE_URL="$BASE_URL"
export MEM_AGENT_OPENAI_API_KEY="${MEM_AGENT_OPENAI_API_KEY:-lm-studio}"

echo "  MEM_AGENT_BASE_URL=$MEM_AGENT_BASE_URL"
echo "  MEM_AGENT_OPENAI_API_KEY=$MEM_AGENT_OPENAI_API_KEY"

# Verify server readiness
ATTEMPTS=20
SLEEP_SECS=1
READY=0
for ((i=1; i<=ATTEMPTS; i++)); do
  if curl -s "${BASE_URL}/models" >/dev/null 2>&1; then
    READY=1; break
  fi
  sleep "$SLEEP_SECS"
done

if [[ "$READY" -eq 1 ]]; then
  echo "✅ LM Studio server is reachable at ${BASE_URL}"
  echo "   Model should now be available to mem-agent."
else
  echo "⚠️ Could not reach ${BASE_URL}."
  echo "   Ensure LM Studio's OpenAI-compatible server is enabled (Settings -> Developer)."
  echo "   If running app in Docker on macOS, use --host host.docker.internal."
fi
