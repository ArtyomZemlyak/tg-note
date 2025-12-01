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
            export_dir: Path to export directory for rendered prompts (optional)
        """
        if prompts_dir is None:
            # Default to config/prompts/
            prompts_dir = Path(__file__).parent.parent.parent / "config" / "prompts"

        self.prompts_dir = prompts_dir
        self.export_dir = export_dir
        self.logger = logger.bind(service="PromptService")

        self.logger.debug(f"PromptService initialized with prompts_dir={self.prompts_dir}")

    def render_prompt(
        self,
        prompt_path: str,
        version: str = "latest",
        vars: Optional[Dict[str, Any]] = None,
        render_mode: str = "file_first",
    ) -> str:
        """
        Render a prompt using promptic.

        AICODE-NOTE: Uses promptic.render() with file-first mode by default.
        References between prompts (@ref()) are resolved by promptic.

        Args:
            prompt_path: Relative path to prompt (e.g., "ask_mode", "autonomous_agent")
            version: Version to load (default: "latest")
            vars: Variables for substitution (e.g., {"response_format": "..."})
            render_mode: Rendering mode (default: "file_first")
                - "file_first": Inline referenced content at @ref() locations
                - "full": Full resolution (not typically needed)

        Returns:
            Rendered prompt string

        Raises:
            FileNotFoundError: If prompt path doesn't exist
            Exception: If rendering fails
        """
        full_path = self.prompts_dir / prompt_path
        self.logger.debug(
            f"Rendering prompt: {prompt_path} (version={version}, "
            f"render_mode={render_mode}, vars={list(vars.keys()) if vars else []})"
        )

        try:
            # Use promptic to render the prompt
            # AICODE-NOTE: render_mode="file_first" inlines @ref() content
            result = render(
                path=str(full_path),
                target_format="markdown",
                render_mode=render_mode,
                vars=vars,
                version=version,
            )

            self.logger.debug(f"Successfully rendered prompt: {prompt_path}")
            return result

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

    def ensure_exported(
        self, mode: str, version: str = "latest", vars: Optional[Dict[str, Any]] = None
    ) -> Optional[Path]:
        """
        Export prompt to export directory if export_dir is set.

        AICODE-NOTE: This is optional - only used if export_dir is configured.
        Most use cases don't need export, just direct rendering.

        Args:
            mode: Mode name ("ask", "agent", "note")
            version: Version to export
            vars: Variables for substitution

        Returns:
            Path to exported prompt, or None if export_dir not set
        """
        if self.export_dir is None:
            self.logger.debug("No export_dir set, skipping export")
            return None

        # Export using promptic
        from promptic import export_version

        mode_map = {
            "ask": "ask_mode",
            "agent": "autonomous_agent",
            "note": "content_processing",
        }

        prompt_path = mode_map.get(mode, mode)
        source_path = self.prompts_dir / prompt_path
        target_dir = self.export_dir / mode

        try:
            export_version(
                source_path=str(source_path),
                version_spec=version,
                target_dir=str(target_dir),
                overwrite=True,
                vars=vars,
            )
            self.logger.debug(f"Exported prompt {mode} to {target_dir}")
            return target_dir

        except Exception as e:
            self.logger.warning(f"Failed to export prompt {mode}: {e}")
            return None


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
