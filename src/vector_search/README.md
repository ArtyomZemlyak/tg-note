# Vector Search Module

Flexible vector search capabilities for the knowledge base with support for multiple embedding models and vector stores.

## Features

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
from src.vector_search import VectorSearchFactory
from config.settings import settings

# Create vector search manager from settings
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
from src.agents.autonomous_agent import AutonomousAgent
from src.vector_search import VectorSearchFactory

# Create vector search manager
manager = VectorSearchFactory.create_from_settings(
    settings=settings,
    kb_root_path=kb_root_path
)

# Initialize
await manager.initialize()
await manager.index_knowledge_base()

# Create agent with vector search
agent = AutonomousAgent(
    llm_connector=llm_connector,
    kb_root_path=kb_root_path,
    enable_vector_search=True,
    vector_search_manager=manager
)

# Agent now has access to kb_vector_search and kb_reindex_vector tools
```

### Manual Component Setup

```python
from src.vector_search import (
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

# Create manager
manager = VectorSearchManager(
    embedder=embedder,
    vector_store=vector_store,
    chunker=chunker,
    kb_root_path=Path("./knowledge_base")
)

# Use as before
await manager.initialize()
await manager.index_knowledge_base()
```

## Agent Tools

When vector search is enabled, two new tools are available:

### kb_vector_search

Performs semantic vector search in the knowledge base.

```python
result = await agent._tool_kb_vector_search({
    "query": "neural network architectures",
    "top_k": 5
})
```

### kb_reindex_vector

Reindexes the knowledge base for vector search.

```python
result = await agent._tool_kb_reindex_vector({
    "force": False  # Set to True to force full reindexing
})
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
