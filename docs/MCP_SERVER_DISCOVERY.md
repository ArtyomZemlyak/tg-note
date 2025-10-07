# MCP Server Discovery

## Overview

The system now supports **automatic MCP server discovery** with both **shared** and **per-user** MCP servers. Agents automatically discover and connect to available MCP servers, making their tools available for use.

## How It Works

### Discovery Process

When an agent is created for a user, the system:

1. **Discovers shared MCP servers** from `data/mcp_servers/`
2. **Discovers user-specific MCP servers** from `data/mcp_servers/user_{user_id}/`
3. **Connects to all enabled servers**
4. **Queries each server for available tools**
5. **Registers tools** in the agent's tool manager

User-specific servers **override** shared servers with the same name.

### Architecture

```
data/mcp_servers/
├── mem-agent.json              # Shared MCP server (available to all users)
├── filesystem.json             # Another shared server
├── user_123456/                # User-specific servers for user 123456
│   ├── mem-agent.json          # Overrides shared mem-agent for this user
│   └── custom-tool.json        # User-specific custom tool
└── user_789012/                # User-specific servers for user 789012
    └── private-api.json        # Private API only for this user
```

## MCP Server Configuration

### Configuration File Format

Each MCP server is configured via a JSON file:

```json
{
  "name": "my-mcp-server",
  "description": "Description of the MCP server",
  "command": "python",
  "args": ["-m", "my_package.server"],
  "env": {
    "API_KEY": "your-api-key",
    "CONFIG_PATH": "/path/to/config"
  },
  "working_dir": "/path/to/working/directory",
  "enabled": true
}
```

**Fields:**
- `name` (required): Unique identifier for the server
- `description` (required): Human-readable description
- `command` (required): Command to start the server
- `args` (optional): Command-line arguments
- `env` (optional): Environment variables
- `working_dir` (optional): Working directory for the server process
- `enabled` (optional): Whether the server is enabled (default: true)

### Example Configurations

#### Shared MCP Server (mem-agent)

File: `data/mcp_servers/mem-agent.json`

```json
{
  "name": "mem-agent",
  "description": "Intelligent memory management using mem-agent model",
  "command": "python",
  "args": ["-m", "src.mem_agent.server"],
  "env": {
    "HF_MODEL": "driaforall/mem-agent"
  },
  "enabled": true
}
```

This server is available to **all users**.

#### User-Specific MCP Server

File: `data/mcp_servers/user_123456/private-api.json`

```json
{
  "name": "private-api",
  "description": "User's private API access",
  "command": "node",
  "args": ["server.js"],
  "env": {
    "USER_API_KEY": "user-specific-key",
    "USER_ID": "123456"
  },
  "enabled": true
}
```

This server is **only available to user 123456**.

#### Overriding Shared Server

File: `data/mcp_servers/user_123456/mem-agent.json`

```json
{
  "name": "mem-agent",
  "description": "Custom mem-agent config for user 123456",
  "command": "python",
  "args": ["-m", "src.mem_agent.server"],
  "env": {
    "HF_MODEL": "custom-model-for-user",
    "MEMORY_PATH": "/custom/path/for/user/123456"
  },
  "enabled": true
}
```

This **overrides** the shared `mem-agent` configuration for user 123456.

## Using MCP Servers

### For End Users (via Telegram Bot)

1. **View available servers**: `/listmcpservers`
2. **Add a new server**: `/addmcpserver` (then paste JSON config)
3. **Enable a server**: `/enablemcp <server_name>`
4. **Disable a server**: `/disablemcp <server_name>`
5. **Remove a server**: `/removemcp <server_name>`

User-added servers are automatically placed in the user-specific directory.

### For Developers

#### Programmatic Access

```python
from src.mcp_registry import MCPServersManager

# Create manager for a specific user
manager = MCPServersManager(user_id=123456)
manager.initialize()

# Get all available servers (shared + user-specific)
all_servers = manager.get_all_servers()
enabled_servers = manager.get_enabled_servers()

# Add a new server
manager.add_server_from_json(json_content)

# Enable/disable servers
manager.enable_server("my-server")
manager.disable_server("my-server")
```

#### Using MCP Registry Client

```python
from src.agents.mcp import MCPRegistryClient

# Create client for a specific user
client = MCPRegistryClient(user_id=123456)
client.initialize()

# Connect to all enabled servers
connected = await client.connect_all_enabled()

# Get a specific connected client
mem_agent_client = client.get_client("mem-agent")

# Call a tool on the server
result = await mem_agent_client.call_tool("store_memory", {
    "content": "Important information to remember"
})
```

## Agent Integration

### Automatic Tool Discovery

When `AGENT_ENABLE_MCP=true`, agents automatically:

1. Discover all available MCP servers for the user
2. Connect to enabled servers
3. Query each server for available tools
4. Register tools with names like `mcp_{server_name}_{tool_name}`

Example: If `mem-agent` server has a tool called `store_memory`, it becomes:
- Tool name in agent: `mcp_mem_agent_store_memory`

### Configuration

Set in `.env` or via settings manager:

