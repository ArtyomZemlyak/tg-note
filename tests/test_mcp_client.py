"""Comprehensive tests for MCP Client implementation.

Tests the MCPClient wrapper around fastmcp.Client with different
transport types, operations, and error scenarios.
"""

from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest
from fastmcp.client.transports import StdioTransport

from src.mcp.client import MCPClient, MCPServerConfig


class _BaseFakeClient:
    """Test double for fastmcp.Client.

    AICODE-NOTE: This base class simulates fastmcp.Client behavior for testing.
    It implements all methods that MCPClient uses.
    """

    def __init__(self, transport: Any, timeout: float, init_timeout: float):
        self.transport = transport
        self.timeout = timeout
        self.init_timeout = init_timeout
        self._connected = False
        self._tools: List[Any] = []

    async def __aenter__(self):
        self._connected = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._connected = False
        return False

    def is_connected(self) -> bool:
        return self._connected

    async def list_tools(self):
        return self._tools

    async def call_tool(self, *args, **kwargs):
        raise AssertionError("call_tool should not be invoked in this test")

    async def list_resources(self):
        return []

    async def read_resource(self, uri: str):
        return []

    async def list_prompts(self):
        return []

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None):
        return None


@pytest.mark.asyncio
async def test_connect_stdio_uses_stdio_transport(monkeypatch):
    """Test that stdio transport is correctly configured for command-based servers."""
    captured: Dict[str, Any] = {}

    class FakeClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            captured["transport"] = transport
            captured["timeout"] = timeout
            captured["init_timeout"] = init_timeout
            self._tools = [
                SimpleNamespace(name="docling", description="Docling tool", inputSchema={})
            ]

    monkeypatch.setattr("src.mcp.client.Client", FakeClient)

    config = MCPServerConfig(command="python", args=["server.py"], transport="stdio")
    client = MCPClient(config)

    assert await client.connect() is True
    assert isinstance(captured["transport"], StdioTransport)
    assert captured["transport"].command == "python"
    assert captured["transport"].args == ["server.py"]
    assert captured["timeout"] == pytest.approx(float(client.timeout))
    assert captured["init_timeout"] == pytest.approx(10.0)

    tools = client.get_tools()
    assert len(tools) == 1
    assert tools[0].name == "docling"

    await client.disconnect()


@pytest.mark.asyncio
async def test_connect_url_uses_http_transport(monkeypatch):
    """Test that URL-based transport is correctly configured for HTTP servers."""
    captured: Dict[str, Any] = {}

    class FakeClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            captured["transport"] = transport
            captured["timeout"] = timeout
            self._tools = [
                SimpleNamespace(name="test_tool", description="Test tool", inputSchema={})
            ]

    monkeypatch.setattr("src.mcp.client.Client", FakeClient)

    config = MCPServerConfig(url="http://localhost:8765/sse")
    client = MCPClient(config)

    assert await client.connect() is True
    # fastmcp.Client receives URL string directly for HTTP-based transports
    assert captured["transport"] == "http://localhost:8765/sse"
    assert client.is_connected is True

    await client.disconnect()


@pytest.mark.asyncio
async def test_connect_with_env_variables(monkeypatch):
    """Test that stdio transport supports environment variables."""
    captured: Dict[str, Any] = {}

    class FakeClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            captured["transport"] = transport
            self._tools = []

    monkeypatch.setattr("src.mcp.client.Client", FakeClient)

    env = {"API_KEY": "secret123"}
    config = MCPServerConfig(command="python", args=["server.py"], env=env)
    client = MCPClient(config)

    assert await client.connect() is True
    assert isinstance(captured["transport"], StdioTransport)
    assert captured["transport"].env == env

    await client.disconnect()


@pytest.mark.asyncio
async def test_connect_failure_handling(monkeypatch):
    """Test that connection failures are properly handled."""

    class FailingClient(_BaseFakeClient):
        async def __aenter__(self):
            raise RuntimeError("Connection failed")

    monkeypatch.setattr("src.mcp.client.Client", FailingClient)

    config = MCPServerConfig(command="python", args=["server.py"])
    client = MCPClient(config)

    assert await client.connect() is False
    assert client.is_connected is False
    assert client._client is None


