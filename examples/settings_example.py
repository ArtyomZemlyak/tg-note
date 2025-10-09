#!/usr/bin/env python3
"""
Example: Using Settings Management System.

This example demonstrates how to:
1. Add a new setting to the system
2. Access it programmatically
3. Use it in your code with user overrides
"""

from pathlib import Path

from pydantic import Field

from config.settings import Settings
from src.bot.settings_manager import SettingsInspector, SettingsManager, UserSettingsStorage

# ============================================================================
# Example 1: Adding a New Setting
# ============================================================================


class ExtendedSettings(Settings):
    """Extended settings with new features."""

    # Add a new KB setting - automatically appears in /kbsettings
    KB_AUTO_CATEGORIZE: bool = Field(
        default=True, description="Automatically categorize articles using AI"
    )

    # Add a new agent setting - automatically in /agentsettings
    AGENT_MAX_RETRIES: int = Field(default=3, description="Maximum retries for agent operations")

    # Add a custom category setting
    NOTIFICATION_ENABLED: bool = Field(default=True, description="Enable notification messages")

    NOTIFICATION_DELAY: int = Field(
        default=5, description="Delay before sending notifications (seconds)"
    )


# ============================================================================
# Example 2: Inspecting Settings
# ============================================================================


def example_inspect_settings():
    """Inspect settings metadata"""
    print("=== Settings Inspection Example ===\n")

    inspector = SettingsInspector(ExtendedSettings)

    # Get all categories
    print("Available categories:")
    for category in inspector.get_all_categories():
        print(f"  - {category}")

    print("\n" + "=" * 50 + "\n")

    # Get KB settings
    kb_settings = inspector.get_settings_by_category("knowledge_base")
    print("Knowledge Base Settings:")
    for setting in kb_settings:
        print(f"  {setting.field_name}:")
        print(f"    Type: {setting.type}")
        print(f"    Default: {setting.default}")
        print(f"    Description: {setting.description}")
        print()

    print("=" * 50 + "\n")

    # Get editable settings only
    editable = inspector.get_editable_settings()
    print(f"Total editable settings: {len(editable)}")
    print("Examples:")
    for setting in editable[:5]:
        print(f"  - {setting.field_name} ({setting.category})")


# ============================================================================
# Example 3: Using Settings Manager
# ============================================================================


def example_settings_manager():
    """Use settings manager with user overrides"""
    print("\n=== Settings Manager Example ===\n")

    # Initialize
    global_settings = ExtendedSettings()
    storage = UserSettingsStorage("./examples/user_settings_example.json")
    manager = SettingsManager(global_settings, storage)

    user_id = 123456789

    # Get default value
    timeout = manager.get_setting(user_id, "AGENT_TIMEOUT")
    print(f"Default AGENT_TIMEOUT: {timeout}")

    # Set user-specific override
    success, msg = manager.set_user_setting(user_id, "AGENT_TIMEOUT", "600")
    print(f"Set override: {msg}")

    # Get updated value
    timeout = manager.get_setting(user_id, "AGENT_TIMEOUT")
    print(f"User AGENT_TIMEOUT: {timeout}")

    # Another user gets default
    other_user = 987654321
    timeout = manager.get_setting(other_user, "AGENT_TIMEOUT")
    print(f"Other user AGENT_TIMEOUT: {timeout}")

    print("\n" + "=" * 50 + "\n")

    # Get all user settings
    summary = manager.get_user_settings_summary(user_id, category="agent")
    print("User's Agent Settings:")
    for name, value in summary.items():
        print(f"  {name}: {value}")

    print("\n" + "=" * 50 + "\n")

    # Reset to default
    success, msg = manager.reset_user_setting(user_id, "AGENT_TIMEOUT")
    print(f"Reset: {msg}")

    timeout = manager.get_setting(user_id, "AGENT_TIMEOUT")
    print(f"After reset: {timeout}")


# ============================================================================
# Example 4: Using in Application Code
# ============================================================================


