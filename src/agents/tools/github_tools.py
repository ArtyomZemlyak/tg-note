"""
GitHub API tools for autonomous agent.

Tools for GitHub API interactions.
Each tool is self-contained with its own metadata and implementation.
"""

from typing import Any, Dict, Optional
import aiohttp
from loguru import logger

from .base_tool import BaseTool, ToolContext


class GitHubAPITool(BaseTool):
    """Tool for GitHub API interactions"""
    
    @property
    def name(self) -> str:
        return "github_api"
    
    @property
    def description(self) -> str:
        return "Вызов GitHub API"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string"},
                "method": {"type": "string"},
                "data": {"type": "object"},
            },
            "required": ["endpoint"],
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """GitHub API tool"""
        endpoint = params.get("endpoint", "")
        method = params.get("method", "GET").upper()
        data = params.get("data")
        github_token = context.github_token
        
        try:
            base_url = "https://api.github.com"
            url = f"{base_url}/{endpoint.lstrip('/')}"
            
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AutonomousAgent/1.0"
            }
            
            # Add auth token if available
            if github_token:
                headers["Authorization"] = f"token {github_token}"
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                    timeout=30
                ) as response:
                    result = await response.json()
                    success = response.status < 400
                    
                    if success:
                        logger.info(f"[github_api] ✓ {method} {endpoint}")
                    else:
                        logger.warning(f"[github_api] Failed: {method} {endpoint} (status {response.status})")
                    
                    return {
                        "success": success,
                        "status": response.status,
                        "data": result
                    }
        
        except Exception as e:
            logger.error(f"[github_api] Error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# Export all github tools
ALL_TOOLS = [
    GitHubAPITool(),
]
