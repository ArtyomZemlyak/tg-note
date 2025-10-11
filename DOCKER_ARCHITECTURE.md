# Docker Architecture

This document describes the Docker-based deployment architecture for tg-note.

## Overview

The system consists of three main services that communicate via HTTP/REST:

```
┌──────────────────────────────────────────────────────────────┐
│                     Docker Network                           │
│                    (tg-note-network)                         │
│                                                              │
│  ┌────────────────┐                                         │
│  │  Telegram Bot  │                                         │
│  │  (main.py)     │                                         │
│  └───────┬────────┘                                         │
│          │ HTTP                                             │
│          ↓                                                  │
│  ┌──────────────────┐         ┌─────────────────┐         │
│  │  MCP HTTP Server │ HTTP    │  vLLM Server    │         │
│  │   (Gateway)      │←────────│  (Optional)     │         │
│  │                  │         │                 │         │
│  │  Storage Router: │         │  GPU Required   │         │
│  │  ├─ JSON        │         │                 │         │
│  │  ├─ Vector      │         └─────────────────┘         │
│  │  └─ Mem-Agent   │                                       │
│  └──────┬───────────┘                                       │
│         │                                                   │
│         ↓                                                   │
│  ┌──────────────────┐                                       │
│  │   Volumes        │                                       │
│  │  - data/memory   │                                       │
│  │  - knowledge_base│                                       │
│  │  - logs          │                                       │
│  └──────────────────┘                                       │
└──────────────────────────────────────────────────────────────┘
```

## Services

### 1. Bot Service (`Dockerfile.bot`)

**Purpose:** Main application that handles Telegram messages and orchestrates workflows

**Key Features:**
- Telegram bot interface
- Agent system (stub, qwen_code, qwen_code_cli)
- Knowledge base management
- Git operations
- Message processing

**Dependencies:**
- MCP HTTP Server (required when AGENT_ENABLE_MCP_MEMORY=true)
- External LLM APIs (OpenAI, Anthropic, Qwen) - optional, depends on agent type

**Volumes:**
- `./knowledge_base:/app/knowledge_base` - User's knowledge base
- `./data:/app/data` - Processed messages, settings
- `./logs:/app/logs` - Application logs
- `./config.yaml:/app/config.yaml` - Optional config

**Environment Variables:**
- `TELEGRAM_BOT_TOKEN` - Required
- `AGENT_TYPE` - Agent type selection
- `AGENT_ENABLE_MCP_MEMORY` - Enable memory features
- `MCP_MEMORY_URL` - URL to MCP server

### 2. MCP HTTP Server (`Dockerfile.mcp`)

**Purpose:** Gateway for memory operations with pluggable storage backends

**Storage Backends:**

#### JSON Storage (Default)
- Fast, lightweight
- No external dependencies
- File-based storage
- Perfect for simple use cases

#### Vector Storage
- Semantic search capabilities
- Uses sentence-transformers for embeddings
- FAISS for vector search
- No GPU required (CPU embeddings)

#### Mem-Agent Storage
- AI-powered memory management
- Context-aware storage and retrieval
- Requires vLLM server (GPU)
- Best for advanced use cases

**Volumes:**
- `./data/memory:/app/data/memory` - Memory storage (per-user)
- `./logs:/app/logs` - MCP server logs
- `huggingface-cache:/root/.cache/huggingface` - Model cache (shared)

**Environment Variables:**
- `MEM_AGENT_STORAGE_TYPE` - Storage backend (json/vector/mem-agent)
- `MEM_AGENT_MODEL` - Model for vector/mem-agent
- `MEM_AGENT_HOST` - vLLM server hostname
- `MEM_AGENT_PORT` - vLLM server port

**API Endpoints:**
- `POST /sse` - MCP protocol over Server-Sent Events
- `GET /health` - Health check

### 3. vLLM Server (`Dockerfile.vllm`)

**Purpose:** High-performance LLM inference server (OpenAI-compatible API)

**Key Features:**
- OpenAI-compatible API
- GPU acceleration
- Efficient batching
- PagedAttention for memory efficiency

**Requirements:**
- NVIDIA GPU with CUDA support
- nvidia-docker runtime
- Sufficient VRAM (depends on model)

**Volumes:**
- `huggingface-cache:/root/.cache/huggingface` - Model cache (shared with MCP)

**Environment Variables:**
- `MODEL_NAME` - HuggingFace model ID
- `GPU_MEMORY_UTILIZATION` - Fraction of GPU memory to use (0.0-1.0)
- `MAX_MODEL_LEN` - Maximum context length
- `TENSOR_PARALLEL_SIZE` - Number of GPUs for tensor parallelism

**API Endpoints:**
- `POST /v1/chat/completions` - OpenAI-compatible chat endpoint
- `POST /v1/completions` - OpenAI-compatible completion endpoint
- `GET /health` - Health check
- `GET /v1/models` - List available models

## Communication Flow

### Message Processing Flow

```
1. User sends message to Telegram
   ↓
2. Bot receives message (bot service)
   ↓
3. Bot processes message with agent
   ↓
4. Agent may call MCP tools for memory operations
   ↓
5. MCP server routes to appropriate storage backend
   ↓
6. If mem-agent backend:
   ├─ MCP calls vLLM server
   ├─ vLLM processes with GPU
   └─ Returns AI-powered response
   ↓
7. Result returned to agent
   ↓
8. Agent generates response
   ↓
9. Bot sends response to user
```

