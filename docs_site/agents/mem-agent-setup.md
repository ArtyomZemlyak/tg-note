# Memory System Setup Guide

This guide covers the installation, configuration, and usage of the MCP Memory system - a flexible note-taking and search system for autonomous agents with multiple storage backends.

## Overview

The MCP Memory system is a local note-taking and search system specifically designed for autonomous agents. The agent uses it to:

- **Record notes**: Write down important information, findings, or context during task execution
- **Search notes**: Find and recall previously recorded information to "remember" details
- **Maintain context**: Keep working memory across multiple LLM calls within a single session
- **Organize information**: Intelligently structure and link related information (advanced modes)

This is particularly useful for autonomous agents (like qwen code cli) that make many LLM calls within one continuous session.

**Deployment Model**: The mem-agent system is designed for **Docker-first deployment**. LLM model inference is handled by separate containers (vLLM, SGLang, or LM Studio), not by direct Python dependencies. This keeps the main application lightweight and scalable.

### Storage Types

The system supports three storage backends:

#### 1. JSON Storage (Default)

- **Simple and Fast**: File-based JSON storage with substring search
- **No Dependencies**: No ML models or additional libraries required
- **Lightweight**: Minimal memory footprint
- **Best for**: Most users, small to medium memory sizes, simple search needs

#### 2. Vector Storage

- **AI-Powered**: Semantic search using embeddings from HuggingFace models (e.g., `BAAI/bge-m3`)
- **Smart Search**: Understands meaning, not just keywords
- **Best for**: Large memory sizes, complex queries, semantic understanding needed
- **Requires**: Additional dependencies (transformers, sentence-transformers)

#### 3. Mem-Agent Storage (Advanced)

- **LLM-Based**: Uses an LLM (driaforall/mem-agent) to reason about memory operations
- **Structured Memory**: Obsidian-style markdown files with wiki-links
- **Intelligent Organization**: Automatically creates and links entities, maintains relationships
- **Best for**: Complex scenarios requiring intelligent memory organization
- **Requires**: LLM inference container (vLLM/SGLang/LM Studio), lightweight dependencies (fastmcp)

The storage type is configured via `MEM_AGENT_STORAGE_TYPE` setting (default: `json`).

## Quick Start

### Docker Deployment (Recommended)

The recommended way to deploy mem-agent is using Docker containers:

```bash
# Start all services (bot, MCP hub, vLLM server)
docker-compose up -d

# Or with SGLang backend for faster inference
docker-compose -f docker-compose.yml -f docker-compose.sglang.yml up -d

# Or without GPU (JSON storage mode only)
docker-compose -f docker-compose.simple.yml up -d
```

The Docker setup automatically:
1. Installs lightweight dependencies (fastmcp, etc.)
2. Runs the LLM model in a separate container (vLLM/SGLang)
3. Configures MCP hub with memory tools
4. Sets up proper networking between containers

See [Docker Deployment Guide](../deployment/docker.md) for more details.

### Local Installation (Development Only)

For local development without Docker:

```bash
python scripts/install_mem_agent.py
```

Note: This will install lightweight dependencies only. You'll need to run a separate LLM server (vLLM, SGLang, or LM Studio) for mem-agent storage type.

### Configuration

Enable memory system in your `config.yaml`:

```yaml
# Enable MCP support
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true

# Memory storage settings
MEM_AGENT_STORAGE_TYPE: json  # Storage type: "json", "vector", or "mem-agent"
MEM_AGENT_MODEL: BAAI/bge-m3  # Model for embeddings (vector) or LLM (mem-agent)
MEM_AGENT_MODEL_PRECISION: 4bit
MEM_AGENT_BACKEND: auto
MEM_AGENT_MAX_TOOL_TURNS: 20  # For mem-agent storage type only

# MCP settings
```

Or use environment variables in `.env`:

```bash
AGENT_ENABLE_MCP=true
AGENT_ENABLE_MCP_MEMORY=true
MEM_AGENT_STORAGE_TYPE=json  # "json", "vector", or "mem-agent"
MEM_AGENT_MODEL=BAAI/bge-m3  # or driaforall/mem-agent for LLM-based
MEM_AGENT_MODEL_PRECISION=4bit
MEM_AGENT_BACKEND=auto
```

#### Choosing Storage Type

**Use JSON storage (default) if:**

- You want fast, lightweight storage
- Simple keyword search is sufficient
- You don't want to download ML models
- You have limited resources

**Use Vector storage if:**

- You need semantic search (understands meaning)
- You have large amounts of memories
- You want AI-powered relevance ranking
- You have resources for ML models

**Use Mem-Agent storage if:**

- You need intelligent memory organization
- You want structured Obsidian-style notes with wiki-links
- You need the system to understand relationships between entities
- You have resources for running an LLM

To enable vector storage:

1. Set `MEM_AGENT_STORAGE_TYPE: vector` in config
2. Install embedding model dependencies (development only):

   ```bash
   pip install sentence-transformers transformers torch
   ```

