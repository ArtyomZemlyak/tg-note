# Memory Storage Architecture Update

## Overview

The memory storage system has been refactored to support multiple storage backends using SOLID principles. This provides flexibility while maintaining backward compatibility.

## What Changed

### New Architecture

```
Before:
  MemoryStorage (JSON only)

After:
  BaseMemoryStorage (Abstract Interface)
    ├── JsonMemoryStorage (JSON-based, default)
    └── VectorBasedMemoryStorage (AI-powered semantic search)
  
  MemoryStorageFactory (Creates appropriate storage)
  MemoryStorage (Legacy wrapper - backward compatible)
```

### New Features

1. **Multiple Storage Types**
   - `json`: Simple JSON storage with substring search (default)
   - `vector`: AI-powered semantic search using HuggingFace embeddings

2. **SOLID Principles**
   - Single Responsibility: Each class has one purpose
   - Open/Closed: Easy to extend with new storage types
   - Liskov Substitution: All storages interchangeable
   - Interface Segregation: Minimal, focused interface
   - Dependency Inversion: Code depends on abstractions

3. **Configuration**
   - New setting: `MEM_AGENT_STORAGE_TYPE` (default: `json`)
   - Existing code works without changes

## Migration Guide

### For Users

**No changes needed!** Your existing code continues to work:

```python
# This still works exactly as before
from src.mem_agent import MemoryStorage
storage = MemoryStorage(data_dir)
```

The system automatically uses JSON storage by default for backward compatibility.

### To Enable Semantic Search

If you want AI-powered semantic search:

1. **Install dependencies:**
   ```bash
   pip install sentence-transformers transformers torch
   ```

2. **Update configuration:**
   ```yaml
   # In config.yaml
   MEM_AGENT_STORAGE_TYPE: vector
   MEM_AGENT_MODEL: BAAI/bge-m3
   ```
   
   Or use environment variables:
   ```bash
   export MEM_AGENT_STORAGE_TYPE=vector
   ```

3. **No code changes needed!** The storage automatically switches.

### For Developers

**New recommended way** (more explicit):

```python
from src.mem_agent import MemoryStorageFactory
from pathlib import Path

# Create JSON storage
storage = MemoryStorageFactory.create(
    storage_type="json",
    data_dir=Path("data/memory")
)

# Create model-based storage
storage = MemoryStorageFactory.create(
    storage_type="vector",
    data_dir=Path("data/memory"),
    model_name="BAAI/bge-m3"
)
```

**Legacy way** (still works):

```python
from src.mem_agent import MemoryStorage

# Auto-selects based on config
storage = MemoryStorage(data_dir)

# Or specify explicitly
storage = MemoryStorage(
    data_dir,
    storage_type="vector",
    model_name="BAAI/bge-m3"
)
```

## Storage Type Comparison

| Feature | JSON Storage | Vector-Based Storage |
|---------|-------------|---------------------|
| **Search** | Substring match | Semantic similarity |
| **Speed** | Very fast | Moderate (first query slower) |
| **Memory** | Minimal (~50 KB) | Higher (~500 MB for model) |
| **Dependencies** | None | transformers, sentence-transformers, torch |
| **Model Download** | Not required | Required (~400 MB) |
| **Setup Time** | Instant | 2-10 seconds (model load) |
| **Best For** | Most use cases | Complex semantic queries |

### Example: Search Difference

**Query:** "security issue"

**JSON Storage** (substring match):
- ✓ Finds: "Found a security issue in login"
- ✗ Misses: "Discovered authentication vulnerability" (no exact words)

**Model-Based Storage** (semantic search):
- ✓ Finds: "Found a security issue in login"
- ✓ Finds: "Discovered authentication vulnerability" (understands meaning)
- ✓ Ranks by relevance

## API Reference

All storage types support the same interface:

```python
# Store a memory
result = storage.store(
    content="Memory content",
    category="category_name",
    tags=["tag1", "tag2"],
    metadata={"key": "value"}
)

# Retrieve/search memories
results = storage.retrieve(
    query="search query",    # Semantic or substring depending on storage type
    category="filter_cat",   # Optional filter
    tags=["filter_tag"],     # Optional filter
    limit=10
)

# List all memories
all_memories = storage.list_all(limit=100)

# List categories
categories = storage.list_categories()

# Delete a memory
storage.delete(memory_id=1)

# Clear memories
storage.clear(category="specific")  # Clear by category
storage.clear()                      # Clear all
```

