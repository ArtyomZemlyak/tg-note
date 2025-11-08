#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-run}"
shift || true

CONFIG_PATH="${DOCLING_CONFIG_PATH:-/opt/docling-mcp/config/docling-config.json}"
CONFIG_DIR="$(dirname "${CONFIG_PATH}")"

mkdir -p "${CONFIG_DIR}" \
    "${DOCLING_MODELS_DIR:-/opt/docling-mcp/models}" \
    "${DOCLING_LOG_DIR:-/opt/docling-mcp/logs}" \
    "${DOCLING_CACHE_DIR:-/opt/docling-mcp/cache}"

export PYTHONUNBUFFERED=1

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
