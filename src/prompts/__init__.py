"""
Prompt registry module for versioned prompt loading.

This module provides two approaches:
1. Legacy: PromptRegistry - direct file loading with version support
2. Promptic: PrompticService - unified prompt management with promptic library

Usage (recommended - using promptic service):
    from src.prompts import prompt_service, render_prompt

    # Using the service
    instruction = prompt_service.render_agent_instruction(locale="ru")

    # Using convenience function
    prompt = render_prompt("qwen_code_cli", locale="ru", version="latest")

Usage (legacy - direct registry):
    from src.prompts import prompt_registry

    content = prompt_registry.get("qwen_code_cli.instruction", locale="ru")
"""

from .promptic_service import PrompticService, prompt_service, render_prompt
from .registry import PromptRegistry, prompt_registry

__all__ = [
    # Promptic service (recommended)
    "PrompticService",
    "prompt_service",
    "render_prompt",
    # Legacy registry (for backwards compatibility)
    "PromptRegistry",
    "prompt_registry",
]
