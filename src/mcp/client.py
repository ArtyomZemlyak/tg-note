"""
MCP (Model Context Protocol) Client

This module provides a client wrapper around fastmcp.Client.
Uses fastmcp's auto-detection for transport type and handles all MCP operations.

Supported MCP features:
- ✅ Tools (tools/list, tools/call)
- ✅ Resources (resources/list, resources/read)
- ✅ Prompts (prompts/list, prompts/get)
- ✅ JSON-RPC 2.0 communication
- ✅ Stdio transport (auto-detected)
- ✅ SSE transport (auto-detected)
- ✅ Streaming HTTP transport (auto-detected)

References:
- MCP Protocol: https://modelcontextprotocol.io/
- MCP Specification: https://modelcontextprotocol.io/docs/specification
- Python MCP SDK: https://github.com/modelcontextprotocol/python-sdk
- FastMCP: https://github.com/jlowin/fastmcp
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from loguru import logger


@dataclass
class MCPToolSchema:
    """Schema for an MCP tool"""

    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPServerConfig:
    """
    Configuration for an MCP server

    The client automatically detects the transport type based on the configuration:
    - If `url` is provided: Uses SSE or Streaming HTTP (auto-detected)
    - If `command` is provided: Uses stdio transport
    - If both provided: URL takes precedence

    Transport auto-detection:
    - http://... or https://... -> SSE or Streaming HTTP (fastmcp auto-detects)
    - Command string -> stdio subprocess
    """

    command: str = ""  # Command for stdio transport (e.g., "npx", "python")
    args: List[str] = field(default_factory=list)  # Arguments for stdio command
    env: Optional[Dict[str, str]] = None  # Environment variables for stdio
    cwd: Optional[Path] = None  # Working directory for stdio
    transport: str = "auto"  # "auto", "stdio", "sse", "streamable-http"
    url: Optional[str] = None  # URL for HTTP-based transports

    def __post_init__(self):
        # Auto-detect transport if not explicitly specified
        # fastmcp.Client handles transport detection, we just need to validate config
        if self.transport == "auto":
            if self.url:
                # URL provided - fastmcp.Client will auto-detect SSE or Streaming HTTP
                self.transport = "http"
            elif self.command:
                self.transport = "stdio"
            else:
                raise ValueError(
                    "Either 'url' (for HTTP-based transport) or 'command' (for stdio) must be provided"
                )


class MCPClient:
    """
    Client wrapper for communicating with MCP servers.

    This class wraps fastmcp.Client which automatically detects and handles
    different transport types (stdio, SSE, streaming HTTP).

    Transport auto-detection:
    - URL provided: fastmcp automatically chooses SSE or Streaming HTTP
    - Command provided: Uses stdio subprocess transport
    - Both provided: URL takes precedence

    Supported operations:
    - Tools: list_tools(), call_tool()
    - Resources: list_resources(), read_resource()
    - Prompts: list_prompts(), get_prompt()

    Example (stdio - auto-detected):
        config = MCPServerConfig(
            command="npx",
            args=["@example/mcp-server"]
        )

    Example (HTTP - auto-detected SSE or Streaming HTTP):
        config = MCPServerConfig(
            url="http://mcp-hub:8765/sse"
        )

    Example (explicit transport):
        config = MCPServerConfig(
            url="http://localhost:8000",
            transport="streamable-http"
        )

    Usage:
        client = MCPClient(config)
        await client.connect()
        tools = await client.list_tools()
        result = await client.call_tool("tool_name", {"arg": "value"})
        await client.disconnect()
    """

    def __init__(self, config: MCPServerConfig, timeout: int = 600):
        """
        Initialize MCP client

        Args:
            config: Server configuration (auto-detects transport type)
            timeout: Timeout in seconds for MCP requests (default: 600 seconds)
        """
        self.config = config
        self.timeout = timeout
        self.is_connected = False
        self.tools: List[MCPToolSchema] = []

        # AICODE-NOTE: fastmcp.Client handles all transport logic
        self._client: Optional[Client] = None
        # AICODE-NOTE: Track reconnection attempts to prevent infinite loops
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 3

    async def connect(self) -> bool:
        """
        Connect to MCP server

        The transport type is automatically detected based on configuration:
        - URL -> SSE or Streaming HTTP (auto-detected by fastmcp)
        - Command -> stdio subprocess

        Returns:
            True if connection successful
        """
        import asyncio

        try:
            # Prepare transport configuration - fastmcp.Client handles auto-detection
            if self.config.url:
                # HTTP-based transport - fastmcp.Client auto-detects SSE or Streaming HTTP
                transport_config = self.config.url
                logger.info(
                    f"[MCPClient] Connecting to MCP server (HTTP, auto-detect): {self.config.url}"
                )
            elif self.config.command:
                # Stdio transport - fastmcp.Client accepts StdioTransport object
                transport_config = StdioTransport(
                    command=self.config.command,
                    args=self.config.args,
                    env=self.config.env or None,
                    cwd=str(self.config.cwd) if self.config.cwd else None,
                )
                logger.info(f"[MCPClient] Connecting to MCP server (stdio): {self.config.command}")
            else:
                raise ValueError(
                    "Either 'url' (for HTTP-based transport) or 'command' (for stdio) must be provided"
                )

            # Create fastmcp.Client - it handles all transport logic and auto-detection
            self._client = Client(
                transport=transport_config,
                timeout=float(self.timeout),
                init_timeout=10.0,  # Connection timeout
            )

            # AICODE-NOTE: Wrap connection attempt with asyncio.wait_for to ensure
            # we don't hang indefinitely if the server is unavailable
            connection_timeout = 30.0  # 30 seconds max for connection attempt

            # Connect using async context manager - fastmcp.Client handles connection
            await asyncio.wait_for(self._client.__aenter__(), timeout=connection_timeout)

            # Verify connection - fastmcp.Client should be connected after __aenter__
            if not self._client.is_connected():
                raise RuntimeError("Client initialization failed - not connected after __aenter__")

            # List available tools
            tools = await self._client.list_tools()
            if tools:
                self.tools = [
                    MCPToolSchema(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema or {},
                    )
                    for tool in tools
                ]
                logger.info(
                    f"[MCPClient] ✓ Connected. Available tools: {[t.name for t in self.tools]}"
                )

            self.is_connected = True
            self._reconnect_attempts = 0  # Reset reconnection attempts on successful connection
            return True

        except asyncio.TimeoutError:
            logger.error(
                f"[MCPClient] Connection timeout after {connection_timeout}s. "
                f"Server may be unavailable or not responding."
            )
            await self.disconnect()
            return False
        except Exception as e:
            logger.error(f"[MCPClient] Failed to connect: {e}")
            await self.disconnect()
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
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception as e:
                logger.debug(f"[MCPClient] Error during disconnect: {e}")
            self._client = None

        self.is_connected = False
        logger.info("[MCPClient] Disconnected")

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any], timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Call an MCP tool

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            timeout: Optional timeout override (seconds). Defaults to client timeout.

        Returns:
            Tool execution result in format:
            {
                "success": bool,
                "output": str,  # Human-readable output
                "is_error": bool,
                "result": dict,  # Full MCP result
                "content": list,  # Content items
                "error": str  # Only if success=False
            }
        """
        if not self.is_connected or not self._client:
            return {"success": False, "error": "Not connected to MCP server"}

        try:
            logger.debug(
                f"[MCPClient] Calling tool: {tool_name} with args: {self._limit_content_for_log(arguments)}"
            )

            # Call tool using fastmcp.Client
            call_timeout = timeout if timeout is not None else self.timeout
            call_kwargs: Dict[str, Any] = {}
            if call_timeout:
                call_kwargs["timeout"] = float(call_timeout)

            response = await self._client.call_tool(
                tool_name,
                arguments or {},
                **call_kwargs,
            )

            # Parse fastmcp response into our format
            return self._parse_tool_response(response)

        except Exception as e:
            logger.error(f"[MCPClient] Tool call failed: {e}", exc_info=True)

            # Try to reconnect if connection lost
            if "connection" in str(e).lower() or "closed" in str(e).lower():
                logger.warning("[MCPClient] Connection lost, attempting to reconnect...")
                if await self.reconnect():
                    logger.info("[MCPClient] Reconnected successfully, retrying tool call...")
                    # Retry the tool call once
                    try:
                        response = await self._client.call_tool(
                            tool_name,
                            arguments or {},
                        )
                        return self._parse_tool_response(response)
                    except Exception as retry_error:
                        return {
                            "success": False,
                            "error": f"Retry failed after reconnection: {str(retry_error)}",
                        }

            return {"success": False, "error": str(e)}

    def _limit_content_for_log(self, data: Any, max_length: int = 50) -> Any:
        """
        Limit content length in data for logging to avoid flooding logs with large payloads.

        Args:
            data: Data to limit (dict, list, str, or other)
            max_length: Maximum length for string values (default: 50 chars)

        Returns:
            Data with limited content length
        """
        if isinstance(data, dict):
            limited = {}
            for key, value in data.items():
                if isinstance(value, str) and len(value) > max_length:
                    limited[key] = f"{value[:max_length]}... (truncated, total: {len(value)} chars)"
                elif isinstance(value, (dict, list)):
                    limited[key] = self._limit_content_for_log(value, max_length)
                else:
                    limited[key] = value
            return limited
        elif isinstance(data, list):
            return [self._limit_content_for_log(item, max_length) for item in data]
        elif isinstance(data, str) and len(data) > max_length:
            return f"{data[:max_length]}... (truncated, total: {len(data)} chars)"
        else:
            return data

    def _parse_tool_response(self, response) -> Dict[str, Any]:
        """
        Parse fastmcp.Client tool response into our standard format

        Args:
            response: Response from fastmcp.Client.call_tool()

        Returns:
            Standardized tool response dict
        """
        content = list(response.content or [])

        # Parse content based on type for convenience string output
        output = []
        for item in content:
            if getattr(item, "type", None) == "text":
                output.append(getattr(item, "text", "") or "")
            elif getattr(item, "type", None) == "resource":
                resource = getattr(item, "resource", None)
                resource_uri = getattr(resource, "uri", "") if resource else ""
                output.append(f"Resource: {resource_uri}")
            elif getattr(item, "type", None) == "markdown":
                text_value = getattr(item, "text", None)
                if text_value:
                    output.append(text_value)
                else:
                    output.append(getattr(item, "markdown", "") or "")

        is_error = response.is_error

        return {
            "success": not is_error,
            "output": "\n".join(output).strip() if output else "Tool executed successfully",
            "is_error": is_error,
            "result": {
                "content": content,
                "structuredContent": response.structured_content,
                "data": response.data,
                "isError": is_error,
            },
            "content": content,
            "structured_content": response.structured_content,
            "data": response.data,
        }

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
        if not self.is_connected or not self._client:
            return []

        try:
            resources = await self._client.list_resources()

            return [
                {
                    "uri": res.uri,
                    "name": getattr(res, "name", res.uri),
                    "description": getattr(res, "description", "") or "",
                    "mimeType": getattr(res, "mimeType", None),
                }
                for res in resources
            ]

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
        if not self.is_connected or not self._client:
            return None

        try:
            contents = await self._client.read_resource(uri)

            return {
                "contents": [
                    {
                        "uri": getattr(content, "uri", uri),
                        "text": getattr(content, "text", None),
                        "mimeType": getattr(content, "mimeType", None),
                        "blob": getattr(content, "blob", None) or getattr(content, "base64", None),
                    }
                    for content in contents
                ]
            }

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
        if not self.is_connected or not self._client:
            return []

        try:
            prompts = await self._client.list_prompts()

            return [
                {
                    "name": prompt.name,
                    "description": getattr(prompt, "description", "") or "",
                    "arguments": [
                        {
                            "name": arg.name,
                            "description": getattr(arg, "description", "") or "",
                            "required": getattr(arg, "required", False),
                        }
                        for arg in getattr(prompt, "arguments", []) or []
                    ],
                }
                for prompt in prompts
            ]

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
        if not self.is_connected or not self._client:
            return None

        try:
            response = await self._client.get_prompt(name, arguments or {})

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
        if self._client:
            try:
                import asyncio

                # Try to clean up resources
                asyncio.create_task(self.disconnect())
            except:
                pass
