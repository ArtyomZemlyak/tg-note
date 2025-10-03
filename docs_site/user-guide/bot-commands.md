# Bot Commands

Complete reference for all tg-note bot commands.

---

## Basic Commands

### /start

Initialize interaction with the bot.

**Usage:**
```
/start
```

**Response:**
- Welcome message
- Bot introduction
- Quick start instructions

---

### /help

Display help information and available commands.

**Usage:**
```
/help
```

**Response:**
- List of all commands
- Brief descriptions
- Links to documentation

---

## Knowledge Base Commands

### /setkb

Setup or change your knowledge base location.

**Usage:**
```
/setkb <name|url>
```

**Examples:**

```
# Local knowledge base
/setkb my-notes

# GitHub repository
/setkb https://github.com/username/kb-repo

# Private repo (configure auth separately)
/setkb https://github.com/username/private-kb
```

**What it does:**
- Creates or connects to a knowledge base
- Initializes Git if needed
- Sets up directory structure

---

### /kb

Show current knowledge base information.

**Usage:**
```
/kb
```

**Response:**
- KB path
- Git status
- Number of files
- Last commit info

---

### /status

Display processing statistics.

**Usage:**
```
/status
```

**Response:**
- Messages processed
- Notes created
- Success/failure rate
- Agent type in use

---

## Settings Commands

### /settings

Open interactive settings menu.

**Usage:**
```
/settings
```

**Features:**
- Browse settings by category
- Interactive inline keyboard
- Quick toggles for boolean values
- Detailed setting information

**Categories:**
- 📚 Knowledge Base
- 🤖 Agent Configuration
- ⚙️ Processing
- 📝 Logging

[Learn more →](settings-management.md)

---

### /viewsettings

View all settings or filtered by category.

**Usage:**
```
/viewsettings [category]
```

**Examples:**

```
# View all settings
/viewsettings

# View specific category
/viewsettings knowledge_base
/viewsettings agent
/viewsettings processing
```

**Response:**
- Setting name
- Current value
- Default value
- Description

---

### /setsetting

Change a specific setting value.

**Usage:**
```
/setsetting <name> <value>
```

**Examples:**

```
# Boolean settings
/setsetting KB_GIT_ENABLED true
/setsetting KB_GIT_AUTO_PUSH false

# Numeric settings
/setsetting AGENT_TIMEOUT 600
/setsetting MESSAGE_GROUP_TIMEOUT 60

# String settings
/setsetting AGENT_TYPE qwen_code_cli
/setsetting LOG_LEVEL DEBUG
```

**Supported Types:**
- Boolean: `true`, `false`, `1`, `0`, `yes`, `no`
- Integer: Any number
- String: Any text
- Path: File system paths

---

### /resetsetting

Reset a setting to its default value.

**Usage:**
```
/resetsetting <name>
```

**Examples:**

```
/resetsetting KB_GIT_AUTO_PUSH
/resetsetting AGENT_TIMEOUT
/resetsetting LOG_LEVEL
```

---

### /kbsettings

Quick access to Knowledge Base settings.

**Usage:**
```
/kbsettings
```

**Shows:**
- KB_PATH
- KB_GIT_ENABLED
- KB_GIT_AUTO_PUSH
- KB_GIT_REMOTE
- KB_GIT_BRANCH

---

### /agentsettings

Quick access to Agent settings.

**Usage:**
```
/agentsettings
```

**Shows:**
- AGENT_TYPE
- AGENT_MODEL
- AGENT_TIMEOUT
- AGENT_ENABLE_WEB_SEARCH
- AGENT_ENABLE_GIT
- AGENT_ENABLE_GITHUB

---

## Message Processing

### Send Text Message

Simply send any text message to save it.

**Example:**
```
This is an interesting article about AI...
```

**Processing:**
1. Message received
2. Analyzed by agent
3. Categorized automatically
4. Saved as Markdown
5. Committed to Git

---

### Forward Message

Forward messages from any chat or channel.

**How:**
1. Find message to save
2. Tap Forward
3. Select your tg-note bot

**Supports:**
- Channel posts
- Group messages
- Media with captions
- Links and URLs

---

### Send Multiple Messages

Send consecutive messages - they'll be grouped automatically.

**Example:**
```
First message about a topic...
(Send)
Second message with more details...
(Send)
Third message with conclusion...
```

**Processing:**
- Bot waits 30 seconds (configurable)
- Groups related messages
- Creates single note

---

### Send Links

Send article links for processing.

**Example:**
```
https://arxiv.org/abs/12345
```

**With Qwen Code CLI:**
- Fetches article content
- Analyzes and summarizes
- Extracts key information
- Saves structured note

---

## Command Reference Table

| Command | Arguments | Description | Example |
|---------|-----------|-------------|---------|
| `/start` | - | Initialize bot | `/start` |
| `/help` | - | Show help | `/help` |
| `/setkb` | `<name\|url>` | Setup KB | `/setkb my-notes` |
| `/kb` | - | Show KB info | `/kb` |
| `/status` | - | Show statistics | `/status` |
| `/settings` | - | Settings menu | `/settings` |
| `/viewsettings` | `[category]` | View settings | `/viewsettings agent` |
| `/setsetting` | `<name> <value>` | Change setting | `/setsetting LOG_LEVEL DEBUG` |
| `/resetsetting` | `<name>` | Reset setting | `/resetsetting AGENT_TIMEOUT` |
| `/kbsettings` | - | KB settings | `/kbsettings` |
| `/agentsettings` | - | Agent settings | `/agentsettings` |

---

## Tips & Tricks

### Quick Configuration

```
/settings → Choose category → Select setting → Change value
```

### Batch Changes

```
/setsetting AGENT_TIMEOUT 600
/setsetting KB_GIT_AUTO_PUSH true
/setsetting LOG_LEVEL DEBUG
```

### View Before Change

```
/viewsettings agent
# Review current values
/setsetting AGENT_TYPE qwen_code_cli
```

### Reset All (Individual)

```
/resetsetting KB_GIT_AUTO_PUSH
/resetsetting AGENT_TIMEOUT
/resetsetting MESSAGE_GROUP_TIMEOUT
```

---

## See Also

- [Settings Management Guide](settings-management.md)
- [Working with Content](working-with-content.md)
- [Knowledge Base Setup](knowledge-base-setup.md)
