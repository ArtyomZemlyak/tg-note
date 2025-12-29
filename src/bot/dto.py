"""
Data Transfer Objects (DTOs) for bot messaging
Decouples application from Telegram types
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class IncomingMessageDTO:
    """
    Data Transfer Object for incoming messages

    This DTO decouples the application from the Telegram SDK,
    allowing services to work with a platform-independent message format.

    Attributes:
        message_id: Unique message identifier
        chat_id: Chat identifier where message was sent
        user_id: User identifier who sent the message
        text: Message text content (if any)
        content_type: Type of message content (text, photo, document, etc.)
        timestamp: Unix timestamp when message was sent
    """

    # Core identifiers
    message_id: int
    chat_id: int
    user_id: int

    # Content
    text: str
    content_type: str
    timestamp: int

    # Optional fields
    caption: Optional[str] = None
    forward_from: Optional[Any] = None
    forward_from_chat: Optional[Any] = None
    forward_from_message_id: Optional[int] = None
    forward_sender_name: Optional[str] = None
    forward_date: Optional[int] = None

    # Media attachments (platform-specific, kept as-is for now)
    photo: Optional[Any] = None
    document: Optional[Any] = None
    video: Optional[Any] = None
    audio: Optional[Any] = None
    voice: Optional[Any] = None
    video_note: Optional[Any] = None
    animation: Optional[Any] = None
    sticker: Optional[Any] = None

    # Internal flags
    skip_deduplication: bool = False  # Skip deduplication check (for scheduled tasks, etc.)

    def is_forwarded(self) -> bool:
        """Check if message is forwarded"""
        if self.forward_date is not None and self.forward_date > 0:
            return True
        return bool(
            self.forward_from
            or self.forward_from_chat
            or (self.forward_sender_name and self.forward_sender_name.strip())
        )


@dataclass
class OutgoingMessageDTO:
    """
    Data Transfer Object for outgoing messages

    Represents a message that needs to be sent by the bot
    """

    chat_id: int
    text: str
    parse_mode: Optional[str] = None
    reply_to_message_id: Optional[int] = None
