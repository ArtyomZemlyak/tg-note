"""
Vector search tools for autonomous agent
Handles semantic search and reindexing
"""

from typing import Any, Dict, Optional
from loguru import logger


async def tool_kb_vector_search(
    params: Dict[str, Any],
    vector_search_manager: Optional[Any]
) -> Dict[str, Any]:
    """
    Vector search in knowledge base
    
    Args:
        params: Tool parameters with 'query' and optional 'top_k' fields
        vector_search_manager: Vector search manager instance
        
    Returns:
        Dict with search results
    """
    if not vector_search_manager:
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
        results = await vector_search_manager.search(
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


async def tool_kb_reindex_vector(
    params: Dict[str, Any],
    vector_search_manager: Optional[Any]
) -> Dict[str, Any]:
    """
    Reindex knowledge base for vector search
    
    Args:
        params: Tool parameters with optional 'force' field
        vector_search_manager: Vector search manager instance
        
    Returns:
        Dict with indexing statistics
    """
    if not vector_search_manager:
        logger.error("[kb_reindex_vector] Vector search manager not configured")
        return {
            "success": False,
            "error": "Vector search is not enabled or not configured"
        }
    
    force = params.get("force", False)
    
    try:
        logger.info(f"[kb_reindex_vector] Starting reindexing (force={force})")
        
        # Perform indexing
        stats = await vector_search_manager.index_knowledge_base(force=force)
        
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
