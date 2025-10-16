"""
Memory Agent Settings

This module provides settings for the mem-agent, integrating with the main
application configuration while maintaining compatibility with the original
mem-agent settings.
"""

import os
from pathlib import Path
from typing import Optional

# Try to import from main config, fallback to defaults
try:
    from config.settings import settings as app_settings

    # Agent settings
    MAX_TOOL_TURNS = app_settings.MEM_AGENT_MAX_TOOL_TURNS

    # Memory settings
    FILE_SIZE_LIMIT = app_settings.MEM_AGENT_FILE_SIZE_LIMIT
    DIR_SIZE_LIMIT = app_settings.MEM_AGENT_DIR_SIZE_LIMIT
    MEMORY_SIZE_LIMIT = app_settings.MEM_AGENT_MEMORY_SIZE_LIMIT

    # Engine settings
    SANDBOX_TIMEOUT = app_settings.MEM_AGENT_TIMEOUT

    # Model/API settings (mem-agent specific; do NOT read global OPENAI_* to avoid conflicts)
    # Use only environment variables for these to keep isolation.
    MEM_AGENT_OPENAI_API_KEY: Optional[str] = os.getenv("MEM_AGENT_OPENAI_API_KEY")
    MEM_AGENT_BASE_URL: Optional[str] = os.getenv("MEM_AGENT_BASE_URL")

    # Backward-compatible aliases
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # kept for backward compatibility

except ImportError:
    # Fallback to environment variables and defaults
    MAX_TOOL_TURNS = int(os.getenv("MEM_AGENT_MAX_TOOL_TURNS", "20"))

    FILE_SIZE_LIMIT = int(os.getenv("MEM_AGENT_FILE_SIZE_LIMIT", str(1024 * 1024)))  # 1MB
    DIR_SIZE_LIMIT = int(os.getenv("MEM_AGENT_DIR_SIZE_LIMIT", str(1024 * 1024 * 10)))  # 10MB
    MEMORY_SIZE_LIMIT = int(
        os.getenv("MEM_AGENT_MEMORY_SIZE_LIMIT", str(1024 * 1024 * 100))
    )  # 100MB

    SANDBOX_TIMEOUT = int(os.getenv("MEM_AGENT_TIMEOUT", "20"))

    # Generic OpenAI-compatible endpoint used by mem-agent (env only)
    MEM_AGENT_OPENAI_API_KEY = os.getenv("MEM_AGENT_OPENAI_API_KEY")
    MEM_AGENT_BASE_URL = os.getenv("MEM_AGENT_BASE_URL")

    # Backward-compatible aliases for legacy OpenRouter-based default
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    # Model setting for mem-agent
    MEM_AGENT_MODEL = app_settings.MEM_AGENT_MODEL

# Memory path - will be set dynamically by the agent based on KB path
MEMORY_PATH = "memory"

# Path settings
SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "system_prompt.txt"
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
