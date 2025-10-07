"""
Agent Prompts Configuration
Centralized configuration for all agent prompts and instructions

DEPRECATED: This module is deprecated in favor of YAML-based prompt configuration.
Please use config.prompt_loader.PromptLoader instead.

This file is kept for backward compatibility only.
"""

from typing import Any, Dict, List

from .prompt_loader import get_default_loader

# Initialize prompt loader
_loader = get_default_loader()

# ═══════════════════════════════════════════════════════════════════════════════
# Agent Default Instructions
# Loaded from YAML files for flexibility and versioning
# ═══════════════════════════════════════════════════════════════════════════════

QWEN_CODE_AGENT_INSTRUCTION = _loader.get_instruction("qwen_code_agent")

QWEN_CODE_CLI_AGENT_INSTRUCTION = _loader.get_instruction("qwen_code_cli_agent")

STUB_AGENT_INSTRUCTION = _loader.get_instruction("stub_agent")

KB_QUERY_PROMPT = _loader.get_instruction("kb_query")


# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Templates for Content Processing
# ═══════════════════════════════════════════════════════════════════════════════

CONTENT_PROCESSING_PROMPT_TEMPLATE = _loader.get_template(
    "qwen_code_agent", "content_processing"
)

URLS_SECTION_TEMPLATE = _loader.get_template(
    "qwen_code_agent", "urls_section"
)

KB_QUERY_PROMPT_TEMPLATE = _loader.get_instruction("kb_query")


# ═══════════════════════════════════════════════════════════════════════════════
# Category Detection Keywords
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_KEYWORDS = _loader.get_category_keywords()

DEFAULT_CATEGORY = _loader.get_default_category()


# ═══════════════════════════════════════════════════════════════════════════════
# Stop Words for Keyword Extraction
# ═══════════════════════════════════════════════════════════════════════════════

STOP_WORDS = set(_loader.get_stop_words())


# ═══════════════════════════════════════════════════════════════════════════════
# Markdown Generation Settings
# ═══════════════════════════════════════════════════════════════════════════════

_markdown_config = _loader.get_markdown_config()

# Default sections in generated markdown
DEFAULT_MARKDOWN_SECTIONS = _markdown_config.get("default_sections", [
    "Metadata",
    "Summary", 
    "Content",
    "Links",
    "Additional Context",
    "Keywords",
])

# Maximum lengths for various fields
MAX_TITLE_LENGTH = _markdown_config.get("max_title_length", 60)
MAX_SUMMARY_LENGTH = _markdown_config.get("max_summary_length", 200)
MAX_KEYWORD_COUNT = _markdown_config.get("max_keyword_count", 10)
MAX_TAG_COUNT = _markdown_config.get("max_tag_count", 5)

# Minimum word length for keyword extraction
MIN_KEYWORD_LENGTH = _markdown_config.get("min_keyword_length", 3)


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Safety Settings
# ═══════════════════════════════════════════════════════════════════════════════

_tool_config = _loader.get_tool_safety_config()

# Safe git commands (read-only operations)
SAFE_GIT_COMMANDS = _tool_config.get("safe_git_commands", [
    "status",
    "log",
    "diff",
    "branch",
    "remote",
    "show",
])

# Dangerous shell command patterns to block
DANGEROUS_SHELL_PATTERNS = _tool_config.get("dangerous_shell_patterns", [
    "rm -rf",
    "rm -f",
    "> /dev",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",  # Fork bomb
    "chmod -R",
    "chown -R",
    "sudo",
    "su -",
    "wget",
    "curl",
])


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy Support
# ═══════════════════════════════════════════════════════════════════════════════

# Keep old constant name for backward compatibility
QWEN_CODE_AGENT_INSTRUCTION_OLD = """You are an autonomous knowledge base agent.
Your task is to analyze content...
"""

# Note: This file now dynamically loads all constants from YAML files.
# The old hardcoded constants are kept in comments for reference only.


# ═══════════════════════════════════════════════════════════════════════════════
# Helper Functions for Backward Compatibility
# ═══════════════════════════════════════════════════════════════════════════════

def reload_prompts() -> None:
    """
    Reload all prompts from YAML files
    Useful for hot-reloading in development
    """
    global _loader
    from .prompt_loader import reload_default_loader
    reload_default_loader()
    _loader = get_default_loader()


def get_prompt_version() -> str:
    """
    Get current prompt version
    
    Returns:
        Version string (e.g., "v1")
    """
    return _loader.version


def list_available_agents() -> List[str]:
    """
    List all available agent prompts
    
    Returns:
        List of agent names
    """
    return _loader.list_agents()


def list_prompt_versions() -> List[str]:
    """
    List all available prompt versions
    
    Returns:
        List of version strings
    """
    return _loader.list_versions()
