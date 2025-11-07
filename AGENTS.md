# AI Agent Instructions for tg-note Project

This document provides comprehensive guidance for AI agents working on the tg-note codebase.

## 📋 Project Overview

**tg-note** is a Telegram bot that automatically transforms messages, reposts, and articles into a structured knowledge base using AI agents. It processes content, categorizes it, and saves it as Markdown files in a GitHub-based knowledge base.

### Key Concepts

- **Telegram Bot**: Receives messages from users via Telegram
- **Agent System**: AI agents analyze and structure content (stub, autonomous, qwen_code_cli)
- **Knowledge Base**: Structured Markdown files organized by topics/categories
- **Git Integration**: Automatic commits to GitHub/GitLab repositories
- **MCP Support**: Model Context Protocol for tool integration and memory

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────┐
│  Telegram Bot   │  ← User interface (pyTelegramBotAPI)
│  (handlers.py)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Message Processor│  ← Grouping & parsing (message_aggregator.py, content_parser.py)
│  (aggregator)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent System   │  ← AI analysis (BaseAgent, AutonomousAgent, QwenCodeCLIAgent, StubAgent)
│  (agents/)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Knowledge Base   │  ← Markdown files (manager.py, git_ops.py, repository.py)
│   Manager       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Git Ops       │  ← Version control (auto commit/push)
│ (auto commit)   │
└─────────────────┘
```

### Data Flow

1. **Input**: User sends message/repost to Telegram bot
2. **Aggregation**: Related messages grouped together (30s timeout by default)
3. **Parsing**: Extract text, media, links, generate hash
4. **Deduplication**: Check if already processed (ProcessingTracker)
5. **Agent Processing**: AI analyzes and structures content
6. **KB Storage**: Save as Markdown in appropriate category
7. **Git Commit**: Auto-commit to repository (if enabled)
8. **Notification**: Inform user of completion

---

## 📁 Project Structure

### Core Directories

```
tg-note/
├── config/                    # Configuration and settings
│   ├── settings.py           # Pydantic settings (YAML + .env)
│   ├── agent_prompts.py      # Agent prompts and keywords
│   └── prompts/              # Markdown prompt files
│
├── src/
│   ├── bot/                  # Telegram bot implementation
│   │   ├── handlers.py       # Message/command handlers
│   │   ├── telegram_bot.py   # Main bot class
│   │   └── response_formatter.py  # Format agent responses
│   │
│   ├── agents/               # AI Agent System
│   │   ├── base_agent.py     # Abstract base class (BaseAgent)
│   │   ├── stub_agent.py     # Simple stub for testing
│   │   ├── autonomous_agent.py  # Python agent (OpenAI-compatible)
│   │   ├── qwen_code_cli_agent.py  # Qwen CLI integration
│   │   ├── agent_factory.py  # Factory pattern for agent creation
│   │   ├── agent_registry.py # Registry pattern for extensibility
│   │   ├── llm_connectors/   # LLM API connectors
│   │   │   ├── base_connector.py
│   │   │   └── openai_connector.py
│   │   └── tools/            # Agent tools (web, git, file, etc.)
│   │       ├── base_tool.py
│   │       ├── registry.py
│   │       ├── web_tools.py
│   │       ├── git_tools.py
│   │       ├── file_tools.py
│   │       └── ...
│   │
│   ├── processor/            # Content processing
│   │   ├── message_aggregator.py  # Message grouping
│   │   └── content_parser.py      # Content extraction
│   │
│   ├── knowledge_base/       # KB management
│   │   ├── manager.py        # KB operations
│   │   ├── git_ops.py        # Git operations
│   │   ├── repository.py     # Repo manager
│   │   └── user_settings.py  # Per-user settings
│   │
│   ├── services/             # Business logic services
│   │   ├── agent_task_service.py
│   │   └── ...
│   │
│   ├── core/                 # Core infrastructure
│   │   └── service_container.py  # Dependency injection
│   │
│   ├── mcp/                  # MCP (Model Context Protocol)
│   │   └── ...
│   │
│   └── tracker/              # Processing tracking
│       └── processing_tracker.py  # Deduplication
│
├── tests/                    # Unit tests
├── examples/                 # Example scripts
├── docs_site/                # Documentation (MkDocs)
├── config.yaml               # Main configuration (YAML)
├── .env                      # Credentials (git-ignored)
├── pyproject.toml            # Poetry dependencies
└── main.py                   # Entry point
```

---

## 🤖 Agent System

### Agent Types

The system supports three agent types:

#### 1. **StubAgent** (`stub`)
- **Purpose**: Testing and MVP
- **Language**: Python
- **Features**: Basic categorization, no external dependencies
- **Best for**: Quick testing, development without API keys

#### 2. **AutonomousAgent** (`autonomous`)
- **Purpose**: Full-featured Python agent
- **Language**: Python
- **Features**:
  - OpenAI-compatible API integration
  - MCP tools support (Python MCP client)
  - Built-in tools: web search, git, github, file management
  - Autonomous planning and decision-making
  - Function calling support
- **Best for**: MCP tools, custom tool development, Python-native integration

#### 3. **QwenCodeCLIAgent** (`qwen_code_cli`)
- **Purpose**: Qwen Code CLI integration
- **Language**: Node.js (subprocess)
- **Features**:
  - Full Qwen3-Coder model integration
  - Free tier: 2000 requests/day
  - Vision model support
  - MCP support via Qwen native mechanism
  - Built-in tools: web search, git, github, shell
- **Best for**: Free tier usage, vision support, official Qwen integration

### Agent Architecture

All agents inherit from `BaseAgent`:

```python
class BaseAgent(ABC):
    @abstractmethod
    async def process(self, content: Dict) -> Dict:
        """Process content and return structured output"""
        pass
    
    @abstractmethod
    def validate_input(self, content: Dict) -> bool:
        """Validate input content"""
        pass
