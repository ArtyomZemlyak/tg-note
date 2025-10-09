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

    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    cwd: Optional[Path] = None
    transport: str = "stdio"  # "stdio" or "sse" (HTTP Server-Sent Events)
    url: Optional[str] = None  # URL for SSE transport (e.g., "http://127.0.0.1:8765/sse")


class MCPClient:
    """
    Client for communicating with MCP servers via stdio.

    This client launches MCP server processes and communicates with them
    using JSON-RPC 2.0 over stdio (stdin/stdout).

    Supported operations:
    - Tools: list_tools(), call_tool()
    - Resources: list_resources(), read_resource()
    - Prompts: list_prompts(), get_prompt()

    Example:
        config = MCPServerConfig(
            command="npx",
            args=["@example/mcp-server"]
        )
        client = MCPClient(config)
        await client.connect()

        # List and call tools
        tools = await client.list_tools()
        result = await client.call_tool("tool_name", {"param": "value"})

        # List and read resources
        resources = await client.list_resources()
        content = await client.read_resource("file:///path/to/file.txt")

        # List and get prompts
        prompts = await client.list_prompts()
        prompt = await client.get_prompt("prompt_name", {"arg": "value"})
    """

    def __init__(self, config: MCPServerConfig):
        """
        Initialize MCP client

        Args:
            config: Server configuration (command, args, env)
        """
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.is_connected = False
        self.tools: List[MCPToolSchema] = []
        self._request_id = 0

    async def connect(self) -> bool:
        """
        Connect to MCP server

        Returns:
            True if connection successful
        """
        try:
            logger.info(f"[MCPClient] Connecting to MCP server: {self.config.command}")

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

            # Send initialize request
            init_response = await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        # Client supports roots (workspace roots)
                        "roots": {"listChanged": True},
                        # Note: sampling not implemented yet, so removed from capabilities
                    },
                    "clientInfo": {"name": "tg-note-agent", "version": "0.1.0"},
                },
            )

            if not init_response or "error" in init_response:
                error = (
                    init_response.get("error", "Unknown error") if init_response else "No response"
                )
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
                logger.info(
                    f"[MCPClient] ✓ Connected. Available tools: {[t.name for t in self.tools]}"
                )

            self.is_connected = True
            return True

        except FileNotFoundError as e:
            logger.error(
                f"[MCPClient] Failed to connect: Command not found '{self.config.command}'. "
                f"Please ensure the command is installed and available in PATH. Error: {e}"
            )
            await self.disconnect()
            return False
        except Exception as e:
            logger.error(
                f"[MCPClient] Failed to connect to MCP server '{self.config.command}': {e}",
                exc_info=True,
            )
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None

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
        Send JSON-RPC request to server

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            Response dict or None if error
        """
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
            logger.error(f"[MCPClient] Request failed: {e}", exc_info=True)
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
        if not self.process or not self.process.stdin:
            return

        notification = {"jsonrpc": "2.0", "method": method, "params": params or {}}

        try:
            notification_json = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_json)
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"[MCPClient] Notification failed: {e}", exc_info=True)

    def __del__(self):
        """Cleanup on deletion"""
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
