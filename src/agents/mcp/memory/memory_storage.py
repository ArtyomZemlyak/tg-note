"""
Legacy Memory Storage Wrapper

This module provides backward compatibility by wrapping the new storage implementations.
Uses the factory pattern to create the appropriate storage based on configuration.

For new code, prefer using the factory directly:
    from src.agents.mcp.memory import MemoryStorageFactory
    storage = MemoryStorageFactory.create("json", data_dir)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .memory_base import BaseMemoryStorage
from .memory_factory import MemoryStorageFactory


class MemoryStorage(BaseMemoryStorage):
    """
    Legacy memory storage wrapper for backward compatibility
    
    This class maintains the same interface as the original MemoryStorage
    but delegates to the appropriate storage implementation based on configuration.
    
    By default, uses JsonMemoryStorage for backward compatibility.
    Can be configured to use VectorBasedMemoryStorage via environment or settings.
    
    Usage (legacy code continues to work):
        storage = MemoryStorage(data_dir)
        storage.store(content="Hello", category="test")
        results = storage.retrieve(query="Hello")
    
    Note: For new code, prefer using the factory directly for more control:
        from src.agents.mcp.memory import MemoryStorageFactory
        storage = MemoryStorageFactory.create("vector", data_dir, model_name="...")
    """
    
    def __init__(
        self,
        data_dir: Path,
        storage_type: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """
        Initialize memory storage
        
        Args:
            data_dir: Directory for storing memory files
            storage_type: Type of storage ("json" or "vector"). 
                         If None, tries to read from environment/settings.
            model_name: Model name for vector-based storage. 
                       If None, tries to read from settings.
        """
        # Don't call super().__init__ because we delegate to another storage
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine storage type
        if storage_type is None:
            storage_type = self._get_storage_type_from_config()
        
        # Determine model name for vector-based storage
        if model_name is None and storage_type == "vector":
            model_name = self._get_model_name_from_config()
        
        # Create the actual storage implementation
        try:
            self._storage = MemoryStorageFactory.create(
                storage_type=storage_type,
                data_dir=data_dir,
                model_name=model_name
            )
            logger.info(
                f"[MemoryStorage] Initialized with '{storage_type}' storage at {data_dir}"
            )
        except Exception as e:
            logger.warning(
                f"[MemoryStorage] Failed to create '{storage_type}' storage: {e}. "
                f"Falling back to 'json' storage."
            )
            # Fallback to json storage
            self._storage = MemoryStorageFactory.create(
                storage_type="json",
                data_dir=data_dir
            )
    
    def _get_storage_type_from_config(self) -> str:
        """
        Get storage type from configuration
        
        Priority:
        1. Environment variable MEM_AGENT_STORAGE_TYPE
        2. Settings module (if available)
        3. Default to "json"
        
        Returns:
            Storage type name
        """
        import os
        
        # Try environment variable first
        storage_type = os.getenv("MEM_AGENT_STORAGE_TYPE")
        if storage_type:
            return storage_type.lower()
        
        # Try settings module
        try:
            from config.settings import settings
            return settings.MEM_AGENT_STORAGE_TYPE.lower()
        except (ImportError, AttributeError):
            pass
        
        # Default to json
        return "json"
    
    def _get_model_name_from_config(self) -> str:
        """
        Get model name from configuration
        
        Priority:
        1. Environment variable MEM_AGENT_MODEL
        2. Settings module (if available)
        3. Default to "BAAI/bge-m3"
        
        Returns:
            Model name
        """
        import os
        
        # Try environment variable first
        model_name = os.getenv("MEM_AGENT_MODEL")
        if model_name:
            return model_name
        
        # Try settings module
        try:
            from config.settings import settings
            return settings.MEM_AGENT_MODEL
        except (ImportError, AttributeError):
            pass
        
        # Default model
        return "BAAI/bge-m3"
    
    # Delegate all methods to the underlying storage implementation
    
    def store(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Store information in memory"""
        return self._storage.store(content, category, metadata, tags)
    
    def retrieve(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Retrieve information from memory"""
        return self._storage.retrieve(query, category, tags, limit)
    
    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search memories"""
        return self._storage.search(query, limit)
    
    def list_all(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """List all memories"""
        return self._storage.list_all(limit)
    
    def list_categories(self) -> Dict[str, Any]:
        """List all categories"""
        return self._storage.list_categories()
    
    def delete(self, memory_id: int) -> Dict[str, Any]:
        """Delete a memory by ID"""
        return self._storage.delete(memory_id)
    
    def clear(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Clear memories"""
        return self._storage.clear(category)

    # Compatibility: expose in-memory list if underlying storage has it (e.g., JsonMemoryStorage)
    @property
    def memories(self):
        """Provide direct access to underlying storage's memories for legacy tests."""
        return getattr(self._storage, "memories", [])
