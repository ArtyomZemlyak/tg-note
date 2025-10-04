"""
Vector Search Module
Provides flexible vector search capabilities with multiple embedding models and vector stores
"""

from .embeddings import BaseEmbedder, SentenceTransformerEmbedder, OpenAIEmbedder, InfinityEmbedder
from .vector_stores import BaseVectorStore, FAISSVectorStore, QdrantVectorStore
from .chunking import DocumentChunker, ChunkingStrategy
from .manager import VectorSearchManager
from .factory import VectorSearchFactory

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
