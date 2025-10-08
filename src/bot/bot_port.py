"""
BotPort Interface
Abstract interface for bot messaging operations (Clean Architecture)
This interface decouples services from the specific transport implementation
"""

from abc import ABC, abstractmethod
from typing import Optional, Any


class BotPort(ABC):
    """
    Abstract interface for bot messaging operations
    
    This interface defines the contract for sending and editing messages,
    allowing services to be independent of the specific transport (Telegram, Slack, etc.)
    """
    
    @abstractmethod
    async def send_message(
        self,
        chat_id: int,
        text: str,
        **kwargs
    ) -> Any:
        """
        Send a message to a chat
        
        Args:
            chat_id: Chat identifier
            text: Message text
            **kwargs: Additional transport-specific parameters
            
        Returns:
            Message object (transport-specific)
        """
        pass
    
    @abstractmethod
    async def reply_to(
        self,
        message: Any,
        text: str,
        **kwargs
    ) -> Any:
        """
        Reply to a message
        
        Args:
            message: Original message to reply to
            text: Reply text
            **kwargs: Additional transport-specific parameters
            
        Returns:
            Message object (transport-specific)
        """
        pass
    
    @abstractmethod
    async def edit_message_text(
        self,
        text: str,
        chat_id: int,
        message_id: int,
        **kwargs
    ) -> Any:
        """
        Edit a message text
        
        Args:
            text: New message text
            chat_id: Chat identifier
            message_id: Message identifier to edit
            **kwargs: Additional transport-specific parameters
            
        Returns:
            Updated message object (transport-specific)
        """
        pass
    
    @abstractmethod
    async def download_file(
        self,
        file_path: str
    ) -> bytes:
        """
        Download a file by its file path
        
        Args:
            file_path: File path from the transport service
            
        Returns:
            File content as bytes
        """
        pass
    
    @abstractmethod
    async def get_file(
        self,
        file_id: str
    ):
        """
        Get file info by file ID
        
        Args:
            file_id: File identifier
            
        Returns:
            File object with path information
        """
        pass
    
    @abstractmethod
    async def get_me(self):
        """
        Get bot information
        
        Returns:
            Bot information object
        """
        pass
