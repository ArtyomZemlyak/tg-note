# 🤖 AGENTS.md - MANDATORY INSTRUCTIONS FOR ALL AI AGENTS

## ⚠️ CRITICAL: READ THIS FILE FIRST BEFORE ANY WORK

This file contains **mandatory** instructions that **MUST** be followed by all AI coding agents (Cursor, Copilot, Claude, GPT, etc.).

---

## 📋 PRE-WORK CHECKLIST (MUST DO BEFORE STARTING)

**Every agent MUST complete this checklist before making any code changes:**

1. **✅ READ THIS FILE COMPLETELY** - You are reading it now, good!
2. **✅ ENSURE DEPENDENCIES ARE INSTALLED**:
   ```bash
   # Check if pre-commit is installed
   which pre-commit || pip install pre-commit black isort pytest pytest-asyncio

   # Install pre-commit hooks (run once)
   export PATH="/home/ubuntu/.local/bin:$PATH"
   pre-commit install
   ```
3. **✅ UNDERSTAND PROJECT STRUCTURE** - Check `docs_site/` for architecture
4. **✅ VERIFY TESTS EXIST** - Check `tests/` directory for related test files

---

## 🔧 DEVELOPMENT WORKFLOW (MANDATORY)

### 1. **Code Formatting (ALWAYS)**
- **USE Python Black formatter** with line-length=100
- **USE isort** for import sorting
- Run before committing:
  ```bash
  export PATH="/home/ubuntu/.local/bin:$PATH"
  black --line-length=100 <changed_files>
  isort --profile=black --line-length=100 <changed_files>
  ```

### 2. **Special Code Comments (USE THESE)**
You **MUST** use these comment types when appropriate:
- `# AICODE-NOTE:` - Important notes for AI agents and developers
- `# AICODE-TODO:` - Tasks for AI agents to handle
- `# AICODE-ASK:` - Questions to ask the user (then record answer as AICODE-NOTE)

**Example:**
```python
# AICODE-NOTE: This function is called by the Telegram bot handler
# AICODE-TODO: Add caching to improve performance
# AICODE-ASK: Should we use Redis or in-memory cache?
```

### 3. **Documentation (AFTER CODE CHANGES)**
- **✅ UPDATE** relevant docs in `docs_site/` after implementing new features
- **✅ UPDATE** docstrings in the modified code
- **❌ DO NOT** create standalone summary files (`.md` or `.txt`) in repo root

### 4. **Testing (AFTER CODE CHANGES)**
- **✅ CHECK** if tests exist for modified code in `tests/`
- **✅ UPDATE** existing tests if behavior changed
- **✅ ADD** new tests for new features
- **✅ RUN** tests to verify nothing broke:
  ```bash
  export PATH="/home/ubuntu/.local/bin:$PATH"
  pytest tests/ -v
  ```

### 5. **Pre-commit Hooks (BEFORE GIT COMMIT)**
**THIS IS MANDATORY - NO EXCUSES!**

Before **EVERY** git commit, you **MUST** run:
```bash
export PATH="/home/ubuntu/.local/bin:$PATH"
pre-commit run --all-files
```

**If pre-commit is not installed:**
```bash
pip install pre-commit black isort
pre-commit install
```

**What pre-commit does:**
- Formats code with Black
- Sorts imports with isort
- Checks YAML/JSON/TOML syntax
- Fixes trailing whitespace
- Fixes line endings
- Prevents large files from being committed

---

## ❌ FORBIDDEN ACTIONS

**NEVER do these:**
1. ❌ Commit code without running pre-commit
2. ❌ Create summary `.md` or `.txt` files in repo root
3. ❌ Ignore Black formatting rules
4. ❌ Skip updating tests when changing code
5. ❌ Ignore AICODE-TODO or AICODE-ASK comments
6. ❌ Say "pre-commit is not available" - INSTALL IT!

---

## 🎯 QUICK REFERENCE: COMPLETE WORKFLOW

```bash
# 1. Ensure tools are installed
export PATH="/home/ubuntu/.local/bin:$PATH"
which pre-commit || pip install pre-commit black isort pytest pytest-asyncio
pre-commit install

# 2. Make your code changes
# ... edit files ...

# 3. Format code
black --line-length=100 <changed_files>
isort --profile=black --line-length=100 <changed_files>

# 4. Update tests
# ... edit test files ...

# 5. Run tests
pytest tests/ -v

# 6. Update documentation
# ... edit docs_site/ if needed ...

# 7. Run pre-commit (MANDATORY)
pre-commit run --all-files

# 8. Commit
git add <files>
git commit -m "Your commit message"
```

---

## 📚 Additional Resources

- **Architecture**: `docs_site/architecture/`
- **Development Guide**: `docs_site/development/`
- **API Reference**: `docs_site/reference/`
- **Tests**: `tests/`
- **Pre-commit config**: `.pre-commit-config.yaml`
- **Python config**: `pyproject.toml`

---

## 🤝 FOR THE USER

If an AI agent tells you:
- "pre-commit is not available" → They're wrong, they can install it
- "I can't run tests" → They can, they just need to install pytest
- "Should I update docs?" → YES, ALWAYS!

**Show them this file and tell them to follow the instructions!**
