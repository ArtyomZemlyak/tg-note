# Docker Compose with Vector Search

This stack adds semantic search capabilities to the knowledge base using Qdrant (vector database) and Infinity (embedding service).

## Recommended configuration (tested setup)

This is the most frequently tested, day-to-day setup. It is based on `docker-compose.vector.my.yml`, `config.yaml`, and `.env` from the repository.

**Why we recommend it**

- Full stack enabled: bot, MCP Hub, Docling MCP, Qdrant, Infinity.
- Vector search enabled by default with Infinity + Qdrant.
- Timeouts/logging tuned for long OCR/vectorization flows.
- GPU paths for Docling and Infinity are already wired (you can disable for CPU-only).

**How it differs from the base `docker-compose.yml`**

- No vLLM/SGLang — Qwen Code CLI is used inside the bot container.
- Infinity runs `BAAI/bge-m3`, caches via `~/.cache/huggingface`, has healthcheck + GPU flags (drop `privileged`/`runtime` for CPU).
- Docling MCP mounts shared `config.yaml` and cache/model dirs; GPU flags are on (remove `privileged/deploy` for CPU).
- MCP Hub mounts logs/memory/MCP registry, reads `config.yaml`, and waits on Qdrant/Infinity/Docling healthchecks.
- Bot mounts `./data`, `./logs`, `./knowledge_base`, `./config.yaml`, and Qwen CLI cache (`~/.qwen`).

**Key `config.yaml` changes vs `config.example.yaml`**

- KB Git branch: `KB_GIT_BRANCH: test`.
- Faster grouping: `MESSAGE_GROUP_TIMEOUT: 5`.
- Verbose logs: `LOG_LEVEL: DEBUG`.
- Docling: backend `tesseract`, RapidOCR disabled, `layout` preset `layout_heron`, added `MEDIA_PROCESSING_DOCLING.mcp.timeout: 300`.
- Agent: `AGENT_TYPE: qwen_code_cli`, `AGENT_TIMEOUT: 900`.
- MCP enabled: `AGENT_ENABLE_MCP: true`, `AGENT_ENABLE_MCP_MEMORY: true`, `MCP_TIMEOUT: 120`.
- Vector search enabled: `VECTOR_SEARCH_ENABLED: true`, embedding provider `infinity` (`VECTOR_INFINITY_API_URL: http://infinity:7997`), vector store `qdrant` (`VECTOR_QDRANT_URL: http://qdrant:6333`), chunk size `VECTOR_CHUNK_SIZE: 1024`.

**Environment variables (.env)**

Set tokens and base params (example values, no secrets):

```env
TELEGRAM_BOT_TOKEN=<required>
ALLOWED_USER_IDS=<list or empty>

QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
INFINITY_MODEL=BAAI/bge-m3
INFINITY_BATCH_SIZE=32
MCP_PORT=8765
```

**Run the tested stack**

```bash
docker compose -f docker-compose.vector.my.yml up -d --build
docker compose -f docker-compose.vector.my.yml logs -f
```

Use this as your baseline; if you need CPU-only, drop `privileged/runtime/deploy` from Infinity and Docling.

## Architecture

```
┌─────────────────┐
│  Telegram Bot   │
│  (tg-note-bot)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│   MCP Hub       │─────▶│   Infinity   │
│  (tg-note-hub)  │      │  (embeddings)│
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│    Qdrant       │
│ (vector store)  │
└─────────────────┘
```

## Components

### 1. Qdrant
**Vector database** for storing and searching text embeddings.

- **Image**: `qdrant/qdrant:latest`
- **Ports**: 6333 (HTTP API), 6334 (gRPC API)
- **Storage**: `./data/qdrant_storage`
- **Features**:
  - Stores embeddings
  - Fast semantic similarity search
  - Metadata filtering
  - Collections (one per knowledge base)

### 2. Infinity
**Embedding service** based on transformer models.

- **Image**: `michaelf34/infinity:latest`
- **Port**: 7997
- **Storage**: `./data/infinity_cache` (models cache)
- **Features**:
  - Text-to-vector embeddings
  - Multiple HuggingFace models
  - Batching for speed
  - Optional GPU support

### 3. MCP Hub
**Central gateway** with vector-search tools.

- **Tools**:
  - `vector_search` — semantic search over the KB
  - `reindex_vector` — reindex KB (triggered by the bot container)
- **Flow**:
  - Receives requests from the bot
  - Creates embeddings via Infinity
  - Searches in Qdrant
  - Returns relevant chunks

### 4. Telegram Bot
**Telegram bot** orchestrates vectorization.

- **Flow**:
  - Decides when to index
  - Triggers reindex
  - Performs searches via MCP tools
  - Each KB → its own Qdrant collection

## Quick start

### 1. Prepare

```bash
# Create data directories
mkdir -p data/qdrant_storage data/infinity_cache data/vector_index

# Copy config
cp config.example.yaml config.yaml
```

### 2. Set environment variables

Create or update `.env`:

