# Settings Management Architecture

## Design Philosophy

The settings management system is built on the principle of **automation over configuration**. Instead of manually creating Telegram commands for each setting, we automatically generate them from pydantic-settings metadata.

## Key Benefits

1. **Zero Boilerplate** - Add a field to Settings, get Telegram UI automatically
2. **Type Safety** - pydantic ensures correctness at all levels
3. **Self-Documenting** - Field descriptions become help text
4. **User-Friendly** - Interactive menus and clear commands
5. **Extensible** - Easy to add new settings and categories

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram User                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ /settings, /setsetting, etc.
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              SettingsHandlers                                │
│  - Command handlers (/settings, /setsetting, etc.)          │
│  - Inline keyboard UI generation                            │
│  - Callback query processing                                │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ get_setting(), set_user_setting()
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              SettingsManager                                 │
│  - Combines global + user-specific settings                 │
│  - Value validation and conversion                          │
│  - Setting access abstraction                               │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
           │                              │
┌──────────▼──────────────┐   ┌───────────▼──────────────────┐
│  SettingsInspector      │   │  UserSettingsStorage         │
│  - Introspects Settings │   │  - Per-user overrides        │
│  - Extracts metadata    │   │  - JSON file storage         │
│  - Categorizes fields   │   │  - Thread-safe with locks    │
└──────────┬──────────────┘   └──────────────────────────────┘
           │
           │ reads metadata from
           │
┌──────────▼──────────────────────────────────────────────────┐
│              Settings (pydantic-settings)                    │
│  - Global configuration                                      │
│  - YAML + .env + env vars                                   │
│  - Type definitions and defaults                            │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Reading a Setting

```
User → /viewsettings KB_GIT_ENABLED
  ↓
SettingsHandlers.handle_view_settings()
  ↓
SettingsManager.get_setting(user_id, "KB_GIT_ENABLED")
  ↓
1. Check UserSettingsStorage for user override
2. If not found, use global Settings value
  ↓
Return value to user
```

### Changing a Setting

```
User → /setsetting KB_GIT_ENABLED false
  ↓
SettingsHandlers.handle_set_setting()
  ↓
SettingsManager.set_user_setting(user_id, "KB_GIT_ENABLED", "false")
  ↓
1. Get SettingInfo from SettingsInspector
2. Validate: not readonly, not secret
3. Convert "false" → bool(False)
4. Save to UserSettingsStorage
  ↓
Confirm to user
```

### Interactive Menu

```
User → /settings
  ↓
SettingsHandlers.handle_settings_menu()
  ↓
SettingsInspector.get_all_categories()
  ↓
Generate InlineKeyboardMarkup with category buttons
  ↓
User clicks "📚 Knowledge Base"
  ↓
SettingsHandlers.handle_settings_callback("settings:category:knowledge_base")
  ↓
SettingsManager.get_user_settings_summary(user_id, "knowledge_base")
  ↓
Generate UI with current values and toggle buttons
  ↓
User clicks toggle button
  ↓
SettingsHandlers._set_setting_callback()
  ↓
Update setting and refresh display
```

## Components Deep Dive

### SettingsInspector

**Purpose**: Introspect pydantic-settings and extract metadata

**Key Methods**:
- `_extract_settings()` - Read all fields from Settings class
- `_get_category()` - Determine category from field name prefix
- `get_editable_settings()` - Filter out secrets and readonly fields
- `get_settings_by_category()` - Group settings by category

**Metadata Extracted**:
```python
SettingInfo(
    name="kb_git_enabled",           # Command-friendly name
    field_name="KB_GIT_ENABLED",     # Actual field name
    description="Enable Git ops",    # From Field(description=...)
    type=bool,                       # From type annotation
    default=True,                    # From Field(default=...)
    is_secret=False,                 # From SECRET_FIELDS list
    is_readonly=False,               # From READONLY_FIELDS list
    category="knowledge_base"        # From KB_ prefix
)
```

### UserSettingsStorage

**Purpose**: Store per-user setting overrides

**Storage Format**: JSON file with file locking

**Methods**:
- `get_user_settings(user_id)` - Get all overrides for user
- `set_user_setting(user_id, name, value)` - Set one override
- `remove_user_setting(user_id, name)` - Remove override

**Thread Safety**: Uses `filelock` for concurrent access

**File Structure**:
```json
{
  "user_id_1": {
    "SETTING_NAME": value,
    ...
  },
  "user_id_2": {
    ...
  }
}
```

### SettingsManager

**Purpose**: Unified interface for settings access

**Key Features**:
1. **Override Resolution**: User override → Global → Default
2. **Type Conversion**: String → Proper type
3. **Validation**: Check readonly, secret, type compatibility
4. **Summary Generation**: Format settings for display

**Methods**:
- `get_setting(user_id, name)` - Get effective setting value
- `set_user_setting(user_id, name, value)` - Set override with validation
- `reset_user_setting(user_id, name)` - Remove override
- `get_user_settings_summary(user_id, category)` - Get formatted summary

### SettingsHandlers

**Purpose**: Telegram UI and command handlers

**Commands Registered**:
- `/settings` - Main menu with categories
- `/viewsettings [category]` - View all or filtered settings
- `/setsetting <name> <value>` - Change a setting
- `/resetsetting <name>` - Reset to default
- `/kbsettings` - KB category shortcut
- `/agentsettings` - Agent category shortcut

