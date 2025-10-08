# MCP Configuration Format Migration

## Summary

Migrated `data/mcp_servers/mem-agent.json` from a custom format to the standard MCP (Model Context Protocol) configuration format used by Cursor, Claude Desktop, Qwen CLI, and other MCP clients.

## Changes Made

### 1. Configuration Format (`server_manager.py`)

**Before** (Custom format):
```json
{
  "name": "mem-agent",
  "description": "...",
  "command": "python",
  "args": [...],
  "env": {},
  "working_dir": "...",
  "enabled": true,
  "transport": "http"
}
```

**After** (Standard MCP format):
```json
{
  "mcpServers": {
    "mem-agent": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "...",
      "_stdio_variant": {
        "command": "python",
        "args": [...],
        "cwd": "...",
        "env": {},
        "timeout": 10000,
        "trust": true,
        "description": "..."
      }
    }
  }
}
```

### 2. Configuration Reader (`memory_agent_tool.py`)

Updated `mcp_server_config` property to:
- Read the standard `mcpServers` structure
- Support both HTTP/SSE and stdio transports
- Handle the `url` field for HTTP/SSE
- Use `cwd` instead of `working_dir` for stdio
- Fall back to defaults if config is missing or invalid

### 3. Documentation

Created new documentation:
- **`docs_site/agents/mcp-config-format.md`** - Comprehensive guide to MCP configuration format
  - HTTP/SSE transport specification
  - stdio transport specification
  - Field descriptions and requirements
  - Compatibility information
  - Migration guide

Updated existing documentation:
- **`docs_site/agents/mem-agent-setup.md`** - Updated troubleshooting section with new format
- **`docs_site/architecture/per-user-storage.md`** - Added references to format documentation

## Standard MCP Format Details

### HTTP/SSE Transport (Default)

```json
{
  "mcpServers": {
    "server-name": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "Server description"
    }
  }
}
```

**Required fields:**
- `url` - SSE endpoint URL
- `timeout` - Connection timeout in milliseconds
- `trust` - Whether to trust this server
- `description` - Human-readable description

### stdio Transport

```json
{
  "mcpServers": {
    "server-name": {
      "command": "python",
      "args": ["-m", "module.path"],
      "cwd": "/path/to/working/dir",
      "env": {},
      "timeout": 10000,
      "trust": true,
      "description": "Server description"
    }
  }
}
```

**Required fields:**
- `command` - Command to execute
- `args` - Command arguments
- `cwd` - Working directory (note: was `working_dir` in old format)
- `env` - Environment variables
- `timeout` - Connection timeout in milliseconds
- `trust` - Whether to trust this server
- `description` - Human-readable description

## Key Differences

### Top-Level Structure
- **Old**: Configuration at root level
- **New**: Configuration under `mcpServers` key with server name as sub-key

### Field Names
- **Old**: `working_dir`
- **New**: `cwd` (standard MCP field name)

### Transport Specification
- **Old**: Custom `transport` field with custom values
- **New**: Presence of `url` field indicates HTTP/SSE, presence of `command` indicates stdio

### Additional Fields
- **Old**: Custom fields like `name`, `enabled`
- **New**: Standard fields only, with internal metadata prefixed with `_`

## Compatibility

The new format is compatible with:
- ✓ Cursor MCP
- ✓ Claude Desktop
- ✓ Qwen CLI
- ✓ Other MCP clients following the standard

## Internal Metadata

Fields prefixed with `_` are for internal use and ignored by standard MCP clients:
- `_transport` - Transport type hint
- `_command` - Command for internal process management
- `_args` - Arguments for internal process management
- `_cwd` - Working directory for internal use
- `_stdio_variant` - Complete stdio configuration for reference

## Migration Path

### Automatic Migration
When the bot starts:
1. Old format files will be ignored
2. New format files will be auto-generated
3. No manual intervention required

### Manual Migration
If you have customizations:
1. Read old configuration
2. Map fields to new format:
   - `working_dir` → `cwd`
   - Add `mcpServers` wrapper
   - Add `timeout` and `trust` fields
   - For HTTP: Add `url` field
   - For stdio: Keep `command`, `args`, `env`

### Validation
Run validation test:
```bash
python3 -c "
import json
from pathlib import Path

config_file = Path('data/mcp_servers/mem-agent.json')
config = json.load(open(config_file))

assert 'mcpServers' in config, 'Missing mcpServers key'
assert 'mem-agent' in config['mcpServers'], 'Missing mem-agent'
mem_agent = config['mcpServers']['mem-agent']

if 'url' in mem_agent:
    print('✓ HTTP/SSE format valid')
    assert 'timeout' in mem_agent
    assert 'trust' in mem_agent
    assert 'description' in mem_agent
elif 'command' in mem_agent:
    print('✓ stdio format valid')
    assert 'args' in mem_agent
    assert 'cwd' in mem_agent
    assert 'env' in mem_agent
else:
    raise ValueError('Invalid format')

print('✓ Configuration is valid!')
"
```

## Files Modified

1. **src/agents/mcp/server_manager.py** - Generate standard format
2. **src/agents/mcp/memory_agent_tool.py** - Read standard format
3. **docs_site/agents/mcp-config-format.md** - New documentation
4. **docs_site/agents/mem-agent-setup.md** - Updated examples
5. **docs_site/architecture/per-user-storage.md** - Added references

## Benefits

1. **Standardization** - Follows official MCP specification
2. **Compatibility** - Works with multiple MCP clients
3. **Maintainability** - Easier to understand and maintain
4. **Documentation** - Well-documented standard format
5. **Future-proof** - Compatible with future MCP tools

## References

- [MCP Configuration Format Documentation](docs_site/agents/mcp-config-format.md)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Cursor MCP Documentation](https://docs.cursor.com/context/mcp)
- [Qwen Config Generator](src/agents/mcp/qwen_config_generator.py)

## Testing

The configuration was validated to ensure:
- ✓ Correct structure with `mcpServers` key
- ✓ HTTP/SSE fields present and valid
- ✓ stdio variant included for reference
- ✓ Compatible with qwen_config_generator.py patterns
- ✓ Readable by memory_agent_tool.py

## Date

Migration completed: 2025-10-08
