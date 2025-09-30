"""
Base Agent
Abstract base class for all agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseAgent(ABC):
    """Abstract base class for content processing agents"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
    
    @abstractmethod
    async def process(self, content: Dict) -> Dict:
        """
        Process content and return structured output
        
        Args:
            content: Content dictionary with text, urls, etc.
        
        Returns:
            Processed content dictionary
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