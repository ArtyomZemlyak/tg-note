"""
Memory Agent MCP Tool

This tool integrates the local mem-agent MCP server for memory management.

The memory agent uses the driaforall/mem-agent model from HuggingFace
to provide intelligent memory storage and retrieval for autonomous agents.

The MCP server configuration is loaded from data/mcp_servers/mem-agent.json
which is created by running scripts/install_mem_agent.py.

References:
- Model: https://huggingface.co/driaforall/mem-agent
- Installation: scripts/install_mem_agent.py
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from .base_mcp_tool import BaseMCPTool
from .client import MCPServerConfig


class MemoryAgentMCPTool(BaseMCPTool):
    """
    Memory Agent MCP Tool
    
    This tool provides intelligent memory management using the mem-agent model.
    It can store, retrieve, and search through memories with semantic understanding.
    
    Usage:
        - Store memories: Save information for later retrieval
        - Search memories: Find relevant memories based on queries
        - Manage context: Maintain conversation context across sessions
    """
    
    @property
    def name(self) -> str:
        return "mcp_memory_agent"
    
    @property
    def description(self) -> str:
        return (
            "Intelligent memory management tool. "
            "Can store and retrieve memories with semantic understanding. "
            "Use this to remember important information across tasks and sessions. "
            "Supports: storing memories, searching memories, and managing context."
        )
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["store", "search", "list"],
                    "description": "Action to perform: store (save memory), search (find memories), list (show all memories)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to store (for 'store' action) or query (for 'search' action)"
                },
                "context": {
                    "type": "string",
                    "description": "Optional context or metadata for the memory"
                }
            },
            "required": ["action"]
        }
    
    @property
    def mcp_server_config(self) -> MCPServerConfig:
        """
        Load MCP server configuration from data/mcp_servers/mem-agent.json
        
        The configuration is created by running scripts/install_mem_agent.py
        and contains the command, args, and environment variables for the
        local Python-based mem-agent MCP server.
        
        Note: The KB_PATH environment variable is set dynamically at runtime
        in the execute() method, as it's user-specific.
        """
        config_file = Path("data/mcp_servers/mem-agent.json")
        
        if not config_file.exists():
            logger.warning(
                f"[MemoryAgentMCPTool] Config file not found: {config_file}. "
                "Run 'python scripts/install_mem_agent.py' to set up the memory agent."
            )
            # Return a default config that won't work but won't crash
            return MCPServerConfig(
                command="python",
                args=["-m", "src.mem_agent.server"],
                env={}
            )
        
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            return MCPServerConfig(
                command=config_data.get("command", "python"),
                args=config_data.get("args", ["-m", "src.mem_agent.server"]),
                env=config_data.get("env", {}),
                cwd=Path(config_data["working_dir"]) if config_data.get("working_dir") else None
            )
        except Exception as e:
            logger.error(f"[MemoryAgentMCPTool] Failed to load config from {config_file}: {e}")
            # Return a default config
            return MCPServerConfig(
                command="python",
                args=["-m", "src.mem_agent.server"],
                env={}
            )
    
    @property
    def mcp_tool_name(self) -> str:
        """
        The tool name in the MCP server
        
        Note: This depends on how the mem-agent-mcp server exposes its tools.
        Common names might be: 'memory', 'store_memory', 'search_memory', etc.
        
        We'll use a generic approach and map our actions to the server's tools.
        """
        return "memory"
    
    async def execute(self, params: Dict[str, Any], context: 'ToolContext') -> Dict[str, Any]:
        """
        Execute memory agent action
        
        Args:
            params: Action parameters (action, content, context)
            context: Tool execution context (contains kb_root_path)
            
        Returns:
            Dict with execution result
        """
        # Add KB_PATH to environment variables for this execution
        # This allows the MCP server to create the memory directory at runtime
        # in the correct user-specific location: {kb_path}/memory/
        if hasattr(context, 'kb_root_path') and context.kb_root_path:
            # Update the MCP client's environment with the current user's KB path
            if not hasattr(self, '_original_env'):
                # Store original env on first execution
                config = self.mcp_server_config
                self._original_env = config.env.copy() if config.env else {}
            
            # Create new env with KB_PATH for this user
            kb_path = str(context.kb_root_path)
            updated_env = self._original_env.copy()
            updated_env['KB_PATH'] = kb_path
            
            # Temporarily update the client's config
            if self.client:
                self.client.config.env = updated_env
                logger.debug(f"[MemoryAgentMCPTool] Set KB_PATH={kb_path} for memory agent")
        
        action = params.get("action", "")
        content = params.get("content", "")
        memory_context = params.get("context", "")
        
        # Map our action to MCP tool parameters
        # The actual parameter names depend on the mem-agent-mcp implementation
        mcp_params = {
            "action": action,
            "text": content,
            "metadata": {"context": memory_context} if memory_context else {}
        }
        
        # Call parent execute which handles MCP connection and tool calling
        result = await super().execute(mcp_params, context)
        
        # Add helpful information to the result
        if result.get("success"):
            if action == "store":
                result["message"] = f"Memory stored successfully: {content[:50]}..."
            elif action == "search":
                result["message"] = f"Search completed for: {content}"
            elif action == "list":
                result["message"] = "Retrieved all memories"
        
        return result


class MemoryStoreTool(BaseMCPTool):
    """Simplified tool for storing memories"""
    
    @property
    def name(self) -> str:
        return "memory_store"
    
    @property
    def description(self) -> str:
        return "Store a memory for later retrieval. Use this to remember important information."
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content to store in memory"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorizing the memory"
                }
            },
            "required": ["content"]
        }
    
    @property
    def mcp_server_config(self) -> MCPServerConfig:
        return MemoryAgentMCPTool().mcp_server_config
    
    @property
    def mcp_tool_name(self) -> str:
        return "store_memory"


class MemorySearchTool(BaseMCPTool):
    """Simplified tool for searching memories"""
    
    @property
    def name(self) -> str:
        return "memory_search"
    
    @property
    def description(self) -> str:
        return "Search through stored memories. Use this to find relevant information from past conversations."
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant memories"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    
    @property
    def mcp_server_config(self) -> MCPServerConfig:
        return MemoryAgentMCPTool().mcp_server_config
    
    @property
    def mcp_tool_name(self) -> str:
        return "search_memory"


# Export all memory tools
ALL_TOOLS = [
    MemoryAgentMCPTool(),
    MemoryStoreTool(),
    MemorySearchTool(),
]
