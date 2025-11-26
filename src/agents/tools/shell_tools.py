"""
Shell command tools for autonomous agent.

Tools for shell command execution with security restrictions.
WARNING: This tool poses security risks and should be disabled by default.
Each tool is self-contained with its own metadata and implementation.
"""

import subprocess
from typing import Any, Dict

from loguru import logger

from config.constants import DANGEROUS_SHELL_PATTERNS

from .base_tool import BaseTool, ToolContext


class ShellCommandTool(BaseTool):
    """Tool for executing shell commands (SECURITY RISK - disabled by default)"""

    @property
    def name(self) -> str:
        return "shell_command"

    @property
    def description(self) -> str:
        return "Выполнить shell-команду (по умолчанию отключено)"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
            },
            "required": ["command"],
        }

    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Shell command tool (SECURITY RISK - disabled by default)"""
        if not context.enable_shell:
            logger.warning("[shell_command] Tool is disabled for security")
            return {"success": False, "error": "Shell command tool is disabled for security"}

        command = params.get("command", "")
        cwd = params.get("cwd", ".")

        try:
            # Security: block dangerous commands from config
            dangerous_patterns = DANGEROUS_SHELL_PATTERNS

            if any(pattern in command for pattern in dangerous_patterns):
                logger.error(f"[shell_command] Dangerous pattern detected in: {command}")
                return {"success": False, "error": "Command contains dangerous patterns"}

            # Execute command
            result = subprocess.run(
                command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=30
            )

            success = result.returncode == 0
            if success:
                logger.info(f"[shell_command] ✓ Executed: {command}")
            else:
                logger.warning(f"[shell_command] Failed: {command} (code {result.returncode})")

            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

        except Exception as e:
            logger.error(f"[shell_command] Error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# Export all shell tools
ALL_TOOLS = [
    ShellCommandTool(),
]
