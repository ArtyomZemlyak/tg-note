"""
Memory MCP Tool - Agent's Personal Note-Taking System

This tool provides a personal note-taking and search system specifically for the main agent.
The agent can use it to:
- Record important notes, findings, or context during task execution
- Search through recorded notes to "remember" previously written information
- Maintain working memory within a single agent session

This is designed for autonomous agents (like qwen code cli) where the agent makes many
LLM calls within one session and needs to maintain context across these calls.

The memory system uses embeddings (e.g., BAAI/bge-m3) from HuggingFace
and the MCP server configuration is loaded from data/mcp_servers/memory.json
which is created by running scripts/install_mem_agent.py.

References:
- Model: https://huggingface.co/BAAI/bge-m3
- Installation: scripts/install_mem_agent.py
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from ..base_mcp_tool import BaseMCPTool
from ..client import MCPServerConfig


class MemoryMCPTool(BaseMCPTool):
    """
    Memory MCP Tool - Agent's Personal Note-Taking System

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
        return "mcp_memory"

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
                    "description": "Action to perform: store (save memory), search (find memories), list (show all memories)",
                },
                "content": {
                    "type": "string",
                    "description": "Note content to record (for 'store' action) or search query to find notes (for 'search' action)",
                },
                "context": {
                    "type": "string",
                    "description": "Optional context or metadata for the note",
                },
            },
            "required": ["action"],
        }

    @property
    def mcp_server_config(self) -> MCPServerConfig:
        """
        Load MCP server configuration from data/mcp_servers/memory.json

        The configuration is created by MCPServerManager and contains settings
        for the memory HTTP server (SSE transport).

        Note: The KB_PATH environment variable is set dynamically at runtime
        in the execute() method, as it's user-specific.
        """
        config_file = Path("data/mcp_servers/memory.json")

        if not config_file.exists():
            # Try legacy mem-agent.json for backward compatibility
            legacy_config_file = Path("data/mcp_servers/mem-agent.json")
            if legacy_config_file.exists():
                config_file = legacy_config_file
                logger.info(f"[MemoryMCPTool] Using legacy config file: {config_file}")
            else:
                logger.warning(
                    f"[MemoryMCPTool] Config file not found: {config_file}. "
                    "Using default HTTP server configuration."
                )
                # Return default HTTP server config
                return MCPServerConfig(
                    command="python",
                    args=[
                        "-m",
                        "src.agents.mcp.memory.memory_server_http",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8765",
                    ],
                    env={},
                    transport="sse",
                    url="http://127.0.0.1:8765/sse",
                )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # Standard MCP format: {"mcpServers": {"memory": {...}}} or {"mcpServers": {"mem-agent": {...}}}
            mcp_servers = config_data.get("mcpServers", {})
            memory_config = mcp_servers.get("memory") or mcp_servers.get("mem-agent")

            if not memory_config:
                logger.warning(f"[MemoryMCPTool] No memory config found in {config_file}")
                raise ValueError("memory not found in mcpServers")

            # Check if this is HTTP/SSE transport (has "url" field)
            if "url" in memory_config:
                # HTTP/SSE transport
                return MCPServerConfig(
                    command=memory_config.get("_command", "python"),
                    args=memory_config.get(
                        "_args",
                        [
                            "-m",
                            "src.agents.mcp.memory.memory_server_http",
                            "--host",
                            "127.0.0.1",
                            "--port",
                            "8765",
                        ],
                    ),
                    env={},
                    cwd=(
                        Path(memory_config.get("_cwd", Path.cwd()))
                        if memory_config.get("_cwd")
                        else None
                    ),
                    transport="sse",
                    url=memory_config["url"],
                )
            else:
                # stdio transport (has "command" and "args" fields)
                return MCPServerConfig(
                    command=memory_config.get("command", "python"),
                    args=memory_config.get(
                        "args", ["-m", "src.agents.mcp.memory.memory_server_http"]
                    ),
                    env=memory_config.get("env", {}),
                    cwd=Path(memory_config["cwd"]) if memory_config.get("cwd") else None,
                    transport="stdio",
                    url=None,
                )
        except Exception as e:
            logger.error(f"[MemoryMCPTool] Failed to load config from {config_file}: {e}")
            # Return default HTTP config
            return MCPServerConfig(
                command="python",
                args=[
                    "-m",
                    "src.agents.mcp.memory.memory_server_http",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8765",
                ],
                env={},
                transport="sse",
                url="http://127.0.0.1:8765/sse",
            )

    @property
    def mcp_tool_name(self) -> str:
        """
        The tool name in the MCP server

        Note: This depends on how the memory-mcp server exposes its tools.
        Common names might be: 'memory', 'store_memory', 'search_memory', etc.

        We'll use a generic approach and map our actions to the server's tools.
        """
        return "memory"

    async def execute(self, params: Dict[str, Any], context: "ToolContext") -> Dict[str, Any]:
        """
        Execute memory action

        Args:
            params: Action parameters (action, content, context)
            context: Tool execution context (contains kb_root_path)

        Returns:
            Dict with execution result
        """
        # Add KB_PATH to environment variables for this execution
        # This allows the MCP server to create the memory directory at runtime
        # in the correct user-specific location: {kb_path}/memory/
        if hasattr(context, "kb_root_path") and context.kb_root_path:
            # Update the MCP client's environment with the current user's KB path
            if not hasattr(self, "_original_env"):
                # Store original env on first execution
                config = self.mcp_server_config
                self._original_env = config.env.copy() if config.env else {}

            # Create new env with KB_PATH for this user
            kb_path = str(context.kb_root_path)
            updated_env = self._original_env.copy()
            updated_env["KB_PATH"] = kb_path

            # Temporarily update the client's config
            if self.client:
                self.client.config.env = updated_env
                logger.debug(f"[MemoryMCPTool] Set KB_PATH={kb_path} for memory")

        action = params.get("action", "")
        content = params.get("content", "")
        memory_context = params.get("context", "")

        # Map our action to MCP tool parameters
        # The actual parameter names depend on the memory-mcp implementation
        mcp_params = {
            "action": action,
            "text": content,
            "metadata": {"context": memory_context} if memory_context else {},
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
                    "description": "Note content to record - write down any important information you want to remember",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorizing the note",
                },
            },
            "required": ["content"],
        }

    @property
    def mcp_server_config(self) -> MCPServerConfig:
        return MemoryMCPTool().mcp_server_config

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
                    "description": "Search query to find relevant notes from what you previously recorded",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of notes to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    @property
    def mcp_server_config(self) -> MCPServerConfig:
        return MemoryMCPTool().mcp_server_config

    @property
    def mcp_tool_name(self) -> str:
        return "search_memory"


# Export all memory tools
ALL_TOOLS = [
    MemoryMCPTool(),
    MemoryStoreTool(),
    MemorySearchTool(),
]
