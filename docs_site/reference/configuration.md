# Configuration Reference

Complete reference for all tg-note configuration options.

---

## Configuration Files

tg-note uses two configuration files:

1. **`.env`** - Sensitive credentials (not committed to git)
2. **`config.yaml`** - Main configuration (can be committed)

**Priority:** Environment Variables > `.env` file > `config.yaml`

---

## Knowledge Base Settings

### KB_PATH

Path to knowledge base directory.

- **Type:** `str`
- **Default:** `./knowledge_base`
- **Example:** `./my-notes` or `/path/to/kb`

### KB_GIT_ENABLED

Enable Git integration for knowledge base.

- **Type:** `bool`
- **Default:** `true`
- **Description:** If enabled, changes are committed to git

### KB_GIT_AUTO_PUSH

Automatically push commits to remote repository.

- **Type:** `bool`
- **Default:** `true`
- **Requires:** `KB_GIT_ENABLED=true`

### KB_GIT_REMOTE

Git remote name.

- **Type:** `str`
- **Default:** `origin`

### KB_GIT_BRANCH

Git branch name.

- **Type:** `str`
- **Default:** `main`

### KB_TOPICS_ONLY

Restrict agents to work only in `topics/` folder.

- **Type:** `bool`
- **Default:** `true`
- **Description:** Prevents agents from modifying meta files like `index.md`, `README.md` in KB root
- **When true:** Agents can only access `KB_PATH/topics/`
- **When false:** Agents have full access to entire KB directory

---

## Agent Settings

### AGENT_TYPE

Type of AI agent to use.

- **Type:** `str`
- **Default:** `stub`
- **Options:** `stub`, `autonomous`, `qwen_code_cli`
- **Description:**
  - `stub` - Simple testing agent (no API needed)
  - `autonomous` - Python-based agent with OpenAI-compatible API
  - `qwen_code_cli` - Advanced agent using Qwen Code CLI

### AGENT_MODEL

Model name for the agent.

- **Type:** `str`
- **Default:** `qwen-max`
- **Examples:** `gpt-4`, `gpt-3.5-turbo`, `qwen-max`, `claude-3-sonnet`

### AGENT_TIMEOUT

Maximum time (in seconds) for agent operations.

- **Type:** `int`
- **Default:** `300`
- **Range:** `60` to `600`

### AGENT_ENABLE_WEB_SEARCH

Enable web search capability for agents.

- **Type:** `bool`
- **Default:** `true`

### AGENT_ENABLE_GIT

Enable Git operations for agents.

- **Type:** `bool`
- **Default:** `true`

### AGENT_ENABLE_GITHUB

Enable GitHub integration for agents.

- **Type:** `bool`
- **Default:** `true`

### AGENT_ENABLE_SHELL

Enable shell command execution for agents.

- **Type:** `bool`
- **Default:** `false`
- **Warning:** Security risk if enabled

### AGENT_ENABLE_FILE_MANAGEMENT

Enable file create/edit/delete operations.

- **Type:** `bool`
- **Default:** `true`

### AGENT_ENABLE_FOLDER_MANAGEMENT

Enable folder create/delete/move operations.

- **Type:** `bool`
- **Default:** `true`

### MCP_TIMEOUT

Timeout for MCP (Model Context Protocol) requests.

- **Type:** `int`
- **Default:** `600` (10 minutes)
- **Description:** Controls how long to wait for MCP server responses
- **Recommended values:**
  - Simple requests: 60-120 seconds
  - Complex operations: 300-600 seconds (5-10 minutes)
  - Very long operations: 900-1800 seconds (15-30 minutes)

---

## Processing Settings

### MESSAGE_GROUP_TIMEOUT

Time (in seconds) to wait for related messages before processing.

- **Type:** `int`
- **Default:** `30`
- **Description:** Bot groups consecutive messages within this timeout

### PROCESSED_LOG_PATH

Path to processed messages log file.

- **Type:** `str`
- **Default:** `./data/processed.json`

---

## Logging Settings

### LOG_LEVEL

Logging level.

- **Type:** `str`
- **Default:** `INFO`
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### LOG_FILE

Path to log file.

- **Type:** `str`
- **Default:** `./logs/bot.log`

---

## Security Settings

### ALLOWED_USER_IDS

