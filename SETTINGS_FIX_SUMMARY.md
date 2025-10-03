# Settings Application Fix Summary

## Problem Identified

When users changed settings through the `/settings` menu, the values were successfully saved to user storage, but the bot continued using the old (global/default) values. This was verified with `MESSAGE_GROUP_TIMEOUT`, but affected all settings.

### Root Cause

1. **MessageAggregator**: Initialized once at bot startup with global `settings.MESSAGE_GROUP_TIMEOUT`
2. **Agent**: Created once at bot startup with global settings via `AgentFactory.from_settings(settings)`
3. **No user-specific lookup**: The bot didn't check user-specific settings overrides when processing messages

The settings were being saved correctly to `./data/user_settings_overrides.json`, but the bot's components never read from this file during runtime.

## Solution Implemented

### 1. Per-User Component Instances

Changed from global components to per-user instances that are created on-demand with user-specific settings:

**Before:**
```python
class BotHandlers:
    def __init__(self, ...):
        self.message_aggregator = MessageAggregator(settings.MESSAGE_GROUP_TIMEOUT)
        self.agent = AgentFactory.from_settings(settings)
```

**After:**
```python
class BotHandlers:
    def __init__(self, ...):
        self.settings_manager = SettingsManager(settings)
        self.user_message_aggregators: Dict[int, MessageAggregator] = {}
        self.user_agents: Dict[int, Any] = {}
```

### 2. Lazy Initialization with User Settings

Added helper methods to create user-specific instances on first use:

```python
def _get_or_create_user_aggregator(self, user_id: int) -> MessageAggregator:
    """Get or create message aggregator for a user with their settings"""
    if user_id not in self.user_message_aggregators:
        timeout = self.settings_manager.get_setting(user_id, "MESSAGE_GROUP_TIMEOUT")
        aggregator = MessageAggregator(timeout)
        # ... setup and start background task
        self.user_message_aggregators[user_id] = aggregator
    return self.user_message_aggregators[user_id]

def _get_or_create_user_agent(self, user_id: int):
    """Get or create agent for a user with their settings"""
    if user_id not in self.user_agents:
        config = {
            "api_key": self.settings_manager.get_setting(user_id, "QWEN_API_KEY"),
            "model": self.settings_manager.get_setting(user_id, "AGENT_MODEL"),
            "timeout": self.settings_manager.get_setting(user_id, "AGENT_TIMEOUT"),
            # ... all agent settings
        }
        agent_type = self.settings_manager.get_setting(user_id, "AGENT_TYPE")
        agent = AgentFactory.create_agent(agent_type=agent_type, config=config)
        self.user_agents[user_id] = agent
    return self.user_agents[user_id]
```

### 3. Cache Invalidation on Settings Change

Added cache invalidation to ensure settings changes take effect immediately:

```python
def invalidate_user_cache(self, user_id: int) -> None:
    """Invalidate cached user-specific components when settings change"""
    # Stop and remove user's message aggregator
    if user_id in self.user_message_aggregators:
        self.user_message_aggregators[user_id].stop_background_task()
        del self.user_message_aggregators[user_id]
    
    # Remove user's agent
    if user_id in self.user_agents:
        del self.user_agents[user_id]
```

This method is called automatically by `SettingsHandlers` whenever a setting is changed or reset.

### 4. Updated All Settings Usage Points

Changed all hardcoded `settings.SETTING_NAME` references to use user-specific values:

**Git Settings:**
```python
# Before
git_ops = GitOperations(str(kb_path), enabled=settings.KB_GIT_ENABLED)
if settings.KB_GIT_AUTO_PUSH:
    git_ops.push(settings.KB_GIT_REMOTE, settings.KB_GIT_BRANCH)

# After
kb_git_enabled = self.settings_manager.get_setting(user_id, "KB_GIT_ENABLED")
git_ops = GitOperations(str(kb_path), enabled=kb_git_enabled)
kb_git_auto_push = self.settings_manager.get_setting(user_id, "KB_GIT_AUTO_PUSH")
if kb_git_auto_push:
    kb_git_remote = self.settings_manager.get_setting(user_id, "KB_GIT_REMOTE")
    kb_git_branch = self.settings_manager.get_setting(user_id, "KB_GIT_BRANCH")
    git_ops.push(kb_git_remote, kb_git_branch)
```

