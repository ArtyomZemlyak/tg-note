# Vector Search MCP Integration

This page describes the architecture for integrating vector search with MCP (Model Context Protocol).

## Overview

Vector search is fully integrated with MCP Hub with a clear split of responsibilities.

### Responsibility split

**MCP Hub (WHAT it does):**
- **Search** — semantic search in the knowledge base
- **CRUD** — add, delete, update documents in the vector DB
- **Full reindex** — when needed

**Bot (WHEN to do it):**
- **Change monitoring** — tracks KB changes
- **Decision making** — decides when to call MCP Hub to update the index
- **Reactivity** — reacts to file change events

### Architecture benefits
1. **Centralized control** — all vector DB operations are done by MCP Hub
2. **No duplication** — bot does not duplicate MCP Hub logic
3. **Incremental updates** — bot calls add/update/delete for specific files
4. **Unified access** — agents use vector search via standard MCP tools

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Bot Container                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  main.py (Startup)                                   │  │
│  │  1. MCP Hub health check                             │  │
│  │  2. Init Vector Search Manager                       │  │
│  │  3. Start change monitoring                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  BotVectorSearchManager                              │  │
│  │  - Checks tool availability via API                  │  │
│  │  - Scans KB files                                    │  │
│  │  - Detects changes (diff)                            │  │
│  │  - Triggers reindex via MCP                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           │ HTTP API                        │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     MCP Hub Container                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MCP Hub Server                                      │  │
│  │  /health - list available tools                      │  │
│  │  /registry/servers - MCP servers                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Vector Search Tools (MCP)                           │  │
│  │  Search:                                             │  │
│  │  - vector_search(query, top_k)                       │  │
│  │                                                      │  │
│  │  CRUD (called by bot):                               │  │
│  │  - add_vector_documents(file_paths)                  │  │
│  │  - delete_vector_documents(file_paths)               │  │
│  │  - update_vector_documents(file_paths)               │  │
│  │  - reindex_vector(force) [full reindex]              │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  VectorSearchManager                                 │  │
│  │  - Embeddings (sentence-transformers/openai)         │  │
│  │  - Vector Store (FAISS/Qdrant)                       │  │
│  │  - Chunking (fixed/semantic)                         │  │
│  │  - Index Management                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ MCP Protocol
┌─────────────────────────────────────────────────────────────┐
│                        Agent                                │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tool Manager                                        │  │
│  │  - kb_vector_search                                  │  │
│  │  - (reindex is bot-only)                             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Bot Container

#### BotVectorSearchManager (`src/bot/vector_search_manager.py`)

**AICODE-NOTE: Bot decides WHEN to update vector search**

Responsibilities (when to act):
- Check vector search availability via MCP Hub `/health`
- Scan KB files to detect changes
- Compute file hashes to track modifications
- Decide when to call MCP Hub to update the index
- Persist/load tracking state (file hashes)

**Does NOT do** (MCP Hub does this):
- Create embeddings
- Manage the vector DB
- Perform indexing/reindexing
- CRUD on documents

Key methods:
- `check_vector_search_availability()` — verifies MCP Hub tools
- `perform_initial_indexing()` — kicks off initial indexing via MCP Hub
- `check_and_reindex_changes()` — **main loop**: detect changes and call MCP Hub
  - New files → `add_vector_documents`
  - Modified files → `update_vector_documents`
  - Deleted files → `delete_vector_documents`
- `start_monitoring()` — background monitoring (every 5 minutes)
- `trigger_reindex()` — manual reindex trigger
- `shutdown()` — graceful shutdown

Important traits:
- **Event-driven:** subscribes to KB file change events (create/modify/delete)
- **Batching:** groups changes within 2 seconds into one operation
- **Concurrency safety:** async lock to prevent concurrent runs
- **Incremental updates:** uses add/update/delete instead of full reindex
- **Graceful stop:** `shutdown()` cancels pending tasks

#### Initialization in main.py

```python
# main.py
if settings.VECTOR_SEARCH_ENABLED:
    from src.bot.vector_search_manager import initialize_vector_search_for_bot

    vector_search_manager = await initialize_vector_search_for_bot(
        mcp_hub_url=mcp_hub_url,
        kb_root_path=settings.KB_PATH,
        start_monitoring=True,
    )
```

