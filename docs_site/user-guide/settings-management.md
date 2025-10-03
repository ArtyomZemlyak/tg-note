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

```
/setsetting AGENT_TIMEOUT 600
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
- `AGENT_TIMEOUT` - Operation timeout
- `AGENT_ENABLE_WEB_SEARCH` - Enable web search
- `AGENT_ENABLE_GIT` - Enable Git operations
- `AGENT_ENABLE_GITHUB` - Enable GitHub API

### ⚙️ Processing

- `MESSAGE_GROUP_TIMEOUT` - Message grouping timeout
- `PROCESSED_LOG_PATH` - Processing log path

### 📝 Logging

- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE` - Log file path

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

```
/setsetting AGENT_TIMEOUT 600
```

### Disable Auto-Push

```
/setsetting KB_GIT_AUTO_PUSH false
```

### Enable Debug Logging

```
/setsetting LOG_LEVEL DEBUG
```

---

## See Also

- [Bot Commands](bot-commands.md)
- [Configuration Guide](../getting-started/configuration.md)
