from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import List

import tg_docling.tools  # noqa: F401  # Register additional MCP tools
from docling_mcp.servers.mcp_server import ToolGroups, TransportType
from docling_mcp.servers.mcp_server import main as mcp_main
from docling_mcp.shared import mcp
from tg_docling.config import DEFAULT_SETTINGS_PATH, load_docling_settings
from tg_docling.converter import install_converter
from tg_docling.logging import configure_logging
from tg_docling.model_sync import sync_models

from config.settings import DoclingSettings, Settings
from mcp.types import ToolAnnotations

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path(os.getenv("DOCLING_SETTINGS_PATH", str(DEFAULT_SETTINGS_PATH)))


def _normalise_tool_names(names: List[str]) -> List[ToolGroups]:
    """Map user-facing names to ToolGroups enum."""
    mapping = {item.value: item for item in ToolGroups}
    resolved: List[ToolGroups] = []
    for name in names:
        key = name.lower().strip()
        if key in mapping:
            resolved.append(mapping[key])
        else:
            logger.warning("Unknown Docling tool group requested: %s", name)
    return resolved


def _run_startup_sync(settings: DoclingSettings) -> None:
    if not settings.startup_sync:
        logger.info("Startup model sync disabled by configuration")
        return

    logger.info("Running startup model synchronisation")
    result = sync_models(settings, force=False)
    logger.debug("Startup sync result: %s", json.dumps(result, indent=2))


def _apply_env_overrides(settings: DoclingSettings) -> DoclingSettings:
    models_dir_override = os.getenv("DOCLING_MODELS_DIR")
    if models_dir_override:
        settings.model_cache.base_dir = models_dir_override

    models_dir = Path(settings.model_cache.base_dir)
    os.environ.setdefault("DOCLING_MODELS_DIR", str(models_dir))
    os.environ.setdefault(
        "DOCLING_CACHE_DIR", os.getenv("DOCLING_CACHE_DIR", "/opt/docling-mcp/cache")
    )
    os.environ.setdefault("DOCLING_ARTIFACTS_PATH", str(models_dir))
    return settings


def _load_and_apply_settings() -> tuple[DoclingSettings, Settings]:
    docling_settings, app_settings = load_docling_settings(SETTINGS_PATH)
    docling_settings = _apply_env_overrides(docling_settings)
    install_converter(docling_settings)
    return docling_settings, app_settings


@mcp.tool(
    title="Synchronise Docling Models",
    description="Download or refresh model artefacts required by the Docling pipelines.",
    structured_output=True,
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
def sync_docling_models(force: bool = False) -> dict:
    """
    MCP tool for triggering model downloads from within the container.

    Args:
        force: When True existing model directories will be redownloaded.
    """
    try:
        docling_settings, _ = _load_and_apply_settings()
        result = sync_models(docling_settings, force=force)
        return {"success": True, "force": force, "result": result}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Docling model sync failed")
        return {"success": False, "force": force, "error": str(exc)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Docling MCP container entrypoint")
    parser.add_argument(
        "--settings",
        type=str,
        default=str(SETTINGS_PATH),
        help="Path to tg-note settings YAML",
    )
    parser.add_argument(
        "--no-startup-sync",
        action="store_true",
        help="Skip model download during container startup",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global SETTINGS_PATH
    SETTINGS_PATH = Path(args.settings)

    docling_settings, app_settings = _load_and_apply_settings()

    log_dir = os.getenv("DOCLING_LOG_DIR", "/opt/docling-mcp/logs")
    configure_logging(os.getenv("DOCLING_LOG_LEVEL", app_settings.LOG_LEVEL), log_dir=log_dir)

    if not args.no_startup_sync:
        _run_startup_sync(docling_settings)

    tool_names = docling_settings.mcp.tool_groups
    selected_tools = _normalise_tool_names(tool_names)
    if not selected_tools:
        logger.warning(
            "No valid tool groups configured, defaulting to conversion/generation/manipulation"
        )
        selected_tools = _normalise_tool_names(["conversion", "generation", "manipulation"])

    logger.info(
        "Starting Docling MCP server (transport=%s, host=%s, port=%s, tools=%s)",
        docling_settings.mcp.transport,
        docling_settings.mcp.listen_host,
        docling_settings.mcp.listen_port,
        [tool.value for tool in selected_tools],
    )

    try:
        transport = TransportType(docling_settings.mcp.transport)
    except ValueError:
        logger.warning(
            "Unknown transport '%s', defaulting to 'sse'", docling_settings.mcp.transport
        )
        transport = TransportType.SSE

    mcp_main(
        transport=transport,
        host=docling_settings.mcp.listen_host,
        port=docling_settings.mcp.listen_port,
        tools=selected_tools,
    )


if __name__ == "__main__":
    main()
