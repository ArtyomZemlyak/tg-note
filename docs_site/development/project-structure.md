# Project Structure

A quick map of the repository so you know where to look when adding or reviewing
features.

## Top-level layout

- `src/` — application code
  - `agents/` — agent implementations (stub, autonomous, Qwen Code CLI) and factories
  - `bot/` — Telegram bot handlers, keyboards, and state management
  - `core/` — dependency injection container and shared base services
  - `knowledge_base/` — KB file/commit orchestration and validation
  - `mcp/` — MCP hub client, registry, memory agent helpers, vector search tools
  - `processor/` — message/file parsing pipeline
  - `prompts/` — runtime prompt helpers
  - `services/` — cross-cutting services (git, storage paths, validation)
  - `tracker/` — processing tracker and metrics
- `config/` — typed settings, constants, logging config, and prompt templates
- `config.example.yaml` — sample runtime configuration
- `docs_site/` — MkDocs sources (what you are reading)
- `tests/` — unit/integration tests covering agents, MCP, KB operations, and bot flows
- `scripts/` — helper scripts for MCP, mem-agent, and validation utilities
- `docker/` and `docker-compose*.yml` — container setups (bot, vector search, docling MCP)
- `knowledge_base/` — sample KB content used by tests and docs
- `examples/` — minimal usage examples and agent traces
- `mkdocs.yml` — documentation site configuration
- `requirements-docs.txt` — dependencies for building documentation
- `logs/` — runtime logs (git-ignored)

## Entrypoints

- CLI: `poetry run tg-note` (from `main.py` via the `tg-note` console script)
- Tests: `pytest tests -q` (see `development/testing.md` for fixtures and options)
- Docs: `mkdocs serve` for local preview, `mkdocs build` for CI parity

## Configuration

- Primary runtime configuration lives in `config.yaml` (copied from `config.example.yaml`)
- Sensitive tokens live in `.env` (Telegram bot token, API keys, Git tokens)
- Prompt templates used by agents are stored under `config/prompts/`

## Data and storage

- KB files live under `knowledge_base/` by default; Git settings control commits/pushes
- MCP server JSON configs are stored under `data/mcp_servers/` (managed via bot commands)
