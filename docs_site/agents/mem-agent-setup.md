# Memory Agent Setup Guide

This guide covers the installation, configuration, and usage of the integrated mem-agent - a personal note-taking and search system for autonomous agents.

## Overview

The memory agent is a local LLM-powered note-taking system specifically designed for the main agent. The agent uses it to:

- **Record notes**: Write down important information, findings, or context during task execution
- **Search notes**: Find and recall previously recorded information to "remember" details
- **Maintain context**: Keep working memory across multiple LLM calls within a single session

This is particularly useful for autonomous agents (like qwen code cli) that make many LLM calls within one continuous session.

The system uses the `driaforall/mem-agent` model from HuggingFace and can run on various backends:

- **vLLM** (Linux with GPU) - Best performance
- **MLX** (macOS with Apple Silicon) - Native ARM support
- **Transformers** (CPU fallback) - Works everywhere, slower

## Quick Start

### Installation

Run the installation script:

```bash
python scripts/install_mem_agent.py
```

This will:
1. Install all required dependencies
2. Download the mem-agent model from HuggingFace
3. Setup the memory directory structure
4. Create the MCP server configuration
5. Register mem-agent as an MCP server

### Configuration

Enable mem-agent in your `config.yaml`:

```yaml
# Enable MCP support
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true

# Memory agent settings
MEM_AGENT_MODEL: driaforall/mem-agent
MEM_AGENT_MODEL_PRECISION: 4bit
MEM_AGENT_BACKEND: auto
MEM_AGENT_MEMORY_POSTFIX: memory  # Postfix within KB (kb_path/memory)
MEM_AGENT_MAX_TOOL_TURNS: 20

# MCP settings
MCP_SERVERS_POSTFIX: .mcp_servers  # Per-user MCP servers (kb_path/.mcp_servers)
```

Or use environment variables in `.env`:

```bash
AGENT_ENABLE_MCP=true
AGENT_ENABLE_MCP_MEMORY=true
MEM_AGENT_MODEL=driaforall/mem-agent
MEM_AGENT_MODEL_PRECISION=4bit
MEM_AGENT_BACKEND=auto
MEM_AGENT_MEMORY_POSTFIX=memory
MCP_SERVERS_POSTFIX=.mcp_servers
```

### Verification

Test that mem-agent is installed correctly:

```bash
# Check if model is downloaded
huggingface-cli scan-cache | grep mem-agent

# Verify MCP server configuration exists
cat data/mcp_servers/mem-agent.json

# Check memory directory
ls -la knowledge_bases/default/memory/
```

## Advanced Installation

### Custom Model Location

```bash
python scripts/install_mem_agent.py \
  --model driaforall/mem-agent \
  --precision 8bit \
  --workspace /path/to/workspace
```

### Skip Model Download

If you've already downloaded the model:

```bash
python scripts/install_mem_agent.py --skip-model-download
```

### Platform-Specific Backends

#### Linux with GPU (vLLM)

```bash
# Install vLLM
pip install vllm

# Configure to use vLLM
export MEM_AGENT_BACKEND=vllm
export MEM_AGENT_VLLM_HOST=127.0.0.1
export MEM_AGENT_VLLM_PORT=8001
```

#### macOS with Apple Silicon (MLX)

```bash
# Install MLX
pip install mlx mlx-lm

# Configure to use MLX
export MEM_AGENT_BACKEND=mlx
export MEM_AGENT_MODEL_PRECISION=4bit
```

#### CPU Fallback (Transformers)

```bash
# Already installed with base dependencies
export MEM_AGENT_BACKEND=transformers
```

## Memory Structure

The memory agent uses an Obsidian-like file structure stored **per-user** within each knowledge base:

```
knowledge_bases/
└── {user_kb_name}/       # Each user has their own KB
    ├── .mcp_servers/     # Per-user MCP server configs
    │   └── mem-agent.json
    ├── memory/           # Per-user memory (postfix configurable)
    │   ├── user.md       # Personal information
    │   └── entities/     # Entity files
    │       ├── person_name.md
    │       ├── company_name.md
    │       └── place_name.md
    └── topics/           # User's notes
```

**Key Points:**
- Memory path is constructed as: `{kb_path}/{MEM_AGENT_MEMORY_POSTFIX}`
- MCP servers are stored at: `{kb_path}/{MCP_SERVERS_POSTFIX}`
- Each user gets their own isolated memory and MCP configuration

### user.md Structure

