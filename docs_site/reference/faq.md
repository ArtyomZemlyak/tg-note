# FAQ

## The bot does not start. What should I check first?

- `TELEGRAM_BOT_TOKEN` is set in `.env` or the environment
- `config.yaml` exists (copied from `config.example.yaml`)
- Python version is 3.11–3.12; run inside the Poetry environment
- Run `poetry run tg-note` to ensure dependencies are loaded

## How do I switch agents?

Set `AGENT_TYPE` in `config.yaml` to `stub`, `autonomous`, or `qwen_code_cli`.
Restart the bot after changing the value. See [Agent System](../agents/overview.md).

## Where are MCP servers configured?

Through the bot commands (`/addmcpserver`, `/listmcpservers`, `/enablemcp`, etc.).
Each server is stored as JSON under `data/mcp_servers/`. See
[MCP Server Management](../user-guide/mcp-server-management.md).

## How do I enable vector search?

Set `VECTOR_SEARCH_ENABLED: true` in `config.yaml`. For remote Qdrant, also set
`VECTOR_SEARCH_PROVIDER: qdrant_remote` and provide the Qdrant URL/API key. See
[Vector Search Overview](../architecture/vector-search-overview.md).

## Where are Git credentials stored?

Use the secure credentials flow in Telegram (see
[Secure Git Credentials](../user-guide/secure-git-credentials.md)). Tokens are
encrypted per user; do not hardcode them in `config.yaml`.

## How do I run the bot without Git?

Set `KB_GIT_ENABLED: false` in `config.yaml`. Notes will be written locally under
`knowledge_base/` without committing or pushing.

## Tests are slow. How can I iterate faster?

Use targeted runs: `pytest tests -k "<pattern>" -q`. Many tests have focused
scopes (e.g., MCP, vector search) so you can run only what changed.

## How do I preview docs locally?

Install docs deps (`pip install -r requirements-docs.txt` or `poetry install`),
then run `mkdocs serve` for live preview or `mkdocs build` to mirror CI.

## Can I run tg-note as a library?

Yes, but prefer the console script. If embedding, create the service container
from `src.core.service_container.create_service_container()` and manage the
Telegram bot lifecycle manually.
