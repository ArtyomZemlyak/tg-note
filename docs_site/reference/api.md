# API Documentation

tg-note is primarily a Telegram bot and MCP-enabled agent runner. It does **not**
expose a public REST API. The supported integration surfaces are:

1. **Telegram commands and buttons** — the main user interface (`/start`, `/kb`,
   `/ask`, `/agent`, `/settings`, `/addmcpserver`, etc.). See
   [Bot Commands](../user-guide/bot-commands.md) for the full matrix.
2. **Console entrypoint** — the `tg-note` script (or `python main.py`) starts the
   bot using `config.yaml` and `.env`.
3. **MCP tools** — when `AGENT_ENABLE_MCP` or `AGENT_ENABLE_MCP_MEMORY` is set,
   the bot registers MCP tools (vector search, KB operations, memory agent)
   behind the Model Context Protocol. See [MCP Tools](../agents/mcp-tools.md).

## Console entrypoint

The console script lives at `main.cli_main` and is installed as `tg-note`:

```bash
# From the repo root
export TELEGRAM_BOT_TOKEN=...        # or set in .env
cp config.example.yaml config.yaml   # adjust settings
poetry run tg-note                   # starts the Telegram bot
```

The process is fully async and will:

- Validate `config.yaml` and environment variables
- Initialize the dependency container and Telegram bot
- Auto-start MCP servers (if enabled) and wire vector search
- Keep running until interrupted (Ctrl+C)

## Programmatic usage

If you need to embed tg-note inside another Python process, you can re-use the
service container:

```python
from src.core.service_container import create_service_container

container = create_service_container()
telegram_bot = container.get("telegram_bot")

# Start/stop the bot manually (async context)
await telegram_bot.start()
# ...
await telegram_bot.stop()
```

Use this only if you need tight integration; for normal usage, prefer the
`tg-note` console script.

## Configuration surface

- Runtime settings come from `config.yaml` (pydantic settings) and `.env`
- Agent/MCP toggles: `AGENT_TYPE`, `AGENT_ENABLE_MCP`, `AGENT_ENABLE_MCP_MEMORY`
- Vector search: `VECTOR_SEARCH_ENABLED`, related Qdrant/embedding options
- Git: `KB_GIT_ENABLED`, `KB_GIT_AUTO_PUSH`, `KB_GIT_REMOTE`, `KB_GIT_BRANCH`

Refer to [Configuration Options](configuration.md) for the full list and
environment variable equivalents.
