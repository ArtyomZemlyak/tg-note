# MCP Server Configuration Format

This document describes the standard MCP (Model Context Protocol) server configuration format used in this project.

## Overview

The configuration file `data/mcp_servers/mem-agent.json` follows the standard MCP configuration format that is compatible with:
- ✓ Cursor MCP
- ✓ Claude Desktop
- ✓ Qwen CLI
- ✓ Other MCP clients

## Standard Configuration Structure

All MCP server configurations follow this top-level structure:

```json
{
  "mcpServers": {
    "server-name": {
      // Server configuration here
    }
  }
}
```

## HTTP/SSE Transport (Default)

For servers using HTTP with Server-Sent Events (SSE), the configuration format is:

```json
{
  "mcpServers": {
    "mem-agent": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "Agent's personal note-taking and search system"
    }
  }
}
```

### HTTP/SSE Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | ✓ | SSE endpoint URL (typically `/sse` path) |
| `timeout` | number | ✓ | Connection timeout in milliseconds |
| `trust` | boolean | ✓ | Whether to trust this server |
| `description` | string | ✓ | Human-readable server description |

### Advantages of HTTP/SSE

- ✓ Better compatibility with network environments
- ✓ Easier debugging with standard HTTP tools
- ✓ Single server instance can handle multiple clients
- ✓ Works across different processes and machines

## stdio Transport

For servers using standard input/output, the configuration format is:

```json
{
  "mcpServers": {
    "mem-agent": {
      "command": "python",
      "args": ["-m", "src.agents.mcp.memory.memory_server"],
      "cwd": "/path/to/project",
      "env": {},
      "timeout": 10000,
      "trust": true,
      "description": "Agent's personal note-taking and search system"
    }
  }
}
```

### stdio Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | ✓ | Command to execute (e.g., "python", "node") |
| `args` | array | ✓ | Command arguments |
| `cwd` | string | ✓ | Working directory for the process |
| `env` | object | ✓ | Environment variables |
| `timeout` | number | ✓ | Connection timeout in milliseconds |
| `trust` | boolean | ✓ | Whether to trust this server |
| `description` | string | ✓ | Human-readable server description |

### Advantages of stdio

- ✓ Simpler for local-only scenarios
- ✓ One server instance per client
- ✓ No network ports required
- ✓ Easier process isolation

## Our Implementation

### Generated Configuration

When the bot starts, it automatically generates `data/mcp_servers/mem-agent.json` with:

1. **HTTP/SSE configuration** (default) - Used for client connections
2. **stdio variant** (reference) - Available in `_stdio_variant` field for alternative setups

Example generated file:

```json
{
  "mcpServers": {
    "mem-agent": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "Agent's personal note-taking and search system",
      "_transport": "http",
      "_command": "python",
      "_args": ["-m", "src.agents.mcp.memory.memory_server_http", "--host", "127.0.0.1", "--port", "8765"],
      "_cwd": "/workspace",
      "_stdio_variant": {
        "command": "python",
        "args": ["-m", "src.agents.mcp.mem_agent_server_http", "--host", "127.0.0.1", "--port", "8765"],
        "cwd": "/workspace",
        "env": {},
        "timeout": 10000,
        "trust": true,
        "description": "Agent's personal note-taking and search system (stdio variant)"
      }
    }
  }
}
```

### Internal Metadata Fields

Fields prefixed with `_` are used internally and are not part of the standard MCP format:

- `_transport`: Transport type ("http" or "stdio")
- `_command`: Command for internal process management
- `_args`: Arguments for internal process management
- `_cwd`: Working directory for internal process management
- `_stdio_variant`: Complete stdio configuration for reference

These fields are ignored by standard MCP clients and provide additional metadata for our internal tooling.

## Using the Configuration

### With Qwen CLI

The Qwen CLI configuration generator (`qwen_config_generator.py`) creates compatible configurations:

```python
from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config

# HTTP/SSE mode (default)
setup_qwen_mcp_config(
    global_config=True,
    use_http=True,
    http_port=8765
)

# stdio mode
setup_qwen_mcp_config(
    global_config=True,
    use_http=False
)
```

### With Python MCP Client

```python
from src.agents.mcp.memory.memory_tool import MemoryMCPTool

tool = MemoryMCPTool()
config = tool.mcp_server_config

# Config is automatically loaded from mem-agent.json
# and supports both HTTP/SSE and stdio formats
```

### With Cursor / Claude Desktop

Copy the configuration (without internal `_` fields) to:
- Cursor: `.mcp.json` in project root
- Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

## Validation

To validate your configuration:

```bash
python3 test_mcp_config_format_simple.py
```

This will:
1. Create a sample configuration
2. Validate the format
3. Show compatibility information
4. Display both HTTP/SSE and stdio variants

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Cursor MCP Documentation](https://docs.cursor.com/context/mcp)
- [Claude Desktop MCP Support](https://docs.anthropic.com/claude/docs/mcp)
- [Qwen CLI Configuration](../qwen_cli_setup.md)

## Migration from Old Format

If you have an old-format configuration file, it will be automatically replaced with the standard format when the bot starts. The old format looked like:

```json
{
  "name": "mem-agent",
  "command": "python",
  "args": [...],
  "working_dir": "...",
  "enabled": true,
  "transport": "http"
}
```

This non-standard format is no longer supported. Delete the old `mem-agent.json` and let the bot recreate it in the standard format.
