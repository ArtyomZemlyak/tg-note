# Memory Agent (mem-agent) Integration Summary

## Overview

Successfully integrated the mem-agent implementation from [firstbatchxyz/mem-agent-mcp](https://github.com/firstbatchxyz/mem-agent-mcp) into the tg-note project.

## What Was Added

### Core Implementation Files

All files are located in `/workspace/src/agents/mcp/memory/mem_agent_impl/`:

1. **`__init__.py`** - Package initialization with main exports
2. **`agent.py`** - Main Agent class for chat and memory operations
3. **`engine.py`** - Sandboxed Python code execution engine
4. **`model.py`** - Model interface supporting vLLM and OpenRouter
5. **`schemas.py`** - Pydantic schemas (ChatMessage, AgentResponse, StaticMemory, etc.)
6. **`settings.py`** - Settings integration with main config
7. **`tools.py`** - File and directory operations for memory management
8. **`utils.py`** - Utility functions (code extraction, formatting, etc.)
9. **`system_prompt.txt`** - System prompt defining agent behavior
10. **`mcp_server.py`** - MCP server implementation with 4 tools
11. **`README.md`** - Comprehensive documentation

### Documentation & Examples

1. **`examples/mem_agent_example.py`** - Usage example with conversations
2. **`tests/test_mem_agent.py`** - Comprehensive unit tests
3. **`scripts/test_mem_agent_basic.py`** - Basic validation script

### Updated Files

1. **`pyproject.toml`**:
   - Updated `mem-agent` dependencies to include `black>=23.0.0`
   - Updated `mem-agent-linux` to use `vllm>=0.5.5`

2. **`scripts/install_mem_agent.py`**:
   - Updated default model to `driaforall/mem-agent`
   - Added MCP server start instructions

## Model Information

- **Model**: [driaforall/mem-agent](https://huggingface.co/driaforall/mem-agent)
- **Base Model**: Qwen3-4B-Thinking-2507
- **Training Method**: GSPO (Zheng et al., 2025)
- **Purpose**: LLM-based agent for Obsidian-like memory management

## Key Features

### 1. Structured Memory System
- Obsidian-style markdown files with wiki-links
- `user.md` for user information and relationships
- `entities/` directory for people, places, organizations
- Cross-references using `[[entity_name]]` syntax

### 2. Sandboxed Execution
- Safe Python code execution in isolated environment
- Path restrictions to prevent unauthorized file access
- Timeout protection (configurable, default 20s)
- Size limits for files, directories, and total memory

### 3. MCP Integration
Four MCP tools exposed:
- `chat_with_memory`: Full bidirectional interaction
- `query_memory`: Read-only information retrieval
- `save_to_memory`: Explicit information storage
- `list_memory_structure`: View memory organization

### 4. Flexible Backend Support
- **vLLM** (recommended for Linux): High-performance inference
- **MLX** (recommended for macOS): Apple Silicon optimization
- **OpenRouter** (cloud): Fallback option
- **Transformers** (local): Portable but slower

## Installation

### 1. Install Dependencies

```bash
# Using the installation script (recommended)
python3 scripts/install_mem_agent.py

# Or install manually
pip install transformers huggingface-hub fastmcp aiofiles pydantic python-dotenv jinja2 black

# For Linux (vLLM backend)
pip install vllm>=0.5.5

# For macOS (MLX backend)
pip install mlx mlx-lm
```

### 2. Download Model

```bash
# Automatically downloaded during installation
python3 scripts/install_mem_agent.py

# Or download manually
huggingface-cli download driaforall/mem-agent
```

### 3. Configure Settings

In `config.yaml` or `.env`:

```yaml
# Enable MCP memory tools
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true

# Memory agent settings
MEM_AGENT_MAX_TOOL_TURNS: 20
MEM_AGENT_TIMEOUT: 20
MEM_AGENT_MEMORY_POSTFIX: memory
MEM_AGENT_VLLM_HOST: 127.0.0.1
MEM_AGENT_VLLM_PORT: 8000

# Size limits
MEM_AGENT_FILE_SIZE_LIMIT: 1048576      # 1MB
MEM_AGENT_DIR_SIZE_LIMIT: 10485760      # 10MB
MEM_AGENT_MEMORY_SIZE_LIMIT: 104857600  # 100MB
```

## Usage Examples

### Standalone Usage

```python
from src.agents.mcp.memory.mem_agent_impl import Agent

# Create agent
agent = Agent(
    memory_path="/path/to/memory",
    use_vllm=True,
    model="driaforall/mem-agent"
)

# Save information
response = agent.chat("My name is Alice and I work at Google")
print(response.reply)

# Query information
response = agent.chat("What is my name?")
print(response.reply)
```

### MCP Server Usage

```bash
# Start MCP server
python3 -m src.agents.mcp.memory.mem_agent_impl.mcp_server --host 127.0.0.1 --port 8766

# Or with custom settings
python3 -m src.agents.mcp.memory.mem_agent_impl.mcp_server --host 0.0.0.0 --port 9000
```

### With vLLM Backend

```bash
# Start vLLM server
python3 -m vllm.entrypoints.openai.api_server \
    --model driaforall/mem-agent \
    --host 127.0.0.1 \
    --port 8000

# Agent will automatically connect to vLLM
```

## Architecture Integration

### Memory Path Structure

```
knowledge_base/
└── {user_kb_name}/
    ├── topics/              # User's knowledge base content
    ├── .mcp_servers/        # MCP server configurations
    └── memory/              # mem-agent memory (new)
        ├── user.md
        └── entities/
            ├── person1.md
            └── company1.md
```

Each user's memory is isolated in their own KB directory.

### Settings Integration

The mem-agent integrates seamlessly with existing settings:
- Reads from `config.settings` when available
- Falls back to environment variables
- Provides sensible defaults

### Import Structure

```python
# Main imports
from src.agents.mcp.memory.mem_agent_impl import Agent, AgentResponse

# MCP server
from src.agents.mcp.memory.mem_agent_impl.mcp_server import run_server

# Settings
from src.agents.mcp.memory.mem_agent_impl.settings import get_memory_path

# Schemas
from src.agents.mcp.memory.mem_agent_impl.schemas import ChatMessage, Role
```

## Agent Response Format

The agent uses structured XML tags:

```xml
<think>
Reasoning about memory operations needed...
</think>

<python>
# Sandboxed code execution
content = read_file("user.md")
result = update_file("user.md", old_content, new_content)
</python>

<reply>
Final response to user
</reply>
```

## Memory Tools API

Available in sandboxed Python environment:

```python
# File operations
create_file(file_path: str, content: str = "") -> bool
update_file(file_path: str, old_content: str, new_content: str) -> Union[bool, str]
read_file(file_path: str) -> str
delete_file(file_path: str) -> bool
check_if_file_exists(file_path: str) -> bool

# Directory operations
create_dir(dir_path: str) -> bool
list_files() -> str
check_if_dir_exists(dir_path: str) -> bool

# Utilities
get_size(file_or_dir_path: str) -> int
go_to_link(link_string: str) -> str
```

## Testing

### Run Basic Tests

```bash
# Without pytest (basic validation)
python3 scripts/test_mem_agent_basic.py

# With pytest (comprehensive tests)
python3 -m pytest tests/test_mem_agent.py -v
```

### Run Example

```bash
# Make sure dependencies are installed first
python3 examples/mem_agent_example.py
```

## Security Considerations

### Sandboxed Execution
- Code runs in subprocess with restricted environment
- File access limited to allowed memory path
- Timeout prevents infinite loops
- Size limits prevent resource exhaustion

### Path Security
- All file operations validated against allowed path
- Absolute paths enforced
- Parent directory traversal prevented

### Resource Limits
- File size: 1MB (default)
- Directory size: 10MB (default)
- Total memory: 100MB (default)
- Execution timeout: 20s (default)

## Known Limitations

1. **Model Requirements**: Requires ~4GB VRAM for 4-bit quantization
2. **Inference Speed**: Local inference may be slower than cloud APIs
3. **Context Length**: Limited by base model context (varies by version)
4. **Language Support**: Optimized for English, may work with other languages

## Troubleshooting

### Import Errors

```bash
# Install missing dependencies
pip install -r requirements.txt
pip install transformers huggingface-hub fastmcp aiofiles black
```

### vLLM Connection Issues

```bash
# Check if vLLM server is running
curl http://127.0.0.1:8000/v1/models

# Check vLLM server logs
# Ensure model is loaded correctly
```

### Memory Path Issues

```python
# Verify memory path exists and is writable
from src.agents.mcp.memory.mem_agent_impl.settings import get_memory_path
from pathlib import Path

memory_path = get_memory_path(Path("/path/to/kb"))
print(f"Memory path: {memory_path}")
print(f"Exists: {memory_path.exists()}")
print(f"Writable: {os.access(memory_path, os.W_OK)}")
```

### Sandbox Timeout

```bash
# Increase timeout in settings
export MEM_AGENT_TIMEOUT=30  # Increase to 30 seconds
```

## Future Enhancements

Possible improvements:
1. Support for more model backends (Ollama, LlamaCpp)
2. Asynchronous agent operations
3. Multi-user session management
4. Advanced memory search with embeddings
5. Memory compression and archival
6. Conversation history persistence

## References

- **Original Implementation**: https://github.com/firstbatchxyz/mem-agent-mcp
- **Model**: https://huggingface.co/driaforall/mem-agent
- **Base Model**: Qwen3-4B-Thinking-2507
- **MCP Protocol**: https://modelcontextprotocol.io/
- **FastMCP**: https://github.com/jlowin/fastmcp

## Support

For issues or questions:
1. Check the README: `src/agents/mem_agent/README.md`
2. Run tests: `python3 scripts/test_mem_agent_basic.py`
3. Review examples: `examples/mem_agent_example.py`
4. Check original repo: https://github.com/firstbatchxyz/mem-agent-mcp

---

**Status**: ✅ Implementation Complete

The mem-agent has been successfully integrated into the tg-note project. All core components are in place and ready for use after installing dependencies and downloading the model.
