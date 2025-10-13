"""
MCP (Model Context Protocol) support package.

Note: This package's top-level imports are intentionally minimal to avoid
import-time side effects and heavy dependencies. Import specific submodules
directly, for example:

    from src.mcp.tools_description import get_mcp_tools_description
    from src.mcp.qwen_config_generator import setup_qwen_mcp_config

Other components are available under their respective submodules:
- client: MCPClient, MCPServerConfig
- registry: registry, manager, registry_client
- dynamic_mcp_tools: DynamicMCPTool, discover_and_create_mcp_tools
- memory: memory tools and servers
"""

__all__ = []
