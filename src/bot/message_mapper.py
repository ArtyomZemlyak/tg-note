"""
Message Mapper
Maps between Telegram messages and application DTOs
"""

from typing import Dict, Any
from telebot.types import Message

from src.bot.dto import IncomingMessageDTO


class MessageMapper:
    """
    Mapper for converting between Telegram messages and application DTOs
    
    This mapper isolates the Telegram SDK dependency to the bot layer,
    allowing the rest of the application to work with platform-independent DTOs.
    """
    
    @staticmethod
    def from_telegram_message(message: Message) -> IncomingMessageDTO:
        """
        Convert Telegram message to IncomingMessageDTO
        
        Args:
            message: Telegram Message object
        
        Returns:
            IncomingMessageDTO with all relevant data
        """
        return IncomingMessageDTO(
            message_id=message.message_id,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text=message.text or '',
            content_type=message.content_type,
            timestamp=message.date,
            caption=message.caption or '',
            forward_from=message.forward_from,
            forward_from_chat=message.forward_from_chat,
            forward_from_message_id=message.forward_from_message_id,
            forward_sender_name=message.forward_sender_name,
            forward_date=message.forward_date,
            photo=message.photo if hasattr(message, 'photo') else None,
            document=message.document if hasattr(message, 'document') else None,
            video=message.video if hasattr(message, 'video') else None,
            audio=message.audio if hasattr(message, 'audio') else None,
            voice=message.voice if hasattr(message, 'voice') else None,
            video_note=message.video_note if hasattr(message, 'video_note') else None,
            animation=message.animation if hasattr(message, 'animation') else None,
            sticker=message.sticker if hasattr(message, 'sticker') else None,
        )
    
    @staticmethod
    def to_dict(dto: IncomingMessageDTO) -> Dict[str, Any]:
        """
        Convert IncomingMessageDTO to dictionary format
        
        This is useful for legacy code that still works with dict representations
        
        Args:
            dto: IncomingMessageDTO object
        
        Returns:
            Dictionary with message data
        """
        message_dict = {
            'message_id': dto.message_id,
            'chat_id': dto.chat_id,
            'user_id': dto.user_id,
            'text': dto.text,
            'caption': dto.caption or '',
            'content_type': dto.content_type,
            'forward_from': dto.forward_from,
            'forward_from_chat': dto.forward_from_chat,
            'forward_from_message_id': dto.forward_from_message_id,
            'forward_sender_name': dto.forward_sender_name,
            'forward_date': dto.forward_date,
            'date': dto.timestamp,
        }
        
        # Add media attachments if present
        if dto.photo:
            message_dict['photo'] = dto.photo
        if dto.document:
            message_dict['document'] = dto.document
        if dto.video:
            message_dict['video'] = dto.video
        if dto.audio:
            message_dict['audio'] = dto.audio
        if dto.voice:
            message_dict['voice'] = dto.voice
        if dto.video_note:
            message_dict['video_note'] = dto.video_note
        if dto.animation:
            message_dict['animation'] = dto.animation
        if dto.sticker:
            message_dict['sticker'] = dto.sticker
        
        return message_dict