```

### Agent Factory Pattern

Agents are created via `AgentFactory` using registry pattern:

```python
# From settings
agent = AgentFactory.from_settings(settings, user_id=user_id)

# Direct creation
agent = AgentFactory.create_agent("autonomous", config={...})
```

### Agent Tools

Tools are organized in `src/agents/tools/`:

- **BaseTool**: Abstract base class for all tools
- **ToolManager**: Registry and executor for tools
- **Tool modules**: Each module contains related tools
  - `web_tools.py`: Web search and browsing
  - `git_tools.py`: Git operations
  - `github_tools.py`: GitHub API operations
  - `file_tools.py`: File read/write operations
  - `folder_tools.py`: Directory operations
  - `kb_reading_tools.py`: Knowledge base reading
  - `vector_search_tools.py`: Vector/semantic search
  - `planning_tools.py`: Task planning

Tools are auto-discovered and registered based on configuration.

---

## 🔧 Code Conventions

### Python Style

- **Formatter**: Black (line length: 100)
- **Python Version**: 3.11+
- **Type Hints**: Use type hints where appropriate
- **Async/Await**: Use async/await for I/O operations

### Special Comments

Use these comment prefixes for AI/agent communication:

- `AICODE-NOTE`: Note for AI agents or other AI+Code systems
- `AICODE-TODO`: Tasks for AI agents or other AI+Code systems
- `AICODE-ASK`: Questions for user (after resolving, write answer as AICODE-NOTE)

Example:
```python
# AICODE-NOTE: This function handles edge cases for empty content
# AICODE-TODO: Add support for video files
# AICODE-ASK: Should we support batch processing?
```

### File Organization

- **No summarization files**: Don't write `.md` or `.txt` files in repo root
- **Documentation**: Update `docs_site/` after new implementations
- **Tests**: Update `tests/` after new implementations
- **Pre-commit**: Use pre-commit hooks after committing

### Import Organization

Follow this order:
1. Standard library
2. Third-party packages
3. Local application imports (`src/`, `config/`)

---

## ⚙️ Configuration System

### Settings Priority

1. **Environment Variables** (highest priority)
2. **`.env` file** (credentials and overrides)
3. **`config.yaml`** (main configuration)
4. **CLI arguments** (future)

### Key Settings

**Telegram Bot:**
- `TELEGRAM_BOT_TOKEN`: Bot token (required, from .env)
- `ALLOWED_USER_IDS`: Comma-separated user IDs (empty = all allowed)

**Agent Configuration:**
- `AGENT_TYPE`: `"stub"`, `"autonomous"`, or `"qwen_code_cli"`
- `AGENT_MODEL`: Model name (e.g., `"gpt-3.5-turbo"`, `"qwen-max"`)
- `AGENT_TIMEOUT`: Timeout in seconds (default: 300)
- `AGENT_ENABLE_*`: Feature flags (web_search, git, github, shell, file_management, mcp, etc.)

**Knowledge Base:**
- `KB_PATH`: Path to knowledge base directory
- `KB_GIT_ENABLED`: Enable Git integration
- `KB_GIT_AUTO_PUSH`: Auto-push after commit
- `KB_TOPICS_ONLY`: Restrict agent to `topics/` folder only

**API Keys** (from `.env`):
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_BASE_URL`: Custom OpenAI endpoint (optional)
- `QWEN_API_KEY`: Qwen API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `GITHUB_TOKEN`: GitHub token

