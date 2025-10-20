"""
DEPRECATED: Vector Search Module

This module has been moved to src.mcp.vector_search.
This file is kept for backward compatibility only.

AICODE-NOTE: All vector search functionality has been refactored into MCP Hub:
- Core functionality moved to src.mcp.vector_search
- Bot-side coordination remains in src.bot.vector_search_manager
- MCP Hub provides vector search and DB editing tools
- BOT manages when to use these tools (monitors KB changes)

Please update your imports to:
    from src.mcp.vector_search import ...
"""

import warnings

# Re-export from new location for backward compatibility
from src.mcp.vector_search import (
    BaseEmbedder,
    BaseVectorStore,
    ChunkingStrategy,
    DocumentChunker,
    FAISSVectorStore,
    InfinityEmbedder,
    OpenAIEmbedder,
    QdrantVectorStore,
    SentenceTransformerEmbedder,
    VectorSearchFactory,
    VectorSearchManager,
)

# Show deprecation warning on import
warnings.warn(
    "Importing from src.vector_search is deprecated. "
    "Please use src.mcp.vector_search instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "BaseEmbedder",
    "SentenceTransformerEmbedder",
    "OpenAIEmbedder",
    "InfinityEmbedder",
    "BaseVectorStore",
    "FAISSVectorStore",
    "QdrantVectorStore",
    "DocumentChunker",
    "ChunkingStrategy",
    "VectorSearchManager",
    "VectorSearchFactory",
]
