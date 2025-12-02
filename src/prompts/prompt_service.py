"""
Prompt Service - manages prompt loading and rendering using promptic library.

AICODE-NOTE: This service uses promptic's render() function with file-first approach.
Prompts can reference each other using file paths, and promptic handles resolution.
Dynamic content (like response_format) is inserted via vars parameter.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger
from promptic import render


class PromptService:
    """
    Service for loading and rendering prompts using promptic library.

    AICODE-NOTE: Uses file-first approach where prompts reference each other
    by file paths (not inline content). Dynamic vars are passed to render().
    """

    def __init__(self, prompts_dir: Optional[Path] = None, export_dir: Optional[Path] = None):
        """
        Initialize PromptService.

        Args:
            prompts_dir: Path to prompts directory (default: config/prompts/)
            export_dir: Path to export directory for rendered prompts (default: data/prompts/)
        """
        if prompts_dir is None:
            # Default to config/prompts/
            prompts_dir = Path(__file__).parent.parent.parent / "config" / "prompts"

        if export_dir is None:
            # Default to data/prompts/ for qwen CLI access
            export_dir = Path(__file__).parent.parent.parent / "data" / "prompts"
            export_dir.mkdir(parents=True, exist_ok=True)

        self.prompts_dir = prompts_dir
        self.export_dir = export_dir
        self.logger = logger.bind(service="PromptService")

        self.logger.debug(
            f"PromptService initialized with prompts_dir={self.prompts_dir}, export_dir={self.export_dir}"
        )

    def render_prompt(
        self,
        prompt_path: str,
        version: str = "latest",
        vars: Optional[Dict[str, Any]] = None,
        render_mode: str = "file_first",
    ) -> str:
        """
        Render a prompt using promptic with export to files.

        AICODE-NOTE: Uses promptic.render() with export_to parameter.
        Files are exported to export_dir, and main file content is returned as string.
        With render_mode="file_first", @ref() links are preserved and agent reads files.

        Args:
            prompt_path: Relative path to prompt file (e.g., "note_mode_v2.md", "ask_mode_v2.md")
                For files with .md extension - used directly (no version resolution)
                For directories - version resolution applied
            version: Version to load (default: "latest") - only used for directory paths
            vars: Variables for substitution (e.g., {"response_format": "..."})
            render_mode: Rendering mode (default: "file_first")
                - "file_first": Preserve @ref() as file links, export files for agent access
                - "full": Inline all @ref() content into single string (no export)

        Returns:
            Rendered prompt string (main file content)

        Raises:
            FileNotFoundError: If prompt path doesn't exist
            Exception: If rendering fails
        """
        full_path = self.prompts_dir / prompt_path

        # AICODE-NOTE: For .md files, source_base = parent dir (config/prompts/)
        # This allows relative links like qwen_code_cli/instruction.md to resolve correctly
        # For files with extension - don't use version (file is specified directly)
        is_direct_file = prompt_path.endswith(".md")

        # Export target name: remove extension and version suffix for cleaner names
        export_name = prompt_path.replace("/", "_").replace(".md", "")
        export_target = self.export_dir / export_name

        self.logger.debug(
            f"Rendering prompt: {prompt_path} (is_direct_file={is_direct_file}, "
            f"version={version if not is_direct_file else 'N/A'}, "
            f"render_mode={render_mode}, export_to={export_target}, "
            f"vars={list(vars.keys()) if vars else []})"
        )

        try:
            # Use promptic to render and export the prompt
            # AICODE-NOTE: export_to exports files for qwen CLI filesystem access
            # For direct files (.md) - don't pass version, promptic uses file as-is
            # For directories - pass version for resolution
            render_kwargs = {
                "path": str(full_path),
                "target_format": "markdown",
                "render_mode": render_mode,
                "vars": vars,
                "export_to": str(export_target),
                "overwrite": True,
            }
            if not is_direct_file:
                render_kwargs["version"] = version

            result = render(**render_kwargs)

            self.logger.debug(
                f"Successfully rendered and exported prompt: {prompt_path} to {export_target}"
            )

            # Return the main file content as string
            # AICODE-NOTE: ExportResult has root_prompt_content, not content
            if hasattr(result, "root_prompt_content"):
                return result.root_prompt_content
            if hasattr(result, "content"):
                return result.content
            return str(result)

        except FileNotFoundError:
            self.logger.error(f"Prompt not found: {full_path}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to render prompt {prompt_path}: {e}")
            raise

    def render_for_mode(
        self, mode: str, vars: Optional[Dict[str, Any]] = None, version: str = "latest"
    ) -> str:
        """
        Render prompt for a specific mode (ask, agent, note).

        Args:
            mode: Mode name ("ask", "agent", "note")
            vars: Variables for substitution
            version: Version to load (default: "latest")

        Returns:
            Rendered prompt string
        """
        mode_map = {
            "ask": "ask_mode",
            "agent": "qwen_code_cli",
            "note": "content_processing",
        }

        prompt_path = mode_map.get(mode, mode)
        return self.render_prompt(prompt_path, version=version, vars=vars, render_mode="file_first")

    def get_prompt_path(self, mode: str) -> Path:
        """
        Get path to prompt directory for a mode.

        Args:
            mode: Mode name ("ask", "agent", "note")

        Returns:
            Path to prompt directory
        """
        mode_map = {
            "ask": "ask_mode",
            "agent": "autonomous_agent",
            "note": "content_processing",
        }

        prompt_path = mode_map.get(mode, mode)
        return self.prompts_dir / prompt_path


def create_prompt_service(
    prompts_dir: Optional[Path] = None, export_dir: Optional[Path] = None
) -> PromptService:
    """
    Factory function to create PromptService.

    Args:
        prompts_dir: Path to prompts directory (default: config/prompts/)
        export_dir: Path to export directory (optional)

    Returns:
        PromptService instance
    """
    return PromptService(prompts_dir=prompts_dir, export_dir=export_dir)
