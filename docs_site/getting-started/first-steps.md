# First Steps

Your first steps with tg-note after installation.

---

## 1. Get Your Telegram Bot Token

### Create a Bot with BotFather

1. Open Telegram and search for **@BotFather**
2. Start a chat and send `/newbot`
3. Follow the prompts:
   - Choose a **name** for your bot (e.g., "My Knowledge Bot")
   - Choose a **username** (must end in "bot", e.g., "my_knowledge_bot")
4. BotFather will give you a **token** - save it securely!

Example token format:

```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz12345678
```

### Add Token to Configuration

Add your token to `.env`:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz12345678
```

---

## 2. Get Your User ID (Optional)

If you want to restrict bot access to only yourself:

1. Open Telegram and search for **@userinfobot**
2. Start a chat and send any message
3. Bot will reply with your user info
4. Copy your **User ID**

Add to `config.yaml`:

```yaml
ALLOWED_USER_IDS: "123456789"  # Your user ID
```

---

## 3. Setup Knowledge Base

### Option A: Local Knowledge Base

Create a new local Git repository:

```bash
mkdir my-knowledge-base
cd my-knowledge-base
git init
git add .
git commit -m "Initial commit"
cd ..
```

Update `config.yaml`:

```yaml
KB_PATH: ./my-knowledge-base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: false  # No remote yet
```

### Option B: GitHub Knowledge Base

1. Create a new repository on GitHub (e.g., `my-kb`)
2. Clone it locally:

```bash
git clone https://github.com/yourusername/my-kb.git
```

3. Update `config.yaml`:

```yaml
KB_PATH: ./my-kb
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main
```

---

## 4. Start the Bot

```bash
poetry run python main.py
```

Expected output:

```
INFO - Starting tg-note bot...
INFO - Configuration validated successfully
INFO - Processing tracker initialized
INFO - Repository manager initialized
INFO - Telegram bot started successfully
INFO - Bot initialization completed
INFO - Press Ctrl+C to stop
```

---

## 5. Initialize Bot in Telegram

Open Telegram, find your bot, and send:

```
/start
```

Bot will greet you with an interactive menu showing:

- **📚 База знаний (Knowledge Base)** - Create or manage your KB
- **🔄 Режим работы (Work Mode)** - Switch between note-taking, Q&A, and agent modes
- **⚙️ Настройки (Settings)** - Configure bot behavior
- **🔧 MCP серверы (MCP Servers)** - Manage MCP integrations
- **💬 Контекст (Context)** - Manage conversation context
- **❓ Помощь (Help)** - Get help and documentation

---

## 6. Configure Knowledge Base via Interactive Menu

### Quick Setup: Click the Button

1. In the `/start` menu, click **➕ Создать БЗ (Create KB)**
2. Choose your KB type:
   - **📁 Локальная БЗ** - Create a local knowledge base
   - **🌐 GitHub репозиторий** - Connect a GitHub repository
3. Follow the prompts:
   - For local KB: Enter a name (e.g., `my-notes`)
   - For GitHub: Enter repository URL (e.g., `https://github.com/yourusername/my-kb`)

### Alternative: Use Commands

You can still use traditional commands:

```
/kb
```

This opens the KB management menu where you can:
- Create a new KB
- Switch between multiple KBs
- View KB information
- Setup MkDocs documentation (for GitHub repos)

---

## 7. Send Your First Message

Send or forward any message to the bot. Examples:

- Plain text message
- Forwarded message from a channel
- Article link
- Multiple messages

The bot will process and save it to your knowledge base!

---

## 8. Check Your Knowledge Base

Look in your KB directory:

```bash
ls -la my-knowledge-base/
```

You should see:

```
topics/
├── general/
│   └── 2025-10-03-your-first-note.md
└── index.md
```

---

## 9. Verify Git Commits

```bash
cd my-knowledge-base
git log --oneline
```

You should see automatic commits!

---

## 10. Explore Bot Commands

Try these commands:

```
/help      # Show all commands
/kb        # Show KB info
/status    # Show statistics
/settings  # Open settings menu
```

---

## Next Steps

<div class="grid cards" markdown>

- :material-book-multiple:{ .lg .middle } **Learn All Commands**

    ---

    Master all bot commands and features

    [:octicons-arrow-right-24: Bot Commands](../user-guide/bot-commands.md)

- :material-robot:{ .lg .middle } **Upgrade Your Agent**

    ---

    Install Qwen Code CLI for better AI processing

    [:octicons-arrow-right-24: Agent Setup](../agents/qwen-code-cli.md)

- :material-cog:{ .lg .middle } **Customize Settings**

    ---

    Configure bot behavior via Telegram

    [:octicons-arrow-right-24: Settings Guide](../user-guide/settings-management.md)

- :material-folder-open:{ .lg .middle } **Organize Your KB**

    ---

    Learn KB structure and organization

    [:octicons-arrow-right-24: KB Setup](../user-guide/knowledge-base-setup.md)

</div>

---

## Common First-Time Issues

### Bot Not Responding

1. Check if bot is running in terminal
2. Verify bot token in `.env`
3. Check logs: `tail -f logs/bot.log`

### "Not authorized" Error

- Wrong bot token
- Check `.env` file
- Restart the bot

### KB Not Created

- Check `KB_PATH` in config
- Ensure directory exists
- Check permissions

### Messages Not Saved

- Check logs for errors
- Verify KB setup: `/kb`
- Check Git status in KB folder

---

## Getting Help

- 📖 [Full Documentation](../index.md)
- 🐛 [Issue Tracker](https://github.com/ArtyomZemlyak/tg-note/issues)
- 💬 [Discussions](https://github.com/ArtyomZemlyak/tg-note/discussions)
