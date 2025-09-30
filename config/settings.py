"""
Application Settings
Loads configuration from environment variables
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ALLOWED_USER_IDS: List[int] = [
        int(uid.strip()) 
        for uid in os.getenv("ALLOWED_USER_IDS", "").split(",")
        if uid.strip()
    ]
    
    # Agent System Settings (for future)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # Knowledge Base Settings
    KB_PATH: Path = Path(os.getenv("KB_PATH", "./knowledge_base"))
    KB_GIT_ENABLED: bool = os.getenv("KB_GIT_ENABLED", "true").lower() == "true"
    KB_GIT_AUTO_PUSH: bool = os.getenv("KB_GIT_AUTO_PUSH", "true").lower() == "true"
    KB_GIT_REMOTE: str = os.getenv("KB_GIT_REMOTE", "origin")
    KB_GIT_BRANCH: str = os.getenv("KB_GIT_BRANCH", "main")
    
    # Processing Settings
    MESSAGE_GROUP_TIMEOUT: int = int(os.getenv("MESSAGE_GROUP_TIMEOUT", "30"))
    PROCESSED_LOG_PATH: Path = Path(os.getenv("PROCESSED_LOG_PATH", "./data/processed.json"))
    
    # Logging Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[Path] = Path(os.getenv("LOG_FILE", "./logs/bot.log")) if os.getenv("LOG_FILE") else None
    
    def validate(self) -> List[str]:
        """
        Validate settings
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        if not self.ALLOWED_USER_IDS:
            errors.append("ALLOWED_USER_IDS must contain at least one user ID")
        
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