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
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import YamlConfigSettingsSource


class CliSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source for CLI arguments (future implementation)"""

    def __init__(self, settings_cls: Type[BaseSettings]):
        super().__init__(settings_cls)
        self._cli_args: Dict[str, Any] = {}
        # Parse CLI args in the future
        # For now, return empty dict

    def get_field_value(self, field_name: str, field_info: Any) -> Tuple[Any, str, bool]:
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


class EnvOverridesSource(PydanticBaseSettingsSource):
    """Custom env source to handle special parsing cases.

    Specifically fixes JSON decoding errors for complex types when env vars are
    empty strings or comma-separated values (common in Docker Compose).
    """

    def __init__(self, settings_cls: Type[BaseSettings]):
        super().__init__(settings_cls)

    def get_field_value(self, field_name: str, field_info: Any) -> Tuple[Any, str, bool]:
        """Return per-field override from environment with robust parsing.

        Only handles `ALLOWED_USER_IDS`; other fields are ignored.
        """
        import json
        import os

        if field_name != "ALLOWED_USER_IDS":
            return None, field_name, False

        raw_allowed = os.environ.get("ALLOWED_USER_IDS")
        if raw_allowed is None:
            return None, field_name, False

        value = raw_allowed.strip()
        if value == "":
            return [], field_name, False

        try:
            if value.startswith("["):
                parsed = json.loads(value)
                return [int(x) for x in parsed], field_name, False
            else:
                return (
                    [int(uid.strip()) for uid in value.split(",") if uid.strip()],
                    field_name,
                    False,
                )
        except Exception:
            # Fallback to robust comma-splitting
            return [int(uid.strip()) for uid in value.split(",") if uid.strip()], field_name, False

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> Dict[str, Any]:
        import json
        import os

        result: Dict[str, Any] = {}

        # Handle ALLOWED_USER_IDS from environment in a resilient way
        raw_allowed = os.environ.get("ALLOWED_USER_IDS")
        if raw_allowed is not None:
            value = raw_allowed.strip()
            if value == "":
                # Empty string means no restriction
                result["ALLOWED_USER_IDS"] = []
            else:
                # Try JSON first if it looks like JSON, otherwise treat as comma-separated
                try:
                    if value.startswith("["):
                        parsed = json.loads(value)
                        result["ALLOWED_USER_IDS"] = [int(x) for x in parsed]
                    else:
                        result["ALLOWED_USER_IDS"] = [
                            int(uid.strip()) for uid in value.split(",") if uid.strip()
                        ]
                except Exception:
                    # Fallback to robust comma-splitting
                    result["ALLOWED_USER_IDS"] = [
                        int(uid.strip()) for uid in value.split(",") if uid.strip()
                    ]

        return result


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
        default="", description="Telegram bot token (from .env or env vars only)"
    )
    ALLOWED_USER_IDS: List[int] = Field(
        default_factory=list, description="Comma-separated list of allowed user IDs"
    )

    # Agent System Settings (credentials - not in YAML)
    OPENAI_API_KEY: Optional[str] = Field(
        default=None, description="OpenAI API key (from .env or env vars only)"
    )
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None, description="Anthropic API key (from .env or env vars only)"
    )
    QWEN_API_KEY: Optional[str] = Field(
        default=None, description="Qwen API key (from .env or env vars only)"
    )
    OPENAI_BASE_URL: Optional[str] = Field(
        default=None,
        description="OpenAI API base URL for custom endpoints (from .env or env vars only)",
    )
    GITHUB_TOKEN: Optional[str] = Field(
        default=None, description="GitHub personal access token (from .env or env vars only)"
    )
    GITHUB_USERNAME: Optional[str] = Field(
        default=None,
        description="GitHub username for HTTPS authentication (from .env or env vars only)",
    )
    GITLAB_TOKEN: Optional[str] = Field(
        default=None, description="GitLab personal access token (from .env or env vars only)"
    )
    GITLAB_USERNAME: Optional[str] = Field(
        default=None,
        description="GitLab username for HTTPS authentication (from .env or env vars only)",
    )

    # Agent Configuration (can be in YAML)
    AGENT_TYPE: str = Field(
        default="stub", description="Agent type: stub, qwen_code, qwen_code_cli"
    )
    AGENT_QWEN_CLI_PATH: str = Field(default="qwen", description="Path to qwen CLI executable")
    AGENT_TIMEOUT: int = Field(default=300, description="Timeout in seconds for agent operations")
    AGENT_MODEL: str = Field(
        default="qwen-max", description="Model to use for agent (e.g., qwen-max, qwen-plus)"
    )
    AGENT_INSTRUCTION: Optional[str] = Field(
        default=None, description="Custom instruction for the agent"
    )
    AGENT_ENABLE_WEB_SEARCH: bool = Field(
        default=True, description="Enable web search tool for agent"
    )
    AGENT_ENABLE_GIT: bool = Field(default=True, description="Enable git command tool for agent")
    AGENT_ENABLE_GITHUB: bool = Field(default=True, description="Enable GitHub API tool for agent")
    AGENT_ENABLE_SHELL: bool = Field(
        default=False, description="Enable shell command tool for agent (security risk)"
    )
    AGENT_ENABLE_FILE_MANAGEMENT: bool = Field(
        default=True, description="Enable file operations (create, edit, delete, move files)"
    )
    AGENT_ENABLE_FOLDER_MANAGEMENT: bool = Field(
        default=True, description="Enable folder operations (create, delete, move folders)"
    )

    # MCP (Model Context Protocol) Settings (can be in YAML)
    AGENT_ENABLE_MCP: bool = Field(
        default=False, description="Enable MCP (Model Context Protocol) tools"
    )
    AGENT_ENABLE_MCP_MEMORY: bool = Field(
        default=False, description="Enable MCP memory agent tool (local memory via HTTP)"
    )
    MCP_TIMEOUT: int = Field(
        default=600, description="Timeout in seconds for MCP requests (default: 600 seconds)"
    )
    VECTOR_SEARCH_BATCH_SIZE: int = Field(
        default=50, description="Batch size for vector search operations (default: 50 documents per batch)"
    )

    # Memory Agent Settings (can be in YAML)
    MEM_AGENT_STORAGE_TYPE: str = Field(
        default="json",
        description="Memory storage type: json (simple, fast) or vector (AI-powered semantic search)",
    )
    MEM_AGENT_MODEL: str = Field(
        default="BAAI/bge-m3",
        description="HuggingFace model ID for embeddings (used with 'vector' storage type)",
    )
    MEM_AGENT_MODEL_PRECISION: str = Field(
        default="4bit", description="Model precision: 4bit, 8bit, or fp16"
    )
    MEM_AGENT_BACKEND: str = Field(
        default="auto", description="Backend to use: auto, vllm, mlx, or transformers"
    )
    MEM_AGENT_BASE_URL: Optional[str] = Field(
        default=None, description="OpenAI-compatible endpoint URL (e.g., http://localhost:8001/v1)"
    )
    MEM_AGENT_OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for mem-agent endpoint (use 'lm-studio' for local servers)",
    )
    MEM_AGENT_MAX_TOOL_TURNS: int = Field(
        default=20, description="Maximum number of tool execution turns"
    )
    MEM_AGENT_TIMEOUT: int = Field(
        default=20, description="Timeout for sandboxed code execution (seconds)"
    )
    MEM_AGENT_FILE_SIZE_LIMIT: int = Field(
        default=1024 * 1024, description="Maximum file size in bytes"  # 1MB
    )
    MEM_AGENT_DIR_SIZE_LIMIT: int = Field(
        default=1024 * 1024 * 10, description="Maximum directory size in bytes"  # 10MB
    )
    MEM_AGENT_MEMORY_SIZE_LIMIT: int = Field(
        default=1024 * 1024 * 100, description="Maximum total memory size in bytes"  # 100MB
    )

    # OpenRouter API Key (for backward compatibility)
    OPENROUTER_API_KEY: Optional[str] = Field(
        default=None, description="OpenRouter API key (for backward compatibility)"
    )

    # Vector Search Settings (can be in YAML)
    VECTOR_SEARCH_ENABLED: bool = Field(
        default=False, description="Enable vector search for knowledge base"
    )

    # Embedding Model Settings
    VECTOR_EMBEDDING_PROVIDER: str = Field(
        default="sentence_transformers",
        description="Embedding provider: sentence_transformers, openai, infinity",
    )
    VECTOR_EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2", description="Embedding model name"
    )
    VECTOR_INFINITY_API_URL: Optional[str] = Field(
        default="http://localhost:7997", description="Infinity API URL (for infinity provider)"
    )
    VECTOR_INFINITY_API_KEY: Optional[str] = Field(
        default=None, description="Infinity API key (from .env or env vars only)"
    )

    # Vector Store Settings
    VECTOR_STORE_PROVIDER: str = Field(
        default="faiss", description="Vector store provider: faiss, qdrant"
    )
    VECTOR_QDRANT_URL: Optional[str] = Field(
        default="http://localhost:6333", description="Qdrant API URL (for qdrant provider)"
    )
    VECTOR_QDRANT_API_KEY: Optional[str] = Field(
        default=None, description="Qdrant API key (from .env or env vars only)"
    )
    VECTOR_QDRANT_COLLECTION: str = Field(
        default="knowledge_base", description="Qdrant collection name"
    )

    # Chunking Settings
    VECTOR_CHUNKING_STRATEGY: str = Field(
        default="fixed_size_overlap",
        description="Chunking strategy: fixed_size, fixed_size_overlap, semantic",
    )
    VECTOR_CHUNK_SIZE: int = Field(default=512, description="Chunk size in characters")
    VECTOR_CHUNK_OVERLAP: int = Field(
        default=50, description="Overlap between chunks (for fixed_size_overlap)"
    )
    VECTOR_RESPECT_HEADERS: bool = Field(
        default=True, description="Respect markdown headers when chunking (for semantic strategy)"
    )

    # Search Settings
    VECTOR_SEARCH_TOP_K: int = Field(
        default=5, description="Number of results to return in vector search"
    )

    # Knowledge Base Settings (can be in YAML)
    KB_PATH: Path = Field(
        default=Path("./knowledge_base"), description="Root directory for all knowledge bases"
    )
    KB_TOPICS_ONLY: bool = Field(
        default=True, description="Restrict agents to work only in topics/ folder"
    )
    KB_GIT_ENABLED: bool = Field(default=True, description="Enable Git operations")
    KB_GIT_AUTO_PUSH: bool = Field(default=True, description="Auto-push to remote")
    KB_GIT_REMOTE: str = Field(default="origin", description="Git remote name")
    KB_GIT_BRANCH: str = Field(default="main", description="Git branch name")

    # Conversation Context Settings (can be in YAML)
    CONTEXT_ENABLED: bool = Field(
        default=True, description="Enable conversation context for agents"
    )
    CONTEXT_MAX_TOKENS: int = Field(
        default=2000, description="Maximum number of tokens to keep in context"
    )

    # Processing Settings (can be in YAML)
    MESSAGE_GROUP_TIMEOUT: int = Field(
        default=30, description="Message grouping timeout in seconds"
    )
    PROCESSED_LOG_PATH: Path = Field(
        default=Path("./data/processed.json"), description="Path to processed messages log"
    )

    # Rate Limiting Settings (can be in YAML)
    RATE_LIMIT_ENABLED: bool = Field(
        default=True, description="Enable rate limiting for agent calls"
    )
    RATE_LIMIT_MAX_REQUESTS: int = Field(
        default=20, description="Maximum agent requests per user per time window"
    )
    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60, description="Rate limit time window in seconds"
    )

    # Health Check Settings (can be in YAML)
    HEALTH_CHECK_INTERVAL: int = Field(
        default=30, description="Interval between health checks in seconds"
    )
    HEALTH_CHECK_MAX_FAILURES: int = Field(
        default=5, description="Maximum consecutive health check failures before giving up"
    )

    # Logging Settings (can be in YAML)
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: Optional[Path] = Field(default=Path("./logs/bot.log"), description="Log file path")

    # Media Processing Settings (can be in YAML)
    MEDIA_PROCESSING_ENABLED: bool = Field(
        default=True, description="Enable media file processing (master switch)"
    )
    MEDIA_PROCESSING_DOCLING_FORMATS: List[str] = Field(
        default_factory=lambda: [
            "pdf",
            "docx",
            "pptx",
            "xlsx",
            "html",
            "md",
            "txt",
            "jpg",
            "jpeg",
            "png",
            "tiff",
        ],
        description="List of file formats to process with Docling",
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
        yaml_file = Path(settings_cls.model_config.get("yaml_file", "config.yaml"))

        # Create custom sources
        yaml_settings = YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file)
        cli_settings = CliSettingsSource(settings_cls)
        env_overrides = EnvOverridesSource(settings_cls)

        # Return sources in priority order (leftmost = highest priority)
        # AICODE-NOTE: Explicit constructor arguments (init_settings) MUST have the
        # highest priority so that direct instantiation like Settings(MEDIA_PROCESSING_ENABLED=False)
        # reliably overrides all other configuration sources.
        return (
            init_settings,  # Highest priority - explicit constructor args
            env_overrides,  # Then normalized env overrides
            env_settings,  # Then standard env vars
            cli_settings,  # Then CLI (reserved)
            dotenv_settings,  # Then .env file
            yaml_settings,  # Finally YAML config
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
            "HF_HOME", os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
        )
        return Path(cache_home) / "hub" / f"models--{self.MEM_AGENT_MODEL.replace('/', '--')}"

    def get_mem_agent_memory_dir(self, user_id: int) -> Path:
        """
        Get memory directory for a specific user

        Args:
            user_id: User ID

        Returns:
            Full path to user's memory directory: data/memory/user_{user_id}
        """
        return Path(f"data/memory/user_{user_id}")

    def is_media_processing_enabled(self) -> bool:
        """
        Check if media processing is enabled globally

        Returns:
            True if media processing is enabled, False otherwise
        """
        return self.MEDIA_PROCESSING_ENABLED

    def get_media_processing_formats(self, processor: str = "docling") -> List[str]:
        """
        Get enabled file formats for a specific media processor

        Args:
            processor: Name of the processor (e.g., "docling")

        Returns:
            List of enabled file format extensions (empty list if processing is disabled)
        """
        # Check if media processing is enabled globally
        if not self.is_media_processing_enabled():
            return []

        if processor == "docling":
            return self.MEDIA_PROCESSING_DOCLING_FORMATS
        # AICODE-NOTE: Add other processors here in the future
        return []

    def is_format_enabled(self, file_format: str, processor: str = "docling") -> bool:
        """
        Check if a specific file format is enabled for processing

        Args:
            file_format: File format/extension (e.g., "pdf", "jpg")
            processor: Name of the processor (default: "docling")

        Returns:
            True if the format is enabled and media processing is active, False otherwise
        """
        # Check if media processing is enabled globally
        if not self.is_media_processing_enabled():
            return False

        formats = self.get_media_processing_formats(processor)
        return file_format.lower() in [fmt.lower() for fmt in formats]

    def ensure_mem_agent_memory_dir_exists(self, user_id: int) -> None:
        """
        Ensure memory directory exists for a specific user

        Args:
            user_id: User ID
        """
        memory_dir = self.get_mem_agent_memory_dir(user_id)
        memory_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> List[str]:
        """
        Validate settings comprehensively

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Required credentials
        if not self.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")

        # Timeout validations
        if self.AGENT_TIMEOUT <= 0:
            errors.append(f"AGENT_TIMEOUT must be positive, got {self.AGENT_TIMEOUT}")

        if self.MESSAGE_GROUP_TIMEOUT < 0:
            errors.append(
                f"MESSAGE_GROUP_TIMEOUT cannot be negative, got {self.MESSAGE_GROUP_TIMEOUT}"
            )

        if self.MEM_AGENT_TIMEOUT <= 0:
            errors.append(f"MEM_AGENT_TIMEOUT must be positive, got {self.MEM_AGENT_TIMEOUT}")

        if self.HEALTH_CHECK_INTERVAL <= 0:
            errors.append(
                f"HEALTH_CHECK_INTERVAL must be positive, got {self.HEALTH_CHECK_INTERVAL}"
            )

        # Rate limit validations
        if self.RATE_LIMIT_ENABLED:
            if self.RATE_LIMIT_MAX_REQUESTS <= 0:
                errors.append(
                    f"RATE_LIMIT_MAX_REQUESTS must be positive, got {self.RATE_LIMIT_MAX_REQUESTS}"
                )
            if self.RATE_LIMIT_WINDOW_SECONDS <= 0:
                errors.append(
                    f"RATE_LIMIT_WINDOW_SECONDS must be positive, got {self.RATE_LIMIT_WINDOW_SECONDS}"
                )

        # Path validations
        if self.KB_PATH:
            # Check if parent directory exists or can be created
            try:
                parent = self.KB_PATH.parent
                if not parent.exists():
                    # Try to create it to validate permissions
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        errors.append(
                            f"KB_PATH parent directory cannot be created: {parent}. Error: {e}"
                        )
            except Exception as e:
                errors.append(f"KB_PATH validation failed: {e}")

        if self.LOG_FILE:
            # Check if log directory can be created
            try:
                log_dir = self.LOG_FILE.parent
                if not log_dir.exists():
                    try:
                        log_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        errors.append(
                            f"LOG_FILE directory cannot be created: {log_dir}. Error: {e}"
                        )
            except Exception as e:
                errors.append(f"LOG_FILE validation failed: {e}")

        # Context validations
        if self.CONTEXT_MAX_TOKENS <= 0:
            errors.append(f"CONTEXT_MAX_TOKENS must be positive, got {self.CONTEXT_MAX_TOKENS}")

        # Vector search validations
        if self.VECTOR_SEARCH_ENABLED:
            if self.VECTOR_CHUNK_SIZE <= 0:
                errors.append(f"VECTOR_CHUNK_SIZE must be positive, got {self.VECTOR_CHUNK_SIZE}")
            if self.VECTOR_CHUNK_OVERLAP < 0:
                errors.append(
                    f"VECTOR_CHUNK_OVERLAP cannot be negative, got {self.VECTOR_CHUNK_OVERLAP}"
                )
            if self.VECTOR_CHUNK_OVERLAP >= self.VECTOR_CHUNK_SIZE:
                errors.append(
                    f"VECTOR_CHUNK_OVERLAP ({self.VECTOR_CHUNK_OVERLAP}) "
                    f"must be less than VECTOR_CHUNK_SIZE ({self.VECTOR_CHUNK_SIZE})"
                )
            if self.VECTOR_SEARCH_TOP_K <= 0:
                errors.append(
                    f"VECTOR_SEARCH_TOP_K must be positive, got {self.VECTOR_SEARCH_TOP_K}"
                )

        # File size validations
        if self.MEM_AGENT_FILE_SIZE_LIMIT <= 0:
            errors.append(
                f"MEM_AGENT_FILE_SIZE_LIMIT must be positive, got {self.MEM_AGENT_FILE_SIZE_LIMIT}"
            )
        if self.MEM_AGENT_DIR_SIZE_LIMIT <= 0:
            errors.append(
                f"MEM_AGENT_DIR_SIZE_LIMIT must be positive, got {self.MEM_AGENT_DIR_SIZE_LIMIT}"
            )
        if self.MEM_AGENT_MEMORY_SIZE_LIMIT <= 0:
            errors.append(
                f"MEM_AGENT_MEMORY_SIZE_LIMIT must be positive, got {self.MEM_AGENT_MEMORY_SIZE_LIMIT}"
            )

        # Log level validation
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of {valid_log_levels}, got {self.LOG_LEVEL}")

        return errors

    def __repr__(self) -> str:
        """String representation (hiding sensitive data)"""
        return (
            f"Settings(\n"
            f"  TELEGRAM_BOT_TOKEN={'*' * 10 if self.TELEGRAM_BOT_TOKEN else 'NOT_SET'},\n"
            f"  ALLOWED_USER_IDS={self.ALLOWED_USER_IDS},\n"
            f"  KB_PATH={self.KB_PATH},\n"
            f"  KB_GIT_ENABLED={self.KB_GIT_ENABLED},\n"
            f"  KB_GIT_AUTO_PUSH={self.KB_GIT_AUTO_PUSH},\n"
            f"  MESSAGE_GROUP_TIMEOUT={self.MESSAGE_GROUP_TIMEOUT}\n"
            f")"
        )


