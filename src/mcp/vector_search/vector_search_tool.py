"""
Vector Search MCP Tool - Knowledge Base Vector Search

This tool provides vector search capabilities for the knowledge base via MCP.
The agent can use it to:
- Perform semantic search in the knowledge base
- Reindex knowledge base for vector search

This integrates the vector search functionality through the MCP hub server.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from ..base_mcp_tool import BaseMCPTool
from ..client import MCPServerConfig


class VectorSearchMCPTool(BaseMCPTool):
    """
    Vector Search MCP Tool - Semantic Search in Knowledge Base

    This tool provides semantic vector search capabilities for the knowledge base.
    The agent can use it to find relevant information using natural language queries.
    """

    @property
    def name(self) -> str:
        return "kb_vector_search"

    @property
    def description(self) -> str:
        return (
            "Semantic vector search in knowledge base. "
            "Use this tool to search for relevant information using natural language queries. "
            "This performs AI-powered semantic search that understands meaning, not just keywords."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - describe what you're looking for in natural language",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    @property
    def mcp_server_config(self) -> MCPServerConfig:
        """
        Load MCP server configuration from data/mcp_servers/mcp-hub.json

        Uses the same MCP hub as memory tools
        """
        # Prefer explicit MCP_HUB_URL in Docker mode
        mcp_hub_url = os.getenv("MCP_HUB_URL")
        if mcp_hub_url:
            return MCPServerConfig(
                command="python3",
                args=[
                    "-m",
                    "src.mcp.mcp_hub_server",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8765",
                ],
                env={},
                transport="sse",
                url=mcp_hub_url,
            )

        config_file = Path("data/mcp_servers/mcp-hub.json")

        if not config_file.exists():
            logger.warning(
                f"[VectorSearchMCPTool] Config file not found: {config_file}. "
                "Using default HTTP server configuration."
            )
            # Return default HTTP server config (host environment)
            return MCPServerConfig(
                command="python3",
                args=[
                    "-m",
                    "src.mcp.mcp_hub_server",
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

            # Standard MCP format: prefer "mcp-hub"
            mcp_servers = config_data.get("mcpServers", {})
            hub_config = mcp_servers.get("mcp-hub")

            if not hub_config:
                logger.warning(f"[VectorSearchMCPTool] No mcp-hub config found in {config_file}")
                raise ValueError("mcp-hub not found in mcpServers")

            # Check if this is HTTP/SSE transport (has "url" field)
            if "url" in hub_config:
                # HTTP/SSE transport
                return MCPServerConfig(
                    command=hub_config.get("_command", "python3"),
                    args=hub_config.get(
                        "_args",
                        [
                            "-m",
                            "src.mcp.mcp_hub_server",
                            "--host",
                            "127.0.0.1",
                            "--port",
                            "8765",
                        ],
                    ),
                    env={},
                    cwd=(
                        Path(hub_config.get("_cwd", Path.cwd())) if hub_config.get("_cwd") else None
                    ),
                    transport="sse",
                    url=hub_config["url"],
                )
            else:
                # stdio transport (has "command" and "args" fields)
                return MCPServerConfig(
                    command=hub_config.get("command", "python3"),
                    args=hub_config.get("args", ["-m", "src.mcp.mcp_hub_server"]),
                    env=hub_config.get("env", {}),
                    cwd=Path(hub_config["cwd"]) if hub_config.get("cwd") else None,
                    transport="stdio",
                    url=None,
                )
        except Exception as e:
            logger.error(f"[VectorSearchMCPTool] Failed to load config from {config_file}: {e}")
            # Return default HTTP config
            return MCPServerConfig(
                command="python3",
                args=[
                    "-m",
                    "src.mcp.mcp_hub_server",
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
        """The tool name in the MCP server"""
        return "vector_search"

    async def execute(self, params: Dict[str, Any], context: "ToolContext") -> Dict[str, Any]:
        """
        Execute vector search

        Args:
            params: Search parameters (query, top_k)
            context: Tool execution context

        Returns:
            Dict with search results
        """
        query = params.get("query", "")
        top_k = params.get("top_k", 5)

        if not query:
            return {"success": False, "error": "Query is required"}

        # Get user_id from context if available
        user_id = getattr(context, "user_id", None)

        # Prepare MCP parameters
        mcp_params = {
            "query": query,
            "top_k": top_k,
        }

        if user_id:
            mcp_params["user_id"] = user_id

        result = await super().execute(mcp_params, context)

        # Add helpful information to the result
        if result.get("success"):
            result["message"] = f"Vector search completed for: {query}"

        return result


class VectorReindexMCPTool(BaseMCPTool):
    """
    Vector Reindex MCP Tool - Reindex Knowledge Base

    This tool reindexes the knowledge base for vector search.
    """

    @property
    def name(self) -> str:
        return "kb_reindex_vector"

    @property
    def description(self) -> str:
        return (
            "Reindex knowledge base for vector search. "
            "Use this tool when the knowledge base has been updated and needs to be reindexed. "
            "This rebuilds the vector index for semantic search."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "Force reindexing even if index exists (default: false)",
                    "default": False,
                },
            },
        }

    @property
    def mcp_server_config(self) -> MCPServerConfig:
        """Use the same MCP hub as vector search"""
        return VectorSearchMCPTool().mcp_server_config

    @property
    def mcp_tool_name(self) -> str:
        """The tool name in the MCP server"""
        return "reindex_vector"

    async def execute(self, params: Dict[str, Any], context: "ToolContext") -> Dict[str, Any]:
        """
        Execute vector reindexing

        Args:
            params: Reindex parameters (force)
            context: Tool execution context

        Returns:
            Dict with reindexing results
        """
        force = params.get("force", False)

        # Get user_id from context if available
        user_id = getattr(context, "user_id", None)

        # Prepare MCP parameters
        mcp_params = {
            "force": force,
        }

        if user_id:
            mcp_params["user_id"] = user_id

        result = await super().execute(mcp_params, context)

        # Add helpful information to the result
        if result.get("success"):
            result["message"] = "Knowledge base reindexing completed"

        return result


# Export only vector search tool for agents
# AICODE-NOTE: Reindexing is bot-container responsibility; do not expose to agent
ALL_TOOLS = [VectorSearchMCPTool()]
