# Development Overview

This page is a quick orientation for contributors working on tg-note. It links to
the detailed guides in this section and highlights the daily workflow we expect.

## Prerequisites

- Python 3.11–3.12 with Poetry
- Git and a Telegram account for bot testing
- Node.js 20+ (optional, for the `qwen_code_cli` agent)
- Docker + Docker Compose (optional, for vector search/MCP stacks)
- Installed tooling: `pre-commit`, `pytest`, `black`, `isort` (see AGENTS.md)

## Local setup

```bash
git clone https://github.com/ArtyomZemlyak/tg-note.git
cd tg-note

# Install dependencies (add extras as needed)
poetry install
poetry install -E mcp -E mem-agent -E vector-search

# Install hooks once per machine
pre-commit install

# Copy sample configuration
cp config.example.yaml config.yaml
cp .env.example .env
```

## Day-to-day workflow

- Run the bot: `poetry run tg-note` (or `poetry run python main.py`)
- Keep configs in sync: update `config.yaml` and `.env` for your test bot token
- Format before pushing: `black --line-length=100 <files>` and
  `isort --profile=black --line-length=100 <files>`
- Test fast: `pytest tests -q` or focus with `pytest tests -k "<pattern>"`
- Docs: `mkdocs serve` for live preview, `mkdocs build` for CI parity
- Logs: check `logs/` and the bot output for failures; keep an eye on MCP startup

## Where to go next

- Project layout: [Project Structure](project-structure.md)
- Testing matrix and fixtures: [Running Tests](testing.md)
- Formatting and linting rules: [Code Quality](code-quality.md)
- Contribution expectations: [Contributing](contributing.md)
