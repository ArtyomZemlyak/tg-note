# MCP setup for containerized deployments

Guide for configuring MCP (Model Context Protocol) servers for Docker deployments.

## Overview

When running in Docker, the MCP Hub runs as a separate container (`mcp-hub`) and interacts with:
- Bot container — Telegram bot with Python MCP clients
- Qwen CLI — runs inside the bot container or on the host
- Other LLMs — local inference backends (vLLM, SGLang, LM Studio, etc.)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Docker environment                                          │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │     Bot      │ HTTP/SSE│   MCP Hub    │                  │
│  │              │────────▶│     :8765    │                  │
│  │  - Qwen CLI  │         │               │                  │
│  │  - Python    │         │  - Memory     │                  │
│  └──────────────┘         │  - Registry   │                  │
│                           └──────────────┘                  │
│                                  ▲                          │
│                                  │                          │
│                                  │ vLLM/SGLang              │
│                           ┌──────────────┐                  │
│                           │    vLLM      │                  │
│                           │   server     │                  │
│                           │    :8001     │                  │
│                           └──────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ HTTP :8765
                                  │
                           ┌──────────────┐
                           │    Host      │
                           │   machine    │
                           │              │
                           │  - Qwen CLI  │
                           │  - LM Studio │
                           │  - Cursor    │
                           └──────────────┘
```

## Networking

### Docker internal network

Services communicate by service names inside Docker Compose network:

```yaml
# docker-compose.yml
services:
  mcp-hub:
    ports:
      - "8765:8765"  # Exposed to host

  bot:
    environment:
      - MCP_HUB_URL=http://mcp-hub:8765/sse  # Inside Docker
```

**Internal URLs:**
- MCP Hub: `http://mcp-hub:8765/sse`
- vLLM: `http://vllm-server:8001`

### Access from host

From host use localhost:

**Host URLs:**
- MCP Hub: `http://127.0.0.1:8765/sse`
- vLLM: `http://127.0.0.1:8001`

## MCP configuration files

### Auto-generated configurations

The system automatically generates configurations for different clients:

1. Qwen CLI — `~/.qwen/settings.json`
2. Python clients — `data/mcp_servers/mcp-hub.json`
3. Cursor — `.mcp.json` (project root)
4. Claude Desktop — `~/Library/Application Support/Claude/claude_desktop_config.json`
5. LM Studio — `~/.lmstudio/mcp_config.json`

### Environment detection

Config generators automatically detect environment:

Detection order:
1. Check environment variable `MCP_HUB_URL`
2. Default to localhost (host environment)

## Scenarios

### 1. Qwen CLI in bot container

When Qwen CLI runs inside the bot container:

**Environment:**
```bash
MCP_HUB_URL=http://mcp-hub:8765/sse
```

**Generated `~/.qwen/settings.json`:**
```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://mcp-hub:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "MCP Hub - Unified MCP gateway"
    }
  },
  "allowMCPServers": ["mcp-hub"]
}
```

### 2. Qwen CLI on host

When Qwen CLI runs on the host:

**Generated `~/.qwen/settings.json`:**
```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "MCP Hub - Unified MCP gateway"
    }
  },
  "allowMCPServers": ["mcp-hub"]
}
```

## Manual setup

### Using universal configuration generator

Generate configurations for all supported clients:

```bash
# Inside container
python -m src.mcp.universal_config_generator --all

# On host
python -m src.mcp.universal_config_generator --all --url http://127.0.0.1:8765/sse
```

Generate configuration for a specific client:

```bash
# Qwen CLI only
python -m src.mcp.universal_config_generator --qwen

# Cursor only
python -m src.mcp.universal_config_generator --cursor

# LM Studio only
python -m src.mcp.universal_config_generator --lmstudio

# Data directory (Python clients)
python -m src.mcp.universal_config_generator --data
```

## Authentication and security

### API keys in Docker

API keys are passed via environment variables and automatically available to Qwen CLI:

