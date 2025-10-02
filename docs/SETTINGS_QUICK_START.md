# Settings Management - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Open Settings Menu

Send this command to the bot:
```
/settings
```

You'll see an interactive menu with categories:
```
⚙️ Settings Menu

Choose a category to view and modify settings:

• Settings are stored per-user
• You can override global defaults
• Use /viewsettings to see all settings

[📚 Knowledge Base] [🤖 Agent]
[⚙️ Processing]    [📝 Logging]
[🔒 Security]      [🔧 General]
```

### Step 2: View Settings in a Category

Click on **📚 Knowledge Base** or use:
```
/kbsettings
```

You'll see:
```
📚 Knowledge Base Settings

• KB_PATH: ./knowledge_base
  Path to knowledge base

• KB_GIT_ENABLED: ✅ enabled
  Enable Git operations

• KB_GIT_AUTO_PUSH: ✅ enabled
  Auto-push to remote

• KB_GIT_REMOTE: origin
  Git remote name

• KB_GIT_BRANCH: main
  Git branch name

[✅ Enable Git]    [❌ Disable Git]
[✅ Enable Auto-Push] [❌ Disable Auto-Push]
```

### Step 3: Change a Setting

**Option A: Use Toggle Button**

Just click the button! For example, click **❌ Disable Auto-Push**

**Option B: Use Command**
```
/setsetting KB_GIT_AUTO_PUSH false
```

You'll get confirmation:
```
✅ Setting KB_GIT_AUTO_PUSH updated to: False
```

### Step 4: View All Your Settings

```
/viewsettings
```

See all your custom settings:
```
⚙️ All Settings

KNOWLEDGE_BASE:
• KB_PATH: ./knowledge_base
• KB_GIT_ENABLED: ✅ enabled
• KB_GIT_AUTO_PUSH: ❌ disabled  ← Changed!
• KB_GIT_REMOTE: origin
• KB_GIT_BRANCH: main

AGENT:
• AGENT_TYPE: qwen_code_cli
• AGENT_TIMEOUT: 300
• AGENT_ENABLE_WEB_SEARCH: ✅ enabled
...
```

### Step 5: Reset to Default

Changed your mind? Reset easily:
```
/resetsetting KB_GIT_AUTO_PUSH
```

Confirmation:
```
✅ Setting KB_GIT_AUTO_PUSH reset to default: True
```

## 🎯 Common Use Cases

### Use Case 1: Increase Agent Timeout

**Scenario**: Agent operations are timing out

**Solution**:
```
/setsetting AGENT_TIMEOUT 600
```

Or use interactive menu:
```
/agentsettings
[Set Timeout: 300s] [Set Timeout: 600s] ← Click this
```

### Use Case 2: Disable Web Search

**Scenario**: You want faster responses, don't need web search

**Solution**:
```
/setsetting AGENT_ENABLE_WEB_SEARCH false
```

Or:
```
/agentsettings
[Disable Web Search] ← Click this
```

### Use Case 3: Change Message Grouping Timeout

**Scenario**: Messages are grouped too quickly

**Solution**:
```
/setsetting MESSAGE_GROUP_TIMEOUT 60
```

This changes from default 30s to 60s.

### Use Case 4: Disable Git Integration

**Scenario**: Testing without committing to Git

**Solution**:
```
/kbsettings
[Disable Git] ← Click this
```

Or:
```
/setsetting KB_GIT_ENABLED false
```

### Use Case 5: View Only KB Settings

**Scenario**: Only interested in KB configuration

**Solution**:
```
/viewsettings knowledge_base
```

## 📋 Settings Reference

### Knowledge Base Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `KB_PATH` | Path | `./knowledge_base` | Path to KB directory |
| `KB_GIT_ENABLED` | bool | `true` | Enable Git operations |
| `KB_GIT_AUTO_PUSH` | bool | `true` | Auto-push commits |
| `KB_GIT_REMOTE` | str | `origin` | Git remote name |
| `KB_GIT_BRANCH` | str | `main` | Git branch name |

**Quick Access**: `/kbsettings`

### Agent Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `AGENT_TYPE` | str | `stub` | Agent implementation |
| `AGENT_MODEL` | str | `qwen-max` | AI model to use |
| `AGENT_TIMEOUT` | int | `300` | Timeout in seconds |
| `AGENT_ENABLE_WEB_SEARCH` | bool | `true` | Enable web search |
| `AGENT_ENABLE_GIT` | bool | `true` | Enable Git operations |
| `AGENT_ENABLE_GITHUB` | bool | `true` | Enable GitHub API |

**Quick Access**: `/agentsettings`

