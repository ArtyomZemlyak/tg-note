#!/bin/bash
# Helper script to launch and integrate LM Studio on macOS (Apple Silicon)
# - Opens LM Studio
# - Exports env vars for mem-agent to use LM Studio's OpenAI-compatible server
# - Verifies server readiness

set -euo pipefail

OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"

if [[ "$OS_NAME" != "Darwin" || "$ARCH_NAME" != "arm64" ]]; then
  echo "This script is intended for macOS on Apple Silicon (arm64)."
  echo "Detected: ${OS_NAME} ${ARCH_NAME}"
  exit 1
fi

 LMSTUDIO_PORT="${LMSTUDIO_PORT:-1234}"
 LMSTUDIO_HOST="${LMSTUDIO_HOST:-127.0.0.1}"
 # If you are connecting from inside Docker containers on macOS, use:
 #   export LMSTUDIO_HOST=host.docker.internal
 BASE_URL="http://${LMSTUDIO_HOST}:${LMSTUDIO_PORT}/v1"

# Export env vars for current shell session
export MEM_AGENT_BASE_URL="$BASE_URL"
export MEM_AGENT_OPENAI_API_KEY="${MEM_AGENT_OPENAI_API_KEY:-lm-studio}"

cat <<EOF
========================================
LM Studio Integration for mem-agent
========================================

1) Launch LM Studio (if not already running):
   open -a "LM Studio"

2) In LM Studio:
   - Download the desired model (e.g., driaforall/mem-agent or a compatible variant)
   - Open Settings -> Developer -> Enable "OpenAI-compatible server"
   - Ensure the server is listening on port ${LMSTUDIO_PORT}

3) Environment configured for mem-agent:
   MEM_AGENT_BASE_URL=$MEM_AGENT_BASE_URL
   MEM_AGENT_OPENAI_API_KEY=$MEM_AGENT_OPENAI_API_KEY
   (Tip: If running the app in Docker, set LMSTUDIO_HOST=host.docker.internal before running this script.)

4) Verifying server...
EOF

# Try to open LM Studio (non-fatal if it fails)
open -a "LM Studio" >/dev/null 2>&1 || true

# Wait briefly and check readiness
ATTEMPTS=10
SLEEP_SECS=1
READY=0
for ((i=1; i<=ATTEMPTS; i++)); do
  if curl -s "${BASE_URL}/models" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep "$SLEEP_SECS"
done

if [[ "$READY" -eq 1 ]]; then
  echo "✅ LM Studio server is reachable at ${BASE_URL}"
  echo "You can now start the app or tests that rely on mem-agent."
else
  echo "⚠️ Could not reach ${BASE_URL}."
  echo "Please ensure LM Studio is running and the OpenAI server is enabled on port ${LMSTUDIO_PORT}."
fi
