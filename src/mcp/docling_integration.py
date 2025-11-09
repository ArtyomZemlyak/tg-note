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
from typing import Any, Callable, Dict, Optional

from loguru import logger

from config.settings import DoclingSettings

# AICODE-NOTE: Global callback for sending model sync progress to external systems (e.g., Telegram)
_docling_sync_notification_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None


def set_docling_sync_notification_callback(
    callback: Optional[Callable[[str, Dict[str, Any]], None]],
) -> None:
    """
    Register a callback to receive Docling model sync notifications.

    The callback receives:
        - message (str): Human-readable progress message
        - data (Dict[str, Any]): Structured data about the sync operation

    This is used to forward model download progress to external systems like Telegram.
    """
    global _docling_sync_notification_callback
    _docling_sync_notification_callback = callback


def get_docling_sync_notification_callback() -> Optional[Callable[[str, Dict[str, Any]], None]]:
    """Return the currently registered Docling sync notification callback."""
    return _docling_sync_notification_callback


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
    return spec_path
