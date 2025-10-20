# Vector Search Module

Flexible vector search capabilities for the knowledge base with support for multiple embedding models and vector stores.

## Features

### Knowledge Base Isolation

- **Per-KB Collections**: Each knowledge base gets its own Qdrant collection
- **Separate Metadata**: Metadata stored in isolated directories
- **Document Filtering**: Documents include `kb_id` for proper isolation
- **Scalable**: Support for unlimited knowledge bases

### Embedding Models

- **sentence-transformers**: Local embeddings (recommended)
  - No API calls required
  - Runs on CPU or GPU
  - Free and private
- **OpenAI API**: High-quality cloud embeddings
  - Requires API key
  - Paid service
- **Infinity API**: Self-hosted or remote embeddings
  - Open-source alternative
  - Flexible deployment
  - Dimension is determined dynamically at runtime

### Vector Stores

- **FAISS**: Fast local vector search (recommended)
  - Optimized similarity search
  - No external services
  - CPU or GPU support
- **Qdrant**: Production-ready vector database
  - Scalable and distributed
  - Can be local or remote
  - Advanced filtering

### Document Chunking

- **Fixed size**: Simple fixed-size chunks
- **Fixed size with overlap**: Chunks with overlap for better context
- **Semantic**: Respects markdown structure (headers, paragraphs)

## Installation

### Basic Installation

```bash
# Install optional dependencies
pip install -e '.[vector-search]'
```

### Individual Components

```bash
# For local embeddings
pip install sentence-transformers

# For FAISS vector store
pip install faiss-cpu  # or faiss-gpu for GPU support

# For Qdrant vector store
pip install qdrant-client
```

## Configuration

Edit `config.yaml` to enable and configure vector search:

```yaml
# Enable vector search
VECTOR_SEARCH_ENABLED: true

# Embedding configuration
VECTOR_EMBEDDING_PROVIDER: "sentence_transformers"  # or "openai", "infinity"
VECTOR_EMBEDDING_MODEL: "all-MiniLM-L6-v2"

# Vector store configuration
VECTOR_STORE_PROVIDER: "faiss"  # or "qdrant"

# Chunking configuration
VECTOR_CHUNKING_STRATEGY: "fixed_size_overlap"  # or "fixed_size", "semantic"
VECTOR_CHUNK_SIZE: 512
VECTOR_CHUNK_OVERLAP: 50
VECTOR_RESPECT_HEADERS: true

# Search settings
VECTOR_SEARCH_TOP_K: 5
```

## Usage

### Basic Usage

```python
from pathlib import Path
from src.mcp.vector_search import VectorSearchFactory
from config.settings import settings

# Create vector search manager from settings (dimension is auto-detected)
manager = VectorSearchFactory.create_from_settings(
    settings=settings,
    kb_root_path=Path("./knowledge_base")
)

# Initialize and index
await manager.initialize()
await manager.index_knowledge_base()

# Search
results = await manager.search(
    query="How do neural networks work?",
    top_k=5
)

for result in results:
    print(f"File: {result['file_path']}")
    print(f"Score: {result['score']}")
    print(f"Text: {result['text'][:200]}")
```

### With Autonomous Agent

```python
# AICODE-NOTE: Vector search is now integrated via MCP Hub
# The bot container manages when to trigger reindexing based on KB changes

from src.bot.vector_search_manager import initialize_vector_search_for_bot

# Initialize vector search for bot (checks availability, performs initial indexing)
vector_search_manager = await initialize_vector_search_for_bot(
    mcp_hub_url="http://mcp-hub:8765/sse",
    kb_root_path=kb_root_path,
    start_monitoring=True  # Start monitoring KB changes
)

# Bot now:
# - Monitors KB changes via events (file operations, git commits)
# - Triggers reindexing via MCP Hub when needed
# - Uses MCP Hub's vector_search tool for semantic search

# Agents access vector search via MCP tools:
# - kb_vector_search: Semantic search in knowledge base
# - (Reindexing is bot responsibility, not exposed to agents)
```

### Manual Component Setup

```python
from src.mcp.vector_search import (
    SentenceTransformerEmbedder,
    FAISSVectorStore,
    DocumentChunker,
    ChunkingStrategy,
    VectorSearchManager,
)

# Create embedder
embedder = SentenceTransformerEmbedder(model_name="all-MiniLM-L6-v2")

# Create vector store
dimension = embedder.get_dimension()
vector_store = FAISSVectorStore(dimension=dimension)

# Create chunker
chunker = DocumentChunker(
    strategy=ChunkingStrategy.SEMANTIC,
    chunk_size=512,
    chunk_overlap=50,
    respect_headers=True
)

# Create manager (used by MCP Hub internally)
manager = VectorSearchManager(
    embedder=embedder,
    vector_store=vector_store,
    chunker=chunker,
    # kb_root_path is optional for MCP usage
    index_path=Path("./data/vector_index"),
    kb_id="my_knowledge_base"  # Optional: for knowledge base isolation
)

# Use as before
await manager.initialize()
await manager.index_knowledge_base()
```

