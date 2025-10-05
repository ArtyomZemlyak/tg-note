"""
Web tools for autonomous agent
Handles web search and URL fetching
"""

from typing import Any, Dict
import aiohttp
from loguru import logger


async def tool_web_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Web search tool
    
    Args:
        params: Tool parameters with 'query' field
        
    Returns:
        Dict with search results or fetched content
    """
    query = params.get("query", "")
    
    try:
        # Simple implementation: fetch URL metadata
        if query.startswith("http"):
            async with aiohttp.ClientSession() as session:
                async with session.get(query, timeout=10) as response:
                    if response.status == 200:
                        text = await response.text()
                        # Extract title (simple)
                        title = "Unknown"
                        if "<title>" in text.lower():
                            start = text.lower().find("<title>") + 7
                            end = text.lower().find("</title>", start)
                            if end > start:
                                title = text[start:end].strip()
                        
                        logger.info(f"[web_search] ✓ Fetched URL: {query}")
                        return {
                            "success": True,
                            "url": query,
                            "title": title,
                            "status": response.status
                        }
        
        # For non-URL queries, return placeholder
        logger.info(f"[web_search] Executed search: {query}")
        return {
            "success": True,
            "query": query,
            "message": "Web search executed (placeholder)"
        }
    
    except Exception as e:
        logger.error(f"[web_search] Failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
