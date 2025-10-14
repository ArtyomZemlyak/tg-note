# tg-note

> **Intelligent Knowledge Base Builder** - Telegram bot that automatically transforms your messages, reposts, and articles into a structured knowledge base using AI agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://artyomzemlyak.github.io/tg-note/)

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Bot](#running-the-bot)
- [Usage](#-usage)
  - [Bot Commands](#bot-commands)
  - [Working with Content](#working-with-content)
- [Agent Types](#-agent-types)
  - [autonomous (Recommended for MCP)](#1-autonomous-recommended-for-mcp-)
  - [qwen_code_cli (Best for Free Tier)](#2-qwen_code_cli-best-for-free-tier-)
  - [stub (Testing Only)](#3-stub-testing-only)
- [Architecture](#-architecture)
  - [System Components](#system-components)
  - [Data Flow](#data-flow)
  - [Project Structure](#project-structure)
- [Configuration Reference](#-configuration-reference)
- [Development](#-development)
  - [Running Tests](#running-tests)
  - [Code Quality](#code-quality)
- [Deployment](#-deployment)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**tg-note** is a Telegram bot that acts as your personal knowledge curator. It receives messages, reposts, and articles through Telegram, analyzes them using AI agent systems, and automatically saves the important information to your GitHub-based knowledge base in structured Markdown format.

Perfect for:

- 📚 Building a personal knowledge base from Telegram channels
- 🔬 Organizing research papers and scientific articles
- 📰 Archiving news and insights from multiple sources
- 🧠 Creating a searchable second brain

---

## ✨ Key Features

- **🤖 AI-Powered Analysis**: Intelligent content categorization and structuring using agent systems
- **📝 Automatic Markdown Generation**: Converts any content into well-formatted Markdown files
- **🗂️ Smart Organization**: Automatic categorization by topics (AI, biology, physics, tech, etc.)
- **🔄 GitHub Integration**: Direct commits to your knowledge base repository
- **👥 Multi-User Support**: Each user can have their own knowledge base
- **📦 Message Grouping**: Intelligently combines related messages into single notes
- **🔍 Deduplication**: Tracks processed messages to avoid duplicates
- **🎯 Flexible Agents**: Choose between stub or Qwen Code CLI agents
- **⚡ Async Architecture**: Fast, non-blocking message processing
- **⚙️ Telegram Settings Management**: Configure bot settings directly via Telegram commands
- **📄 File Format Recognition**: Automatic content extraction from various file formats using Docling (NEW!)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Poetry** (Python dependency manager)
- **Git**
- **Telegram Account**
- **Node.js 20+** (optional, for qwen_code_cli agent)
- **Docker & Docker Compose** (optional, for containerized deployment)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/ArtyomZemlyak/tg-note.git
cd tg-note
```

2. **Install Poetry** (if not already installed)

```bash
curl -sSL https://install.python-poetry.org | python3 -
# or using pipx:
# pipx install poetry
```

3. **Install dependencies**

```bash
poetry install
```

This will automatically create a virtual environment and install all dependencies.

4. **Optional features (extras)**

```bash
# Enable MCP and mem-agent extras (tooling, memory backends)
poetry install -E mcp -E mem-agent

# Vector search capabilities
poetry install -E vector-search
```

Alternatively with pip/pipx:

```bash
# Editable install with extras
pip install -e ".[mcp,mem-agent,vector-search]"

# Or isolate via pipx
pipx install "."
```

### Configuration

1. **Create configuration files**

```bash
# Copy example configuration
cp config.example.yaml config.yaml
```

2. **Get Telegram Bot Token**

- Open [@BotFather](https://t.me/botfather) in Telegram
- Send `/newbot` and follow instructions
- Copy the token provided

3. **Create `.env` file** (for sensitive credentials)

```bash
cat > .env << EOF
# Required: Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional: API keys for agents
# OPENAI_API_KEY=your_openai_key
# OPENAI_BASE_URL=https://api.openai.com/v1  # Optional, for custom endpoints
# QWEN_API_KEY=your_qwen_key
# ANTHROPIC_API_KEY=your_anthropic_key
# GITHUB_TOKEN=your_github_token
EOF
```

4. **Configure `config.yaml`** (basic settings)

```yaml
# Knowledge Base Settings
KB_PATH: ./knowledge_base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main

# Agent Configuration
AGENT_TYPE: "stub"  # Options: stub, autonomous, qwen_code_cli

# Processing Settings
MESSAGE_GROUP_TIMEOUT: 30  # seconds

# Logging
LOG_LEVEL: INFO
LOG_FILE: ./logs/bot.log

# User Access Control (empty = all users allowed)
ALLOWED_USER_IDS: ""
```

5. **(Optional) Install Qwen Code CLI** for advanced AI processing

```bash
# Install Node.js 20+ first, then:
npm install -g @qwen-code/qwen-code@latest

# Authenticate (2000 free requests/day)
qwen

# Update config.yaml
AGENT_TYPE: "qwen_code_cli"
```

### Running the Bot

1. **Start the bot**

```bash
# Recommended (via console script)
poetry run tg-note

# Or directly with Python
poetry run python main.py

# If installed with pip (outside Poetry)
tg-note
```

You should see:

```
INFO - Starting tg-note bot...
INFO - Configuration validated successfully
INFO - Processing tracker initialized
INFO - Repository manager initialized
INFO - Telegram bot started successfully
INFO - Bot initialization completed
INFO - Press Ctrl+C to stop
```

2. **Configure your knowledge base in Telegram**

Open your bot in Telegram and:

```
/start                    # Initialize the bot
/setkb my-notes           # Create local knowledge base
# or
/setkb https://github.com/username/kb-repo  # Use GitHub repository
```

3. **Start sending messages!**

Just forward any message or write text - the bot will automatically process and save it to your knowledge base.

4. **Stop the bot**

Press `Ctrl+C` in the terminal

---

## 📖 Usage

### Working Modes

The bot has **three working modes** that you can switch between:

#### 📝 Note Mode (Default) - `/note`

Analyzes and saves your messages to the knowledge base.

- Automatic categorization
- Structured markdown generation
- Git integration

#### 🤔 Ask Mode - `/ask`

Answers questions about your knowledge base content.

- Searches through your KB
- Provides answers with sources
- Russian language support

#### 🤖 Agent Mode - `/agent`

Full autonomous access to your knowledge base.

- Can answer questions (like Ask mode)
- Can add/edit/delete content
- Can restructure and organize KB
- Shows detailed file changes

Switch between modes: `/note` | `/ask` | `/agent`

### Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot interaction | `/start` |
| `/help` | Display help information | `/help` |
| `/note` | Switch to note creation mode | `/note` |
| `/ask` | Switch to question mode | `/ask` |
| `/agent` | Switch to agent mode (full access) | `/agent` |
| `/setkb <name\|url>` | Setup knowledge base | `/setkb my-notes` or `/setkb https://github.com/user/repo` |
| `/kb` | Show current KB info | `/kb` |
| `/status` | Display processing statistics | `/status` |
| `/settings` | Open interactive settings menu | Navigate through categories and settings |
| `/viewsettings [category]` | View all or filtered settings | `/viewsettings knowledge_base` |
| `/resetsetting <name>` | Reset to default | `/resetsetting AGENT_TIMEOUT` |
| `/kbsettings` | KB settings quick access | View and modify KB configuration |
| `/agentsettings` | Agent settings quick access | View and modify agent configuration |

### ⚙️ Settings Management (NEW!)

**Per-User Configuration**

Each user can customize bot behavior via Telegram commands:

```bash
# Open interactive settings menu
/settings
# Navigate through categories → Select setting → Enter new value

# View all settings or filter by category
/viewsettings
/viewsettings knowledge_base

# Reset to global defaults
/resetsetting KB_GIT_AUTO_PUSH

# Quick access to categories
/kbsettings       # Knowledge Base settings
/agentsettings    # Agent configuration
```

**How Settings Work:**

1. Use `/settings` to open the interactive menu
2. Choose a category (Knowledge Base, Agent, Processing, etc.)
3. Click on any setting to view its details
4. For boolean settings: Click Enable/Disable buttons
5. For other settings: Send the new value as a text message
6. Settings include descriptions, types, and allowed values

**Features:**

- ✅ **Interactive UI**: Inline keyboards with category navigation
- ✅ **Type Safety**: Automatic validation and type conversion
- ✅ **Per-User Overrides**: Each user can customize their settings
- ✅ **Auto-Generated**: New settings automatically appear in UI
- ✅ **Secure**: Credentials cannot be changed via Telegram

**Available Settings Categories:**

- 📚 Knowledge Base (Git, paths, auto-push)
- 🤖 Agent (model, timeout, tools enabled)
- ⚙️ Processing (message grouping, deduplication)
- 📝 Logging (level, file path)

See [Settings Management guide](https://artyomzemlyak.github.io/tg-note/user-guide/settings-management/) for details.

### Working with Content

**Supported Content Types:**

- ✅ Text messages
- ✅ Forwarded messages from channels
- ✅ Photos with captions
- ✅ Documents (PDF, DOCX, PPTX, XLSX, MD, HTML, TXT)
- ✅ **NEW: Automatic file format recognition** using Docling
- ✅ Multiple consecutive messages (auto-grouped)

**Processing Workflow:**

1. Send or forward content to the bot
2. Bot analyzes and categorizes the content
3. Creates a structured Markdown note
4. Saves to appropriate category in your KB
5. Commits to Git (if enabled)
6. Notifies you of completion

**Example Output Structure:**

```
knowledge_base/
├── topics/
│   ├── ai/
│   │   └── 2025-10-02-neural-networks-breakthrough.md
│   ├── biology/
│   │   └── 2025-10-01-crispr-advancement.md
│   └── physics/
│       └── 2025-09-30-quantum-computing.md
└── index.md
```

---

## 🤖 Agent Types

The system supports three types of agents for content processing:

### Agent Compatibility Matrix

| Feature | AutonomousAgent | QwenCodeCLIAgent | StubAgent |
|---------|----------------|------------------|-----------|
| **Language** | Python | Node.js (subprocess) | Python |
| **MCP Tools** | ✅ Python MCP | ✅ Qwen Native MCP | ❌ No |
| **Built-in Tools** | ✅ Yes | ✅ Yes | ❌ No |
| **Custom Tools** | ✅ Easy (Python) | ✅ Via MCP Config | ❌ No |
| **Free Tier** | Provider-dependent | 2000/day | ✅ Always |
| **Setup Complexity** | Medium | Medium-High | Low |
| **AI Quality** | High | High | Basic |

> **💡 MCP Support Note**: Both **AutonomousAgent** and **QwenCodeCLIAgent** support MCP, but with different approaches:
>
> - **AutonomousAgent**: Uses Python MCP client (`DynamicMCPTool`) - MCP servers managed from Python code
> - **QwenCodeCLIAgent**: Uses Qwen's native MCP client - MCP servers configured in `.qwen/settings.json` as standalone processes
>
> [Learn more about MCP integration →](https://artyomzemlyak.github.io/tg-note/agents/qwen-code-cli/)

---

### 1. autonomous (Recommended for MCP) ✅

Python-based autonomous agent with OpenAI-compatible API support and **full MCP support**.

**Features:**

- ✅ **MCP Tools Support** - Full access to Model Context Protocol tools
- ✅ OpenAI-compatible API integration
- ✅ Autonomous planning and decision-making
- ✅ Built-in tools: web search, git, github, file management
- ✅ Function calling support
- ✅ Works with various LLM providers

**Setup:**

```bash
pip install openai  # included in requirements
```

**Configuration:**

```yaml
AGENT_TYPE: "autonomous"
AGENT_MODEL: "gpt-3.5-turbo"  # or any compatible model
AGENT_ENABLE_MCP: true  # Enable MCP tools
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_FILE_MANAGEMENT: true
```

**Environment Variables:**

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional, for custom endpoints
```

📚 [Detailed Documentation →](https://artyomzemlyak.github.io/tg-note/agents/autonomous-agent/)

---

### 2. qwen_code_cli (Best for Free Tier) ✅

Uses [Qwen Code CLI](https://github.com/QwenLM/qwen-code) for advanced AI processing.

**Features:**

- ✅ Full integration with Qwen3-Coder models
- ✅ Automatic TODO planning
- ✅ Built-in tools: web search, git, github, shell
- ✅ Free tier: 2000 requests/day
- ✅ Vision model support
- ✅ **MCP support** via qwen native mechanism (requires `.qwen/settings.json`)

**Setup:**

```bash
npm install -g @qwen-code/qwen-code@latest
qwen  # authenticate
```

**Configuration:**

```yaml
AGENT_TYPE: "qwen_code_cli"
AGENT_QWEN_CLI_PATH: "qwen"
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_MCP: true  # Optional - requires .qwen/settings.json configuration
```

**MCP Configuration** (optional, for custom tools via MCP):

Create `.qwen/settings.json` in your KB directory:

```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "MCP Hub - Built-in memory tools and server registry"
    }
  },
  "allowMCPServers": ["mcp-hub"]
}
```

> **ℹ️ MCP Integration**: Qwen CLI has built-in MCP support! It can connect to MCP servers configured as standalone processes. This is different from AutonomousAgent's Python MCP client. [Learn more →](https://artyomzemlyak.github.io/tg-note/agents/qwen-code-cli/)

📚 [Detailed Documentation →](https://artyomzemlyak.github.io/tg-note/agents/qwen-code-cli/)

---

### 3. stub (Testing Only)

Simple stub agent for testing and MVP.

**Features:**

- ⚡ Fast and lightweight
- 🔧 No external dependencies
- 📋 Basic categorization
- 🧪 Perfect for testing

**Configuration:**

```yaml
AGENT_TYPE: "stub"
```

**Best for:** Quick testing, MVP demos, development without API keys

---

### Choosing the Right Agent

**Use AutonomousAgent when:**

- ✅ You need **MCP tools** (memory, custom integrations)
- ✅ You have an OpenAI-compatible API key
- ✅ You want Python-native integration
- ✅ You need custom tool development

**Use QwenCodeCLIAgent when:**

- ✅ You want **free tier** (2000 requests/day)
- ✅ You need **vision model** support
- ✅ You prefer official Qwen integration
- ✅ You can create standalone MCP servers (if using MCP)

**Use StubAgent when:**

- ✅ Testing without API keys
- ✅ MVP development
- ✅ Quick prototyping

---

## 🏗️ Architecture

### System Components

```
┌─────────────────┐
│  Telegram Bot   │  ← User interface
│ (pyTelegramBotAPI) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Message Processor│  ← Grouping & parsing
│  (aggregator)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent System   │  ← AI analysis
│ (qwen/stub)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Knowledge Base   │  ← Markdown files
│   Manager       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Git Ops       │  ← Version control
│ (auto commit)   │
└─────────────────┘
```

### Data Flow

1. **Input**: User sends message/repost to Telegram bot
2. **Aggregation**: Related messages grouped together (30s timeout)
3. **Parsing**: Extract text, media, links, generate hash
4. **Deduplication**: Check if already processed
5. **Agent Processing**: AI analyzes and structures content
6. **KB Storage**: Save as Markdown in appropriate category
7. **Git Commit**: Auto-commit to repository
8. **Notification**: Inform user of completion

### Project Structure

```
tg-note/
├── config/
│   ├── __init__.py
│   └── settings.py              # Pydantic settings
├── src/
│   ├── bot/
│   │   ├── handlers.py          # Telegram event handlers
│   │   ├── telegram_bot.py      # Main bot class
│   │   └── utils.py             # Helper functions
│   ├── processor/
│   │   ├── message_aggregator.py  # Message grouping
│   │   └── content_parser.py      # Content extraction
│   ├── agents/
│   │   ├── base_agent.py        # Abstract base class
│   │   ├── stub_agent.py        # Simple stub
│   │   ├── autonomous_agent.py  # Python agent (OpenAI-compatible)
│   │   ├── qwen_code_cli_agent.py  # CLI integration
│   │   └── agent_factory.py     # Agent factory
│   ├── knowledge_base/
│   │   ├── manager.py           # KB management
│   │   ├── git_ops.py           # Git operations
│   │   ├── repository.py        # Repo manager
│   │   └── user_settings.py     # User preferences
│   └── tracker/
│       └── processing_tracker.py  # Deduplication
├── tests/                       # Unit tests
├── data/                        # Runtime data (auto-created)
├── logs/                        # Log files
├── config.yaml                  # Main configuration
├── .env                         # Credentials (git-ignored)
├── pyproject.toml               # Project metadata and dependencies
├── poetry.lock                  # Locked dependency versions
└── main.py                      # Entry point
```

---

## ⚙️ Configuration Reference

### Environment Variables (`.env`)

```env
# Required
TELEGRAM_BOT_TOKEN=your_token_here

# Optional API Keys
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional, for custom endpoints
QWEN_API_KEY=your_qwen_key
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
```

### YAML Configuration (`config.yaml`)

```yaml
# Knowledge Base
KB_PATH: ./knowledge_base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main

# Agent
AGENT_TYPE: "qwen_code_cli"  # stub, autonomous, qwen_code_cli
AGENT_MODEL: "qwen-max"
AGENT_TIMEOUT: 300
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false
AGENT_ENABLE_FILE_MANAGEMENT: true
AGENT_ENABLE_FOLDER_MANAGEMENT: true

# Processing
MESSAGE_GROUP_TIMEOUT: 30
PROCESSED_LOG_PATH: ./data/processed.json

# Logging
LOG_LEVEL: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE: ./logs/bot.log

# Security
ALLOWED_USER_IDS: ""  # Comma-separated user IDs (empty = all allowed)
```

**Priority:** Environment Variables > `.env` file > `config.yaml`

📚 [Full Configuration Guide →](https://artyomzemlyak.github.io/tg-note/getting-started/configuration/)

---

## 🛠️ Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# With coverage report
poetry run pytest --cov=src --cov-report=html

# Specific test file
poetry run pytest tests/test_tracker.py -v

# Or activate shell first:
poetry shell
pytest
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

### Project Commands

```bash
# Check configuration
poetry run python -c "from config import settings; print(settings)"

# View processing stats
poetry run python -c "from src.tracker.processing_tracker import ProcessingTracker; \
           t = ProcessingTracker('./data/processed.json'); \
           print(t.get_stats())"

# Verify structure
poetry run python verify_structure.py
```

---

## 🚀 Deployment

### Docker Compose

This repository includes production-like Docker setup with a Makefile.

Prerequisites: Docker and Docker Compose.

1) One-time setup

```bash
make setup            # copies .env.docker.example -> .env and creates data dirs
```

2) Start in simple mode (no GPU, JSON storage)

```bash
make up-simple        # uses docker-compose.simple.yml
make logs-bot         # follow bot logs
```

3) Full stack with vLLM (GPU) for mem-agent

```bash
make up               # uses docker-compose.yml (vLLM + MCP Hub + Bot)
```

Helpful commands:

```bash
make down             # stop services
make rebuild          # rebuild and restart
make logs             # show all service logs
make ps               # show service status

# Storage modes (simple stack)
make json             # JSON storage (default)
make vector           # Vector storage (semantic search)
make mem-agent        # mem-agent storage (requires GPU backend)

# Alternative backend
make up-sglang        # SGLang backend instead of vLLM
```

Without Makefile:

```bash
docker-compose -f docker-compose.simple.yml up -d          # simple mode
docker-compose up -d                                       # full stack (vLLM)
```

Configuration used inside containers is mounted from `config.docker.yaml` and secrets come from `.env` (see `.env.docker.example`).

### Systemd Service (Linux)

```bash
# Create service file
sudo nano /etc/systemd/system/tg-note.service
```

```ini
[Unit]
Description=TG-Note Telegram Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/tg-note
ExecStart=/usr/local/bin/poetry run python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable tg-note
sudo systemctl start tg-note
sudo systemctl status tg-note
```

---

## 🗺️ Roadmap

### ✅ Completed

- ✅ Core infrastructure and project structure
- ✅ Telegram bot with async support
- ✅ Message aggregation and parsing
- ✅ Agent system (stub, qwen_code_cli)
- ✅ Knowledge base management with Git
- ✅ Multi-user support with personal KBs
- ✅ Deduplication tracking
- ✅ Comprehensive test suite
- ✅ Settings management via Telegram
- ✅ **File format recognition with Docling** (NEW!)

### 🚧 In Progress

- 🚧 Enhanced error handling and recovery
- 🚧 Docker deployment
- 🚧 CI/CD pipeline

### 📋 Planned

- 📋 Enhanced vision model support for image analysis
- 📋 Audio and video file processing
- 📋 Web interface for KB browsing
- 📋 Vector database for semantic search
- 📋 PostgreSQL storage option
- 📋 Backup and restore system
- 📋 Advanced analytics and metrics
- 📋 Batch message processing
- 📋 Real-time streaming results
- 📋 Custom agent plugins
- 📋 Multi-language support

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Guidelines

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

```bash
# Install all dependencies (including dev)
poetry install

# Activate virtual environment
poetry shell

# Run tests before committing
poetry run pytest

# Format code
poetry run black src/ tests/
```

---

## 📚 Documentation

### 📖 Complete Documentation

**[View Full Documentation →](https://artyomzemlyak.github.io/tg-note/)**

Our comprehensive documentation is hosted on GitHub Pages and includes:

- **Getting Started** - Installation, configuration, and first steps
- **User Guide** - Commands, content management, and settings
- **Agent System** - AI agents, tools, and autonomous processing
- **Architecture** - System design and component details
- **Development** - Contributing, testing, and code quality
- **Deployment** - Production setup, Docker, and CI/CD

### Quick Links

- 🚀 [Quick Start Guide](https://artyomzemlyak.github.io/tg-note/getting-started/quick-start/)
- ⚙️ [Configuration Reference](https://artyomzemlyak.github.io/tg-note/getting-started/configuration/)
- 📝 [Bot Commands](https://artyomzemlyak.github.io/tg-note/user-guide/bot-commands/)
- 🤖 [Agent Overview](https://artyomzemlyak.github.io/tg-note/agents/overview/)
- 🔧 [Settings Management](https://artyomzemlyak.github.io/tg-note/user-guide/settings-management/)
- 📄 [File Format Recognition](https://artyomzemlyak.github.io/tg-note/user-guide/file-format-recognition/)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Qwen Code](https://github.com/QwenLM/qwen-code) - AI agent framework
- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) - Telegram bot library
- [GitPython](https://github.com/gitpython-developers/GitPython) - Git integration

---

## 📞 Support & Contact

- 📖 [Full Documentation](https://artyomzemlyak.github.io/tg-note/)
- 🐛 [Issue Tracker](https://github.com/ArtyomZemlyak/tg-note/issues)
- 💬 [Discussions](https://github.com/ArtyomZemlyak/tg-note/discussions)

---

<div align="center">

**Built with ❤️ by [Artem Zemliak](https://github.com/ArtyomZemlyak)**

⭐ Star this repository if you find it helpful!

</div>