## Files Modified

1. **src/bot/handlers.py**
   - Added `settings_manager`, `user_message_aggregators`, `user_agents` attributes
   - Added `_get_or_create_user_aggregator()` method
   - Added `_get_or_create_user_agent()` method
   - Added `invalidate_user_cache()` method
   - Updated `_process_message()` to use user-specific aggregator
   - Updated `_process_message_group()` to use user-specific agent and git settings
   - Updated `handle_status()` to show user-specific git status

2. **src/bot/settings_handlers.py**
   - Added `handlers` parameter to `__init__()` for cross-reference
   - Updated `_set_setting_callback()` to invalidate cache
   - Updated `_reset_setting_callback()` to invalidate cache
   - Updated `handle_setting_input()` to invalidate cache
   - Updated `handle_reset_setting()` to invalidate cache

3. **src/bot/telegram_bot.py**
   - Changed initialization order to allow cross-references between handlers

## How It Works Now

1. **User changes a setting** via `/settings` menu or commands
2. **Setting is saved** to `./data/user_settings_overrides.json`
3. **Cache is invalidated** - user's MessageAggregator and Agent are removed
4. **Next message from user** triggers lazy re-initialization
5. **New components created** with updated user-specific settings
6. **Bot behavior reflects new settings** immediately

## Settings Affected

All settings are now properly user-specific, including but not limited to:

- `MESSAGE_GROUP_TIMEOUT` - Message grouping timeout
- `AGENT_TYPE` - Which agent to use (stub, qwen_code, qwen_code_cli)
- `AGENT_MODEL` - Model for agent
- `AGENT_TIMEOUT` - Agent processing timeout
- `AGENT_ENABLE_WEB_SEARCH` - Enable web search in agent
- `AGENT_ENABLE_GIT` - Enable git operations in agent
- `AGENT_ENABLE_GITHUB` - Enable GitHub operations in agent
- `AGENT_ENABLE_SHELL` - Enable shell operations in agent
- `KB_GIT_ENABLED` - Enable git for knowledge base
- `KB_GIT_AUTO_PUSH` - Auto-push to remote
- `KB_GIT_REMOTE` - Git remote name
- `KB_GIT_BRANCH` - Git branch name

## Testing Recommendations

To verify the fix works:

1. **Test MESSAGE_GROUP_TIMEOUT:**
   ```
   /settings → Processing → MESSAGE_GROUP_TIMEOUT
   Change from 30 to 10 seconds
   Send messages and verify they group after 10s, not 30s
   ```

2. **Test AGENT_TIMEOUT:**
   ```
   /settings → Agent → AGENT_TIMEOUT
   Change from 300 to 60 seconds
   Send a message that requires processing
   Verify timeout occurs after 60s if agent is slow
   ```

3. **Test KB_GIT_ENABLED:**
   ```
   /settings → Knowledge Base → KB_GIT_ENABLED
   Toggle it off
   Send a message
   Verify no git commit is made
   Toggle it back on
   Send a message
   Verify git commit is made
   ```

4. **Test per-user isolation:**
   ```
   User A: Set MESSAGE_GROUP_TIMEOUT to 10s
   User B: Set MESSAGE_GROUP_TIMEOUT to 60s
   Both send messages
   Verify each user's messages group according to their timeout
   ```

## Benefits

1. ✅ Settings changes now take effect immediately
2. ✅ Each user can have their own settings
3. ✅ No need to restart the bot when settings change
4. ✅ Clean separation between global defaults and user overrides
5. ✅ Automatic cleanup of old components when settings change
6. ✅ Lazy initialization reduces memory usage for inactive users
