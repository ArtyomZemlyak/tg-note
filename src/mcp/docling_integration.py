"""
Docling MCP Integration Helpers

Provides utilities to synchronise Docling MCP server configuration with the
local MCP registry (data/mcp_servers). This ensures the Docling MCP server
definition is available for both the MCP Hub and other components (e.g.,
FileProcessor) without requiring manual configuration.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from config.settings import DoclingSettings


def _build_docling_mcp_spec(docling_settings: DoclingSettings) -> Optional[Dict[str, Any]]:
    """
    Build a Docling MCP server specification dictionary.

    Returns:
        Spec dictionary compatible with MCPServerSpec/to_dict or None if the
        configuration is insufficient to describe the server.
    """
    mcp_cfg = docling_settings.mcp
    transport = mcp_cfg.transport or "stdio"
    enabled = bool(docling_settings.use_mcp())

    spec: Dict[str, Any] = {
        "name": mcp_cfg.server_name or "docling",
        "description": "Docling document processing MCP server",
        "transport": transport,
        "enabled": enabled,
    }

    # Include timeout override when provided
    if mcp_cfg.timeout is not None:
        spec["timeout"] = mcp_cfg.timeout

    if transport == "sse":
        url = mcp_cfg.resolve_url()
        if url:
            spec["url"] = url
        else:
            if enabled:
                logger.warning(
                    "[DoclingMCP] Docling MCP backend enabled but no URL could be resolved. "
                    "Set MEDIA_PROCESSING_DOCLING.mcp.url or DOCLING_MCP_URL."
                )
                return None
    elif transport == "stdio":
        command = mcp_cfg.command
        if not command:
            if enabled:
                logger.warning(
                    "[DoclingMCP] Docling MCP backend enabled with stdio transport but no command configured."
                )
                return None
        else:
            spec["command"] = command

        if mcp_cfg.args:
            spec["args"] = mcp_cfg.args
        if mcp_cfg.env:
            spec["env"] = mcp_cfg.env
        if mcp_cfg.working_dir:
            spec["working_dir"] = mcp_cfg.working_dir
    else:
        logger.warning(
            "[DoclingMCP] Unknown transport '%s' for Docling MCP server. Supported: sse, stdio",
            transport,
        )
        return None

    return spec


def _write_json_if_changed(path: Path, payload: Dict[str, Any]) -> None:
    """
    Write JSON payload to path if content differs from existing file.
    """
    try:
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing == payload:
                return
    except Exception:
        logger.debug("[DoclingMCP] Failed to read existing spec at %s, will overwrite.", path)

    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("[DoclingMCP] Wrote MCP server spec: %s", path)


def write_docling_container_config(
    docling_settings: DoclingSettings,
    config_dir: Optional[Path] = None,
    log_level: Optional[str] = None,
) -> Optional[Path]:
    """
    Write Docling container configuration JSON based on application settings.
    """

    if config_dir is None:
        env_dir = os.getenv("DOCLING_CONTAINER_CONFIG_DIR")
        config_dir = Path(env_dir) if env_dir else Path("data/docling/config")

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.error("[DoclingMCP] Failed to prepare container config directory %s: %s", config_dir, exc)
        return None

    config_path = config_dir / "docling-config.json"
    payload = docling_settings.to_container_config(
        log_level=log_level or os.getenv("DOCLING_LOG_LEVEL", "INFO")
    )
    _write_json_if_changed(config_path, payload)
    return config_path


def ensure_docling_mcp_spec(
    docling_settings: DoclingSettings, servers_dir: Optional[Path] = None
) -> Optional[Path]:
    """
    Ensure Docling MCP server specification file exists/updated.

    Args:
        docling_settings: Resolved Docling configuration from application settings.
        servers_dir: Optional custom directory for MCP server specs.

    Returns:
        Path to the spec file if written, otherwise None.
    """
    spec = _build_docling_mcp_spec(docling_settings)
    if spec is None:
        return None

    if servers_dir is None:
        servers_dir = Path("data/mcp_servers")

    servers_dir.mkdir(parents=True, exist_ok=True)

    spec_path = servers_dir / f"{spec['name']}.json"
    _write_json_if_changed(spec_path, spec)
    write_docling_container_config(docling_settings)
    return spec_path
