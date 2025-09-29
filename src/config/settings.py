"""Application configuration settings."""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    secret_key: str = Field(default="dev-secret-key")
    
    # Telegram Bot
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    telegram_webhook_url: Optional[str] = Field(None, description="Webhook URL")
    telegram_webhook_secret: Optional[str] = Field(None, description="Webhook secret")
    allowed_telegram_user_ids: List[int] = Field(default_factory=list)
    
    # AI Services
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview")
    openai_max_tokens: int = Field(default=4000)
    
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229")
    
    ollama_base_url: Optional[str] = Field(None, description="Ollama base URL")
    ollama_model: str = Field(default="llama2:13b")
    
    # GitHub
    github_token: str = Field(..., description="GitHub personal access token")
    github_repo_owner: str = Field(..., description="GitHub repository owner")
    github_repo_name: str = Field(..., description="GitHub repository name")
    github_branch: str = Field(default="main")
    
    # Database
    database_url: str = Field(..., description="Database connection URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(None, description="Sentry DSN")
    
    # File Processing
    max_file_size_mb: int = Field(default=50)
    supported_image_formats: List[str] = Field(
        default_factory=lambda: ["jpg", "jpeg", "png", "gif", "webp"]
    )
    supported_document_formats: List[str] = Field(
        default_factory=lambda: ["pdf", "txt", "docx", "md"]
    )
    
    # Agent Configuration
    agent_temperature: float = Field(default=0.7)
    agent_max_retries: int = Field(default=3)
    agent_timeout_seconds: int = Field(default=30)
    
    # Knowledge Base
    kb_default_category: str = Field(default="general")
    kb_auto_categorize: bool = Field(default=True)
    kb_generate_tags: bool = Field(default=True)
    kb_min_content_length: int = Field(default=10)
    
    @validator("allowed_telegram_user_ids", pre=True)
    def parse_user_ids(cls, v):
        """Parse comma-separated user IDs."""
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v
    
    @validator("supported_image_formats", "supported_document_formats", pre=True)
    def parse_formats(cls, v):
        """Parse comma-separated formats."""
        if isinstance(v, str):
            return [x.strip().lower() for x in v.split(",") if x.strip()]
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def has_ai_service(self) -> bool:
        """Check if any AI service is configured."""
        return bool(
            self.openai_api_key or 
            self.anthropic_api_key or 
            self.ollama_base_url
        )


# Global settings instance
settings = Settings()