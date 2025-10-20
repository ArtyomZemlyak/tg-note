"""
Git tools for autonomous agent.

Tools for git command execution with security restrictions.
Each tool is self-contained with its own metadata and implementation.
"""

import subprocess
from typing import Any, Dict

from loguru import logger

from config.agent_prompts import SAFE_GIT_COMMANDS
from src.core.events import EventType

from ._event_publisher import publish_kb_git_event
from .base_tool import BaseTool, ToolContext


class GitCommandTool(BaseTool):
    """Tool for executing safe git commands"""

    @property
    def name(self) -> str:
        return "git_command"

    @property
    def description(self) -> str:
        return "Выполнить безопасную git-команду"

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
        """Git command tool"""
        command = params.get("command", "")
        cwd = params.get("cwd", ".")

        try:
            # Security: only allow specific safe git commands from config
            safe_commands = SAFE_GIT_COMMANDS

            cmd_parts = command.split()
            if not cmd_parts or cmd_parts[0] != "git":
                logger.error("[git_command] Command must start with 'git'")
                return {"success": False, "error": "Command must start with 'git'"}

            if len(cmd_parts) < 2 or cmd_parts[1] not in safe_commands:
                logger.error(f"[git_command] Command not allowed: {cmd_parts[1]}")
                return {
                    "success": False,
                    "error": f"Git command not allowed. Allowed: {safe_commands}",
                }

            # Execute command
            result = subprocess.run(
                command.split(), cwd=cwd, capture_output=True, text=True, timeout=30
            )

            success = result.returncode == 0
            if success:
                logger.info(f"[git_command] ✓ Executed: {command}")

                # Publish git events for specific commands
                if len(cmd_parts) >= 2:
                    git_subcommand = cmd_parts[1]

                    # Map git commands to events
                    if git_subcommand == "commit":
                        publish_kb_git_event(
                            EventType.KB_GIT_COMMIT,
                            user_id=context.user_id,
                            source="git_command_tool",
                            command=command,
                        )
                    elif git_subcommand == "push":
                        publish_kb_git_event(
                            EventType.KB_GIT_PUSH,
                            user_id=context.user_id,
                            source="git_command_tool",
                            command=command,
                        )
                    elif git_subcommand == "pull":
                        publish_kb_git_event(
                            EventType.KB_GIT_PULL,
                            user_id=context.user_id,
                            source="git_command_tool",
                            command=command,
                        )
            else:
                logger.warning(f"[git_command] Failed: {command} (code {result.returncode})")

            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

        except Exception as e:
            logger.error(f"[git_command] Error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# Export all git tools
ALL_TOOLS = [
    GitCommandTool(),
]
