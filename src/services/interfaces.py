"""
Service Interfaces
Defines abstract interfaces for services (Dependency Inversion Principle)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.bot.dto import IncomingMessageDTO
from src.processor.message_aggregator import MessageGroup


class IUserContextManager(ABC):
    """Interface for managing user-specific contexts"""

    @abstractmethod
    async def get_or_create_aggregator(self, user_id: int):
        """Get or create message aggregator for a user (async, thread-safe)"""
        pass

    @abstractmethod
    async def get_or_create_agent(self, user_id: int):
        """Get or create agent for a user (async, thread-safe)"""
        pass

    @abstractmethod
    def get_user_mode(self, user_id: int) -> str:
        """Get current mode for user"""
        pass

    @abstractmethod
    def set_user_mode(self, user_id: int, mode: str) -> None:
        """Set mode for user"""
        pass

    @abstractmethod
    async def invalidate_cache(self, user_id: int) -> None:
        """Invalidate cached user-specific components"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup all user contexts"""
        pass


class IMessageProcessor(ABC):
    """Interface for processing messages"""

    @abstractmethod
    async def process_message(self, message: IncomingMessageDTO) -> None:
        """Process an incoming message"""
        pass

    @abstractmethod
    async def process_message_group(
        self, group: MessageGroup, processing_msg_id: int, chat_id: int
    ) -> None:
        """Process a complete message group"""
        pass


class INoteCreationService(ABC):
    """Interface for note creation service"""

    @abstractmethod
    async def create_note(
        self, group: MessageGroup, processing_msg_id: int, chat_id: int, user_id: int, user_kb: dict
    ) -> None:
        """Create a note from message group"""
        pass


class IQuestionAnsweringService(ABC):
    """Interface for question answering service"""

    @abstractmethod
    async def answer_question(
        self, group: MessageGroup, processing_msg_id: int, chat_id: int, user_id: int, user_kb: dict
    ) -> None:
        """Answer a question based on knowledge base"""
        pass


class IAgentTaskService(ABC):
    """Interface for agent task service"""

    @abstractmethod
    async def execute_task(
        self, group: MessageGroup, processing_msg_id: int, chat_id: int, user_id: int, user_kb: dict
    ) -> None:
        """Execute a free-form agent task"""
        pass