```markdown
# User Information
- user_name: John Doe
- user_age: 30
- user_location: San Francisco, CA

## User Relationships
- employer: [[entities/acme_corp.md]]
- spouse: [[entities/jane_doe.md]]

## Preferences
- favorite_color: blue
- favorite_food: pizza
```

### Entity File Structure

```markdown
# Acme Corporation
- entity_type: Company
- industry: Technology
- location: San Francisco, CA
- founded: 2010

## Employees
- ceo: [[entities/john_smith.md]]
```

## Usage

### Through Agent

The agent automatically uses mem-agent when enabled to record notes and search them:

```python
from src.agents import AgentFactory
from config.settings import settings

# Create agent with mem-agent enabled
agent = AgentFactory.from_settings(settings)

# The agent can record notes during task execution
# For example, during a complex task:
result = await agent.process({
    "text": "Analyze this codebase and suggest improvements"
})
# The agent internally records findings like:
# - "Found authentication vulnerability in login.py"
# - "Database queries missing indexes in user_service.py"
# - "Found 15 TODO comments that need attention"

# Later in the same session, the agent can search its notes:
# When asked about specific findings, the agent searches:
# "What security issues did I find?"
# And retrieves the authentication vulnerability note
```

### Direct API (Advanced)

```python
from config.settings import settings
from pathlib import Path

# Memory agent settings are now part of the main settings module
# Construct paths based on user's KB:
kb_path = Path("./knowledge_bases/user_kb_name")  # Get from user settings

print(f"Model: {settings.MEM_AGENT_MODEL}")
print(f"Memory postfix: {settings.MEM_AGENT_MEMORY_POSTFIX}")
print(f"Full memory path: {settings.get_mem_agent_memory_path(kb_path)}")
print(f"MCP servers dir: {settings.get_mcp_servers_dir(kb_path)}")
print(f"Backend: {settings.get_mem_agent_backend()}")

# The MemoryAgent and MemoryAgentMCPServer classes are planned for future development
```

## Model Selection

### Available Models

- **driaforall/mem-agent** (default) - Optimized for memory tasks
- **driaforall/mem-agent-8bit** - 8-bit quantized version
- **driaforall/mem-agent-4bit** - 4-bit quantized version (smallest)

### Changing Models

1. Update configuration:

```yaml
MEM_AGENT_MODEL: driaforall/mem-agent-8bit
MEM_AGENT_MODEL_PRECISION: 8bit
```

2. Download new model:

```bash
huggingface-cli download driaforall/mem-agent-8bit
```

3. Restart the application

### Model Download Management

Models are cached in HuggingFace cache directory:

```bash
# Check downloaded models
huggingface-cli scan-cache

# Delete specific model
huggingface-cli delete-cache --repo driaforall/mem-agent

# Clear entire cache
huggingface-cli delete-cache
```

## Configuration Options

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `MEM_AGENT_MODEL` | `driaforall/mem-agent` | HuggingFace model ID |
| `MEM_AGENT_MODEL_PRECISION` | `4bit` | Model precision (4bit, 8bit, fp16) |
| `MEM_AGENT_BACKEND` | `auto` | Backend (auto, vllm, mlx, transformers) |
| `MEM_AGENT_MEMORY_POSTFIX` | `memory` | Memory directory postfix within KB |
| `MEM_AGENT_MAX_TOOL_TURNS` | `20` | Max tool execution iterations |
| `MEM_AGENT_TIMEOUT` | `20` | Timeout for code execution (seconds) |
| `MEM_AGENT_VLLM_HOST` | `127.0.0.1` | vLLM server host |
| `MEM_AGENT_VLLM_PORT` | `8001` | vLLM server port |
| `MEM_AGENT_FILE_SIZE_LIMIT` | `1048576` | Max file size (1MB) |
| `MEM_AGENT_DIR_SIZE_LIMIT` | `10485760` | Max directory size (10MB) |
| `MEM_AGENT_MEMORY_SIZE_LIMIT` | `104857600` | Max total memory (100MB) |
| `MCP_SERVERS_POSTFIX` | `.mcp_servers` | MCP servers directory postfix within KB |

### Backend Selection Logic

The `auto` backend automatically selects the best available option:

1. **macOS**: MLX if available, else Transformers
2. **Linux**: vLLM if available, else Transformers
3. **Windows**: Transformers

## Performance Tuning

### GPU Acceleration (vLLM)

For best performance on Linux with GPU:

