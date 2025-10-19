# Settings Architecture

## Overview

tg-note uses a sophisticated multi-layer settings system that combines global configuration, environment variables, and per-user overrides. The architecture is built on Pydantic for type safety, validation, and seamless integration with multiple configuration sources.

## Core Principles

1. **Type Safety**: All settings are strongly typed and validated
2. **Source Hierarchy**: Clear precedence rules for configuration sources
3. **User Overrides**: Per-user customization without affecting global config
4. **Security**: Sensitive credentials handled separately
5. **Interactive UI**: Settings management via Telegram commands

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                Configuration Sources                          │
│                (Priority: High to Low)                        │
└───────────────────────────┬──────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────┐
│ Environment  │  │  .env File       │  │ config.yaml  │
│ Variables    │  │                  │  │ (global)     │
│ (highest)    │  │ - Credentials    │  │              │
└──────┬───────┘  └────────┬─────────┘  └──────┬───────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
        ┌────────────────────────────────────────┐
        │     Settings (Pydantic BaseSettings)    │
        │                                         │
        │  - Validates all values                 │
        │  - Type conversion                      │
        │  - Default values                       │
        │  - Field validation                     │
        └────────────────┬───────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────┐
        │  UserSettingsManager                    │
        │                                         │
        │  - Per-user overrides                   │
        │  - Merges with global settings          │
        │  - Persistent storage                   │
        └────────────────┬───────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────┐
        │  SettingsHandlers                       │
        │  (Telegram UI)                          │
        │                                         │
        │  - Interactive menus                    │
        │  - Category navigation                  │
        │  - Value input/validation               │
        │  - Confirmation messages                │
        └─────────────────────────────────────────┘
```

## Component Details

### 1. Settings (Pydantic)

**Location**: `config/settings.py`

**Purpose**: Central configuration management with type safety

**Key Features**:

- **Pydantic BaseSettings**: Automatic loading from multiple sources
- **Type annotations**: Strong typing for all settings
- **Field validation**: Custom validators for complex types
- **Default values**: Sensible defaults for all settings
- **Computed properties**: Derived values from other settings

**Example Settings Definition**:

```python
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Knowledge Base Settings
    KB_PATH: str = Field(
        default="./knowledge_base",
        description="Path to knowledge base directory"
    )
    KB_GIT_ENABLED: bool = Field(
        default=True,
        description="Enable Git operations"
    )
    KB_GIT_AUTO_PUSH: bool = Field(
        default=True,
        description="Automatically push commits to remote"
    )
    KB_GIT_REMOTE: str = Field(
        default="origin",
        description="Git remote name"
    )
    KB_GIT_BRANCH: str = Field(
        default="main",
        description="Git branch name"
    )

    # Agent Settings
    AGENT_TYPE: str = Field(
        default="stub",
        description="Agent type: stub, qwen_code_cli, autonomous"
    )
    AGENT_MODEL: str = Field(
        default="gpt-3.5-turbo",
        description="LLM model name"
    )
    AGENT_TIMEOUT: int = Field(
        default=300,
        description="Agent execution timeout (seconds)",
        ge=10,  # minimum 10 seconds
        le=3600  # maximum 1 hour
    )

    # Processing Settings
    MESSAGE_GROUP_TIMEOUT: int = Field(
        default=30,
        description="Message grouping timeout (seconds)"
    )

    # User Access Control
    ALLOWED_USER_IDS: List[int] = Field(
        default_factory=list,
        description="Allowed Telegram user IDs (empty = all allowed)"
    )

    # Custom validator example
    @field_validator("AGENT_TYPE")
    def validate_agent_type(cls, v):
        allowed = ["stub", "qwen_code_cli", "autonomous"]
        if v not in allowed:
            raise ValueError(f"AGENT_TYPE must be one of {allowed}")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file="config.yaml",
        extra="ignore"
    )
```

**Settings Loading Priority**:

```
1. Environment Variables        (HIGHEST PRIORITY)
   Example: export AGENT_TYPE=autonomous

2. .env File
   Example: AGENT_TYPE=autonomous

3. config.yaml
   Example: AGENT_TYPE: autonomous

4. Default Values                (LOWEST PRIORITY)
   Example: default="stub"
