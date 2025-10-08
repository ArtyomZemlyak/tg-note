# MCP (Model Context Protocol) Support

This directory contains MCP (Model Context Protocol) support for the autonomous agent system.

## Overview

MCP is a protocol for connecting AI agents to external tools and data sources. The implementation here allows the autonomous agent to communicate with MCP servers and use their tools seamlessly.

### Transport Modes

This implementation supports two transport modes:

- **HTTP/SSE (default)**: Uses Server-Sent Events over HTTP for better compatibility and reliability
- **STDIO (legacy)**: Uses stdio-based JSON-RPC communication

As of the latest update, HTTP/SSE is the default mode for `mem-agent` MCP server configurations. To use STDIO mode, set `use_http=False` when calling `setup_qwen_mcp_config()`.

## Architecture

```
src/agents/mcp/
├── __init__.py              # Package exports
├── README.md                # This file
├── client.py                # MCP client implementation
├── base_mcp_tool.py         # Base class for MCP tools
└── memory_agent_tool.py     # Memory agent MCP tool
```

## Components

### MCPClient (`client.py`)

The MCP client handles communication with MCP servers:

- **Connection Management**: Launches and manages MCP server processes
- **JSON-RPC 2.0 Communication**: Sends requests and receives responses via stdio
- **Tool Support**: Lists and calls tools from the MCP server
- **Resource Support**: Lists and reads resources (NEW!)
- **Prompt Support**: Lists and gets prompts (NEW!)

**Supported MCP Features:**
- ✅ Tools (tools/list, tools/call)
- ✅ Resources (resources/list, resources/read)
- ✅ Prompts (prompts/list, prompts/get)
- ✅ JSON-RPC 2.0 protocol
- ✅ HTTP/SSE transport (default for mem-agent)
- ✅ Stdio transport (legacy)

**Usage:**
```python
from src.agents.mcp import MCPClient, MCPServerConfig

config = MCPServerConfig(
    command="npx",
    args=["@example/mcp-server"],
    env=os.environ.copy()
)

client = MCPClient(config)
await client.connect()

# Work with tools
tools = await client.list_tools()
result = await client.call_tool("tool_name", {"param": "value"})

# Work with resources (NEW!)
resources = await client.list_resources()
content = await client.read_resource("file:///path/to/file.txt")

# Work with prompts (NEW!)
prompts = await client.list_prompts()
prompt = await client.get_prompt("prompt_name", {"arg": "value"})
```

### BaseMCPTool (`base_mcp_tool.py`)

Base class for creating MCP-backed agent tools:

- **Automatic Connection**: Manages MCP client lifecycle
- **Tool Wrapping**: Exposes MCP tools as agent tools
- **Enable/Disable**: Tools can be toggled on/off
- **Error Handling**: Graceful handling of connection and execution errors

**Usage:**
```python
from src.agents.mcp import BaseMCPTool, MCPServerConfig

class MyMCPTool(BaseMCPTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Tool description"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {...}}
    
    @property
    def mcp_server_config(self) -> MCPServerConfig:
        return MCPServerConfig(command="...", args=[...])
    
    @property
    def mcp_tool_name(self) -> str:
        return "tool_name_in_server"
```

### Memory Agent Tool (`memory_agent_tool.py`)

Built-in MCP tool for intelligent memory management:

- **MemoryAgentMCPTool**: Unified memory tool (store, search, list)
- **MemoryStoreTool**: Simplified tool for storing memories
- **MemorySearchTool**: Simplified tool for searching memories

