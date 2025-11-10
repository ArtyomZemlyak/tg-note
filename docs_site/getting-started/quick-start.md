# Quick Start Guide

Get up and running with tg-note in just a few minutes!

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11 or 3.12** installed
- **Poetry** (Python dependency manager)
- **Git** installed
- **Telegram Account**
- **Node.js 20+** (optional, for qwen_code_cli agent)

---

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/ArtyomZemlyak/tg-note.git
cd tg-note
```

### 2. Install Poetry

If you don't have Poetry installed:

```bash
curl -sSL https://install.python-poetry.org | python3 -
# or using pipx:
# pipx install poetry
```

### 3. Install Dependencies

```bash
poetry install
```

This will automatically create a virtual environment and install all dependencies.

---

## Configuration

### 1. Create Configuration Files

```bash
# Copy example configuration
cp config.example.yaml config.yaml
```

### 2. Get Telegram Bot Token

1. Open [@BotFather](https://t.me/botfather) in Telegram
2. Send `/newbot` and follow instructions
3. Copy the token provided

### 3. Create `.env` File

Create a `.env` file with your credentials:

```bash
cat > .env << EOF
# Required: Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional: API keys for advanced agents
# OPENAI_API_KEY=your_openai_key
# ANTHROPIC_API_KEY=your_anthropic_key
EOF
```

### 4. Configure `config.yaml`

Edit `config.yaml` with your basic settings:

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

# User Access Control
# Accepts empty (allow all), comma-separated (e.g., "123,456"), or JSON list (e.g., [123,456])
ALLOWED_USER_IDS: ""
```

---

## Running the Bot

### Start the Bot

```bash
# Recommended: Use the console script
poetry run tg-note

# Or directly with Python
poetry run python main.py

# Or activate the virtual environment first:
poetry shell
tg-note
# or
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

### Configure Knowledge Base in Telegram

Open your bot in Telegram and:

```
/start                    # Initialize the bot
/setkb my-notes           # Create local knowledge base
# or
/setkb https://github.com/username/kb-repo  # Use GitHub repository
```

### Start Sending Messages

Just forward any message or write text - the bot will automatically process and save it to your knowledge base.

### Stop the Bot

Press `Ctrl+C` in the terminal.

---

## Optional: Install Qwen Code CLI

For advanced AI processing, install the Qwen Code CLI agent:

```bash
# Install Node.js 20+ first, then:
npm install -g @qwen-code/qwen-code@latest

# Authenticate (2000 free requests/day)
qwen

# Update config.yaml
AGENT_TYPE: "qwen_code_cli"
```

[Learn more about Qwen Code CLI →](../agents/qwen-code-cli.md)

---

## Basic Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot interaction | `/start` |
| `/help` | Display help information | `/help` |
| `/setkb <name\|url>` | Setup knowledge base | `/setkb my-notes` |
| `/kb` | Show current KB info | `/kb` |
| `/status` | Display processing statistics | `/status` |
| `/settings` | Open interactive settings menu | `/settings` |
| `/note` | Switch to note creation mode | `/note` |
| `/ask` | Switch to question mode | `/ask` |
| `/agent` | Switch to agent mode (full access) | `/agent` |

[Full command reference →](../user-guide/bot-commands.md)

---

## Working Modes

The bot has three working modes:

### 📝 Note Mode (Default)

Analyzes and saves your messages to the knowledge base.

### 🤔 Ask Mode

Answers questions about your knowledge base content.

### 🤖 Agent Mode

Full autonomous access - can answer questions, add/edit content, and restructure the KB.

Switch between modes with `/note`, `/ask`, or `/agent` commands.

---

## Next Steps

Now that you have tg-note running, explore these topics:

<div class="grid cards" markdown>

- :material-cog:{ .lg .middle } **Configuration**

    ---

    Learn about all configuration options

    [:octicons-arrow-right-24: Configuration Guide](configuration.md)

- :material-book-open-variant:{ .lg .middle } **User Guide**

    ---

    Learn how to use all bot features

    [:octicons-arrow-right-24: User Guide](../user-guide/bot-commands.md)

- :material-robot:{ .lg .middle } **Agent System**

    ---

    Understand AI agents and choose the right one

    [:octicons-arrow-right-24: Agent Overview](../agents/overview.md)

- :material-folder-settings:{ .lg .middle } **Knowledge Base**

    ---

    Setup and manage your knowledge base

    [:octicons-arrow-right-24: KB Setup](../user-guide/knowledge-base-setup.md)

</div>

---

## Troubleshooting

### Common Issues

!!! warning "TELEGRAM_BOT_TOKEN is required"
    Add your bot token to the `.env` file

!!! warning "Not a git repository"
    Check `KB_PATH` in config.yaml - it should point to a git repository

!!! warning "ModuleNotFoundError"
    Activate the Poetry virtual environment: `poetry shell`

!!! warning "Tests not running"
    Install dependencies: `poetry install`

[Full troubleshooting guide →](../reference/troubleshooting.md)

---

## Getting Help

- 📖 Check the [User Guide](../user-guide/bot-commands.md)
- 🐛 Report issues on [GitHub](https://github.com/ArtyomZemlyak/tg-note/issues)
- 💬 Ask questions in [Discussions](https://github.com/ArtyomZemlyak/tg-note/discussions)
