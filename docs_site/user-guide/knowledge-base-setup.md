# Knowledge Base Setup

Setup and manage your knowledge base.

---

## Creating a Knowledge Base

### Option 1: Local KB

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
3. Configure path

```yaml
KB_PATH: ./my-kb
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main
```

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

---

## See Also

- [Bot Commands](bot-commands.md)
- [Working with Content](working-with-content.md)
