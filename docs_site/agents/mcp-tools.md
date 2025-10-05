# MCP (Model Context Protocol) Tools

The autonomous agent supports MCP (Model Context Protocol) tools, allowing you to connect external tools and services as agent capabilities.

## Overview

MCP is a protocol for connecting AI agents to external tools and data sources. The agent can communicate with MCP servers to access their tools and functionality.

### Built-in MCP Tools

Currently, the following built-in MCP tools are available:

#### Memory Agent Tool

Intelligent memory management using the [mem-agent](https://huggingface.co/driaforall/mem-agent) model.

**Features:**
- Store memories with semantic understanding
- Search memories based on queries
- Maintain conversation context across sessions
- Automatic categorization and tagging

**Tools:**
- `mcp_memory_agent` - Unified memory management (store, search, list)
- `memory_store` - Store a memory
- `memory_search` - Search through memories

## Configuration

### Enable MCP Tools

Add to your `config.yaml`:

```yaml
# MCP Settings
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true
MCP_MEMORY_PROVIDER: "openai"
MCP_MEMORY_MODEL: "gpt-4"
```

Or set environment variables:

```bash
export AGENT_ENABLE_MCP=true
export AGENT_ENABLE_MCP_MEMORY=true
export MCP_MEMORY_PROVIDER=openai
export MCP_MEMORY_MODEL=gpt-4
```

### Install MCP Server

The memory agent tool requires the `mem-agent-mcp` server:

```bash
# Install globally
npm install -g @firstbatch/mem-agent-mcp

# Or use npx (no installation required)
# The tool will automatically use npx if the server is not installed
```

### Set API Keys

The memory agent requires an LLM API key:

```bash
# For OpenAI
export OPENAI_API_KEY=your_key_here

# For Anthropic
export ANTHROPIC_API_KEY=your_key_here
```

## Usage

### Enable in Code

```python
from src.agents.autonomous_agent import AutonomousAgent
from src.agents.llm_connectors import OpenAIConnector

agent = AutonomousAgent(
    llm_connector=OpenAIConnector(api_key="your_key"),
    enable_mcp=True,
    enable_mcp_memory=True,
    max_iterations=10
)
```

### Store Memories

```python
result = await agent.tool_manager.execute(
    "memory_store",
    {
        "content": "User prefers Python for backend development",
        "tags": ["preferences", "programming"]
    }
)
```

### Search Memories

```python
result = await agent.tool_manager.execute(
    "memory_search",
    {
        "query": "What are the user's programming preferences?",
        "limit": 5
    }
)
```

### Unified Memory Agent

```python
# Store
await agent.tool_manager.execute(
    "mcp_memory_agent",
    {
        "action": "store",
        "content": "Important information",
        "context": "Project context"
    }
)

# Search
await agent.tool_manager.execute(
    "mcp_memory_agent",
    {
        "action": "search",
        "content": "query text"
    }
)

# List all
await agent.tool_manager.execute(
    "mcp_memory_agent",
    {
        "action": "list"
    }
)
```

## How It Works

### MCP Architecture

```
┌─────────────────────┐
│  Autonomous Agent   │
│                     │
│  ┌───────────────┐  │
│  │  Tool Manager │  │
│  └───────┬───────┘  │
└──────────┼──────────┘
           │
           │ Function Calls
           │
           ▼
┌──────────────────────┐
│   MCP Client         │
│   (Python)           │
└──────────┬───────────┘
           │
           │ JSON-RPC over stdio
           │
           ▼
┌──────────────────────┐
│   MCP Server         │
│   (Node.js)          │
│                      │
│  mem-agent-mcp       │
└──────────┬───────────┘
           │
           │ API Calls
           │
           ▼
┌──────────────────────┐
│   LLM API            │
│   (OpenAI, etc.)     │
└──────────────────────┘
```

### Communication Flow

1. **Agent Decision**: The agent decides to use an MCP tool
2. **Tool Execution**: The tool manager calls the MCP tool
3. **MCP Connection**: The MCP client connects to the server (if not already connected)
4. **JSON-RPC Request**: The client sends a JSON-RPC request over stdio
5. **Server Processing**: The MCP server processes the request
6. **LLM Interaction**: The server may call an LLM API for processing
7. **Response**: The result is sent back through the chain

## Creating Custom MCP Tools

You can create custom MCP tools by extending the `BaseMCPTool` class:

```python
from src.agents.mcp import BaseMCPTool, MCPServerConfig

class MyCustomMCPTool(BaseMCPTool):
    @property
    def name(self) -> str:
        return "my_custom_tool"
    
    @property
    def description(self) -> str:
        return "Description of what the tool does"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
            },
            "required": ["param1"]
        }
    
    @property
    def mcp_server_config(self) -> MCPServerConfig:
        return MCPServerConfig(
            command="npx",
            args=["@your/mcp-server"],
            env=os.environ.copy()
        )
    
    @property
    def mcp_tool_name(self) -> str:
        return "tool_name_in_server"
```

## Connecting Any MCP Server

To connect any MCP-compatible server:

1. **Install the MCP server** (usually via npm)
2. **Create a tool class** extending `BaseMCPTool`
3. **Configure the server** in `mcp_server_config`
4. **Enable the tool** in your configuration
5. **Register the tool** in the tool manager

See `src/agents/mcp/memory_agent_tool.py` for a complete example.

## Troubleshooting

### MCP Server Not Found

```
Error: Failed to connect to MCP server
```

**Solution**: Install the MCP server:
```bash
npm install -g @firstbatch/mem-agent-mcp
```

### API Key Missing

```
Error: API key not found
```

**Solution**: Set the appropriate API key:
```bash
export OPENAI_API_KEY=your_key_here
```

### Connection Issues

```
Error: Server process exited immediately
```

**Solutions:**
1. Check that Node.js is installed: `node --version`
2. Check server installation: `npm list -g @firstbatch/mem-agent-mcp`
3. Try running the server manually: `npx @firstbatch/mem-agent-mcp`
4. Check server logs for errors

## Examples

See `examples/mcp_memory_agent_example.py` for complete working examples.

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [mem-agent Model](https://huggingface.co/driaforall/mem-agent)
- [mem-agent-mcp Server](https://github.com/firstbatchxyz/mem-agent-mcp)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
