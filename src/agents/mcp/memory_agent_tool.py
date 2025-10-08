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
        Prefer stdio mem-agent configuration for Python MCP client.
        Falls back to a safe stdio default if config file is missing or invalid.
        """
        config_file = Path("data/mcp_servers/mem-agent.json")
        
        if not config_file.exists():
            logger.info(
                f"[MemoryAgentMCPTool] Config file not found: {config_file}. Using stdio fallback."
            )
            # Default to stdio server
            return MCPServerConfig(
                command="python3",
                args=["-m", "src.agents.mcp.mem_agent_server"],
                env={},
                transport="stdio",
                url=None
            )
        
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            # If config explicitly specifies HTTP/SSE, prefer stdio fallback for Python client
            transport = config_data.get("transport")
            if transport and transport.lower() in {"http", "sse"}:
                logger.info("[MemoryAgentMCPTool] HTTP/SSE config detected. Using stdio fallback for Python client.")
                return MCPServerConfig(
                    command="python3",
                    args=["-m", "src.agents.mcp.mem_agent_server"],
                    env=config_data.get("env", {}),
                    cwd=Path(config_data["working_dir"]) if config_data.get("working_dir") else None,
                    transport="stdio",
                    url=None
                )
            
            # Otherwise, assume config is suitable for stdio
            return MCPServerConfig(
                command=config_data.get("command", "python3"),
                args=config_data.get("args", ["-m", "src.agents.mcp.mem_agent_server"]),
                env=config_data.get("env", {}),
                cwd=Path(config_data["working_dir"]) if config_data.get("working_dir") else None,
                transport="stdio",
                url=None
            )
        except Exception as e:
            logger.error(f"[MemoryAgentMCPTool] Failed to load config from {config_file}: {e}")
            # Return default stdio config
            return MCPServerConfig(
                command="python3",
                args=["-m", "src.agents.mcp.mem_agent_server"],
                env={},
                transport="stdio",
                url=None
            )
    
    @property
    def mcp_tool_name(self) -> str:
        # Not used directly; execute() selects tool dynamically
        return "store_memory"

    def build_runtime_env(self, context: 'ToolContext') -> Dict[str, str]:
        env = {}
        if hasattr(context, 'kb_root_path') and context.kb_root_path:
            env['KB_PATH'] = str(context.kb_root_path)
        return env
    
    async def execute(self, params: Dict[str, Any], context: 'ToolContext') -> Dict[str, Any]:
        """
        Execute memory agent action
        
        Args:
            params: Action parameters (action, content, context)
            context: Tool execution context (contains kb_root_path)
            
        Returns:
            Dict with execution result
        """
        action = params.get("action", "")
        content = params.get("content", "")
        memory_context = params.get("context", "")
        
        # Ensure connection with runtime env
        connected = await self._ensure_connected(context)
        if not connected:
            return {"success": False, "error": "Failed to connect to mem-agent MCP server"}

        # Determine actual tool and params
        if action == "store":
            tool_name = "store_memory"
            mcp_params = {
                "content": content,
                "category": "general",
                "tags": [],
                "metadata": {"context": memory_context} if memory_context else {}
            }
        elif action == "search":
            tool_name = "retrieve_memory"
            mcp_params = {
                "query": content,
                "limit": 10
            }
        elif action == "list":
            tool_name = "list_categories"
            mcp_params = {}
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

        # Validate tool availability
        available_tools = [tool.name for tool in self.client.get_tools()]
        if tool_name not in available_tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not available. Available: {available_tools}"
            }

        # Execute
        result = await self.client.call_tool(tool_name, mcp_params)
        
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
    
    def build_runtime_env(self, context: 'ToolContext') -> Dict[str, str]:
        env = {}
        if hasattr(context, 'kb_root_path') and context.kb_root_path:
            env['KB_PATH'] = str(context.kb_root_path)
        return env
    
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
    
    def build_runtime_env(self, context: 'ToolContext') -> Dict[str, str]:
        env = {}
        if hasattr(context, 'kb_root_path') and context.kb_root_path:
            env['KB_PATH'] = str(context.kb_root_path)
        return env
    
    @property
    def mcp_tool_name(self) -> str:
        return "retrieve_memory"


# Export all memory tools
ALL_TOOLS = [
    MemoryAgentMCPTool(),
    MemoryStoreTool(),
    MemorySearchTool(),
]
