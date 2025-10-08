"""
Base Memory Storage Interface

This module defines the abstract base class for all memory storage implementations,
following SOLID principles (Interface Segregation and Dependency Inversion).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaseMemoryStorage(ABC):
    """
    Abstract base class for memory storage implementations
    
    This interface defines the contract that all memory storage implementations must follow.
    Following SOLID principles:
    - Single Responsibility: Each implementation handles only its storage mechanism
    - Open/Closed: New storage types can be added without modifying existing code
    - Liskov Substitution: All implementations can be used interchangeably
    - Interface Segregation: Minimal interface with only necessary methods
    - Dependency Inversion: Clients depend on abstraction, not concrete implementations
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize memory storage
        
        Args:
            data_dir: Directory for storing memory data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def store(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Store information in memory
        
        Args:
            content: Content to store
            category: Category for organization
            metadata: Additional metadata
            tags: Optional tags for categorization
            
        Returns:
            Result with memory ID and success status
        """
        pass
    
    @abstractmethod
    def retrieve(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieve information from memory
        
        Args:
            query: Search query (implementation-specific behavior)
            category: Filter by category
            tags: Filter by tags
            limit: Maximum number of results
            
        Returns:
            Dict with success status and list of matching memories
        """
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search memories (convenience method)
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Search results
        """
        pass
    
    @abstractmethod
    def list_all(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        List all memories
        
        Args:
            limit: Optional limit on number of results
            
        Returns:
            All memories (up to limit)
        """
        pass
    
    @abstractmethod
    def list_categories(self) -> Dict[str, Any]:
        """
        List all available categories
        
        Returns:
            List of categories with counts
        """
        pass
    
    @abstractmethod
    def delete(self, memory_id: int) -> Dict[str, Any]:
        """
        Delete a memory by ID
        
        Args:
            memory_id: ID of memory to delete
            
        Returns:
            Result of deletion
        """
        pass
    
    @abstractmethod
    def clear(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear memories (all or by category)
        
        Args:
            category: Optional category to clear (clears all if None)
            
        Returns:
            Result of clearing
        """
        pass
    
    def _create_memory_entry(
        self,
        memory_id: int,
        content: str,
        category: str,
        metadata: Dict,
        tags: List[str]
    ) -> Dict[str, Any]:
        """
        Create a standardized memory entry
        
        Helper method to ensure consistent memory entry format across implementations.
        
        Args:
            memory_id: Unique memory ID
            content: Memory content
            category: Category name
            metadata: Additional metadata
            tags: Tags list
            
        Returns:
            Standardized memory entry dict
        """
        return {
            "id": memory_id,
            "content": content,
            "category": category,
            "metadata": metadata,
            "tags": tags,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