### Per-User Settings

Users can override settings via Telegram commands:
- `/settings`: Interactive settings menu
- `/viewsettings [category]`: View settings
- `/resetsetting <name>`: Reset to default

Settings are stored in `data/user_settings_overrides.json` (encrypted).

---

## 🔐 Security & Credentials

### Git Credentials

- **Per-user encrypted tokens**: Users can add GitHub/GitLab tokens via Telegram
- **Encryption**: AES-128 (Fernet)
- **Storage**: `data/memory/` (encrypted)
- **Commands**: `/settoken`, `/listcredentials`, `/removetoken`

### Access Control

- `ALLOWED_USER_IDS`: Restrict bot access to specific users
- Empty list = allow all users

---

## 🧪 Testing

### Running Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=src --cov-report=html

# Specific test file
poetry run pytest tests/test_tracker.py -v
```

### Test Structure

- Tests in `tests/` directory
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

---

## 📝 Knowledge Base Structure

### Default Structure

```
knowledge_base/
├── topics/
│   ├── ai/
│   │   ├── machine-learning/
│   │   │   └── 2025-01-15-neural-networks.md
│   │   └── models/
│   ├── biology/
│   └── physics/
├── index.md
└── .git/  (if Git enabled)
```

### KB Structure Class

```python
class KBStructure:
    category: str = "general"
    subcategory: Optional[str] = None
    tags: List[str] = []
    custom_path: Optional[str] = None
```

### Agent Response Format

Agents should return structured data:

```python
{
    "markdown": str,      # Formatted markdown content
    "title": str,         # Article title
    "metadata": Dict,     # Article metadata
    "kb_structure": KBStructure  # Where to save
}
```

Agents can include metadata in markdown:

```markdown
```metadata
category: ai
subcategory: machine-learning
tags: gpt, transformer, llm
```
```

---

## 🔌 MCP (Model Context Protocol)

### MCP Support

- **AutonomousAgent**: Uses Python MCP client (`DynamicMCPTool`)
- **QwenCodeCLIAgent**: Uses Qwen's native MCP client (via `.qwen/settings.json`)

### MCP Configuration

For Qwen CLI, create `.qwen/settings.json`:

```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true
    }
  }
}
```

### MCP Tools

MCP tools are available via MCP Hub server (port 8765):
- Memory tools
- Custom integrations
- Server registry

---

## 🚀 Development Workflow

### Setup

```bash
# Install dependencies
poetry install

# Install extras (optional)
poetry install -E mcp -E mem-agent -E vector-search

# Activate shell
poetry shell
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Lint
poetry run flake8 src/ tests/

