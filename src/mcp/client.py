"""
MCP (Model Context Protocol) Client

This module provides a client wrapper around the official MCP Python SDK.
Uses mcp.ClientSession for communicating with MCP servers.

Supported MCP features:
- ✅ Tools (tools/list, tools/call)
- ✅ Resources (resources/list, resources/read)
- ✅ Prompts (prompts/list, prompts/get)
- ✅ JSON-RPC 2.0 communication
- ✅ Stdio transport
- ✅ SSE transport (HTTP Server-Sent Events)

References:
- MCP Protocol: https://modelcontextprotocol.io/
- MCP Specification: https://modelcontextprotocol.io/docs/specification
- Python MCP SDK: https://github.com/modelcontextprotocol/python-sdk
"""

import asyncio
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client


@dataclass
class MCPToolSchema:
    """Schema for an MCP tool"""

    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""

    command: str = ""  # Empty for HTTP/SSE transport
    args: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    cwd: Optional[Path] = None
    transport: str = "stdio"  # "stdio" or "sse" (HTTP Server-Sent Events)
    url: Optional[str] = None  # URL for SSE transport (e.g., "http://127.0.0.1:8765/sse")

    def __post_init__(self):
        # Validate config
        if self.transport == "sse":
            if not self.url:
                raise ValueError("URL is required for SSE transport")
        elif self.transport == "stdio":
            if not self.command:
                raise ValueError("Command is required for stdio transport")


