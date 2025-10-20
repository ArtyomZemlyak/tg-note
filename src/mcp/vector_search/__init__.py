"""
Vector Search Module for MCP Hub

This module provides comprehensive vector search capabilities for the MCP Hub:
- Vector search functionality (semantic search)
- Vector database editing (add, delete, update documents)
- Multiple embedding models (SentenceTransformers, OpenAI, Infinity)
- Multiple vector stores (FAISS, Qdrant)
- Flexible chunking strategies

Architecture:
- MCP HUB provides vector search functionality via tools
- MCP HUB provides vector DB editing functionality (add, delete, update documents)
- BOT manages when to use these operations (monitors KB changes and triggers reindexing)

AICODE-NOTE: The bot-side manager (src/bot/vector_search_manager.py) decides when
to trigger reindexing based on KB changes. This module provides the core functionality.
"""

from .chunking import ChunkingStrategy, DocumentChunker
from .embeddings import BaseEmbedder, InfinityEmbedder, OpenAIEmbedder, SentenceTransformerEmbedder
from .factory import VectorSearchFactory
from .manager import VectorSearchManager
from .vector_stores import BaseVectorStore, FAISSVectorStore, QdrantVectorStore

__all__ = [
    # Embedders
    "BaseEmbedder",
    "SentenceTransformerEmbedder",
    "OpenAIEmbedder",
    "InfinityEmbedder",
    # Vector stores
    "BaseVectorStore",
    "FAISSVectorStore",
    "QdrantVectorStore",
    # Chunking
    "DocumentChunker",
    "ChunkingStrategy",
    # Manager and factory
    "VectorSearchManager",
    "VectorSearchFactory",
]