@pytest.mark.asyncio
async def test_disconnect_without_connect(monkeypatch):
    """Test that disconnect works even if never connected."""
    config = MCPServerConfig(command="python", args=["server.py"])
    client = MCPClient(config)

    # Should not raise an error
    await client.disconnect()
    assert client.is_connected is False


@pytest.mark.asyncio
async def test_call_tool_when_not_connected():
    """Test that tool calls fail gracefully when not connected."""
    config = MCPServerConfig(command="python", args=["server.py"])
    client = MCPClient(config)

    result = await client.call_tool("test_tool", {"arg": "value"})

    assert result["success"] is False
    assert "Not connected" in result["error"]


@pytest.mark.asyncio
async def test_reconnect_on_connection_loss(monkeypatch):
    """Test automatic reconnection on connection loss."""
    connection_attempts = []
    call_counts = [0]  # Use list to make it mutable across instances

    class ReconnectableClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            self._tools = [
                SimpleNamespace(name="test_tool", description="Test tool", inputSchema={})
            ]

        async def __aenter__(self):
            connection_attempts.append(True)
            await super().__aenter__()
            return self

        async def call_tool(self, name: str, arguments=None, **kwargs):
            call_counts[0] += 1
            if call_counts[0] == 1:
                # First call fails with connection error
                raise RuntimeError("Connection closed")
            # Second call (after reconnection) succeeds
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Success")],
                structured_content=None,
                data=None,
                is_error=False,
            )

    monkeypatch.setattr("src.mcp.client.Client", ReconnectableClient)

    config = MCPServerConfig(command="python", args=["server.py"])
    client = MCPClient(config)

    await client.connect()
    assert len(connection_attempts) == 1

    # Call tool - should fail first time and trigger reconnection
    result = await client.call_tool("test_tool", {})

    # Should have reconnected
    assert len(connection_attempts) == 2
    assert result["success"] is True
    assert result["output"] == "Success"

    await client.disconnect()


@pytest.mark.asyncio
async def test_reconnect_max_attempts(monkeypatch):
    """Test that reconnection stops after max attempts."""
    connection_attempts = []
    call_attempts = [0]  # Track tool call attempts

    class AlwaysFailingClient(_BaseFakeClient):
        async def __aenter__(self):
            connection_attempts.append(True)
            if len(connection_attempts) > 1:
                # Fail reconnection attempts
                raise RuntimeError("Connection failed")
            await super().__aenter__()
            return self

        async def call_tool(self, name: str, arguments=None, **kwargs):
            call_attempts[0] += 1
            # Always fail with connection error
            raise RuntimeError("Connection closed")

    monkeypatch.setattr("src.mcp.client.Client", AlwaysFailingClient)

    config = MCPServerConfig(command="python", args=["server.py"])
    client = MCPClient(config, timeout=600)

    await client.connect()
    initial_attempts = len(connection_attempts)

    # Call tool - should fail, trigger reconnection, but fail to reconnect
    result = await client.call_tool("test_tool", {})

    # Should have attempted reconnection but failed
    assert len(connection_attempts) == initial_attempts + 1
    assert result["success"] is False
    # The error message will be from the reconnection failure
    assert "Connection closed" in result["error"] or "Retry failed" in result["error"]

    await client.disconnect()