```env
# Telegram bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_USER_IDS=123456789

# Qdrant
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_COLLECTION=knowledge_base

# Infinity
INFINITY_PORT=7997
# Choose an embedding model (see "Models")
INFINITY_MODEL=BAAI/bge-small-en-v1.5
INFINITY_BATCH_SIZE=32

# MCP Hub
MCP_PORT=8765
```

### 3. Configure `config.yaml`

Enable vector search in `config.yaml`:

```yaml
# Vector search
VECTOR_SEARCH_ENABLED: true

# Embedding provider
VECTOR_EMBEDDING_PROVIDER: infinity
VECTOR_EMBEDDING_MODEL: BAAI/bge-small-en-v1.5
VECTOR_INFINITY_API_URL: http://infinity:7997

# Vector store
VECTOR_STORE_PROVIDER: qdrant
VECTOR_QDRANT_URL: http://qdrant:6333
VECTOR_QDRANT_COLLECTION: knowledge_base

# Chunking
VECTOR_CHUNKING_STRATEGY: fixed_size_overlap
VECTOR_CHUNK_SIZE: 512
VECTOR_CHUNK_OVERLAP: 50

# Search
VECTOR_SEARCH_TOP_K: 5
```

### 4. Run

```bash
# Start all services (including Qdrant and Infinity)
# IMPORTANT: vLLM and SGLang use the same port — comment one out in docker-compose.yml!
docker-compose up -d

# Check logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 5. Health checks

```bash
# Qdrant
curl http://localhost:6333/healthz

# Infinity
curl http://localhost:7997/health

# MCP Hub
curl http://localhost:8765/health
```

**Note**: When using external embedding providers (Infinity or OpenAI), installing `sentence-transformers` locally is **not required** because embeddings are generated by the service. You only need the vector store backend (`faiss-cpu` or `qdrant-client`).

## Embedding models

### Recommended models for Infinity

#### English

| Model | Dim | Quality | Speed | Use case |
|-------|-----|---------|-------|----------|
| `BAAI/bge-small-en-v1.5` | 384 | Good | ⚡⚡⚡ | Default, fast |
| `BAAI/bge-base-en-v1.5` | 768 | Excellent | ⚡⚡ | Balanced |
| `BAAI/bge-large-en-v1.5` | 1024 | Best quality | ⚡ | Max quality |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Good | ⚡⚡⚡ | Lightweight alternative |

#### Multilingual

| Model | Dim | Languages | Recommendation |
|-------|-----|-----------|----------------|
| `BAAI/bge-m3` | 1024 | 100+ | Best multilingual choice |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384 | 50+ | Compact alternative |

#### Russian

| Model | Dim | Notes |
|-------|-----|-------|
| `BAAI/bge-m3` | 1024 | Works great for Russian |
| `intfloat/multilingual-e5-large` | 1024 | Strong quality for Russian |

### Switching models

Change the model in `.env`:

```env
INFINITY_MODEL=BAAI/bge-m3
```

After updating the model:

```bash
# Restart Infinity to load the new model
docker-compose restart infinity

# Reindex the knowledge base (via bot or MCP API)
```

### Auto-detect vector dimension and reindex

- Embedding dimensionality is auto-detected at startup for `Infinity` and `OpenAI`.
- If you change models and the dimension changes, the system will trigger a full reindex on next start.
- For `Qdrant`: if an existing collection has a different dimension, it will be recreated with the correct size.

## Usage

### Via Telegram bot

The bot manages vector search automatically:

1. **Auto indexing**: when new documents arrive
2. **Semantic search**: bot uses vector search to answer questions
3. **Reindex**: bot decides when to refresh the index

### Via MCP API

#### Vector search

```bash
# Semantic similarity search
curl -X POST http://localhost:8765/tools/vector_search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how do neural networks work",
    "top_k": 5
  }'
```

Response:
```json
{
  "success": true,
  "query": "how do neural networks work",
  "top_k": 5,
  "results": [
    {
      "file_path": "topics/ml/neural-networks.md",
      "text": "Neural networks are...",
      "score": 0.89,
      "chunk_index": 0
    }
  ],
  "results_count": 5
}
```

#### Reindex

```bash
# Reindex the knowledge base
curl -X POST http://localhost:8765/tools/reindex_vector \
  -H "Content-Type: application/json" \
  -d '{
    "force": false
  }'
```

Response:
```json
{
  "success": true,
  "files_processed": 42,
  "files_skipped": 5,
  "chunks_indexed": 1234,
  "time_elapsed": "12.5s"
}
```

## Data management

### Data layout

```
./data/
├── qdrant_storage/     # Qdrant vector DB
├── infinity_cache/     # Infinity model cache
└── vector_index/       # Index metadata (for FAISS)
```

### Cleaning data

```bash
# Stop services
docker-compose down

