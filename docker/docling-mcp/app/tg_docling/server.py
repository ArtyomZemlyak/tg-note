from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import List

from docling_mcp.servers.mcp_server import (
    ToolGroups,
    TransportType,
)
from docling_mcp.servers.mcp_server import main as mcp_main
from docling_mcp.shared import mcp
from tg_docling.config import ContainerConfig, ensure_config_file, load_config
from tg_docling.converter import install_converter
from tg_docling.logging import configure_logging
from tg_docling.model_sync import sync_models

from mcp.types import ToolAnnotations

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(os.getenv("DOCLING_CONFIG_PATH", "/opt/docling-mcp/config/docling-config.json"))


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


def _run_startup_sync(config: ContainerConfig) -> None:
    if not config.startup_sync:
        logger.info("Startup model sync disabled by configuration")
        return

    logger.info("Running startup model synchronisation")
    result = sync_models(config, force=False)
    logger.debug("Startup sync result: %s", json.dumps(result, indent=2))


def _apply_env_overrides(config: ContainerConfig) -> ContainerConfig:
    models_dir = os.getenv("DOCLING_MODELS_DIR")
    if models_dir:
        config.model_cache.base_dir = Path(models_dir)
    return config


def _load_and_apply_config() -> ContainerConfig:
    config_file = ensure_config_file(CONFIG_PATH)
    config = _apply_env_overrides(load_config(config_file))
    install_converter(config)
    return config


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
        config = _load_and_apply_config()
        result = sync_models(config, force=force)
        return {"success": True, "force": force, "result": result}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Docling model sync failed")
        return {"success": False, "force": force, "error": str(exc)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Docling MCP container entrypoint")
    parser.add_argument(
        "--config",
        type=str,
        default=str(CONFIG_PATH),
        help="Path to Docling container configuration file",
    )
    parser.add_argument(
        "--no-startup-sync",
        action="store_true",
        help="Skip model download during container startup",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global CONFIG_PATH
    CONFIG_PATH = Path(args.config)

    log_dir = os.getenv("DOCLING_LOG_DIR", "/opt/docling-mcp/logs")
    configure_logging(os.getenv("DOCLING_LOG_LEVEL", "INFO"), log_dir=log_dir)

    config = _load_and_apply_config()

    if not args.no_startup_sync:
        _run_startup_sync(config)

    tool_names = config.mcp.tools
    selected_tools = _normalise_tool_names(tool_names)
    if not selected_tools:
        logger.warning(
            "No valid tool groups configured, defaulting to conversion/generation/manipulation"
        )
        selected_tools = _normalise_tool_names(["conversion", "generation", "manipulation"])

    logger.info(
        "Starting Docling MCP server (transport=%s, host=%s, port=%s, tools=%s)",
        config.mcp.transport,
        config.mcp.host,
        config.mcp.port,
        [tool.value for tool in selected_tools],
    )

    try:
        transport = TransportType(config.mcp.transport)
    except ValueError:
        logger.warning("Unknown transport '%s', defaulting to 'sse'", config.mcp.transport)
        transport = TransportType.SSE

    mcp_main(
        transport=transport,
        host=config.mcp.host,
        port=config.mcp.port,
        tools=selected_tools,
    )


if __name__ == "__main__":
    main()