### 2. MCP Hub Container

#### MCP Hub Server (`src/mcp/mcp_hub_server.py`)

Provides vector search as MCP tools.

Available tools:

**For agents (search):**
1. **`vector_search`** — semantic search in the KB
   - `query` (string)
   - `top_k` (int, default 5)
   - `user_id` (optional)

**For bot (CRUD):**
2. **`add_vector_documents`** — add documents to the index
   - `file_paths` (list[str]) relative to KB root
   - `user_id` (optional)

3. **`delete_vector_documents`** — remove documents from the index
   - `file_paths` (list[str])
   - `user_id` (optional)

4. **`update_vector_documents`** — update documents in the index
   - `file_paths` (list[str])
   - `user_id` (optional)

5. **`reindex_vector`** — full reindex (fallback)
   - `force` (bool, default false)
   - `user_id` (optional)

Availability check:

```python
def check_vector_search_availability() -> bool:
    """Checks configuration and dependencies"""
    # 1. VECTOR_SEARCH_ENABLED
    # 2. Embedding provider dependencies
    # 3. Vector store backend
    return available
```

Initialization:

```python
async def get_vector_search_manager() -> Optional[VectorSearchManager]:
    """Create and initialize VectorSearchManager"""
    manager = VectorSearchFactory.create_from_settings(...)
    await manager.initialize()  # load existing index
    return manager
```

#### VectorSearchManager (`src/mcp/vector_search/manager.py`)

**AICODE-NOTE: MCP Hub owns WHAT operations are provided**

Core manager that exposes vector search functionality.

Components:
- **Embedder** — builds embeddings (sentence-transformers/openai/infinity)
- **VectorStore** — stores vectors (FAISS/Qdrant)
- **Chunker** — splits documents into chunks
- **Index Metadata** — tracks indexed files and hashes

Key methods:

**Search:**
- `search(query, top_k)` — semantic search

**Indexing:**
- `add_documents(documents)` — add/update documents (caller provides content)
- `delete_documents(document_ids)` — delete documents
- `update_documents(documents)` — delete + add
- `initialize()` — load existing index
- `clear_index()` — drop index

**Metadata management:**
- `get_stats()` — index stats
- `_save_metadata()` / `_load_metadata()` — persist metadata and content hashes

**Incremental indexing:**
- Stores document content hashes in `metadata.json` under `.vector_index/`
- Compares hashes to detect changes
- Indexes only new/changed documents
- Triggers full reindex if configuration changes (embedder/chunker/vector store)

**Handling deletions:**
- **Qdrant:** deletes by `document_id` filter via `delete_by_filter`
- **FAISS:** delete not supported; `delete_documents` returns an error → full reindex required
- **Metadata:** updated only after successful ops

### 3. Agent

#### Tool Registry (`src/agents/tools/registry.py`)

Registers MCP vector-search tools:

```python
if enable_vector_search:
    from ..mcp.vector_search import vector_search_tool

    for tool in vector_search_tool.ALL_TOOLS:
        tool.enable()
    manager.register_many(vector_search_tool.ALL_TOOLS)
```

#### Agent Factory (`src/agents/agent_factory.py`)

Passes the vector-search flag from settings:

```python
config = {
    ...
    "enable_vector_search": settings.VECTOR_SEARCH_ENABLED,
    ...
}

agent = AutonomousAgent(
    ...
    enable_vector_search=config.get("enable_vector_search", False),
    ...
)
```

## Execution flow

### Startup sequence

1. **Bot container startup**
   ```
   1. main.py starts
   2. MCP Hub server starts
   3. Wait for MCP Hub health check
   4. Check vector search availability
   5. Initialize BotVectorSearchManager
   6. Scan knowledge bases
   7. Start background monitoring
   ```

2. **MCP Hub initialization**
   ```
   1. mcp_hub_server.py starts
   2. Check VECTOR_SEARCH_ENABLED
   3. Check dependencies
   4. Register vector-search tools
   5. /health returns available tools
   ```

### Agent vector-search flow

1. **Agent calls `kb_vector_search`**
   ```
   Agent → ToolManager → VectorSearchMCPTool → MCP Client → MCP Hub
   ```

2. **MCP Hub processes request**
   ```
   MCP Hub → vector_search tool → VectorSearchManager → Embedder/VectorStore
   ```

