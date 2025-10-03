"""
Configuration module
Exports settings and config helpers
"""

from .settings import settings

# Import config modules for easier access
from . import agent_prompts
from . import kb_structure

__all__ = ["settings", "agent_prompts", "kb_structure"]