# Secure Git Credentials via Telegram Bot

## Problem

When working with multiple users, there's a problem:
- ❌ Only one token can be stored in `.env` file
- ❌ All users use the same token
- ❌ Passing tokens through other channels is insecure

## Solution

✅ **Personal encrypted tokens for each user**

Now each user can securely add their personal GitHub or GitLab token directly through the Telegram bot!

## Security

🔐 **How it works:**

1. **Encryption**: Tokens are encrypted using Fernet (AES-128)
2. **Auto-delete**: Token messages are automatically deleted
3. **No logging**: Tokens don't appear in logs
4. **Secure storage**: Credential files have 600 permissions

## Quick Start

### 1. Install Dependencies

```bash
poetry install
# or
pip install -e .
```

This will install the new `cryptography` dependency for encryption.

### 2. Get Token

**GitHub:**
1. Go to: https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scope: `repo`
4. Copy token

**GitLab:**
1. Go to: https://gitlab.com/-/profile/personal_access_tokens
2. Create token
3. Select scope: `write_repository`
4. Copy token

### 3. Add Token via Bot

```
1. Open chat with bot
2. Send: /settoken
3. Choose platform (GitHub or GitLab)
4. Enter username
5. Enter token
6. ✅ Done! Token encrypted and saved
```

## Commands

### `/settoken` - Add Token
Safely adds your personal Git token. Supports GitHub and GitLab.

### `/listcredentials` - View Tokens
Shows information about saved tokens (without revealing the tokens themselves).

### `/removetoken` - Remove Token
Removes saved tokens for selected platform or all at once.

## How It Works Internally

### Credential Priority

When performing Git operations (pull, push, commit):

1. **Personal token** (from `/settoken`) - highest priority
2. **Global token** (from `.env`) - fallback

This means:
- Users with personal tokens use them automatically
- Users without personal tokens use global (if configured)

### Automatic Platform Detection

Bot automatically determines which token to use:

```
https://github.com/user/repo.git  → GitHub credentials
https://gitlab.com/user/repo.git  → GitLab credentials
```

### Credential Injection

When performing Git operations:

```
https://github.com/user/repo.git
    ↓
https://username:token@github.com/user/repo.git
```

## Architecture

```
┌─────────────────────────────────────────────┐
│           Telegram Bot                       │
│                                               │
│  User → /settoken → CredentialsHandlers     │
│                            ↓                  │
│                    CredentialsManager        │
│                            ↓                  │
│                    Encrypt (Fernet)          │
│                            ↓                  │
│                    Save to disk              │
│                                               │
│  Git Operation → GitOperations               │
│                            ↓                  │
│                    Get credentials           │
│                            ↓                  │
│                    Inject to URL             │
│                            ↓                  │
│                    Execute Git command       │
└─────────────────────────────────────────────┘
```

## Files

### New Files

- `src/knowledge_base/credentials_manager.py` - Encryption and storage manager
- `src/bot/credentials_handlers.py` - Telegram handlers for token management
- `docs_site/user-guide/secure-git-credentials.md` - Complete documentation

### Modified Files

- `config/settings.py` - Added `GITLAB_TOKEN` and `GITLAB_USERNAME`
- `src/knowledge_base/git_ops.py` - Support for personal credentials
- `src/services/agent_task_service.py` - Uses credentials_manager
- `src/services/note_creation_service.py` - Uses credentials_manager
- `src/bot/telegram_bot.py` - Integration of credentials_handlers
- `src/core/service_container.py` - Registration of credentials_manager
- `pyproject.toml` - Added `cryptography` dependency

### Credential Storage

After first use, these will be created:

- `./data/.credentials_key` - Encryption key (permissions: 600)
- `./data/user_credentials.enc` - Encrypted tokens (permissions: 600)

**⚠️ Important:**
- Don't delete the encryption key!
- Make backup copies of the key
- These files are already added to `.gitignore`

## Update .env

Now you can (optionally) add GitLab credentials to `.env`:

```env
# GitHub credentials (fallback)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_USERNAME=username

# GitLab credentials (fallback)
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_USERNAME=username
```

## Migration for Existing Users

If you already have a global GitHub token configured in `.env`:

1. It will continue to work as fallback
2. Users can add their personal tokens via `/settoken`
3. Personal tokens will have priority

## Testing

```bash
# Install dependencies
poetry install

# Start bot
poetry run tg-note

# In Telegram:
1. /settoken
2. Choose platform
3. Enter credentials
4. Check: /listcredentials
```

## Security FAQ

**Q: Is it safe to pass tokens through Telegram?**

A: Yes:
- Telegram uses encryption
- Message is automatically deleted
- Token is encrypted before storage
- Token doesn't appear in logs

**Q: Can the administrator see tokens?**

A: No, tokens are stored encrypted.

**Q: What if I lose the encryption key?**

A: Tokens become unreadable. You'll need to add them again via `/settoken`.

## Support

Questions and issues: https://github.com/ArtyomZemlyak/tg-note/issues

---

Made with ❤️ for secure multi-user Git operations
