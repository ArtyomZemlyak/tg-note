# Settings Management - Visual Guide

## 🎨 Feature Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Settings Management System                    │
│                                                                  │
│  Zero-Boilerplate • Type-Safe • Per-User • Interactive UI      │
└─────────────────────────────────────────────────────────────────┘
```

## 📱 User Interface Flow

### 1. Main Settings Menu

```
┌─────────────────────────────────────────────┐
│  User sends: /settings                       │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  ⚙️ Settings Menu                           │
│                                              │
│  Choose a category:                         │
│                                              │
│  ┌──────────────┐  ┌──────────────┐        │
│  │ 📚 Knowledge │  │  🤖 Agent    │        │
│  │    Base      │  │              │        │
│  └──────────────┘  └──────────────┘        │
│                                              │
│  ┌──────────────┐  ┌──────────────┐        │
│  │ ⚙️ Processing│  │  📝 Logging  │        │
│  │              │  │              │        │
│  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────┘
```

### 2. Category View (Knowledge Base)

```
┌─────────────────────────────────────────────┐
│  User clicks: 📚 Knowledge Base              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  📚 Knowledge Base Settings                 │
│                                              │
│  • KB_GIT_ENABLED: ✅ enabled               │
│    Enable Git operations                    │
│                                              │
│  • KB_GIT_AUTO_PUSH: ✅ enabled             │
│    Auto-push to remote                      │
│                                              │
│  • KB_PATH: ./knowledge_base                │
│    Path to knowledge base                   │
│                                              │
│  ┌────────────┐  ┌────────────┐            │
│  │ ✅ Enable  │  │ ❌ Disable │            │
│  │    Git     │  │    Git     │            │
│  └────────────┘  └────────────┘            │
│                                              │
│  ┌────────────┐  ┌────────────┐            │
│  │ ✅ Enable  │  │ ❌ Disable │            │
│  │ Auto-Push  │  │ Auto-Push  │            │
│  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────┘
```

### 3. Toggle Setting

```
┌─────────────────────────────────────────────┐
│  User clicks: ❌ Disable Auto-Push           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  ✅ Setting KB_GIT_AUTO_PUSH updated!       │
│     New value: False                        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  📚 Knowledge Base Settings (Updated)       │
│                                              │
│  • KB_GIT_AUTO_PUSH: ❌ disabled  ← Changed!│
│                                              │
│  ┌────────────┐  ┌────────────┐            │
│  │ ✅ Enable  │  │ ❌ Disable │ ← Updated   │
│  │ Auto-Push  │  │ Auto-Push  │            │
│  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────┘
```

## 🔄 System Architecture

### High-Level Flow

```
┌──────────────┐
│ Telegram User│
└──────┬───────┘
       │ /settings, /setsetting, etc.
       ↓
┌──────────────────────────────────────────┐
│        SettingsHandlers                   │
│  ┌─────────────────────────────────┐     │
│  │ • Parse commands                 │     │
│  │ • Generate UI from metadata      │     │
│  │ • Handle callbacks               │     │
│  └─────────────────────────────────┘     │
└──────────────┬───────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│        SettingsManager                    │
│  ┌─────────────────────────────────┐     │
│  │ • Get setting (user override?)   │     │
│  │ • Set setting (validate & save)  │     │
│  │ • Convert types (str → bool/int) │     │
│  └─────────────────────────────────┘     │
└──────┬───────────────────┬───────────────┘
       │                   │
       ↓                   ↓
┌──────────────┐    ┌──────────────────┐
│   Settings   │    │ UserSettings     │
│   Inspector  │    │   Storage        │
│              │    │                  │
│ • Introspect │    │ • JSON storage   │
│   pydantic   │    │ • File locking   │
│ • Categorize │    │ • Per-user data  │
└──────┬───────┘    └────────┬─────────┘
       │                     │
       ↓                     ↓
┌──────────────┐    ┌──────────────────┐
│  Settings    │    │  user_settings_  │
│  (global)    │    │  overrides.json  │
└──────────────┘    └──────────────────┘
```

### Data Flow: Reading a Setting

```
1. User Request
   ┌──────────────────────────────────┐
   │ User: /viewsettings              │
   │ SettingsHandler called           │
   └────────────┬─────────────────────┘
                ↓
