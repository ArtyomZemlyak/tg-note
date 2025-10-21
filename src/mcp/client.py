"""
MCP (Model Context Protocol) Client

This module provides a client for connecting to and communicating with MCP servers.
MCP is a protocol for connecting AI agents to external tools and data sources.

Supported MCP features:
- ✅ Tools (tools/list, tools/call)
- ✅ Resources (resources/list, resources/read)
- ✅ Prompts (prompts/list, prompts/get)
- ✅ JSON-RPC 2.0 communication
- ✅ Stdio transport
- ⚠️ Sampling (not yet implemented)
- ⚠️ Server-initiated requests/notifications (not yet implemented)

References:
- MCP Protocol: https://modelcontextprotocol.io/
- MCP Specification: https://modelcontextprotocol.io/docs/specification
- Python MCP SDK: https://github.com/modelcontextprotocol/python-sdk
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import aiohttp
from loguru import logger


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
    args: List[str] = None  # Empty for HTTP/SSE transport
    env: Optional[Dict[str, str]] = None
    cwd: Optional[Path] = None
    transport: str = "stdio"  # "stdio" or "sse" (HTTP Server-Sent Events)
    url: Optional[str] = None  # URL for SSE transport (e.g., "http://127.0.0.1:8765/sse")

    def __post_init__(self):
        if self.args is None:
            self.args = []
        # Validate config
        if self.transport == "sse":
            if not self.url:
                raise ValueError("URL is required for SSE transport")
        elif self.transport == "stdio":
            if not self.command:
                raise ValueError("Command is required for stdio transport")


class MCPClient:
    """
    Client for communicating with MCP servers via stdio or HTTP/SSE.

    Supports two transport modes:
    1. stdio: Launches MCP server as subprocess (JSON-RPC over stdin/stdout)
    2. sse: Connects to HTTP/SSE endpoint (JSON-RPC over HTTP Server-Sent Events)

    FastMCP SSE Protocol:
    - Client opens SSE connection (GET /sse/) and keeps it open
    - Server sends session_id via SSE 'endpoint' event
    - Client sends JSON-RPC requests via POST to /messages/?session_id=xxx
    - Server sends responses back via SSE stream as 'message' events
    - SSE connection must remain open to receive responses

    IMPORTANT: The SSE connection is NOT closed after getting the session_id.
    It must remain open to receive JSON-RPC responses from the server.
    Closing it prematurely causes ClosedResourceError on the server side.

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
        self.process: Optional[subprocess.Popen] = None
        self.session: Optional[aiohttp.ClientSession] = None  # For HTTP/SSE
        self.is_connected = False
        self.tools: List[MCPToolSchema] = []
        self._request_id = 0
        # AICODE-NOTE: Cache discovered HTTP JSON-RPC endpoint when using SSE transport
        self._rpc_url: Optional[str] = None
        # AICODE-NOTE: Store session_id for FastMCP SSE protocol
        self._session_id: Optional[str] = None
        # AICODE-NOTE: Keep SSE response open to receive server messages
        self._sse_response: Optional[aiohttp.ClientResponse] = None
        self._sse_reader_task: Optional[asyncio.Task] = None
        # AICODE-NOTE: Pending requests waiting for responses from SSE stream
        self._pending_requests: Dict[int, asyncio.Future] = {}
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
        """Connect via stdio transport"""
        logger.info(f"[MCPClient] Connecting to MCP server (stdio): {self.config.command}")

        # Launch server process
        self.process = subprocess.Popen(
            [self.config.command] + self.config.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.config.env,
            cwd=self.config.cwd,
            text=True,
            bufsize=1,
        )

        # Wait a bit for server to start
        await asyncio.sleep(0.5)

        # Check if process is still running
        if self.process.poll() is not None:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"Server process exited immediately. Stderr: {stderr}")

        # Initialize connection
        return await self._initialize()

    async def _connect_sse(self) -> bool:
        """Connect via HTTP/SSE transport (FastMCP protocol)"""
        logger.info(f"[MCPClient] Connecting to MCP server (SSE): {self.config.url}")

        # Create aiohttp session
        self.session = aiohttp.ClientSession()

        # Ensure URL has trailing slash to avoid redirects
        sse_url = self.config.url
        if not sse_url.endswith("/"):
            sse_url += "/"

        # Establish SSE connection and get session_id
        try:
            # Make GET request to establish SSE connection
            logger.debug(f"[MCPClient] Opening SSE connection to {sse_url}")
            response = await self.session.get(sse_url, timeout=aiohttp.ClientTimeout(total=10))

            if response.status != 200:
                raise RuntimeError(f"SSE connection failed with status {response.status}")

            # Parse SSE events to extract session_id
            # FastMCP sends an 'endpoint' event with the session_id
            # SSE format: "event: <type>\ndata: <content>\n\n"
            # Note: FastMCP may send data as either:
            #   1. JSON: {"uri": "/messages/?session_id=..."}
            #   2. Plain text: /messages/?session_id=...
            # We handle both formats for compatibility

            lines_read = 0
            max_lines = 100  # Safety limit
            event_type = None

            async for line in response.content:
                lines_read += 1
                if lines_read > max_lines:
                    break

                line_str = line.decode("utf-8").strip()

                # Skip empty lines
                if not line_str:
                    continue

                # Parse event type
                if line_str.startswith("event:"):
                    event_type = line_str[6:].strip()
                    logger.debug(f"[MCPClient] SSE event: {event_type}")
                    continue

                # Parse event data
                if line_str.startswith("data:") and event_type == "endpoint":
                    data_str = line_str[5:].strip()

                    # Check if data is empty before parsing
                    if not data_str:
                        logger.debug("[MCPClient] SSE data field is empty, skipping")
                        continue

                    # Try to parse as JSON first (newer FastMCP format)
                    try:
                        data_json = json.loads(data_str)
                        logger.debug(f"[MCPClient] SSE endpoint data (JSON): {data_json}")

                        # Extract session_id from URL query params in 'uri' field
                        if "uri" in data_json:
                            from urllib.parse import parse_qs, urlparse

                            parsed = urlparse(data_json["uri"])
                            qs = parse_qs(parsed.query)
                            if "session_id" in qs:
                                self._session_id = qs["session_id"][0]
                                logger.info(
                                    f"[MCPClient] ✓ SSE session established: {self._session_id}"
                                )
                                break

                        # Alternative: session_id might be in the data directly
                        if "session_id" in data_json:
                            self._session_id = data_json["session_id"]
                            logger.info(
                                f"[MCPClient] ✓ SSE session established: {self._session_id}"
                            )
                            break
                    except json.JSONDecodeError:
                        # FastMCP might send plain text URI instead of JSON
                        # Try to parse as plain URI string (e.g., "/messages/?session_id=...")
                        from urllib.parse import parse_qs, urlparse

                        logger.debug(f"[MCPClient] SSE endpoint data (plain text): {data_str}")

                        try:
                            parsed = urlparse(data_str)
                            qs = parse_qs(parsed.query)
                            if "session_id" in qs:
                                self._session_id = qs["session_id"][0]
                                logger.info(
                                    f"[MCPClient] ✓ SSE session established (plain text format): {self._session_id}"
                                )
                                break
                        except Exception as parse_err:
                            logger.warning(
                                f"[MCPClient] Failed to parse SSE data as JSON or URI: {parse_err}. "
                                f"Data (first 200 chars): {data_str[:200]}"
                            )
                            continue

            # AICODE-NOTE: Keep SSE response open to receive server messages
            # DO NOT close the response - we need it to receive JSON-RPC responses
            if not self._session_id:
                error_msg = (
                    f"Failed to extract session_id from SSE endpoint at {sse_url}. "
                    f"Read {lines_read} lines but no valid session_id found. "
                    f"Check if the MCP Hub server is running and accessible."
                )
                logger.error(f"[MCPClient] {error_msg}")
                raise RuntimeError(error_msg)

            # Derive the JSON-RPC endpoint URL from SSE URL
            parts = urlsplit(self.config.url)
            path = parts.path or "/"
            if path.endswith("/sse") or path.endswith("/sse/"):
                base_path = path[:-4] if path.endswith("/sse") else path[:-5]
                messages_path = f"{base_path}/messages/"
                self._rpc_url = urlunsplit((parts.scheme, parts.netloc, messages_path, "", ""))
            else:
                # Default to /messages/ at same base
                self._rpc_url = urlunsplit((parts.scheme, parts.netloc, "/messages/", "", ""))

            logger.info(f"[MCPClient] Using RPC endpoint: {self._rpc_url}")

            # Store SSE response and start background task to read from stream
            self._sse_response = response
            self._sse_reader_task = asyncio.create_task(self._sse_reader())
            logger.debug("[MCPClient] Started SSE reader task")

        except asyncio.TimeoutError:
            error_msg = (
                f"SSE connection timeout - server at {sse_url} did not respond within 10 seconds. "
                f"Verify that:\n"
                f"  1. MCP Hub server is running\n"
                f"  2. URL is correct (currently: {self.config.url})\n"
                f"  3. Network connectivity is available\n"
                f"  4. Firewall allows the connection"
            )
            logger.error(f"[MCPClient] {error_msg}")
            raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"[MCPClient] Failed to establish SSE connection: {e}", exc_info=True)
            raise RuntimeError(f"SSE connection failed: {e}")

        # Initialize connection (send initialize request)
        return await self._initialize()

    async def _initialize(self) -> bool:
        """Initialize MCP connection (common for both transports)"""
        # Send initialize request
        init_response = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                },
                "clientInfo": {"name": "tg-note-agent", "version": "0.1.0"},
            },
        )

        if not init_response or "error" in init_response:
            error = init_response.get("error", "Unknown error") if init_response else "No response"
            raise RuntimeError(f"Failed to initialize: {error}")

        # Send initialized notification
        await self._send_notification("notifications/initialized")

        # List available tools
        tools_response = await self._send_request("tools/list", {})

        if tools_response and "result" in tools_response:
            tools_list = tools_response["result"].get("tools", [])
            self.tools = [
                MCPToolSchema(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                )
                for tool in tools_list
            ]
            logger.info(f"[MCPClient] ✓ Connected. Available tools: {[t.name for t in self.tools]}")

        self.is_connected = True
        self._reconnect_attempts = 0  # Reset reconnection attempts on successful connection
        return True

    async def reconnect(self) -> bool:
        """
        Reconnect to MCP server
        
        Returns:
            True if reconnection successful
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error(f"[MCPClient] Maximum reconnection attempts ({self._max_reconnect_attempts}) exceeded")
            return False
            
        self._reconnect_attempts += 1
        logger.info(f"[MCPClient] Attempting to reconnect (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})...")
        await self.disconnect()
        success = await self.connect()
        if success:
            self._reconnect_attempts = 0  # Reset on successful reconnection
        return success

    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        # Cancel SSE reader task if running
        if self._sse_reader_task and not self._sse_reader_task.done():
            self._sse_reader_task.cancel()
            try:
                await self._sse_reader_task
            except asyncio.CancelledError:
                pass
            self._sse_reader_task = None

        # Close SSE response if open
        if self._sse_response:
            self._sse_response.close()
            self._sse_response = None

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None

        if self.session:
            await self.session.close()
            self.session = None

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
        if not self.is_connected:
            return {"success": False, "error": "Not connected to MCP server"}

        try:
            logger.debug(f"[MCPClient] Calling tool: {tool_name} with args: {arguments}")

            response = await self._send_request(
                "tools/call", {"name": tool_name, "arguments": arguments}
            )

            if not response:
                # Check if SSE reader task failed
                if self._sse_reader_task and self._sse_reader_task.done():
                    try:
                        await self._sse_reader_task
                    except Exception as e:
                        logger.warning(f"[MCPClient] SSE connection lost: {e}. Attempting to reconnect...")
                        # Try to reconnect
                        if await self.reconnect():
                            logger.info("[MCPClient] Reconnected successfully, retrying tool call...")
                            # Retry the tool call once
                            response = await self._send_request(
                                "tools/call", {"name": tool_name, "arguments": arguments}
                            )
                            if not response:
                                return {"success": False, "error": "No response from server after reconnection"}
                        else:
                            return {"success": False, "error": f"SSE connection lost and reconnection failed: {e}"}
                else:
                    return {"success": False, "error": "No response from server"}

            if "error" in response:
                error = response["error"]
                return {
                    "success": False,
                    "error": f"{error.get('message', 'Unknown error')} (code: {error.get('code', -1)})",
                }

            # Extract result from response
            result = response.get("result", {})
            content = result.get("content", [])

            # Parse content based on type
            output = []
            for item in content:
                if item.get("type") == "text":
                    output.append(item.get("text", ""))
                elif item.get("type") == "resource":
                    output.append(f"Resource: {item.get('resource', {}).get('uri', '')}")

            return {
                "success": True,
                "output": "\n".join(output) if output else "Tool executed successfully",
                "is_error": result.get("isError", False),
            }

        except Exception as e:
            logger.error(f"[MCPClient] Tool call failed: {e}", exc_info=True)
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
        if not self.is_connected:
            return []

        try:
            response = await self._send_request("resources/list", {})

            if response and "result" in response:
                return response["result"].get("resources", [])

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
        if not self.is_connected:
            return None

        try:
            response = await self._send_request("resources/read", {"uri": uri})

            if response and "result" in response:
                return response["result"]

            if "error" in response:
                logger.error(f"[MCPClient] Resource read error: {response['error']}")

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
        if not self.is_connected:
            return []

        try:
            response = await self._send_request("prompts/list", {})

            if response and "result" in response:
                return response["result"].get("prompts", [])

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
        if not self.is_connected:
            return None

        try:
            params = {"name": name}
            if arguments:
                params["arguments"] = arguments

            response = await self._send_request("prompts/get", params)

            if response and "result" in response:
                return response["result"]

            if "error" in response:
                logger.error(f"[MCPClient] Prompt get error: {response['error']}")

            return None

        except Exception as e:
            logger.error(f"[MCPClient] Failed to get prompt {name}: {e}")
            return None

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send JSON-RPC request to server (stdio or HTTP)

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            Response dict or None if error
        """
        if self.config.transport == "sse":
            return await self._send_request_http(method, params)
        else:
            return await self._send_request_stdio(method, params)

    async def _send_request_stdio(
        self, method: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Send request via stdio transport"""
        if not self.process or not self.process.stdin or not self.process.stdout:
            return None

        self._request_id += 1
        request = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()

            # Read response
            response_line = self.process.stdout.readline()
            if not response_line:
                return None

            response = json.loads(response_line)
            return response

        except Exception as e:
            logger.error(f"[MCPClient] stdio request failed: {e}", exc_info=True)
            return None

    async def _sse_reader(self) -> None:
        """
        Background task to read responses from SSE stream.

        FastMCP sends JSON-RPC responses as SSE 'message' events.
        This task reads those events and matches them to pending requests.
        """
        if not self._sse_response:
            logger.error("[MCPClient] SSE reader started but no response available")
            return

        try:
            logger.debug("[MCPClient] SSE reader task started")
            event_type = None

            async for line in self._sse_response.content:
                line_str = line.decode("utf-8").strip()

                # Skip empty lines
                if not line_str:
                    continue

                # Parse event type
                if line_str.startswith("event:"):
                    event_type = line_str[6:].strip()
                    continue

                # Parse event data
                if line_str.startswith("data:"):
                    data_str = line_str[5:].strip()

                    if not data_str:
                        continue

                    # Only process 'message' events (JSON-RPC responses)
                    if event_type == "message":
                        try:
                            response = json.loads(data_str)

                            # Match response to pending request by ID
                            if "id" in response and response["id"] in self._pending_requests:
                                future = self._pending_requests.pop(response["id"])
                                if not future.done():
                                    future.set_result(response)
                                    logger.debug(
                                        f"[MCPClient] Matched response for request ID {response['id']}"
                                    )
                                else:
                                    logger.warning(
                                        f"[MCPClient] Received response for already completed request ID {response['id']}"
                                    )
                            else:
                                logger.debug(
                                    f"[MCPClient] Received response with no matching request: {response.get('id')}. "
                                    f"Pending requests: {list(self._pending_requests.keys())}"
                                )

                        except json.JSONDecodeError as e:
                            logger.warning(f"[MCPClient] Failed to parse SSE message data: {e}")
                            continue

        except asyncio.CancelledError:
            logger.debug("[MCPClient] SSE reader task cancelled")
            raise
        except Exception as e:
            logger.error(f"[MCPClient] SSE reader task error: {e}", exc_info=True)
            # Cancel all pending requests when SSE reader fails
            for request_id, future in list(self._pending_requests.items()):
                if not future.done():
                    future.cancel()
            self._pending_requests.clear()
        finally:
            logger.debug("[MCPClient] SSE reader task finished")

    async def _send_request_http(
        self, method: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Send request via HTTP/SSE transport (FastMCP protocol)"""
        if not self.session:
            return None
        
        # Check if SSE reader task is still running
        if self._sse_reader_task and self._sse_reader_task.done():
            try:
                await self._sse_reader_task
            except Exception as e:
                logger.error(f"[MCPClient] SSE reader task failed before request: {e}")
                return None
        
        # Check if SSE response is still active
        if self._sse_response and self._sse_response.closed:
            logger.error("[MCPClient] SSE response is closed, cannot send request")
            return None

        self._request_id += 1
        request = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}
        logger.debug(f"[MCPClient] Sending request ID {self._request_id}: {method}")

        # Use the discovered RPC URL with session_id
        if self._rpc_url and self._session_id:
            # Add session_id as query parameter
            from urllib.parse import urlencode

            url_with_session = f"{self._rpc_url}?{urlencode({'session_id': self._session_id})}"

            try:
                # Create a Future to wait for the response from SSE stream
                future = asyncio.get_event_loop().create_future()
                self._pending_requests[self._request_id] = future

                # Send the request (server returns 202 Accepted, response comes via SSE)
                async with self.session.post(
                    url_with_session, json=request, timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status not in (200, 202):
                        # Remove pending request on error
                        self._pending_requests.pop(self._request_id, None)
                        logger.error(
                            f"[MCPClient] HTTP request failed with status {response.status} at {url_with_session}"
                        )
                        return None

                # Wait for response from SSE stream (with timeout)
                try:
                    # Check if SSE reader task is still running
                    if self._sse_reader_task and self._sse_reader_task.done():
                        # SSE reader task has finished, check if it was due to an error
                        try:
                            await self._sse_reader_task
                        except Exception as e:
                            logger.error(f"[MCPClient] SSE reader task failed: {e}")
                            self._pending_requests.pop(self._request_id, None)
                            return None
                    
                    result = await asyncio.wait_for(future, timeout=float(self.timeout))
                    return result
                except asyncio.TimeoutError:
                    self._pending_requests.pop(self._request_id, None)
                    logger.error(
                        f"[MCPClient] Timeout waiting for response to request ID {self._request_id}"
                    )
                    return None

            except Exception as e:
                self._pending_requests.pop(self._request_id, None)
                logger.error(f"[MCPClient] HTTP request exception: {e}", exc_info=True)
                return None

        # Fallback to old behavior if no session_id (shouldn't happen with FastMCP)
        logger.warning("[MCPClient] No session_id available, falling back to legacy behavior")

        # Build candidate RPC URLs. Some servers expose SSE at /sse (GET only)
        # but handle JSON-RPC POST at a different path (e.g., /messages or /rpc).
        candidates: List[str] = []
        if self._rpc_url:
            candidates.append(self._rpc_url)

        # Ensure URL has trailing slash
        url_with_slash = self.config.url if self.config.url.endswith("/") else self.config.url + "/"
        if url_with_slash not in candidates:
            candidates.append(url_with_slash)

        # Derive common alternatives from an /sse URL
        try:
            parts = urlsplit(self.config.url)
            path = parts.path or "/"
            if path.endswith("/sse") or path.endswith("/sse/"):
                base_path = path[:-4] if path.endswith("/sse") else path[:-5]

                def make_url(p: str) -> str:
                    # Ensure trailing slash
                    if not p.endswith("/"):
                        p += "/"
                    return urlunsplit((parts.scheme, parts.netloc, p, "", ""))

                for p in (f"{base_path}/messages", f"{base_path}/rpc", base_path or "/"):
                    u = make_url(p)
                    if u not in candidates:
                        candidates.append(u)
        except Exception:
            pass

        errors: List[str] = []
        for url in candidates:
            try:
                async with self.session.post(
                    url, json=request, timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status in (200, 202):
                        # Cache working RPC endpoint
                        self._rpc_url = url
                        result = await response.json()
                        return result
                    else:
                        msg = f"{response.status} at {url}"
                        errors.append(msg)
                        # Try next candidate on 404/405/307/400; otherwise stop early
                        if response.status not in (307, 400, 404, 405):
                            logger.error(f"[MCPClient] HTTP request failed with status {msg}")
                            return None
            except Exception as e:
                errors.append(f"exception {type(e).__name__} at {url}: {e}")
                continue

        logger.error(
            f"[MCPClient] HTTP request failed for all endpoints. Tried: {', '.join(errors)}"
        )
        return None

    async def _send_notification(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send JSON-RPC notification (no response expected)

        Args:
            method: Notification method name
            params: Optional parameters
        """
        if self.config.transport == "sse":
            await self._send_notification_http(method, params)
        else:
            await self._send_notification_stdio(method, params)

    async def _send_notification_stdio(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send notification via stdio"""
        if not self.process or not self.process.stdin:
            return

        notification = {"jsonrpc": "2.0", "method": method, "params": params or {}}

        try:
            notification_json = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_json)
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"[MCPClient] stdio notification failed: {e}", exc_info=True)

    async def _send_notification_http(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send notification via HTTP (fire and forget, FastMCP protocol)"""
        if not self.session:
            return

        notification = {"jsonrpc": "2.0", "method": method, "params": params or {}}

        # Use the discovered RPC URL with session_id
        if self._rpc_url and self._session_id:
            from urllib.parse import urlencode

            url_with_session = f"{self._rpc_url}?{urlencode({'session_id': self._session_id})}"

            try:
                await self.session.post(
                    url_with_session, json=notification, timeout=aiohttp.ClientTimeout(total=5)
                )
                return
            except Exception as e:
                logger.debug(f"[MCPClient] HTTP notification failed: {e}")
                return

        # Fallback to old behavior
        urls_to_try: List[str] = []
        if self._rpc_url:
            urls_to_try.append(self._rpc_url)

        url_with_slash = self.config.url if self.config.url.endswith("/") else self.config.url + "/"
        if url_with_slash not in urls_to_try:
            urls_to_try.append(url_with_slash)

        for url in urls_to_try:
            try:
                await self.session.post(
                    url, json=notification, timeout=aiohttp.ClientTimeout(total=5)
                )
                return
            except Exception:
                continue
        logger.error("[MCPClient] HTTP notification failed: all endpoints unreachable")

    def __del__(self):
        """Cleanup on deletion"""
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
