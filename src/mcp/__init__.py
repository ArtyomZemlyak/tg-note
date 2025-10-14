"""
MCP (Model Context Protocol) support package.

Top-level imports are intentionally kept lazy to avoid import-time side effects
in environments like the MCP Hub container. Import specific submodules directly
when possible, e.g.:

    from src.mcp.tools_description import get_mcp_tools_description
    from src.mcp.qwen_config_generator import setup_qwen_mcp_config

Available components by submodule:
 - client: MCPClient, MCPServerConfig
 - registry: registry, manager, registry_client
 - dynamic_mcp_tools: DynamicMCPTool, discover_and_create_mcp_tools
 - memory: memory tools and servers
"""

__all__ = [
    # tools_description
    "get_mcp_tools_description",
    "format_mcp_tools_for_prompt",
    # dynamic_mcp_tools
    "DynamicMCPTool",
    "discover_and_create_mcp_tools",
]


def __getattr__(name: str):
    """Lazily import selected symbols on demand to prevent side effects.

    This avoids importing agent-related modules when the MCP Hub server imports
    memory subpackages (which only need `src.mcp` to be a package).
    """
    if name in {"get_mcp_tools_description", "format_mcp_tools_for_prompt"}:
        from .tools_description import (  # type: ignore
            format_mcp_tools_for_prompt,
            get_mcp_tools_description,
        )

        globals().update(
            {
                "get_mcp_tools_description": get_mcp_tools_description,
                "format_mcp_tools_for_prompt": format_mcp_tools_for_prompt,
            }
        )
        return globals()[name]

    if name in {"DynamicMCPTool", "discover_and_create_mcp_tools"}:
        from .dynamic_mcp_tools import (  # type: ignore
            DynamicMCPTool,
            discover_and_create_mcp_tools,
        )

        globals().update(
            {
                "DynamicMCPTool": DynamicMCPTool,
                "discover_and_create_mcp_tools": discover_and_create_mcp_tools,
            }
        )
        return globals()[name]

    raise AttributeError(f"module 'src.mcp' has no attribute {name!r}")
