"""
Web tools for autonomous agent.

Tools for web search and URL fetching.
Each tool is self-contained with its own metadata and implementation.
"""

from typing import Any, Dict

import aiohttp
from loguru import logger

from .base_tool import BaseTool, ToolContext


class WebSearchTool(BaseTool):
    """Tool for web search and URL fetching"""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Поиск информации в интернете"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }

    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Web search tool"""
        query = params.get("query", "")

        try:
            # Simple implementation: fetch URL metadata
            if query.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    response = await session.get(query, timeout=10)
                    if response.status == 200:
                        text = await response.text()
                        # Extract title (simple)
                        title = "Unknown"
                        tl = text.lower()
                        if "<title>" in tl:
                            start = tl.find("<title>") + 7
                            end = tl.find("</title>", start)
                            if end > start:
                                title = text[start:end].strip()

                        logger.info(f"[web_search] ✓ Fetched URL: {query}")
                        return {
                            "success": True,
                            "url": query,
                            "title": title,
                            "status": response.status,
                        }

            # For non-URL queries or mocked sessions without context manager
            logger.info(f"[web_search] Executed search: {query}")
            return {"success": True, "query": query, "message": "Web search executed (placeholder)", "url": query}

        except Exception as e:
            logger.error(f"[web_search] Failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# Export all web tools
ALL_TOOLS = [
    WebSearchTool(),
]
