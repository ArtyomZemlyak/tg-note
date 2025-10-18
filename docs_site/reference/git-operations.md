# Git Operations Reference

This document provides detailed information about git operations in the knowledge base system.

---

## Overview

The `GitOperations` class (`src/knowledge_base/git_ops.py`) provides a high-level interface for git operations with built-in error handling, authentication management, and safety checks.

---

## Key Features

### 1. Automatic HTTPS Authentication

Automatically configures GitHub HTTPS remotes with credentials:

```python
git_ops = GitOperations(
    repo_path="/path/to/repo",
    enabled=True,
    github_username="your_username",
    github_token="ghp_your_token"
)
```

**Behavior**:
- Only modifies HTTPS GitHub URLs (`https://github.com/...`)
- Skips URLs that already contain credentials (`@` in URL)
- Leaves SSH remotes unchanged (`git@github.com:...`)
- Idempotent: safe to call multiple times
- Per-remote error handling: failure on one remote doesn't affect others

### 2. Safety Checks

**Repository Boundary Protection**:
- `add()` method validates that files are within repository boundaries
- Prevents adding files from outside the repository (security)
- Uses resolved absolute paths for comparison

**Branch Safety**:
- Detects detached HEAD state
- Prevents dangerous operations in detached HEAD
- Validates branch existence before operations
- Verifies branch after switching

**Stash Protection**:
- Automatically stashes uncommitted changes before branch switch
- Returns error if stashing fails (prevents data loss)
- Restores stash after successful branch switch

### 3. Error Handling

All methods return clear success/failure status with descriptive messages:

```python
# Pull example
success, message = git_ops.pull(remote="origin", branch="main")
if not success:
    print(f"Pull failed: {message}")
```

**Error categories**:
- Authentication errors (HTTPS/SSH)
- Merge conflicts
- Missing remotes/branches
- Uncommitted changes
- Detached HEAD state
- File not found
- Files outside repository

---

## API Reference

### `__init__(repo_path, enabled=True, github_username=None, github_token=None)`

Initialize git operations for a repository.

**Parameters**:
- `repo_path` (str): Path to git repository
- `enabled` (bool): Enable git operations (default: True)
- `github_username` (str, optional): GitHub username for HTTPS auth
- `github_token` (str, optional): GitHub personal access token

**Behavior**:
- Initializes repository if valid
- Configures HTTPS credentials if provided
- Disables operations if repo is invalid or GitPython not available

### `add(file_path: str) -> bool`

Add file to git staging area.

**Parameters**:
- `file_path` (str): Path to file to add

**Returns**:
- `bool`: True if successful, False otherwise

**Safety checks**:
- Validates file exists
- Validates file is within repository boundaries
- Uses relative path from repo root

**Error cases**:
- File doesn't exist
- File is outside repository (security)
- Git operations disabled
- File add operation fails

### `commit(message: str) -> bool`

Commit staged changes.

**Parameters**:
- `message` (str): Commit message

**Returns**:
- `bool`: True if successful, False otherwise

**Error cases**:
- No staged changes
- Git operations disabled
- Commit operation fails

### `pull(remote="origin", branch=None) -> tuple[bool, str]`

Pull latest changes from remote repository.

**Parameters**:
- `remote` (str): Remote name (default: "origin")
- `branch` (str, optional): Branch to pull. If None/"auto", uses tracking branch

**Returns**:
- `tuple[bool, str]`: (success, message)

**Behavior**:
- Checks for uncommitted changes (fails if found)
- Validates remote exists
- Determines tracking branch if not specified
- Handles fast-forward and up-to-date cases
- Creates and pushes branch if remote branch doesn't exist

**Error cases**:
- Uncommitted changes in working directory
- Remote not found
- Detached HEAD state (when creating missing branch)
- Merge conflicts
- Remote branch doesn't exist (auto-creates if possible)
- Network/authentication errors

### `push(remote="origin", branch=None) -> bool`

Push commits to remote repository.

**Parameters**:
- `remote` (str): Remote name (default: "origin")
- `branch` (str, optional): Branch to push. If None/"auto", uses current branch

**Returns**:
- `bool`: True if successful, False otherwise

**Behavior**:
- Validates remote exists
- Determines current branch if not specified
- Sets upstream tracking if not configured
- Provides authentication guidance on HTTPS errors

**Error cases**:
- Remote not found
- Authentication failure (HTTPS/SSH)
- Network errors
- Force push required (diverged branches)
- Detached HEAD state

### `add_commit_push(file_path, message, remote="origin", branch="main") -> bool`

Combined operation: add file, commit, and push in one call.

**Parameters**:
- `file_path` (str): Path to file to add
- `message` (str): Commit message
- `remote` (str): Remote name (default: "origin")
- `branch` (str): Branch name (default: "main")

**Returns**:
- `bool`: True if all operations successful, False otherwise

**Behavior**:
- Calls `add()`, `commit()`, and `push()` in sequence
- Stops on first failure

### `auto_commit_and_push(message, remote="origin", branch=None) -> tuple[bool, str]`

Automatically commit all changes and push to remote.

**Parameters**:
- `message` (str): Commit message
- `remote` (str): Remote name (default: "origin")
- `branch` (str, optional): Branch to commit/push to

**Returns**:
- `tuple[bool, str]`: (success, message)

**Behavior**:
1. Switches to target branch if specified
2. Stashes uncommitted changes if switching branches
3. Checks for changes
4. Adds all changes (`git add -A`)
5. Commits with provided message
6. Pushes to remote if configured
7. Restores stash if created

