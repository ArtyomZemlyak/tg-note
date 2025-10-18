# Troubleshooting

## Tests: `pytest: command not found`

Some environments (e.g., system Python 3.13) install packages into user site without exposing console scripts on PATH. Use the module form instead:

```bash
python -m pytest
```

Alternatively, ensure your virtual environment is active so `pytest` is on PATH.

## Git push: authentication errors

If pushing to `https://github.com/...` fails with username/password errors:

- Switch to SSH remote: `git remote set-url origin git@github.com:user/repo.git`
- Or configure a credential helper: `git config credential.helper store`
- Or use a personal access token (PAT) in the HTTPS URL.

`GitOperations` detects HTTPS and logs guidance. It also avoids double credential injection.

## Missing optional dependencies

Vector search and some agents require extras. Install as needed:

```bash
pip install -e ".[vector-search]"
pip install -e ".[mcp]"
pip install -e ".[mem-agent]"
```
