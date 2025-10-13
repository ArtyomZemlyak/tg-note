# Mem-Agent Integration Guide

This document describes how the mem-agent was integrated into the memory storage architecture.

## Overview

The mem-agent is a complete LLM-based agent system for managing Obsidian-style memory files. It was integrated into our SOLID-based memory architecture with minimal changes to the original code.

## Integration Principles

1. **Minimal Changes to Original Code**
   - Only import paths were updated
   - Original agent logic remains intact
   - System prompt and tools unchanged

2. **SOLID Architecture**
   - Adapter pattern for interface compatibility
   - Factory pattern for creation
   - Open/Closed principle for extensibility

3. **Separation of Concerns**
   - Storage abstraction (MemAgentStorage)
   - LLM operations (Original Agent)
   - File operations (Original tools)

## File Structure

### Original mem-agent (preserved)

```
src/agents/mcp/memory/mem_agent_impl/
├── agent.py              # Main agent with chat() method
├── engine.py             # Sandboxed Python execution
├── model.py              # LLM client (vLLM/OpenRouter)
├── tools.py              # File operations
├── schemas.py            # Data models
├── settings.py           # Configuration
├── utils.py              # Helpers
├── system_prompt.txt     # Agent prompt
└── README.md             # Original documentation
```

### Integration layer (new)

```
src/agents/mcp/memory/
├── memory_mem_agent_storage.py    # Adapter implementing BaseMemoryStorage
├── memory_mem_agent_tools.py      # Direct chat tools
└── memory_factory.py               # Factory with mem-agent registration
```

## How It Works

### Storage Interface (Recommended)

```python
# 1. Factory creates MemAgentStorage
storage = MemoryStorageFactory.create(
    storage_type="mem-agent",
    data_dir=Path("data/memory"),
    model="driaforall/mem-agent"
)

# 2. MemAgentStorage wraps Agent
#    - Implements BaseMemoryStorage interface
#    - Converts method calls to natural language
#    - Calls agent.chat() internally

# 3. Agent processes the request
#    - LLM generates thoughts and code
#    - Code executes in sandbox
#    - Response returned
```

### Data Flow

```
User Code
    ↓
storage.store("Important info")
    ↓
MemAgentStorage.store()
    ↓
Converts to natural language:
"Please save the following information to memory: Important info"
    ↓
agent.chat(message)
    ↓
LLM processes request
    ↓
Generates Python code:
create_file("user.md", content)
    ↓
Sandboxed execution
    ↓
Response returned
```

## Configuration

### Environment Variables

```bash
# Enable mem-agent storage
export MEM_AGENT_STORAGE_TYPE=mem-agent
export MEM_AGENT_MODEL=driaforall/mem-agent

# Backend configuration (auto, vllm, mlx, or transformers)
export MEM_AGENT_BACKEND=auto

# vLLM configuration (when backend is vllm)
export MEM_AGENT_VLLM_HOST=127.0.0.1
export MEM_AGENT_VLLM_PORT=8001

# Or use OpenRouter (when backend is auto/transformers without local server)
export OPENROUTER_API_KEY=your-key
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### Programmatic Configuration

```python
storage = MemoryStorageFactory.create(
    storage_type="mem-agent",
    data_dir=Path("data/memory"),
    model="driaforall/mem-agent",
    use_vllm=True,
    max_tool_turns=20
)
```

## Key Design Decisions

### 1. Adapter Pattern

**Why:** The mem-agent has a `chat()` method that takes natural language, while `BaseMemoryStorage` has structured methods like `store()` and `retrieve()`.

**Solution:** `MemAgentStorage` acts as an adapter:

- Implements `BaseMemoryStorage` interface
- Converts structured calls to natural language
- Wraps the original `Agent`

### 2. Preserved Original Code

**Why:** The mem-agent is a complex system with LLM, tools, and prompts working together.

**Solution:**

- Moved to `mem_agent_impl/` directory
- Updated only import paths
- Original logic untouched

### 3. Factory Registration

**Why:** Need to create mem-agent storage alongside json/vector.

**Solution:**

- Added "mem-agent" to `MemoryStorageFactory.STORAGE_TYPES`
- Factory handles creation with appropriate parameters
- Follows Open/Closed Principle

### 4. MCP Server Integration

**Why:** Memory server needs to support all storage types.

**Solution:**

- `memory_server.py` uses factory to create storage
- Reads `MEM_AGENT_STORAGE_TYPE` env var
- Falls back to JSON if mem-agent fails

## Testing

### Basic Test

```python
from pathlib import Path
from src.agents.mcp.memory import MemoryStorageFactory

# Create storage
storage = MemoryStorageFactory.create(
    storage_type="mem-agent",
    data_dir=Path("/tmp/test_memory"),
    model="driaforall/mem-agent",
    use_vllm=False  # Use OpenRouter for testing
)

# Store
result = storage.store("Test information")
assert result["success"]

# Retrieve
results = storage.retrieve(query="Test")
assert results["success"]
```

### With vLLM

```bash
# Start vLLM server
python -m vllm.entrypoints.openai.api_server \
    --model driaforall/mem-agent \
    --host 127.0.0.1 \
    --port 8000

# Run test with vLLM
python -c "
from pathlib import Path
from src.agents.mcp.memory import MemoryStorageFactory

storage = MemoryStorageFactory.create(
    storage_type='mem-agent',
    data_dir=Path('/tmp/test_memory'),
    use_vllm=True
)

result = storage.store('Test with vLLM')
print(result)
"
```

## Migration Guide

### From JSON to mem-agent

```python
# Old (JSON storage)
storage = MemoryStorage(Path("data/memory"))
storage.store("Info", category="notes")

# New (mem-agent storage)
storage = MemoryStorageFactory.create(
    storage_type="mem-agent",
    data_dir=Path("data/memory")
)
storage.store("Info", category="notes")  # Same interface!
```

### Using Both

```python
# JSON for simple data
json_storage = MemoryStorageFactory.create(
    storage_type="json",
    data_dir=Path("data/memory/json")
)

# Mem-agent for complex operations
agent_storage = MemoryStorageFactory.create(
    storage_type="mem-agent",
    data_dir=Path("data/memory/agent")
)

# Use whichever fits your needs
json_storage.store("Quick note")
agent_storage.store("Complex information requiring organization")
```

## Troubleshooting

### Import Errors

```python
# If you see: "mem-agent components not available"
# Install dependencies:
pip install fastmcp transformers openai
```

### vLLM Issues

```bash
# Check if vLLM server is running
curl http://127.0.0.1:8000/v1/models

# Check environment variables
echo $VLLM_HOST
echo $VLLM_PORT
```

### Memory Path Issues

```python
# Ensure memory path exists and is writable
from pathlib import Path
memory_path = Path("data/memory")
memory_path.mkdir(parents=True, exist_ok=True)
```

## Future Enhancements

1. **Caching**: Cache agent instances per memory path
2. **Streaming**: Support streaming responses from LLM
3. **Batch Operations**: Process multiple operations efficiently
4. **Advanced Parsing**: Parse agent responses into structured data
5. **Custom Prompts**: Allow custom system prompts per use case

## References

- Original mem-agent: `src/agents/mcp/memory/mem_agent_impl/README.md`
- Memory architecture: `src/agents/mcp/memory/README.md`
- Base interface: `src/agents/mcp/memory/memory_base.py`
- Adapter implementation: `src/agents/mcp/memory/memory_mem_agent_storage.py`
