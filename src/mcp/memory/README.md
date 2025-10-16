# Memory Storage Architecture

This module implements memory storage for autonomous agents using SOLID principles.

> **Note on Terminology:**
>
> - **Memory Storage** (this module) - Provides storage backends (JSON, Vector) for the MCP Memory tool
> - **MCP Memory Tool** - The agent's note-taking interface (implemented)
>
> The module provides the storage backend for MCP Memory tool.

## Architecture Overview

```
BaseMemoryStorage (Abstract Interface)
    ├── JsonMemoryStorage (Simple JSON-based)
    ├── VectorBasedMemoryStorage (AI-powered semantic search)
    └── MemAgentStorage (LLM-based intelligent memory with Obsidian-style markdown)

MemoryStorageFactory (Creates appropriate storage)
MemoryStorage (Legacy wrapper for backward compatibility)
```

## Storage Types

### 1. JsonMemoryStorage

**File:** `memory_json_storage.py`

- Simple JSON file storage
- Substring-based search
- Fast and lightweight
- No ML dependencies
- Default storage type

**Best for:**

- Most use cases
- Simple keyword search
- Resource-constrained environments

### 2. VectorBasedMemoryStorage

**File:** `memory_vector_storage.py`

- AI-powered semantic search
- Uses embeddings from HuggingFace models
- Cosine similarity for relevance
- Fallback to JSON for persistence

**Best for:**

- Large memory collections
- Complex semantic queries
- When understanding context matters

**Requires:**

- `sentence-transformers`
- `transformers`
- `torch` or `numpy`

### 3. MemAgentStorage

**File:** `memory_mem_agent_storage.py`

- LLM-based intelligent memory management
- Obsidian-style markdown files with wiki-links
- Sandboxed Python code execution
- Natural language interface for memory operations
- Intelligent information organization

**Best for:**

- Complex memory scenarios requiring reasoning
- Natural language memory interactions
- Intelligent information organization and linking
- When you need the agent to "think" about memory operations

**Requires:**

- `fastmcp`
- `transformers`
- `openai` (for OpenRouter) or vLLM setup
- Model: `driaforall/mem-agent` or compatible

**Architecture:**
The mem-agent is a complete LLM-based agent system that:

