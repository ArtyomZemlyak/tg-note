"""
JSON-based Memory Storage Implementation

Simple file-based storage using JSON format.
Uses substring search for queries.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .memory_base import BaseMemoryStorage


class JsonMemoryStorage(BaseMemoryStorage):
    """
    JSON file-based memory storage implementation

    Features:
    - Simple file-based JSON storage
    - Substring search for queries
    - Category-based organization
    - Metadata and tags support
    - Fast and lightweight

    Best for:
    - Small to medium memory sizes
    - Simple search requirements
    - No ML dependencies needed
    """

    def __init__(self, data_dir: Path):
        """
        Initialize JSON memory storage

        Args:
            data_dir: Directory for storing memory files
        """
        super().__init__(data_dir)
        self.memory_file = self.data_dir / "memory.json"

        # Load existing memory
        self.memories: List[Dict[str, Any]] = []
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    self.memories = json.load(f)
                logger.info(
                    f"[JsonMemoryStorage] Loaded {len(self.memories)} memories from {self.memory_file}"
                )
            except Exception as e:
                logger.error(f"[JsonMemoryStorage] Failed to load memories: {e}")

    def _save(self) -> None:
        """Save memories to file"""
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[JsonMemoryStorage] Failed to save memories: {e}")

    def store(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Store information in memory

        Args:
            content: Content to store
            category: Category for organization
            metadata: Additional metadata
            tags: Optional tags for categorization

        Returns:
            Result with memory ID
        """
        memory_id = len(self.memories) + 1

        memory = self._create_memory_entry(
            memory_id=memory_id,
            content=content,
            category=category,
            metadata=metadata or {},
            tags=tags or [],
        )

        self.memories.append(memory)
        self._save()

        logger.info(f"[JsonMemoryStorage] Stored memory #{memory_id} in category '{category}'")

        return {
            "success": True,
            "memory_id": memory_id,
            "message": f"Memory stored successfully (ID: {memory_id})",
        }

    def retrieve(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Retrieve information from memory

        Uses simple substring search for queries.

        Args:
            query: Search query (substring match)
            category: Filter by category
            tags: Filter by tags
            limit: Maximum number of results

        Returns:
            List of matching memories
        """
        results = self.memories.copy()

        # Filter by category
        if category:
            results = [m for m in results if m.get("category") == category]

        # Filter by tags
        if tags:
            results = [m for m in results if any(tag in m.get("tags", []) for tag in tags)]

        # Filter by query (simple substring search)
        if query:
            query_lower = query.lower()
            results = [
                m
                for m in results
                if query_lower in m.get("content", "").lower()
                or query_lower in m.get("category", "").lower()
            ]

        # Limit results
        results = results[-limit:]  # Get last N results

        logger.info(
            f"[JsonMemoryStorage] Retrieved {len(results)} memories "
            f"(query='{query}', category='{category}', tags={tags})"
        )

        return {"success": True, "count": len(results), "memories": results}

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search memories (alias for retrieve with query)

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            Search results
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

        return {"success": True, "count": len(results), "memories": results}

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
                {"name": cat, "count": count} for cat, count in sorted(categories.items())
            ],
        }

    def delete(self, memory_id: int) -> Dict[str, Any]:
        """
        Delete a memory by ID

        Args:
            memory_id: ID of memory to delete

        Returns:
            Result of deletion
        """
        original_count = len(self.memories)
        self.memories = [m for m in self.memories if m.get("id") != memory_id]

        if len(self.memories) < original_count:
            self._save()
            logger.info(f"[JsonMemoryStorage] Deleted memory #{memory_id}")
            return {"success": True, "message": f"Memory {memory_id} deleted successfully"}
        else:
            return {"success": False, "error": f"Memory {memory_id} not found"}

    def clear(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear memories (all or by category)

        Args:
            category: Optional category to clear (clears all if None)

        Returns:
            Result of clearing
        """
        original_count = len(self.memories)

        if category:
            self.memories = [m for m in self.memories if m.get("category") != category]
            message = (
                f"Cleared {original_count - len(self.memories)} memories from category '{category}'"
            )
        else:
            self.memories = []
            message = f"Cleared all {original_count} memories"

        self._save()
        logger.info(f"[JsonMemoryStorage] {message}")

        return {
            "success": True,
            "message": message,
            "deleted_count": original_count - len(self.memories),
        }