@pytest.mark.asyncio
async def test_call_tool_and_metadata(monkeypatch):
    """Test tool calling with various content types and metadata extraction."""
    captured: Dict[str, Any] = {"raise_on_error": []}

    class FakeClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            self._tools = [
                SimpleNamespace(name="docling", description="Docling tool", inputSchema={})
            ]
            self._resources = [
                SimpleNamespace(
                    uri="file:///tmp/output.txt",
                    name="output",
                    description="Example resource",
                    mimeType="text/plain",
                )
            ]
            self._resource_contents = [
                SimpleNamespace(
                    uri="file:///tmp/output.txt",
                    text="hello world",
                    mimeType="text/plain",
                )
            ]
            self._prompts = [
                SimpleNamespace(
                    name="demo",
                    description="Demo prompt",
                    arguments=[SimpleNamespace(name="arg1", description="Argument", required=True)],
                )
            ]
            self._prompt_result = SimpleNamespace(
                description="Demo prompt description",
                messages=[
                    SimpleNamespace(
                        role="user",
                        content=SimpleNamespace(type="text", text="Prompt body"),
                    )
                ],
            )

        async def call_tool(self, name: str, arguments=None, **kwargs):
            captured["raise_on_error"].append(kwargs.get("raise_on_error"))
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Processing complete")],
                structured_content={"result": {"status": "ok"}},
                data={"status": "ok"},
                is_error=False,
            )

        async def list_resources(self):
            return list(self._resources)

        async def read_resource(self, uri: str):
            return list(self._resource_contents)

        async def list_prompts(self):
            return list(self._prompts)

        async def get_prompt(self, name: str, arguments=None):
            return self._prompt_result

    monkeypatch.setattr("src.mcp.client.Client", FakeClient)

    config = MCPServerConfig(url="http://localhost:8000/sse", transport="sse")
    client = MCPClient(config)
    assert await client.connect() is True

    # Test tool call
    result = await client.call_tool("docling", {"foo": "bar"})
    assert result["success"] is True
    assert result["output"] == "Processing complete"
    assert result["is_error"] is False
    assert result["data"] == {"status": "ok"}
    assert result["structured_content"] == {"result": {"status": "ok"}}
    assert result["result"]["structuredContent"] == {"result": {"status": "ok"}}
    assert captured["raise_on_error"] == [False]

    # Test list resources
    resources = await client.list_resources()
    assert resources == [
        {
            "uri": "file:///tmp/output.txt",
            "name": "output",
            "description": "Example resource",
            "mimeType": "text/plain",
        }
    ]

    # Test read resource
    resource_contents = await client.read_resource("file:///tmp/output.txt")
    assert resource_contents == {
        "contents": [
            {
                "uri": "file:///tmp/output.txt",
                "text": "hello world",
                "mimeType": "text/plain",
                "blob": None,
            }
        ]
    }

    # Test list prompts
    prompts = await client.list_prompts()
    assert prompts == [
        {
            "name": "demo",
            "description": "Demo prompt",
            "arguments": [
                {"name": "arg1", "description": "Argument", "required": True},
            ],
        }
    ]

    # Test get prompt
    prompt = await client.get_prompt("demo")
    assert prompt == {
        "description": "Demo prompt description",
        "messages": [
            {"role": "user", "content": {"type": "text", "text": "Prompt body"}},
        ],
    }

    await client.disconnect()


@pytest.mark.asyncio
async def test_tool_call_with_error_response(monkeypatch):
    """Test tool calling when MCP server returns an error."""

    class ErrorClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            self._tools = [
                SimpleNamespace(name="failing_tool", description="Tool that fails", inputSchema={})
            ]

        async def call_tool(self, name: str, arguments=None, **kwargs):
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Error occurred")],
                structured_content=None,
                data=None,
                is_error=True,  # MCP server returned an error
            )

    monkeypatch.setattr("src.mcp.client.Client", ErrorClient)

    config = MCPServerConfig(command="python", args=["server.py"])
    client = MCPClient(config)
    await client.connect()

    result = await client.call_tool("failing_tool", {})

    assert result["success"] is False  # success=False when is_error=True
    assert result["is_error"] is True
    assert result["output"] == "Error occurred"

    await client.disconnect()


@pytest.mark.asyncio
async def test_context_manager_usage(monkeypatch):
    """Test using MCPClient as async context manager."""

    class FakeClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            self._tools = []

    monkeypatch.setattr("src.mcp.client.Client", FakeClient)

    config = MCPServerConfig(command="python", args=["server.py"])

    async with MCPClient(config) as client:
        assert client.is_connected is True

    # Should be disconnected after context manager exits
    assert client.is_connected is False