- Uses its own LLM to reason about memory operations
- Executes sandboxed Python code to manipulate files
- Maintains Obsidian-style markdown with wiki-links
- Provides structured memory (user.md, entities/*.md)

**Important:** This is a wrapper around the original mem-agent implementation,
maintaining minimal changes to the original code following SOLID principles.

## Usage

### Using the Factory (Recommended)

```python
from src.agents.mcp.memory import MemoryStorageFactory
from pathlib import Path

# Create JSON storage
storage = MemoryStorageFactory.create(
    storage_type="json",
    data_dir=Path("data/memory")
)

# Create vector-based storage
storage = MemoryStorageFactory.create(
    storage_type="vector",
    data_dir=Path("data/memory"),
    model_name="BAAI/bge-m3"
)

# Create mem-agent storage (LLM-based)
storage = MemoryStorageFactory.create(
    storage_type="mem-agent",
    data_dir=Path("data/memory"),
    model="driaforall/mem-agent",
    use_vllm=True,
    max_tool_turns=20
)
```

### Using Legacy Interface (Backward Compatible)

```python
from src.agents.mcp.memory import MemoryStorage
from pathlib import Path

# Automatically selects storage type from config
storage = MemoryStorage(Path("data/memory"))

# Or specify explicitly
storage = MemoryStorage(
    Path("data/memory"),
    storage_type="vector",
    model_name="BAAI/bge-m3"
)
```

### Basic Operations

All storage types support the same interface:

```python
# Store a memory
result = storage.store(
    content="Important information",
    category="notes",
    tags=["important", "research"],
    metadata={"source": "meeting"}
)

# Search/retrieve memories
results = storage.retrieve(
    query="information",  # Semantic search with model, substring with JSON
    category="notes",      # Optional filter
    tags=["important"],    # Optional filter
    limit=5
)

# List all memories
all_memories = storage.list_all(limit=100)

# List categories
categories = storage.list_categories()

# Delete a memory
storage.delete(memory_id=1)

# Clear all or by category
storage.clear(category="notes")  # Clear specific category
storage.clear()                   # Clear all
```

## Configuration

Storage type is configured in `config/settings.py` or via environment variables:

```bash
# Storage type: "json" (default), "vector", or "mem-agent"
export MEM_AGENT_STORAGE_TYPE=json

# For vector storage
export MEM_AGENT_MODEL=BAAI/bge-m3

# For mem-agent storage
export MEM_AGENT_STORAGE_TYPE=mem-agent
export MEM_AGENT_MODEL=driaforall/mem-agent
export MEM_AGENT_BACKEND=vllm  # Options: auto, vllm, mlx, transformers
export MEM_AGENT_MAX_TOOL_TURNS=20

# OpenAI-compatible endpoint configuration
# Recommended: configure in config.yaml
# Or use environment variables:
export MEM_AGENT_BASE_URL=http://127.0.0.1:8001/v1
export MEM_AGENT_OPENAI_API_KEY=lm-studio
```

## Extending with New Storage Types

Following the Open/Closed Principle, you can add new storage types without modifying existing code:

```python
from src.agents.mcp.memory import BaseMemoryStorage, MemoryStorageFactory
from pathlib import Path
from typing import Any, Dict, List, Optional

class DatabaseMemoryStorage(BaseMemoryStorage):
    """Custom storage using database"""

    def __init__(self, data_dir: Path, db_url: str):
        super().__init__(data_dir)
        self.db_url = db_url
        # ... initialize database connection

    def store(self, content: str, category: str = "general",
              metadata: Optional[Dict] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        # ... implement storage logic
        pass

    # ... implement other abstract methods

# Register the new storage type
MemoryStorageFactory.register_storage_type("database", DatabaseMemoryStorage)

# Now you can use it
storage = MemoryStorageFactory.create(
    storage_type="database",
    data_dir=Path("data/memory"),
    db_url="postgresql://..."
)
```

## SOLID Principles Applied

1. **Single Responsibility Principle (SRP)**
   - Each storage class handles only its storage mechanism
   - Factory only handles creation logic
   - Base class only defines interface

2. **Open/Closed Principle (OCP)**
   - New storage types can be added via factory registration
   - No modification of existing code needed

3. **Liskov Substitution Principle (LSP)**
   - All storage implementations can be used interchangeably
   - Same interface contract guaranteed

4. **Interface Segregation Principle (ISP)**
   - Minimal interface with only necessary methods
   - No client forced to depend on unused methods

5. **Dependency Inversion Principle (DIP)**
   - Clients depend on BaseMemoryStorage abstraction
   - Not on concrete implementations

## Files Structure

```
src/agents/mcp/memory/
├── __init__.py                      # Public API exports
├── README.md                        # This file
├── memory_base.py                   # BaseMemoryStorage abstract class
├── memory_json_storage.py           # JSON storage implementation
├── memory_vector_storage.py         # Vector-based storage implementation
├── memory_mem_agent_storage.py      # Mem-agent storage implementation (LLM-based)
├── memory_factory.py                # MemoryStorageFactory
├── memory_storage.py                # Legacy wrapper for backward compatibility
├── memory_server.py                 # MCP server (stdio transport)
├── memory_server_http.py            # MCP server (HTTP/SSE transport)
├── memory_tool.py                   # MCP tool for agent integration
├── memory_mem_agent_tools.py        # Direct mem-agent tools (chat, query)
└── mem_agent_impl/                  # Mem-agent implementation
    ├── __init__.py
    ├── agent.py                     # Main agent class
    ├── engine.py                    # Sandboxed code execution
    ├── model.py                     # LLM interface (vLLM/OpenRouter)
    ├── tools.py                     # File/directory operations
    ├── schemas.py                   # Data models
    ├── settings.py                  # Configuration
    ├── utils.py                     # Utility functions
    ├── system_prompt.txt            # Agent system prompt
    ├── mcp_server.py                # Standalone MCP server (deprecated, use memory_server.py)
    └── README.md                    # Mem-agent documentation
```

## Testing

```python
import pytest
from src.agents.mcp.memory import MemoryStorageFactory
from pathlib import Path
from tempfile import TemporaryDirectory

def test_json_storage():
    with TemporaryDirectory() as tmpdir:
        storage = MemoryStorageFactory.create("json", Path(tmpdir))

        # Store
        result = storage.store("Test content", category="test")
        assert result["success"]

        # Retrieve
        results = storage.retrieve(query="Test")
        assert results["count"] > 0
        assert "Test content" in results["memories"][0]["content"]

def test_vector_storage():
    with TemporaryDirectory() as tmpdir:
        storage = MemoryStorageFactory.create(
            "vector",
            Path(tmpdir),
            model_name="all-MiniLM-L6-v2"  # Small model for testing
        )

        # Store
        storage.store("The cat sat on the mat", category="test")
        storage.store("A feline rested on the carpet", category="test")

        # Semantic search
        results = storage.retrieve(query="animal on rug", limit=2)
        assert results["count"] == 2
        # Both should be found due to semantic similarity
```

## Performance Considerations

### JSON Storage

- **Memory**: ~10-50 KB per 1000 memories
- **Search**: O(n) substring search
- **Startup**: Instant
- **Scalability**: Good up to ~10,000 memories

### Vector-Based Storage

- **Memory**: ~200-500 MB (model) + ~100 KB per 1000 memories (embeddings)
- **Search**: O(n) cosine similarity (can be optimized with FAISS)
- **Startup**: 2-10 seconds (model loading)
- **Scalability**: Good up to ~100,000 memories

## Future Enhancements

Possible improvements following SOLID principles:

1. **Vector Database Storage** (Pinecone, Weaviate, Qdrant)
   - Register new storage type via factory
   - No changes to existing code

2. **Hybrid Storage** (JSON + Vector DB)
   - Implements BaseMemoryStorage
   - Combines benefits of both

3. **Caching Layer**
   - Decorator pattern over existing storage
   - Transparent to clients

4. **Distributed Storage** (Redis, Cassandra)
   - New implementation of BaseMemoryStorage
   - Same interface, different backend

## Mem-Agent Integration

The mem-agent is integrated following SOLID principles with minimal changes to the original code:

### Integration Architecture

1. **MemAgentStorage** (`memory_mem_agent_storage.py`)
   - Adapter class implementing `BaseMemoryStorage` interface
   - Wraps the original `Agent` class from `mem_agent_impl`
   - Converts structured method calls to natural language instructions
   - Follows Adapter pattern to maintain compatibility

2. **Original mem-agent** (`mem_agent_impl/`)
   - Complete LLM-based agent system
   - Minimal modifications (only import path updates)
   - Maintains its own:
     - LLM client (vLLM/OpenRouter)
     - Sandboxed execution engine
     - File operation tools
     - System prompt

3. **Factory Registration**
   - Registered as "mem-agent" storage type in `MemoryStorageFactory`
   - Can be created alongside json/vector storage types
   - Follows Open/Closed Principle

### Usage Patterns

#### Via Storage Interface (Recommended)

```python
from src.agents.mcp.memory import MemoryStorageFactory
from pathlib import Path

# Create mem-agent storage
storage = MemoryStorageFactory.create(
    storage_type="mem-agent",
    data_dir=Path("data/memory"),
    model="driaforall/mem-agent",
    use_vllm=True
)

# Use standard storage interface
result = storage.store(
    content="Important project information",
    category="project",
    tags=["important"]
)

results = storage.retrieve(query="project information")
```

#### Via Direct Chat Tools

```python
from src.agents.mcp.memory.memory_mem_agent_tools import ChatWithMemoryTool

# Direct conversation with mem-agent
tool = ChatWithMemoryTool()
response = await tool.execute(
    {"message": "Remember that I prefer Python for backend development"},
    context
)
```

#### Via MCP Server

Set environment variable and use memory_server.py:

```bash
export MEM_AGENT_STORAGE_TYPE=mem-agent
export MEM_AGENT_MODEL=driaforall/mem-agent
python -m src.agents.mcp.memory.memory_server
```

### Benefits of This Integration

1. **SOLID Compliance**
   - Follows all SOLID principles
   - Minimal changes to original mem-agent code
   - Easy to maintain and extend

2. **Flexibility**
   - Can use mem-agent via standard storage interface
   - Can chat directly with agent when needed
   - Can switch between storage types easily

3. **Backward Compatibility**
   - Existing code continues to work
   - New mem-agent features available optionally
   - Legacy storage types still supported

4. **Separation of Concerns**
   - Storage abstraction handled by adapter
   - LLM operations handled by original agent
   - Each component has single responsibility

## License

MIT License - Same as parent project
