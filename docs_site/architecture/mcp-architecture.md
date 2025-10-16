# MCP Architecture

## Overview

The MCP (Model Context Protocol) layer in tg-note follows a clean separation of concerns between the **MCP Hub Service** and the **Bot Client**.

## Core Principles

1. **Single Source of Truth**: MCP Hub service owns ALL MCP-related logic
2. **Pure Client Pattern**: Bot is a pure client that connects to MCP Hub
3. **No Config Duplication**: Only MCP Hub creates configuration files
4. **Mode-Agnostic Bot**: Bot behavior is the same in Docker and standalone modes

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Bot Service                              │
│  ┌────────────────────────────────────────────────────────┐     │
│  │         MCPServerManager (Subprocess Manager)          │     │
│  │                                                        │     │
│  │  - Docker Mode: Does nothing (pure client)            │     │
│  │  - Standalone Mode: Launches MCP Hub subprocess       │     │
│  │                                                        │     │
│  │  NOT responsible for:                                 │     │
│  │    ✗ Config generation                                │     │
│  │    ✗ MCP tool registration                            │     │
│  │    ✗ Server registry management                       │     │
│  └────────────────────────────────────────────────────────┘     │
│                            │                                     │
│                            │ HTTP/SSE                            │
│                            ▼                                     │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    MCP Hub Service                               │
│  ┌────────────────────────────────────────────────────────┐     │
│  │           Unified MCP Gateway                          │     │
│  │                                                        │     │
│  │  ✓ Built-in MCP Tools (memory, etc.)                 │     │
│  │  ✓ MCP Server Registry                                │     │
│  │  ✓ Configuration Generation                           │     │
│  │  ✓ HTTP/SSE API                                       │     │
│  │  ✓ Per-user isolation                                 │     │
│  │                                                        │     │
│  │  Endpoints:                                            │     │
│  │    - /health (includes builtin tools & servers)       │     │
│  │    - /sse (MCP protocol)                              │     │
│  │    - /registry/servers (CRUD)                         │     │
│  │    - /config/client/{type} (config generation)        │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Modes

### Docker Mode

```yaml
# docker-compose.yml
services:
  mcp-hub:
    # MCP Hub runs as standalone service
    # Generates configs on startup
    # Owns all MCP logic
    
  bot:
    # Bot is pure client
    # Connects via MCP_HUB_URL
    # No subprocess, no config generation
    environment:
      - MCP_HUB_URL=http://mcp-hub:8765/sse
```

**Flow:**
1. MCP Hub container starts
2. MCP Hub generates client configs (`~/.qwen/settings.json`)
3. Bot container starts
4. Bot connects to MCP Hub via `MCP_HUB_URL`
5. Bot uses MCP tools through HTTP/SSE

### Standalone Mode

```bash
# Bot launches MCP Hub as subprocess
python -m main
```

**Flow:**
1. Bot starts
2. Bot detects no `MCP_HUB_URL` (standalone mode)
3. Bot launches MCP Hub as subprocess
4. MCP Hub subprocess generates client configs
5. Bot connects to MCP Hub at `http://127.0.0.1:8765/sse`
6. Bot uses MCP tools through HTTP/SSE

## Responsibilities

### MCP Hub Service (`src/mcp/mcp_hub_server.py`)

**Owns:**
- ✅ Built-in MCP tools (memory, etc.)
- ✅ MCP server registry
- ✅ Configuration file generation
- ✅ HTTP/SSE API endpoints
- ✅ Per-user storage isolation

**On Startup:**
1. Initialize FastMCP server
2. Register built-in tools
3. Initialize registry from `data/mcp_servers/*.json`
4. **Generate client configurations:**
   - `~/.qwen/settings.json` (Qwen CLI)
   - `data/mcp_servers/mcp-hub.json` (standalone mode only)
5. Start HTTP/SSE server

**Configuration Generation:**
```python
# Automatic on startup
python -m src.mcp.mcp_hub_server

# Skip config generation
python -m src.mcp.mcp_hub_server --skip-config-gen
```

### Bot (`src/mcp/server_manager.py`)

**MCPServerManager Responsibilities:**
- ✅ Subprocess lifecycle (standalone mode only)
- ✅ Health monitoring
- ✅ Start/stop subprocess

**Does NOT:**
- ❌ Create configuration files
- ❌ Register MCP tools
- ❌ Manage MCP server registry

**Code:**
```python
class MCPServerManager:
    """
    Subprocess Lifecycle Manager (Standalone Mode Only)
    
    Docker mode: Does nothing (bot is pure client)
    Standalone mode: Launches MCP Hub subprocess
    """
    
    def setup_default_servers(self):
        mcp_hub_url = os.getenv("MCP_HUB_URL")
        
        if mcp_hub_url:
            # Docker mode: pure client, no action needed
            logger.info(f"Docker mode: connecting to {mcp_hub_url}")
        else:
            # Standalone mode: launch subprocess
            self._setup_memory_subprocess()
```

## Health Check Endpoint

The `/health` endpoint provides comprehensive information about the MCP Hub state:

