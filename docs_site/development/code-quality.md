# Code Quality

tg-note uses a simple, enforceable toolchain: Black + isort + pytest, wrapped by
pre-commit. Follow these rules for every change.

## Formatting and imports

- **Black** with `--line-length=100`
- **isort** with `--profile=black --line-length=100 --skip-gitignore`
- Run them on changed files before committing:

```bash
black --line-length=100 <files>
isort --profile=black --line-length=100 <files>
```

## Pre-commit hooks (mandatory before commits)

```bash
pre-commit install        # once per machine
pre-commit run --all-files
```

Hooks cover trailing whitespace, EOF fixers, YAML/JSON/TOML checks, Black, and
isort. Commits should only be made after hooks pass.

## Tests

- Run `pytest tests -q` for a fast sweep
- Scope runs with `pytest tests -k "<pattern>"` when iterating
- Add or update tests alongside behavior changes

## Optional checks

- mypy config exists in `pyproject.toml`; run `mypy src` if adding type-heavy
  changes
- Use `mkdocs build` after editing docs to catch broken links or bad front matter

## Comments for AI agents

When adding meta-notes for automation, use the project-specific prefixes:
`AICODE-NOTE`, `AICODE-TODO`, `AICODE-ASK`.