```yaml
MEM_AGENT_BACKEND: vllm
MEM_AGENT_MODEL_PRECISION: fp16
```

Adjust vLLM parameters:

```bash
# Run vLLM server separately for better control
vllm serve driaforall/mem-agent \
  --host 127.0.0.1 \
  --port 8001 \
  --tensor-parallel-size 1
```

### Memory Limits

Adjust memory size limits based on your use case:

```yaml
# For power users with lots of memories
MEM_AGENT_FILE_SIZE_LIMIT: 5242880      # 5MB per file
MEM_AGENT_DIR_SIZE_LIMIT: 52428800      # 50MB per directory  
MEM_AGENT_MEMORY_SIZE_LIMIT: 524288000  # 500MB total
```

### Response Time

Reduce max tool turns for faster responses:

```yaml
MEM_AGENT_MAX_TOOL_TURNS: 10  # Faster but less thorough
```

## Troubleshooting

### Model Download Issues

**Problem**: Model download fails or is very slow

**Solutions**:
1. Check internet connection
2. Try using a HuggingFace mirror:
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```
3. Download manually:
   ```bash
   huggingface-cli download driaforall/mem-agent --local-dir ./models/mem-agent
   ```

### Backend Issues

**Problem**: Backend initialization fails

**Solutions**:

1. For vLLM errors:
   ```bash
   # Ensure CUDA is available
   python -c "import torch; print(torch.cuda.is_available())"
   
   # Reinstall vLLM
   pip uninstall vllm
   pip install vllm --no-cache-dir
   ```

2. For MLX errors:
   ```bash
   # Ensure on macOS with Apple Silicon
   uname -m  # Should show arm64
   
   # Reinstall MLX
   pip uninstall mlx mlx-lm
   pip install mlx mlx-lm
   ```

3. Fallback to transformers:
   ```yaml
   MEM_AGENT_BACKEND: transformers
   ```

### Memory Path Issues

**Problem**: Memory files not being created

**Solutions**:

1. Check permissions:
   ```bash
   # Replace {user_kb} with actual KB name
   ls -la knowledge_bases/{user_kb}/memory/
   chmod -R 755 knowledge_bases/{user_kb}/memory/
   ```

2. Verify path in configuration:
   ```python
   from config.settings import settings
   from pathlib import Path
   
   kb_path = Path("./knowledge_bases/user_kb")
   print(f"Memory postfix: {settings.MEM_AGENT_MEMORY_POSTFIX}")
   print(f"Full path: {settings.get_mem_agent_memory_path(kb_path)}")
   ```

3. Create manually:
   ```bash
   # Replace {user_kb} with actual KB name
   mkdir -p knowledge_bases/{user_kb}/memory/entities
   touch knowledge_bases/{user_kb}/memory/user.md
   ```

### MCP Server Connection Issues

**Problem**: Agent can't connect to mem-agent MCP server

**Solutions**:

1. Verify server is registered:
   ```bash
   cat data/mcp_servers/mem-agent.json
   ```

2. Check if enabled:
   ```python
   from src.mcp_registry import MCPServersManager
   manager = MCPServersManager()
   manager.initialize()
   server = manager.get_server("mem-agent")
   print(f"Enabled: {server.enabled}")
   ```

3. Test server manually:
   ```bash
   python -m src.mem_agent.server
   ```

## Best Practices

### Memory Organization

1. **Use descriptive entity names**: `jane_doe.md`, not `person1.md`
2. **Link entities**: Use `[[entities/name.md]]` for relationships
3. **Keep files focused**: One entity per file
4. **Update regularly**: Memory agent will update files as it learns

### Model Selection

1. **Start with 4-bit**: Good balance of size and performance
2. **Upgrade to 8-bit**: If you have more RAM and want better quality
3. **Use fp16**: Only on GPU with plenty of VRAM

### Security

1. **Review memories**: Periodically check `knowledge_bases/{user_kb}/memory/` for sensitive info
2. **Set size limits**: Prevent memory from growing too large
3. **Backup regularly**: Memory files are plain text, easy to backup
4. **Per-user isolation**: Each user has isolated memory and MCP configs in their KB
5. **Knowledge base integration**: Memory is stored within your knowledge base structure

## See Also

- [MCP Server Registry](./mcp-server-registry.md) - Managing MCP servers
- [MCP Tools](./mcp-tools.md) - Using MCP tools in agents
- [Configuration](../reference/configuration.md) - Complete configuration reference