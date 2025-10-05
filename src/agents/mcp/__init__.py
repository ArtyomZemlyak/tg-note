"""
MCP (Model Context Protocol) support for autonomous agents.

This module provides:
- MCP client for connecting to MCP servers
- Base classes for MCP tools
- Built-in MCP tools (memory agent, etc.)
"""

from .client import MCPClient
from .base_mcp_tool import BaseMCPTool
from .memory_agent_tool import MemoryAgentMCPTool

__all__ = [
    "MCPClient",
    "BaseMCPTool",
    "MemoryAgentMCPTool",
]
