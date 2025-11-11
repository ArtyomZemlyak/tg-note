#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-run}"
shift || true

SETTINGS_PATH="${DOCLING_SETTINGS_PATH:-/opt/docling-mcp/config.yaml}"
SETTINGS_DIR="$(dirname "${SETTINGS_PATH}")"

# AICODE-NOTE: Ensure all required directories exist before starting service
mkdir -p "${SETTINGS_DIR}" \
    "${DOCLING_MODELS_DIR:-/opt/docling-mcp/models}" \
    "${DOCLING_LOG_DIR:-/opt/docling-mcp/logs}" \
    "${DOCLING_CACHE_DIR:-/opt/docling-mcp/cache}" \
    "${HF_HOME:-/opt/docling-mcp/cache/huggingface}"

# AICODE-NOTE: Clean up stale lock files from previous interrupted downloads
# This prevents infinite hangs when container was killed during model download
echo "🧹 Cleaning up stale lock files..."
find "${DOCLING_MODELS_DIR:-/opt/docling-mcp/models}" -name "*.lock" -type f -delete 2>/dev/null || true
find "${HF_HOME:-/opt/docling-mcp/cache/huggingface}" -name "*.lock" -type f -delete 2>/dev/null || true
echo "✅ Lock files cleaned"

export PYTHONUNBUFFERED=1

if [[ ! -f "${SETTINGS_PATH}" ]]; then
    echo "⚠️  Docling settings file not found at ${SETTINGS_PATH}" >&2
fi

case "${COMMAND}" in
    run)
        exec python -m tg_docling.server "$@"
        ;;
    sync-models)
        exec python -m tg_docling.model_sync "$@"
        ;;
    *)
        exec "${COMMAND}" "$@"
        ;;
esac
