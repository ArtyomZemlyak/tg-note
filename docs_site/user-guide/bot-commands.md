# Bot Commands

Complete reference for all tg-note bot commands.

---

## Working Modes

The bot has three working modes that you can switch between:

### /note - Note Creation Mode (Default)

Switches the bot to knowledge base creation mode.

**Usage:**

```
/note
```

**Response:**

```
📝 Режим создания базы знаний активирован!

Теперь ваши сообщения будут анализироваться и сохраняться в базу знаний.
Отправьте сообщение, репост или документ для обработки.

Для переключения в режим вопросов используйте /ask
```

**What it does:**

- Bot analyzes incoming messages
- Creates structured notes in knowledge base
- Automatically categorizes content
- Saves to Git repository

---

### /ask - Question Mode

Switches the bot to question mode for querying your knowledge base.

**Usage:**

```
/ask
```

**Requirements:**

- Knowledge base must be set up via `/setkb`

**Response:**

```
🤔 Режим вопросов по базе знаний активирован!

Теперь вы можете задавать вопросы агенту о содержимому вашей базы знаний.
Агент будет искать информацию в базе и отвечать на ваши вопросы.

Для возврата в режим создания заметок используйте /note
Для переключения в режим агента используйте /agent
```

**What it does:**

- Accepts questions about knowledge base content
- Agent searches for relevant information using KB reading tools
- Provides answers based on found content
- Shows sources of information

**Example interaction:**

```
User: /ask
Bot: 🤔 Режим вопросов по базе знаний активирован!

User: Что такое GPT-4?
Bot: 🔍 Ищу информацию в базе знаний...
     💡 Ответ:

     GPT-4 - это большая языковая модель от OpenAI...

     Источники:
     - ai/models/gpt4.md
     - ai/multimodal/vision.md
```

---

### /agent - Agent Mode (Full Access)

Switches the bot to agent mode with full autonomous capabilities.

**Usage:**

```
/agent
```

**Requirements:**

- Knowledge base must be set up via `/setkb`

**Response:**

```
🤖 Режим агента активирован!

Теперь агент может выполнять любые задачи с вашей базой знаний:
• Отвечать на вопросы
• Добавлять новую информацию
• Редактировать существующие заметки
• Переструктурировать базу знаний
• И многое другое!

Просто опишите что нужно сделать, и агент выполнит задачу автономно.

Переключить: /note | /ask
```

**What it does:**

- Accepts any tasks related to knowledge base
- Can answer questions (like /ask mode)
- Can add/edit/delete/restructure content
- Has full autonomous access to KB (restricted to topics/ folder by default)
- Shows detailed results with file changes

**Example interactions:**

**Answering questions:**

```
User: Что такое GPT-4?
Bot: 💡 Ответ:
     GPT-4 - это большая языковая модель от OpenAI...
```

**Adding information:**

```
User: Добавь информацию о новой модели Gemini 2.0
Bot: 📋 Выполнено: Добавлена информация о Gemini 2.0
     📝 Изменения:
       ✨ Создано файлов: 1
         • ai/models/gemini-2.0.md
```

**Restructuring:**

```
User: Переименуй папку "ml" в "machine-learning"
Bot: 📋 Выполнено: Папка переименована, ссылки обновлены
     📝 Изменения:
       📁 Создано папок: 1
         • machine-learning
       ✏️ Изменено файлов: 5
```

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
- Information about working modes

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
- Working modes information

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

Display processing statistics and current working mode.

**Usage:**

```
/status
```

**Response:**

- Messages processed
- Notes created
- Success/failure rate
- Agent type in use
- **Current working mode** (Note Creation or Question Mode)
- Knowledge base information
- Git integration status

**Example:**

```
📊 Статистика обработки

Всего обработано сообщений: 10
Ожидает обработки: 0
Последняя обработка: 2024-01-01 12:00:00

База знаний: my-notes (local)
Git интеграция: Включена

📝 Текущий режим: Создание базы знаний
Переключить: /note | /ask | /agent
```

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
| `/note` | - | Switch to note creation mode | `/note` |
| `/ask` | - | Switch to question mode | `/ask` |
| `/agent` | - | Switch to agent mode (full access) | `/agent` |
| `/setkb` | `<name\|url>` | Setup KB | `/setkb my-notes` |
| `/kb` | - | Show KB info | `/kb` |
| `/status` | - | Show statistics and mode | `/status` |
| `/settings` | - | Settings menu | `/settings` |
| `/viewsettings` | `[category]` | View settings | `/viewsettings agent` |
| `/resetsetting` | `<name>` | Reset setting | `/resetsetting AGENT_TIMEOUT` |
| `/kbsettings` | - | KB settings | `/kbsettings` |
| `/agentsettings` | - | Agent settings | `/agentsettings` |

---

## Tips & Tricks

### Quick Configuration

```
/settings → Choose category → Select setting → Change value
```

### View Settings

```
/viewsettings
/viewsettings agent
/viewsettings knowledge_base
```

### Interactive Changes

```
/settings
# Navigate through categories
# Click on setting to change
# For boolean: Use Enable/Disable buttons
# For others: Send new value
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
