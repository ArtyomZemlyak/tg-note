"""
Application Settings
Loads configuration from environment variables using pydantic-settings
"""

from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, field_validator, field_serializer
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram bot token")
    ALLOWED_USER_IDS: Union[str, List[int]] = Field(
        default="",
        description="Comma-separated list of allowed user IDs"
    )
    
    # Agent System Settings (for future)
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    
    # Knowledge Base Settings
    KB_PATH: Path = Field(default=Path("./knowledge_base"), description="Path to knowledge base")
    KB_GIT_ENABLED: bool = Field(default=True, description="Enable Git operations")
    KB_GIT_AUTO_PUSH: bool = Field(default=True, description="Auto-push to remote")
    KB_GIT_REMOTE: str = Field(default="origin", description="Git remote name")
    KB_GIT_BRANCH: str = Field(default="main", description="Git branch name")
    
    # Processing Settings
    MESSAGE_GROUP_TIMEOUT: int = Field(default=30, description="Message grouping timeout in seconds")
    PROCESSED_LOG_PATH: Path = Field(
        default=Path("./data/processed.json"),
        description="Path to processed messages log"
    )
    
    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: Optional[Path] = Field(default=Path("./logs/bot.log"), description="Log file path")
    
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