### Processing Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `MESSAGE_GROUP_TIMEOUT` | int | `30` | Grouping timeout (seconds) |
| `PROCESSED_LOG_PATH` | Path | `./data/processed.json` | Processing log path |

### Logging Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `LOG_LEVEL` | str | `INFO` | Logging level |
| `LOG_FILE` | Path | `./logs/bot.log` | Log file path |

## 💡 Tips & Tricks

### Tip 1: Start with Interactive Menu

Use `/settings` to explore visually before using commands.

### Tip 2: Use Category Shortcuts

Faster than navigating menus:
- `/kbsettings` for Knowledge Base
- `/agentsettings` for Agent

### Tip 3: View Before Changing

Check current value first:
```
/viewsettings knowledge_base
```

### Tip 4: Experiment Safely

All changes are per-user and reversible:
```
/resetsetting SETTING_NAME
```

### Tip 5: Boolean Values

Multiple ways to set boolean values:
```
/setsetting KB_GIT_ENABLED true   ✅
/setsetting KB_GIT_ENABLED 1      ✅
/setsetting KB_GIT_ENABLED yes    ✅
/setsetting KB_GIT_ENABLED on     ✅

/setsetting KB_GIT_ENABLED false  ✅
/setsetting KB_GIT_ENABLED 0      ✅
/setsetting KB_GIT_ENABLED no     ✅
```

## 🚫 What You CANNOT Change

### Secret Settings (For Security)

These are **read-only** and shown as `***hidden***`:
- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `QWEN_API_KEY`
- `GITHUB_TOKEN`

**Why?** Security - credentials must be set in `.env` file.

### Readonly Settings

These settings cannot be changed via Telegram:
- `TELEGRAM_BOT_TOKEN` - Would disconnect the bot

## ❓ Troubleshooting

### Problem: Setting Not Appearing

**Possible Causes**:
1. It's a secret field (API keys, tokens)
2. It's marked as readonly
3. Wrong category

**Solution**: Use `/viewsettings` to see all available settings.

### Problem: Value Not Updating

**Check**:
1. Correct setting name (case-sensitive)
2. Valid value for the type
3. Not a readonly field

**Example Error**:
```
/setsetting AGENT_TIMEOUT not_a_number
❌ Invalid value: could not convert string to float
```

**Correct**:
```
/setsetting AGENT_TIMEOUT 600
✅ Setting AGENT_TIMEOUT updated to: 600
```

### Problem: Want to Reset All Settings

**Solution**: Reset one by one:
```
/resetsetting KB_GIT_AUTO_PUSH
/resetsetting AGENT_TIMEOUT
...
```

Or manually delete the storage file (advanced):
```bash
rm ./data/user_settings_overrides.json
```

## 🎓 Learning Path

### Beginner
1. ✅ Use `/settings` to explore categories
2. ✅ Try `/kbsettings` and `/agentsettings`
3. ✅ Change one setting with toggle button
4. ✅ Reset it back with `/resetsetting`

### Intermediate
1. ✅ Use `/viewsettings` to see all settings
2. ✅ Use `/setsetting` command directly
3. ✅ Filter settings by category
4. ✅ Customize your workflow

### Advanced
1. ✅ Understand setting categories
2. ✅ Know all setting types and defaults
3. ✅ Use settings in combination
4. ✅ Create optimal configuration

## 📚 Examples

### Example 1: Developer Setup

Disable Git for faster testing:
```
/setsetting KB_GIT_ENABLED false
/setsetting AGENT_TIMEOUT 120
/setsetting LOG_LEVEL DEBUG
```

### Example 2: Production Setup

Enable all Git features:
```
/setsetting KB_GIT_ENABLED true
/setsetting KB_GIT_AUTO_PUSH true
/setsetting LOG_LEVEL WARNING
```

### Example 3: Quick Processing

Faster message grouping:
```
/setsetting MESSAGE_GROUP_TIMEOUT 15
/setsetting AGENT_TIMEOUT 120
```

### Example 4: Thorough Processing

Longer timeouts for complex content:
```
/setsetting MESSAGE_GROUP_TIMEOUT 60
/setsetting AGENT_TIMEOUT 900
/setsetting AGENT_ENABLE_WEB_SEARCH true
```

## 🔗 Related Commands

| Command | Purpose |
|---------|---------|
| `/help` | Show all commands |
| `/status` | View processing stats |
| `/kb` | View KB info |
| `/setkb` | Setup KB |

## 📖 Further Reading

- [Full Settings Documentation](SETTINGS_MANAGEMENT.md)
- [Architecture Guide](SETTINGS_ARCHITECTURE.md)
- [Code Examples](../examples/settings_example.py)

---

**Questions?** Just type `/help` in the bot! 🤖