class MyAgent:
    """Example agent using settings manager"""

    def __init__(self, settings_manager: SettingsManager, user_id: int):
        self.settings_manager = settings_manager
        self.user_id = user_id

    def process(self, content: str):
        """Process content with user-specific settings"""
        # Get user-specific timeout
        timeout = self.settings_manager.get_setting(self.user_id, "AGENT_TIMEOUT")
        max_retries = self.settings_manager.get_setting(self.user_id, "AGENT_MAX_RETRIES")

        print(f"Processing with timeout={timeout}s, max_retries={max_retries}")

        # Use settings in logic
        for attempt in range(max_retries):
            try:
                # Simulate processing with timeout
                print(f"  Attempt {attempt + 1}/{max_retries}")
                # ... actual processing ...
                return "Success!"
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"  Retry due to: {e}")


def example_application_usage():
    """Show how to use settings in application code"""
    print("\n=== Application Usage Example ===\n")

    global_settings = ExtendedSettings()
    storage = UserSettingsStorage("./examples/user_settings_example.json")
    manager = SettingsManager(global_settings, storage)

    user_id = 123456789

    # Set custom settings for this user
    manager.set_user_setting(user_id, "AGENT_TIMEOUT", "120")
    manager.set_user_setting(user_id, "AGENT_MAX_RETRIES", "5")

    # Create agent with user settings
    agent = MyAgent(manager, user_id)

    # Process - uses user-specific settings
    result = agent.process("Some content")
    print(f"Result: {result}")


# ============================================================================
# Example 5: Type Conversion
# ============================================================================


def example_type_conversion():
    """Demonstrate automatic type conversion"""
    print("\n=== Type Conversion Example ===\n")

    global_settings = ExtendedSettings()
    manager = SettingsManager(global_settings)
    user_id = 123456789

    examples = [
        ("KB_GIT_ENABLED", "true", bool),
        ("KB_GIT_ENABLED", "false", bool),
        ("AGENT_TIMEOUT", "600", int),
        ("MESSAGE_GROUP_TIMEOUT", "45", int),
        ("KB_PATH", "./my_kb", Path),
    ]

    for setting_name, value_str, expected_type in examples:
        success, msg = manager.set_user_setting(user_id, setting_name, value_str)
        if success:
            actual_value = manager.get_setting(user_id, setting_name)
            print(f"{setting_name}:")
            print(f"  Input: '{value_str}' (str)")
            print(f"  Output: {actual_value} ({type(actual_value).__name__})")
            print(f"  Expected type: {expected_type.__name__}")
            print(f"  ✓ Converted correctly: {isinstance(actual_value, expected_type)}")
            print()


# ============================================================================
# Example 6: Validation and Error Handling
# ============================================================================


def example_validation():
    """Demonstrate validation and error handling"""
    print("\n=== Validation Example ===\n")

    global_settings = ExtendedSettings()
    manager = SettingsManager(global_settings)
    user_id = 123456789

    # Test cases
    test_cases = [
        ("TELEGRAM_BOT_TOKEN", "new_token", "Should fail - readonly"),
        ("OPENAI_API_KEY", "sk-xxx", "Should fail - secret"),
        ("UNKNOWN_SETTING", "value", "Should fail - unknown"),
        ("AGENT_TIMEOUT", "not_a_number", "Should fail - invalid type"),
        ("KB_GIT_ENABLED", "yes", "Should succeed - valid bool"),
        ("MESSAGE_GROUP_TIMEOUT", "60", "Should succeed - valid int"),
    ]

    for setting_name, value, description in test_cases:
        success, msg = manager.set_user_setting(user_id, setting_name, value)

        status = "✓" if success else "✗"
        print(f"{status} {setting_name} = '{value}'")
        print(f"  {description}")
        print(f"  Result: {msg}")
        print()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Settings Management System Examples")
    print("=" * 70)

    # Run examples
    example_inspect_settings()
    example_settings_manager()
    example_application_usage()
    example_type_conversion()
    example_validation()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70 + "\n")

    print("Next steps:")
    print("1. Add new settings to config/settings.py")
    print("2. They automatically appear in Telegram UI")
    print("3. Use SettingsManager in your code")
    print("4. Users can customize via /settings command")
