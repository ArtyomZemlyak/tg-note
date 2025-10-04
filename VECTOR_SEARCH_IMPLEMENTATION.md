# Vector Search Implementation Summary

## Overview
Added flexible vector search capabilities to the autonomous agent tools, enabling semantic search in the knowledge base.

## What Was Implemented

### 1. Vector Search Module (`src/vector_search/`)
Created a complete vector search system with the following components:

#### Embedding Models (`embeddings.py`)
- **BaseEmbedder**: Abstract base class for embedding models
- **SentenceTransformerEmbedder**: Local embeddings using sentence-transformers
- **OpenAIEmbedder**: OpenAI API embeddings
- **InfinityEmbedder**: Infinity API embeddings (https://github.com/michaelfeil/infinity)

#### Vector Stores (`vector_stores.py`)
- **BaseVectorStore**: Abstract base class for vector stores
- **FAISSVectorStore**: Local FAISS-based vector store
- **QdrantVectorStore**: Qdrant API-based vector store

#### Document Chunking (`chunking.py`)
- **DocumentChunker**: Splits documents into searchable chunks
- **ChunkingStrategy**: Three strategies:
  - `FIXED_SIZE`: Fixed-size chunks
  - `FIXED_SIZE_WITH_OVERLAP`: Fixed-size with overlap
  - `SEMANTIC`: Respects markdown structure (headers, paragraphs)

#### Vector Search Manager (`manager.py`)
- **VectorSearchManager**: Orchestrates indexing and search
  - Tracks indexed files and detects changes
  - Automatic re-indexing when configuration changes
  - Incremental indexing (only indexes modified files)
  - Metadata tracking for configuration validation

#### Factory (`factory.py`)
- **VectorSearchFactory**: Creates components from configuration
  - `create_embedder()`: Creates embedding model from settings
  - `create_vector_store()`: Creates vector store from settings
  - `create_chunker()`: Creates document chunker from settings
  - `create_from_settings()`: Full setup from settings object

### 2. Configuration (`config/settings.py`)
Added comprehensive vector search settings:
- `VECTOR_SEARCH_ENABLED`: Enable/disable vector search
- Embedding settings: provider, model, API configuration
- Vector store settings: provider, Qdrant configuration
- Chunking settings: strategy, size, overlap, header respect
- Search settings: top_k results

### 3. Agent Integration (`src/agents/autonomous_agent.py`)
Extended AutonomousAgent with:
- `enable_vector_search` parameter
- `vector_search_manager` parameter
- Two new tools:
  - **kb_vector_search**: Semantic search in knowledge base
  - **kb_reindex_vector**: Reindex knowledge base

### 4. Dependencies (`pyproject.toml`)
Added optional dependency group `vector-search`:
```bash
pip install -e '.[vector-search]'
```
Includes:
- `sentence-transformers>=2.2.0`
- `faiss-cpu>=1.7.4`
- `qdrant-client>=1.7.0`

### 5. Documentation
- `src/vector_search/README.md`: Comprehensive module documentation
- `config.example.yaml`: Detailed configuration examples with comments
- `examples/vector_search_example.py`: Complete usage examples

### 6. Tests (`tests/test_vector_search.py`)
Tests for document chunking strategies:
- Fixed size chunking
- Chunking with overlap
- Semantic chunking
- Paragraph splitting
- Edge cases (empty text, long paragraphs)
- Metadata preservation
- Integration tests

## Features

### Flexible Configuration
Users can choose from multiple options:

**Embedding Models:**
- Local: sentence-transformers (no API, private, free)
- Cloud: OpenAI API (high quality, paid)
- Self-hosted: Infinity API (flexible, open-source)

**Vector Stores:**
- Local: FAISS (fast, no external services)
- Remote: Qdrant (production-ready, scalable)

**Chunking Strategies:**
- Fixed size: Simple, predictable
- Fixed size with overlap: Better context continuity
- Semantic: Respects document structure

### Automatic Management
- **Change Detection**: Tracks file modifications
- **Incremental Indexing**: Only indexes changed files
- **Configuration Validation**: Re-indexes if configuration changes
- **Error Handling**: Graceful degradation if dependencies missing

### Agent Tools
When enabled, agent gets two new tools:

1. **kb_vector_search**: Semantic search
   ```python
   {
       "query": "neural network architectures",
       "top_k": 5
   }
   ```

2. **kb_reindex_vector**: Force reindexing
   ```python
   {
       "force": true  # Optional, default: false
   }
   ```

## Usage Examples

### Basic Setup
```python
from src.vector_search import VectorSearchFactory
from config.settings import settings

# Create from settings
manager = VectorSearchFactory.create_from_settings(
    settings=settings,
    kb_root_path=Path("./knowledge_base")
)

# Initialize and index
await manager.initialize()
await manager.index_knowledge_base()

# Search
results = await manager.search("neural networks", top_k=5)
```

### With Agent
```python
from src.agents.autonomous_agent import AutonomousAgent

agent = AutonomousAgent(
    llm_connector=llm_connector,
    kb_root_path=kb_root_path,
    enable_vector_search=True,
    vector_search_manager=manager
)

# Agent now has kb_vector_search and kb_reindex_vector tools
```

### Configuration
```yaml
# config.yaml
VECTOR_SEARCH_ENABLED: true
VECTOR_EMBEDDING_PROVIDER: "sentence_transformers"
VECTOR_EMBEDDING_MODEL: "all-MiniLM-L6-v2"
VECTOR_STORE_PROVIDER: "faiss"
VECTOR_CHUNKING_STRATEGY: "fixed_size_overlap"
VECTOR_CHUNK_SIZE: 512
VECTOR_CHUNK_OVERLAP: 50
```

## Default Behavior

**Vector search is disabled by default.**

When enabled:
1. On first use, knowledge base is automatically indexed
2. Index is saved to `.vector_index/` in KB root
3. Subsequent starts load existing index
4. Modified files are automatically re-indexed
5. Configuration changes trigger full re-indexing

## File Structure
```
src/vector_search/
├── __init__.py           # Module exports
├── embeddings.py         # Embedding models
├── vector_stores.py      # Vector stores
├── chunking.py          # Document chunking
├── manager.py           # Search manager
├── factory.py           # Factory for creating components
└── README.md            # Documentation

tests/
└── test_vector_search.py # Tests

examples/
└── vector_search_example.py # Usage examples

config/
└── settings.py          # Vector search settings

config.example.yaml      # Configuration documentation
```

## Performance Considerations

### Model Selection
- **all-MiniLM-L6-v2**: Fast, 384-dim, good quality (recommended)
- **all-mpnet-base-v2**: Slower, 768-dim, better quality
- **text-embedding-ada-002**: OpenAI, 1536-dim, excellent (paid)

### Chunk Size
- Small (256-512): Better precision, more chunks
- Medium (512-1024): Balanced (recommended)
- Large (1024-2048): More context, faster indexing

### GPU Acceleration
- sentence-transformers: Automatic GPU support if PyTorch with CUDA
- FAISS: Use `faiss-gpu` for GPU-accelerated search

## Important Notes

1. **Optional Dependencies**: Vector search requires additional packages
   ```bash
   pip install -e '.[vector-search]'
   ```

2. **Disabled by Default**: Must be explicitly enabled in config

3. **Re-indexing Required**: When changing:
   - Embedding model or provider
   - Vector store provider
   - Chunking strategy or parameters

4. **Incremental Updates**: 
   - Only modified files are re-indexed
   - Configuration tracked with hash
   - Metadata stored in `.vector_index/metadata.json`

5. **Privacy**: 
   - sentence-transformers: Fully local, no data leaves system
   - OpenAI/Infinity: Data sent to API

## Testing

Run tests:
```bash
# Basic chunking tests (no dependencies required)
pytest tests/test_vector_search.py -v

# Full examples (requires dependencies)
python examples/vector_search_example.py
```

## Future Enhancements

Possible additions:
- Support for more embedding models (Cohere, HuggingFace Inference API)
- Support for more vector stores (Weaviate, Pinecone, Milvus)
- Hybrid search (combining keyword and vector search)
- Reranking with cross-encoder models
- Query expansion and refinement
- Metadata filtering in searches
- Batch processing for large knowledge bases

## References

- sentence-transformers: https://www.sbert.net/
- FAISS: https://github.com/facebookresearch/faiss
- Qdrant: https://qdrant.tech/
- Infinity: https://github.com/michaelfeil/infinity
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
