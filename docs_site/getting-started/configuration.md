# Configuration Guide

Complete guide to configuring tg-note.

---

## Configuration Sources

tg-note supports multiple configuration sources with the following priority (highest to lowest):

1. **Environment Variables** - Highest priority
2. **`.env` file** - For credentials and overrides
3. **`config.yaml`** - Base configuration
4. **Default values** - Built-in defaults

!!! tip "Best Practice"
    - Store **sensitive data** (tokens, API keys) in `.env`
    - Store **general settings** in `config.yaml`
    - Use **environment variables** for deployment overrides

---

## Configuration Files

### config.yaml

Main configuration file for non-sensitive settings.

```yaml
# Knowledge Base Settings
KB_PATH: ./knowledge_base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main

# Agent Configuration
AGENT_TYPE: "qwen_code_cli"  # stub, autonomous, qwen_code_cli
AGENT_MODEL: "qwen-max"
AGENT_TIMEOUT: 300
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false

# Processing Settings
MESSAGE_GROUP_TIMEOUT: 30
PROCESSED_LOG_PATH: ./data/processed.json

# Logging Settings
LOG_LEVEL: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE: ./logs/bot.log

# Security
ALLOWED_USER_IDS: ""  # Comma-separated, empty = all allowed
```

### .env File

Credentials and sensitive data (never commit to git!).

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional API Keys
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional, for custom endpoints
ANTHROPIC_API_KEY=sk-ant-...
QWEN_API_KEY=your_qwen_key

# GitHub Integration
GITHUB_TOKEN=ghp_...
```

---

## Configuration Options

### Knowledge Base Settings

#### KB_PATH
- **Type:** Path
- **Default:** `./knowledge_base`
- **Description:** Path to your knowledge base directory
- **Example:** `/path/to/my-kb`

#### KB_GIT_ENABLED
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable Git operations
- **Example:** `true` or `false`

#### KB_GIT_AUTO_PUSH
- **Type:** Boolean
- **Default:** `true`
- **Description:** Automatically push changes to remote
- **Example:** `true` or `false`

#### KB_GIT_REMOTE
- **Type:** String
- **Default:** `origin`
- **Description:** Git remote name
- **Example:** `origin`

#### KB_GIT_BRANCH
- **Type:** String
- **Default:** `main`
- **Description:** Git branch to use
- **Example:** `main` or `master`

---

### Agent Settings

#### AGENT_TYPE
- **Type:** String
- **Default:** `stub`
- **Options:** `stub`, `autonomous`, `qwen_code_cli`
- **Description:** Agent implementation to use
- **Recommendation:** Use `qwen_code_cli` for production, or `autonomous` for OpenAI-compatible APIs

#### AGENT_MODEL
- **Type:** String
- **Default:** `qwen-max`
- **Description:** AI model to use
- **Examples:** `qwen-max`, `qwen-turbo`, `gpt-4`

#### AGENT_QWEN_CLI_PATH
- **Type:** String
- **Default:** `qwen`
- **Description:** Path to qwen CLI executable
- **Examples:** `qwen`, `/usr/local/bin/qwen`, `./bin/qwen`

#### AGENT_INSTRUCTION
- **Type:** String (Optional)
- **Default:** `None`
- **Description:** Custom instruction for the agent
- **Example:** `"Always be concise and use bullet points"`

#### AGENT_TIMEOUT
- **Type:** Integer (seconds)
- **Default:** `300`
- **Description:** Maximum time for agent processing
- **Example:** `600` (10 minutes)

#### AGENT_ENABLE_WEB_SEARCH
- **Type:** Boolean
- **Default:** `true`
- **Description:** Allow web search capability
- **Example:** `true` or `false`

#### AGENT_ENABLE_GIT
- **Type:** Boolean
- **Default:** `true`
- **Description:** Allow Git operations
- **Example:** `true` or `false`

#### AGENT_ENABLE_GITHUB
- **Type:** Boolean
- **Default:** `true`
- **Description:** Allow GitHub API access
- **Example:** `true` or `false`

#### AGENT_ENABLE_SHELL
- **Type:** Boolean
- **Default:** `false`
- **Description:** Allow shell command execution
- **Warning:** ⚠️ Security risk, use with caution
- **Example:** `false`

#### AGENT_ENABLE_FILE_MANAGEMENT
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable file operations (create, edit, delete, move files)
- **Example:** `true` or `false`

#### AGENT_ENABLE_FOLDER_MANAGEMENT
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable folder operations (create, delete, move folders)
- **Example:** `true` or `false`

---

### Processing Settings

#### MESSAGE_GROUP_TIMEOUT
- **Type:** Integer (seconds)
- **Default:** `30`
- **Description:** Wait time before processing grouped messages
- **Example:** `60` (1 minute)

#### PROCESSED_LOG_PATH
- **Type:** Path
- **Default:** `./data/processed.json`
- **Description:** Path to processing tracker database
- **Example:** `./data/tracker.json`

---

### Logging Settings

#### LOG_LEVEL
- **Type:** String
- **Default:** `INFO`
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description:** Logging verbosity level
- **Example:** `DEBUG` for development

#### LOG_FILE
- **Type:** Path
- **Default:** `./logs/bot.log`
- **Description:** Path to log file
- **Example:** `./logs/tg-note.log`

---

### Security Settings

#### TELEGRAM_BOT_TOKEN
- **Type:** String (Secret)
- **Required:** Yes
- **Source:** `.env` or environment variable only
- **Description:** Telegram bot authentication token
- **Example:** `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