# Global settings instance
settings = Settings()


# ═══════════════════════════════════════════════════════════════════════════════
# Mem-Agent Helper Functions and Constants
# ═══════════════════════════════════════════════════════════════════════════════

import os

# Environment variable overrides for mem-agent (have priority over config)
MEM_AGENT_BASE_URL = os.getenv("MEM_AGENT_BASE_URL", settings.MEM_AGENT_BASE_URL)
MEM_AGENT_OPENAI_API_KEY = os.getenv("MEM_AGENT_OPENAI_API_KEY", settings.MEM_AGENT_OPENAI_API_KEY)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", settings.OPENROUTER_API_KEY)

# Mem-agent constants with environment variable overrides
MAX_TOOL_TURNS = int(os.getenv("MEM_AGENT_MAX_TOOL_TURNS", str(settings.MEM_AGENT_MAX_TOOL_TURNS)))
FILE_SIZE_LIMIT = int(
    os.getenv("MEM_AGENT_FILE_SIZE_LIMIT", str(settings.MEM_AGENT_FILE_SIZE_LIMIT))
)
DIR_SIZE_LIMIT = int(os.getenv("MEM_AGENT_DIR_SIZE_LIMIT", str(settings.MEM_AGENT_DIR_SIZE_LIMIT)))
MEMORY_SIZE_LIMIT = int(
    os.getenv("MEM_AGENT_MEMORY_SIZE_LIMIT", str(settings.MEM_AGENT_MEMORY_SIZE_LIMIT))
)
SANDBOX_TIMEOUT = int(os.getenv("MEM_AGENT_TIMEOUT", str(settings.MEM_AGENT_TIMEOUT)))
MEM_AGENT_MODEL = settings.MEM_AGENT_MODEL

# Memory path - will be set dynamically by the agent based on KB path
MEMORY_PATH = "memory"

# Path settings
SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "mcp"
    / "memory"
    / "mem_agent_impl"
    / "system_prompt.txt"
)
SAVE_CONVERSATION_PATH = Path("output/conversations/")


def get_memory_path(kb_path: Optional[Path] = None) -> Path:
    """
    Get the memory path for a specific knowledge base.

    Args:
        kb_path: Path to knowledge base. If None, uses default.

    Returns:
        Path to memory directory
    """
    if kb_path is None:
        return Path(MEMORY_PATH)
    return kb_path / MEMORY_PATH