@pytest.mark.asyncio
async def test_server_config_auto_detection():
    """Test that MCPServerConfig auto-detects transport type."""
    # URL provided - should auto-detect HTTP
    config_url = MCPServerConfig(url="http://localhost:8000/sse")
    assert config_url.transport == "http"

    # Command provided - should auto-detect stdio
    config_cmd = MCPServerConfig(command="python", args=["server.py"])
    assert config_cmd.transport == "stdio"


@pytest.mark.asyncio
async def test_server_config_requires_url_or_command():
    """Test that MCPServerConfig requires either URL or command."""
    with pytest.raises(ValueError, match="Either 'url'.*or 'command'.*must be provided"):
        MCPServerConfig()


@pytest.mark.asyncio
async def test_list_tools_returns_correct_format(monkeypatch):
    """Test that list_tools returns tools in MCP protocol format."""

    class FakeClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            self._tools = [
                SimpleNamespace(
                    name="tool1",
                    description="First tool",
                    inputSchema={"type": "object", "properties": {"param": {"type": "string"}}},
                ),
                SimpleNamespace(name="tool2", description="Second tool", inputSchema={}),
            ]

    monkeypatch.setattr("src.mcp.client.Client", FakeClient)

    config = MCPServerConfig(command="python", args=["server.py"])
    client = MCPClient(config)
    await client.connect()

    tools = await client.list_tools()

    assert len(tools) == 2
    assert tools[0]["name"] == "tool1"
    assert tools[0]["description"] == "First tool"
    assert "properties" in tools[0]["inputSchema"]
    assert tools[1]["name"] == "tool2"

    await client.disconnect()


@pytest.mark.asyncio
async def test_parse_tool_response_with_markdown_content(monkeypatch):
    """Test parsing tool response with markdown content type."""

    class FakeClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            self._tools = [SimpleNamespace(name="md_tool", description="", inputSchema={})]

        async def call_tool(self, name: str, arguments=None, **kwargs):
            return SimpleNamespace(
                content=[SimpleNamespace(type="markdown", text="# Markdown Content")],
                structured_content=None,
                data=None,
                is_error=False,
            )

    monkeypatch.setattr("src.mcp.client.Client", FakeClient)

    config = MCPServerConfig(command="python", args=["server.py"])
    client = MCPClient(config)
    await client.connect()

    result = await client.call_tool("md_tool", {})

    assert result["success"] is True
    assert "# Markdown Content" in result["output"]

    await client.disconnect()


@pytest.mark.asyncio
async def test_parse_tool_response_with_resource_content(monkeypatch):
    """Test parsing tool response with resource content type."""

    class FakeClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            self._tools = [SimpleNamespace(name="res_tool", description="", inputSchema={})]

        async def call_tool(self, name: str, arguments=None, **kwargs):
            resource_obj = SimpleNamespace(uri="file:///test.txt")
            return SimpleNamespace(
                content=[SimpleNamespace(type="resource", resource=resource_obj)],
                structured_content=None,
                data=None,
                is_error=False,
            )

    monkeypatch.setattr("src.mcp.client.Client", FakeClient)

    config = MCPServerConfig(command="python", args=["server.py"])
    client = MCPClient(config)
    await client.connect()

    result = await client.call_tool("res_tool", {})

    assert result["success"] is True
    assert "Resource: file:///test.txt" in result["output"]

    await client.disconnect()


@pytest.mark.asyncio
async def test_empty_content_response(monkeypatch):
    """Test handling of tool response with no content."""

    class FakeClient(_BaseFakeClient):
        def __init__(self, transport: Any, timeout: float, init_timeout: float):
            super().__init__(transport, timeout, init_timeout)
            self._tools = [SimpleNamespace(name="empty_tool", description="", inputSchema={})]

        async def call_tool(self, name: str, arguments=None, **kwargs):
            return SimpleNamespace(
                content=[], structured_content=None, data=None, is_error=False  # No content
            )

    monkeypatch.setattr("src.mcp.client.Client", FakeClient)

    config = MCPServerConfig(command="python", args=["server.py"])
    client = MCPClient(config)
    await client.connect()

    result = await client.call_tool("empty_tool", {})

    assert result["success"] is True
    assert result["output"] == "Tool executed successfully"  # Default message for empty content

    await client.disconnect()
