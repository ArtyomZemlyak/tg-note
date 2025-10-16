"""
MCP Tools Description Generator

Generates human-readable descriptions of available MCP servers and their tools.
This is used to inform LLMs about available MCP tools in their system prompts.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .client import MCPClient, MCPServerConfig
from .registry_client import MCPRegistryClient


async def get_mcp_tools_description(
    user_id: Optional[int] = None, servers_dir: Optional[Path] = None
) -> str:
    """
    Get human-readable description of available MCP tools

    This function:
    1. Discovers available MCP servers (shared + per-user)
    2. Connects to enabled servers
    3. Queries each server for available tools
    4. Generates a formatted description for use in LLM prompts

    Args:
        user_id: Optional user ID for per-user MCP server discovery
        servers_dir: Optional custom servers directory

    Returns:
        Formatted description of MCP tools, or empty string if no tools available
    """
    try:
        # Docker mode: connect directly to MCP Hub via HTTP/SSE and avoid local registry
        mcp_hub_url = os.getenv("MCP_HUB_URL")
        connected_clients: Dict[str, MCPClient] = {}

        if mcp_hub_url:
            try:
                client = MCPClient(MCPServerConfig(transport="sse", url=mcp_hub_url))
                if await client.connect():
                    connected_clients["mcp-hub"] = client
                else:
                    logger.warning(
                        f"[MCPToolsDescription] Failed to connect to MCP Hub at {mcp_hub_url}"
                    )
            except Exception as e:
                logger.error(
                    f"[MCPToolsDescription] Error connecting to MCP Hub at {mcp_hub_url}: {e}",
                    exc_info=True,
                )
        else:
            # Standalone mode: discover via local registry
            registry_client = MCPRegistryClient(servers_dir=servers_dir, user_id=user_id)
            registry_client.initialize()
            connected_clients = await registry_client.connect_all_enabled()

        if not connected_clients:
            logger.debug("[MCPToolsDescription] No MCP servers connected")
            return ""

        # Build description
        lines = []
        lines.append("# Available MCP Tools")
        lines.append("")
        lines.append(
            "The following MCP (Model Context Protocol) servers are available with their tools:"
        )
        lines.append("")

        total_tools = 0

        # For each connected server, list its tools
        for server_name, client in connected_clients.items():
            try:
                # List available tools from the MCP server
                available_tools = await client.list_tools()

                if not available_tools:
                    continue

                lines.append(f"## MCP Server: {server_name}")
                lines.append("")

                # List each tool with its description
                for tool_schema in available_tools:
                    tool_name = tool_schema.get("name")
                    tool_description = tool_schema.get("description", "No description available")

                    if not tool_name:
                        continue

                    # Tool name in agent will be: mcp_{server_name}_{tool_name}
                    agent_tool_name = f"mcp_{server_name}_{tool_name}"

                    lines.append(f"### {agent_tool_name}")
                    lines.append(f"- **Original name**: `{tool_name}`")
                    lines.append(f"- **Description**: {tool_description}")

                    # Add parameter information if available
                    input_schema = tool_schema.get("inputSchema", {})
                    properties = input_schema.get("properties", {})
                    required = input_schema.get("required", [])

                    if properties:
                        lines.append(f"- **Parameters**:")
                        for param_name, param_info in properties.items():
                            param_type = param_info.get("type", "unknown")
                            param_desc = param_info.get("description", "")
                            is_required = " (required)" if param_name in required else " (optional)"

                            lines.append(
                                f"  - `{param_name}` ({param_type}){is_required}: {param_desc}"
                            )

                    lines.append("")
                    total_tools += 1

            except Exception as e:
                logger.error(
                    f"[MCPToolsDescription] Failed to describe tools from {server_name}: {e}"
                )

        if total_tools == 0:
            return ""

        # Add usage note
        lines.append("---")
        lines.append("")
        lines.append(
            f"**Total MCP tools available**: {total_tools} from {len(connected_clients)} server(s)"
        )
        lines.append("")
        lines.append(
            "**Usage**: Call these tools using their agent tool name (e.g., `mcp_server_tool`)"
        )
        lines.append("")

        description = "\n".join(lines)
        logger.info(f"[MCPToolsDescription] Generated description for {total_tools} MCP tools")

        return description

    except Exception as e:
        logger.error(f"[MCPToolsDescription] Failed to generate MCP tools description: {e}")
        return ""


def format_mcp_tools_for_prompt(tools_description: str, include_in_system: bool = True) -> str:
    """
    Format MCP tools description for inclusion in LLM prompts

    Args:
        tools_description: Description from get_mcp_tools_description()
        include_in_system: If True, formats for system prompt; otherwise for user prompt

    Returns:
        Formatted text for prompt
    """
    if not tools_description:
        return ""

    if include_in_system:
        return f"""

## MCP Tools Available

You have access to additional tools via MCP (Model Context Protocol):

{tools_description}

Use these tools when appropriate for the task.
"""
    else:
        return f"""

---

{tools_description}
"""
