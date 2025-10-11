# Docker Deployment Guide

This guide explains how to deploy tg-note using Docker Compose.

## Architecture

The deployment consists of three main services:

1. **bot** - Main Telegram bot application
2. **mcp-http-server** - MCP HTTP gateway for memory operations (supports json, vector, and mem-agent storage)
3. **vllm-server** - vLLM inference server for mem-agent (optional, only needed if using mem-agent storage)

```
┌─────────────────┐
│  Telegram Bot   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐       ┌──────────────┐
│ MCP HTTP Server │←──────│ vLLM Server  │
│   (Gateway)     │       │ (optional)   │
└─────────────────┘       └──────────────┘
         │
         ↓
   ┌─────────┐
   │ Storage │
   │  Types  │
   ├─────────┤
   │  json   │ ← Simple, fast (default)
   │ vector  │ ← Semantic search
   │mem-agent│ ← AI-powered (needs vLLM)
   └─────────┘
```

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- NVIDIA GPU (for vLLM server) with nvidia-docker runtime
- At least 8GB free disk space
- Telegram Bot Token

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.docker.example .env

# Edit .env and set your credentials
nano .env
```

**Required variables:**
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token from @BotFather

### 2. Choose Storage Mode

The system supports three storage modes:

#### Mode 1: JSON Storage (Default, Fastest)
```bash
# In .env:
MEM_AGENT_STORAGE_TYPE=json
```

Start only bot and mcp-server:
```bash
docker-compose up -d bot mcp-http-server
```

#### Mode 2: Vector Storage (Semantic Search)
```bash
# In .env:
MEM_AGENT_STORAGE_TYPE=vector
MEM_AGENT_MODEL=BAAI/bge-m3
```

Start only bot and mcp-server:
```bash
docker-compose up -d bot mcp-http-server
```

#### Mode 3: Mem-Agent Storage (AI-Powered, Requires GPU)
```bash
# In .env:
MEM_AGENT_STORAGE_TYPE=mem-agent
MEM_AGENT_MODEL=driaforall/mem-agent
MEM_AGENT_BACKEND=vllm
```

Start all services including vLLM:
```bash
docker-compose up -d
```

### 3. Monitor Services

```bash
# View logs
docker-compose logs -f

# Check service status
docker-compose ps

# Check specific service
docker-compose logs -f bot
docker-compose logs -f mcp-http-server
docker-compose logs -f vllm-server
```

## Configuration

### Memory Storage Options

| Storage Type | Speed | Features | GPU Required | Use Case |
|--------------|-------|----------|--------------|----------|
| `json` | ⚡️ Fast | Simple key-value storage | No | Quick notes, basic memory |
| `vector` | 🔍 Medium | Semantic search, embeddings | No | Semantic search, similar memory retrieval |
| `mem-agent` | 🤖 Slower | AI-powered context management | Yes | Advanced memory operations, intelligent retrieval |

### Environment Variables

See `.env.docker.example` for all available options.

**Key variables:**

```bash
# Storage configuration
MEM_AGENT_STORAGE_TYPE=json|vector|mem-agent
MEM_AGENT_MODEL=driaforall/mem-agent

# vLLM settings (for mem-agent mode)
GPU_MEMORY_UTILIZATION=0.8    # 0.0-1.0, adjust based on GPU
MAX_MODEL_LEN=4096             # Context window
TENSOR_PARALLEL_SIZE=1         # Number of GPUs

# Agent configuration
AGENT_TYPE=stub|qwen_code|qwen_code_cli
AGENT_ENABLE_MCP_MEMORY=true
```

## Data Persistence

All data is persisted using Docker volumes:

```
./data/memory/        - Memory storage (per-user)
./knowledge_base/     - Knowledge base files
./logs/              - Application logs
huggingface-cache    - Model cache (Docker volume)
```

## Service Management

### Start Services
```bash
# All services
docker-compose up -d

# Specific services
docker-compose up -d bot mcp-http-server
```

### Stop Services
```bash
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

### Restart Services
```bash
docker-compose restart bot
```

### Update Services
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

## Troubleshooting

### Bot not starting
```bash
# Check logs
docker-compose logs bot

# Common issues:
# - Missing TELEGRAM_BOT_TOKEN
# - MCP server not ready
```

### MCP Server not responding
```bash
# Check logs
docker-compose logs mcp-http-server

# Test endpoint
curl http://localhost:8765/health
```

### vLLM Server issues
```bash
# Check GPU availability
nvidia-smi

# Check vLLM logs
docker-compose logs vllm-server

# Common issues:
# - Insufficient GPU memory - reduce GPU_MEMORY_UTILIZATION
# - Model download in progress - wait for completion
# - NVIDIA runtime not configured
```

### Configure NVIDIA Docker Runtime

If you get GPU errors:

```bash
# Install nvidia-docker2
sudo apt-get install nvidia-docker2

# Restart Docker
sudo systemctl restart docker

# Test GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

## Scaling and Production

### Without GPU (JSON/Vector mode only)

If you don't have GPU, use json or vector storage:

```yaml
# docker-compose.override.yml
services:
  bot:
    environment:
      - MEM_AGENT_STORAGE_TYPE=json
```

```bash
docker-compose up -d bot mcp-http-server
```

### Multiple Bots (Shared MCP)

Multiple bot instances can share the same MCP server:

```yaml
services:
  bot-1:
    extends:
      service: bot
    environment:
      - TELEGRAM_BOT_TOKEN=${BOT_TOKEN_1}
  
  bot-2:
    extends:
      service: bot
    environment:
      - TELEGRAM_BOT_TOKEN=${BOT_TOKEN_2}
```

### Health Monitoring

All services have health checks:

```bash
# Check health status
docker-compose ps

# Automated monitoring
docker events --filter 'event=health_status'
```

## Performance Tuning

### vLLM Server

```bash
# Use more GPU memory (faster inference)
GPU_MEMORY_UTILIZATION=0.95

# Smaller context for less memory
MAX_MODEL_LEN=2048

# Multi-GPU setup
TENSOR_PARALLEL_SIZE=2
```

### MCP Server

```bash
# Increase memory limits
MEM_AGENT_MEMORY_SIZE_LIMIT=209715200  # 200MB
```

## Security Considerations

1. **Never commit `.env` file** - Contains sensitive credentials
2. **Restrict access** - Use `ALLOWED_USER_IDS` to whitelist users
3. **Network isolation** - Services communicate via internal Docker network
4. **Volume permissions** - Ensure proper permissions on mounted volumes

```bash
# Set proper permissions
chmod 700 data/
chmod 700 logs/
chmod 600 .env
```

## Backup and Restore

### Backup
```bash
# Stop services
docker-compose down

# Backup data
tar -czf backup-$(date +%Y%m%d).tar.gz data/ knowledge_base/ .env

# Start services
docker-compose up -d
```

### Restore
```bash
# Stop services
docker-compose down

# Restore data
tar -xzf backup-YYYYMMDD.tar.gz

# Start services
docker-compose up -d
```

## Logs and Debugging

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service with tail
docker-compose logs -f --tail=100 bot

# Export logs
docker-compose logs > debug.log
```

### Debug Mode
```bash
# Enable debug logging
docker-compose exec bot sh -c 'export LOG_LEVEL=DEBUG && python main.py'
```

### Access Container Shell
```bash
docker-compose exec bot bash
docker-compose exec mcp-http-server bash
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/ArtyomZemlyak/tg-note/issues
- Documentation: See `docs_site/` directory
