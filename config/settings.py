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
    ALLOWED_USER_IDS: List[int] = Field(
        default_factory=list,
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
    OPENAI_BASE_URL: Optional[str] = Field(
        default=None,
        description="OpenAI API base URL for custom endpoints (from .env or env vars only)"
    )
    GITHUB_TOKEN: Optional[str] = Field(
        default=None,
        description="GitHub personal access token (from .env or env vars only)"
    )
    
    # Agent Configuration (can be in YAML)
    AGENT_TYPE: str = Field(
        default="stub",
        description="Agent type: stub, qwen_code, qwen_code_cli"
    )
    AGENT_QWEN_CLI_PATH: str = Field(
        default="qwen",
        description="Path to qwen CLI executable"
    )
    AGENT_TIMEOUT: int = Field(
        default=300,
        description="Timeout in seconds for agent operations"
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
    AGENT_ENABLE_FILE_MANAGEMENT: bool = Field(
        default=True,
        description="Enable file operations (create, edit, delete, move files)"
    )
    AGENT_ENABLE_FOLDER_MANAGEMENT: bool = Field(
        default=True,
        description="Enable folder operations (create, delete, move folders)"
    )
    
    # MCP (Model Context Protocol) Settings (can be in YAML)
    AGENT_ENABLE_MCP: bool = Field(
        default=False,
        description="Enable MCP (Model Context Protocol) tools"
    )
    AGENT_ENABLE_MCP_MEMORY: bool = Field(
        default=False,
        description="Enable MCP memory agent tool (local mem-agent via HTTP)"
    )
    MCP_SERVERS_POSTFIX: str = Field(
        default=".mcp_servers",
        description="Postfix for MCP servers directory within KB (e.g., '.mcp_servers' -> kb_path/.mcp_servers)"
    )
    
    # Memory Agent Settings (can be in YAML)
    MEM_AGENT_STORAGE_TYPE: str = Field(
        default="json",
        description="Memory storage type: json (simple, fast) or model (AI-powered semantic search)"
    )
    MEM_AGENT_MODEL: str = Field(
        default="BAAI/bge-m3",
        description="HuggingFace model ID for embeddings (used with 'model' storage type)"
    )
    MEM_AGENT_MODEL_PRECISION: str = Field(
        default="4bit",
        description="Model precision: 4bit, 8bit, or fp16"
    )
    MEM_AGENT_BACKEND: str = Field(
        default="auto",
        description="Backend to use: auto, vllm, mlx, or transformers"
    )
    MEM_AGENT_VLLM_HOST: str = Field(
        default="127.0.0.1",
        description="vLLM server host"
    )
    MEM_AGENT_VLLM_PORT: int = Field(
        default=8001,
        description="vLLM server port"
    )
    MEM_AGENT_MEMORY_POSTFIX: str = Field(
        default="memory",
        description="Postfix for memory directory within KB (e.g., 'memory' -> kb_path/memory)"
    )
    MEM_AGENT_MAX_TOOL_TURNS: int = Field(
        default=20,
        description="Maximum number of tool execution turns"
    )
    MEM_AGENT_TIMEOUT: int = Field(
        default=20,
        description="Timeout for sandboxed code execution (seconds)"
    )
    MEM_AGENT_FILE_SIZE_LIMIT: int = Field(
        default=1024 * 1024,  # 1MB
        description="Maximum file size in bytes"
    )
    MEM_AGENT_DIR_SIZE_LIMIT: int = Field(
        default=1024 * 1024 * 10,  # 10MB
        description="Maximum directory size in bytes"
    )
    MEM_AGENT_MEMORY_SIZE_LIMIT: int = Field(
        default=1024 * 1024 * 100,  # 100MB
        description="Maximum total memory size in bytes"
    )
    
    # Vector Search Settings (can be in YAML)
    VECTOR_SEARCH_ENABLED: bool = Field(
        default=False,
        description="Enable vector search for knowledge base"
    )
    
    # Embedding Model Settings
    VECTOR_EMBEDDING_PROVIDER: str = Field(
        default="sentence_transformers",
        description="Embedding provider: sentence_transformers, openai, infinity"
    )
    VECTOR_EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        description="Embedding model name"
    )
    VECTOR_INFINITY_API_URL: Optional[str] = Field(
        default="http://localhost:7997",
        description="Infinity API URL (for infinity provider)"
    )
    VECTOR_INFINITY_API_KEY: Optional[str] = Field(
        default=None,
        description="Infinity API key (from .env or env vars only)"
    )
    
    # Vector Store Settings
    VECTOR_STORE_PROVIDER: str = Field(
        default="faiss",
        description="Vector store provider: faiss, qdrant"
    )
    VECTOR_QDRANT_URL: Optional[str] = Field(
        default="http://localhost:6333",
        description="Qdrant API URL (for qdrant provider)"
    )
    VECTOR_QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Qdrant API key (from .env or env vars only)"
    )
    VECTOR_QDRANT_COLLECTION: str = Field(
        default="knowledge_base",
        description="Qdrant collection name"
    )
    
    # Chunking Settings
    VECTOR_CHUNKING_STRATEGY: str = Field(
        default="fixed_size_overlap",
        description="Chunking strategy: fixed_size, fixed_size_overlap, semantic"
    )
    VECTOR_CHUNK_SIZE: int = Field(
        default=512,
        description="Chunk size in characters"
    )
    VECTOR_CHUNK_OVERLAP: int = Field(
        default=50,
        description="Overlap between chunks (for fixed_size_overlap)"
    )
    VECTOR_RESPECT_HEADERS: bool = Field(
        default=True,
        description="Respect markdown headers when chunking (for semantic strategy)"
    )
    
    # Search Settings
    VECTOR_SEARCH_TOP_K: int = Field(
        default=5,
        description="Number of results to return in vector search"
    )
    
    # Knowledge Base Settings (can be in YAML)
    KB_PATH: Path = Field(
        default=Path("./knowledge_base"),
        description="Root directory for all knowledge bases"
    )
    KB_TOPICS_ONLY: bool = Field(
        default=True,
        description="Restrict agents to work only in topics/ folder"
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
    
    # Conversation Context Settings (can be in YAML)
    CONTEXT_ENABLED: bool = Field(
        default=True,
        description="Enable conversation context for agents"
    )
    CONTEXT_MAX_TOKENS: int = Field(
        default=2000,
        description="Maximum number of tokens to keep in context"
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
    
    def get_mem_agent_backend(self) -> str:
        """
        Determine the memory agent backend to use
        
        Returns:
            Backend name: vllm, mlx, or transformers
        """
        if self.MEM_AGENT_BACKEND != "auto":
            return self.MEM_AGENT_BACKEND
        
        # Auto-detect based on platform
        import sys
        if sys.platform == "darwin":
            # macOS - prefer MLX if available, otherwise transformers
            try:
                import mlx
                return "mlx"
            except ImportError:
                return "transformers"
        else:
            # Linux/Windows - prefer vLLM if available, otherwise transformers
            try:
                import vllm
                return "vllm"
            except ImportError:
                return "transformers"
    
    def get_mem_agent_model_path(self) -> Path:
        """
        Get the path where the mem-agent model will be cached
        
        Returns:
            Path to model cache
        """
        # Use HuggingFace cache directory
        import os
        cache_home = os.environ.get(
            "HF_HOME",
            os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
        )
        return Path(cache_home) / "hub" / f"models--{self.MEM_AGENT_MODEL.replace('/', '--')}"
    
    def get_mcp_servers_dir(self, kb_path: Path) -> Path:
        """
        Get MCP servers directory for a specific knowledge base
        
        Args:
            kb_path: Path to knowledge base
        
        Returns:
            Full path to MCP servers directory (kb_path/{postfix})
        """
        return kb_path / self.MCP_SERVERS_POSTFIX
    
    def get_mem_agent_memory_path(self, kb_path: Path) -> Path:
        """
        Get memory agent memory path for a specific knowledge base
        
        Args:
            kb_path: Path to knowledge base
        
        Returns:
            Full path to memory directory (kb_path/{postfix})
        """
        return kb_path / self.MEM_AGENT_MEMORY_POSTFIX
    
    def ensure_mem_agent_memory_path_exists(self, kb_path: Path) -> None:
        """
        Ensure memory agent memory path exists for a specific KB
        
        Args:
            kb_path: Path to knowledge base
        """
        memory_path = self.get_mem_agent_memory_path(kb_path)
        memory_path.mkdir(parents=True, exist_ok=True)
    
    def ensure_mcp_servers_dir_exists(self, kb_path: Path) -> None:
        """
        Ensure MCP servers directory exists for a specific KB
        
        Args:
            kb_path: Path to knowledge base
        """
        mcp_dir = self.get_mcp_servers_dir(kb_path)
        mcp_dir.mkdir(parents=True, exist_ok=True)
    
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
