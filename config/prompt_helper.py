"""
Prompt helper module for tg-note project

This module provides a wrapper around the promptic library that:
1. Handles the base_dir + relative path pattern used in the codebase
2. Provides proper version resolution for .vX.md file naming
3. Supports variable substitution via Jinja2-style templating

AICODE-NOTE: The promptic library's render() function doesn't have a base_dir parameter.
This helper bridges the gap between the expected API and the actual promptic API.
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

# Default prompts directory (relative to this file)
DEFAULT_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _find_latest_version_file(prompt_dir: Path, base_name: str) -> Optional[Path]:
    """
    Find the latest version of a prompt file in a directory.

    Looks for files matching pattern: {base_name}.v{version}.md
    Returns the file with the highest version number.

    Args:
        prompt_dir: Directory to search in
        base_name: Base name of the prompt (e.g., "instruction")

    Returns:
        Path to the latest version file, or None if not found
    """
    if not prompt_dir.exists():
        return None

    # Pattern for versioned files: base_name.vX.md or base_name.vX.Y.Z.md
    version_pattern = re.compile(rf"^{re.escape(base_name)}\.v(\d+(?:\.\d+)*)\.md$")

    versioned_files = []
    for f in prompt_dir.iterdir():
        if f.is_file():
            match = version_pattern.match(f.name)
            if match:
                version_str = match.group(1)
                # Parse version as tuple of integers for proper sorting
                version_tuple = tuple(int(x) for x in version_str.split("."))
                versioned_files.append((version_tuple, f))

    if not versioned_files:
        # Fallback: try to find a file without version suffix
        fallback = prompt_dir / f"{base_name}.md"
        if fallback.exists():
            return fallback
        return None

    # Sort by version tuple (highest first) and return the file with highest version
    versioned_files.sort(key=lambda x: x[0], reverse=True)
    return versioned_files[0][1]


def render_prompt(
    prompt_path: str,
    base_dir: Optional[Path] = None,
    version: str = "latest",
    vars: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Render a prompt template with variable substitution.

    This function provides a wrapper around promptic that supports:
    - base_dir + relative path pattern
    - Automatic version resolution for .vX.md files
    - Jinja2-style variable substitution

    Args:
        prompt_path: Relative path to prompt (e.g., "qwen_code_cli/instruction")
        base_dir: Base directory for prompts (defaults to config/prompts)
        version: Version specification ("latest" or specific like "v1")
        vars: Variables for template substitution

    Returns:
        Rendered prompt string

    Raises:
        FileNotFoundError: If prompt file not found
        ValueError: If version not found

    Example:
        >>> content = render_prompt(
        ...     "qwen_code_cli/instruction",
        ...     vars={"instruction_media": "...", "response_format": "..."}
        ... )
    """
    if base_dir is None:
        base_dir = DEFAULT_PROMPTS_DIR

    if vars is None:
        vars = {}

    # Parse the prompt path
    path_parts = prompt_path.split("/")
    if len(path_parts) < 2:
        # Single name like "instruction" - use as base_name in base_dir
        prompt_dir = base_dir
        base_name = path_parts[0]
    else:
        # Path like "qwen_code_cli/instruction"
        prompt_dir = base_dir / "/".join(path_parts[:-1])
        base_name = path_parts[-1]

    # Find the appropriate version file
    if version == "latest":
        prompt_file = _find_latest_version_file(prompt_dir, base_name)
    else:
        # Specific version requested
        # Try exact match first (e.g., v1 -> instruction.v1.md)
        version_num = version.lstrip("v")
        prompt_file = prompt_dir / f"{base_name}.v{version_num}.md"
        if not prompt_file.exists():
            # Try finding as-is
            prompt_file = prompt_dir / f"{base_name}.{version}.md"
            if not prompt_file.exists():
                prompt_file = None

    if prompt_file is None or not prompt_file.exists():
        available_files = list(prompt_dir.glob(f"{base_name}*.md")) if prompt_dir.exists() else []
        available_str = ", ".join(f.name for f in available_files) if available_files else "none"
        raise FileNotFoundError(
            f"Prompt '{prompt_path}' version '{version}' not found in {prompt_dir}. "
            f"Available: {available_str}"
        )

    logger.debug(f"Loading prompt from: {prompt_file}")

    # Read the template content
    template_content = prompt_file.read_text(encoding="utf-8")

    # Perform variable substitution
    # Support both {var} and {{var}} patterns for compatibility
    rendered_content = template_content
    for var_name, var_value in vars.items():
        # Replace {var_name} patterns (Jinja2 style without spaces)
        rendered_content = rendered_content.replace(f"{{{var_name}}}", str(var_value))
        # Also support {{ var_name }} with spaces
        rendered_content = rendered_content.replace(f"{{{{ {var_name} }}}}", str(var_value))

    return rendered_content


# Alias for backward compatibility
def promptic_render(
    prompt_path: str,
    base_dir: Optional[Path] = None,
    version: str = "latest",
    vars: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Alias for render_prompt() for backward compatibility.

    AICODE-NOTE: This function name matches the import pattern used in the codebase:
    `from promptic import render as promptic_render`
    """
    return render_prompt(prompt_path, base_dir=base_dir, version=version, vars=vars)