2. Get Setting Value
   ┌──────────────────────────────────┐
   │ SettingsManager.get_setting()    │
   │   ↓                              │
   │   Check UserSettingsStorage      │
   │   ↓                              │
   │   User override exists?          │
   │   ├─ Yes → Return override       │
   │   └─ No → Return global value    │
   └────────────┬─────────────────────┘
                ↓
3. Display to User
   ┌──────────────────────────────────┐
   │ Format and send to Telegram      │
   │                                  │
   │ ⚙️ All Settings                  │
   │                                  │
   │ • KB_GIT_ENABLED: ✅ enabled     │
   │ • AGENT_TIMEOUT: 600             │
   └──────────────────────────────────┘
```

### Data Flow: Changing a Setting

```
1. User Command
   ┌──────────────────────────────────┐
   │ User: /setsetting                │
   │       AGENT_TIMEOUT 600          │
   └────────────┬─────────────────────┘
                ↓
2. Validation
   ┌──────────────────────────────────┐
   │ SettingsManager.set_user_setting │
   │   ↓                              │
   │   Get SettingInfo from Inspector │
   │   ↓                              │
   │   Check: Not readonly?           │
   │   Check: Not secret?             │
   │   Check: Valid type?             │
   │   ↓                              │
   │   Convert "600" → int(600)       │
   └────────────┬─────────────────────┘
                ↓
3. Save Override
   ┌──────────────────────────────────┐
   │ UserSettingsStorage.set()        │
   │   ↓                              │
   │   File lock acquired             │
   │   ↓                              │
   │   Update JSON:                   │
   │   {                              │
   │     "123456": {                  │
   │       "AGENT_TIMEOUT": 600       │
   │     }                            │
   │   }                              │
   │   ↓                              │
   │   File lock released             │
   └────────────┬─────────────────────┘
                ↓
4. Confirmation
   ┌──────────────────────────────────┐
   │ ✅ Setting AGENT_TIMEOUT         │
   │    updated to: 600               │
   └──────────────────────────────────┘
```

## 🏗️ Component Responsibilities

### SettingsInspector

```
┌─────────────────────────────────────┐
│       SettingsInspector              │
├─────────────────────────────────────┤
│ INPUT:  pydantic Settings class     │
│ OUTPUT: Metadata about all fields   │
├─────────────────────────────────────┤
│ Responsibilities:                   │
│  • Extract field info                │
│  • Determine categories              │
│  • Identify secret/readonly fields   │
│  • Cache metadata                    │
└─────────────────────────────────────┘
```

### UserSettingsStorage

```
┌─────────────────────────────────────┐
│       UserSettingsStorage            │
├─────────────────────────────────────┤
│ INPUT:  user_id, setting, value     │
│ OUTPUT: Success/failure              │
├─────────────────────────────────────┤
│ Responsibilities:                   │
│  • Store per-user overrides          │
│  • Thread-safe file operations       │
│  • JSON serialization                │
│  • File locking                      │
└─────────────────────────────────────┘
```

### SettingsManager

```
┌─────────────────────────────────────┐
│         SettingsManager              │
├─────────────────────────────────────┤
│ INPUT:  Setting requests from UI    │
│ OUTPUT: Validated, converted values │
├─────────────────────────────────────┤
│ Responsibilities:                   │
│  • Resolve overrides                 │
│  • Type conversion                   │
│  • Validation                        │
│  • Coordinate components             │
└─────────────────────────────────────┘
```

### SettingsHandlers

```
┌─────────────────────────────────────┐
│        SettingsHandlers              │
├─────────────────────────────────────┤
│ INPUT:  Telegram commands/callbacks │
│ OUTPUT: Interactive UI messages     │
├─────────────────────────────────────┤
│ Responsibilities:                   │
│  • Parse user commands               │
│  • Generate inline keyboards         │
│  • Handle callbacks                  │
│  • Format output                     │
└─────────────────────────────────────┘
```

## 📊 Settings Hierarchy

```
                    ┌──────────────────┐
                    │  User Override   │
                    │  (Highest)       │
                    └────────┬─────────┘
                             │ If exists
                             ↓
                    ┌──────────────────┐
                    │ config.yaml      │
                    │ (Middle)         │
                    └────────┬─────────┘
                             │ If not in user
                             ↓
                    ┌──────────────────┐
                    │ pydantic Default │
                    │ (Lowest)         │
                    └──────────────────┘

