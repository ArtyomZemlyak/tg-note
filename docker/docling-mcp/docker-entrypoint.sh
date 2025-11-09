#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-run}"
shift || true

SETTINGS_PATH="${DOCLING_SETTINGS_PATH:-/opt/docling-mcp/config.yaml}"
SETTINGS_DIR="$(dirname "${SETTINGS_PATH}")"

mkdir -p "${SETTINGS_DIR}" \
    "${DOCLING_MODELS_DIR:-/opt/docling-mcp/models}" \
    "${DOCLING_LOG_DIR:-/opt/docling-mcp/logs}" \
    "${DOCLING_CACHE_DIR:-/opt/docling-mcp/cache}"

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
