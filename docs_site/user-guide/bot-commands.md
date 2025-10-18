# Bot Commands

Complete reference for all tg-note bot commands.

---

## Working Modes

The bot has three working modes that you can switch between:

### /note — Note Creation Mode (Default)

Switches the bot to knowledge base creation mode.

Usage:
```
/note
```

Reply example:
```
📝 Note creation mode is active!

Your messages will be analyzed and saved to the knowledge base.
Send a message, a forward, or a document to process.

Switch: /ask | /agent
```

What it does:
- Analyze incoming messages
- Create structured notes in knowledge base
- Auto-categorize content
- Save to Git repository

---

### /ask — Question Mode

Switches the bot to question mode for querying your knowledge base.

Usage:
```
/ask
```

Requirement:
- Knowledge base must be configured via `/setkb`

Reply example:
```
🤔 Question mode is active!

You can now ask questions about your knowledge base.
The agent will search and answer based on your content.

Switch: /note | /agent
```

---

### /agent — Agent Mode (Full Access)

Switches the bot to agent mode with full autonomous capabilities.

Usage:
```
/agent
```

Requirement:
- Knowledge base must be configured via `/setkb`

Reply example:
```
🤖 Agent mode is active!

The agent can now perform any KB tasks:
• Answer questions
• Add new information
• Edit existing notes
• Restructure the knowledge base

Describe what to do; the agent will complete it autonomously.

Switch: /note | /ask
```

---

## Basic Commands

### /start
Initialize bot interaction.

Usage:
```
/start
```

### /help
Show help and quick links.

Usage:
```
/help
```

---

## Knowledge Base Commands

### /setkb
Setup or change knowledge base location.

Usage:
```
/setkb <name|url>
```

Examples:
```
# Local KB
/setkb my-notes

# GitHub repository
/setkb https://github.com/username/kb-repo

# Private repo (configure auth separately)
/setkb https://github.com/username/private-kb
```

### /kb
Show current knowledge base information.

Usage:
```
/kb
```

Returns:
- KB path
- KB type
- GitHub URL (if used)

### /setupmkdocs
Configure MkDocs for GitHub-based knowledge bases to build and deploy static documentation.

Usage:
```
/setupmkdocs
```

Requirements:
- Knowledge base must be GitHub-based (configured via `/setkb <github_url>`)
- MkDocs must not be already configured

What it does:
- Creates `mkdocs.yml` configuration file
- Sets up `docs/` directory with structured content
- Adds `.github/workflows/docs.yml` for automatic deployment
- Creates `requirements-docs.txt` with dependencies
- Updates `.gitignore` to exclude build artifacts

After running:
1. Commit and push changes to GitHub
2. Enable GitHub Pages in repo settings (Settings → Pages → Source: GitHub Actions)
3. Documentation will be automatically built and deployed on every push

Your docs will be available at: `https://<username>.github.io/<repo-name>/`

---

## Status

### /status
Show processing statistics and current mode.

Usage:
```
/status
```

Returns:
- Messages processed
- Pending groups
- Last processed time
- Knowledge base info
- Git integration status
- Current mode and how to switch

---

## Settings

### /settings
Open interactive settings menu.

### /viewsettings [category]
View all settings or filter by category.

### /resetsetting <name>
Reset a setting to default.

### /kbsettings
Quick access to KB settings.

### /agentsettings
Quick access to agent settings.

See also:
- Settings Management
- Working with Content
- Knowledge Base Setup
