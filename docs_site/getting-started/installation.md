# Installation Guide

Detailed installation instructions for tg-note.

---

## System Requirements

### Required

- **Python 3.11 or higher**
- **Poetry** - Python dependency manager
- **Git** - Version control system
- **Telegram Account** - To create and use the bot

### Optional

- **Node.js 20+** - Required for `qwen_code_cli` agent (recommended)
- **Docker** - For containerized deployment

---

## Installation Methods

=== "Local Installation"

    ### 1. Install Python 3.11+

    Check your Python version:

    ```bash
    python3 --version
    ```

    If you need to install Python 3.11+:

    === "Ubuntu/Debian"
        ```bash
        sudo apt update
        sudo apt install python3.11 python3.11-venv python3-pip
        ```

    === "macOS"
        ```bash
        brew install python@3.11
        ```

    === "Windows"
        Download from [python.org](https://www.python.org/downloads/)

    ### 2. Install Poetry

    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

    Or using pipx:

    ```bash
    pipx install poetry
    ```

    Add Poetry to your PATH (if needed):

    ```bash
    export PATH="$HOME/.local/bin:$PATH"
    ```

    ### 3. Clone the Repository

    ```bash
    git clone https://github.com/ArtyomZemlyak/tg-note.git
    cd tg-note
    ```

    ### 4. Install Dependencies

    ```bash
    poetry install
    ```

    This creates a virtual environment and installs all required packages.

    ### 5. Verify Installation

    ```bash
    poetry run python -c "from config import settings; print('Installation successful!')"
    ```

=== "Docker Installation"

    Use Docker for a reproducible setup. See detailed guides in the Deployment section.

    ```bash
    # Build and start services
    docker compose up -d --build

    # (optional) Authenticate Qwen CLI inside the bot container
    docker exec -it tg-note-bot bash -lc "qwen"
    docker exec -it tg-note-bot bash -lc "qwen <<<'/approval-mode yolo --project'"
    ```

    - For service details see: [Docker Deployment](../deployment/docker.md)
    - For semantic search stack see: [Vector Search](../deployment/docker-vector-search.md)

---

## Optional Dependencies

### MCP (Model Context Protocol) Support

To use MCP server features (memory tools, vector search, server registry):

```bash
poetry install --extras mcp
```

**What's included:**
- `fastmcp` - MCP server framework
- `nest-asyncio` - Event loop handling for async contexts

**Use cases:**
- Exposing tools via MCP protocol
- Integrating with AI assistants that support MCP
- Running MCP Hub server

[Learn more about MCP features →](../agents/mcp-tools.md)

### Qwen Code CLI (Recommended for Production)

The Qwen Code CLI agent provides the best AI-powered processing capabilities.

#### 1. Install Node.js 20+

=== "Ubuntu/Debian"
    ```bash
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    ```

=== "macOS"
    ```bash
    brew install node@20
    ```

=== "Windows"
    Download from [nodejs.org](https://nodejs.org/)

#### 2. Install Qwen Code CLI

```bash
npm install -g @qwen-code/qwen-code@latest
```

#### 3. Verify Installation

```bash
qwen --version
```

#### 4. Authenticate

```bash
qwen
```

Follow the interactive authentication process. You'll get:

- **2000 free requests per day**
- **60 requests per minute**
- No token limits

[Learn more about Qwen Code CLI →](../agents/qwen-code-cli.md)

---

## Post-Installation Setup

### 1. Create Configuration Files

```bash
# Copy example configuration
cp config.example.yaml config.yaml
```

### 2. Setup Environment Variables

Create a `.env` file:

```bash
touch .env
```

Add your credentials:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional - For advanced features
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

!!! warning "Security"
    Never commit your `.env` file to version control!
    It's already in `.gitignore`, but always double-check.

### 3. Configure Basic Settings

Edit `config.yaml`:

```yaml
# Knowledge Base
KB_PATH: ./knowledge_base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true

# Agent Type
AGENT_TYPE: "stub"  # Options: stub, autonomous, qwen_code_cli

# Logging
LOG_LEVEL: INFO
LOG_FILE: ./logs/bot.log
```

[Full configuration guide →](configuration.md)

---

## Verification

### Run Tests

Verify everything is working:

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test
poetry run pytest tests/test_tracker.py -v
```

### Check Configuration

```bash
poetry run python -c "from config import settings; print(settings)"
```

### Test Bot Connection

```bash
poetry run python main.py
```

You should see:

```
INFO - Starting tg-note bot...
INFO - Configuration validated successfully
INFO - Bot initialization completed
```

---

## Directory Structure

After installation, your directory should look like:

```
tg-note/
├── config/              # Configuration modules
├── src/
│   ├── bot/            # Telegram bot
│   ├── processor/      # Message processing
│   ├── agents/         # AI agents
│   ├── knowledge_base/ # KB management
│   └── tracker/        # Processing tracker
├── tests/              # Unit tests
├── data/               # Created on first run
├── logs/               # Created on first run
├── config.yaml         # Your configuration
├── .env                # Your credentials
├── pyproject.toml      # Project metadata
├── poetry.lock         # Dependency lock file
└── main.py            # Entry point
```

---

## Updating

To update tg-note to the latest version:

```bash
git pull origin main
poetry install
```

To update dependencies:

```bash
poetry update
```

---

## Troubleshooting Installation

### Poetry Not Found

```bash
# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Make permanent
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Python Version Issues

```bash
# Use specific Python version with Poetry
poetry env use python3.11

# Verify
poetry run python --version
```

### Permission Errors

```bash
# On Linux/macOS
sudo chown -R $USER:$USER ~/.local

# Or install without sudo
curl -sSL https://install.python-poetry.org | python3 - --user
```

### Virtual Environment Issues

```bash
# Remove and recreate
poetry env remove python
poetry install
```

---

## Next Steps

After successful installation:

1. [Configure the bot](configuration.md)
2. [Get your Telegram bot token](first-steps.md)
3. [Run the bot](quick-start.md#running-the-bot)
4. [Choose your agent](../agents/overview.md)

---

## Uninstallation

To completely remove tg-note:

```bash
# Remove virtual environment
poetry env remove python

# Remove project directory
cd ..
rm -rf tg-note

# Optionally remove Poetry
pipx uninstall poetry
```
