# Settings Management via Telegram

## Overview

The tg-note bot now supports comprehensive settings management directly through Telegram commands. This feature allows users to customize their bot behavior without modifying configuration files.

## Features

### 🔧 Automatic Settings Discovery
- Automatically introspects all pydantic-settings fields
- Generates Telegram commands dynamically
- Provides categorized settings organization

### 👤 Per-User Settings
- Each user can have their own settings overrides
- Settings are stored separately from global defaults
- Easy to reset to default values

### 🎨 Interactive UI
- Inline keyboard menus for easy navigation
- Category-based organization
- Quick toggle buttons for boolean settings

### 🔒 Security
- Secret fields (API keys, tokens) cannot be changed via Telegram
- Readonly fields are protected
- Sensitive data is hidden from view

## Architecture

### Components

1. **SettingsInspector** (`src/bot/settings_manager.py`)
   - Introspects pydantic-settings `Settings` class
   - Extracts field metadata (type, description, default, etc.)
   - Categorizes settings automatically

2. **UserSettingsStorage** (`src/bot/settings_manager.py`)
   - Stores per-user settings overrides in JSON
   - Thread-safe with file locking
   - Separate from KB user settings

3. **SettingsManager** (`src/bot/settings_manager.py`)
   - Combines global and user-specific settings
   - Handles value conversion and validation
   - Provides unified settings access

4. **SettingsHandlers** (`src/bot/settings_handlers.py`)
   - Telegram command handlers
   - Inline keyboard UI
   - Auto-generated from settings metadata

## Usage

### Telegram Commands

#### View Settings Menu
```
/settings
```
Shows an interactive menu with all settings categories.

#### View All Settings
```
/viewsettings
```
Shows all settings with current values.

```
/viewsettings knowledge_base
```
Shows settings for a specific category.

#### Change a Setting
```
/setsetting KB_GIT_ENABLED true
/setsetting AGENT_TIMEOUT 600
/setsetting MESSAGE_GROUP_TIMEOUT 60
```

#### Reset to Default
```
/resetsetting KB_GIT_ENABLED
```
Resets a setting to the global default value.

#### Category-Specific Views
```
/kbsettings      # Knowledge Base settings
/agentsettings   # Agent configuration
```

### Interactive Menu

The `/settings` command provides an interactive menu with:

1. **Category Selection** - Browse settings by category
2. **Quick Toggles** - One-tap toggle for boolean settings
3. **Setting Details** - View descriptions and current values
4. **Reset Options** - Restore defaults easily

## Settings Categories

### 📚 Knowledge Base (`knowledge_base`)
- `KB_PATH` - Path to knowledge base directory
- `KB_GIT_ENABLED` - Enable Git operations
- `KB_GIT_AUTO_PUSH` - Automatically push changes
- `KB_GIT_REMOTE` - Git remote name
- `KB_GIT_BRANCH` - Git branch name

### 🤖 Agent (`agent`)
- `AGENT_TYPE` - Agent implementation type
- `AGENT_MODEL` - AI model to use
- `AGENT_TIMEOUT` - Operation timeout in seconds
- `AGENT_ENABLE_WEB_SEARCH` - Enable web search
- `AGENT_ENABLE_GIT` - Enable Git operations
- `AGENT_ENABLE_GITHUB` - Enable GitHub API
- `AGENT_ENABLE_SHELL` - Enable shell commands

### ⚙️ Processing (`processing`)
- `MESSAGE_GROUP_TIMEOUT` - Message grouping timeout
- `PROCESSED_LOG_PATH` - Path to processed messages log

### 📝 Logging (`logging`)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE` - Path to log file

### 🔒 Security (`security`)
- `ALLOWED_USER_IDS` - List of allowed user IDs

### 🔑 Credentials (`credentials`)
These settings are **read-only** via Telegram for security:
- API keys and tokens
- Must be set in `.env` file or environment variables

## Implementation Details

### Settings Introspection

The system uses pydantic's field metadata to automatically extract:

```python
class Settings(BaseSettings):
    KB_GIT_ENABLED: bool = Field(
        default=True,
        description="Enable Git operations"  # Used in UI
    )
```

The `SettingsInspector` reads this and generates:
- Command name: `kb_git_enabled`
- Category: `knowledge_base` (from `KB_` prefix)
- Type: `bool` (for validation)
- Description: "Enable Git operations" (for help text)

### Value Conversion

The system automatically converts string input to the correct type:

- **Boolean**: `true`, `1`, `yes`, `on`, `enabled` → `True`
- **Integer**: `"300"` → `300`
- **Float**: `"3.14"` → `3.14`
- **Path**: `"./data"` → `Path("./data")`

### Storage Format

User settings are stored in `./data/user_settings_overrides.json`:

```json
{
  "123456789": {
    "KB_GIT_ENABLED": false,
    "AGENT_TIMEOUT": 600,
    "MESSAGE_GROUP_TIMEOUT": 45
  },
  "987654321": {
    "KB_GIT_AUTO_PUSH": false
  }
}
```

### Settings Priority

1. User-specific override (highest priority)
2. Global default from config.yaml
3. pydantic default value (lowest priority)

## Extension Guide

### Adding New Settings

1. Add field to `Settings` class in `config/settings.py`:
```python
NEW_FEATURE_ENABLED: bool = Field(
    default=True,
    description="Enable new feature"
)
```

2. The setting is **automatically**:
   - Categorized (based on prefix)
   - Available via `/settings` command
   - Validated with correct type
   - Stored per-user

### Custom Categories

Add prefixes to `SettingsInspector.CATEGORIES`:

```python
CATEGORIES = {
    "MY_PREFIX_": "my_category",
    # ...
}
```

### Secret Fields

Mark sensitive fields in `SettingsInspector.SECRET_FIELDS`:

```python
SECRET_FIELDS = {
    "MY_SECRET_KEY",
    # ...
}
```

### Readonly Fields

Prevent changes via Telegram:

```python
READONLY_FIELDS = {
    "MY_READONLY_FIELD",
    # ...
}
```

## Security Considerations

1. **Credentials Protection**: API keys and tokens cannot be changed via Telegram
2. **Field Validation**: All values are validated before storage
3. **Type Safety**: pydantic ensures type correctness
4. **File Locking**: Thread-safe storage with filelock
5. **User Isolation**: Each user's settings are separate

## Future Enhancements

- [ ] Settings export/import
- [ ] Settings templates
- [ ] Bulk settings update
- [ ] Settings history/audit log
- [ ] Validation rules from pydantic constraints
- [ ] Advanced type support (lists, dicts, enums)
- [ ] Settings search functionality

## Troubleshooting

### Setting not appearing
- Check if it's marked as `SECRET` or `READONLY`
- Verify the field is in `Settings` class
- Check category assignment

### Value not updating
- Ensure correct type format
- Check validation errors in bot response
- Verify user has permission to change setting

### Reset not working
- Confirm global default exists
- Check file permissions for storage file
- Review logs for errors

## Example Workflow

1. **User wants to disable Git auto-push**:
   ```
   /kbsettings
   # Click "Disable Auto-Push" button
   # Or use: /setsetting KB_GIT_AUTO_PUSH false
   ```

2. **User wants to increase agent timeout**:
   ```
   /agentsettings
   # Click "Set Timeout: 600s" button
   # Or use: /setsetting AGENT_TIMEOUT 600
   ```

3. **User wants to view all settings**:
   ```
   /viewsettings
   # See all categories and values
   ```

4. **User wants to reset everything**:
   ```
   /resetsetting KB_GIT_AUTO_PUSH
   /resetsetting AGENT_TIMEOUT
   # Or manually delete user_settings_overrides.json
   ```

## Related Files

- `config/settings.py` - Main settings definition
- `src/bot/settings_manager.py` - Settings introspection and storage
- `src/bot/settings_handlers.py` - Telegram command handlers
- `src/bot/telegram_bot.py` - Bot integration
- `./data/user_settings_overrides.json` - Per-user overrides