# Remove vector data
rm -rf data/qdrant_storage/*
rm -rf data/vector_index/*

# You may keep model cache for faster restart
# rm -rf data/infinity_cache/*

# Start again
docker-compose up -d
```

### Backup

```bash
# Stop Qdrant for consistent backup
docker-compose stop qdrant

# Create backup
tar -czf qdrant_backup_$(date +%Y%m%d).tar.gz data/qdrant_storage/

# Start Qdrant
docker-compose start qdrant
```

## Performance

### Infinity batching

```env
# Larger = faster, more memory
INFINITY_BATCH_SIZE=32  # Default

# For large models or limited memory
INFINITY_BATCH_SIZE=16

# For powerful hardware
INFINITY_BATCH_SIZE=64
```

### GPU acceleration

Uncomment in `docker-compose.yml` (infinity section):

```yaml
infinity:
  # ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

Requirements:
- NVIDIA GPU
- nvidia-docker installed
- CUDA drivers

### Chunk size tuning

In `config.yaml`:

```yaml
# Smaller chunks = more precise search, slower indexing
VECTOR_CHUNK_SIZE: 256

# Larger chunks = faster indexing, less precise search
VECTOR_CHUNK_SIZE: 1024

# Balanced (recommended)
VECTOR_CHUNK_SIZE: 512
```

## Monitoring

### View logs

```bash
# All services
docker-compose logs -f

# Qdrant
docker-compose logs -f qdrant

# Infinity
docker-compose logs -f infinity

# MCP Hub
docker-compose logs -f mcp-hub
```

### Qdrant status

```bash
# List collections
curl http://localhost:6333/collections

# Specific collection
curl http://localhost:6333/collections/knowledge_base
```

### Infinity checks

```bash
# List models
curl http://localhost:7997/models

# Test embeddings
curl -X POST http://localhost:7997/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "BAAI/bge-small-en-v1.5",
    "input": ["test text"]
  }'
```

## Troubleshooting

### Infinity does not start

**Issue**: `Model download failed`

**Fix**:
```bash
# Check logs
docker-compose logs infinity

# Clear cache and restart
rm -rf data/infinity_cache/*
docker-compose restart infinity
```

### Qdrant uses too much space

**Fix**:
```bash
# Check size
du -sh data/qdrant_storage/

# Optimize (run inside Qdrant container)
docker exec tg-note-qdrant curl -X POST http://localhost:6333/collections/knowledge_base/optimize
```

### Slow indexing

**Possible causes**:
1. Large embedding model
2. Many files
3. Small batch size

**Fixes**:
```bash
# 1. Use a smaller model
INFINITY_MODEL=BAAI/bge-small-en-v1.5

# 2. Increase batch size
INFINITY_BATCH_SIZE=64

# 3. Use GPU (see "GPU acceleration")
```

### Vector search not available

**Issue**: Error "Vector search is not available"

**Fix**:
1. Ensure `VECTOR_SEARCH_ENABLED=true` in config.yaml
2. Verify `VECTOR_EMBEDDING_PROVIDER`:
   - For `infinity` or `openai`: do **not** install `sentence-transformers`
   - For `sentence_transformers`: install `pip install sentence-transformers`
3. Install at least one vector store backend:
   - `pip install faiss-cpu` OR `pip install qdrant-client`
4. Ensure Qdrant and Infinity are running
5. Check container networking

```bash
# Inspect network
docker network inspect tg-note-network

# Ensure all containers share the network
docker-compose ps
```

## Migrating from the simple stack

If you used a simple stack without vector search:

```bash
# 1. Stop current services
docker-compose down

# 2. Update config.yaml (enable VECTOR_SEARCH_ENABLED)

# 3. Ensure qdrant and infinity sections are active in docker-compose.yml

# 4. Start all services
docker-compose up -d

# 5. Reindex the existing knowledge base
# (via bot or call reindex_vector API — not from an agent)
```

## Integrating with an existing knowledge base

On first start with vector search:

1. All existing documents are indexed automatically.
2. Index is stored in Qdrant.
3. New documents are indexed automatically.

## Security

### Qdrant API Key

For production enable authentication:

```yaml
qdrant:
  environment:
    - QDRANT__SERVICE__API_KEY=your-secret-key
```

And update `.env`:

```env
VECTOR_QDRANT_API_KEY=your-secret-key
```

### Infinity API Key

If you need authentication for Infinity:

```yaml
infinity:
  environment:
    - INFINITY_API_KEY=your-secret-key
```

And in `.env`:

```env
VECTOR_INFINITY_API_KEY=your-secret-key
```

## Additional resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Infinity GitHub](https://github.com/michaelfeil/infinity)
- [BGE Models](https://huggingface.co/BAAI)
- [Sentence Transformers](https://www.sbert.net/)

## AICODE-NOTE

Flow logic:
- **Bot** orchestrates: decides when to index and when to search
- **MCP Hub** exposes tools: `vector_search` (and `reindex_vector` for the bot)
- **Qdrant** stores vectors: separate collection per knowledge base
- **Infinity** generates embeddings: turns text into vectors

Each user knowledge base gets its own Qdrant collection for isolation.
