# Storage Paths Architecture

## Overview

The system uses **fixed directory paths** for storage with strict per-user isolation for memory and shared/user-override pattern for MCP servers.

## Storage Paths

### Memory Storage (Per-User Only)

**Path:** `data/memory/user_{user_id}/`

**Rules:**
- ✅ Each user has isolated memory at `data/memory/user_{user_id}/`
- ❌ NO shared memory
- ❌ NO KB-based paths
- ✅ `user_id` is **required** for all memory operations

**Reason:** Memory stores results of user actions and must never affect other users.

**Example:**
```
data/memory/
├── user_123/
│   ├── memories.json
│   └── vector_store/
└── user_456/
    └── memories.json
```

### MCP Servers (Shared + User Override)

**Paths:**
- `data/mcp_servers/` - Shared servers (available to all users)
- `data/mcp_servers/user_{user_id}/` - User-specific servers (override shared)

**Rules:**
- ✅ Shared MCP servers allowed (tools, not data)
- ✅ User-specific servers override shared servers with same name
- ✅ Registry automatically discovers both levels

**Reason:** MCP servers are tools (like calculator) and can be shared.

**Example:**
```
data/mcp_servers/
├── mem-agent.json              # Shared memory server
├── weather-api.json            # Shared weather tool
└── user_123/                   # User 123's overrides
    └── weather-api.json        # Personal API config
```

## Discovery Priority

### MCP Servers

```python
from src.mcp_registry import MCPServersManager

# Create manager (default: data/mcp_servers/)
manager = MCPServersManager()
manager.initialize()

# Discovery order:
# 1. Shared servers in data/mcp_servers/
# 2. User-specific in data/mcp_servers/user_{user_id}/ (if user_id provided)
#
# User-specific servers override shared servers with the same name
```

### Memory Storage

```python
from config.settings import settings

# Get user's memory directory
user_id = 123
memory_dir = settings.get_mem_agent_memory_dir(user_id)
# Returns: Path("data/memory/user_123")

# Ensure directory exists
settings.ensure_mem_agent_memory_dir_exists(user_id)
# Creates: data/memory/user_123/
```

## Usage in Code

### Memory Operations

```python
# Memory operations REQUIRE user_id
from src.agents.mcp.memory.memory_server_http import get_storage

user_id = 123
storage = get_storage(user_id)  # ✅ Creates/gets storage for user 123

# This will raise error:
storage = get_storage(None)  # ❌ ValueError: user_id required
```

### MCP Tool Calls

```python
# All MCP memory tools require user_id parameter
result = await mcp_client.call_tool(
    "store_memory",
    {
        "content": "Important note",
        "user_id": 123,  # ✅ Required
        "category": "general"
    }
)
```

### MCP Manager with User

```python
from src.mcp_registry import MCPServersManager

# Without user_id (shared servers only)
manager = MCPServersManager()
manager.initialize()
# Discovers: data/mcp_servers/

# With user_id (shared + user override)
manager = MCPServersManager(user_id=123)
manager.initialize()
# Discovers:
#   1. data/mcp_servers/
#   2. data/mcp_servers/user_123/
```

## Configuration

### config.yaml

```yaml
# MCP Memory Settings
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true

# Memory storage type
MEM_AGENT_STORAGE_TYPE: json  # or "vector", "mem-agent"

# Storage paths (fixed, not configurable):
# - Memory: data/memory/user_{user_id}/
# - MCP servers: data/mcp_servers/ and data/mcp_servers/user_{user_id}/
```

## Multi-User HTTP Server

The MCP memory HTTP server runs in multi-user mode:

```bash
# Start server (no user_id needed)
python -m src.agents.mcp.memory.memory_server_http --host 127.0.0.1 --port 8765
```

**How it works:**
- Single HTTP server handles all users
- Each tool call includes `user_id` parameter
- Storage is created on-demand for each user
- Storage instances are cached per `user_id`

## Benefits

1. ✅ **Strict user isolation** - No shared memory
2. ✅ **Simple paths** - Fixed, no configuration needed
3. ✅ **Security** - `user_id` required, can't access other users' memory
4. ✅ **MCP flexibility** - Shared tools + user overrides
5. ✅ **Multi-user server** - One HTTP server for all users
6. ✅ **Performance** - Storage caching per user

## Migration from Old Architecture

If you have old per-KB paths, they are **no longer supported**:

**Old (REMOVED):**
```
❌ {kb_path}/.mcp_servers/
❌ {kb_path}/memory/
❌ data/memory/shared/
```

**New (CORRECT):**
```
✅ data/memory/user_{user_id}/
✅ data/mcp_servers/
✅ data/mcp_servers/user_{user_id}/
```

## See Also

- [Memory Agent Setup](../agents/mem-agent-setup.md) - Setting up memory storage
- [MCP Server Registry](../agents/mcp-server-registry.md) - Managing MCP servers
- [MCP Tools](../agents/mcp-tools.md) - Using MCP tools in agents
