# Vector Search Refactoring Notes

## Overview

This document describes the refactoring of the vector search functionality into the MCP Hub architecture.

## Changes Made

### 1. Module Relocation

**Before:**
```
src/vector_search/
├── __init__.py
├── manager.py
├── factory.py
├── embeddings.py
├── vector_stores.py
├── chunking.py
└── README.md
```

**After:**
```
src/mcp/vector_search/
├── __init__.py
├── manager.py
├── factory.py
├── embeddings.py
├── vector_stores.py
├── chunking.py
├── vector_search_tool.py  (MCP tools)
└── README.md

src/bot/
└── vector_search_manager.py  (Bot-side manager - unchanged)

src/vector_search/  (Deprecated, kept for backward compatibility)
└── __init__.py  (Re-exports from new location with deprecation warning)
```

### 2. Architecture Clarification

The refactoring clarifies the separation of responsibilities:

#### MCP Hub (`src/mcp/vector_search/`)
- Provides vector search functionality (semantic search)
- Provides vector DB editing functionality (add, delete, update documents)
- Manages vector search configuration and components
- Handles indexing operations when triggered
- Exposes MCP tools: `vector_search`, `reindex_vector`

#### Bot Container (`src/bot/vector_search_manager.py`)
- Monitors knowledge base changes (file operations, git commits)
- Decides when reindexing is needed
- Calls MCP Hub's `reindex_vector` tool
- Manages reindexing schedules and batching
- Tracks file hashes to detect changes

#### Agents
- Use vector search via MCP tools (`vector_search`)
- Do NOT trigger reindexing (bot responsibility)
- Access through `kb_vector_search` MCP tool

### 3. Updated Imports

All imports updated from:
```python
from src.vector_search import VectorSearchManager
```

To:
```python
from src.mcp.vector_search import VectorSearchManager
```

**Files Updated:**
- `src/mcp/mcp_hub_server.py`
- `tests/test_vector_search.py`
- `examples/vector_search_example.py`
- `src/mcp/vector_search/__init__.py`

### 4. Backward Compatibility

The old `src/vector_search/__init__.py` still exists and re-exports from the new location with a deprecation warning. This ensures existing code continues to work while encouraging migration.

```python
# Old code (still works but shows deprecation warning)
from src.vector_search import VectorSearchManager

# New code (recommended)
from src.mcp.vector_search import VectorSearchManager
```

### 5. Documentation Updates

- Updated `src/mcp/vector_search/README.md` with new architecture
- Added deprecation notice to `src/vector_search/README.md`
- Existing architecture docs in `docs_site/` already describe this correctly

## Benefits

1. **Clear Separation of Concerns**
   - MCP Hub: Provides functionality
   - Bot: Manages when to use it
   - Agents: Use via MCP tools

2. **Better Code Organization**
   - Vector search is part of MCP Hub infrastructure
   - Easier to understand ownership and responsibilities

3. **Simplified Testing**
   - MCP Hub can be tested independently
   - Bot manager can be tested with mocked MCP Hub

4. **Scalability**
   - Bot can manage multiple knowledge bases
   - MCP Hub handles all vector operations centrally

## Migration Guide

### For Developers

If you have custom code using the old import:

```python
# Before
from src.vector_search import VectorSearchManager, VectorSearchFactory

# After
from src.mcp.vector_search import VectorSearchManager, VectorSearchFactory
```

### For Users

No changes required! The refactoring is transparent to end users:
- Configuration remains the same
- MCP tools work the same way
- Bot behavior is unchanged

## Testing

Tests updated to use new import paths:
- `tests/test_vector_search.py` ✓
- `examples/vector_search_example.py` ✓
- `examples/vector_search_git_events_example.py` ✓

## Future Improvements

Potential enhancements enabled by this refactoring:

1. **Per-User Vector Stores**
   - Bot can manage separate indices per user
   - MCP Hub provides isolation

2. **Incremental Updates**
   - Bot can send specific file changes
   - MCP Hub can update index incrementally

3. **Distributed Search**
   - Multiple MCP Hub instances
   - Bot coordinates across instances

4. **Advanced Monitoring**
   - Bot tracks reindexing metrics
   - MCP Hub exposes health endpoints

## AICODE-NOTE

This refactoring implements the principle that:
- **MCP HUB** provides tools and functionality
- **BOT** decides when and how to use those tools
- **AGENTS** use tools via standard MCP protocol

This separation makes the system more maintainable, testable, and scalable.
