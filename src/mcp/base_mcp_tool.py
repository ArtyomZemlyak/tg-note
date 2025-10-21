"""
Base MCP Tool class

This module provides a base class for wrapping MCP server tools
as autonomous agent tools.
"""

from abc import abstractmethod
from typing import Any, Dict, Optional

from loguru import logger

from ..agents.tools.base_tool import BaseTool, ToolContext
from .client import MCPClient, MCPServerConfig


class BaseMCPTool(BaseTool):
    """
    Base class for MCP-backed tools.

    This class wraps an MCP server and exposes its tools as agent tools.
    Subclasses should configure the MCP server and handle tool execution.
    """

    def __init__(self, timeout: int = 600):
        """
        Initialize MCP tool
        
        Args:
            timeout: Timeout in seconds for MCP requests (default: 600 seconds)
        """
        self.client: Optional[MCPClient] = None
        self.enabled = False
        self._connected = False
        self.timeout = timeout

    @property
    @abstractmethod
    def mcp_server_config(self) -> MCPServerConfig:
        """
        Get MCP server configuration

        Returns:
            MCPServerConfig with server command and args
        """
        pass

    @property
    @abstractmethod
    def mcp_tool_name(self) -> str:
        """
        Get the name of the MCP tool to call

        Returns:
            Name of the tool in the MCP server
        """
        pass

    async def _ensure_connected(self) -> bool:
        """
        Ensure MCP client is connected

        Returns:
            True if connected successfully
        """
        if self._connected and self.client and self.client.is_connected:
            return True

        if not self.client:
            self.client = MCPClient(self.mcp_server_config, timeout=self.timeout)

        self._connected = await self.client.connect()
        return self._connected

    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """
        Execute the MCP tool

        Args:
            params: Tool parameters
            context: Execution context

        Returns:
            Dict with execution result
        """
        if not self.enabled:
            return {
                "success": False,
                "error": f"MCP tool {self.name} is disabled. Enable it in configuration.",
            }

        # Ensure connection
        if not await self._ensure_connected():
            return {"success": False, "error": f"Failed to connect to MCP server for {self.name}"}

        # Validate that the tool exists in MCP server
        available_tools = [tool.name for tool in self.client.get_tools()]
        if self.mcp_tool_name not in available_tools:
            return {
                "success": False,
                "error": f"Tool '{self.mcp_tool_name}' not found in MCP server. Available: {available_tools}",
            }

        # Call the MCP tool
        try:
            result = await self.client.call_tool(self.mcp_tool_name, params)

            if result.get("success"):
                logger.info(f"[{self.name}] ✓ MCP tool executed successfully")
            else:
                logger.warning(f"[{self.name}] MCP tool execution failed: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"[{self.name}] MCP tool execution error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        if self.client:
            await self.client.disconnect()
            self._connected = False

    def enable(self) -> None:
        """Enable this MCP tool"""
        self.enabled = True
        logger.info(f"[{self.name}] MCP tool enabled")

    def disable(self) -> None:
        """Disable this MCP tool"""
        self.enabled = False
        if self.client:
            # Disconnect when disabled
            import asyncio

            asyncio.create_task(self.disconnect())
        logger.info(f"[{self.name}] MCP tool disabled")

    def __del__(self):
        """Cleanup on deletion"""
        if self.client:
            try:
                import asyncio

                asyncio.create_task(self.disconnect())
            except:
                pass