## Extending with Custom Storage

You can easily add new storage types:

```python
from src.mem_agent import BaseMemoryStorage, MemoryStorageFactory

class RedisMemoryStorage(BaseMemoryStorage):
    """Custom Redis-based storage"""
    
    def __init__(self, data_dir, redis_url):
        super().__init__(data_dir)
        self.redis_url = redis_url
        # ... initialize Redis connection
    
    # Implement abstract methods
    def store(self, content, category="general", metadata=None, tags=None):
        # ... implementation
        pass
    
    # ... other methods

# Register your storage type
MemoryStorageFactory.register_storage_type("redis", RedisMemoryStorage)

# Use it
storage = MemoryStorageFactory.create(
    storage_type="redis",
    data_dir=Path("data"),
    redis_url="redis://localhost:6379"
)
```

## Files

### New Files
- `src/mem_agent/base.py` - Abstract base class
- `src/mem_agent/json_storage.py` - JSON storage implementation
- `src/mem_agent/vector_storage.py` - Vector-based storage implementation
- `src/mem_agent/factory.py` - Storage factory
- `src/mem_agent/README.md` - Developer documentation
- `examples/memory_storage_types_example.py` - Usage examples

### Modified Files
- `src/mem_agent/__init__.py` - Updated exports
- `src/mem_agent/storage.py` - Now a legacy wrapper
- `config/settings.py` - Added `MEM_AGENT_STORAGE_TYPE`
- `config.example.yaml` - Added storage type configuration
- `docs_site/agents/mem-agent-setup.md` - Updated documentation

### Unchanged Files
- `src/agents/mcp/mem_agent_server.py` - Works as before
- `src/agents/mcp/mem_agent_server_http.py` - Works as before
- All existing code using `MemoryStorage` - Works as before

## Testing

Run the examples:

```bash
# Test all storage types
python examples/memory_storage_types_example.py

# Test with existing code
python examples/mcp_memory_agent_example.py
```

## Performance Tips

### JSON Storage
- **Pros:** Instant startup, minimal memory, very fast for small datasets
- **Best for:** < 10,000 memories, simple keyword search
- **No optimization needed**

### Model-Based Storage
- **Pros:** Semantic understanding, better for large datasets
- **First-time cost:** Model download (~400 MB) and load (~5 seconds)
- **Subsequent runs:** Model cached, load time ~2-3 seconds
- **Best for:** > 1,000 memories, complex semantic queries
- **Optimization:** Model is loaded once per process, queries are fast

## Troubleshooting

### "ModuleNotFoundError: No module named 'sentence_transformers'"

You're trying to use model-based storage without dependencies.

**Solution:**
```bash
pip install sentence-transformers transformers torch
```

Or switch to JSON storage:
```yaml
MEM_AGENT_STORAGE_TYPE: json
```

### "Model download failed"

The model couldn't be downloaded from HuggingFace.

**Solutions:**
1. Check internet connection
2. Try a different model: `MEM_AGENT_MODEL: all-MiniLM-L6-v2`
3. Use JSON storage as fallback

### Slow startup with model storage

First run downloads the model (~400 MB). Subsequent runs load from cache (~2-5 seconds).

**Solutions:**
- Pre-download model: `huggingface-cli download BAAI/bge-m3`
- Use JSON storage if speed is critical
- Model is loaded once per process

## FAQ

**Q: Do I need to change my code?**
A: No! Existing code works without changes.

**Q: Which storage type should I use?**
A: Start with JSON (default). Switch to model-based if you need semantic search.

**Q: Can I switch storage types later?**
A: Yes, just update the config. Existing data is preserved (both use same data directory structure).

**Q: Is the BAAI/bge-m3 model required?**
A: Only for model-based storage. JSON storage works without it.

**Q: Can I use a different model?**
A: Yes! Any sentence-transformers compatible model works. Set `MEM_AGENT_MODEL` to your preferred model.

**Q: How do I add a new storage type?**
A: Inherit from `BaseMemoryStorage`, implement abstract methods, register with factory. See "Extending" section above.

## Support

- Documentation: `docs_site/agents/mem-agent-setup.md`
- Developer Docs: `src/mem_agent/README.md`
- Examples: `examples/memory_storage_types_example.py`
- Issues: GitHub Issues

## License

MIT License - Same as parent project