3. The embedding model will be downloaded automatically on first use

To enable mem-agent storage:

1. Set `MEM_AGENT_STORAGE_TYPE: mem-agent` in config
2. Set `MEM_AGENT_MODEL: driaforall/mem-agent` in config
3. **Docker (Recommended)**: Start vLLM/SGLang container - model downloads automatically:
   ```bash
   docker-compose up -d vllm-server  # or use sglang overlay
   ```

4. **Local Development**: Run LLM server separately:
   ```bash
   # Option A: vLLM
   vllm serve driaforall/mem-agent --host 127.0.0.1 --port 8001

   # Option B: LM Studio - load model via UI
   # Option C: SGLang
   python -m sglang.launch_server --model driaforall/mem-agent --port 8001
   ```

5. Configure endpoint in `.env` or `config.yaml`:
   ```bash
   MEM_AGENT_BASE_URL=http://127.0.0.1:8001/v1
   MEM_AGENT_OPENAI_API_KEY=lm-studio
   ```

### Verification

Test that mem-agent is installed correctly:

```bash
# Check if model is downloaded
huggingface-cli scan-cache | grep mem-agent

# Verify MCP server configuration exists
cat data/mcp_servers/mem-agent.json

# Check memory directory (per-user)
ls -la data/memory/user_123/
```

## Advanced Installation

### Custom Model Location

```bash
python scripts/install_mem_agent.py \
  --model BAAI/bge-m3 \
  --precision 8bit \
  --workspace /path/to/workspace
```

### Skip Model Download

If you've already downloaded the model:

```bash
python scripts/install_mem_agent.py --skip-model-download
```

### Platform-Specific Backends

**IMPORTANT**: Direct Python backends (transformers, MLX, vLLM pip packages) are **DEPRECATED** for production use.

Use Docker containers or external LLM servers instead:

#### Docker Deployment (Recommended)

```bash
# Linux/GPU: vLLM container
docker-compose up -d vllm-server

# Linux/GPU: SGLang container (faster)
docker-compose -f docker-compose.yml -f docker-compose.sglang.yml up -d

# macOS/No GPU: LM Studio
# Download and run LM Studio, load driaforall/mem-agent model
# Configure: MEM_AGENT_BASE_URL=http://host.docker.internal:1234/v1
```

#### Local Development

```bash
# Option 1: LM Studio (easiest, works on all platforms)
# 1. Install LM Studio from https://lmstudio.ai/
# 2. Load driaforall/mem-agent model
# 3. Configure:
export MEM_AGENT_BASE_URL=http://127.0.0.1:1234/v1
export MEM_AGENT_OPENAI_API_KEY=lm-studio

# Option 2: vLLM (Linux with GPU)
# Install: pip install vllm
vllm serve driaforall/mem-agent --host 127.0.0.1 --port 8001
export MEM_AGENT_BASE_URL=http://127.0.0.1:8001/v1

# Option 3: SGLang (Linux with GPU, faster than vLLM)
# Install: pip install sglang
python -m sglang.launch_server --model driaforall/mem-agent --port 8001
export MEM_AGENT_BASE_URL=http://127.0.0.1:8001/v1
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

## Available Tools

The MCP Memory server provides three tools that the agent can use:

### 1. `store_memory`
Stores information in memory for later retrieval.

**Parameters:**
- `content` (string, required): Content to store in memory
- `category` (string, optional): Category for organization (e.g., 'tasks', 'notes', 'ideas'). Default: "general"
- `tags` (array of strings, optional): Tags for categorization
- `metadata` (object, optional): Additional metadata

**Example:**
```json
{
  "content": "Found authentication vulnerability in login.py",
  "category": "security",
  "tags": ["vulnerability", "authentication"]
}
```

### 2. `retrieve_memory`
Retrieves information from memory.

**Parameters:**
- `query` (string, optional): Search query. Returns all memories if not specified
- `category` (string, optional): Filter by category
- `tags` (array of strings, optional): Filter by tags
- `limit` (integer, optional): Maximum number of results. Default: 10

**Example:**
```json
{
  "query": "authentication",
  "category": "security",
  "limit": 5
}
```

### 3. `list_categories`
Lists all memory categories with counts.

**Parameters:** None

**Returns:** List of categories with memory counts

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

- **BAAI/bge-m3** (default) - High-quality multilingual embedding model
- Any sentence-transformers compatible model can be used

### Changing Models

1. Update configuration:

```yaml
MEM_AGENT_MODEL: sentence-transformers/all-MiniLM-L6-v2
MEM_AGENT_MODEL_PRECISION: fp16
```

2. Download new model:

```bash
huggingface-cli download BAAI/bge-m3
```

3. Restart the application

### Model Download Management

Models are cached in HuggingFace cache directory:

```bash
# Check downloaded models
huggingface-cli scan-cache

