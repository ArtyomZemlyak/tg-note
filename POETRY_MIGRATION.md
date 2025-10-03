# Poetry Migration Guide

## ✅ Completed Migration

This project has been successfully migrated from `pip` + `requirements.txt` to **Poetry** for dependency management.

## 🎯 What Changed

### Files Added
- ✅ `pyproject.toml` - Poetry configuration and dependencies
- ✅ `poetry.lock` - Locked dependency versions

### Files Removed
- ❌ `requirements.txt` - Replaced by `pyproject.toml`

### Documentation Updated
- ✅ `README.md` - Updated installation and usage instructions
- ✅ `docs/QUICK_START.md` - Updated with Poetry commands

## 📦 New Workflow

### Installation

**Before (pip):**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**After (Poetry):**
```bash
curl -sSL https://install.python-poetry.org | python3 -
poetry install
```

### Running the Bot

**Before:**
```bash
python main.py
```

**After:**
```bash
poetry run python main.py
# or
poetry shell
python main.py
```

### Running Tests

**Before:**
```bash
pytest
pytest --cov=src
```

**After:**
```bash
poetry run pytest
poetry run pytest --cov=src
```

### Development Tools

**Before:**
```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

**After:**
```bash
poetry run black src/ tests/
poetry run flake8 src/ tests/
poetry run mypy src/
```

## 🔧 Managing Dependencies

### Add New Dependency
```bash
# Production dependency
poetry add package-name

# Development dependency
poetry add --group dev package-name

# Specific version
poetry add package-name==1.2.3
```

### Update Dependencies
```bash
# Update all dependencies
poetry update

# Update specific package
poetry update package-name

# Show outdated packages
poetry show --outdated
```

### Remove Dependency
```bash
poetry remove package-name
```

## 📊 Benefits of Poetry

1. **Dependency Resolution**: Poetry ensures compatible versions
2. **Lock File**: `poetry.lock` guarantees reproducible builds
3. **Virtual Environment**: Automatically managed by Poetry
4. **Build System**: Built-in packaging and publishing
5. **Dev Dependencies**: Separate production and development deps
6. **Modern Standards**: Uses PEP 621 (pyproject.toml)

## 🔍 Current Configuration

### Production Dependencies
- pydantic 2.10.4
- pydantic-settings 2.7.0
- PyYAML 6.0.1
- pyTelegramBotAPI 4.14.0
- GitPython 3.1.40
- filelock 3.13.1
- qwen-agent 0.0.31
- aiohttp 3.9.1
- requests 2.31.0

### Development Dependencies
- pytest 7.4.3
- pytest-asyncio 0.21.1
- pytest-cov 4.1.0
- black 23.12.1
- flake8 6.1.0
- mypy 1.7.1

## 📝 Common Commands

```bash
# Install all dependencies
poetry install

# Activate virtual environment
poetry shell

# Show dependency tree
poetry show --tree

# Validate configuration
poetry check

# Export requirements.txt (if needed for compatibility)
poetry export -f requirements.txt --output requirements.txt

# Update Poetry itself
poetry self update
```

## 🐛 Troubleshooting

### Poetry Not Found
```bash
# Add Poetry to PATH
export PATH="/home/ubuntu/.local/bin:$PATH"

# Or install with pipx
pipx install poetry
```

### Clear Cache
```bash
poetry cache clear --all pypi
```

### Recreate Virtual Environment
```bash
poetry env remove python
poetry install
```

### Check Virtual Environment Location
```bash
poetry env info
```

## 🚀 CI/CD Integration

### GitHub Actions Example
```yaml
- name: Install Poetry
  run: pipx install poetry

- name: Install dependencies
  run: poetry install

- name: Run tests
  run: poetry run pytest
```

### Docker Example
```dockerfile
FROM python:3.11-slim

# Install Poetry
RUN pip install poetry

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY . .

# Install dependencies
RUN poetry install --no-root

# Run application
CMD ["poetry", "run", "python", "main.py"]
```

## 📚 Resources

- [Poetry Documentation](https://python-poetry.org/docs/)
- [PEP 621 - pyproject.toml metadata](https://peps.python.org/pep-0621/)
- [Poetry GitHub](https://github.com/python-poetry/poetry)

## ✨ Next Steps

1. ✅ All dependencies migrated
2. ✅ Documentation updated
3. ✅ Poetry lock file generated
4. ✅ Configuration validated

The project is now ready to use with Poetry! 🎉