#### ALLOWED_USER_IDS
- **Type:** String (comma-separated)
- **Default:** `""` (all users allowed)
- **Description:** Whitelist of allowed Telegram user IDs
- **Example:** `12345678,87654321`

#### OPENAI_API_KEY
- **Type:** String (Secret)
- **Required:** No
- **Source:** `.env` or environment variable only
- **Description:** OpenAI API key for autonomous agent
- **Example:** `sk-...`

#### OPENAI_BASE_URL
- **Type:** String (Secret)
- **Required:** No
- **Source:** `.env` or environment variable only
- **Description:** OpenAI API base URL for custom endpoints
- **Example:** `https://api.openai.com/v1`

#### QWEN_API_KEY
- **Type:** String (Secret)
- **Required:** No
- **Source:** `.env` or environment variable only
- **Description:** Qwen API key (for custom integrations)
- **Example:** `your_qwen_key`

#### ANTHROPIC_API_KEY
- **Type:** String (Secret)
- **Required:** No
- **Source:** `.env` or environment variable only
- **Description:** Anthropic API key (future use)
- **Example:** `sk-ant-...`

#### GITHUB_TOKEN
- **Type:** String (Secret)
- **Required:** No
- **Source:** `.env` or environment variable only
- **Description:** GitHub personal access token for API operations
- **Example:** `ghp_...`

---

## Configuration Examples

### Development Setup

```yaml title="config.yaml"
# Development configuration
KB_PATH: ./dev-kb
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: false  # Manual push for dev

AGENT_TYPE: "stub"  # Fast testing
AGENT_TIMEOUT: 60

MESSAGE_GROUP_TIMEOUT: 10  # Quick testing

LOG_LEVEL: DEBUG
LOG_FILE: ./logs/dev.log

ALLOWED_USER_IDS: "your_user_id"  # Only you
```

### Production Setup

```yaml title="config.yaml"
# Production configuration
KB_PATH: /var/kb/production
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main

AGENT_TYPE: "qwen_code_cli"
AGENT_MODEL: "qwen-max"
AGENT_TIMEOUT: 300
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false
AGENT_ENABLE_FILE_MANAGEMENT: true
AGENT_ENABLE_FOLDER_MANAGEMENT: true

MESSAGE_GROUP_TIMEOUT: 30
PROCESSED_LOG_PATH: /var/data/processed.json

LOG_LEVEL: INFO
LOG_FILE: /var/log/tg-note/bot.log

ALLOWED_USER_IDS: ""  # Allow all authenticated users
```

### Testing Setup

```yaml title="config.yaml"
# Testing configuration
KB_PATH: ./test-kb
KB_GIT_ENABLED: false  # No git for tests

AGENT_TYPE: "stub"
AGENT_TIMEOUT: 30

MESSAGE_GROUP_TIMEOUT: 5

LOG_LEVEL: WARNING  # Reduce noise
LOG_FILE: ./logs/test.log

ALLOWED_USER_IDS: "123"  # Test user only
```

---

## Environment-Specific Configuration

### Using Environment Variables

Override any setting using environment variables:

```bash
export MESSAGE_GROUP_TIMEOUT=120
export LOG_LEVEL=DEBUG
export AGENT_TYPE=qwen_code_cli

python main.py
```

### Docker Environment

```dockerfile
ENV TELEGRAM_BOT_TOKEN=your_token
ENV KB_PATH=/app/kb
ENV LOG_LEVEL=INFO
ENV AGENT_TYPE=qwen_code_cli
```

---

## Configuration Validation

### Check Current Configuration

```bash
poetry run python -c "from config import settings; print(settings)"
```

### Validate Configuration

```python
from config import settings

errors = settings.validate()
if errors:
    print(f"Configuration errors: {errors}")
else:
    print("Configuration is valid!")
```

---

## Troubleshooting

### Setting Not Applied

Check the priority order:

1. Environment variable set? → Takes precedence
2. Value in `.env`? → Overrides `config.yaml`
3. Value in `config.yaml`? → Uses this
4. Falls back to default

```bash
# Check environment variable
echo $MESSAGE_GROUP_TIMEOUT

# Check .env file
cat .env | grep MESSAGE_GROUP_TIMEOUT

# Check config.yaml
cat config.yaml | grep MESSAGE_GROUP_TIMEOUT
```

### YAML Syntax Error

Validate YAML syntax:

```bash
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### Permission Issues

Check file permissions:

```bash
ls -la config.yaml .env
chmod 600 .env  # Secure credentials
chmod 644 config.yaml
```

---

## See Also

- [Installation Guide](installation.md)
- [Settings Management](../user-guide/settings-management.md)
- [Agent Configuration](../agents/overview.md)
