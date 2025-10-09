"""
Configuration module
Exports settings and config helpers
"""

# Import config modules for easier access
from . import agent_prompts, kb_structure
from .settings import settings

__all__ = ["settings", "agent_prompts", "kb_structure"]
