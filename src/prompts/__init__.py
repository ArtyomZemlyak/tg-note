"""
Prompts module - provides prompt loading and rendering via promptic.

AICODE-NOTE: This module exports PromptService for managing prompts with
file-first approach and dynamic variable substitution.
"""

from src.prompts.prompt_service import PromptService, create_prompt_service

__all__ = ["PromptService", "create_prompt_service"]


