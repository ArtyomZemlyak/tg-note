# Memory Storage Architecture

This module implements memory storage for autonomous agents using SOLID principles.

> **Note on Terminology:**
> - **Memory Storage** (this module) - Provides storage backends (JSON, Vector) for the MCP Memory tool
> - **MCP Memory Tool** - The agent's note-taking interface (implemented)
> - **mem-agent** - A future LLM-based memory assistant (not yet implemented)
> 
> The naming "mem_agent" in paths is historical; the actual functionality is memory storage.

## Architecture Overview

```
BaseMemoryStorage (Abstract Interface)
    ├── JsonMemoryStorage (Simple JSON-based)
    └── VectorBasedMemoryStorage (AI-powered semantic search)

MemoryStorageFactory (Creates appropriate storage)
MemoryStorage (Legacy wrapper for backward compatibility)
```

## Storage Types

### 1. JsonMemoryStorage
**File:** `json_storage.py`

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
**File:** `vector_storage.py`

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

## Usage

### Using the Factory (Recommended)

```python
from src.mem_agent import MemoryStorageFactory
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
```

### Using Legacy Interface (Backward Compatible)

```python
from src.mem_agent import MemoryStorage
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

Storage type is configured in `config/settings.py`:

```python
MEM_AGENT_STORAGE_TYPE: str = "json"  # or "vector"
MEM_AGENT_MODEL: str = "BAAI/bge-m3"
```

Or via environment variables:

```bash
export MEM_AGENT_STORAGE_TYPE=vector
export MEM_AGENT_MODEL=BAAI/bge-m3
```

## Extending with New Storage Types

Following the Open/Closed Principle, you can add new storage types without modifying existing code:

```python
from src.mem_agent import BaseMemoryStorage, MemoryStorageFactory
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
src/mem_agent/
├── __init__.py           # Public API exports
├── README.md             # This file
├── base.py               # BaseMemoryStorage abstract class
├── json_storage.py       # JSON storage implementation
├── vector_storage.py     # Vector-based storage implementation
├── factory.py            # MemoryStorageFactory
└── storage.py            # Legacy wrapper for backward compatibility
```

## Testing

```python
import pytest
from src.mem_agent import MemoryStorageFactory
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

## License

MIT License - Same as parent project
