# MCP Configuration for Containerized Deployments

This guide explains how to configure MCP (Model Context Protocol) servers for containerized deployments with Docker.

## Overview

When running in Docker, MCP Hub is deployed as a separate container (`mcp-hub`) that communicates with:
- **Bot container** - Main Telegram bot using Python MCP clients
- **Qwen CLI** - Running inside bot container or on host machine
- **Other LLMs** - Locally deployed LLMs (vLLM, SGLang, LM Studio, etc.)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Docker Environment                                          │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │  Bot         │ HTTP/SSE│  MCP Hub     │                │
│  │  Container   │────────▶│  Container   │                │
│  │              │         │  :8765       │                │
│  │  - Qwen CLI  │         │              │                │
│  │  - Python    │         │  - Memory    │                │
│  └──────────────┘         │  - Registry  │                │
│                           └──────────────┘                │
│                                  ▲                          │
│                                  │                          │
│                                  │ vLLM/SGLang              │
│                           ┌──────────────┐                │
│                           │  vLLM        │                │
│                           │  Server      │                │
│                           │  :8001       │                │
│                           └──────────────┘                │
└─────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ HTTP :8765
                                  │
                           ┌──────────────┐
                           │  Host        │
                           │  Machine     │
                           │              │
                           │  - Qwen CLI  │
                           │  - LM Studio │
                           │  - Cursor    │
                           └──────────────┘
```

## Network Configuration

### Docker Internal Network

Services within Docker Compose network communicate using service names:

```yaml
# docker-compose.yml
services:
  mcp-hub:
    ports:
      - "8765:8765"  # Exposed to host

  bot:
    environment:
      - MCP_HUB_URL=http://mcp-hub:8765/sse  # Docker internal
```

**Internal URLs:**
- MCP Hub: `http://mcp-hub:8765/sse`
- vLLM: `http://vllm-server:8001`

### Host Machine Access

From the host machine, use localhost:

**Host URLs:**
- MCP Hub: `http://127.0.0.1:8765/sse`
- vLLM: `http://127.0.0.1:8001`

## MCP Configuration Files

### Auto-Generated Configurations

The system automatically generates MCP configs for different clients:

1. **Qwen CLI** - `~/.qwen/settings.json`
2. **Python Clients** - `data/mcp_servers/mcp-hub.json`
3. **Cursor** - `.mcp.json` (project root)
4. **Claude Desktop** - `~/Library/Application Support/Claude/claude_desktop_config.json`
5. **LM Studio** - `~/.lmstudio/mcp_config.json`

### Environment Detection

The config generators automatically detect the environment:

```python
# Auto-detection logic:
1. Check for /.dockerenv file (Docker container)
2. Check MCP_HUB_URL environment variable
3. Check /proc/1/cgroup for docker
4. Default to localhost (host environment)
```

## Configuration for Different Scenarios

### 1. Qwen CLI in Bot Container

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

### 2. Qwen CLI on Host Machine

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

### 3. LM Studio on Host

**Generated `~/.lmstudio/mcp_config.json`:**
```json
{
  "mcp_servers": {
    "mcp-hub": {
      "transport": "http",
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "enabled": true,
      "description": "MCP Hub - Memory and tool gateway"
    }
  }
}
```

### 4. Python MCP Clients

**Generated `data/mcp_servers/mcp-hub.json`:**
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

## Manual Configuration

### Using Universal Config Generator

Generate configs for all supported clients:

```bash
# Inside container
python -m src.mcp.universal_config_generator --all

# On host machine
python -m src.mcp.universal_config_generator --all --url http://127.0.0.1:8765/sse
```

Generate config for specific client:

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

### Using Qwen Config Generator

For Qwen CLI specifically:

```bash
# Auto-detect environment
python -m src.mcp.qwen_config_generator --http

# Explicit URL for Docker
python -m src.mcp.qwen_config_generator --http --url http://mcp-hub:8765/sse

# Explicit URL for host
python -m src.mcp.qwen_config_generator --http --url http://127.0.0.1:8765/sse
```

## Authentication and Security

### API Keys in Docker

API keys are passed through environment variables and automatically available to Qwen CLI:

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

### Environment Variables

In `.env` file:

```bash
# API Keys
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
QWEN_API_KEY=...
ANTHROPIC_API_KEY=...

# MCP Configuration (optional - auto-detected if not set)
MCP_HUB_URL=http://mcp-hub:8765/sse
```

### Running Qwen CLI in Container

Qwen CLI inside the container automatically has access to environment variables:

```bash
# Enter bot container
docker exec -it tg-note-bot bash

# Qwen CLI uses environment variables automatically
qwen "Analyze this code and store insights in memory"

# MCP Hub is accessible via http://mcp-hub:8765/sse
```

### Running Qwen CLI on Host

On the host machine, set environment variables:

```bash
# Export API keys
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1

# Run qwen CLI
qwen "Analyze this code and store insights in memory"

# MCP Hub is accessible via http://127.0.0.1:8765/sse
```

## Updating Authentication

When API keys are rotated:

1. **Update `.env` file:**
   ```bash
   vim .env
   # Update OPENAI_API_KEY=...
   ```

2. **Restart containers:**
   ```bash
   docker-compose restart bot
   ```

3. **Verify MCP access:**
   ```bash
   curl http://127.0.0.1:8765/health
   ```

No need to regenerate MCP configs - authentication is handled separately via environment variables.

## Troubleshooting

### MCP Hub Not Accessible

**From bot container:**
```bash
docker exec -it tg-note-bot bash
curl http://mcp-hub:8765/health
```

**From host:**
```bash
curl http://127.0.0.1:8765/health
```

### Check MCP Configuration

**Qwen CLI config:**
```bash
cat ~/.qwen/settings.json
```

**Python clients config:**
```bash
cat data/mcp_servers/mcp-hub.json
```

### Regenerate Configurations

**Inside bot container:**
```bash
docker exec -it tg-note-bot python -m src.mcp.universal_config_generator --all
```

**On host:**
```bash
python -m src.mcp.universal_config_generator --all --url http://127.0.0.1:8765/sse
```

### Check Logs

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

## Best Practices

1. **Use Environment Variables** - Store all secrets in `.env`, never in config files
2. **Auto-Detection** - Let the system auto-detect Docker vs host environment
3. **Regenerate on Deploy** - MCP configs are auto-generated on container startup
4. **Port Consistency** - Keep MCP Hub on port 8765 for consistency
5. **Health Checks** - Use `/health` endpoint to verify MCP Hub is running
6. **Container Names** - Use consistent service names in docker-compose.yml

## References

- [MCP Configuration Format](../agents/mcp-config-format.md)
- [MCP Tools Documentation](../agents/mcp-tools.md)
- [Qwen CLI Documentation](../agents/qwen-code-cli.md)
- [Docker Deployment](./docker.md)