Whitelist of allowed Telegram user IDs. When set via environment variables, it accepts:

- empty string → allow all users
- comma-separated string → e.g., `"123456789,987654321"`
- JSON list → e.g., `[123456789, 987654321]`

- **Type:** `List[int]`
- **Default:** `[]` (empty list = all users allowed)
- **Examples:** `"123456789,987654321"` or `[123456789, 987654321]`

---

## Credentials Settings

### GITHUB_TOKEN

GitHub personal access token for API operations and Git authentication.

- **Type:** `Optional[str]`
- **Default:** `None`
- **Description:** Used for GitHub API calls and HTTPS Git authentication
- **Security:** Should be stored in `.env` file, not in `config.yaml`

### GITHUB_USERNAME

GitHub username for HTTPS authentication.

- **Type:** `Optional[str]`
- **Default:** `None`
- **Description:** Required when using HTTPS Git remotes with GitHub
- **Note:** Can be set per-user via Telegram `/settoken` command

### GITLAB_TOKEN

GitLab personal access token for API operations and Git authentication.

- **Type:** `Optional[str]`
- **Default:** `None`
- **Description:** Used for GitLab API calls and HTTPS Git authentication
- **Security:** Should be stored in `.env` file, not in `config.yaml`
- **Get token:** https://gitlab.com/-/profile/personal_access_tokens

### GITLAB_USERNAME

GitLab username for HTTPS authentication.

- **Type:** `Optional[str]`
- **Default:** `None`
- **Description:** Required when using HTTPS Git remotes with GitLab
- **Note:** Can be set per-user via Telegram `/settoken` command

### OPENROUTER_API_KEY

OpenRouter API key for backward compatibility.

- **Type:** `Optional[str]`
- **Default:** `None`
- **Description:** Used for OpenRouter API access (backward compatibility)
- **Note:** Can also be used with memory agent for cloud LLM access

---

## Environment Variables (.env)

### Required

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### Optional API Keys

```env
# OpenAI (for autonomous agent)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional, for custom endpoints

# Qwen
QWEN_API_KEY=your_qwen_key

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# GitHub
GITHUB_TOKEN=ghp_...
GITHUB_USERNAME=your_username  # Optional, for HTTPS authentication

# GitLab
GITLAB_TOKEN=glpat-...
GITLAB_USERNAME=your_username  # Optional, for HTTPS authentication

# OpenRouter (for backward compatibility)
OPENROUTER_API_KEY=your_openrouter_key
```

---

## Example Configuration

### Minimal Setup (Stub Agent)

```yaml
# config.yaml
KB_PATH: ./knowledge_base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: false
AGENT_TYPE: "stub"
LOG_LEVEL: INFO
```

```env
# .env
TELEGRAM_BOT_TOKEN=your_token
```

### Production Setup (Qwen Code CLI)

```yaml
# config.yaml
KB_PATH: /data/knowledge_base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main
KB_TOPICS_ONLY: true

AGENT_TYPE: "qwen_code_cli"
AGENT_TIMEOUT: 300
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false
AGENT_ENABLE_FILE_MANAGEMENT: true
AGENT_ENABLE_FOLDER_MANAGEMENT: true

MESSAGE_GROUP_TIMEOUT: 30
LOG_LEVEL: INFO
LOG_FILE: /var/log/tg-note/bot.log

ALLOWED_USER_IDS: "123456789"
```

```env
# .env
TELEGRAM_BOT_TOKEN=your_production_token
GITHUB_TOKEN=ghp_your_github_token
```

### Development Setup (Autonomous Agent)

```yaml
# config.yaml
KB_PATH: ./test_kb
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: false
KB_TOPICS_ONLY: false

AGENT_TYPE: "autonomous"
AGENT_MODEL: "gpt-3.5-turbo"
AGENT_TIMEOUT: 200
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_FILE_MANAGEMENT: true

MESSAGE_GROUP_TIMEOUT: 10
LOG_LEVEL: DEBUG
```

```env
# .env
TELEGRAM_BOT_TOKEN=your_dev_token
OPENAI_API_KEY=sk-...
```

---

## See Also

- [Quick Start Guide](../getting-started/quick-start.md)
- [Settings Management](../user-guide/settings-management.md)
- [Agent Overview](../agents/overview.md)