```yaml
# docker-compose.yml
services:
  bot:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL}
      - QWEN_API_KEY=${QWEN_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

### Environment variables

In `.env`:

```bash
# API keys
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
QWEN_API_KEY=...
ANTHROPIC_API_KEY=...

# MCP configuration (optional — auto-detected if not provided)
MCP_HUB_URL=http://mcp-hub:8765/sse
```

### Running Qwen CLI in container

```bash
# Enter bot container
docker exec -it tg-note-bot bash

# Qwen CLI will use environment variables automatically
qwen "Analyze this code and save insights to memory"

# MCP Hub available at http://mcp-hub:8765/sse
```

### Running Qwen CLI on host

On host set environment variables:

```bash
# Export API keys
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1

# Run qwen CLI
qwen "Analyze this code and save insights to memory"

# MCP Hub available at http://127.0.0.1:8765/sse
```

## Auth updates

When rotating API keys:

1. Update `.env`:
   ```bash
   vim .env
   # Update OPENAI_API_KEY=...
   ```

2. Restart containers:
   ```bash
   docker-compose restart bot
   ```

3. Check MCP health:
   ```bash
   curl http://127.0.0.1:8765/health
   ```

No need to regenerate MCP configs — authentication is handled via environment variables.

## Troubleshooting

### MCP Hub is unreachable

**From bot container:**
```bash
docker exec -it tg-note-bot bash
curl http://mcp-hub:8765/health
```

**From host:**
```bash
curl http://127.0.0.1:8765/health
```

### Inspect MCP configuration

**Qwen CLI config:**
```bash
cat ~/.qwen/settings.json
```

**Python client config:**
```bash
cat data/mcp_servers/mcp-hub.json
```

### Regenerate configs

**Inside bot container:**
```bash
docker exec -it tg-note-bot python -m src.mcp.universal_config_generator --all
```

**On host:**
```bash
python -m src.mcp.universal_config_generator --all --url http://127.0.0.1:8765/sse
```

### Logs

**MCP Hub logs:**
```bash
docker logs tg-note-hub
# or
tail -f logs/mcp_hub.log
```

**Bot logs:**
```bash
docker logs tg-note-bot
# or
tail -f logs/bot.log
```

## FAQ

### What should MCP JSON configs look like?

**Qwen CLI (`~/.qwen/settings.json`):**
```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://mcp-hub:8765/sse",  // In Docker
      // or
      "url": "http://127.0.0.1:8765/sse", // On host
      "timeout": 10000,
      "trust": true
    }
  },
  "allowMCPServers": ["mcp-hub"]
}
```

**Generic MCP servers (`data/mcp_servers/mcp-hub.json`):**
```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://mcp-hub:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "MCP Hub - Memory tools"
    }
  }
}
```

### How does Qwen CLI run in containers?

1. Qwen CLI is installed in bot container (via Dockerfile.bot)
2. Environment variables are passed via docker-compose.yml:
   ```yaml
   bot:
     environment:
       - OPENAI_API_KEY=${OPENAI_API_KEY}
       - MCP_HUB_URL=http://mcp-hub:8765/sse
   ```
3. MCP config is generated automatically on bot startup
4. Qwen CLI uses generated config from `~/.qwen/settings.json`

### How does authentication work?

1. API keys are stored in `.env` — never in MCP configs
2. Docker passes environment variables to containers
3. Qwen CLI reads keys from environment automatically
4. When keys change — just restart containers, no config changes required

### Access for other local LLMs

For other local LLMs (e.g., LM Studio, Ollama with MCP support):

```bash
# Generate configs for all clients
python -m src.mcp.universal_config_generator --all --url http://127.0.0.1:8765/sse

# Or for a specific client
python -m src.mcp.universal_config_generator --lmstudio --url http://127.0.0.1:8765/sse
```

This creates configuration files with correct URLs for host access.

## Best practices

1. Use environment variables — store secrets in `.env`, never in configs
2. Environment detection — let the system detect Docker vs host
3. Regenerate on deploy — MCP configs are auto-generated on container start
4. Consistent ports — keep MCP Hub on port 8765
5. Health checks — use `/health` endpoint to verify MCP Hub