```

**Accessing Settings**:

```python
from config.settings import settings

# Access settings
kb_path = settings.KB_PATH
agent_type = settings.AGENT_TYPE
timeout = settings.AGENT_TIMEOUT

# Check if Git enabled
if settings.KB_GIT_ENABLED:
    git_ops.commit_and_push()
```

### 2. UserSettingsManager

**Location**: `src/bot/settings_manager.py`

**Purpose**: Manage per-user setting overrides

**Key Features**:

- **Per-user storage**: Each user can customize their settings
- **Merge with globals**: User overrides applied on top of global settings
- **Persistent storage**: Saved to `data/user_settings_overrides.json`
- **Type validation**: Ensures user-provided values are valid
- **Atomic updates**: Safe concurrent access

**Storage Format** (`data/user_settings_overrides.json`):

```json
{
  "123": {
    "KB_GIT_AUTO_PUSH": false,
    "AGENT_TIMEOUT": 600,
    "MESSAGE_GROUP_TIMEOUT": 60
  },
  "456": {
    "AGENT_TYPE": "autonomous",
    "AGENT_MODEL": "gpt-4"
  }
}
```

**API Methods**:

```python
class UserSettingsManager:
    def get_user_setting(
        self,
        user_id: int,
        setting_name: str
    ) -> Any:
        """Get setting value for user (with override if exists)"""
        pass

    def update_user_setting(
        self,
        user_id: int,
        setting_name: str,
        value: Any
    ) -> bool:
        """Update user's setting override"""
        pass

    def reset_user_setting(
        self,
        user_id: int,
        setting_name: str
    ) -> bool:
        """Remove user's override, revert to global"""
        pass

    def get_all_user_settings(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """Get all settings for user (merged with global)"""
        pass

    def list_user_overrides(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """List only user's overrides (not global)"""
        pass
```

**Usage Example**:

```python
from src.bot.settings_manager import UserSettingsManager
from config.settings import settings

manager = UserSettingsManager(settings)

# Get setting for user (with override if exists)
timeout = manager.get_user_setting(user_id=123, setting_name="AGENT_TIMEOUT")
# Returns: 600 (user override) or 300 (global default)

# Update user's setting
manager.update_user_setting(
    user_id=123,
    setting_name="KB_GIT_AUTO_PUSH",
    value=False
)

# Reset to global default
manager.reset_user_setting(user_id=123, setting_name="AGENT_TIMEOUT")
```

### 3. SettingsHandlers (Telegram UI)

**Location**: `src/bot/settings_handlers.py`

**Purpose**: Interactive settings management via Telegram

**Key Features**:

- **Category navigation**: Settings grouped by category
- **Interactive buttons**: Inline keyboards for easy navigation
- **Type-aware input**: Different UI for boolean/string/number settings
- **Validation feedback**: Real-time validation errors
- **Confirmation messages**: Clear feedback on changes

**UI Flow**:

```
/settings
    │
    ▼
┌─────────────────────────────────────┐
│  ⚙️ Settings Management             │
│                                     │
│  Choose a category:                 │
│                                     │
│  [📚 Knowledge Base]                │
│  [🤖 Agent Configuration]           │
│  [⚙️ Processing Settings]           │
│  [📝 Logging Settings]              │
│  [👥 Access Control]                │
│                                     │
│  [🔙 Back to Main Menu]             │
└─────────────────────────────────────┘
    │
    │ User clicks "📚 Knowledge Base"
    ▼
┌─────────────────────────────────────┐
│  📚 Knowledge Base Settings         │
│                                     │
│  KB_PATH: ./knowledge_base          │
│  [Change]                           │
│                                     │
│  KB_GIT_ENABLED: ✅ Enabled         │
│  [Toggle]                           │
│                                     │
│  KB_GIT_AUTO_PUSH: ✅ Enabled       │
│  [Toggle]                           │
│                                     │
│  KB_GIT_REMOTE: origin              │
│  [Change]                           │
│                                     │
│  KB_GIT_BRANCH: main                │
│  [Change]                           │
│                                     │
│  [🔙 Back to Categories]            │
└─────────────────────────────────────┘
    │
    │ User clicks "KB_GIT_AUTO_PUSH"
    ▼
┌─────────────────────────────────────┐
│  KB_GIT_AUTO_PUSH                   │
│                                     │
│  📝 Description:                    │
│  Automatically push commits to      │
│  remote repository after changes    │
│                                     │
│  🔧 Type: Boolean                   │
│  📊 Current: ✅ Enabled             │
│                                     │
│  [✅ Enable]  [❌ Disable]          │
│                                     │
│  [🔄 Reset to Default]              │
│  [🔙 Back to Settings]              │
└─────────────────────────────────────┘
    │
    │ User clicks "❌ Disable"
    ▼
┌─────────────────────────────────────┐
│  ✅ Setting updated!                │
│                                     │
│  KB_GIT_AUTO_PUSH = false           │
│                                     │
│  [🔙 Back to Settings]              │
└─────────────────────────────────────┘
```

**Handler Methods**:

```python
class SettingsHandlers:
    async def cmd_settings(self, message):
        """Show settings main menu"""
        pass

    async def show_category_settings(self, call, category):
        """Show settings in a category"""
        pass

    async def show_setting_detail(self, call, setting_name):
        """Show detailed info about a setting"""
        pass

    async def handle_setting_update(self, message, setting_name):
        """Handle user input for setting update"""
        pass

    async def handle_setting_toggle(self, call, setting_name):
        """Handle boolean setting toggle"""
        pass

    async def reset_setting(self, call, setting_name):
        """Reset setting to default"""
        pass
```

## Settings Categories

### 1. Knowledge Base Settings

**Prefix**: `KB_`

**Settings**:

- `KB_PATH`: Knowledge base directory path
- `KB_GIT_ENABLED`: Enable/disable Git operations
- `KB_GIT_AUTO_PUSH`: Auto-push after commits
- `KB_GIT_REMOTE`: Git remote name
- `KB_GIT_BRANCH`: Git branch name
- `KB_TOPICS_ONLY`: Restrict agent to topics/ directory

**Use Case**: Configure knowledge base behavior

### 2. Agent Configuration Settings

**Prefix**: `AGENT_`

**Settings**:

- `AGENT_TYPE`: Agent type (stub/qwen_code_cli/autonomous)
- `AGENT_MODEL`: LLM model name
- `AGENT_TIMEOUT`: Execution timeout
- `AGENT_MAX_ITERATIONS`: Max autonomous iterations
- `AGENT_ENABLE_WEB_SEARCH`: Enable web search tool
- `AGENT_ENABLE_FILE_MANAGEMENT`: Enable file tools
- `AGENT_ENABLE_GIT`: Enable Git tools
- `AGENT_ENABLE_GITHUB`: Enable GitHub tools
- `AGENT_ENABLE_SHELL`: Enable shell tools (security risk)
- `AGENT_ENABLE_MCP`: Enable MCP tools
- `AGENT_ENABLE_MCP_MEMORY`: Enable MCP memory tools

**Use Case**: Configure AI agent behavior and capabilities

### 3. Processing Settings

**Prefix**: `MESSAGE_GROUP_`

**Settings**:

- `MESSAGE_GROUP_TIMEOUT`: Seconds to wait before processing grouped messages
- `PROCESSED_LOG_PATH`: Path to deduplication log

**Use Case**: Control message processing behavior

### 4. Logging Settings

**Prefix**: `LOG_`

**Settings**:

- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `LOG_FILE`: Path to log file
- `LOG_FORMAT`: Log message format
- `LOG_ROTATION`: Enable log rotation

**Use Case**: Control logging verbosity and output

### 5. Access Control

**Settings**:

- `ALLOWED_USER_IDS`: List of allowed Telegram user IDs

**Use Case**: Restrict bot access to specific users

### 6. MCP Settings

**Prefix**: `MCP_` or `MEM_AGENT_`

**Settings**:

- `MCP_HUB_URL`: MCP Hub endpoint URL (Docker mode)
- `MCP_HUB_PORT`: MCP Hub port
- `MEM_AGENT_STORAGE_TYPE`: Memory storage type (json/vector/mem-agent)
- `MEM_AGENT_MODEL`: Memory agent model
- `MEM_AGENT_BACKEND_URL`: Backend LLM URL (vLLM/SGLang)

**Use Case**: Configure MCP and memory services

## Settings Validation

### Type Validation

```python
# Boolean validation
KB_GIT_ENABLED: bool = True

# Integer with range
AGENT_TIMEOUT: int = Field(
    default=300,
    ge=10,    # minimum 10 seconds
    le=3600   # maximum 1 hour
)

# String with enum
AGENT_TYPE: str = Field(
    default="stub",
    pattern="^(stub|qwen_code_cli|autonomous)$"
)

# List of integers
ALLOWED_USER_IDS: List[int] = Field(default_factory=list)
```

### Custom Validators

```python
@field_validator("KB_PATH")
def validate_kb_path(cls, v):
    """Ensure KB path exists or can be created"""
    path = Path(v)
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Cannot create KB directory: {e}")
    return str(path.absolute())

@field_validator("ALLOWED_USER_IDS")
def validate_allowed_users(cls, v):
    """Parse allowed user IDs from various formats"""
    if isinstance(v, str):
        if v.strip() == "":
            return []
        if v.startswith("["):
            # JSON list
            import json
            return [int(x) for x in json.loads(v)]
        else:
            # Comma-separated
            return [int(x.strip()) for x in v.split(",") if x.strip()]
    return v
```

### Validation Errors

```python
try:
    settings = Settings()
except ValidationError as e:
    for error in e.errors():
        print(f"Field: {error['loc'][0]}")
        print(f"Error: {error['msg']}")
        print(f"Input: {error['input']}")
```

## Settings Usage in Code

### Service Layer

```python
from config.settings import settings
from src.bot.settings_manager import UserSettingsManager

class NoteCreationService:
    def __init__(self, settings_manager: UserSettingsManager):
        self.settings_manager = settings_manager

    async def create_note(self, user_id: int, ...):
        # Get user-specific or global setting
        git_enabled = self.settings_manager.get_user_setting(
            user_id, "KB_GIT_ENABLED"
        )

        if git_enabled:
            # Perform Git operations
            pass
```

### Agent Layer

```python
from config.settings import settings

class AutonomousAgent:
    def __init__(self):
        self.model = settings.AGENT_MODEL
        self.timeout = settings.AGENT_TIMEOUT
        self.max_iterations = settings.AGENT_MAX_ITERATIONS

    async def process(self, ...):
        # Use settings
        with timeout_context(self.timeout):
            for i in range(self.max_iterations):
                # Agent loop
                pass
```

### KB Layer

```python
from config.settings import settings

class GitOperations:
    def __init__(self, kb_path: Path):
        self.enabled = settings.KB_GIT_ENABLED
        self.auto_push = settings.KB_GIT_AUTO_PUSH
        self.remote = settings.KB_GIT_REMOTE
        self.branch = settings.KB_GIT_BRANCH

    def commit_and_push(self, message: str):
        if not self.enabled:
            return

        self.commit(message)

        if self.auto_push:
            self.push(self.remote, self.branch)
```

## Configuration Files

### config.yaml (Global Settings)

```yaml
# Knowledge Base
KB_PATH: ./knowledge_base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main
KB_TOPICS_ONLY: false

# Agent
AGENT_TYPE: "stub"  # stub, qwen_code_cli, autonomous
AGENT_MODEL: "gpt-3.5-turbo"
AGENT_TIMEOUT: 300
AGENT_MAX_ITERATIONS: 10

# Tools
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_FILE_MANAGEMENT: true
AGENT_ENABLE_FOLDER_MANAGEMENT: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false  # Security risk
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true

# Processing
MESSAGE_GROUP_TIMEOUT: 30
PROCESSED_LOG_PATH: ./data/processed.json

# Logging
LOG_LEVEL: INFO
LOG_FILE: ./logs/bot.log

# Access Control (empty = all allowed)
ALLOWED_USER_IDS: []

# MCP
MEM_AGENT_STORAGE_TYPE: json  # json, vector, mem-agent
```

### .env (Credentials and Overrides)

```env
# Required: Telegram Bot Token
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Optional: API Keys
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
QWEN_API_KEY=qwen-...
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...

# Optional: User Credentials
GITHUB_USERNAME=myusername
GITHUB_TOKEN=ghp_mytoken

# Optional: Overrides
# AGENT_TYPE=autonomous
# AGENT_TIMEOUT=600
```

### user_settings_overrides.json (Per-User)

```json
{
  "123": {
    "KB_GIT_AUTO_PUSH": false,
    "AGENT_TIMEOUT": 600,
    "MESSAGE_GROUP_TIMEOUT": 60
  },
  "456": {
    "AGENT_TYPE": "autonomous",
    "AGENT_MODEL": "gpt-4",
    "KB_TOPICS_ONLY": true
  }
}
```

## Best Practices

### 1. Use Settings Manager for User-Specific Logic

```python
# ✅ Good: Use settings manager
timeout = settings_manager.get_user_setting(user_id, "AGENT_TIMEOUT")

# ❌ Bad: Direct access (ignores user overrides)
timeout = settings.AGENT_TIMEOUT
```

### 2. Validate Before Saving

```python
# ✅ Good: Validate type and range
try:
    value = int(value)
    if value < 10 or value > 3600:
        raise ValueError("Timeout must be between 10 and 3600 seconds")
    settings_manager.update_user_setting(user_id, "AGENT_TIMEOUT", value)
except ValueError as e:
    notify_user(f"Invalid value: {e}")

# ❌ Bad: No validation
settings_manager.update_user_setting(user_id, "AGENT_TIMEOUT", value)
```

### 3. Document Settings

```python
# ✅ Good: Clear description and constraints
AGENT_TIMEOUT: int = Field(
    default=300,
    description="Agent execution timeout in seconds",
    ge=10,
    le=3600
)

# ❌ Bad: No description
AGENT_TIMEOUT: int = 300
```

### 4. Use Environment Variables for Secrets

```python
# ✅ Good: Credentials in .env
TELEGRAM_BOT_TOKEN=secret_token

# ❌ Bad: Credentials in config.yaml (tracked by Git)
# TELEGRAM_BOT_TOKEN: secret_token
```

### 5. Provide Sensible Defaults

```python
# ✅ Good: Reasonable default
MESSAGE_GROUP_TIMEOUT: int = Field(default=30)

# ❌ Bad: No default (requires manual configuration)
MESSAGE_GROUP_TIMEOUT: int
```

## Security Considerations

### 1. Credential Isolation

- ✅ Credentials in `.env` (git-ignored)
- ✅ Per-user Git credentials encrypted
- ❌ Never store credentials in `config.yaml`
- ❌ Never log credential values

### 2. Setting Access Control

- ✅ Some settings cannot be changed via Telegram (credentials)
- ✅ Validate all user inputs
- ✅ Rate limit setting changes
- ❌ Don't expose sensitive settings in UI

### 3. File Permissions

- ✅ Restrict access to `.env` file (600)
- ✅ Restrict access to user overrides file (600)
- ✅ Validate file paths (prevent traversal)

## Troubleshooting

### Settings Not Loading

**Check loading priority:**

```bash
# 1. Check environment variables
echo $AGENT_TYPE

# 2. Check .env file
cat .env | grep AGENT_TYPE

# 3. Check config.yaml
grep AGENT_TYPE config.yaml

# 4. Check default values in code
grep "AGENT_TYPE.*Field" config/settings.py
```

### User Overrides Not Applied

**Debug steps:**

```python
# Check if override exists
overrides = settings_manager.list_user_overrides(user_id=123)
print(overrides)

# Check merged settings
all_settings = settings_manager.get_all_user_settings(user_id=123)
print(all_settings["AGENT_TIMEOUT"])

# Verify file contents
cat data/user_settings_overrides.json
```

### Validation Errors

**Enable debug logging:**

```python
import logging
logging.getLogger("config.settings").setLevel(logging.DEBUG)

# Will show detailed validation errors
```

## Related Documentation

- [Architecture Overview](overview.md) - System-wide architecture
- [User Guide: Settings Management](../user-guide/settings-management.md) - User-facing settings guide
- [Configuration Reference](../getting-started/configuration.md) - Configuration guide
- [Deployment: Configuration](../deployment/production.md#configuration) - Production configuration
