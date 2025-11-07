# Settings Management

Configure tg-note directly from Telegram.

---

## Overview

The settings management system allows you to customize bot behavior without editing configuration files. All settings can be changed directly through Telegram commands.

---

## Features

- ✅ **Interactive UI** - Inline keyboards with category navigation
- ✅ **Type Safety** - Automatic validation and conversion
- ✅ **Per-User** - Each user has their own settings
- ✅ **Auto-Generated** - New settings appear automatically
- ✅ **Secure** - Credentials cannot be changed via Telegram

---

## Quick Start

### Open Settings Menu

```
/settings
```

### View All Settings

```
/viewsettings
```

### Change a Setting

Use the interactive menu and inline buttons:

```
/settings → choose category → select setting → use buttons or send value
```

### Reset to Default

```
/resetsetting AGENT_TIMEOUT
```

---

## Settings Categories

### 📚 Knowledge Base

- `KB_PATH` - Path to knowledge base
- `KB_GIT_ENABLED` - Enable Git operations  
- `KB_GIT_AUTO_PUSH` - Auto-push changes
- `KB_GIT_REMOTE` - Git remote name
- `KB_GIT_BRANCH` - Git branch

### 🤖 Agent

- `AGENT_TYPE` - Agent implementation
- `AGENT_MODEL` - AI model to use
- `AGENT_QWEN_CLI_PATH` - Path to qwen CLI executable
- `AGENT_INSTRUCTION` - Custom instruction for agent
- `AGENT_TIMEOUT` - Operation timeout
- `AGENT_ENABLE_WEB_SEARCH` - Enable web search
- `AGENT_ENABLE_GIT` - Enable Git operations
- `AGENT_ENABLE_GITHUB` - Enable GitHub API
- `AGENT_ENABLE_SHELL` - Enable shell commands (⚠️ security risk)
- `AGENT_ENABLE_FILE_MANAGEMENT` - Enable file operations
- `AGENT_ENABLE_FOLDER_MANAGEMENT` - Enable folder operations

### ⚙️ Processing

- `MESSAGE_GROUP_TIMEOUT` - Message grouping timeout
- `PROCESSED_LOG_PATH` - Processing log path

### 📝 Logging

- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE` - Log file path

### 🔑 Credentials

Credentials category contains API keys and authentication tokens. These settings are **read-only** via the settings menu for security reasons. Use the `/settoken` command to manage Git credentials (GitHub/GitLab tokens).

**Note:** Credentials cannot be changed through `/settings` menu. Use `/settoken` command for Git credentials or set them in `.env` file for global defaults.

---

## Interactive Menu

The `/settings` command provides:

1. **Category Selection** - Browse by category
2. **Quick Toggles** - One-tap for booleans
3. **Setting Details** - View descriptions
4. **Reset Options** - Restore defaults

---

## Examples

### Change Timeout

Open `/settings`, navigate to Agent category, select `AGENT_TIMEOUT`, and set it to `600`.

### Disable Auto-Push

Open `/settings`, navigate to Knowledge Base category, and toggle `KB_GIT_AUTO_PUSH` to off.

### Enable Debug Logging

Open `/settings`, navigate to Logging, select `LOG_LEVEL`, and choose `DEBUG`.

---

## See Also

- [Bot Commands](bot-commands.md)
- [Configuration Guide](../getting-started/configuration.md)
