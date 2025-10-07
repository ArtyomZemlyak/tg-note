"""
MCP Servers Registry

This module provides a registry system for MCP (Model Context Protocol) servers.
It allows dynamic discovery and management of MCP servers through JSON configuration files.

Architecture:
- JSON-based configuration files in data/mcp_servers/
- Dynamic server discovery and registration
- Enable/disable servers through configuration
- Support for both built-in and user-provided MCP servers
"""

from .registry import MCPServerRegistry, MCPServerSpec
from .manager import MCPServersManager

__all__ = [
    "MCPServerRegistry",
    "MCPServerSpec",
    "MCPServersManager",
]