**Callback Patterns**:
- `settings:category:<category>` - Show category settings
- `settings:set:<name>:<value>` - Set setting from button
- `settings:reset:<name>` - Reset from button
- `settings:menu` - Back to main menu

**UI Generation**:
- Automatic keyboard creation from settings
- Toggle buttons for booleans
- Quick action buttons for common values
- Category navigation

## Extension Points

### Adding a New Setting Type

Current supported types: `bool`, `int`, `float`, `str`, `Path`

To add a new type (e.g., `List[str]`):

1. **Add converter in SettingsManager**:
```python
def _convert_value(self, value: str, target_type: Type) -> Any:
    # ... existing code ...
    elif target_type == List[str]:
        return [s.strip() for s in value.split(',')]
```

2. **Add UI formatter in SettingsHandlers**:
```python
def _format_value(self, value: Any, info: SettingInfo) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    # ... existing code ...
```

### Adding a New Category

Just add a field with a new prefix:

```python
class Settings(BaseSettings):
    NEWCAT_FEATURE_X: bool = Field(default=True)
    NEWCAT_FEATURE_Y: int = Field(default=100)
```

Update `CATEGORIES` in `SettingsInspector`:

```python
CATEGORIES = {
    "NEWCAT_": "new_category",
    # ...
}
```

Category automatically appears in `/settings` menu!

### Custom Validation

Add validation to `SettingsManager.set_user_setting()`:

```python
def set_user_setting(self, user_id, setting_name, value, validate=True):
    # ... existing validation ...
    
    # Custom validation
    if setting_name == "AGENT_TIMEOUT":
        if converted_value < 10 or converted_value > 3600:
            return False, "Timeout must be between 10 and 3600 seconds"
    
    # ... save ...
```

### Custom UI Elements

Add special handling in `SettingsHandlers`:

```python
async def handle_special_setting(self, message: Message):
    # Custom UI for a complex setting
    keyboard = InlineKeyboardMarkup()
    # ... build custom keyboard ...
    await self.bot.send_message(...)
```

## Performance Considerations

1. **Metadata Caching**: `SettingsInspector` extracts once on init
2. **Lazy Loading**: User settings loaded only when needed
3. **File Locking**: Minimal lock duration for concurrent access
4. **JSON Parsing**: Small files, negligible overhead

## Security Model

### Three-Level Protection

1. **SECRET_FIELDS**: Cannot be viewed or changed via Telegram
   - API keys, tokens, passwords
   - Shown as `***hidden***` in UI
   - Set only via `.env` or environment

2. **READONLY_FIELDS**: Can be viewed but not changed
   - Bot token (changing would break bot)
   - System-critical settings

3. **Editable Fields**: Can be changed per-user
   - Feature flags, timeouts, paths
   - User preferences

### Validation Layers

1. **Pydantic validation**: Type correctness
2. **Settings check**: Readonly/secret protection
3. **Custom validation**: Business logic rules
4. **Type conversion**: String → proper type

## Testing Strategy

### Unit Tests

```python
def test_settings_inspector():
    inspector = SettingsInspector(Settings)
    assert "KB_GIT_ENABLED" in inspector.settings_info
    assert inspector.get_setting_info("KB_GIT_ENABLED").category == "knowledge_base"

def test_user_storage():
    storage = UserSettingsStorage(":memory:")
    storage.set_user_setting(123, "TEST", True)
    assert storage.get_user_settings(123)["TEST"] == True

def test_settings_manager():
    manager = SettingsManager(settings)
    success, msg = manager.set_user_setting(123, "KB_GIT_ENABLED", "false")
    assert success
    assert manager.get_setting(123, "KB_GIT_ENABLED") == False
```

### Integration Tests

```python
async def test_settings_command():
    # Send /settings
    # Verify keyboard has all categories
    # Click category button
    # Verify settings displayed
    # Click toggle button
    # Verify setting changed
```

## Migration Path

### From Old System

If you have existing per-user settings in `user_settings.json`:

1. Keep KB-specific settings there (KB name, GitHub URL)
2. Use new system for configuration overrides
3. Migrate gradually:
   ```python
   # Old: Stored in user_settings
   kb_settings = user_settings.get_user_kb(user_id)
   
   # New: Stored in settings overrides
   git_enabled = settings_manager.get_setting(user_id, "KB_GIT_ENABLED")
   ```

### Future: Unified Storage

Potential consolidation:
```python
class UnifiedUserSettings:
    """Single source for all user data"""
    kb_info: KBInfo  # KB name, URL, type
    overrides: Dict[str, Any]  # Setting overrides
    preferences: Dict[str, Any]  # UI preferences
```

## Best Practices

1. **Descriptive Field Names**: Use clear, prefixed names
2. **Good Descriptions**: Used in UI help text
3. **Sensible Defaults**: Most users shouldn't need to change
4. **Category Prefixes**: Consistent naming for auto-categorization
5. **Type Safety**: Use proper types, not `Any`
6. **Validation**: Add custom validation for complex rules
7. **Documentation**: Update SETTINGS_MANAGEMENT.md when adding fields

## Future Enhancements

### Short-term
- [ ] Settings templates (presets)
- [ ] Bulk settings import/export
- [ ] Settings search/filter

### Mid-term
- [ ] Advanced types (List, Dict, Enum)
- [ ] Validation from pydantic constraints
- [ ] Settings history/audit log

### Long-term
- [ ] Web UI for settings management
- [ ] Settings recommendations based on usage
- [ ] A/B testing for settings
- [ ] Settings analytics