### Knowledge Base Isolation Example

```python
# Different knowledge bases get separate collections and metadata
kb1_manager = VectorSearchManager(
    embedder=embedder,
    vector_store=vector_store,
    chunker=chunker,
    kb_id="user_1_kb"  # Creates collection: knowledge_base_user_1_kb
)

kb2_manager = VectorSearchManager(
    embedder=embedder,
    vector_store=vector_store,
    chunker=chunker,
    kb_id="user_2_kb"  # Creates collection: knowledge_base_user_2_kb
)

# Documents are automatically tagged with kb_id
documents = [
    {"id": "doc1", "content": "User 1's document", "metadata": {"source": "file1.md"}}
]

# This document will have kb_id="user_1_kb" in its metadata
await kb1_manager.add_documents(documents)
```

## Architecture

Vector search is now integrated into the MCP Hub architecture:

### MCP Hub Responsibilities

- Provides `vector_search` tool for semantic search
- Provides `reindex_vector` tool for manual reindexing
- Manages vector search configuration and components
- Handles indexing operations when triggered

### Bot Container Responsibilities

- Monitors knowledge base changes (file operations, git commits)
- Decides when reindexing is needed
- Calls MCP Hub's `reindex_vector` tool
- Manages reindexing schedules and batching

### Agent Access

Agents can use vector search via MCP tools:

```python
# Semantic search (available to agents)
result = await mcp_client.call_tool("vector_search", {
    "query": "neural network architectures",
    "top_k": 5
})

# Reindexing (bot container responsibility)
# Agents do not trigger reindexing directly
# Bot monitors KB changes and triggers reindexing automatically
```

## Performance Considerations

### Model Selection

| Model | Dimension | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| all-MiniLM-L6-v2 | 384 | ⚡⚡⚡ | Good | General use |
| all-mpnet-base-v2 | 768 | ⚡⚡ | Better | Quality-focused |
| text-embedding-ada-002 | 1536 | ⚡ (API) | Excellent | OpenAI users |

### Chunk Size

- **Small (256-512)**: Better precision, more chunks, slower indexing
- **Medium (512-1024)**: Balanced (recommended)
- **Large (1024-2048)**: More context, faster indexing, less precision

### GPU Acceleration

For faster embeddings with sentence-transformers:

```bash
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Model will automatically use GPU if available
```

For faster search with FAISS:

```bash
pip install faiss-gpu
```

## Troubleshooting

### Missing Dependencies

```
ImportError: No module named 'sentence_transformers'
```

**Solution**: Install dependencies: `pip install -e '.[vector-search]'`

### Qdrant Connection Error

```
Failed to connect to Qdrant: Connection refused
```

**Solution**: Start Qdrant server:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### Out of Memory

**Solution**: Reduce chunk size or batch size in indexing

### Slow Indexing

**Solution**:

- Use GPU acceleration
- Use smaller embedding model
- Increase chunk size

### Model change and reindexing

- When you change the embedding model (e.g., switch Infinity or OpenAI model), the embedding
  dimension is detected automatically.
- The vector search manager includes the embedding dimension in its configuration hash. If it
  changes, a full reindex will be triggered on the next run.
- For Qdrant, if an existing collection has a different vector size, it will be recreated
  automatically with the correct dimension.

## Examples

See `examples/vector_search_example.py` for comprehensive examples including:

- Different embedding models
- Different vector stores
- Chunking strategies comparison
- Integration with autonomous agent

## Architecture

```
┌─────────────────────────────────────────────┐
│         VectorSearchManager                 │
│  - Orchestrates indexing and search         │
│  - Manages configuration changes            │
│  - Tracks indexed files                     │
└────────────┬────────────────────────────────┘
             │
             ├─────────────────┬──────────────┐
             │                 │              │
┌────────────▼──────┐  ┌──────▼──────┐  ┌───▼─────────┐
│   BaseEmbedder    │  │ BaseVector  │  │  Document   │
│                   │  │   Store     │  │  Chunker    │
│ - embed_texts()   │  │             │  │             │
│ - embed_query()   │  │ - add()     │  │ - chunk()   │
│ - get_dimension() │  │ - search()  │  │             │
└───────────────────┘  └─────────────┘  └─────────────┘
         │                    │                │
    ┌────┴────┬───────┐      │           ┌────┴────┬────────┐
    │         │       │      │           │         │        │
┌───▼──┐  ┌──▼──┐ ┌──▼──┐   │    ┌─────▼──┐  ┌──▼───┐ ┌──▼───┐
│ ST   │  │ OAI │ │ Inf │   │    │ Fixed  │  │ Over │ │ Sem  │
└──────┘  └─────┘ └─────┘   │    │ Size   │  │ lap  │ │ antic│
                        ┌────┴────┐ └────────┘  └──────┘ └──────┘
                        │         │
                   ┌────▼───┐ ┌──▼─────┐
                   │ FAISS  │ │ Qdrant │
                   └────────┘ └────────┘
```

## License

Same as the main project.
