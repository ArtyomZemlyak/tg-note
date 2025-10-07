# mem-agent Migration Summary

This document summarizes the migration of mem-agent from https://github.com/firstbatchxyz/mem-agent-mcp to the tg-note repository.

## What Was Done

### 1. MCP Server Registry System

Created a comprehensive MCP server registry system that allows:

- **Dynamic server discovery** from JSON configuration files
- **Simple server management** (enable/disable/add/remove)
- **Support for both built-in and user-provided servers**
- **Flexible server configuration** through JSON files

**Files Created:**
- `src/mcp_registry/__init__.py` - Registry module exports
- `src/mcp_registry/registry.py` - Core registry implementation
- `src/mcp_registry/manager.py` - High-level registry manager
- `src/agents/mcp/registry_client.py` - MCP client that uses registry

**Directory Structure:**
- `data/mcp_servers/` - Directory for MCP server JSON configurations

### 2. Memory Agent Integration

Integrated the mem-agent as a native component with:

- **Local LLM-based memory** using HuggingFace models
- **Multiple backend support** (vLLM for Linux GPU, MLX for macOS, Transformers for CPU)
- **Automatic model download** via HuggingFace CLI
- **MCP server wrapper** for agent integration

**Files Created:**
- `src/mem_agent/__init__.py` - Memory agent module
- `scripts/install_mem_agent.py` - Installation and setup script

**Settings Integration:**
- Memory agent settings are now in `config/settings.py` (consolidated configuration)
- Settings use **postfix approach** for per-user paths:
  - `MEM_AGENT_MEMORY_POSTFIX` (default: "memory") - postfix within KB
  - `MCP_SERVERS_POSTFIX` (default: ".mcp_servers") - postfix within KB

**Directory Structure (Per-User):**
- `{kb_path}/{MEM_AGENT_MEMORY_POSTFIX}/` - Memory storage (e.g., `knowledge_bases/user_kb/memory/`)
- `{kb_path}/{MCP_SERVERS_POSTFIX}/` - MCP servers config (e.g., `knowledge_bases/user_kb/.mcp_servers/`)

### 3. Configuration Updates

Updated application settings to support mem-agent:

**Modified Files:**
- `config/settings.py` - Added mem-agent configuration fields
  - `MEM_AGENT_MODEL` - HuggingFace model ID
  - `MEM_AGENT_MODEL_PRECISION` - Model precision (4bit/8bit/fp16)
  - `MEM_AGENT_BACKEND` - Backend selection (auto/vllm/mlx/transformers)
  - `MEM_AGENT_MEMORY_POSTFIX` - Memory directory postfix within KB (per-user)
  - `MCP_SERVERS_POSTFIX` - MCP servers directory postfix within KB (per-user)

### 4. Dependencies

Added new optional dependencies for MCP and mem-agent:

**Modified Files:**
- `pyproject.toml` - Added dependency groups:
  - `[project.optional-dependencies.mcp]` - FastMCP for MCP servers
  - `[project.optional-dependencies.mem-agent]` - Memory agent dependencies
  - Updated core dependencies to include `huggingface-hub`

### 5. Documentation

Created comprehensive documentation for the new systems:

**Files Created:**
- `docs_site/agents/mcp-server-registry.md` - MCP registry documentation
- `docs_site/agents/mem-agent-setup.md` - Memory agent setup guide

## Key Features

### MCP Server Registry

1. **JSON-based Configuration**
   ```json
   {
     "name": "server-name",
     "description": "Server description",
     "command": "python",
     "args": ["-m", "module"],
     "env": {"VAR": "value"},
     "enabled": true
   }
   ```

2. **Simple Management API**
   ```python
   from src.mcp_registry import MCPServersManager
   
   manager = MCPServersManager()
   manager.initialize()
   
   # Enable/disable servers
   manager.enable_server("mem-agent")
   manager.disable_server("mem-agent")
   
   # Add custom servers
   manager.add_server_from_json(json_content)
   ```

3. **Automatic Discovery**
   - Scans `data/mcp_servers/*.json` on initialization
   - Only connects to enabled servers
   - Supports hot-reloading through re-initialization

### Memory Agent

1. **Local LLM Memory**
   - Uses `driaforall/mem-agent` model from HuggingFace
   - Stores memories in Obsidian-like markdown structure
   - Supports entity relationships and cross-references

2. **Flexible Backend**
   - **Auto-detection** based on platform
   - **vLLM** for Linux with GPU (best performance)
   - **MLX** for macOS with Apple Silicon
   - **Transformers** for CPU fallback

3. **Model Management**
   - Automatic download via HuggingFace CLI
   - Configurable precision (4bit/8bit/fp16)
   - Easy model switching through configuration

4. **Memory Structure**
   ```
   data/memory/
   ├── user.md              # User information
   └── entities/            # Entity files
       ├── person_name.md
       └── company_name.md
   ```

## Installation

### Quick Start

1. Install mem-agent:
   ```bash
   python scripts/install_mem_agent.py
   ```

2. Enable in configuration:
   ```yaml
   # config.yaml
   AGENT_ENABLE_MCP: true
   AGENT_ENABLE_MCP_MEMORY: true
   ```

3. Install optional dependencies:
   ```bash
   # For MCP support
   pip install ".[mcp]"
   
   # For mem-agent
   pip install ".[mem-agent]"
   
   # Platform-specific backends
   # macOS:
   pip install mlx mlx-lm
   
   # Linux with GPU:
   pip install vllm
   ```

### Advanced Installation

