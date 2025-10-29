# Dependencies Separation

This project has been refactored to separate dependencies between the MCP Hub server and Bot server for better containerization and deployment.

## Architecture

- **MCP Hub Server** (`Dockerfile.hub`): Lightweight server providing MCP protocol gateway, memory tools, and vector search
- **Bot Server** (`Dockerfile.bot`): Full-featured Telegram bot with document processing, Git operations, and agent system

## Requirements Files

### `requirements-mcp-hub.txt`
Dependencies for the MCP Hub server:
- Core: `pydantic`, `pydantic-settings`, `PyYAML`, `loguru`
- MCP Protocol: `fastmcp`
- Memory Agent: `aiofiles`, `jinja2`, `pygments`, `black` (lightweight)
- Vector Search: `sentence-transformers`, `faiss-cpu`, `qdrant-client` (optional)
- HTTP: `aiohttp`, `requests`
- File operations: `filelock`

### `requirements-bot.txt`
Dependencies for the Bot server:
- Core: `pydantic`, `pydantic-settings`, `PyYAML`, `loguru`
- Telegram: `pyTelegramBotAPI`
- Git: `GitPython`
- Agent system: `qwen-agent`
- LLM APIs: `openai`
- Document processing: `docling`
- HuggingFace: `huggingface-hub`
- Encryption: `cryptography`
- Vector search: `qdrant-client`
- File operations: `filelock`
- HTTP: `aiohttp`, `requests`

## Docker Images

### MCP Hub Server
```bash
# Build MCP Hub image
docker build -f Dockerfile.hub -t tg-note-hub .

# Run MCP Hub
docker run -p 8765:8765 tg-note-hub
```

### Bot Server
```bash
# Build Bot image
docker build -f Dockerfile.bot -t tg-note-bot .

# Run Bot (requires MCP Hub running)
docker run --env MCP_HUB_URL=http://mcp-hub:8765/sse tg-note-bot
```

## Docker Compose

All docker-compose files automatically use the appropriate Dockerfiles:
- `docker-compose.yml` - Full stack with vLLM
- `docker-compose.simple.yml` - Simplified with JSON storage
- `docker-compose.vector.yml` - With vector search support
- `docker-compose.sglang.yml` - With SGLang backend

## Development

For local development, install all dependencies:
```bash
pip install -e .
```

For production deployment, use the separate requirements files as shown in the Dockerfiles.

## Benefits

1. **Smaller Images**: MCP Hub image is lightweight (no Telegram, Git, or heavy ML dependencies)
2. **Better Separation**: Each service only includes what it needs
3. **Faster Builds**: Reduced dependency conflicts and faster CI/CD
4. **Security**: Smaller attack surface for each container
5. **Scalability**: Services can be scaled independently