class MCPClient:
    """
    Client wrapper for communicating with MCP servers via stdio or HTTP/SSE.

    This class wraps the official MCP Python SDK's ClientSession and provides
    a simplified interface compatible with the project's existing code.

    Supports two transport modes:
    1. stdio: Launches MCP server as subprocess (JSON-RPC over stdin/stdout)
    2. sse: Connects to HTTP/SSE endpoint (JSON-RPC over HTTP Server-Sent Events)

    Supported operations:
    - Tools: list_tools(), call_tool()
    - Resources: list_resources(), read_resource()
    - Prompts: list_prompts(), get_prompt()

    Example (stdio):
        config = MCPServerConfig(
            command="npx",
            args=["@example/mcp-server"],
            transport="stdio"
        )

    Example (HTTP/SSE - for Docker deployments):
        config = MCPServerConfig(
            transport="sse",
            url="http://mcp-hub:8765/sse"
        )

    client = MCPClient(config)
    await client.connect()
    """

    def __init__(self, config: MCPServerConfig, timeout: int = 600):
        """
        Initialize MCP client

        Args:
            config: Server configuration (command+args for stdio, or url for sse)
            timeout: Timeout in seconds for MCP requests (default: 600 seconds)
        """
        self.config = config
        self.timeout = timeout
        self.is_connected = False
        self.tools: List[MCPToolSchema] = []

        # AICODE-NOTE: Use AsyncExitStack to manage async context managers
        self._exit_stack: Optional[AsyncExitStack] = None
        # AICODE-NOTE: Official MCP SDK session
        self._session: Optional[ClientSession] = None
        # AICODE-NOTE: Track reconnection attempts to prevent infinite loops
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 3

    async def connect(self) -> bool:
        """
        Connect to MCP server (stdio or HTTP/SSE)

        Returns:
            True if connection successful
        """
        try:
            if self.config.transport == "sse":
                return await self._connect_sse()
            else:
                return await self._connect_stdio()
        except Exception as e:
            logger.error(f"[MCPClient] Failed to connect: {e}", exc_info=True)
            await self.disconnect()
            return False

    async def _connect_stdio(self) -> bool:
        """Connect via stdio transport using official MCP SDK"""
        logger.info(f"[MCPClient] Connecting to MCP server (stdio): {self.config.command}")

        try:
            # Create exit stack for managing async context managers
            self._exit_stack = AsyncExitStack()

            # Create server parameters
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env,
                cwd=str(self.config.cwd) if self.config.cwd else None,
            )

            # Connect using stdio_client context manager
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )

            # Create client session
            read_stream, write_stream = stdio_transport
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Initialize connection
            return await self._initialize()

        except Exception as e:
            logger.error(f"[MCPClient] stdio connection failed: {e}", exc_info=True)
            await self.disconnect()
            return False

    async def _connect_sse(self) -> bool:
        """Connect via HTTP/SSE transport using official MCP SDK"""
        logger.info(f"[MCPClient] Connecting to MCP server (SSE): {self.config.url}")

        try:
            # Create exit stack for managing async context managers
            self._exit_stack = AsyncExitStack()

            # Ensure URL has trailing slash to avoid redirects
            sse_url = self.config.url
            if not sse_url.endswith("/"):
                sse_url += "/"

            # Connect using sse_client context manager
            sse_transport = await self._exit_stack.enter_async_context(
                sse_client(
                    url=sse_url,
                    timeout=10.0,  # Connection timeout
                    sse_read_timeout=float(self.timeout),  # Read timeout
                )
            )

            # Create client session
            read_stream, write_stream = sse_transport
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Initialize connection
            return await self._initialize()

        except Exception as e:
            logger.error(f"[MCPClient] SSE connection failed: {e}", exc_info=True)
            await self.disconnect()
            return False

    async def _initialize(self) -> bool:
        """Initialize MCP connection (common for both transports)"""
        if not self._session:
            return False

        try:
            # Initialize session with server capabilities
            await self._session.initialize()

            # List available tools
            tools_response = await self._session.list_tools()

            if tools_response and hasattr(tools_response, "tools"):
                self.tools = [
                    MCPToolSchema(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema or {},
                    )
                    for tool in tools_response.tools
                ]
                logger.info(
                    f"[MCPClient] ✓ Connected. Available tools: {[t.name for t in self.tools]}"
                )

            self.is_connected = True
            self._reconnect_attempts = 0  # Reset reconnection attempts on successful connection
            return True

        except Exception as e:
            logger.error(f"[MCPClient] Initialization failed: {e}", exc_info=True)
            return False

    async def reconnect(self) -> bool:
        """
        Reconnect to MCP server

        Returns:
            True if reconnection successful
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error(
                f"[MCPClient] Maximum reconnection attempts ({self._max_reconnect_attempts}) exceeded"
            )
            return False

        self._reconnect_attempts += 1
        logger.info(
            f"[MCPClient] Attempting to reconnect (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})..."
        )
        await self.disconnect()
        success = await self.connect()
        if success:
            self._reconnect_attempts = 0  # Reset on successful reconnection
        return success

    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                logger.debug(f"[MCPClient] Error during disconnect: {e}")
            self._exit_stack = None

        self._session = None
        self.is_connected = False
        logger.info("[MCPClient] Disconnected")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self.is_connected or not self._session:
            return {"success": False, "error": "Not connected to MCP server"}

        try:
            logger.debug(f"[MCPClient] Calling tool: {tool_name} with args: {arguments}")

            # Call tool using official SDK
            response = await self._session.call_tool(tool_name, arguments)

            if not response:
                return {"success": False, "error": "No response from server"}

            # Extract content from response
            content = response.content if hasattr(response, "content") else []

            # Parse content based on type for convenience string output
            output = []
            for item in content:
                if hasattr(item, "type"):
                    if item.type == "text":
                        output.append(item.text if hasattr(item, "text") else "")
                    elif item.type == "resource":
                        resource_uri = (
                            item.resource.uri
                            if hasattr(item, "resource") and hasattr(item.resource, "uri")
                            else ""
                        )
                        output.append(f"Resource: {resource_uri}")
                    elif item.type == "markdown":
                        output.append(
                            item.text
                            if hasattr(item, "text")
                            else (item.markdown if hasattr(item, "markdown") else "")
                        )

            is_error = response.isError if hasattr(response, "isError") else False

            return {
                "success": True,
                "output": "\n".join(output).strip() if output else "Tool executed successfully",
                "is_error": is_error,
                "result": {"content": content, "isError": is_error},
                "content": content,
            }

        except Exception as e:
            logger.error(f"[MCPClient] Tool call failed: {e}", exc_info=True)

            # Try to reconnect if connection lost
            if "connection" in str(e).lower() or "closed" in str(e).lower():
                logger.warning("[MCPClient] Connection lost, attempting to reconnect...")
                if await self.reconnect():
                    logger.info("[MCPClient] Reconnected successfully, retrying tool call...")
                    # Retry the tool call once
                    try:
                        response = await self._session.call_tool(tool_name, arguments)
                        if response:
                            content = response.content if hasattr(response, "content") else []
                            output = []
                            for item in content:
                                if hasattr(item, "type") and item.type == "text":
                                    output.append(item.text if hasattr(item, "text") else "")
                            return {
                                "success": True,
                                "output": (
                                    "\n".join(output).strip()
                                    if output
                                    else "Tool executed successfully"
                                ),
                                "content": content,
                            }
                    except Exception as retry_error:
                        return {
                            "success": False,
                            "error": f"Retry failed after reconnection: {str(retry_error)}",
                        }

            return {"success": False, "error": str(e)}

    def get_tools(self) -> List[MCPToolSchema]:
        """
        Get list of available tools

        Returns:
            List of tool schemas
        """
        return self.tools

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from MCP server

        This method returns tools in the format expected by the MCP protocol.
        For cached access, use get_tools() instead.

        Returns:
            List of tool schemas as dicts
        """
        return [
            {"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema}
            for tool in self.tools
        ]

    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        List available resources from MCP server

        Resources provide context and data for the LLM.

        Returns:
            List of resource schemas
        """
        if not self.is_connected or not self._session:
            return []

        try:
            response = await self._session.list_resources()

            if response and hasattr(response, "resources"):
                return [
                    {
                        "uri": res.uri,
                        "name": res.name if hasattr(res, "name") else res.uri,
                        "description": res.description if hasattr(res, "description") else "",
                        "mimeType": res.mimeType if hasattr(res, "mimeType") else None,
                    }
                    for res in response.resources
                ]

            return []

        except Exception as e:
            logger.error(f"[MCPClient] Failed to list resources: {e}")
            return []

    async def read_resource(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Read a resource from MCP server

        Args:
            uri: Resource URI (e.g., "file:///path/to/file.txt")

        Returns:
            Resource content or None if error
        """
        if not self.is_connected or not self._session:
            return None

        try:
            response = await self._session.read_resource(uri)

            if response and hasattr(response, "contents"):
                return {
                    "contents": [
                        {
                            "uri": content.uri if hasattr(content, "uri") else uri,
                            "text": content.text if hasattr(content, "text") else None,
                            "mimeType": content.mimeType if hasattr(content, "mimeType") else None,
                            "blob": (
                                content.blob
                                if hasattr(content, "blob")
                                else (content.base64 if hasattr(content, "base64") else None)
                            ),
                        }
                        for content in response.contents
                    ]
                }

            return None

        except Exception as e:
            logger.error(f"[MCPClient] Failed to read resource {uri}: {e}")
            return None

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """
        List available prompts from MCP server

        Prompts are pre-defined templates for working with the LLM.

        Returns:
            List of prompt schemas
        """
        if not self.is_connected or not self._session:
            return []

        try:
            response = await self._session.list_prompts()

            if response and hasattr(response, "prompts"):
                return [
                    {
                        "name": prompt.name,
                        "description": (
                            prompt.description if hasattr(prompt, "description") else ""
                        ),
                        "arguments": (
                            [
                                {
                                    "name": arg.name,
                                    "description": (
                                        arg.description if hasattr(arg, "description") else ""
                                    ),
                                    "required": arg.required if hasattr(arg, "required") else False,
                                }
                                for arg in prompt.arguments
                            ]
                            if hasattr(prompt, "arguments")
                            else []
                        ),
                    }
                    for prompt in response.prompts
                ]

            return []

        except Exception as e:
            logger.error(f"[MCPClient] Failed to list prompts: {e}")
            return []

    async def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a prompt from MCP server

        Args:
            name: Prompt name
            arguments: Optional prompt arguments

        Returns:
            Prompt content or None if error
        """
        if not self.is_connected or not self._session:
            return None

        try:
            response = await self._session.get_prompt(name, arguments or {})

            if response and hasattr(response, "messages"):
                return {
                    "description": response.description if hasattr(response, "description") else "",
                    "messages": [
                        {
                            "role": msg.role if hasattr(msg, "role") else "user",
                            "content": (
                                {
                                    "type": msg.content.type,
                                    "text": (
                                        msg.content.text if hasattr(msg.content, "text") else ""
                                    ),
                                }
                                if hasattr(msg, "content")
                                else {}
                            ),
                        }
                        for msg in response.messages
                    ],
                }

            return None

        except Exception as e:
            logger.error(f"[MCPClient] Failed to get prompt {name}: {e}")
            return None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    def __del__(self):
        """Cleanup on deletion"""
        if self._exit_stack or self._session:
            try:
                # Try to clean up resources
                asyncio.create_task(self.disconnect())
            except:
                pass
