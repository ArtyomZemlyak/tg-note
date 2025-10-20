"""
Vector Stores
Supports multiple vector store backends: FAISS (local), Qdrant (API)
"""

import json
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class BaseVectorStore(ABC):
    """Base class for vector stores"""

    @abstractmethod
    async def add_documents(
        self,
        embeddings: List[List[float]],
        documents: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> None:
        """
        Add documents with their embeddings to the store

        Args:
            embeddings: List of embedding vectors
            documents: List of document metadata
            ids: Optional list of document IDs
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of documents with scores
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all documents from the store"""
        pass

    @abstractmethod
    async def get_count(self) -> int:
        """Get number of documents in the store"""
        pass

    @abstractmethod
    async def save(self, path: Path) -> None:
        """Save the vector store to disk"""
        pass

    @abstractmethod
    async def load(self, path: Path) -> None:
        """Load the vector store from disk"""
        pass

    # Optional capabilities (not abstract to keep subclasses compatible)
    def supports_delete_by_filter(self) -> bool:
        """Return True if store supports deletion by metadata filter"""
        return False

    async def delete_by_filter(self, filter_dict: Dict[str, Any]) -> int:
        """Delete documents matching metadata filter. Returns number deleted if known."""
        raise NotImplementedError("delete_by_filter is not supported by this vector store")


class FAISSVectorStore(BaseVectorStore):
    """FAISS-based local vector store"""

    def __init__(self, dimension: int):
        """
        Initialize FAISS vector store

        Args:
            dimension: Embedding dimension
        """
        self.dimension = dimension
        self._index = None
        self._documents: List[Dict[str, Any]] = []
        self._ids: List[str] = []

    def _get_index(self):
        """Lazy load FAISS index"""
        if self._index is None:
            try:
                import faiss

                logger.info(f"Creating FAISS index with dimension {self.dimension}")
                # Use IndexFlatL2 for exact search (can be changed to IVF for large datasets)
                self._index = faiss.IndexFlatL2(self.dimension)
            except ImportError:
                raise ImportError(
                    "faiss not installed. "
                    "Install with: pip install faiss-cpu (or faiss-gpu for GPU support)"
                )
        return self._index

    async def add_documents(
        self,
        embeddings: List[List[float]],
        documents: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> None:
        """Add documents to FAISS index"""
        import numpy as np

        index = self._get_index()

        if len(embeddings) != len(documents):
            raise ValueError("Number of embeddings must match number of documents")

        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # Add to index
        index.add(embeddings_array)

        # Store documents and IDs
        self._documents.extend(documents)
        if ids:
            self._ids.extend(ids)
        else:
            # Generate IDs
            start_id = len(self._ids)
            self._ids.extend([f"doc_{start_id + i}" for i in range(len(documents))])

        logger.info(f"Added {len(embeddings)} documents to FAISS index")

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search FAISS index"""
        import numpy as np

        index = self._get_index()

        if index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return []

        # Convert query to numpy array
        query_array = np.array([query_embedding], dtype=np.float32)

        # Search
        distances, indices = index.search(query_array, min(top_k, index.ntotal))

        # Prepare results
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0 or idx >= len(self._documents):
                continue

            doc = self._documents[idx].copy()
            doc["score"] = float(1 / (1 + distance))  # Convert distance to similarity score
            doc["_distance"] = float(distance)
            doc["_id"] = self._ids[idx]

            # Apply filter if provided
            if filter_dict:
                match = all(doc.get(key) == value for key, value in filter_dict.items())
                if not match:
                    continue

            results.append(doc)

        logger.debug(f"Found {len(results)} results in FAISS index")
        return results

    async def clear(self) -> None:
        """Clear FAISS index"""
        self._index = None
        self._documents = []
        self._ids = []
        logger.info("Cleared FAISS index")

    def supports_delete_by_filter(self) -> bool:
        """FAISS (IndexFlatL2) does not support in-place deletions; requires rebuild"""
        return False

    async def delete_by_filter(self, filter_dict: Dict[str, Any]) -> int:
        """Not supported for FAISS IndexFlatL2. Use full reindex instead."""
        raise NotImplementedError(
            "FAISS store does not support delete_by_filter; perform full reindex"
        )

    async def get_count(self) -> int:
        """Get number of documents"""
        if self._index is None:
            return 0
        return self._index.ntotal

    async def save(self, path: Path) -> None:
        """Save FAISS index and metadata"""
        import faiss

        path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        if self._index is not None:
            index_path = path / "index.faiss"
            faiss.write_index(self._index, str(index_path))
            logger.info(f"Saved FAISS index to {index_path}")

        # Save documents and IDs
        metadata = {"documents": self._documents, "ids": self._ids, "dimension": self.dimension}
        metadata_path = path / "metadata.pkl"
        with open(metadata_path, "wb") as f:
            pickle.dump(metadata, f)
        logger.info(f"Saved metadata to {metadata_path}")

    async def load(self, path: Path) -> None:
        """Load FAISS index and metadata"""
        import faiss

        # Load FAISS index
        index_path = path / "index.faiss"
        if index_path.exists():
            self._index = faiss.read_index(str(index_path))
            logger.info(f"Loaded FAISS index from {index_path}")

        # Load documents and IDs
        metadata_path = path / "metadata.pkl"
        if metadata_path.exists():
            with open(metadata_path, "rb") as f:
                metadata = pickle.load(f)
            self._documents = metadata["documents"]
            self._ids = metadata["ids"]
            self.dimension = metadata["dimension"]
            logger.info(f"Loaded metadata from {metadata_path}")


class QdrantVectorStore(BaseVectorStore):
    """Qdrant API-based vector store"""

    def __init__(
        self,
        collection_name: str,
        dimension: int,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
    ):
        """
        Initialize Qdrant vector store

        Args:
            collection_name: Name of the Qdrant collection
            dimension: Embedding dimension
            url: Qdrant API URL
            api_key: Optional API key for authentication
        """
        self.collection_name = collection_name
        self.dimension = dimension
        self.url = url
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        """Lazy load Qdrant client"""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import Distance, VectorParams

                logger.info(f"Connecting to Qdrant at {self.url}")
                self._client = QdrantClient(url=self.url, api_key=self.api_key)

                # Create collection if it doesn't exist
                try:
                    info = self._client.get_collection(self.collection_name)
                    # Validate collection vector dimension; recreate if mismatched
                    current_size = None
                    try:
                        # Single vector configuration
                        current_size = info.config.params.vectors.size  # type: ignore[attr-defined]
                    except Exception:
                        try:
                            # Named vectors configuration
                            vectors_cfg = info.config.params.vectors  # type: ignore[attr-defined]
                            if isinstance(vectors_cfg, dict) and vectors_cfg:
                                # Take the first vector's size
                                current_size = next(iter(vectors_cfg.values())).size
                        except Exception:
                            current_size = None

                    if current_size is not None and int(current_size) != int(self.dimension):
                        logger.warning(
                            "Qdrant collection exists but dimension differs "
                            f"(have {current_size}, need {self.dimension}). Recreating collection."
                        )
                        try:
                            self._client.delete_collection(self.collection_name)
                        except Exception as del_e:
                            logger.warning(f"Failed to delete existing collection: {del_e}")
                        self._client.create_collection(
                            collection_name=self.collection_name,
                            vectors_config=VectorParams(
                                size=self.dimension, distance=Distance.COSINE
                            ),
                        )
                        logger.info(
                            f"Recreated collection {self.collection_name} with dimension {self.dimension}"
                        )
                    else:
                        logger.info(f"Using existing collection: {self.collection_name}")
                except Exception:
                    logger.info(f"Creating collection: {self.collection_name}")
                    self._client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
                    )

            except ImportError:
                raise ImportError(
                    "qdrant-client not installed. " "Install with: pip install qdrant-client"
                )

        return self._client

    async def add_documents(
        self,
        embeddings: List[List[float]],
        documents: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> None:
        """Add documents to Qdrant"""
        import uuid

        from qdrant_client.models import PointStruct

        client = self._get_client()

        if len(embeddings) != len(documents):
            raise ValueError("Number of embeddings must match number of documents")

        # Prepare points
        points = []
        for i, (embedding, doc) in enumerate(zip(embeddings, documents)):
            point_id = ids[i] if ids else str(uuid.uuid4())
            points.append(PointStruct(id=point_id, vector=embedding, payload=doc))

        # Upload to Qdrant
        client.upsert(collection_name=self.collection_name, points=points)

        logger.info(f"Added {len(points)} documents to Qdrant collection: {self.collection_name}")

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search Qdrant"""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = self._get_client()

        # Build filter
        query_filter = None
        if filter_dict:
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filter_dict.items()
            ]
            query_filter = Filter(must=conditions)

        # Search
        search_results = client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter,
        )

        # Format results
        results = []
        for hit in search_results:
            doc = hit.payload.copy()
            doc["score"] = float(hit.score)
            doc["_id"] = str(hit.id)
            results.append(doc)

        logger.debug(f"Found {len(results)} results in Qdrant")
        return results

    async def clear(self) -> None:
        """Clear Qdrant collection"""
        client = self._get_client()

        try:
            # Delete and recreate collection
            from qdrant_client.models import Distance, VectorParams

            client.delete_collection(self.collection_name)
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
            )
            logger.info(f"Cleared Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error clearing Qdrant collection: {e}")
            raise

    async def get_count(self) -> int:
        """Get number of documents in collection"""
        client = self._get_client()

        try:
            collection_info = client.get_collection(self.collection_name)
            return int(collection_info.points_count)
        except Exception as e:
            logger.error(f"Error getting count from Qdrant: {e}")
            return 0

    async def save(self, path: Path) -> None:
        """Save not needed for Qdrant (persists on server)"""
        logger.info("Qdrant collections are persisted on the server, no local save needed")

    async def load(self, path: Path) -> None:
        """Load not needed for Qdrant (persists on server)"""
        logger.info("Qdrant collections are loaded from the server automatically")

    def supports_delete_by_filter(self) -> bool:
        return True

    async def delete_by_filter(self, filter_dict: Dict[str, Any]) -> int:
        """Delete points in Qdrant matching payload filter"""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = self._get_client()

        # Build conditions from exact-match payload fields
        conditions = [
            FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filter_dict.items()
        ]
        q_filter = Filter(must=conditions) if conditions else None

        try:
            # Delete by filter; Qdrant does not return count synchronously
            client.delete(collection_name=self.collection_name, points_selector=q_filter)
            logger.info(
                f"Deleted documents from Qdrant where {filter_dict} in collection {self.collection_name}"
            )
            return -1  # unknown count
        except Exception as e:
            logger.error(f"Error deleting by filter in Qdrant: {e}")
            raise