```bash
curl http://localhost:8765/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "mcp-hub",
  "version": "1.0.0",
  "builtin_tools": {
    "total": 3,
    "names": [
      "store_memory",
      "retrieve_memory",
      "list_categories"
    ]
  },
  "registry": {
    "servers_total": 0,
    "servers_enabled": 0
  },
  "storage": {
    "active_users": 0
  },
  "ready": true
}
```

**Fields:**
- `builtin_tools` - MCP tools provided by the hub itself (always available)
- `registry.servers_total` - External MCP servers registered (user-added servers)
- `registry.servers_enabled` - Number of enabled external servers
- `storage.active_users` - Number of users with active storage sessions

## Configuration Files

### Who Creates What

| File | Created By | When | Mode |
|------|------------|------|------|
| `~/.qwen/settings.json` | MCP Hub | On startup | Both |
| `data/mcp_servers/mcp-hub.json` | MCP Hub | On startup | Standalone only |
| `data/mcp_servers/*.json` | User/Admin | Manual | Both |

### Configuration API

MCP Hub provides a dynamic configuration API:

```bash
# Get standard config (Cursor, Claude Desktop, Qwen CLI)
curl http://localhost:8765/config/client/standard

# Get LM Studio config
curl http://localhost:8765/config/client/lmstudio

# Download as file
curl http://localhost:8765/config/client/standard?format=raw \
  -o mcp-hub.json
```

## Migration Notes

### What Changed

**Before (❌ Wrong):**
- Bot created configs in both modes
- `MCPServerManager._create_qwen_config()` ran in Docker mode
- Config generation logic scattered across bot codebase
- Duplication between bot and MCP Hub

**After (✅ Correct):**
- MCP Hub owns ALL config generation
- Bot is pure client (no config creation)
- Single source of truth for MCP logic
- Clear separation of concerns

### Migration Checklist

- [x] Remove `_create_qwen_config()` from `MCPServerManager`
- [x] Remove `_setup_mcp_hub_connection()` from `MCPServerManager`
- [x] Remove config creation from `_setup_memory_subprocess()`
- [x] Add config generation to MCP Hub startup
- [x] Add `/config/client/{type}` API endpoint
- [x] Update `MCPServerManager` docstring
- [x] Update `setup_default_servers()` logic

## Testing

### Docker Mode Test

```bash
# Start services
docker-compose up

# Check MCP Hub health
curl http://localhost:8765/health

# Verify no configs created by bot
# (only by MCP Hub service)
```

### Standalone Mode Test

```bash
# Start bot
python -m main

# Verify MCP Hub subprocess started
ps aux | grep mcp_hub_server

# Verify configs created by MCP Hub
ls -la ~/.qwen/settings.json
ls -la data/mcp_servers/mcp-hub.json
```

### Config Generation Test

```bash
# Test dynamic config API
curl http://localhost:8765/config/client/standard | jq

# Expected output:
{
  "success": true,
  "client_type": "standard",
  "config": {
    "mcpServers": {
      "mcp-hub": {
        "url": "http://127.0.0.1:8765/sse",
        ...
      }
    }
  }
}
```

## Best Practices

### For Developers

1. **Never create configs in bot code**
   - All config generation belongs in MCP Hub
   - Bot is a pure client

2. **Use environment detection correctly**
   ```python
   mcp_hub_url = os.getenv("MCP_HUB_URL")
   if mcp_hub_url:
       # Docker mode
   else:
       # Standalone mode
   ```

3. **Add new MCP features in MCP Hub**
   - New tools → Add to `mcp_hub_server.py`
   - New configs → Add to `_generate_client_configs()`
   - New registry features → Add to registry module

### For DevOps

1. **Docker deployments**
   - Set `MCP_HUB_URL` environment variable
   - Bot will automatically be pure client

2. **Standalone deployments**
   - Don't set `MCP_HUB_URL`
   - Bot will launch MCP Hub subprocess

3. **Configuration management**
   - Configs are generated on MCP Hub startup
   - To regenerate: restart MCP Hub service

## Troubleshooting

### Issue: Logs show config generation in Docker mode

**Symptom:**
```
[MCPServerManager] Creating MCP configurations for various clients...
[MCPServerManager] Creating Qwen CLI config (HTTP/SSE mode)
```

**Cause:** Old code running (pre-refactor)

**Solution:** 
1. Verify you're on latest code
2. Check `MCPServerManager.setup_default_servers()` doesn't call `_create_qwen_config()`
3. Rebuild Docker images

### Issue: MCP Hub not creating configs

**Symptom:** `~/.qwen/settings.json` doesn't exist

**Possible causes:**
1. MCP Hub started with `--skip-config-gen` flag
2. Config generation failed (check logs)
3. Permission issues with home directory

**Solution:**
```bash
# Check MCP Hub logs
docker logs mcp-hub | grep "Generating client configurations"

# Manually trigger config generation via API
curl http://localhost:8765/config/client/standard
```

## Related Documentation

- [MCP Docker Setup](../deployment/mcp-docker-setup.md)
- [MCP Server Registry](../agents/mcp-server-registry.md)
- [MCP Tools](../agents/mcp-tools.md)
