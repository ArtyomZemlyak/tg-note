# Memory Agent (mem-agent)

An LLM-based agent for interacting with Obsidian-like memory systems. The mem-agent can read, write, and manage structured markdown-based memory to maintain persistent knowledge across conversations.

## Overview

The mem-agent is based on the [driaforall/mem-agent](https://huggingface.co/driaforall/mem-agent) model and provides:

- **Structured Memory**: Obsidian-style markdown files with wiki-links
- **Sandboxed Execution**: Safe Python code execution for memory operations
- **MCP Integration**: Exposed as MCP tools for use by other agents
- **Flexible Backends**: Support for vLLM, MLX, and transformers

## Architecture

### Core Components

1. **Agent** (`agent.py`): Main agent class that handles chat and memory operations
2. **Engine** (`engine.py`): Sandboxed code execution environment
3. **Model** (`model.py`): Model interface supporting vLLM and OpenRouter
4. **Tools** (`tools.py`): File and directory operations for memory management
5. **MCP Server** (`mcp_server.py`): MCP protocol interface for tool integration

### Memory Structure

```
memory/
├── user.md              # User information and relationships
└── entities/            # Entity files
    ├── person_name.md
    ├── company_name.md
    └── location_name.md
```

Each memory file uses markdown with:

- YAML-style attributes (`- key: value`)
- Wiki-links for relationships (`[[entities/name.md]]`)
- Standard markdown formatting

## Usage

### Standalone Usage

```python
from src.agents.mcp.memory.mem_agent_impl import Agent

# Create agent
agent = Agent(
    memory_path="/path/to/memory",
    use_vllm=True,  # Use vLLM backend
    model="driaforall/mem-agent"
)

# Chat with agent
response = agent.chat("Remember that I work at Acme Corp as a senior engineer")
print(response.reply)

# Query memory
response = agent.chat("Where do I work?")
print(response.reply)
```

### MCP Server Usage

Start the MCP server:

```bash
python -m src.agents.mcp.memory.mem_agent_impl.mcp_server --host 127.0.0.1 --port 8766
```

Or use it in your code:

```python
from src.agents.mcp.memory.mem_agent_impl.mcp_server import run_server

run_server(host="127.0.0.1", port=8766)
```

### MCP Tools

The mem-agent exposes four MCP tools:

1. **chat_with_memory**: Full bidirectional interaction (read/write)
2. **query_memory**: Read-only information retrieval
3. **save_to_memory**: Explicit information storage
4. **list_memory_structure**: View current memory organization

## Configuration

The mem-agent integrates with the main application settings:

```yaml
# config.yaml
MEM_AGENT_MAX_TOOL_TURNS: 20
MEM_AGENT_TIMEOUT: 20
MEM_AGENT_FILE_SIZE_LIMIT: 1048576  # 1MB
MEM_AGENT_DIR_SIZE_LIMIT: 10485760  # 10MB
MEM_AGENT_MEMORY_SIZE_LIMIT: 104857600  # 100MB
# OpenAI-compatible endpoint (configure in config.yaml)
MEM_AGENT_BASE_URL: http://127.0.0.1:8001/v1
MEM_AGENT_OPENAI_API_KEY: lm-studio
```

Or use environment variables (they override config.yaml):

```bash
export MEM_AGENT_MAX_TOOL_TURNS=20
export MEM_AGENT_TIMEOUT=20
export MEM_AGENT_BASE_URL=http://127.0.0.1:8001/v1
export MEM_AGENT_OPENAI_API_KEY=lm-studio
```

## Model Backends

### vLLM (Recommended for Linux)

```bash
# Install vLLM
pip install vllm>=0.5.5

# Start vLLM server
python -m vllm.entrypoints.openai.api_server \
    --model driaforall/mem-agent \
    --host 127.0.0.1 \
    --port 8000
```

### MLX (Recommended for macOS)

```bash
# Install MLX
pip install mlx mlx-lm

# Use MLX in code
agent = Agent(
    use_vllm=False,
    model="driaforall/mem-agent"
)
```

### OpenRouter (Cloud)

```bash
# Set API key
export OPENAI_API_KEY=your-openrouter-key
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Agent will use OpenRouter automatically if vLLM is not available
```

## Agent Response Format

The agent uses structured XML tags in responses:

```xml
<think>
Reasoning about what memory operations are needed...
</think>

<python>
# Python code for memory operations
content = read_file("user.md")
</python>

<reply>
Final response to the user
</reply>
```

The code in `<python>` blocks is executed in a sandboxed environment with access to memory tools.

## Memory Tools API

Available functions in sandboxed Python environment:

### File Operations

- `create_file(file_path: str, content: str = "") -> bool`
- `update_file(file_path: str, old_content: str, new_content: str) -> Union[bool, str]`
- `read_file(file_path: str) -> str`
- `delete_file(file_path: str) -> bool`
- `check_if_file_exists(file_path: str) -> bool`

### Directory Operations

- `create_dir(dir_path: str) -> bool`
- `list_files() -> str`
- `check_if_dir_exists(dir_path: str) -> bool`

### Utilities

- `get_size(file_or_dir_path: str) -> int`
- `go_to_link(link_string: str) -> str`

## Installation

Install mem-agent dependencies:

```bash
# Core dependencies
pip install transformers huggingface-hub fastmcp aiofiles pydantic python-dotenv jinja2 black

# For Linux (vLLM)
pip install vllm>=0.5.5

# For macOS (MLX)
pip install mlx mlx-lm
```

Or use the installation script:

```bash
python scripts/install_mem_agent.py
```

## Security

The sandboxed execution environment provides:

- **Path Restriction**: File operations limited to allowed memory path
- **Timeout Protection**: Code execution limited to configurable timeout
- **Size Limits**: File, directory, and total memory size restrictions
- **Function Blacklisting**: Dangerous operations can be disabled

## Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

View agent thoughts and Python code:

```python
response = agent.chat("What is my name?")
print("Thoughts:", response.thoughts)
print("Python:", response.python_block)
print("Reply:", response.reply)
```

## References

- **Model**: [driaforall/mem-agent on Hugging Face](https://huggingface.co/driaforall/mem-agent)
- **Original Implementation**: [firstbatchxyz/mem-agent-mcp](https://github.com/firstbatchxyz/mem-agent-mcp)
- **Training Method**: GSPO (Zheng et al., 2025)
- **Base Model**: Qwen3-4B-Thinking-2507

## License

This implementation is based on the open-source mem-agent project. See LICENSE for details.
