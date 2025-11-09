from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from fastmcp.client.transports import StdioTransport

from src.mcp.client import MCPClient, MCPServerConfig


class _BaseFakeClient:
    """Test double for fastmcp.Client."""

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
async def test_call_tool_and_metadata(monkeypatch):
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
                    arguments=[
                        SimpleNamespace(name="arg1", description="Argument", required=True)
                    ],
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

    result = await client.call_tool("docling", {"foo": "bar"})
    assert result["success"] is True
    assert result["output"] == "Processing complete"
    assert result["is_error"] is False
    assert result["data"] == {"status": "ok"}
    assert result["structured_content"] == {"result": {"status": "ok"}}
    assert result["result"]["structuredContent"] == {"result": {"status": "ok"}}
    assert captured["raise_on_error"] == [False]

    resources = await client.list_resources()
    assert resources == [
        {
            "uri": "file:///tmp/output.txt",
            "name": "output",
            "description": "Example resource",
            "mimeType": "text/plain",
        }
    ]

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

    prompt = await client.get_prompt("demo")
    assert prompt == {
        "description": "Demo prompt description",
        "messages": [
            {"role": "user", "content": {"type": "text", "text": "Prompt body"}},
        ],
    }

    await client.disconnect()
