"""
Settings Manager for Telegram Bot
Automatically generates Telegram commands and handlers from pydantic-settings
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Type, get_args, get_origin

from loguru import logger
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings

from config.settings import Settings


class SettingInfo(BaseModel):
    """Information about a single setting"""

    name: str
    field_name: str
    description: str
    type: Any  # Changed from Type to Any to accept generic aliases like List[int], Union, etc.
    default: Any
    is_secret: bool = False
    is_readonly: bool = False
    category: str = "general"
    validation_pattern: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None


class SettingsInspector:
    """Inspects pydantic-settings and extracts metadata"""

    # Categories for different setting types
    CATEGORIES = {
        "TELEGRAM_": "telegram",
        "ALLOWED_": "security",
        "OPENAI_": "credentials",
        "ANTHROPIC_": "credentials",
        "QWEN_": "credentials",
        "GITHUB_": "credentials",
        "GITLAB_": "credentials",
        "OPENROUTER_": "credentials",
        "AGENT_": "agent",
        "KB_": "knowledge_base",
        "MESSAGE_": "processing",
        "ENABLE_": "processing",
        "PROCESSED_": "processing",
        "LOG_": "logging",
        "VECTOR_": "vector_search",
        "MEM_AGENT_": "memory_agent",
        "MCP_": "mcp",
        "MEDIA_": "media",
        "CONTEXT_": "context",
        "RATE_LIMIT_": "rate_limiting",
        "HEALTH_CHECK_": "health_check",
    }

    # Credentials and readonly fields
    SECRET_FIELDS = {
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "QWEN_API_KEY",
        "GITHUB_TOKEN",
        "GITHUB_USERNAME",
        "GITLAB_TOKEN",
        "GITLAB_USERNAME",
        "OPENROUTER_API_KEY",
        "MEM_AGENT_OPENAI_API_KEY",
        "VECTOR_INFINITY_API_KEY",
        "VECTOR_QDRANT_API_KEY",
    }

    READONLY_FIELDS = {
        "TELEGRAM_BOT_TOKEN",  # Should not be changed via Telegram
    }

    def __init__(self, settings_class: Type[BaseSettings]):
        self.settings_class = settings_class
        self.settings_info: Dict[str, SettingInfo] = {}
        self._extract_settings()

    def _extract_settings(self) -> None:
        """Extract all settings from pydantic model"""
        for field_name, field_info in self.settings_class.model_fields.items():
            # Determine category
            category = self._get_category(field_name)

            # Check if secret
            is_secret = field_name in self.SECRET_FIELDS
            is_readonly = field_name in self.READONLY_FIELDS

            # Extract type information
            field_type = field_info.annotation
            default_value = field_info.default

            # Get description
            description = field_info.description or f"Setting: {field_name}"

            # Create setting info
            setting_info = SettingInfo(
                name=self._field_to_command_name(field_name),
                field_name=field_name,
                description=description,
                type=field_type,
                default=default_value,
                is_secret=is_secret,
                is_readonly=is_readonly,
                category=category,
            )

            self.settings_info[field_name] = setting_info

    def _get_category(self, field_name: str) -> str:
        """Get category for a field"""
        for prefix, category in self.CATEGORIES.items():
            if field_name.startswith(prefix):
                return category
        return "general"

    def _field_to_command_name(self, field_name: str) -> str:
        """Convert field name to command name (lowercase)"""
        return field_name.lower()

    def get_settings_by_category(self, category: str) -> List[SettingInfo]:
        """Get all settings in a category"""
        return [info for info in self.settings_info.values() if info.category == category]

    def get_editable_settings(self) -> List[SettingInfo]:
        """Get all editable (non-secret, non-readonly) settings"""
        return [
            info
            for info in self.settings_info.values()
            if not info.is_secret and not info.is_readonly
        ]

    def get_setting_info(self, field_name: str) -> Optional[SettingInfo]:
        """Get info for a specific setting"""
        return self.settings_info.get(field_name)

    def get_all_categories(self) -> List[str]:
        """Get list of all categories"""
        return list(set(info.category for info in self.settings_info.values()))


class UserSettingsStorage:
    """Storage for user-specific settings overrides"""

    def __init__(self, storage_file: str = "./data/user_settings_overrides.json"):
        """
        Initialize user settings storage

        Args:
            storage_file: Path to storage file
        """
        import json

        from filelock import FileLock

        self.storage_file = Path(storage_file)
        self.lock_file = Path(str(storage_file) + ".lock")

        # Ensure parent directory exists
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize storage file
        if not self.storage_file.exists():
            self._save_data({})

    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Get settings overrides for a user"""
        import json

        from filelock import FileLock

        with FileLock(self.lock_file):
            try:
                if self.storage_file.exists():
                    with open(self.storage_file, "r", encoding="utf-8") as f:
                        all_data: Dict[str, Any] = json.load(f)
                        return all_data.get(str(user_id), {})
            except Exception as e:
                logger.error(f"Error loading user settings: {e}")

        return {}

    def set_user_setting(self, user_id: int, setting_name: str, value: Any) -> bool:
        """Set a setting override for a user"""
        import json

        from filelock import FileLock

        try:
            with FileLock(self.lock_file):
                data = {}
                if self.storage_file.exists():
                    with open(self.storage_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                user_key = str(user_id)
                if user_key not in data:
                    data[user_key] = {}

                data[user_key][setting_name] = value

                with open(self.storage_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Set user {user_id} setting {setting_name} = {value}")
            return True

        except Exception as e:
            logger.error(f"Error setting user setting: {e}")
            return False

    def remove_user_setting(self, user_id: int, setting_name: str) -> bool:
        """Remove a setting override for a user"""
        import json

        from filelock import FileLock

        try:
            with FileLock(self.lock_file):
                if not self.storage_file.exists():
                    return True

                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                user_key = str(user_id)
                if user_key in data and setting_name in data[user_key]:
                    del data[user_key][setting_name]

                    if not data[user_key]:
                        del data[user_key]

                    with open(self.storage_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Removed user {user_id} setting {setting_name}")
            return True

        except Exception as e:
            logger.error(f"Error removing user setting: {e}")
            return False

    def _save_data(self, data: Dict) -> None:
        """Save data to file"""
        import json

        from filelock import FileLock

        with FileLock(self.lock_file):
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)


class SettingsManager:
    """Manages settings with user-specific overrides"""

    def __init__(
        self, global_settings: Settings, user_storage: Optional[UserSettingsStorage] = None
    ):
        self.global_settings = global_settings
        self.inspector = SettingsInspector(Settings)
        self.user_storage = user_storage or UserSettingsStorage()

    def get_setting(self, user_id: int, setting_name: str) -> Any:
        """
        Get setting value for a user (with override support)

        Args:
            user_id: User ID
            setting_name: Setting field name

        Returns:
            Setting value (user override or global default)
        """
        # Check user override first
        user_settings = self.user_storage.get_user_settings(user_id)
        if setting_name in user_settings:
            return user_settings[setting_name]

        # Fall back to global settings
        return getattr(self.global_settings, setting_name, None)

    def set_user_setting(
        self, user_id: int, setting_name: str, value: Any, validate: bool = True
    ) -> tuple[bool, str]:
        """
        Set a user-specific setting override

        Args:
            user_id: User ID
            setting_name: Setting field name
            value: New value
            validate: Whether to validate the value

        Returns:
            Tuple of (success, message)
        """
        # Get setting info
        setting_info = self.inspector.get_setting_info(setting_name)
        if not setting_info:
            return False, f"Unknown setting: {setting_name}"

        # Check if readonly
        if setting_info.is_readonly:
            return False, f"Setting {setting_name} is read-only"

        # Check if secret
        if setting_info.is_secret:
            return False, f"Setting {setting_name} cannot be changed via Telegram"

        # Validate and convert value
        if validate:
            try:
                converted_value = self._convert_value(value, setting_info.type)
            except ValueError as e:
                return False, f"Invalid value: {e}"
        else:
            converted_value = value

        # Save to user storage
        success = self.user_storage.set_user_setting(user_id, setting_name, converted_value)

        if success:
            return True, f"Setting {setting_name} updated to: {converted_value}"
        else:
            return False, "Failed to save setting"

    def reset_user_setting(self, user_id: int, setting_name: str) -> tuple[bool, str]:
        """Reset a user setting to global default"""
        success = self.user_storage.remove_user_setting(user_id, setting_name)

        if success:
            default_value = getattr(self.global_settings, setting_name, None)
            return True, f"Setting {setting_name} reset to default: {default_value}"
        else:
            return False, "Failed to reset setting"

    def get_user_settings_summary(
        self, user_id: int, category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary of all settings for a user"""
        settings = {}

        # Filter by category if specified
        if category:
            setting_infos = self.inspector.get_settings_by_category(category)
        else:
            setting_infos = list(self.inspector.settings_info.values())

        for info in setting_infos:
            # Skip secret fields
            if info.is_secret:
                settings[info.field_name] = "***hidden***"
            else:
                settings[info.field_name] = self.get_setting(user_id, info.field_name)

        return settings

    def _convert_value(self, value: str, target_type: Type) -> Any:
        """Convert string value to target type"""
        # Handle Optional types
        origin = get_origin(target_type)
        if origin is not None:
            args = get_args(target_type)
            # For Optional[X], use X as the actual type
            if type(None) in args:
                target_type = next(arg for arg in args if arg is not type(None))

        # Convert based on type
        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "on", "enabled")
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == Path:
            return Path(value)
        elif target_type == str:
            return str(value)
        else:
            # Try to use the type's constructor
            return target_type(value)