# Type checking
poetry run mypy src/
```

### Pre-commit

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## 📚 Documentation

### Documentation Structure

- **Location**: `docs_site/`
- **Format**: MkDocs (Markdown)
- **Build**: `mkdocs build`
- **Serve**: `mkdocs serve`

### Documentation Categories

- `getting-started/`: Installation, configuration, quick start
- `user-guide/`: Commands, content management, settings
- `agents/`: Agent system documentation
- `architecture/`: System design and components
- `development/`: Contributing, testing, code quality
- `deployment/`: Production setup, Docker, CI/CD

### Updating Documentation

**Always update documentation after:**
- Adding new features
- Changing configuration options
- Modifying agent behavior
- Adding new tools or capabilities

---

## 🐳 Docker Deployment

### Docker Compose Files

- `docker-compose.yml`: Full stack with vLLM
- `docker-compose.simple.yml`: Lightweight (no GPU)
- `docker-compose.vector.yml`: Vector search stack
- `docker-compose.sglang.yml`: SGLang backend

### Services

- **bot**: Main Telegram bot
- **mcp-hub**: MCP Hub server (port 8765)
- **vllm-server**: LLM inference (GPU required)
- **qdrant**: Vector database (port 6333)
- **infinity**: Embedding service (port 7997)

---

## 🔍 Common Patterns

### Service Container

Dependency injection via `ServiceContainer`:

```python
from src.core.service_container import create_service_container

container = create_service_container()
repo_manager = container.get_repository_manager()
agent_service = container.get_agent_task_service()
```

### Agent Creation

```python
from src.agents import AgentFactory

# From settings
agent = AgentFactory.from_settings(settings, user_id=user_id)

# Process content
result = await agent.process({
    "text": "Content to process",
    "urls": ["https://example.com"],
    "media": []
})
```

### KB Operations

```python
from src.knowledge_base.manager import KnowledgeBaseManager

kb_manager = KnowledgeBaseManager(kb_path)
kb_structure = KBStructure(category="ai", subcategory="ml")
kb_manager.save_note(
    title="Note Title",
    content="# Note Content",
    kb_structure=kb_structure
)
```

### Git Operations

```python
from src.knowledge_base.git_ops import GitOps

git_ops = GitOps(repo_path)
git_ops.commit_and_push(
    message="Add note",
    files=["topics/ai/note.md"]
)
```

---

## ⚠️ Important Notes

### Do's

✅ **DO**:
- Use async/await for I/O operations
- Follow Black formatting (line length: 100)
- Add type hints where appropriate
- Update tests after changes
- Update documentation after new features
- Use AICODE-* comments for AI communication
- Validate input in agent `process()` methods
- Handle errors gracefully

### Don'ts

❌ **DON'T**:
- Write `.md` or `.txt` files in repo root
- Commit credentials or secrets
- Break backward compatibility without good reason
- Skip tests for new features
- Ignore linter errors
- Use blocking I/O in async functions
- Hardcode paths or configuration values

---

## 🆘 Troubleshooting

### Common Issues

**Agent not responding:**
- Check API keys in `.env`
- Verify agent type in `config.yaml`
- Check logs: `logs/bot.log`

**Git operations failing:**
- Verify Git credentials
- Check repository permissions
- Ensure `KB_GIT_ENABLED` is `true`

**MCP tools not working:**
- Verify MCP Hub is running (port 8765)
- Check `.qwen/settings.json` for Qwen CLI
- Ensure `AGENT_ENABLE_MCP` is `true`

**Import errors:**
- Run `poetry install`
- Check Python version (3.11+)
- Verify virtual environment is activated

---

## 📖 Additional Resources

- **Full Documentation**: https://artyomzemlyak.github.io/tg-note/
- **GitHub Repository**: https://github.com/ArtyomZemlyak/tg-note
- **Issue Tracker**: https://github.com/ArtyomZemlyak/tg-note/issues

---

## 🔄 Version Information

- **Python**: 3.11+
- **Project Version**: 0.3.0
- **License**: MIT

---

**Last Updated**: 2025-01-15
