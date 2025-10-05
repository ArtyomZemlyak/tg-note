"""
Vector search tools for autonomous agent.

Tools for semantic search and reindexing in the knowledge base.
Each tool is self-contained with its own metadata and implementation.
"""

from typing import Any, Dict, Optional
from loguru import logger

from .base_tool import BaseTool, ToolContext


class VectorSearchTool(BaseTool):
    """Tool for semantic vector search in knowledge base"""
    
    @property
    def name(self) -> str:
        return "kb_vector_search"
    
    @property
    def description(self) -> str:
        return "Семантический векторный поиск по базе знаний"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer"},
            },
            "required": ["query"],
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Vector search in knowledge base"""
        if not context.vector_search_manager:
            logger.error("[kb_vector_search] Vector search manager not configured")
            return {
                "success": False,
                "error": "Vector search is not enabled or not configured"
            }
        
        query = params.get("query", "")
        top_k = params.get("top_k", 5)
        
        if not query:
            logger.error("[kb_vector_search] No query provided")
            return {"success": False, "error": "No query provided"}
        
        try:
            logger.info(f"[kb_vector_search] Searching for: {query}")
            
            # Perform vector search
            results = await context.vector_search_manager.search(
                query=query,
                top_k=top_k
            )
            
            logger.info(f"[kb_vector_search] ✓ Found {len(results)} results")
            
            return {
                "success": True,
                "query": query,
                "top_k": top_k,
                "results": results,
                "results_count": len(results)
            }
        
        except Exception as e:
            logger.error(f"[kb_vector_search] Failed: {e}", exc_info=True)
            return {"success": False, "error": f"Vector search failed: {e}"}


class VectorReindexTool(BaseTool):
    """Tool for reindexing knowledge base for vector search"""
    
    @property
    def name(self) -> str:
        return "kb_reindex_vector"
    
    @property
    def description(self) -> str:
        return "Переиндексировать базу знаний для векторного поиска"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"force": {"type": "boolean"}},
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Reindex knowledge base for vector search"""
        if not context.vector_search_manager:
            logger.error("[kb_reindex_vector] Vector search manager not configured")
            return {
                "success": False,
                "error": "Vector search is not enabled or not configured"
            }
        
        force = params.get("force", False)
        
        try:
            logger.info(f"[kb_reindex_vector] Starting reindexing (force={force})")
            
            # Perform indexing
            stats = await context.vector_search_manager.index_knowledge_base(force=force)
            
            logger.info(
                f"[kb_reindex_vector] ✓ Indexing complete: "
                f"{stats['files_processed']} files processed, "
                f"{stats['chunks_created']} chunks created"
            )
            
            return {
                "success": True,
                "stats": stats,
                "message": f"Successfully indexed {stats['files_processed']} files"
            }
        
        except Exception as e:
            logger.error(f"[kb_reindex_vector] Failed: {e}", exc_info=True)
            return {"success": False, "error": f"Reindexing failed: {e}"}


# Export all vector search tools
ALL_TOOLS = [
    VectorSearchTool(),
    VectorReindexTool(),
]