Uses the [mem-agent](https://huggingface.co/driaforall/mem-agent) model via [mem-agent-mcp](https://github.com/firstbatchxyz/mem-agent-mcp) server.

## Built-in MCP Tools

### Memory Agent

**Installation:**
```bash
npm install -g @firstbatch/mem-agent-mcp
```

**Configuration:**
```python
# In config.yaml or environment variables
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true
MCP_MEMORY_PROVIDER: "openai"
MCP_MEMORY_MODEL: "gpt-4"
```

**Available Tools:**
- `mcp_memory_agent` - Unified memory management
- `memory_store` - Store a memory
- `memory_search` - Search memories

## Creating Custom MCP Tools

### Step 1: Install MCP Server

First, install the MCP server you want to use (usually via npm):

```bash
npm install -g @your-org/your-mcp-server
```

### Step 2: Create Tool Class

Create a new Python file in this directory:

```python
# my_custom_tool.py

from typing import Any, Dict
from .base_mcp_tool import BaseMCPTool
from .client import MCPServerConfig

class MyCustomTool(BaseMCPTool):
    @property
    def name(self) -> str:
        return "my_custom_tool"
    
    @property
    def description(self) -> str:
        return "Description for the LLM to understand when to use this tool"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query parameter"
                }
            },
            "required": ["query"]
        }
    
    @property
    def mcp_server_config(self) -> MCPServerConfig:
        return MCPServerConfig(
            command="npx",
            args=["@your-org/your-mcp-server"],
            env=os.environ.copy()
        )
    
    @property
    def mcp_tool_name(self) -> str:
        # The name of the tool as exposed by the MCP server
        return "tool_name_in_server"

# Export the tool
ALL_TOOLS = [MyCustomTool()]
```

### Step 3: Register in Tool Registry

Edit `src/agents/tools/registry.py`:

```python
# Add after MCP memory tools section
if enable_mcp and config.get("enable_my_custom_tool", False):
    from ..mcp import my_custom_tool
    for tool in my_custom_tool.ALL_TOOLS:
        tool.enable()
    manager.register_many(my_custom_tool.ALL_TOOLS)
```

### Step 4: Add Configuration

Add to `config/settings.py`:

```python
AGENT_ENABLE_MY_CUSTOM_TOOL: bool = Field(
    default=False,
    description="Enable my custom MCP tool"
)
```

### Step 5: Use the Tool

```python
from src.agents.autonomous_agent import AutonomousAgent

agent = AutonomousAgent(
    llm_connector=...,
    enable_mcp=True,
    enable_my_custom_tool=True
)

result = await agent.tool_manager.execute(
    "my_custom_tool",
    {"query": "test"}
)
```

## MCP Protocol Details

### Communication Flow

1. **Server Launch**: MCP client launches the server as a subprocess
2. **Initialization**: Client sends `initialize` JSON-RPC request with protocol version "2024-11-05"
3. **Initialized Notification**: Client sends `notifications/initialized` to complete handshake
4. **Discovery**: Client can request:
   - Available tools via `tools/list`
   - Available resources via `resources/list`
   - Available prompts via `prompts/list`
5. **Execution**: Client can:
   - Call tools via `tools/call` with parameters
   - Read resources via `resources/read` with URI
   - Get prompts via `prompts/get` with name and arguments
6. **Response Handling**: Server returns results in MCP format

### JSON-RPC Format

**Request:**
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "tool_name",
        "arguments": {"param": "value"}
    }
}
```

**Response:**
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [
            {
                "type": "text",
                "text": "Tool output"
            }
        ],
        "isError": false
    }
}
```

## Testing

### Unit Tests

Test your MCP tool:

```python
import pytest
from src.agents.mcp import MyCustomTool

@pytest.mark.asyncio
async def test_my_custom_tool():
    tool = MyCustomTool()
    tool.enable()
    
    result = await tool.execute(
        {"query": "test"},
        context=mock_context
    )
    
    assert result["success"] == True
```

### Integration Tests

Test with the autonomous agent:

```python
@pytest.mark.asyncio
async def test_agent_with_mcp():
    agent = AutonomousAgent(
        enable_mcp=True,
        enable_my_custom_tool=True
    )
    
    result = await agent.tool_manager.execute(
        "my_custom_tool",
        {"query": "test"}
    )
    
    assert result["success"] == True
```

## Troubleshooting

### Server Won't Start

**Problem**: `Server process exited immediately`

**Solutions:**
1. Check Node.js is installed: `node --version`
2. Check server is installed: `npm list -g @your/server`
3. Try running manually: `npx @your/server`
4. Check environment variables are set

### Connection Timeout

**Problem**: `Failed to connect to MCP server`

**Solutions:**
1. Increase connection timeout in `client.py`
2. Check server logs for startup errors
3. Verify firewall/network settings
4. Try different stdio buffering settings

### Tool Not Found

**Problem**: `Tool 'name' not found in MCP server`

**Solutions:**
1. Check `mcp_tool_name` matches server's tool name
2. List available tools: `client.get_tools()`
3. Verify server version compatibility
4. Check server initialization completed

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [mem-agent-mcp Server](https://github.com/firstbatchxyz/mem-agent-mcp)
- [Creating MCP Servers](https://modelcontextprotocol.io/docs/concepts/servers)

## License

Same as the parent project (MIT).