```bash
# Custom model and precision
python scripts/install_mem_agent.py \
  --model driaforall/mem-agent \
  --precision 8bit \
  --workspace /path/to/workspace

# Skip model download (if already downloaded)
python scripts/install_mem_agent.py --skip-model-download
```

## Architecture Changes

### Before

```
Agent → MCP Client → External MCP Server (Node.js)
                    (requires npm install @firstbatch/mem-agent-mcp)
```

### After

```
Agent → MCP Registry Client → MCP Server Registry
         ↓                      ↓
         └→ MCP Clients    → Discovered Servers
                              ├── mem-agent (Python)
                              ├── other-server-1
                              └── other-server-2
```

**Key Improvements:**
1. **No OpenAI API required** - Uses local LLM models
2. **Python-based** - No Node.js/npm dependency for mem-agent
3. **Dynamic discovery** - Servers configured via JSON files
4. **Easy to extend** - Add new servers by dropping JSON files
5. **Memory stored per-user in KB** - Path constructed as `{kb_path}/{postfix}` for isolation

## Configuration Examples

### Minimal Configuration

```yaml
# config.yaml
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true
```

### Full Configuration

```yaml
# config.yaml

# MCP Settings
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true
MCP_SERVERS_POSTFIX: .mcp_servers

# Memory Agent Settings
MEM_AGENT_MODEL: driaforall/mem-agent
MEM_AGENT_MODEL_PRECISION: 4bit
MEM_AGENT_BACKEND: auto
MEM_AGENT_MEMORY_POSTFIX: memory  # Postfix within KB
MCP_SERVERS_POSTFIX: .mcp_servers  # Per-user MCP servers
MEM_AGENT_MAX_TOOL_TURNS: 20

# vLLM Settings (Linux with GPU)
MEM_AGENT_VLLM_HOST: 127.0.0.1
MEM_AGENT_VLLM_PORT: 8001
```

## Future Enhancements

### Planned Features

1. **Bot Commands for MCP Management**
   ```
   /mcp list
   /mcp enable <server>
   /mcp disable <server>
   /mcp add <server> [upload JSON]
   ```

2. **User-Uploaded MCP Servers**
   - Users can upload custom MCP server JSON configs via bot
   - Automatic validation and sandboxing
   - Per-user server configurations

3. **Memory Visualization**
   - Web UI to browse memory structure
   - Entity relationship graphs
   - Memory search and filtering

4. **Multi-User Memory**
   - Separate memory spaces per user
   - Shared entity databases
   - Privacy controls

5. **Memory Synchronization**
   - Sync memories with cloud storage
   - Backup and restore
   - Cross-device memory sharing

## Migration Checklist

- [x] Created MCP server registry system
- [x] Integrated mem-agent as Python module
- [x] Added installation script with HuggingFace CLI integration
- [x] Updated settings with mem-agent configuration
- [x] Created memory directory structure
- [x] Updated MCP tools to use registry
- [x] Added dependencies to pyproject.toml
- [x] Created comprehensive documentation
- [ ] Add bot commands for MCP management (future)
- [ ] Implement user-uploaded MCP servers (future)
- [ ] Add memory visualization UI (future)

## Testing

### Verify Installation

```bash
# Check MCP server registry
python -c "
from src.mcp_registry import MCPServersManager
manager = MCPServersManager()
manager.initialize()
print(f'Found {len(manager.get_all_servers())} servers')
print(f'Enabled: {len(manager.get_enabled_servers())} servers')
"

# Check memory directory
# Example for user with KB at knowledge_bases/user_kb
ls -la knowledge_bases/user_kb/memory/
ls -la knowledge_bases/user_kb/.mcp_servers/

# Check mem-agent configuration
cat data/mcp_servers/mem-agent.json
```

### Test Memory Agent

```python
from config.settings import settings
from pathlib import Path

# Memory agent settings use postfix approach
kb_path = Path("./knowledge_bases/user_kb")  # Get from user settings

print(f"Model: {settings.MEM_AGENT_MODEL}")
print(f"Precision: {settings.MEM_AGENT_MODEL_PRECISION}")
print(f"Backend: {settings.get_mem_agent_backend()}")
print(f"Memory postfix: {settings.MEM_AGENT_MEMORY_POSTFIX}")
print(f"Full memory path: {settings.get_mem_agent_memory_path(kb_path)}")
print(f"MCP servers dir: {settings.get_mcp_servers_dir(kb_path)}")
```

## Known Issues

1. **Large Model Downloads**: The mem-agent model is several GB, downloads may take time
2. **Backend Selection**: Auto-detection may not always choose optimal backend
3. **Memory Limits**: Default limits may be too restrictive for power users

## Support

For issues, questions, or contributions:

1. Check documentation:
   - [MCP Server Registry](docs_site/agents/mcp-server-registry.md)
   - [Memory Agent Setup](docs_site/agents/mem-agent-setup.md)

2. Review configuration:
   - Settings in `config/settings.py`
   - Server configs in `data/mcp_servers/`

3. Check logs for errors:
   - Application logs in `logs/bot.log`
   - MCP server errors in stderr

## Conclusion

The migration successfully integrates mem-agent as a native Python component with:

- ✅ **No external dependencies** (no Node.js/npm required)
- ✅ **Local LLM models** (no OpenAI API key needed)
- ✅ **Flexible architecture** (easy to add new MCP servers)
- ✅ **Simple configuration** (JSON files + settings)
- ✅ **Memory stored locally** (alongside knowledge base)
- ✅ **Automatic model management** (HuggingFace CLI)
- ✅ **Multiple backends** (vLLM/MLX/Transformers)
- ✅ **Comprehensive documentation**

The system is now ready for production use and future enhancements!