# Delete specific model
huggingface-cli delete-cache --repo BAAI/bge-m3

# Clear entire cache
huggingface-cli delete-cache
```

## Configuration Options

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `MEM_AGENT_STORAGE_TYPE` | `json` | Storage type: `json`, `vector`, or `mem-agent` |
| `MEM_AGENT_MODEL` | `BAAI/bge-m3` | Model ID (embeddings for vector, LLM for mem-agent) |
| `MEM_AGENT_MODEL_PRECISION` | `4bit` | Model precision (4bit, 8bit, fp16) |
| `MEM_AGENT_BACKEND` | `auto` | Backend (auto, vllm, mlx, transformers) |
| `MEM_AGENT_MAX_TOOL_TURNS` | `20` | Max tool execution iterations (mem-agent only) |
| `MEM_AGENT_TIMEOUT` | `20` | Timeout for code execution (mem-agent only) |
| `MEM_AGENT_BASE_URL` | `null` | OpenAI-compatible endpoint URL (e.g., http://localhost:8001/v1) - configure in config.yaml or env |
| `MEM_AGENT_OPENAI_API_KEY` | `null` | API key for the endpoint (use "lm-studio" for local) - configure in config.yaml or env |
| `MEM_AGENT_FILE_SIZE_LIMIT` | `1048576` | Max file size - 1MB (mem-agent only) |
| `MEM_AGENT_DIR_SIZE_LIMIT` | `10485760` | Max directory size - 10MB (mem-agent only) |
| `MEM_AGENT_MEMORY_SIZE_LIMIT` | `104857600` | Max total memory - 100MB (mem-agent only) |

### Storage Type Comparison

| Feature | JSON Storage | Vector Storage | Mem-Agent Storage |
|---------|-------------|----------------|-------------------|
| Search Type | Substring match | Semantic similarity | LLM-powered understanding |
| Speed | Very fast | Moderate | Slower (LLM inference) |
| Memory Usage | Minimal | Higher (embedding model) | Highest (LLM model) |
| Dependencies | None | transformers, sentence-transformers | fastmcp (+ external LLM server) |
| Model Download | Not required | Required (~400MB) | Required (~8GB, in container/server) |
| Organization | Simple key-value | Embeddings-based | Structured Obsidian-style |
| Best Use Case | Simple searches | Semantic queries | Complex reasoning & organization |
| Example Query | "vulnerability" → exact match | "security issue" → semantic match | Natural language queries with context |

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
# Note: vLLM is for LLM inference, not for embeddings
# For embeddings, the model is loaded directly via sentence-transformers
# vllm serve BAAI/bge-m3 \
#   --host 127.0.0.1 \
#   --port 8001 \
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
   huggingface-cli download BAAI/bge-m3 --local-dir ./models/bge-m3
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
   ls -la data/memory/user_{user_id}/
   chmod -R 755 data/memory/user_{user_id}/
   ```

2. Verify path in configuration:

   ```python
   from config.settings import settings
   from pathlib import Path

   user_id = 123
   print(f"Full path: {settings.get_mem_agent_memory_dir(user_id)}")
   ```

3. Create manually:

   ```bash
   # Replace {user_kb} with actual KB name
   mkdir -p data/memory/user_{user_id}/entities
   touch data/memory/user_{user_id}/user.md
   ```

### MCP Server Connection Issues

**Problem**: Agent can't connect to mem-agent MCP server

**Solutions**:

1. Verify server configuration follows standard MCP format:

   ```bash
   cat data/mcp_servers/mem-agent.json
   ```

   Should contain:

   ```json
   {
     "mcpServers": {
       "mem-agent": {
         "url": "http://127.0.0.1:8765/sse",
         "timeout": 10000,
         "trust": true,
         "description": "..."
       }
     }
   }
   ```

   See [MCP Configuration Format](mcp-config-format.md) for details.

2. Verify HTTP server is running:

   ```bash
   # Server should auto-start with bot
   # Check logs for: "[MCPServerManager] ✓ Server 'mem-agent' started successfully"
   ```

3. Test server manually:

   ```bash
   python -m src.agents.mcp.mem_agent_server_http --host 127.0.0.1 --port 8765
   ```

4. Test SSE endpoint:

   ```bash
   curl http://127.0.0.1:8765/sse
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

1. **Review memories**: Periodically check `data/memory/user_{user_id}/` for sensitive info
2. **Set size limits**: Prevent memory from growing too large
3. **Backup regularly**: Memory files are plain text, easy to backup
4. **Per-user isolation**: Each user has isolated memory and MCP configs in their KB
5. **Knowledge base integration**: Memory is stored within your knowledge base structure

## See Also

- [MCP Server Registry](./mcp-server-registry.md) - Managing MCP servers
- [MCP Tools](./mcp-tools.md) - Using MCP tools in agents
- [Configuration](../reference/configuration.md) - Complete configuration reference
