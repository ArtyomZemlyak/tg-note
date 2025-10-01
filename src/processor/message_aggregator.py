"""
Message Aggregator
Groups consecutive messages into single content blocks
"""

from datetime import datetime
from typing import List, Dict, Optional
from uuid import uuid4


class MessageGroup:
    """Represents a group of related messages"""

    def __init__(self, timeout: int = 30):
        self.group_id = str(uuid4())
        self.messages: List[Dict] = []
        self.started_at = datetime.now()
        self.timeout = timeout
        self.closed = False

    def add_message(self, message: Dict) -> None:
        """Add message to group"""
        if not self.closed:
            self.messages.append(message)

    def should_close(self) -> bool:
        """Check if group should be closed based on timeout"""
        elapsed = (datetime.now() - self.started_at).total_seconds()
        return elapsed >= self.timeout

    def close(self) -> None:
        """Close the group"""
        self.closed = True


class MessageAggregator:
    """Aggregates messages into groups"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.active_groups: Dict[int, MessageGroup] = {}

    def add_message(self, chat_id: int, message: Dict) -> Optional[MessageGroup]:
        """
        Add message to aggregator

        Args:
            chat_id: Telegram chat ID
            message: Message data

        Returns:
            Closed MessageGroup if timeout reached, None otherwise
        """
        # Get or create group for this chat
        if chat_id not in self.active_groups:
            self.active_groups[chat_id] = MessageGroup(self.timeout)

        group = self.active_groups[chat_id]

        # Check if current group should be closed
        if group.should_close():
            group.close()
            closed_group = group
            # Start new group
            self.active_groups[chat_id] = MessageGroup(self.timeout)
            self.active_groups[chat_id].add_message(message)
            return closed_group

        # Add message to current group
        group.add_message(message)
        return None

    def force_close_group(self, chat_id: int) -> Optional[MessageGroup]:
        """
        Force close group for a chat

        Args:
            chat_id: Telegram chat ID

        Returns:
            Closed MessageGroup if exists, None otherwise
        """
        if chat_id in self.active_groups:
            group = self.active_groups[chat_id]
            group.close()
            del self.active_groups[chat_id]
            return group
        return None
