"""
Memory Agent MCP Tool - Agent's Personal Note-Taking System

This tool provides a personal note-taking and search system specifically for the main agent.
The agent can use it to:
- Record important notes, findings, or context during task execution
- Search through recorded notes to "remember" previously written information
- Maintain working memory within a single agent session

This is designed for autonomous agents (like qwen code cli) where the agent makes many
LLM calls within one session and needs to maintain context across these calls.

The memory agent uses the driaforall/mem-agent model from HuggingFace
and the MCP server configuration is loaded from data/mcp_servers/mem-agent.json
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
    Memory Agent MCP Tool - Agent's Personal Note-Taking System
    
    This tool provides a personal note-taking and search system for the agent.
    The agent can use it to record important information and later search through notes to recall details.
    
    Usage:
        - Store notes: Write down important information, context, or findings
        - Search notes: Find relevant information from previously recorded notes
        - List notes: View all recorded notes
    
    This is designed for use within a single agent session (e.g., qwen code cli autonomous agent),
    where the agent makes many LLM calls but maintains one continuous session.
    """
    
    @property
    def name(self) -> str:
        return "mcp_memory_agent"
    
    @property
    def description(self) -> str:
        return (
            "Personal note-taking and search tool for the agent. "
            "Use this tool to record important information, notes, or context during task execution, "
            "and later search through these notes to 'remember' what was recorded. "
            "This is your personal memory within the current session - write down anything important you want to recall later. "
            "Actions: 'store' (save a note), 'search' (find relevant notes), 'list' (show all notes)."
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
                    "description": "Note content to record (for 'store' action) or search query to find notes (for 'search' action)"
                },
                "context": {
                    "type": "string",
                    "description": "Optional context or metadata for the note"
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
                result["message"] = f"Note recorded successfully: {content[:50]}..."
            elif action == "search":
                result["message"] = f"Note search completed for: {content}"
            elif action == "list":
                result["message"] = "Retrieved all recorded notes"
        
        return result


class MemoryStoreTool(BaseMCPTool):
    """Simplified tool for storing notes in the agent's personal memory"""
    
    @property
    def name(self) -> str:
        return "memory_store"
    
    @property
    def description(self) -> str:
        return "Record a note for later retrieval. Use this to write down important information you want to remember during task execution."
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Note content to record - write down any important information you want to remember"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorizing the note"
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
    """Simplified tool for searching through the agent's recorded notes"""
    
    @property
    def name(self) -> str:
        return "memory_search"
    
    @property
    def description(self) -> str:
        return "Search through your recorded notes. Use this to find and recall information you previously wrote down during this session."
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant notes from what you previously recorded"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of notes to return (default: 5)",
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
