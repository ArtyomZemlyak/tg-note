"""
Memory Agent Settings

Configuration for the memory agent.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class MemoryAgentSettings(BaseSettings):
    """Settings for the Memory Agent"""
    
    # Model settings
    MEM_AGENT_MODEL: str = Field(
        default="driaforall/mem-agent",
        description="HuggingFace model ID for memory agent"
    )
    MEM_AGENT_MODEL_PRECISION: str = Field(
        default="4bit",
        description="Model precision: 4bit, 8bit, or fp16"
    )
    
    # Backend settings
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
    
    # Memory path
    MEM_AGENT_MEMORY_PATH: Path = Field(
        default=Path("data/memory"),
        description="Path to store memory files"
    )
    
    # Agent limits
    MEM_AGENT_MAX_TOOL_TURNS: int = Field(
        default=20,
        description="Maximum number of tool execution turns"
    )
    MEM_AGENT_TIMEOUT: int = Field(
        default=20,
        description="Timeout for sandboxed code execution (seconds)"
    )
    
    # Memory size limits
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
    
    def get_backend(self) -> str:
        """
        Determine the backend to use
        
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
    
    def get_model_path(self) -> Path:
        """
        Get the path where the model will be cached
        
        Returns:
            Path to model cache
        """
        # Use HuggingFace cache directory
        cache_home = os.environ.get(
            "HF_HOME",
            os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
        )
        return Path(cache_home) / "hub" / f"models--{self.MEM_AGENT_MODEL.replace('/', '--')}"
    
    def ensure_memory_path_exists(self) -> None:
        """Ensure memory path exists"""
        self.MEM_AGENT_MEMORY_PATH.mkdir(parents=True, exist_ok=True)