Example:
  User: AGENT_TIMEOUT = 600  ← User override
  YAML: AGENT_TIMEOUT = 300
  Default: 300
  
  Result: 600 (user override wins)
```

## 🎯 Type Conversion Examples

```
String Input  →  Type Conversion  →  Stored Value
─────────────────────────────────────────────────
"true"        →  bool              →  True
"false"       →  bool              →  False
"1"           →  bool              →  True
"600"         →  int               →  600
"./my_kb"     →  Path              →  Path("./my_kb")
"origin"      →  str               →  "origin"
```

## 🔒 Security Model

```
┌─────────────────────────────────────────┐
│           Setting Types                  │
├─────────────────────────────────────────┤
│                                          │
│  ┌────────────────────────────────┐     │
│  │  🔴 SECRET FIELDS               │     │
│  │  • API keys, tokens             │     │
│  │  • Cannot view or change        │     │
│  │  • Shown as ***hidden***        │     │
│  └────────────────────────────────┘     │
│                                          │
│  ┌────────────────────────────────┐     │
│  │  🟡 READONLY FIELDS             │     │
│  │  • Can view, cannot change      │     │
│  │  • Critical system settings     │     │
│  │  • Shown with 🔒 icon           │     │
│  └────────────────────────────────┘     │
│                                          │
│  ┌────────────────────────────────┐     │
│  │  🟢 EDITABLE FIELDS             │     │
│  │  • Can view and change          │     │
│  │  • User preferences             │     │
│  │  • Interactive UI available     │     │
│  └────────────────────────────────┘     │
│                                          │
└─────────────────────────────────────────┘
```

## 🎨 UI Generation Process

```
1. Developer adds field to Settings
   ┌─────────────────────────────────┐
   │ KB_GIT_ENABLED: bool = Field(   │
   │     default=True,                │
   │     description="Enable Git"     │
   │ )                                │
   └─────────────┬───────────────────┘
                 ↓
2. SettingsInspector extracts metadata
   ┌─────────────────────────────────┐
   │ SettingInfo(                     │
   │   field_name="KB_GIT_ENABLED"   │
   │   type=bool                      │
   │   category="knowledge_base"      │
   │   description="Enable Git"       │
   │   is_secret=False                │
   │ )                                │
   └─────────────┬───────────────────┘
                 ↓
3. SettingsHandlers generates UI
   ┌─────────────────────────────────┐
   │ Category Button:                 │
   │   "📚 Knowledge Base"            │
   │                                  │
   │ Setting Display:                 │
   │   "• KB_GIT_ENABLED: ✅ enabled" │
   │   "  Enable Git"                 │
   │                                  │
   │ Toggle Buttons:                  │
   │   [✅ Enable Git]                │
   │   [❌ Disable Git]               │
   └──────────────────────────────────┘
```

## 📝 Storage Format

### user_settings_overrides.json

```json
{
  "123456789": {
    "KB_GIT_ENABLED": false,
    "AGENT_TIMEOUT": 600,
    "MESSAGE_GROUP_TIMEOUT": 45
  },
  "987654321": {
    "KB_GIT_AUTO_PUSH": false,
    "AGENT_ENABLE_WEB_SEARCH": true
  }
}
```

**Structure:**
- Top-level keys: User IDs (as strings)
- Values: Dict of setting name → value
- Only stores overrides (not all settings)
- Thread-safe with file locking

## 🔄 Complete User Journey

```
┌─────────────────────────────────────────────┐
│ 1. User wants to change Agent timeout       │
└─────────────┬───────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ 2. Opens /settings menu                      │
│    Sees categories                           │
└─────────────┬───────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ 3. Clicks "🤖 Agent"                         │
│    Sees all agent settings                   │
└─────────────┬───────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ 4. Sees AGENT_TIMEOUT: 300                  │
│    Clicks "Set Timeout: 600s" button         │
└─────────────┬───────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ 5. Gets confirmation:                        │
│    "✅ Setting AGENT_TIMEOUT updated: 600"   │
└─────────────┬───────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ 6. UI refreshes showing new value            │
│    AGENT_TIMEOUT: 600                        │
└─────────────┬───────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ 7. Setting is now active for this user      │
│    Stored in user_settings_overrides.json   │
└─────────────────────────────────────────────┘
```

---

**Visual guide complete! See other docs for detailed implementation.** 📚
