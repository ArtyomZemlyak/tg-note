# Configuration Guide

Complete guide to configuring tg-note. For the full, authoritative list of
settings (including advanced MCP/vector options), see
[Reference → Configuration Options](../reference/configuration.md).

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
KB_TOPICS_ONLY: true
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
AGENT_ENABLE_MCP: false
AGENT_ENABLE_MCP_MEMORY: false

# Processing Settings
MESSAGE_GROUP_TIMEOUT: 30
PROCESSED_LOG_PATH: ./data/processed.json

# Logging Settings
LOG_LEVEL: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE: ./logs/bot.log

# Security
# Accepts empty (allow all), comma-separated (e.g., "123,456"), or JSON list (e.g., [123,456])
ALLOWED_USER_IDS: ""  # Empty = all allowed
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
GITHUB_USERNAME=your_username

# GitLab Integration (optional)
GITLAB_TOKEN=glpat_...
GITLAB_USERNAME=your_username
```

---

## Configuration Options

### Knowledge Base Settings

#### KB_PATH

- **Type:** Path
- **Default:** `./knowledge_base`
- **Description:** Path to your knowledge base directory
- **Example:** `/path/to/my-kb`

#### KB_TOPICS_ONLY

- **Type:** Boolean
- **Default:** `true`
- **Description:** Restrict agents to the `topics/` subfolder for safer edits
- **Example:** `true` or `false`

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
- **Options:** `stub`, `autonomous`, `qwen_code_cli`, `qwen_code` (alias)
- **Description:** Agent implementation to use
- **Recommendation:** Use `qwen_code_cli` for production, `autonomous` for OpenAI-compatible APIs

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

#### AGENT_ENABLE_MCP

- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable MCP tools (vector search, KB ops) via MCP Hub
- **Example:** `true`

#### AGENT_ENABLE_MCP_MEMORY

- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable MCP memory agent tool for semantic recall
- **Example:** `true`

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

- **Type:** List[int] (from env supports: empty, comma-separated, or JSON list)
- **Default:** `[]` (all users allowed)
- **Description:** Whitelist of allowed Telegram user IDs
- **Examples:** `"12345678,87654321"` or `[12345678, 87654321]`

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

#### GITHUB_USERNAME

- **Type:** String
- **Required:** No
- **Source:** `.env` or environment variable only
- **Description:** GitHub username for API operations
- **Example:** `your_username`

#### GITLAB_TOKEN

- **Type:** String (Secret)
- **Required:** No
- **Source:** `.env` or environment variable only
- **Description:** GitLab personal access token for API operations
- **Example:** `glpat_...`

#### GITLAB_USERNAME

- **Type:** String
- **Required:** No
- **Source:** `.env` or environment variable only
- **Description:** GitLab username for API operations
- **Example:** `your_username`

---

### Vector Search Settings

#### VECTOR_SEARCH_ENABLED

- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable semantic vector search
- **Example:** `true` or `false`

#### VECTOR_EMBEDDING_PROVIDER

- **Type:** String
- **Default:** `sentence_transformers`
- **Options:** `sentence_transformers`, `openai`, `infinity`
- **Description:** Embedding provider for vector search
- **Example:** `infinity` for Docker setup

#### VECTOR_EMBEDDING_MODEL

- **Type:** String
- **Default:** `all-MiniLM-L6-v2`
- **Description:** Embedding model to use
- **Examples:** `all-MiniLM-L6-v2`, `BAAI/bge-m3`, `text-embedding-ada-002`

#### VECTOR_INFINITY_API_URL

- **Type:** String
- **Default:** `http://localhost:7997`
- **Description:** Infinity API URL for embeddings
- **Example:** `http://infinity:7997` (Docker)

#### VECTOR_INFINITY_API_KEY

- **Type:** String (Secret)
- **Required:** No
- **Source:** `.env` or environment variable only
- **Description:** Infinity API key (if required)
- **Example:** `your_infinity_key`

#### VECTOR_STORE_PROVIDER

- **Type:** String
- **Default:** `faiss`
- **Options:** `faiss`, `qdrant`
- **Description:** Vector store provider
- **Example:** `qdrant` for Docker setup

#### VECTOR_QDRANT_URL

- **Type:** String
- **Default:** `http://localhost:6333`
- **Description:** Qdrant vector database URL
- **Example:** `http://qdrant:6333` (Docker)

#### VECTOR_QDRANT_API_KEY

- **Type:** String (Secret)
- **Required:** No
- **Source:** `.env` or environment variable only
- **Description:** Qdrant API key (if required)
- **Example:** `your_qdrant_key`

#### VECTOR_QDRANT_COLLECTION

- **Type:** String
- **Default:** `knowledge_base`
- **Description:** Qdrant collection name
- **Example:** `my_kb_vectors`

#### VECTOR_CHUNKING_STRATEGY

- **Type:** String
- **Default:** `fixed_size_overlap`
- **Options:** `fixed_size_overlap`, `semantic`
- **Description:** Text chunking strategy (semantic respects headers)
- **Example:** `semantic`

#### VECTOR_CHUNK_SIZE

- **Type:** Integer
- **Default:** `512`
- **Description:** Size of text chunks for vectorization (characters)
- **Example:** `1024`

#### VECTOR_CHUNK_OVERLAP

- **Type:** Integer
- **Default:** `50`
- **Description:** Overlap between chunks
- **Example:** `100`

#### VECTOR_RESPECT_HEADERS

- **Type:** Boolean
- **Default:** `true`
- **Description:** Keep Markdown headers intact when chunking (semantic strategy)
- **Example:** `true`

#### VECTOR_SEARCH_TOP_K

- **Type:** Integer
- **Default:** `5`
- **Description:** Number of top results to return
- **Example:** `10`

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

### Vector Search Setup

```yaml title="config.yaml"
# Vector search configuration
KB_PATH: ./knowledge_base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true

AGENT_TYPE: "qwen_code_cli"
AGENT_MODEL: "qwen-max"
AGENT_TIMEOUT: 300

# Vector search settings
VECTOR_SEARCH_ENABLED: true

# Embedding settings
VECTOR_EMBEDDING_PROVIDER: infinity
VECTOR_EMBEDDING_MODEL: BAAI/bge-m3
VECTOR_INFINITY_API_URL: http://infinity:7997

# Vector store settings
VECTOR_STORE_PROVIDER: qdrant
VECTOR_QDRANT_URL: http://qdrant:6333
VECTOR_QDRANT_COLLECTION: knowledge_base

# Chunking settings
VECTOR_CHUNKING_STRATEGY: fixed_size_overlap
VECTOR_CHUNK_SIZE: 512
VECTOR_CHUNK_OVERLAP: 50

# Search settings
VECTOR_SEARCH_TOP_K: 5

LOG_LEVEL: INFO
LOG_FILE: ./logs/bot.log
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
- [Vector Search Quick Start](vector-search-quickstart.md)
- [Settings Management](../user-guide/settings-management.md)
- [Agent Configuration](../agents/overview.md)
- [Vector Search Overview](../architecture/vector-search-overview.md)
