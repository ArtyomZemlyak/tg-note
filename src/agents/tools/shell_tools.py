"""
Shell command tools for autonomous agent
Handles shell command execution with security restrictions
WARNING: This tool poses security risks and should be disabled by default
"""

import subprocess
from typing import Any, Dict
from loguru import logger
from config.agent_prompts import DANGEROUS_SHELL_PATTERNS


async def tool_shell_command(
    params: Dict[str, Any],
    enable_shell: bool = False
) -> Dict[str, Any]:
    """
    Shell command tool (SECURITY RISK - disabled by default)
    
    Args:
        params: Tool parameters with 'command' and optional 'cwd' fields
        enable_shell: Whether shell commands are enabled
        
    Returns:
        Dict with command execution results
    """
    if not enable_shell:
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
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
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
            "returncode": result.returncode
        }
    
    except Exception as e:
        logger.error(f"[shell_command] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
