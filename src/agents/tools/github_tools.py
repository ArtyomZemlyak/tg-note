"""
GitHub API tools for autonomous agent
Handles GitHub API interactions
"""

from typing import Any, Dict, Optional
import aiohttp
from loguru import logger


async def tool_github_api(
    params: Dict[str, Any],
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    GitHub API tool
    
    Args:
        params: Tool parameters with 'endpoint', optional 'method' and 'data'
        github_token: Optional GitHub authentication token
        
    Returns:
        Dict with API response
    """
    endpoint = params.get("endpoint", "")
    method = params.get("method", "GET").upper()
    data = params.get("data")
    
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