```bash
# Enable MCP support
AGENT_ENABLE_MCP=true

# Enable legacy MCP memory tool (optional)
AGENT_ENABLE_MCP_MEMORY=false
```

### Per-User Configuration

Each user can have different MCP settings:

```python
from src.bot.settings_manager import SettingsManager

settings = SettingsManager()

# Enable MCP for user
settings.set_user_setting(user_id, "AGENT_ENABLE_MCP", True)

# Each user's agent will discover their own servers
```

## Directory Structure

```
data/
└── mcp_servers/
    ├── shared-server-1.json
    ├── shared-server-2.json
    ├── user_123456/
    │   ├── server-override.json
    │   └── user-specific.json
    └── user_789012/
        └── another-user-server.json
```

## Best Practices

### 1. Shared vs Per-User Servers

**Use shared servers for:**
- Common functionality (like mem-agent)
- Read-only services
- Stateless tools

**Use per-user servers for:**
- User-specific API keys
- Personal data access
- Custom user configurations

### 2. Security

- **Never put sensitive data in shared server configs**
- Use environment variables for secrets
- Keep user-specific credentials in user directories
- Review user-uploaded server configs before enabling

### 3. Performance

- Only enable servers you actually use
- Disable unused servers to reduce startup time
- Keep server processes lightweight

### 4. Naming Conventions

- Use descriptive server names
- Follow kebab-case: `my-server-name`
- Avoid conflicts with existing tool names

## Troubleshooting

### MCP Server Not Found

**Problem**: Agent can't find your MCP server

**Solution**:
1. Check JSON file exists in correct directory
2. Verify `enabled: true` in config
3. Check logs for discovery errors
4. Restart agent to re-discover servers

### Server Connection Failed

**Problem**: MCP server fails to connect

**Solution**:
1. Verify command and args are correct
2. Check server process starts successfully
3. Review environment variables
4. Check working directory exists
5. Look for errors in server logs

### Tools Not Available

**Problem**: MCP server connects but tools aren't available

**Solution**:
1. Verify server implements MCP protocol correctly
2. Check server returns tools in `list_tools` response
3. Ensure tool schemas are valid
4. Review agent logs for tool registration errors

### User Override Not Working

**Problem**: User-specific config not overriding shared config

**Solution**:
1. Verify directory structure: `data/mcp_servers/user_{user_id}/`
2. Check server names match exactly
3. Ensure user agent is using correct user_id
4. Clear agent cache and recreate

## Migration Guide

### From Hardcoded MCP Tools to Dynamic Discovery

**Before:**
```python
# Hardcoded memory agent tool
from src.agents.mcp import MemoryAgentMCPTool

tool = MemoryAgentMCPTool()
```

**After:**
```python
# Automatic discovery - no code changes needed!
# Just create JSON config and enable AGENT_ENABLE_MCP
```

**Legacy Support:**
- Old `AGENT_ENABLE_MCP_MEMORY` still works
- Gradually migrate to new system by creating JSON configs
- Both can coexist during transition

## API Reference

### MCPServersManager

```python
class MCPServersManager:
    def __init__(self, servers_dir: Optional[Path] = None, user_id: Optional[int] = None)
    def initialize(self) -> None
    def get_enabled_servers(self) -> List[MCPServerSpec]
    def get_all_servers(self) -> List[MCPServerSpec]
    def get_server(self, name: str) -> Optional[MCPServerSpec]
    def enable_server(self, name: str) -> bool
    def disable_server(self, name: str) -> bool
    def add_server_from_json(self, json_content: str) -> bool
    def remove_server(self, name: str) -> bool
```

### MCPRegistryClient

```python
class MCPRegistryClient:
    def __init__(self, servers_dir: Optional[Path] = None, user_id: Optional[int] = None)
    def initialize(self) -> None
    def get_enabled_servers(self) -> List[MCPServerSpec]
    async def connect_to_server(self, spec: MCPServerSpec) -> Optional[MCPClient]
    async def connect_all_enabled(self) -> Dict[str, MCPClient]
    async def disconnect_all(self) -> None
    def get_client(self, server_name: str) -> Optional[MCPClient]
```

### Dynamic MCP Tools

```python
async def discover_and_create_mcp_tools(
    user_id: Optional[int] = None,
    servers_dir: Optional[Path] = None
) -> List[BaseTool]

async def create_mcp_tools_for_user(user_id: int) -> List[BaseTool]
```

## Examples

See also:
- `examples/mcp_memory_agent_example.py` - Memory agent usage
- `scripts/install_mem_agent.py` - Setting up mem-agent MCP server
- `src/bot/mcp_handlers.py` - Telegram bot integration

## Summary

The MCP server discovery system provides:

✅ **Automatic discovery** of MCP servers  
✅ **Per-user configuration** support  
✅ **Shared and user-specific** servers  
✅ **Override mechanism** for customization  
✅ **Dynamic tool registration**  
✅ **Telegram bot integration**  
✅ **Easy configuration** via JSON files  

This makes it easy to extend agent capabilities with custom MCP servers while maintaining security and user isolation.