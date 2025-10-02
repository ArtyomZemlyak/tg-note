# tg-note

> **Intelligent Knowledge Base Builder** - Telegram bot that automatically transforms your messages, reposts, and articles into a structured knowledge base using AI agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

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
  - [qwen_code_cli (Recommended)](#1-qwen_code_cli-recommended-)
  - [qwen_code](#2-qwen_code)
  - [stub](#3-stub)
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
- **🎯 Flexible Agents**: Choose between stub, custom Python, or Qwen Code CLI agents
- **⚡ Async Architecture**: Fast, non-blocking message processing

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Git**
- **Telegram Account**
- **Node.js 20+** (optional, for qwen_code_cli agent)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/ArtyomZemlyak/tg-note.git
cd tg-note
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
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

# Optional: API keys for advanced agents (future)
# OPENAI_API_KEY=your_openai_key
# ANTHROPIC_API_KEY=your_anthropic_key
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
AGENT_TYPE: "stub"  # Options: stub, qwen_code, qwen_code_cli

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
python main.py
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

### Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot interaction | `/start` |
| `/help` | Display help information | `/help` |
| `/setkb <name\|url>` | Setup knowledge base | `/setkb my-notes` or `/setkb https://github.com/user/repo` |
| `/kb` | Show current KB info | `/kb` |
| `/status` | Display processing statistics | `/status` |

### Working with Content

**Supported Content Types:**
- ✅ Text messages
- ✅ Forwarded messages from channels
- ✅ Photos with captions
- ✅ Documents
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

### 1. qwen_code_cli (Recommended) ✅

Uses [Qwen Code CLI](https://github.com/QwenLM/qwen-code) for advanced AI processing.

**Features:**
- ✅ Full integration with Qwen3-Coder models
- ✅ Automatic TODO planning
- ✅ Built-in tools: web search, git, github, shell
- ✅ Free tier: 2000 requests/day
- ✅ Vision model support

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
```

📚 [Detailed Documentation →](./QWEN_CODE_CLI_INTEGRATION.md)

### 2. qwen_code

Pure Python agent with custom tools.

**Features:**
- ✅ Python-native implementation
- ✅ Flexible tool configuration
- ✅ Custom TODO planning
- ✅ Web search, Git, GitHub API support

**Configuration:**
```yaml
AGENT_TYPE: "qwen_code"
AGENT_MODEL: "qwen-max"
```

📚 [Detailed Documentation →](./QWEN_CODE_AGENT.md)

### 3. stub

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

## 🏗️ Architecture

### System Components

```
┌─────────────────┐
│  Telegram Bot   │  ← User interface
│   (aiogram)     │
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
│   │   ├── qwen_code_agent.py   # Python agent
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
├── requirements.txt             # Dependencies
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
ANTHROPIC_API_KEY=sk-ant-...
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
AGENT_TYPE: "qwen_code_cli"  # stub, qwen_code, qwen_code_cli
AGENT_MODEL: "qwen-max"
AGENT_TIMEOUT: 300
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false

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

📚 [Full Configuration Guide →](./YAML_CONFIGURATION.md)

---

## 🛠️ Development

### Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_tracker.py -v

# Watch mode
pytest-watch
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

### Project Commands

```bash
# Check configuration
python -c "from config import settings; print(settings)"

# View processing stats
python -c "from src.tracker.processing_tracker import ProcessingTracker; \
           t = ProcessingTracker('./data/processed.json'); \
           print(t.get_stats())"

# Verify structure
python verify_structure.py
```

---

## 🚀 Deployment

### Docker (Coming Soon)

```bash
docker build -t tg-note .
docker run -d \
  --env-file .env \
  -v $(pwd)/knowledge_base:/app/knowledge_base \
  tg-note
```

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
Environment="PATH=/path/to/tg-note/venv/bin"
ExecStart=/path/to/tg-note/venv/bin/python main.py
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
- ✅ Agent system (stub, qwen_code, qwen_code_cli)
- ✅ Knowledge base management with Git
- ✅ Multi-user support with personal KBs
- ✅ Deduplication tracking
- ✅ Comprehensive test suite

### 🚧 In Progress

- 🚧 Enhanced error handling and recovery
- 🚧 Docker deployment
- 🚧 CI/CD pipeline

### 📋 Planned

- 📋 Vision model support for image analysis
- 📋 PDF document processing
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
# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Run tests before committing
pytest

# Format code
black src/ tests/
```

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

- 📖 [Full Documentation](./README.md)
- 🐛 [Issue Tracker](https://github.com/ArtyomZemlyak/tg-note/issues)
- 💬 [Discussions](https://github.com/ArtyomZemlyak/tg-note/discussions)

---

<div align="center">

**Built with ❤️ by [Artem Zemliak](https://github.com/ArtyomZemlyak)**

⭐ Star this repository if you find it helpful!

</div>
