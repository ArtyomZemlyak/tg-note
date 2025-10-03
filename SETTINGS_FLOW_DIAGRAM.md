# Settings Flow Diagram

## Before Fix (Settings Not Applied)

```
┌─────────────────────────────────────────────────────────────────┐
│ Bot Startup                                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BotHandlers.__init__()                                        │
│    ├─ message_aggregator = MessageAggregator(30)  ← GLOBAL     │
│    └─ agent = AgentFactory.from_settings(settings) ← GLOBAL    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ User Changes Setting                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  /settings → MESSAGE_GROUP_TIMEOUT → 10                        │
│    └─ Saves to user_settings_overrides.json ✅                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ User Sends Message                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BotHandlers._process_message()                                │
│    └─ Uses self.message_aggregator (still has 30s!) ❌        │
│                                                                 │
│  BotHandlers._process_message_group()                          │
│    └─ Uses self.agent (still has old config!) ❌              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Problem: Components created once at startup, never updated!
```

## After Fix (Settings Applied Correctly)

```
┌─────────────────────────────────────────────────────────────────┐
│ Bot Startup                                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BotHandlers.__init__()                                        │
│    ├─ settings_manager = SettingsManager()                    │
│    ├─ user_message_aggregators = {}  ← Empty dict             │
│    └─ user_agents = {}                ← Empty dict             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ User 123 Sends First Message                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  _get_or_create_user_aggregator(123)                           │
│    ├─ timeout = settings_manager.get_setting(123, "...")      │
│    │   └─ Returns user override OR global default             │
│    └─ user_message_aggregators[123] = MessageAggregator(30)   │
│                                                                 │
│  _get_or_create_user_agent(123)                                │
│    ├─ config = {...all user-specific settings...}             │
│    └─ user_agents[123] = AgentFactory.create_agent(config)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ User 123 Changes Setting                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  /settings → MESSAGE_GROUP_TIMEOUT → 10                        │
│    ├─ Saves to user_settings_overrides.json ✅                │
│    └─ invalidate_user_cache(123) called                       │
│         ├─ Stop user_message_aggregators[123] ✅              │
│         ├─ Delete user_message_aggregators[123] ✅            │
│         └─ Delete user_agents[123] ✅                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ User 123 Sends Next Message                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  _get_or_create_user_aggregator(123)                           │
│    ├─ Cache miss! (was deleted)                               │
│    ├─ timeout = settings_manager.get_setting(123, "...")      │
│    │   └─ Returns NEW value: 10 ✅                            │
│    └─ user_message_aggregators[123] = MessageAggregator(10)   │
│                                                                 │
│  _get_or_create_user_agent(123)                                │
│    ├─ Cache miss! (was deleted)                               │
│    ├─ config = {...all UPDATED user settings...} ✅           │
│    └─ user_agents[123] = AgentFactory.create_agent(config)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Success: Components recreated with new settings!
```

## Multi-User Isolation

```
┌─────────────────────────────────────────────────────────────────┐
│ User 123                        │ User 456                      │
├─────────────────────────────────┼───────────────────────────────┤
│                                 │                               │
│ MESSAGE_GROUP_TIMEOUT: 10s      │ MESSAGE_GROUP_TIMEOUT: 60s    │
│ AGENT_TYPE: qwen_code          │ AGENT_TYPE: stub              │
│                                 │                               │
│ user_message_aggregators[123]   │ user_message_aggregators[456] │
│   └─ MessageAggregator(10)     │   └─ MessageAggregator(60)    │
│                                 │                               │
│ user_agents[123]                │ user_agents[456]              │
│   └─ QwenCodeAgent(...)        │   └─ StubAgent(...)           │
│                                 │                               │
└─────────────────────────────────┴───────────────────────────────┘

Each user gets their own configured components!
```

## Settings Lookup Priority

```
SettingsManager.get_setting(user_id, "SETTING_NAME")
    │
    ├─ 1. Check user_settings_overrides.json
    │      └─ If user has override → return it ✅
    │
    └─ 2. Fall back to global settings
           └─ Return default from config ✅

Example:
  User 123: MESSAGE_GROUP_TIMEOUT override = 10
  User 456: No override
  
  get_setting(123, "MESSAGE_GROUP_TIMEOUT") → 10 (from override)
  get_setting(456, "MESSAGE_GROUP_TIMEOUT") → 30 (from global)
```

## Cache Invalidation Flow

```
┌────────────────────────────────────────────┐
│ User changes setting via menu              │
└────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────┐
│ SettingsManager.set_user_setting()        │
│   └─ Save to user_settings_overrides.json │
└────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────┐
│ SettingsHandlers._set_setting_callback()  │
│   └─ Call handlers.invalidate_user_cache()│
└────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────┐
│ BotHandlers.invalidate_user_cache()       │
│   ├─ Stop aggregator background task      │
│   ├─ Delete user_message_aggregators[uid] │
│   └─ Delete user_agents[uid]              │
└────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────┐
│ Next message from user                     │
│   ├─ Cache miss detected                  │
│   ├─ Re-read settings from storage        │
│   └─ Create new components with new config│
└────────────────────────────────────────────┘

Settings applied immediately, no restart needed! ✅
```