3. **Results returned**
   ```
   Results → MCP Hub → MCP Client → VectorSearchMCPTool → Agent
   ```

### Change detection and incremental updates

**AICODE-NOTE: New architecture — Bot decides WHEN, MCP Hub does WHAT**

1. **Event-based monitoring (primary, in bot)**
   ```
   KB event (create/modify/delete)
   → BotVectorSearchManager._handle_kb_change_event()
   → Batch changes (2 seconds)
   → check_and_reindex_changes()
   → Scan files and build document payloads
   → Compute hashes
   → Compare with previous hashes
   → Detect added / modified / deleted
   → Call corresponding MCP Hub operations:
      - Added → add_vector_documents (documents payload)
      - Modified → update_vector_documents (documents payload)
      - Deleted → delete_vector_documents (document IDs)
   ```

2. **Background monitoring (fallback, every 5 minutes — bot)**
   ```
   BotVectorSearchManager.start_monitoring()
   → Periodic change check
   → Covers cases not caught by events (NFS, external changes)
   ```

3. **CRUD handling in MCP Hub**
   ```
   MCP Hub receives a bot request:

   add_vector_documents(documents):
   → VectorSearchManager.add_documents()

   delete_vector_documents(document_ids):
   → VectorSearchManager.delete_documents()

   update_vector_documents(documents):
   → VectorSearchManager.update_documents()
   ```

4. **Benefits of incremental updates:**
   - Faster than full reindex (only changed files)
   - Less load on embedder
   - Lower memory usage
   - Better responsiveness

## Configuration

### Environment variables

```bash
# Vector Search Enable
VECTOR_SEARCH_ENABLED=true

# Embedding Provider
VECTOR_EMBEDDING_PROVIDER=sentence_transformers
VECTOR_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Vector Store
VECTOR_STORE_PROVIDER=faiss

# Chunking
VECTOR_CHUNKING_STRATEGY=fixed_size_overlap
VECTOR_CHUNK_SIZE=512
VECTOR_CHUNK_OVERLAP=50

# Search
VECTOR_SEARCH_TOP_K=5
```

### config.yaml

```yaml
# Vector Search Configuration
vector_search:
  enabled: true

  # Embedding configuration
  embedding:
    provider: sentence_transformers  # sentence_transformers, openai, infinity
    model: all-MiniLM-L6-v2

  # Vector store configuration
  vector_store:
    provider: faiss  # faiss, qdrant

  # Chunking configuration
  chunking:
    strategy: fixed_size_overlap  # fixed_size, fixed_size_overlap, semantic
    chunk_size: 512
    chunk_overlap: 50
    respect_headers: true

  # Search configuration
  search:
    top_k: 5
```

## Dependencies

### Required
- `loguru` — logging
- `aiohttp` — HTTP client for bot ↔ MCP Hub
- `pathlib` — path handling

### Optional (vector search)
- `sentence-transformers` — for sentence_transformers provider
- `faiss-cpu` — for FAISS vector store
- `qdrant-client` — for Qdrant vector store
- `openai` — for OpenAI embeddings

## Monitoring and logging

### Bot Container
```
🔍 Checking vector search availability at http://mcp-hub:8765/health
✅ Vector search tools are available: vector_search
🔄 Starting initial knowledge base indexing...
📊 Scanned 150 markdown files
👁️ Starting KB change monitoring (checking every 300s)...
📝 Detected changes: KBChange(added=2, modified=3, deleted=1)
🔄 Triggering reindexing due to changes...
✅ Change detection completed, hashes updated
```

### MCP Hub
```
🛠️ Starting MCP Hub server...
✅ Vector search enabled: True
✅ Embedding provider: sentence_transformers (all-MiniLM-L6-v2)
✅ Vector store: faiss
✅ Chunking: fixed_size_overlap (size=512, overlap=50)
✅ Registered tools: vector_search, add_vector_documents, delete_vector_documents, update_vector_documents, reindex_vector
✅ MCP Hub health: OK
```

## AICODE-NOTE
- Bot = decision-maker (WHEN)
- MCP Hub = executor (WHAT)
- Agent = consumer (uses tools)

This split keeps vector search centralized, avoids duplication, and allows incremental updates driven by bot-detected changes.
