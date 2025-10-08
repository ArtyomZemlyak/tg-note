"""
Vector-based Memory Storage Implementation

Uses embedding models for semantic search and retrieval via vector similarity.
Combines JSON storage with vector embeddings for semantic similarity search.
"""

import json
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .memory_base import BaseMemoryStorage


class VectorBasedMemoryStorage(BaseMemoryStorage):
    """
    Vector-based memory storage with semantic search
    
    Features:
    - Semantic search using embeddings from sentence-transformers models
    - Vector similarity search with cosine similarity
    - Fallback to JSON storage for data persistence
    - Category and tag filtering
    - Hybrid search (semantic + keyword)
    
    Best for:
    - Large memory sizes
    - Complex search requirements
    - Semantic understanding needed
    - When you want AI-powered memory retrieval
    
    Note:
    Requires additional dependencies: transformers, torch, sentence-transformers
    """
    
    def __init__(self, data_dir: Path, model_name: str = "BAAI/bge-m3"):
        """
        Initialize model-based memory storage
        
        Args:
            data_dir: Directory for storing memory files
            model_name: HuggingFace model name for embeddings
        """
        super().__init__(data_dir)
        self.model_name = model_name
        self.memory_file = self.data_dir / "memory.json"
        self.embeddings_file = self.data_dir / "embeddings.npy"
        
        # Initialize model and embeddings
        self._model = None
        self._embeddings: Optional[np.ndarray] = None
        self.memories: List[Dict[str, Any]] = []
        
        # Load existing data
        self._load_data()
        
        logger.info(
            f"[VectorBasedMemoryStorage] Initialized with model '{model_name}' "
            f"({len(self.memories)} memories loaded)"
        )
    
    def _get_model(self):
        """
        Lazy load the embedding model
        
        Returns:
            Loaded model instance
        """
        if self._model is None:
            try:
                # Try to use sentence-transformers (most compatible)
                from sentence_transformers import SentenceTransformer
                
                logger.info(f"[VectorBasedMemoryStorage] Loading model '{self.model_name}'...")
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"[VectorBasedMemoryStorage] Model loaded successfully")
                
            except ImportError:
                logger.error(
                    "[VectorBasedMemoryStorage] sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
                raise
            except Exception as e:
                logger.error(f"[VectorBasedMemoryStorage] Failed to load model: {e}")
                # Try to fallback to a default model
                try:
                    from sentence_transformers import SentenceTransformer
                    logger.warning(
                        f"[VectorBasedMemoryStorage] Falling back to default model 'all-MiniLM-L6-v2'"
                    )
                    self._model = SentenceTransformer('all-MiniLM-L6-v2')
                except Exception as fallback_error:
                    logger.error(
                        f"[VectorBasedMemoryStorage] Fallback model also failed: {fallback_error}"
                    )
                    raise
        
        return self._model
    
    def _load_data(self) -> None:
        """Load memories and embeddings from files"""
        # Load memories from JSON
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
                logger.debug(f"[VectorBasedMemoryStorage] Loaded {len(self.memories)} memories")
            except Exception as e:
                logger.error(f"[VectorBasedMemoryStorage] Failed to load memories: {e}")
                self.memories = []
        
        # Load embeddings from numpy file
        if self.embeddings_file.exists():
            try:
                self._embeddings = np.load(self.embeddings_file)
                logger.debug(
                    f"[VectorBasedMemoryStorage] Loaded embeddings with shape {self._embeddings.shape}"
                )
            except Exception as e:
                logger.error(f"[VectorBasedMemoryStorage] Failed to load embeddings: {e}")
                self._embeddings = None
    
    def _save_data(self) -> None:
        """Save memories and embeddings to files"""
        # Save memories to JSON
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[VectorBasedMemoryStorage] Failed to save memories: {e}")
        
        # Save embeddings to numpy file
        if self._embeddings is not None:
            try:
                np.save(self.embeddings_file, self._embeddings)
            except Exception as e:
                logger.error(f"[VectorBasedMemoryStorage] Failed to save embeddings: {e}")
    
    def _compute_embedding(self, text: str) -> np.ndarray:
        """
        Compute embedding for text using the model
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding
    
    def _compute_similarity(self, query_embedding: np.ndarray, memory_embeddings: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between query and memory embeddings
        
        Args:
            query_embedding: Query embedding vector
            memory_embeddings: Matrix of memory embeddings
            
        Returns:
            Array of similarity scores
        """
        # Normalize vectors
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        memories_norm = memory_embeddings / (np.linalg.norm(memory_embeddings, axis=1, keepdims=True) + 1e-8)
        
        # Compute cosine similarity
        similarities = np.dot(memories_norm, query_norm)
        return similarities
    
    def store(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Store information in memory with embedding
        
        Args:
            content: Content to store
            category: Category for organization
            metadata: Additional metadata
            tags: Optional tags for categorization
            
        Returns:
            Result with memory ID
        """
        memory_id = len(self.memories) + 1
        
        # Create memory entry
        memory = self._create_memory_entry(
            memory_id=memory_id,
            content=content,
            category=category,
            metadata=metadata or {},
            tags=tags or []
        )
        
        # Compute embedding for content
        try:
            embedding = self._compute_embedding(content)
            
            # Add embedding to embeddings matrix
            if self._embeddings is None:
                self._embeddings = embedding.reshape(1, -1)
            else:
                self._embeddings = np.vstack([self._embeddings, embedding])
            
            logger.debug(f"[VectorBasedMemoryStorage] Computed embedding for memory #{memory_id}")
            
        except Exception as e:
            logger.error(f"[VectorBasedMemoryStorage] Failed to compute embedding: {e}")
            # Continue without embedding (will fall back to keyword search)
        
        self.memories.append(memory)
        self._save_data()
        
        logger.info(f"[VectorBasedMemoryStorage] Stored memory #{memory_id} in category '{category}'")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": f"Memory stored successfully (ID: {memory_id})"
        }
    
    def retrieve(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieve information from memory using semantic search
        
        Uses vector similarity search when query is provided,
        otherwise returns filtered results.
        
        Args:
            query: Search query (semantic search)
            category: Filter by category
            tags: Filter by tags
            limit: Maximum number of results
            
        Returns:
            List of matching memories ranked by relevance
        """
        # Start with all memories
        candidates = list(enumerate(self.memories))
        
        # Filter by category
        if category:
            candidates = [(i, m) for i, m in candidates if m.get("category") == category]
        
        # Filter by tags
        if tags:
            candidates = [
                (i, m) for i, m in candidates
                if any(tag in m.get("tags", []) for tag in tags)
            ]
        
        # If no query, return filtered results
        if not query:
            results = [m for _, m in candidates[-limit:]]
            logger.info(
                f"[VectorBasedMemoryStorage] Retrieved {len(results)} memories "
                f"(no query, category='{category}', tags={tags})"
            )
            return {
                "success": True,
                "count": len(results),
                "memories": results
            }
        
        # Semantic search with query
        if self._embeddings is None or len(candidates) == 0:
            # No embeddings available, fall back to keyword search
            logger.warning("[VectorBasedMemoryStorage] No embeddings, falling back to keyword search")
            query_lower = query.lower()
            scored_results = [
                (i, m, 1.0 if query_lower in m.get("content", "").lower() else 0.0)
                for i, m in candidates
            ]
        else:
            try:
                # Compute query embedding
                query_embedding = self._compute_embedding(query)
                
                # Get embeddings for candidate memories
                candidate_indices = [i for i, _ in candidates]
                candidate_embeddings = self._embeddings[candidate_indices]
                
                # Compute similarities
                similarities = self._compute_similarity(query_embedding, candidate_embeddings)
                
                # Create scored results
                scored_results = [
                    (idx, mem, float(sim))
                    for (idx, mem), sim in zip(candidates, similarities)
                ]
                
                logger.debug(
                    f"[VectorBasedMemoryStorage] Computed semantic similarities "
                    f"(top score: {max(similarities):.3f})"
                )
                
            except Exception as e:
                logger.error(f"[VectorBasedMemoryStorage] Semantic search failed: {e}")
                # Fall back to keyword search
                query_lower = query.lower()
                scored_results = [
                    (i, m, 1.0 if query_lower in m.get("content", "").lower() else 0.0)
                    for i, m in candidates
                ]
        
        # Sort by score and take top results
        scored_results.sort(key=lambda x: x[2], reverse=True)
        results = [
            {**mem, "_score": score}
            for _, mem, score in scored_results[:limit]
        ]
        
        logger.info(
            f"[VectorBasedMemoryStorage] Retrieved {len(results)} memories "
            f"(query='{query}', category='{category}', tags={tags})"
        )
        
        return {
            "success": True,
            "count": len(results),
            "memories": results
        }
    
    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search memories using semantic similarity
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Search results ranked by semantic similarity
        """
        return self.retrieve(query=query, limit=limit)
    
    def list_all(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        List all memories
        
        Args:
            limit: Optional limit on number of results
            
        Returns:
            All memories (up to limit)
        """
        results = self.memories.copy()
        if limit:
            results = results[-limit:]
        
        return {
            "success": True,
            "count": len(results),
            "memories": results
        }
    
    def list_categories(self) -> Dict[str, Any]:
        """
        List all available categories
        
        Returns:
            List of categories with counts
        """
        categories: Dict[str, int] = {}
        
        for memory in self.memories:
            cat = memory.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "success": True,
            "categories": [
                {"name": cat, "count": count}
                for cat, count in sorted(categories.items())
            ]
        }
    
    def delete(self, memory_id: int) -> Dict[str, Any]:
        """
        Delete a memory by ID
        
        Also removes corresponding embedding.
        
        Args:
            memory_id: ID of memory to delete
            
        Returns:
            Result of deletion
        """
        # Find memory index
        memory_index = None
        for i, m in enumerate(self.memories):
            if m.get("id") == memory_id:
                memory_index = i
                break
        
        if memory_index is None:
            return {
                "success": False,
                "error": f"Memory {memory_id} not found"
            }
        
        # Remove memory
        self.memories.pop(memory_index)
        
        # Remove corresponding embedding
        if self._embeddings is not None and memory_index < len(self._embeddings):
            self._embeddings = np.delete(self._embeddings, memory_index, axis=0)
        
        self._save_data()
        logger.info(f"[VectorBasedMemoryStorage] Deleted memory #{memory_id}")
        
        return {
            "success": True,
            "message": f"Memory {memory_id} deleted successfully"
        }
    
    def clear(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear memories (all or by category)
        
        Also clears corresponding embeddings.
        
        Args:
            category: Optional category to clear (clears all if None)
            
        Returns:
            Result of clearing
        """
        original_count = len(self.memories)
        
        if category:
            # Find indices to keep
            indices_to_keep = [
                i for i, m in enumerate(self.memories)
                if m.get("category") != category
            ]
            
            # Update memories
            self.memories = [self.memories[i] for i in indices_to_keep]
            
            # Update embeddings
            if self._embeddings is not None:
                self._embeddings = self._embeddings[indices_to_keep]
            
            deleted_count = original_count - len(self.memories)
            message = f"Cleared {deleted_count} memories from category '{category}'"
        else:
            # Clear all
            self.memories = []
            self._embeddings = None
            message = f"Cleared all {original_count} memories"
        
        self._save_data()
        logger.info(f"[VectorBasedMemoryStorage] {message}")
        
        return {
            "success": True,
            "message": message,
            "deleted_count": original_count - len(self.memories)
        }
