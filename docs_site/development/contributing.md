# Contributing

Thank you for improving tg-note! This guide summarizes the expectations for new
changes and reviews.

## Contribution workflow

1. **Create a branch** from `main`
2. **Set up tooling**: `poetry install`, `pre-commit install`
3. **Develop with tests**: add/adjust tests in `tests/` to cover behavior
4. **Format & lint**: run Black/isort and `pre-commit run --all-files`
5. **Docs**: update `docs_site/` when you change flows, commands, or config
6. **Verify**: `pytest tests -q` (plus focused runs with `-k`) and `mkdocs build`
7. **Open a PR**: describe the change, risks, and test coverage

## Coding standards

- Python 3.11–3.12; keep code compatible with both
- Use `AICODE-NOTE`, `AICODE-TODO`, `AICODE-ASK` for meta comments when needed
- Keep functions small; prefer explicit configuration over implicit globals
- Avoid committing secrets or personal access tokens; use `.env` locally

## Testing expectations

- Cover new branches in agents, MCP, KB sync, and bot handlers
- Use existing fixtures where possible; prefer fast tests over long integrations
- If behavior depends on vector search or MCP, mark tests appropriately or keep
  them isolated behind feature flags

## Documentation expectations

- Align user-facing docs with the button-first UX (`/start`, `/kb`, interactive
  menus) and flag any command-only flows as legacy
- Update reference pages when adding settings, commands, or APIs
- Keep examples executable and copy-paste friendly

## Review checklist

- Code formatted, imports sorted
- Tests added/updated and passing locally
- Docs updated where behavior changes
- No stray debug logs, no committed credentials, no large binaries
