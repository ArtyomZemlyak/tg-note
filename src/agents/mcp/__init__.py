"""
MCP (Model Context Protocol) support for autonomous agents.

This module provides:
- MCP client for connecting to MCP servers
- MCP registry client for discovering servers from configuration
- Base classes for MCP tools
- Built-in MCP tools (memory agent, etc.)
- Dynamic MCP tools for auto-discovery and integration
- Qwen native MCP configuration generator

Two integration approaches:
1. Python MCP Client (for AutonomousAgent)
   - DynamicMCPTool, MCPClient, MCPRegistryClient
   - MCP servers managed from Python code
   
2. Qwen Native MCP (for QwenCodeCLIAgent)
   - QwenMCPConfigGenerator, mem_agent_server
   - MCP servers configured in .qwen/settings.json
   - Standalone server processes
"""

from .client import MCPClient, MCPServerConfig
from .registry_client import MCPRegistryClient
from .base_mcp_tool import BaseMCPTool
from .memory.memory_tool import MemoryMCPTool
from .dynamic_mcp_tools import (
    discover_and_create_mcp_tools,
    create_mcp_tools_for_user,
    DynamicMCPTool,
)
from .tools_description import get_mcp_tools_description, format_mcp_tools_for_prompt
from .qwen_config_generator import QwenMCPConfigGenerator, setup_qwen_mcp_config
from .server_manager import MCPServerManager, get_server_manager, set_server_manager

__all__ = [
    # Python MCP Client
    "MCPClient",
    "MCPServerConfig",
    "MCPRegistryClient",
    "BaseMCPTool",
    "MemoryMCPTool",
    "discover_and_create_mcp_tools",
    "create_mcp_tools_for_user",
    "DynamicMCPTool",
    "get_mcp_tools_description",
    "format_mcp_tools_for_prompt",
    
    # Qwen Native MCP
    "QwenMCPConfigGenerator",
    "setup_qwen_mcp_config",
    
    # Server Manager
    "MCPServerManager",
    "get_server_manager",
    "set_server_manager",
]