**Safety features**:
- Validates branch after switching
- Fails if stashing fails (prevents data loss)
- Returns success even if push fails (commit succeeded)
- Handles missing remote gracefully

**Error cases**:
- Failed to stash uncommitted changes
- Failed to switch branches
- Branch mismatch after switch
- Failed to add changes
- Failed to commit
- Push failed (commit still succeeded)

### `has_remote(remote="origin") -> bool`

Check if repository has a remote configured.

**Parameters**:
- `remote` (str): Remote name (default: "origin")

**Returns**:
- `bool`: True if remote exists, False otherwise

### `has_changes() -> bool`

Check if repository has uncommitted changes.

**Returns**:
- `bool`: True if there are uncommitted changes (staged or unstaged), False otherwise

---

## Usage Examples

### Basic Operations

```python
from src.knowledge_base.git_ops import GitOperations

# Initialize with HTTPS authentication
git_ops = GitOperations(
    repo_path="/path/to/kb",
    enabled=True,
    github_username="myusername",
    github_token="ghp_mytoken123"
)

# Add, commit, push
git_ops.add("topics/ai/notes.md")
git_ops.commit("Add AI notes")
success = git_ops.push()

if not success:
    print("Push failed - check authentication")
```

### Pull with Error Handling

```python
# Pull latest changes
success, message = git_ops.pull(remote="origin", branch="main")

if not success:
    if "uncommitted changes" in message.lower():
        print("Please commit or stash your changes first")
    elif "conflict" in message.lower():
        print("Merge conflict - resolve manually")
    elif "remote" in message.lower():
        print("Remote not configured")
    else:
        print(f"Pull failed: {message}")
```

### Auto-commit with Branch Switching

```python
# Commit all changes and push to feature branch
success, message = git_ops.auto_commit_and_push(
    message="Update documentation",
    remote="origin",
    branch="feature/new-docs"
)

if success:
    print(f"Success: {message}")
else:
    print(f"Failed: {message}")
```

### Check Repository State

```python
# Check for remote
if not git_ops.has_remote("origin"):
    print("No origin remote configured")
    print("Add with: git remote add origin <url>")

# Check for uncommitted changes
if git_ops.has_changes():
    print("You have uncommitted changes")
    # Commit them
    git_ops.auto_commit_and_push("Auto-save changes")
```

---

## Error Scenarios and Solutions

### 1. Authentication Errors

**HTTPS without credentials**:
```
Error: "could not read Username for 'https://github.com'"
Solution: Set GITHUB_USERNAME and GITHUB_TOKEN in .env
```

**Invalid token**:
```
Error: "authentication failed"
Solution: Generate new token at https://github.com/settings/tokens
Scopes needed: repo (full control of private repositories)
```

**HTTPS with wrong credentials**:
```
Solution: Update .env file with correct credentials
Alternative: Switch to SSH (git remote set-url origin git@github.com:user/repo.git)
```

### 2. Merge Conflicts

**During pull**:
```
Error: "Merge conflict during pull"
Solution: Resolve manually
  1. git status (see conflicted files)
  2. Edit conflicted files
  3. git add <resolved-files>
  4. git commit
```

### 3. Uncommitted Changes

**Preventing pull**:
```
Error: "Repository has uncommitted changes"
Solution 1: Commit changes first
  git_ops.auto_commit_and_push("WIP: save progress")
Solution 2: Stash changes
  git stash
  git_ops.pull()
  git stash pop
```

**Preventing branch switch**:
```
Error: "Cannot switch branches with uncommitted changes"
Solution: auto_commit_and_push() handles this automatically via stashing
```

### 4. Branch Issues

**Detached HEAD**:
```
Error: "Not on any branch (detached HEAD state)"
Solution: Checkout a branch first
  git checkout main
```

**Missing remote branch**:
```
Behavior: Automatically creates branch locally and pushes to remote
Note: Requires being on a valid branch (not detached HEAD)
```

### 5. File Issues

**File outside repository**:
```
Error: "Cannot add file to git - file is outside repository"
Solution: This is a security feature. Only add files within the KB directory.
```

**File not found**:
```
Error: "Cannot add file to git - file does not exist"
Solution: Verify file path is correct
```

---

## Security Considerations

### Path Traversal Prevention

The `add()` method validates that files are within repository boundaries:

```python
# This will fail
git_ops.add("../../etc/passwd")  # Outside repo

# This is allowed
git_ops.add("topics/notes.md")  # Inside repo
```

### Credential Handling

- GitHub tokens are never logged
- HTTPS URLs in logs hide credentials
- Credentials are only injected into HTTPS URLs, never SSH

### Safe Branch Operations

- Detached HEAD state is detected and blocks dangerous operations
- Uncommitted changes are stashed before branch switches
- Stash failures prevent branch switches (no data loss)

---

## Testing

See `tests/test_git_ops.py` for comprehensive test coverage:

- Basic operations (add, commit, push, pull)
- HTTPS authentication configuration
- Error handling (authentication, conflicts, missing remotes)
- Remote branch creation
- Detached HEAD detection
- File path validation
- Stash handling

Run tests:
```bash
pytest tests/test_git_ops.py -v
```

---

## Related Documentation

- [KB Synchronization Architecture](../architecture/kb-synchronization.md)
- [Knowledge Base Setup](../user-guide/knowledge-base-setup.md)
- [Troubleshooting](troubleshooting.md)