### Memory Operation Flow

```
Store Memory:
Bot → MCP HTTP Server → Storage Backend → File System
                      ↓ (if mem-agent)
                    vLLM Server (GPU)

Retrieve Memory:
Bot → MCP HTTP Server → Storage Backend → File System
                      ↓ (if mem-agent)
                    vLLM Server (GPU)
                      ↓
                    Ranked Results
```

## Network Architecture

All services communicate via internal Docker network (`tg-note-network`).

**Exposed Ports:**
- `8765` - MCP HTTP Server (optional, for external access)
- `8001` - vLLM Server (optional, for external access)

**Internal Communication:**
- Bot → MCP: `http://mcp-http-server:8765/sse`
- MCP → vLLM: `http://vllm-server:8001/v1`

## Data Persistence

### Volumes

1. **Local Bind Mounts:**
   - `./data/memory` - Per-user memory storage
   - `./knowledge_base` - Git-based knowledge base
   - `./logs` - Application logs

2. **Named Volume:**
   - `huggingface-cache` - Shared model cache (persistent)

### Data Organization

```
data/
├── memory/
│   ├── user_{user_id}/
│   │   ├── memories.json          (JSON storage)
│   │   ├── embeddings.faiss       (Vector storage)
│   │   └── mem_agent/             (Mem-agent storage)
│   │       ├── memories/
│   │       └── entities/
│   └── ...
├── processed.json                  (Message tracking)
└── user_settings_overrides.json   (User settings)

knowledge_base/
├── topics/                         (User topics)
├── .git/                          (Git repository)
└── README.md

logs/
├── bot.log                        (Bot logs)
├── memory_http.log               (MCP server logs)
└── memory_http_errors.log        (MCP errors)
```

## Scaling Considerations

### Horizontal Scaling

**Bot Service:**
- Can run multiple instances with different bot tokens
- Each instance is independent
- Share MCP server via network

**MCP Server:**
- Stateless (except file storage)
- Can scale horizontally with shared volume
- Load balance with nginx/traefik

**vLLM Server:**
- Can run multiple instances on different GPUs
- Use separate model copies or shared cache
- Load balance requests

### Vertical Scaling

**Bot Service:**
- CPU-bound for message processing
- Memory scales with context size
- 1-2 CPU cores, 2-4GB RAM recommended

**MCP Server:**
- CPU-bound for JSON/vector modes
- Memory scales with embeddings cache
- 2-4 CPU cores, 4-8GB RAM recommended

**vLLM Server:**
- GPU-bound
- VRAM depends on model size:
  - Small models (1-3B): 6-12GB VRAM
  - Medium models (7-13B): 16-24GB VRAM
  - Large models (30B+): 40GB+ VRAM

## Resource Requirements

### Minimal Setup (JSON mode)
- **CPU:** 2 cores
- **RAM:** 4GB
- **Storage:** 10GB
- **GPU:** None

### Standard Setup (Vector mode)
- **CPU:** 4 cores
- **RAM:** 8GB
- **Storage:** 20GB
- **GPU:** None

### Full Setup (Mem-agent mode)
- **CPU:** 8 cores
- **RAM:** 16GB
- **Storage:** 50GB (for model cache)
- **GPU:** 8GB+ VRAM

## Health Checks

All services include health checks for container orchestration:

**Bot:**
- Check: Python process running
- Interval: 30s
- Timeout: 10s

**MCP Server:**
- Check: HTTP GET /health
- Interval: 30s
- Timeout: 10s
- Start period: 30s

**vLLM Server:**
- Check: HTTP GET /health
- Interval: 30s
- Timeout: 10s
- Start period: 120s (model loading)

## Security

### Network Isolation
- All services communicate via internal network
- No external ports exposed by default
- Optional port exposure for debugging

### Credentials Management
- Sensitive data in `.env` file (not committed)
- Bot token required for authentication
- Optional API keys for LLM services

### User Isolation
- Per-user memory storage
- User ID-based directory structure
- File system permissions

### Container Security
- Non-root user in containers (TODO)
- Read-only file systems where possible (TODO)
- Minimal base images
- Regular security updates

## Monitoring and Debugging

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f bot
docker-compose logs -f mcp-http-server
docker-compose logs -f vllm-server
```

### Health Checks
```bash
# Service status
docker-compose ps

# Manual health checks
curl http://localhost:8765/health
curl http://localhost:8001/health
```

### Resource Usage
```bash
# Container stats
docker stats

# GPU usage (if available)
nvidia-smi
```

## Troubleshooting

See [README.Docker.md](README.Docker.md) for detailed troubleshooting guide.

## Future Enhancements

1. **Kubernetes Support:**
   - Helm charts
   - StatefulSets for vLLM
   - Horizontal Pod Autoscaling

2. **Observability:**
   - Prometheus metrics
   - Grafana dashboards
   - OpenTelemetry tracing

3. **High Availability:**
   - Redis for distributed state
   - PostgreSQL for structured data
   - Multiple vLLM replicas with load balancing

4. **CI/CD:**
   - Automated builds
   - Security scanning
   - Multi-arch images
