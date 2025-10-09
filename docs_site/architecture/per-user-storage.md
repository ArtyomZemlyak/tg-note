# Per-User Storage Architecture

## Overview

The system uses a **postfix-based approach** for per-user storage within knowledge bases. This ensures isolation between users while maintaining a clean configuration.

## Key Concepts

### Postfix Pattern

Instead of hardcoding full paths, settings define **postfixes** that are appended to each user's knowledge base path:

```python
# Settings in config/settings.py
MEM_AGENT_MEMORY_POSTFIX = "memory"          # Default postfix for memory
MCP_SERVERS_POSTFIX = ".mcp_servers"         # Default postfix for MCP servers

# Constructed paths for user with KB at "knowledge_bases/user_kb"
memory_path = kb_path / MEM_AGENT_MEMORY_POSTFIX
# Result: knowledge_bases/user_kb/memory

mcp_servers_dir = kb_path / MCP_SERVERS_POSTFIX
# Result: knowledge_bases/user_kb/.mcp_servers
```

### Directory Structure

Each user's knowledge base contains:

```
knowledge_bases/
└── {user_kb_name}/           # User's KB (from setkb command)
    ├── .mcp_servers/          # Per-user MCP server configs
    │   └── mem-agent.json     # Standard MCP format (see mcp-config-format.md)
    ├── memory/                # Per-user memory
    │   ├── user.md
    │   └── entities/
    └── topics/                # User's notes
```

> **Note**: The `mem-agent.json` file follows the standard MCP server configuration format. See [MCP Configuration Format](../agents/mcp-config-format.md) for details.

## Usage in Code

### Getting User-Specific Paths

```python
from config.settings import settings
from pathlib import Path

# Get user's KB path (from settings manager or user config)
user_id = 12345
kb_path = settings_manager.get_setting(user_id, "KB_PATH")

# Construct full paths
memory_path = settings.get_mem_agent_memory_path(kb_path)
mcp_servers_dir = settings.get_mcp_servers_dir(kb_path)

print(f"Memory: {memory_path}")
# Output: knowledge_bases/user_kb/memory

print(f"MCP servers: {mcp_servers_dir}")
# Output: knowledge_bases/user_kb/.mcp_servers
```

### Creating MCP Manager for User

```python
from src.mcp_registry import MCPServersManager
from config.settings import settings

# Get user's KB path
kb_path = get_user_kb_path(user_id)  # Your function to get user's KB

# Create per-user MCP manager
mcp_servers_dir = settings.get_mcp_servers_dir(kb_path)
manager = MCPServersManager(servers_dir=mcp_servers_dir)

# Now manager works with user's MCP servers
manager.initialize()
enabled_servers = manager.get_enabled_servers()
```

### Ensuring Directories Exist

```python
from config.settings import settings

# Ensure user's memory directory exists
settings.ensure_mem_agent_memory_path_exists(kb_path)

# Ensure user's MCP servers directory exists
settings.ensure_mcp_servers_dir_exists(kb_path)
```

## Helper Methods in Settings

The `Settings` class provides helper methods for working with per-user paths:

### `get_mcp_servers_dir(kb_path: Path) -> Path`

Constructs full MCP servers directory path for a KB.

```python
kb_path = Path("./knowledge_bases/user_kb")
mcp_dir = settings.get_mcp_servers_dir(kb_path)
# Returns: Path("./knowledge_bases/user_kb/.mcp_servers")
```

### `get_mem_agent_memory_path(kb_path: Path) -> Path`

Constructs full memory path for a KB.

```python
kb_path = Path("./knowledge_bases/user_kb")
memory_path = settings.get_mem_agent_memory_path(kb_path)
# Returns: Path("./knowledge_bases/user_kb/memory")
```

### `ensure_mem_agent_memory_path_exists(kb_path: Path) -> None`

Creates memory directory if it doesn't exist.

```python
kb_path = Path("./knowledge_bases/user_kb")
settings.ensure_mem_agent_memory_path_exists(kb_path)
# Creates: knowledge_bases/user_kb/memory/
```

### `ensure_mcp_servers_dir_exists(kb_path: Path) -> None`

Creates MCP servers directory if it doesn't exist.

```python
kb_path = Path("./knowledge_bases/user_kb")
settings.ensure_mcp_servers_dir_exists(kb_path)
# Creates: knowledge_bases/user_kb/.mcp_servers/
```

## Integration with User Settings

When working with user-specific settings, get the KB path first:

```python
from src.bot.settings_manager import SettingsManager
from config.settings import settings

# Initialize settings manager
settings_manager = SettingsManager(settings)

# Get user's KB path
user_id = 12345
kb_path_str = settings_manager.get_setting(user_id, "KB_PATH")
kb_path = Path(kb_path_str)

# Now construct per-user paths
memory_path = settings.get_mem_agent_memory_path(kb_path)
mcp_servers_dir = settings.get_mcp_servers_dir(kb_path)
```

## Configuration

### Global Settings (config.yaml)

```yaml
# Postfixes for per-user directories
MEM_AGENT_MEMORY_POSTFIX: memory
MCP_SERVERS_POSTFIX: .mcp_servers

# Global KB path (can be overridden per-user)
KB_PATH: ./knowledge_bases/default
```

### Per-User Overrides

Users can override their KB path via `/setkb` command:

```
/setkb my-notes
# Sets KB_PATH to knowledge_bases/my-notes for this user
# Memory will be at: knowledge_bases/my-notes/memory
# MCP servers will be at: knowledge_bases/my-notes/.mcp_servers
```

## Benefits

1. **User Isolation**: Each user has separate memory and MCP configurations
2. **Clean Configuration**: Postfixes are simple and don't require full paths
3. **Flexibility**: Easy to change structure by modifying postfixes
4. **Consistency**: All per-user data follows same pattern
5. **KB Integration**: Everything within knowledge base structure

## Migration from Old Structure

Old approach (hardcoded paths):

```python
MCP_SERVERS_DIR = Path("./data/mcp_servers")  # Global
MEM_AGENT_MEMORY_PATH = Path("./data/memory")  # Global
```

New approach (postfixes):

```python
MCP_SERVERS_POSTFIX = ".mcp_servers"  # Per-user: kb_path/.mcp_servers
MEM_AGENT_MEMORY_POSTFIX = "memory"   # Per-user: kb_path/memory
```

## See Also

- [Settings Architecture](./settings-architecture.md) - Overall settings design
- [Memory Agent Setup](../agents/mem-agent-setup.md) - Using memory agent
- [MCP Configuration Format](../agents/mcp-config-format.md) - Standard MCP config format
- [MCP Server Registry](../agents/mcp-server-registry.md) - Managing MCP servers
