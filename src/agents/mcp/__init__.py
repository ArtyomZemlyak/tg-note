"""
MCP (Model Context Protocol) support for autonomous agents.

This module provides:
- MCP client for connecting to MCP servers
- MCP registry client for discovering servers from configuration
- Base classes for MCP tools
- Built-in MCP tools (memory agent, etc.)
- Dynamic MCP tools for auto-discovery and integration
"""

from .client import MCPClient, MCPServerConfig
from .registry_client import MCPRegistryClient
from .base_mcp_tool import BaseMCPTool
from .memory_agent_tool import MemoryAgentMCPTool
from .dynamic_mcp_tools import (
    discover_and_create_mcp_tools,
    create_mcp_tools_for_user,
    DynamicMCPTool,
)
from .tools_description import get_mcp_tools_description, format_mcp_tools_for_prompt

__all__ = [
    "MCPClient",
    "MCPServerConfig",
    "MCPRegistryClient",
    "BaseMCPTool",
    "MemoryAgentMCPTool",
    "discover_and_create_mcp_tools",
    "create_mcp_tools_for_user",
    "DynamicMCPTool",
    "get_mcp_tools_description",
    "format_mcp_tools_for_prompt",
]
