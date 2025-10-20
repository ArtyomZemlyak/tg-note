"""
Vector Search Factory
Creates vector search components from configuration settings
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from .chunking import ChunkingStrategy, DocumentChunker
from .embeddings import BaseEmbedder, InfinityEmbedder, OpenAIEmbedder, SentenceTransformerEmbedder
from .manager import VectorSearchManager
from .vector_stores import BaseVectorStore, FAISSVectorStore, QdrantVectorStore


class VectorSearchFactory:
    """Factory for creating vector search components from settings"""

    @staticmethod
    def create_embedder(
        provider: str,
        model: str,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        infinity_api_url: Optional[str] = None,
        infinity_api_key: Optional[str] = None,
    ) -> BaseEmbedder:
        """
        Create an embedder based on provider

        Args:
            provider: Embedding provider (sentence_transformers, openai, infinity)
            model: Model name
            openai_api_key: OpenAI API key
            openai_base_url: OpenAI base URL
            infinity_api_url: Infinity API URL
            infinity_api_key: Infinity API key

        Returns:
            BaseEmbedder instance
        """
        provider = provider.lower()

        if provider == "sentence_transformers":
            logger.info(f"Creating SentenceTransformer embedder with model: {model}")
            return SentenceTransformerEmbedder(model_name=model)

        elif provider == "openai":
            logger.info(f"Creating OpenAI embedder with model: {model}")
            return OpenAIEmbedder(
                model_name=model, api_key=openai_api_key, base_url=openai_base_url
            )

        elif provider == "infinity":
            logger.info(f"Creating Infinity embedder with model: {model}")
            return InfinityEmbedder(
                model_name=model,
                api_url=infinity_api_url or "http://localhost:7997",
                api_key=infinity_api_key,
            )

        else:
            raise ValueError(
                f"Unknown embedding provider: {provider}. "
                f"Supported: sentence_transformers, openai, infinity"
            )

    @staticmethod
    def create_vector_store(
        provider: str,
        dimension: int,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        qdrant_collection: str = "knowledge_base",
    ) -> BaseVectorStore:
        """
        Create a vector store based on provider

        Args:
            provider: Vector store provider (faiss, qdrant)
            dimension: Embedding dimension
            qdrant_url: Qdrant API URL
            qdrant_api_key: Qdrant API key
            qdrant_collection: Qdrant collection name

        Returns:
            BaseVectorStore instance
        """
        provider = provider.lower()

        if provider == "faiss":
            logger.info(f"Creating FAISS vector store (dimension: {dimension})")
            return FAISSVectorStore(dimension=dimension)

        elif provider == "qdrant":
            logger.info(
                f"Creating Qdrant vector store "
                f"(collection: {qdrant_collection}, dimension: {dimension})"
            )
            return QdrantVectorStore(
                collection_name=qdrant_collection,
                dimension=dimension,
                url=qdrant_url or "http://localhost:6333",
                api_key=qdrant_api_key,
            )

        else:
            raise ValueError(
                f"Unknown vector store provider: {provider}. " f"Supported: faiss, qdrant"
            )

    @staticmethod
    def create_chunker(
        strategy: str, chunk_size: int = 512, chunk_overlap: int = 50, respect_headers: bool = True
    ) -> DocumentChunker:
        """
        Create a document chunker

        Args:
            strategy: Chunking strategy (fixed_size, fixed_size_overlap, semantic)
            chunk_size: Size of chunks in characters
            chunk_overlap: Overlap between chunks
            respect_headers: Respect markdown headers

        Returns:
            DocumentChunker instance
        """
        strategy = strategy.lower()

        if strategy == "fixed_size":
            chunking_strategy = ChunkingStrategy.FIXED_SIZE
        elif strategy == "fixed_size_overlap":
            chunking_strategy = ChunkingStrategy.FIXED_SIZE_WITH_OVERLAP
        elif strategy == "semantic":
            chunking_strategy = ChunkingStrategy.SEMANTIC
        else:
            raise ValueError(
                f"Unknown chunking strategy: {strategy}. "
                f"Supported: fixed_size, fixed_size_overlap, semantic"
            )

        logger.info(
            f"Creating document chunker "
            f"(strategy: {strategy}, size: {chunk_size}, overlap: {chunk_overlap})"
        )

        return DocumentChunker(
            strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            respect_headers=respect_headers,
        )

    @classmethod
    def create_from_settings(
        cls, settings, index_path: Optional[Path] = None
    ) -> Optional[VectorSearchManager]:
        """
        Create vector search manager from settings
        
        AICODE-NOTE: SOLID - Dependency Inversion Principle
        MCP HUB does not need file system access anymore.
        It works with data provided by BOT.

        Args:
            settings: Settings object with vector search configuration
            index_path: Path to store vector index (defaults to data/vector_index)

        Returns:
            VectorSearchManager instance or None if disabled
        """
        if not settings.VECTOR_SEARCH_ENABLED:
            logger.info("Vector search is disabled")
            return None

        try:
            logger.info("Initializing vector search from settings")

            # Create embedder
            embedder = cls.create_embedder(
                provider=settings.VECTOR_EMBEDDING_PROVIDER,
                model=settings.VECTOR_EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_base_url=settings.OPENAI_BASE_URL,
                infinity_api_url=settings.VECTOR_INFINITY_API_URL,
                infinity_api_key=settings.VECTOR_INFINITY_API_KEY,
            )

            # Get embedding dimension dynamically (each embedder implements a sync-safe method)
            dimension = embedder.get_dimension()

            # Create vector store
            vector_store = cls.create_vector_store(
                provider=settings.VECTOR_STORE_PROVIDER,
                dimension=dimension,
                qdrant_url=settings.VECTOR_QDRANT_URL,
                qdrant_api_key=settings.VECTOR_QDRANT_API_KEY,
                qdrant_collection=settings.VECTOR_QDRANT_COLLECTION,
            )

            # Create chunker
            chunker = cls.create_chunker(
                strategy=settings.VECTOR_CHUNKING_STRATEGY,
                chunk_size=settings.VECTOR_CHUNK_SIZE,
                chunk_overlap=settings.VECTOR_CHUNK_OVERLAP,
                respect_headers=settings.VECTOR_RESPECT_HEADERS,
            )

            # Default index path if not provided
            if index_path is None:
                index_path = Path("data/vector_index")

            # Create manager
            manager = VectorSearchManager(
                embedder=embedder,
                vector_store=vector_store,
                chunker=chunker,
                kb_root_path=None,  # MCP doesn't need file system access
                index_path=index_path,
            )

            logger.info("✓ Vector search manager created successfully")
            return manager

        except ImportError as e:
            logger.error(f"Failed to initialize vector search due to missing dependency: {e}")
            logger.info("Install vector search dependencies: " "pip install -e '.[vector-search]'")
            return None

        except Exception as e:
            logger.error(f"Failed to initialize vector search: {e}", exc_info=True)
            return None
