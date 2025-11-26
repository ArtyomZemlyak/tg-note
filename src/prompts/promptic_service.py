"""
Promptic Service - Unified Prompt Management for tg-note

This module provides a unified interface for prompt management using the promptic library.
It supports:
- File-first architecture with versioning
- Single render() call for all prompt types
- Variable substitution with hierarchical scoping
- Export functionality for rendered prompts

Usage:
    from src.prompts.promptic_service import prompt_service

    # Render a complete prompt for note mode in ONE LINE
    prompt = prompt_service.render(
        "note_mode",
        locale="ru",
        version="latest",
        vars={"text": "User content", "urls": ["https://example.com"]}
    )

    # Render a complete prompt for ask mode in ONE LINE
    prompt = prompt_service.render(
        "ask_mode",
        locale="ru",
        version="latest",
        vars={"question": "What is GPT-4?", "kb_path": "/path/to/kb"}
    )

    # Render agent instruction
    instruction = prompt_service.render("agent_instruction", locale="ru")

    # Export rendered prompt to file
    prompt_service.render(
        "note_mode",
        locale="ru",
        vars={...},
        export_to="output/note_prompt.md"
    )

AICODE-NOTE: This service wraps promptic library to provide tg-note specific
functionality. All prompts are stored in config/prompts/ with versioned files.

The service provides a single entry point for all modes:
- note_mode: Processing user content into knowledge base
- ask_mode: Answering questions from knowledge base
- agent_mode: Autonomous agent operations
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from loguru import logger

# Import promptic library functions
try:
    from promptic import export_version as promptic_export
    from promptic import render as promptic_render

    PROMPTIC_AVAILABLE = True
except ImportError:
    # Fallback to None if promptic is not installed
    promptic_render = None
    promptic_export = None
    PROMPTIC_AVAILABLE = False
    logger.warning("promptic library not installed, falling back to legacy registry")

# AICODE-NOTE: Base directory for prompts follows promptic file-first convention
# Prompts are organized as: config/prompts/{category}/{name}_v{version}.md
PROMPTS_BASE_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"


# AICODE-NOTE: Mapping from unified prompt names to legacy registry keys
# This allows using simple names like "note_mode" while still using legacy files
PROMPT_NAME_MAPPING = {
    # Agent instructions
    "agent_instruction": "qwen_code_cli.instruction",
    "qwen_code_cli": "qwen_code_cli.instruction",
    "autonomous_agent": "autonomous_agent.instruction",
    "ask_instruction": "ask_mode.instruction",
    "ask_mode_instruction": "ask_mode.instruction",
    # Templates
    "content_processing": "content_processing.template",
    "urls_section": "content_processing.urls_section",
    "kb_query": "kb_query.template",
    # Component instructions
    "media": "media.instruction",
    "media_instruction": "media.instruction",
    "response_formatter": "response_formatter.instruction",
}


class PromptMode:
    """Prompt mode constants for different agent modes."""

    NOTE = "note"  # Default mode - processing notes/content
    ASK = "ask"  # Question answering mode
    AGENT = "agent"  # Autonomous agent mode


class PrompticService:
    """
    Unified prompt service using promptic library.

    This service provides a single entry point for all prompt operations in tg-note.
    It uses promptic's render() function with file-first architecture and versioning.

    The key design principle is that any prompt can be obtained with a single render() call:

        prompt = prompt_service.render(
            "note_mode_prompt",
            version="latest",
            vars={"text": "content", "urls": []},
            export_to="output/prompt.md"  # optional
        )

    This enables:
    1. File-first architecture - prompts are Markdown files
    2. Versioning - prompts have semantic versions (v1.0.0, v2.0.0)
    3. Variable substitution - dynamic content injection
    4. Export capability - save rendered prompts to files
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize the promptic service.

        Args:
            prompts_dir: Base directory for prompts (defaults to config/prompts/)
        """
        self.prompts_dir = prompts_dir or PROMPTS_BASE_DIR
        self._promptic_available = PROMPTIC_AVAILABLE

        # AICODE-NOTE: Cache for compiled ResponseFormatter prompt
        self._response_format_cache: Dict[str, str] = {}
        # Cache for rendered prompt components
        self._component_cache: Dict[str, str] = {}

        logger.debug(f"PrompticService initialized with prompts_dir: {self.prompts_dir}")
        logger.debug(f"Promptic library available: {self._promptic_available}")

    def _get_response_format(self, github_url: Optional[str] = None) -> str:
        """
        Get the ResponseFormatter format string (cached).

        Args:
            github_url: Optional GitHub URL for file links

        Returns:
            JSON format string for ResponseFormatter
        """
        cache_key = github_url or "__default__"

        if cache_key not in self._response_format_cache:
            from src.bot.response_formatter import ResponseFormatter

            formatter = ResponseFormatter(github_url=github_url)
            example = {field.name: field.generate_example() for field in formatter.fields}
            self._response_format_cache[cache_key] = json.dumps(
                example, ensure_ascii=False, indent=2
            )

        return self._response_format_cache[cache_key]

    def render(
        self,
        prompt_name: str,
        *,
        version: str = "latest",
        locale: str = "ru",
        vars: Optional[Dict[str, Any]] = None,
        export_to: Optional[Union[str, Path]] = None,
    ) -> str:
        """
        Render a prompt using promptic library.

        This is the main entry point for rendering ANY prompt in tg-note.
        It provides a unified interface that enables single-line prompt loading.

        Supported prompt names:
        - "note_mode_prompt": Complete prompt for note/content processing
        - "ask_mode_prompt": Complete prompt for question answering
        - "agent_instruction": Qwen CLI agent instruction
        - "ask_instruction": Ask mode agent instruction
        - "content_processing": Content processing template
        - "kb_query": KB query template
        - "media": Media handling instruction
        - "response_formatter": Response format instruction
        - "autonomous_agent": Autonomous agent instruction

        Args:
            prompt_name: Name of the prompt
            version: Version specification ("latest", "v1", "v1.0", "v1.0.0")
            locale: Locale for the prompt ("ru", "en")
            vars: Variables for substitution. For composite prompts like note_mode_prompt,
                  can include: text, urls, question, kb_path, context, github_url
            export_to: Optional path to export rendered prompt

        Returns:
            Rendered prompt string

        Example:
            # Single line for complete note mode prompt
            >>> prompt = prompt_service.render(
            ...     "note_mode_prompt",
            ...     version="latest",
            ...     vars={"text": "Article content", "urls": ["https://example.com"]}
            ... )

            # Single line for ask mode prompt
            >>> prompt = prompt_service.render(
            ...     "ask_mode_prompt",
            ...     version="latest",
            ...     vars={"question": "What is GPT?", "kb_path": "/kb"}
            ... )
        """
        vars = vars or {}

        # Handle composite prompt names (mode prompts)
        if prompt_name == "note_mode_prompt":
            return self._render_note_mode_prompt(
                locale=locale,
                version=version,
                vars=vars,
                export_to=export_to,
            )
        elif prompt_name == "ask_mode_prompt":
            return self._render_ask_mode_prompt(
                locale=locale,
                version=version,
                vars=vars,
                export_to=export_to,
            )

        # Handle simple prompt names using legacy registry
        return self._legacy_render(prompt_name, locale, version, vars, export_to)

    def _render_note_mode_prompt(
        self,
        locale: str,
        version: str,
        vars: Dict[str, Any],
        export_to: Optional[Union[str, Path]],
    ) -> str:
        """
        Render complete note mode prompt.

        This combines all components:
        - Agent instruction
        - Media instruction
        - Response formatter
        - Content processing template
        """
        text = vars.get("text", "")
        urls = vars.get("urls", [])
        github_url = vars.get("github_url")
        custom_instruction = vars.get("instruction")

        # Build media instruction
        media_instruction = self._legacy_render("media", locale, version, {})

        # Build response format
        response_format = self._get_response_format(github_url)
        response_formatter_prompt = self._legacy_render(
            "response_formatter",
            locale,
            version,
            {"response_format": response_format},
        )

        # Build or use custom agent instruction
        if custom_instruction:
            instruction = custom_instruction
        else:
            instruction = self._legacy_render(
                "agent_instruction",
                locale,
                version,
                {
                    "instruction_media": media_instruction,
                    "response_format": response_formatter_prompt,
                },
            )

        # Build URLs section
        urls_section = ""
        if urls:
            url_list = "\n".join([f"- {url}" for url in urls])
            urls_section = self._legacy_render(
                "urls_section",
                locale,
                version,
                {"url_list": url_list},
            )

        # Build the complete prompt
        prompt = self._legacy_render(
            "content_processing",
            locale,
            version,
            {
                "instruction": instruction,
                "instruction_media": media_instruction,
                "text": text,
                "urls_section": urls_section,
            },
        )

        # Export if requested
        if export_to:
            self._export_to_file(prompt, export_to)

        return prompt

    def _render_ask_mode_prompt(
        self,
        locale: str,
        version: str,
        vars: Dict[str, Any],
        export_to: Optional[Union[str, Path]],
    ) -> str:
        """
        Render complete ask mode prompt.

        This combines:
        - Ask mode instruction
        - KB query template
        - Response formatter
        """
        question = vars.get("question", "")
        kb_path = vars.get("kb_path", "")
        context = vars.get("context", "")
        github_url = vars.get("github_url")

        # Build media instruction
        media_instruction = self._legacy_render("media", locale, version, {})

        # Build response format
        response_format = self._get_response_format(github_url)
        response_formatter_prompt = self._legacy_render(
            "response_formatter",
            locale,
            version,
            {"response_format": response_format},
        )

        # Build KB query
        kb_query = self._legacy_render(
            "kb_query",
            locale,
            version,
            {
                "kb_path": kb_path,
                "question": question,
                "response_format": response_formatter_prompt,
            },
        )

        # Add context if provided
        prompt = f"{context}\n\n{kb_query}" if context else kb_query

        # Export if requested
        if export_to:
            self._export_to_file(prompt, export_to)

        return prompt

    def _export_to_file(self, content: str, export_path: Union[str, Path]) -> None:
        """Export rendered content to a file."""
        path = Path(export_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.debug(f"Exported prompt to: {path}")

    def _legacy_render(
        self,
        prompt_name: str,
        locale: str,
        version: Optional[str],
        vars: Optional[Dict[str, Any]],
        export_to: Optional[Union[str, Path]] = None,
    ) -> str:
        """
        Render prompt using legacy prompt registry.

        Args:
            prompt_name: Name of the prompt
            locale: Locale for the prompt
            version: Version specification
            vars: Variables for substitution
            export_to: Optional path to export rendered prompt

        Returns:
            Rendered prompt string
        """
        from src.prompts.registry import prompt_registry

        # Map unified name to legacy registry key
        key = PROMPT_NAME_MAPPING.get(prompt_name, prompt_name)

        # Convert path-style name to dot-style for legacy registry
        # e.g., "qwen_code_cli/instruction" -> "qwen_code_cli.instruction"
        key = key.replace("/", ".")

        # Parse version for legacy registry
        legacy_version = None
        if version and version != "latest":
            # Convert "v1.0.0" to "v1" format for legacy registry
            legacy_version = version

        try:
            content = prompt_registry.get(key, locale=locale, version=legacy_version)
        except FileNotFoundError:
            logger.error(f"Prompt not found: {key} (locale={locale}, version={legacy_version})")
            raise

        # Apply variable substitution
        if vars:
            for key_name, value in vars.items():
                placeholder = "{" + key_name + "}"
                if placeholder in content:
                    content = content.replace(placeholder, str(value))

        # Export if requested
        if export_to:
            self._export_to_file(content, export_to)

        return content

    def render_agent_instruction(
        self,
        locale: str = "ru",
        version: str = "latest",
        *,
        instruction_media: Optional[str] = None,
        response_format: Optional[str] = None,
        github_url: Optional[str] = None,
    ) -> str:
        """
        Render the qwen code CLI agent instruction.

        This is the primary instruction for the autonomous agent (note mode).

        Args:
            locale: Locale for the instruction
            version: Version specification
            instruction_media: Media handling instruction (auto-loaded if not provided)
            response_format: Response format instruction (auto-generated if not provided)
            github_url: GitHub URL for file links

        Returns:
            Rendered agent instruction
        """
        # Auto-load media instruction if not provided
        if instruction_media is None:
            instruction_media = self._legacy_render("media", locale, version, {})

        # Auto-generate response format if not provided
        if response_format is None:
            response_format_json = self._get_response_format(github_url)
            response_format = self._legacy_render(
                "response_formatter",
                locale,
                version,
                {"response_format": response_format_json},
            )

        return self._legacy_render(
            "agent_instruction",
            locale,
            version,
            {
                "instruction_media": instruction_media,
                "response_format": response_format,
            },
        )

    def render_note_prompt(
        self,
        text: str,
        *,
        urls: Optional[List[str]] = None,
        locale: str = "ru",
        version: str = "latest",
        instruction: Optional[str] = None,
        instruction_media: Optional[str] = None,
        github_url: Optional[str] = None,
        export_to: Optional[Union[str, Path]] = None,
    ) -> str:
        """
        Render a complete prompt for note/content processing mode.

        This is a convenience method that wraps render("note_mode_prompt", ...).
        For the simplest API, use:

            prompt = prompt_service.render(
                "note_mode_prompt",
                vars={"text": "...", "urls": [...]}
            )

        Args:
            text: User text content to process
            urls: List of URLs from the content
            locale: Locale for the prompt
            version: Version specification
            instruction: Custom agent instruction (uses default if not provided)
            instruction_media: Media handling instruction (auto-loaded if not provided)
            github_url: GitHub URL for file links
            export_to: Optional path to export rendered prompt

        Returns:
            Complete rendered prompt for note mode
        """
        return self.render(
            "note_mode_prompt",
            version=version,
            locale=locale,
            vars={
                "text": text,
                "urls": urls or [],
                "instruction": instruction,
                "github_url": github_url,
            },
            export_to=export_to,
        )

    def render_ask_prompt(
        self,
        question: str,
        kb_path: str,
        *,
        context: Optional[str] = None,
        locale: str = "ru",
        version: str = "latest",
        instruction_media: Optional[str] = None,
        github_url: Optional[str] = None,
        export_to: Optional[Union[str, Path]] = None,
    ) -> str:
        """
        Render a complete prompt for ask/question answering mode.

        This is a convenience method that wraps render("ask_mode_prompt", ...).
        For the simplest API, use:

            prompt = prompt_service.render(
                "ask_mode_prompt",
                vars={"question": "...", "kb_path": "..."}
            )

        Args:
            question: User's question
            kb_path: Path to the knowledge base
            context: Optional conversation context
            locale: Locale for the prompt
            version: Version specification
            instruction_media: Media handling instruction
            github_url: GitHub URL for file links
            export_to: Optional path to export rendered prompt

        Returns:
            Complete rendered prompt for ask mode
        """
        return self.render(
            "ask_mode_prompt",
            version=version,
            locale=locale,
            vars={
                "question": question,
                "kb_path": kb_path,
                "context": context or "",
                "github_url": github_url,
            },
            export_to=export_to,
        )

    def render_ask_instruction(
        self,
        locale: str = "ru",
        version: str = "latest",
        *,
        instruction_media: Optional[str] = None,
    ) -> str:
        """
        Render the ask mode agent instruction.

        Args:
            locale: Locale for the instruction
            version: Version specification
            instruction_media: Media handling instruction

        Returns:
            Rendered ask mode instruction
        """
        # Auto-load media instruction if not provided
        if instruction_media is None:
            instruction_media = self._legacy_render("media", locale, version, {})

        return self._legacy_render(
            "ask_instruction",
            locale,
            version,
            {"instruction_media": instruction_media},
        )

    def render_response_formatter_prompt(
        self,
        locale: str = "ru",
        version: str = "latest",
        *,
        github_url: Optional[str] = None,
    ) -> str:
        """
        Render the response formatter instruction.

        Args:
            locale: Locale for the instruction
            version: Version specification
            github_url: GitHub URL for file links

        Returns:
            Rendered response formatter prompt
        """
        # Get the response format JSON
        response_format = self._get_response_format(github_url)

        return self._legacy_render(
            "response_formatter",
            locale,
            version,
            {"response_format": response_format},
        )

    def render_media_instruction(
        self,
        locale: str = "ru",
        version: str = "latest",
    ) -> str:
        """
        Render the media handling instruction.

        Args:
            locale: Locale for the instruction
            version: Version specification

        Returns:
            Rendered media instruction
        """
        return self._legacy_render("media", locale, version, {})

    def render_autonomous_agent_instruction(
        self,
        locale: str = "en",
        version: str = "latest",
    ) -> str:
        """
        Render the autonomous agent instruction (used for QwenCodeAgent).

        Args:
            locale: Locale for the instruction
            version: Version specification

        Returns:
            Rendered autonomous agent instruction
        """
        return self._legacy_render("autonomous_agent", locale, version, {})


# Global instance for easy access
prompt_service = PrompticService()


# Convenience functions for direct import
def render_prompt(
    prompt_name: str,
    *,
    version: str = "latest",
    locale: str = "ru",
    vars: Optional[Dict[str, Any]] = None,
    export_to: Optional[Union[str, Path]] = None,
) -> str:
    """
    Render a prompt using the global prompt service.

    This is a convenience function that wraps prompt_service.render().

    Args:
        prompt_name: Name of the prompt
        version: Version specification
        locale: Locale for the prompt
        vars: Variables for substitution
        export_to: Optional path to export rendered prompt

    Returns:
        Rendered prompt string
    """
    return prompt_service.render(
        prompt_name,
        version=version,
        locale=locale,
        vars=vars,
        export_to=export_to,
    )
