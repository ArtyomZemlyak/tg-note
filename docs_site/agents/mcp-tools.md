# MCP (Model Context Protocol) Tools

The autonomous agent supports MCP (Model Context Protocol) tools, allowing you to connect external tools and services as agent capabilities.

## Overview

MCP is a protocol for connecting AI agents to external tools and data sources. The agent can communicate with MCP servers to access their tools and functionality.

### Built-in MCP Tools

The MCP Hub provides built-in tools that are dynamically available based on configuration and dependencies.

**Tool availability is checked at startup** - disabled tools will NOT appear in the tools list.

**Memory Tools (Conditionally Available):**
- Tools: `store_memory`, `retrieve_memory`, `list_categories`
- Requirement: `AGENT_ENABLE_MCP_MEMORY: true` (default: false)
- Dependencies: None (uses basic JSON storage)
- Total: 3 tools when enabled

**Vector Search Tools (Conditionally Available):**
- Tools: `vector_search`, `reindex_vector`
- Requirements:
  - Configuration: `VECTOR_SEARCH_ENABLED: true` (default: false)
  - Dependencies: `pip install -e '.[vector-search]'`
- Total: 2 tools when enabled

**Possible Configurations:**
- 0 tools: Both disabled (minimal mode)
- 3 tools: Only memory enabled (typical setup)
- 2 tools: Only vector search enabled (rare)
- 5 tools: Both enabled (full features)

#### Memory Tools

⚙️ **Configurable via AGENT_ENABLE_MCP_MEMORY**

Personal note-taking and search system for the agent using JSON storage (no dependencies required).

**Availability:**
These tools are available when:
- **Configuration**: `AGENT_ENABLE_MCP_MEMORY: true` in config.yaml (default: false)
- **Dependencies**: None (uses basic JSON storage with automatic fallback)

**Purpose:**
This tool is specifically designed for the main agent to:

- **Record notes**: Write down important information, findings, or context during task execution
- **Search notes**: Find and recall previously recorded information
- **Maintain working memory**: Keep context across multiple LLM calls within a single session

**Use Cases:**

- During complex multi-step tasks, the agent records findings and retrieves them later
- Autonomous agents (like qwen code cli) making many LLM calls in one session
- Maintaining context when the agent needs to remember what it discovered earlier

**Tools:**

- `store_memory` - Store information in memory
- `retrieve_memory` - Retrieve information from memory
- `list_categories` - List all memory categories

**Note:** If disabled, these tools will NOT appear in the MCP tools list.

#### Vector Search Tools

⚙️ **Configurable via VECTOR_SEARCH_ENABLED + Dependencies Required**

Semantic vector search in knowledge base using AI-powered embeddings.

**Availability:**
These tools are available when:
1. **Configuration**: `VECTOR_SEARCH_ENABLED: true` in config.yaml (default: false)
2. **Dependencies**: Vector search packages installed (`pip install -e '.[vector-search]'`)
   - sentence-transformers (for embeddings)
   - faiss-cpu or qdrant-client (for vector storage)

**Purpose:**
This tool provides semantic search capabilities for the knowledge base:

- **Vector Search**: Find relevant information using natural language queries
- **Semantic Understanding**: Search by meaning, not just keywords
- **Reindexing**: Update the vector index when knowledge base changes

**Use Cases:**

- Finding relevant documentation using natural language questions
- Semantic search that understands context and meaning
- Searching for similar concepts even without exact keyword matches

**Tools:**

- `vector_search` - Semantic search in knowledge base
- `reindex_vector` - Reindex knowledge base for vector search

**Note:** If disabled or dependencies missing, these tools will NOT appear in the MCP tools list.

## Configuration

### Enable MCP Tools

Add to your `config.yaml`:

```yaml
# MCP Settings
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true
MCP_MEMORY_PROVIDER: "openai"
MCP_MEMORY_MODEL: "gpt-4"

# Vector Search Settings
VECTOR_SEARCH_ENABLED: true
VECTOR_SEARCH_MODEL: "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_SEARCH_BACKEND: "auto"
```

Or set environment variables:

```bash
export AGENT_ENABLE_MCP=true
export AGENT_ENABLE_MCP_MEMORY=true
export MCP_MEMORY_PROVIDER=openai
export MCP_MEMORY_MODEL=gpt-4

# Vector Search
export VECTOR_SEARCH_ENABLED=true
export VECTOR_SEARCH_MODEL=sentence-transformers/all-MiniLM-L6-v2
export VECTOR_SEARCH_BACKEND=auto
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
    enable_vector_search=True,
    max_iterations=10
)
```

### Record Notes (Store)

```python
# The agent records a note during task execution
result = await agent.tool_manager.execute(
    "memory_store",
    {
        "content": "Found SQL injection vulnerability in login endpoint /api/auth",
        "tags": ["security", "findings"]
    }
)
```

### Search Notes (Recall)

```python
# Later, the agent searches its notes to remember
result = await agent.tool_manager.execute(
    "memory_search",
    {
        "query": "What security issues did I find?",
        "limit": 5
    }
)
```

### Unified Note Management

```python
# Record a note
await agent.tool_manager.execute(
    "mcp_memory_agent",
    {
        "action": "store",
        "content": "Database uses PostgreSQL 14 with pgvector extension",
        "context": "Infrastructure analysis"
    }
)

# Search notes to recall information
await agent.tool_manager.execute(
    "mcp_memory_agent",
    {
        "action": "search",
        "content": "What database technology is used?"
    }
)

# List all recorded notes
await agent.tool_manager.execute(
    "mcp_memory_agent",
    {
        "action": "list"
    }
)
```

### Vector Search in Knowledge Base

```python
# Semantic search in knowledge base
result = await agent.tool_manager.execute(
    "kb_vector_search",
    {
        "query": "How do I configure authentication?",
        "top_k": 5
    }
)

# Reindex knowledge base after updates
result = await agent.tool_manager.execute(
    "kb_reindex_vector",
    {
        "force": False  # Set to True to force reindexing
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
- [bge-m3 Model](https://huggingface.co/BAAI/bge-m3)
- [mem-agent-mcp Server](https://github.com/firstbatchxyz/mem-agent-mcp)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
