"""
Application Settings
Loads configuration from multiple sources with priority:
1. YAML file (config.yaml) - all settings except credentials
2. .env file - credentials and overrides
3. CLI arguments (future)
4. Environment variables - highest priority
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic_settings.sources import YamlConfigSettingsSource


class CliSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source for CLI arguments (future implementation)"""
    
    def __init__(self, settings_cls: Type[BaseSettings]):
        super().__init__(settings_cls)
        self._cli_args: Dict[str, Any] = {}
        # Parse CLI args in the future
        # For now, return empty dict
    
    def get_field_value(
        self, field_name: str, field_info: Any
    ) -> Tuple[Any, str, bool]:
        """Get field value from CLI args"""
        if field_name in self._cli_args:
            return self._cli_args[field_name], field_name, False
        return None, field_name, False
    
    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        """Prepare the field value"""
        return value
    
    def __call__(self) -> Dict[str, Any]:
        """Return all CLI args"""
        return self._cli_args


class Settings(BaseSettings):
    """Application settings loaded from multiple sources"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        yaml_file="config.yaml",  # Custom config for YAML file path
    )
    
    # Telegram Bot Settings (credentials - not in YAML)
    TELEGRAM_BOT_TOKEN: str = Field(
        default="",
        description="Telegram bot token (from .env or env vars only)"
    )
    ALLOWED_USER_IDS: Union[str, List[int]] = Field(
        default="",
        description="Comma-separated list of allowed user IDs"
    )
    
    # Agent System Settings (credentials - not in YAML)
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key (from .env or env vars only)"
    )
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="Anthropic API key (from .env or env vars only)"
    )
    QWEN_API_KEY: Optional[str] = Field(
        default=None,
        description="Qwen API key (from .env or env vars only)"
    )
    GITHUB_TOKEN: Optional[str] = Field(
        default=None,
        description="GitHub personal access token (from .env or env vars only)"
    )
    
    # Agent Configuration (can be in YAML)
    AGENT_TYPE: str = Field(
        default="stub",
        description="Agent type: stub, qwen_code"
    )
    AGENT_MODEL: str = Field(
        default="qwen-max",
        description="Model to use for agent (e.g., qwen-max, qwen-plus)"
    )
    AGENT_INSTRUCTION: Optional[str] = Field(
        default=None,
        description="Custom instruction for the agent"
    )
    AGENT_ENABLE_WEB_SEARCH: bool = Field(
        default=True,
        description="Enable web search tool for agent"
    )
    AGENT_ENABLE_GIT: bool = Field(
        default=True,
        description="Enable git command tool for agent"
    )
    AGENT_ENABLE_GITHUB: bool = Field(
        default=True,
        description="Enable GitHub API tool for agent"
    )
    AGENT_ENABLE_SHELL: bool = Field(
        default=False,
        description="Enable shell command tool for agent (security risk)"
    )
    
    # Knowledge Base Settings (can be in YAML)
    KB_PATH: Path = Field(
        default=Path("./knowledge_base"),
        description="Path to knowledge base"
    )
    KB_GIT_ENABLED: bool = Field(
        default=True,
        description="Enable Git operations"
    )
    KB_GIT_AUTO_PUSH: bool = Field(
        default=True,
        description="Auto-push to remote"
    )
    KB_GIT_REMOTE: str = Field(
        default="origin",
        description="Git remote name"
    )
    KB_GIT_BRANCH: str = Field(
        default="main",
        description="Git branch name"
    )
    
    # Processing Settings (can be in YAML)
    MESSAGE_GROUP_TIMEOUT: int = Field(
        default=30,
        description="Message grouping timeout in seconds"
    )
    PROCESSED_LOG_PATH: Path = Field(
        default=Path("./data/processed.json"),
        description="Path to processed messages log"
    )
    
    # Logging Settings (can be in YAML)
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    LOG_FILE: Optional[Path] = Field(
        default=Path("./logs/bot.log"),
        description="Log file path"
    )
    
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize the sources and their priority.
        
        Priority order (highest priority first):
        1. Environment variables (env_settings) - highest priority
        2. CLI arguments (cli_settings)
        3. .env file (dotenv_settings)
        4. YAML file (yaml_settings)
        5. Default values (init_settings) - lowest priority
        
        Note: In Pydantic, the FIRST source to find a value wins!
        So we return sources in order from highest to lowest priority.
        """
        # Get YAML file path from config
        yaml_file = Path(settings_cls.model_config.get('yaml_file', 'config.yaml'))
        
        # Create custom sources
        yaml_settings = YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file)
        cli_settings = CliSettingsSource(settings_cls)
        
        # Return sources in priority order (leftmost = highest priority)
        return (
            env_settings,       # Highest priority - check first
            cli_settings,       # Check second
            dotenv_settings,    # Check third
            yaml_settings,      # Lowest priority - check last
        )
    
    @field_validator("ALLOWED_USER_IDS", mode="before")
    @classmethod
    def parse_user_ids(cls, v) -> List[int]:
        """Parse comma-separated user IDs from string or return list"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(uid.strip()) for uid in v.split(",") if uid.strip()]
        return []
    
    @field_validator("KB_PATH", "PROCESSED_LOG_PATH", "LOG_FILE", mode="before")
    @classmethod
    def parse_path(cls, v) -> Optional[Path]:
        """Convert string to Path"""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return Path(v)
        return v
    
    def validate(self) -> List[str]:
        """
        Validate settings
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        # No user validation required - anyone can use the bot
        
        return errors
    
    def __repr__(self) -> str:
        """String representation (hiding sensitive data)"""
        return (
            f"Settings(\n"
            f"  TELEGRAM_BOT_TOKEN={'*' * 10 if self.TELEGRAM_BOT_TOKEN else 'NOT_SET'},\n"
            f"  ALLOWED_USER_IDS={self.ALLOWED_USER_IDS},\n"
            f"  KB_PATH={self.KB_PATH},\n"
            f"  KB_GIT_ENABLED={self.KB_GIT_ENABLED},\n"
            f"  MESSAGE_GROUP_TIMEOUT={self.MESSAGE_GROUP_TIMEOUT}\n"
            f")"
        )


# Global settings instance
settings = Settings()
