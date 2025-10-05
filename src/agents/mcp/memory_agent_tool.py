"""
Memory Agent MCP Tool

This tool integrates the mem-agent-mcp server for memory management.

The memory agent uses the driaforall/mem-agent model from HuggingFace
to provide intelligent memory storage and retrieval for autonomous agents.

References:
- Model: https://huggingface.co/driaforall/mem-agent
- MCP Server: https://github.com/firstbatchxyz/mem-agent-mcp
"""

import os
from pathlib import Path
from typing import Any, Dict

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
        Configure the mem-agent-mcp server
        
        The server should be installed via npx or locally:
        npm install -g @firstbatch/mem-agent-mcp
        
        Environment variables:
        - MEM_AGENT_MCP_PROVIDER: LLM provider (openai, anthropic, etc.)
        - MEM_AGENT_MCP_MODEL: Model name (default: gpt-4)
        - OPENAI_API_KEY or ANTHROPIC_API_KEY: API key for the provider
        """
        # Try to use locally installed version first, fallback to npx
        local_path = Path("node_modules/.bin/mem-agent-mcp")
        
        if local_path.exists():
            command = str(local_path.absolute())
        else:
            # Use npx to run the MCP server
            command = "npx"
        
        args = []
        if command == "npx":
            args.append("@firstbatch/mem-agent-mcp")
        
        # Pass through environment variables for API keys
        env = os.environ.copy()
        
        # Set default provider and model if not set
        if "MEM_AGENT_MCP_PROVIDER" not in env:
            env["MEM_AGENT_MCP_PROVIDER"] = "openai"
        if "MEM_AGENT_MCP_MODEL" not in env:
            env["MEM_AGENT_MCP_MODEL"] = "gpt-4"
        
        return MCPServerConfig(
            command=command,
            args=args,
            env=env
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
            context: Tool execution context
            
        Returns:
            Dict with execution result
        """
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
