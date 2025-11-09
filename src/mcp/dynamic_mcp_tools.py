"""
Dynamic MCP Tools

Auto-discovers MCP servers from the registry and creates tools for them.
Supports both shared and per-user MCP servers.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from config.settings import settings

from ..agents.tools.base_tool import BaseTool, ToolContext
from .client import MCPClient, MCPServerConfig
from .registry_client import MCPRegistryClient


class DynamicMCPTool(BaseTool):
    """
    Dynamic MCP tool that wraps a specific tool from an MCP server

    This tool is created at runtime based on discovered MCP servers.
    It connects to the MCP server and forwards tool calls to it.
    """

    def __init__(
        self, tool_name: str, server_name: str, mcp_client: MCPClient, tool_schema: Dict[str, Any]
    ):
        """
        Initialize dynamic MCP tool

        Args:
            tool_name: Name of the tool in the MCP server
            server_name: Name of the MCP server
            mcp_client: Connected MCP client
            tool_schema: Tool schema from MCP server
        """
        self._tool_name = f"mcp_{server_name}_{tool_name}"
        self._original_tool_name = tool_name
        self._server_name = server_name
        self._mcp_client = mcp_client
        self._tool_schema = tool_schema
        self._description = tool_schema.get("description", f"Tool from MCP server {server_name}")
        self._parameters = tool_schema.get(
            "inputSchema", {"type": "object", "properties": {}, "required": []}
        )

    @property
    def name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return f"[MCP:{self._server_name}] {self._description}"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return self._parameters

    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """
        Execute the tool by calling the MCP server

        Args:
            params: Tool parameters
            context: Execution context

        Returns:
            Tool execution result
        """
        try:
            # Call the MCP server tool
            result = await self._mcp_client.call_tool(self._original_tool_name, params)

            if result.get("success"):
                return {
                    "success": True,
                    "result": result.get("result"),
                    "server": self._server_name,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error from MCP server"),
                    "server": self._server_name,
                }
        except Exception as e:
            logger.error(f"[DynamicMCPTool] Error calling {self._tool_name}: {e}")
            return {
                "success": False,
                "error": f"Error calling MCP tool: {str(e)}",
                "server": self._server_name,
            }


async def discover_and_create_mcp_tools(
    user_id: Optional[int] = None, servers_dir: Optional[Path] = None
) -> List[BaseTool]:
    """
    Discover MCP servers and create tools for them

    This function:
    1. Discovers available MCP servers (shared + per-user if user_id is provided)
    2. Connects to enabled servers
    3. Queries each server for available tools
    4. Creates DynamicMCPTool instances for each tool

    Args:
        user_id: Optional user ID for per-user MCP server discovery
        servers_dir: Optional custom servers directory

    Returns:
        List of MCP tools ready to use
    """
    tools = []

    try:
        connected_clients: Dict[str, MCPClient] = {}

        # Docker mode: connect directly to MCP Hub via HTTP/SSE and avoid local registry
        mcp_hub_url = os.getenv("MCP_HUB_URL")
        if mcp_hub_url:
            try:
                client = MCPClient(
                    MCPServerConfig(url=mcp_hub_url), timeout=settings.MCP_TIMEOUT
                )  # fastmcp.Client auto-detects transport from URL
                if await client.connect():
                    connected_clients["mcp-hub"] = client
                else:
                    logger.warning(
                        f"[DynamicMCPTools] Failed to connect to MCP Hub at {mcp_hub_url}"
                    )
            except Exception as e:
                logger.error(
                    f"[DynamicMCPTools] Error connecting to MCP Hub at {mcp_hub_url}: {e}",
                    exc_info=True,
                )
        else:
            # Standalone mode: discover via local registry
            registry_client = MCPRegistryClient(servers_dir=servers_dir, user_id=user_id)
            registry_client.initialize()
            connected_clients = await registry_client.connect_all_enabled()

        if not connected_clients:
            logger.info("[DynamicMCPTools] No MCP servers connected")
            return tools

        # For each connected server, discover its tools
        for server_name, client in connected_clients.items():
            try:
                # List available tools from the MCP server
                available_tools = await client.list_tools()

                if not available_tools:
                    logger.debug(f"[DynamicMCPTools] Server {server_name} has no tools")
                    continue

                # Create a DynamicMCPTool for each tool
                for tool_schema in available_tools:
                    tool_name = tool_schema.get("name")
                    if not tool_name:
                        logger.warning(
                            f"[DynamicMCPTools] Skipping tool with no name from {server_name}"
                        )
                        continue

                    try:
                        mcp_tool = DynamicMCPTool(
                            tool_name=tool_name,
                            server_name=server_name,
                            mcp_client=client,
                            tool_schema=tool_schema,
                        )
                        tools.append(mcp_tool)
                        logger.info(f"[DynamicMCPTools] Created tool: {mcp_tool.name}")
                    except Exception as e:
                        logger.error(f"[DynamicMCPTools] Failed to create tool {tool_name}: {e}")

            except Exception as e:
                logger.error(f"[DynamicMCPTools] Failed to discover tools from {server_name}: {e}")

        logger.info(
            f"[DynamicMCPTools] Created {len(tools)} MCP tools from {len(connected_clients)} servers"
        )

    except Exception as e:
        logger.error(f"[DynamicMCPTools] Failed to discover MCP tools: {e}")

    return tools


# For backwards compatibility and easy import
async def create_mcp_tools_for_user(user_id: int) -> List[BaseTool]:
    """
    Convenience function to create MCP tools for a specific user

    Args:
        user_id: User ID

    Returns:
        List of MCP tools available to the user
    """
    return await discover_and_create_mcp_tools(user_id=user_id)
