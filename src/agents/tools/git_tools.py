"""
Git tools for autonomous agent
Handles git command execution with security restrictions
"""

import subprocess
from typing import Any, Dict
from loguru import logger
from config.agent_prompts import SAFE_GIT_COMMANDS


async def tool_git_command(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Git command tool
    
    Args:
        params: Tool parameters with 'command' and optional 'cwd' fields
        
    Returns:
        Dict with command execution results
    """
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
                "error": f"Git command not allowed. Allowed: {safe_commands}"
            }
        
        # Execute command
        result = subprocess.run(
            command.split(),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        success = result.returncode == 0
        if success:
            logger.info(f"[git_command] ✓ Executed: {command}")
        else:
            logger.warning(f"[git_command] Failed: {command} (code {result.returncode})")
        
        return {
            "success": success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    except Exception as e:
        logger.error(f"[git_command] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
