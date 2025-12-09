# Git Credentials Management

## Overview

tg-note supports secure, per-user storage of Git credentials (GitHub/GitLab tokens). This enables:

- 🔐 **Secure storage**: tokens are encrypted with Fernet (AES-128)
- 👥 **Multi-user mode**: each user can have their own tokens
- 🌐 **GitHub and GitLab** support
- 🚀 **Simple management**: Telegram commands to add/remove tokens

## Why this matters

HTTPS Git operations require authentication. Storing a shared token in `.env` is problematic:

❌ **One token for everyone**
❌ **Insecure sharing** via other channels
❌ **Hard to manage** — requires editing server files

✅ **Solution:** encrypted, per-user tokens managed via the bot.

## Security

### How tokens are stored

1. **Encryption:** all tokens encrypted with Fernet (symmetric AES-128)
2. **Key location:** `./data/.credentials_key` with mode `600`
3. **Encrypted data:** `./data/user_credentials.enc` with mode `600`
4. **File locking:** prevents race conditions

### Security recommendations

✅ **Do:**
- Create tokens with minimal scopes (`repo` for GitHub, `write_repository` for GitLab)
- Set expiration dates
- Delete messages containing tokens after sending to the bot
- Use separate tokens per project

❌ **Don’t:**
- Share tokens over insecure channels
- Use full-access tokens for everything
- Store tokens in public places

## Management commands

### `/settoken` — add a token

Step-by-step:
1. Run `/settoken` in the bot chat
2. Choose platform (GitHub or GitLab)
3. Enter your username
4. Enter your Personal Access Token

Example:
```
/settoken
→ Select: GitHub
→ Enter: john_doe
→ Enter: ghp_xxxxxxxxxxxxxxxxxxxx
→ ✅ Token saved and encrypted
```

**Auto-delete:** after sending, the token message is deleted for safety.

### `/listcredentials` — view tokens

Shows stored token info (never the token itself).

Example output:
```
🔐 Stored Git Credentials

🐙 GITHUB
  • Username: john_doe
  • Token: ✅ Present
  • Remote: https://github.com/user/repo

🦊 GITLAB
  • Username: jane_smith
  • Token: ✅ Present
```

### `/removetoken` — delete a token

Removes stored tokens.

Options:
- Delete token for a specific platform (GitHub or GitLab)
- Delete all tokens

Example:
```
/removetoken
→ Select: GitHub
→ ✅ GitHub token removed
```

## Getting tokens

### GitHub Personal Access Token

1. Go to [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token" → "Generate new token (classic)"
3. Name the token (e.g., "tg-note bot")
4. Scope: `repo` (full control of private repositories)
5. Optional: set expiration
6. Generate token
7. Copy the token (shown only once)

**Required scope:**
- ✅ `repo`

### GitLab Personal Access Token

1. Go to [GitLab Settings → Access Tokens](https://gitlab.com/-/profile/personal_access_tokens)
2. Name the token (e.g., "tg-note bot")
3. Scopes: `write_repository`
4. Optional: set expiration
5. Create token
6. Copy the token (shown only once)

**Required scope:**
- ✅ `write_repository`

## How it works

### Credential priority

When executing Git operations:
1. **User token** (from CredentialsManager) — highest priority
2. **Global token** (from `.env`) — fallback

This allows users with personal tokens to use them automatically, while others fall back to the global token if configured.

### Platform detection

Platform is detected from the repository URL:
- `github.com` → use GitHub credentials
- `gitlab.com` or other GitLab → use GitLab credentials

### Injecting credentials into URL

During Git operations (pull/push), credentials are injected into the HTTPS URL:

```
https://github.com/user/repo.git
    ↓
https://username:token@github.com/user/repo.git
```

## Admin setup

### Global credentials (fallback)

Admins can set global credentials in `.env`:

```env
# GitHub credentials (fallback)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_USERNAME=admin_username

# GitLab credentials (fallback)
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_USERNAME=admin_username
```

### File locations

- Encryption key: `./data/.credentials_key`
- Encrypted credentials: `./data/user_credentials.enc`

**Important:**
- Do not delete the encryption key; without it tokens are unreadable
- Back up the encryption key
- Set correct file permissions (600)

## Troubleshooting

### Error: "Authentication failed"

**Causes:**
1. Token missing or expired
2. Insufficient scopes
3. Token revoked

**Fix:**
1. Run `/listcredentials` to verify
2. Remove old token: `/removetoken`
3. Add a new token: `/settoken`

### Error: "Remote not found"

- Check repository URL and access permissions

### Git operations still use `.env` token

- Ensure a personal token is set for the user
- The bot automatically prefers per-user tokens when available

---

## AICODE-NOTE
- Per-user encrypted tokens keep credentials secure in multi-user setups.
- Global tokens remain as fallback when no personal token exists.
- Auto-delete of token messages reduces exposure risk.
