"""
Vector Search Manager
Manages indexing and searching of documents using configurable embedding models and vector stores
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .chunking import DocumentChunk, DocumentChunker
from .embeddings import BaseEmbedder
from .vector_stores import BaseVectorStore


class VectorSearchManager:
    """Manages vector search operations"""

    def __init__(
        self,
        embedder: BaseEmbedder,
        vector_store: BaseVectorStore,
        chunker: DocumentChunker,
        kb_root_path: Optional[Path] = None,
        index_path: Optional[Path] = None,
        kb_id: Optional[str] = None,
    ):
        """
        Initialize vector search manager

        Args:
            embedder: Embedding model
            vector_store: Vector store
            chunker: Document chunker
            kb_root_path: Knowledge base root path (optional for MCP usage)
            index_path: Path to save/load index
            kb_id: Knowledge base ID for isolation (optional)
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.chunker = chunker
        self.kb_root_path = Path(kb_root_path) if kb_root_path else None
        self.kb_id = kb_id or "default"
        self.index_path = index_path or (
            self.kb_root_path / ".vector_index"
            if self.kb_root_path
            else Path(f"data/vector_index/{self.kb_id}")
        )

        # Track indexed documents
        self._indexed_documents: Dict[str, str] = {}  # document_id -> content_hash
        self._config_hash: Optional[str] = None

    def _get_config_hash(self) -> str:
        """Get hash of current configuration"""
        # Include embedding dimension so changes trigger reindex even if model name stays same
        try:
            embedder_dimension = self.embedder.get_dimension()
        except Exception:
            # If dimension cannot be determined synchronously, omit it
            embedder_dimension = None

        config = {
            "embedder": self.embedder.get_model_hash(),
            "embedding_dimension": embedder_dimension,
            "vector_store": self.vector_store.__class__.__name__,
            "chunking_strategy": self.chunker.strategy.value,
            "chunk_size": self.chunker.chunk_size,
            "chunk_overlap": self.chunker.chunk_overlap,
            "respect_headers": self.chunker.respect_headers,
        }
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()

    def _get_content_hash(self, content: str) -> str:
        """Get hash of content string"""
        return hashlib.md5(content.encode()).hexdigest()

    async def _save_metadata(self) -> None:
        """Save indexing metadata"""
        metadata = {
            "kb_id": self.kb_id,
            "config_hash": self._config_hash,
            "indexed_documents": self._indexed_documents,
        }

        metadata_path = self.index_path / "metadata.json"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.debug(f"Saved metadata for KB '{self.kb_id}' to {metadata_path}")

    async def _load_metadata(self) -> bool:
        """
        Load indexing metadata

        Returns:
            True if metadata loaded successfully and config matches
        """
        metadata_path = self.index_path / "metadata.json"

        if not metadata_path.exists():
            logger.info(f"No existing index metadata found for KB '{self.kb_id}'")
            return False

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            # Check KB ID match
            saved_kb_id = metadata.get("kb_id", "default")
            if saved_kb_id != self.kb_id:
                logger.warning(
                    f"KB ID mismatch: expected '{self.kb_id}', found '{saved_kb_id}'. "
                    "Full re-indexing required."
                )
                return False

            saved_config_hash = metadata.get("config_hash")
            current_config_hash = self._get_config_hash()

            if saved_config_hash != current_config_hash:
                logger.warning(
                    "Configuration changed since last indexing. " "Full re-indexing required."
                )
                return False

            self._config_hash = saved_config_hash
            self._indexed_documents = metadata.get("indexed_documents", {})

            logger.info(
                f"Loaded metadata for KB '{self.kb_id}': {len(self._indexed_documents)} indexed documents"
            )
            return True

        except Exception as e:
            logger.error(f"Error loading metadata for KB '{self.kb_id}': {e}")
            return False

    async def initialize(self) -> None:
        """Initialize the vector search manager and load existing index"""
        self._config_hash = self._get_config_hash()

        # Try to load existing index
        if await self._load_metadata():
            try:
                await self.vector_store.load(self.index_path)
                logger.info("Vector store loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load vector store: {e}. Will re-index.")
                await self.vector_store.clear()
                self._indexed_documents = {}
        else:
            # Configuration changed or no index exists
            logger.info("Initializing new vector index")
            await self.vector_store.clear()
            self._indexed_documents = {}

    async def search(
        self, query: str, top_k: int = 5, filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query

        Args:
            query: Search query
            top_k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of matching documents with scores
        """
        logger.debug(f"Searching for: {query}")

        # Embed query
        query_embedding = await self.embedder.embed_query(query)

        # Search vector store
        results = await self.vector_store.search(
            query_embedding=query_embedding, top_k=top_k, filter_dict=filter_dict
        )

        logger.info(f"Found {len(results)} results for query")
        return results

    async def clear_index(self) -> None:
        """Clear the vector index"""
        logger.info("Clearing vector index")
        await self.vector_store.clear()
        self._indexed_documents = {}
        await self._save_metadata()

    async def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        count = await self.vector_store.get_count()

        return {
            "indexed_documents": len(self._indexed_documents),
            "total_chunks": count,
            "config_hash": self._config_hash,
            "embedder": self.embedder.__class__.__name__,
            "embedder_model": self.embedder.model_name,
            "vector_store": self.vector_store.__class__.__name__,
            "chunking_strategy": self.chunker.strategy.value,
            "chunk_size": self.chunker.chunk_size,
        }

    async def add_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add or update documents to vector index

        AICODE-NOTE: SOLID - Dependency Inversion Principle
        Works with DATA, not FILES. Receives document content from caller (BOT),
        not file paths. This allows MCP HUB to run without file system access.

        Args:
            documents: List of documents with structure:
                - id (str): Unique document identifier
                - content (str): Document text content
                - metadata (dict): Additional metadata (optional)

        Returns:
            Operation statistics
        """
        logger.info(f"Adding/updating {len(documents)} documents")

        stats = {
            "documents_processed": 0,
            "chunks_created": 0,
            "errors": [],
        }

        all_chunks: List[DocumentChunk] = []

        for doc in documents:
            try:
                doc_id = doc.get("id")
                content = doc.get("content")
                base_metadata = doc.get("metadata", {})

                if not doc_id or not content:
                    error_msg = f"Invalid document: missing id or content"
                    logger.warning(error_msg)
                    stats["errors"].append(error_msg)
                    continue

                # Compute hash
                content_hash = self._get_content_hash(content)

                # Merge metadata
                metadata = {
                    "document_id": doc_id,
                    "kb_id": self.kb_id,
                    **base_metadata,
                }

                # Chunk document
                chunks = self.chunker.chunk_document(
                    text=content, metadata=metadata, source_file=doc_id
                )

                all_chunks.extend(chunks)
                self._indexed_documents[doc_id] = content_hash
                stats["documents_processed"] += 1
                stats["chunks_created"] += len(chunks)

                logger.debug(f"Processed {doc_id}: {len(chunks)} chunks")

            except Exception as e:
                error_msg = f"Error processing document {doc.get('id', 'unknown')}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        # Embed and store chunks
        if all_chunks:
            try:
                logger.info(f"Embedding {len(all_chunks)} chunks")

                # Extract texts
                texts = [chunk.text for chunk in all_chunks]

                # Get embeddings
                embeddings = await self.embedder.embed_texts(texts)

                # Prepare documents for storage
                vector_documents = []
                for chunk in all_chunks:
                    doc = chunk.metadata.copy()
                    doc["text"] = chunk.text
                    doc["chunk_index"] = chunk.chunk_index
                    vector_documents.append(doc)

                # Add to vector store
                await self.vector_store.add_documents(
                    embeddings=embeddings, documents=vector_documents
                )

                logger.info(f"Successfully added {len(all_chunks)} chunks to vector store")

                # Save index and metadata
                await self.vector_store.save(self.index_path)
                await self._save_metadata()

            except Exception as e:
                error_msg = f"Error embedding/storing chunks: {e}"
                logger.error(error_msg, exc_info=True)
                stats["errors"].append(error_msg)

        logger.info(
            f"Add documents complete: {stats['documents_processed']} documents, "
            f"{stats['chunks_created']} chunks, {len(stats['errors'])} errors"
        )

        return stats

    async def delete_documents(self, document_ids: List[str]) -> Dict[str, Any]:
        """
        Delete documents from vector index

        AICODE-NOTE: Works with document IDs, not file paths

        Args:
            document_ids: List of document identifiers

        Returns:
            Operation statistics
        """
        logger.info(f"Deleting {len(document_ids)} documents")

        stats = {
            "documents_deleted": 0,
            "errors": [],
        }

        # Check if vector store supports deletions
        supports_delete = (
            hasattr(self.vector_store, "supports_delete_by_filter")
            and self.vector_store.supports_delete_by_filter()
        )

        if not supports_delete:
            error_msg = "Vector store does not support deletions. Full reindex required."
            logger.warning(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "documents_deleted": 0,
                "errors": [error_msg],
            }

        for doc_id in document_ids:
            try:
                # Delete from vector store by document_id
                await self.vector_store.delete_by_filter({"document_id": doc_id})

                # Remove from metadata
                if doc_id in self._indexed_documents:
                    del self._indexed_documents[doc_id]

                stats["documents_deleted"] += 1
                logger.debug(f"Deleted vectors for: {doc_id}")

            except Exception as e:
                error_msg = f"Error deleting {doc_id}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        # Save updated metadata
        if stats["documents_deleted"] > 0:
            await self._save_metadata()
            await self.vector_store.save(self.index_path)

        logger.info(
            f"Delete documents complete: {stats['documents_deleted']} documents deleted, "
            f"{len(stats['errors'])} errors"
        )

        return stats

    async def update_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update documents in vector index

        AICODE-NOTE: Implemented as delete + add for simplicity

        Args:
            documents: List of documents (same structure as add_documents)

        Returns:
            Operation statistics
        """
        logger.info(f"Updating {len(documents)} documents")

        # Extract document IDs
        document_ids = [doc.get("id") for doc in documents if doc.get("id")]

        # First, delete existing documents
        delete_stats = await self.delete_documents(document_ids)

        # Then add new versions
        add_stats = await self.add_documents(documents)

        # Combine stats
        stats = {
            "documents_updated": add_stats["documents_processed"],
            "documents_deleted": delete_stats.get("documents_deleted", 0),
            "chunks_created": add_stats["chunks_created"],
            "errors": delete_stats.get("errors", []) + add_stats.get("errors", []),
        }

        logger.info(
            f"Update documents complete: {stats['documents_updated']} documents updated, "
            f"{stats['chunks_created']} chunks created, {len(stats['errors'])} errors"
        )

        return stats

        logger.info(
            f"Update documents complete: {stats['files_updated']} files updated, "
            f"{stats['chunks_created']} chunks created, {len(stats['errors'])} errors"
        )

        return stats
