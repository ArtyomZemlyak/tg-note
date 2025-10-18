# Knowledge Base Setup

Setup and manage your knowledge base.

---

## Creating a Knowledge Base

### Option 1: Local KB (via bot)

Recommended: create and initialize a local KB directly from Telegram using the command:

```
/setkb my-kb
```

This will create a new KB under the bot's KB root and initialize Git.

Alternatively, you can prepare one manually:

```bash
mkdir my-kb
cd my-kb
git init
git commit --allow-empty -m "Initial commit"
```

Configure in `config.yaml`:

```yaml
KB_PATH: ./my-kb
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: false
```

### Option 2: GitHub KB

1. Create repo on GitHub
2. Clone locally
3. Configure path or simply use the Telegram command:

```
/setkb https://github.com/yourusername/my-kb
```

Alternatively, configure the path manually:

```yaml
KB_PATH: ./my-kb
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main
```

#### Setting up Static Documentation for GitHub KB

For GitHub-based knowledge bases, you can automatically configure MkDocs to build and deploy static documentation to GitHub Pages:

```
/setupmkdocs
```

This command will:

- **Check** if your KB is GitHub-based (command only works with GitHub repos)
- **Verify** that MkDocs is not already configured
- **Create** all necessary files:
  - `mkdocs.yml` - MkDocs configuration with Material theme
  - `docs/` - Documentation directory with structured content
  - `.github/workflows/docs.yml` - GitHub Actions workflow for automatic deployment
  - `requirements-docs.txt` - Python dependencies for building docs

**After running the command:**

1. Commit and push the changes to GitHub
2. Enable GitHub Pages in repository settings:
   - Go to: **Settings → Pages → Source: GitHub Actions**
3. After push, documentation will be automatically built and published

Your documentation will be available at:
```
https://<username>.github.io/<repo-name>/
```

**Features:**

- ✨ Beautiful Material theme with dark/light mode
- 🔍 Full-text search
- 📱 Mobile-responsive design
- 🏷️ Tags and categories
- 🔗 Automatic navigation from KB structure
- 📝 Markdown extensions (code highlighting, admonitions, etc.)
- 🤖 Automatic deployment on every push

---

## KB Structure

```
knowledge_base/
├── topics/           # Categorized notes
│   ├── ai/
│   ├── biology/
│   ├── physics/
│   └── tech/
├── attachments/      # Media files
└── index.md          # KB index
```

---

## Git Integration

Enable Git operations:

```yaml
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
```

Every note is automatically:

- Added to Git
- Committed with message
- Pushed to remote (if enabled)

### Multi-User Synchronization

When multiple users work with the same knowledge base (shared GitHub repository), the system automatically:

1. **Serializes operations**: Only one user can modify the KB at a time using file-based locks
2. **Pulls latest changes**: Before creating a note, the system pulls the latest changes from GitHub (in note mode)
3. **Prevents conflicts**: Operations are queued and executed sequentially

This applies to both:
- **Note mode** (`/note`): Creating notes from messages
- **Agent mode** (`/agent`): Agent tasks that may read/write KB files

This ensures that:
- No merge conflicts occur
- All users see the latest version of the KB
- Changes are properly synchronized across users
- Safe concurrent access in both note and agent modes

**Example scenario:**
- User A starts creating a note (or executing agent task) → KB is locked
- User B tries to create a note (or execute agent task) → Waits for User A to finish
- User A's operation completes and changes are pushed → Lock is released
- User B's operation starts → (In note mode: pulls latest changes including User A's changes)
- User B's operation completes and changes are pushed

**Technical details:**
- Uses `filelock` for cross-process synchronization
- Lock file: `.kb_operations.lock` in KB directory
- Async locks prevent race conditions within the same process
- Default timeout: 300 seconds (5 minutes)

---

## See Also

- [Bot Commands](bot-commands.md)
- [Working with Content](working-with-content.md)
- [KB Synchronization Architecture](../architecture/kb-synchronization.md)
