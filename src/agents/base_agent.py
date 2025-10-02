"""
Base Agent
Abstract base class for all agents
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class KBStructure:
    """Knowledge Base structure definition from agent"""
    
    def __init__(
        self,
        category: str = "general",
        subcategory: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_path: Optional[str] = None
    ):
        """
        Initialize KB structure
        
        Args:
            category: Main category (e.g., "ai", "biology", "physics")
            subcategory: Optional subcategory (e.g., "machine-learning", "genetics")
            tags: Optional list of tags for the content
            custom_path: Optional custom relative path from KB root
        """
        self.category = category
        self.subcategory = subcategory
        self.tags = tags or []
        self.custom_path = custom_path
    
    def get_relative_path(self) -> str:
        """
        Get relative path for the article based on structure
        
        Returns:
            Relative path string (e.g., "topics/ai/machine-learning")
        """
        if self.custom_path:
            return self.custom_path
        
        # Ensure category is valid (not None or empty)
        category = self.category if self.category else "general"
        
        parts = ["topics", category]
        if self.subcategory:
            parts.append(self.subcategory)
        
        # Filter out None values to prevent join errors
        parts = [str(p) for p in parts if p is not None]
        
        return "/".join(parts)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "tags": self.tags,
            "custom_path": self.custom_path
        }


class BaseAgent(ABC):
    """Abstract base class for content processing agents"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
    
    @abstractmethod
    async def process(self, content: Dict) -> Dict:
        """
        Process content and return structured output with KB structure
        
        Args:
            content: Content dictionary with text, urls, etc.
        
        Returns:
            Processed content dictionary with:
            - markdown: str - formatted markdown content
            - title: str - article title
            - metadata: Dict - article metadata
            - kb_structure: KBStructure - where to save the article
        """
        pass
    
    @abstractmethod
    def validate_input(self, content: Dict) -> bool:
        """
        Validate input content
        
        Args:
            content: Content to validate
        
        Returns:
            True if valid, False otherwise
        """
        pass