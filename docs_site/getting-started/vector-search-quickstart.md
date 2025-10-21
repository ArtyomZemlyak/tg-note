# Vector Search Quick Start

Quick guide to set up semantic vector search in your knowledge base.

## What This Gives You

- 🔍 **Semantic Search**: Search by meaning, not keywords
- 🚀 **Automatic Indexing**: Knowledge base is automatically vectorized
- 🎯 **Accurate Results**: Finds relevant documents even without exact word matches
- 🌐 **Multi-language**: Russian and English support

## Architecture

```
Bot → MCP Hub → Infinity (embeddings) → Qdrant (vector DB)
```

## Quick Start

### 1. Prepare Files

```bash
# Copy configuration examples
cp .env.vector.example .env
cp config.example.yaml config.yaml

# Create data directories
mkdir -p data/qdrant_storage data/infinity_cache
```

### 2. Configure .env

Edit `.env`, minimum required:

```env
# Your Telegram bot token
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Allowed user IDs
ALLOWED_USER_IDS=123456789

# Embedding model (for Russian + English)
INFINITY_MODEL=BAAI/bge-m3
```

### 3. Configure config.yaml

Enable vector search in `config.yaml`:

```yaml
# Enable vector search
VECTOR_SEARCH_ENABLED: true

# Embedding settings
VECTOR_EMBEDDING_PROVIDER: infinity
VECTOR_EMBEDDING_MODEL: BAAI/bge-m3
VECTOR_INFINITY_API_URL: http://infinity:7997

# Qdrant settings
VECTOR_STORE_PROVIDER: qdrant
VECTOR_QDRANT_URL: http://qdrant:6333
VECTOR_QDRANT_COLLECTION: knowledge_base
```

### 4. Start Services

```bash
# Start all services
docker-compose -f docker-compose.vector.yml up -d

# Watch logs (wait for model loading ~1-2 minutes)
docker-compose -f docker-compose.vector.yml logs -f infinity
```

### 5. Verify Operation

```bash
# Check status of all services
docker-compose -f docker-compose.vector.yml ps

# Should be running:
# - tg-note-qdrant (healthy)
# - tg-note-infinity (healthy)
# - tg-note-hub (healthy)
# - tg-note-bot (running)
```

## Usage

### Through Telegram Bot

1. Send documents to the bot (text, PDF, DOCX, etc.)
2. Bot automatically indexes them
3. Ask questions - bot will use semantic search

### Example

```
👤 User: How do transformers work in NLP?

🤖 Bot: [finds relevant sections in knowledge base using vector search]
```

## Model Selection

### For Russian + English (recommended)

```env
INFINITY_MODEL=BAAI/bge-m3
```

### English only (faster)

```env
INFINITY_MODEL=BAAI/bge-small-en-v1.5
```

### Other Options

| Model | Languages | Quality | Speed |
|-------|-----------|---------|-------|
| `BAAI/bge-m3` | Multilingual | ⭐⭐⭐⭐⭐ | ⚡⚡ |
| `BAAI/bge-small-en-v1.5` | English | ⭐⭐⭐⭐ | ⚡⚡⚡ |
| `BAAI/bge-base-en-v1.5` | English | ⭐⭐⭐⭐⭐ | ⚡⚡ |

## Management

### View Logs

```bash
# All logs
docker-compose -f docker-compose.vector.yml logs -f

# Specific service only
docker-compose -f docker-compose.vector.yml logs -f infinity
```

### Restart

```bash
# Restart all
docker-compose -f docker-compose.vector.yml restart

# Restart specific service
docker-compose -f docker-compose.vector.yml restart infinity
```

### Stop

```bash
# Stop all services
docker-compose -f docker-compose.vector.yml down

# Stop and remove data (be careful!)
docker-compose -f docker-compose.vector.yml down -v
```

## Resource Requirements

### Minimum Requirements

- **RAM**: 4 GB (with `bge-small` model)
- **Disk**: 5 GB (for models and data)
- **CPU**: 2 cores

### Recommended Requirements

- **RAM**: 8 GB (with `bge-m3` model)
- **Disk**: 10 GB
- **CPU**: 4 cores
- **GPU** (optional): Speeds up processing 5-10x

## GPU Acceleration (Optional)

To speed up processing, uncomment in `docker-compose.vector.yml`:

```yaml
infinity:
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

## Troubleshooting

### Infinity Won't Start

**Problem**: Infinity container keeps restarting

**Solution**: Check logs and give time for model loading (1-2 minutes)

```bash
docker-compose -f docker-compose.vector.yml logs infinity
```

### Out of Memory

**Problem**: Out of memory

**Solution**: Use smaller model

```env
INFINITY_MODEL=BAAI/bge-small-en-v1.5
INFINITY_BATCH_SIZE=16
```

### Vector Search Not Available

**Problem**: "Vector search is not available"

**Solution**: Check config.yaml

```yaml
VECTOR_SEARCH_ENABLED: true
```

## How It Works

1. **Bot** receives document from user
2. **Bot** calls `reindex_vector` through MCP Hub
3. **MCP Hub** sends text to **Infinity** to create embeddings
4. **MCP Hub** saves vectors to **Qdrant**
5. When searching, **Bot** calls `vector_search`
6. **MCP Hub** gets query embedding from **Infinity**
7. **MCP Hub** searches similar vectors in **Qdrant**
8. **Bot** receives relevant results

Each user's knowledge base → separate collection in Qdrant.

## Additional Documentation

Complete documentation: [Docker Vector Search Setup](../deployment/docker-vector-search.md)

## AICODE-NOTE

- Bot manages vectorization logic (when to index, when to search)
- MCP Hub provides tools (vector_search, reindex_vector)
- Infinity generates embeddings (converts text to vectors)
- Qdrant stores vectors (separate collection for each knowledge base)