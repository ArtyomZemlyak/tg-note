# MCP Server Registry

The MCP (Model Context Protocol) Server Registry provides a flexible system for discovering, managing, and connecting to MCP servers through simple JSON configuration files.

## Overview

The registry system allows you to:

- **Discover servers automatically** from JSON configuration files
- **Enable/disable servers** through configuration
- **Add custom MCP servers** by uploading JSON files
- **Integrate external MCP servers** without modifying code

## Architecture

The MCP server system consists of three main components:

1. **MCP Server Registry** - Discovers and manages server configurations
2. **MCP Registry Client** - Connects to enabled servers
3. **MCP Tools** - Agent tools that use MCP servers

```
┌─────────────────────────────────────────────┐
│         Agent with MCP Support              │
├─────────────────────────────────────────────┤
│                                             │
│  ┌───────────────────────────────────┐     │
│  │   MCP Registry Client             │     │
│  │   - Discovers enabled servers     │     │
│  │   - Creates MCP clients           │     │
│  │   - Manages connections           │     │
│  └───────────────────────────────────┘     │
│           │                                 │
│           ▼                                 │
│  ┌───────────────────────────────────┐     │
│  │   MCP Server Registry             │     │
│  │   - Scans data/mcp_servers/*.json │     │
│  │   - Loads server configurations   │     │
│  │   - Manages enable/disable state  │     │
│  └───────────────────────────────────┘     │
│                                             │
└─────────────────────────────────────────────┘
```

## Server Configuration

### JSON Format

MCP server configurations are stored as JSON files in `data/mcp_servers/`:

```json
{
  "name": "server-name",
  "description": "Human-readable description of the server",
  "command": "python",
  "args": ["-m", "package.module"],
  "env": {
    "ENV_VAR": "value"
  },
  "working_dir": "/path/to/directory",
  "enabled": true
}
```

### Fields

- **name** (required): Unique identifier for the server
- **description** (required): Human-readable description
- **command** (required): Command to execute the server process
- **args** (optional): Command-line arguments as array
- **env** (optional): Environment variables as object
- **working_dir** (optional): Working directory for the server process
- **enabled** (optional, default: true): Whether the server is enabled

### Example: Memory Agent Server

```json
{
  "name": "mem-agent",
  "description": "Local memory agent with intelligent memory management",
  "command": "python",
  "args": ["-m", "src.mem_agent.server"],
  "env": {
    "MEM_AGENT_MEMORY_POSTFIX": "memory",
    "KB_PATH": "/workspace/knowledge_bases/user_kb"
  },
  "working_dir": "/workspace",
  "enabled": true
}
```

## Adding MCP Servers

### Method 1: Installation Script

For built-in servers like mem-agent, use the installation script:

```bash
python scripts/install_mem_agent.py
```

This automatically:
1. Installs dependencies
2. Downloads required models
3. Creates the MCP server configuration
4. Sets up directory structure

### Method 2: Manual Configuration

Create a JSON file in `data/mcp_servers/`:

```bash
cat > data/mcp_servers/my-server.json << EOF
{
  "name": "my-server",
  "description": "My custom MCP server",
  "command": "npx",
  "args": ["@my-org/mcp-server"],
  "enabled": true
}
EOF
```

### Method 3: Programmatic Addition

```python
from src.mcp_registry import MCPServersManager

manager = MCPServersManager()
manager.initialize()

# Add from JSON string
json_config = '''
{
  "name": "custom-server",
  "description": "Custom MCP server",
  "command": "node",
  "args": ["server.js"]
}
'''

success = manager.add_server_from_json(json_config)
```

## Managing Servers

### List All Servers

```python
from src.mcp_registry import MCPServersManager

manager = MCPServersManager()
manager.initialize()

# Get all servers
all_servers = manager.get_all_servers()
for server in all_servers:
    status = "enabled" if server.enabled else "disabled"
    print(f"{server.name}: {server.description} ({status})")

# Get only enabled servers
enabled_servers = manager.get_enabled_servers()
print(f"\nEnabled servers: {len(enabled_servers)}")
```

### Enable/Disable Servers

```python
# Enable a server
manager.enable_server("mem-agent")

# Disable a server
manager.disable_server("mem-agent")

# Get summary
summary = manager.get_servers_summary()
print(f"Total: {summary['total']}, Enabled: {summary['enabled']}")
```

### Remove Server

```python
# Remove server configuration
manager.remove_server("my-server")
```

## Using MCP Servers in Agents

### Automatic Discovery

The MCP registry client automatically discovers and connects to enabled servers:

```python
from src.agents.mcp import MCPRegistryClient

# Create registry client
client = MCPRegistryClient()
client.initialize()

# Connect to all enabled servers
connected = await client.connect_all_enabled()
print(f"Connected to {len(connected)} servers")

# List connected servers
for name in connected:
    print(f"- {name}")
```

### Using Specific Server

```python
# Get a specific server's client
mem_agent_client = client.get_client("mem-agent")

if mem_agent_client and mem_agent_client.is_connected:
    # Use the client
    result = await mem_agent_client.call_tool(
        "use_memory_agent",
        {"question": "What's my name?"}
    )
    print(result)
```

## Bot Integration

Users can add MCP servers through the Telegram bot by uploading JSON files.

### Future Bot Command (TODO)

```
/mcp add <server-name>
```

Then upload a JSON file with the server configuration.

```
/mcp list
/mcp enable <server-name>
/mcp disable <server-name>
/mcp remove <server-name>
```

## Configuration in Settings

MCP servers can be configured through `config.yaml` or environment variables:

```yaml
# Enable MCP support
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true

# MCP servers postfix (per-user within KB)
MCP_SERVERS_POSTFIX: .mcp_servers

# Memory agent settings
MEM_AGENT_MODEL: BAAI/bge-m3
MEM_AGENT_MODEL_PRECISION: 4bit
MEM_AGENT_BACKEND: auto
MEM_AGENT_MEMORY_POSTFIX: memory
```

## Best Practices

### Server Configuration

1. **Use descriptive names**: Make server names clear and unique
2. **Provide good descriptions**: Help users understand what the server does
3. **Set appropriate timeouts**: Configure server timeouts based on expected response time
4. **Use relative paths**: When possible, use relative paths for portability

### Security

1. **Validate server configurations**: Check JSON files before adding
2. **Limit server permissions**: Use working_dir to restrict file access
3. **Review environment variables**: Don't expose sensitive credentials
4. **Monitor server processes**: Ensure servers don't leak resources

### Performance

1. **Enable only needed servers**: Disable unused servers to save resources
2. **Use connection pooling**: Reuse MCP clients when possible
3. **Handle errors gracefully**: Implement proper error handling for server failures

## Troubleshooting

### Server Won't Connect

1. Check if server is enabled:
   ```python
   server = manager.get_server("server-name")
   print(f"Enabled: {server.enabled}")
   ```

2. Verify command and args are correct:
   ```python
   print(f"Command: {server.command}")
   print(f"Args: {server.args}")
   ```

3. Check server process logs:
   ```bash
   # Run server manually to see errors
   python -m src.mem_agent.server
   ```

### Server Configuration Not Loading

1. Verify JSON file location:
   ```bash
   ls -la data/mcp_servers/
   ```

2. Check JSON syntax:
   ```bash
   python -m json.tool data/mcp_servers/server-name.json
   ```

3. Re-discover servers:
   ```python
   manager = MCPServersManager()
   manager.initialize()  # Forces re-discovery
   ```

### Memory Agent Issues

See [mem-agent-setup.md](./mem-agent-setup.md) for specific mem-agent troubleshooting.

## See Also

- [MCP Tools](./mcp-tools.md) - Overview of MCP tools for agents
- [Memory Agent Setup](./mem-agent-setup.md) - Detailed mem-agent setup guide
- [Agent Architecture](../architecture/agent-architecture.md) - Overall agent architecture