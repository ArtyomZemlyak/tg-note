"""
Message Processor Service
Handles message processing and routing
Follows Single Responsibility Principle
"""

from typing import Any, Dict
from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from src.services.interfaces import (
    IMessageProcessor,
    IUserContextManager,
    INoteCreationService,
    IQuestionAnsweringService
)
from src.processor.message_aggregator import MessageGroup
from src.knowledge_base.user_settings import UserSettings


class MessageProcessor(IMessageProcessor):
    """
    Service for processing messages
    
    Responsibilities:
    - Convert messages to dict format
    - Add messages to aggregators
    - Route message groups to appropriate services (note/question)
    """
    
    def __init__(
        self,
        bot: AsyncTeleBot,
        user_context_manager: IUserContextManager,
        user_settings: UserSettings,
        note_creation_service: INoteCreationService,
        question_answering_service: IQuestionAnsweringService
    ):
        """
        Initialize message processor
        
        Args:
            bot: Telegram bot instance
            user_context_manager: User context manager
            user_settings: User settings
            note_creation_service: Note creation service
            question_answering_service: Question answering service
        """
        self.bot = bot
        self.user_context_manager = user_context_manager
        self.user_settings = user_settings
        self.note_creation_service = note_creation_service
        self.question_answering_service = question_answering_service
        self.logger = logger
    
    async def process_message(self, message: Message) -> None:
        """
        Process an incoming message
        
        Args:
            message: Telegram message
        """
        try:
            # Send processing notification
            processing_msg = await self.bot.reply_to(message, "🔄 Обрабатываю сообщение...")
            
            # Convert message to dict
            message_dict = self._message_to_dict(message)
            
            # Get user-specific aggregator
            user_aggregator = self.user_context_manager.get_or_create_aggregator(message.from_user.id)
            
            # Add message to aggregator
            closed_group = await user_aggregator.add_message(message.chat.id, message_dict)
            
            if closed_group:
                # Previous group was closed, process it
                prev_processing_msg = await self.bot.send_message(
                    message.chat.id,
                    "🔄 Обрабатываю предыдущую группу сообщений..."
                )
                await self.process_message_group(closed_group, prev_processing_msg)
                
                # Update current message status
                await self.bot.edit_message_text(
                    "🔄 Добавлено к новой группе сообщений...",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
            else:
                # Message added to existing group
                await self.bot.edit_message_text(
                    "🔄 Добавлено к группе сообщений, ожидаю завершения...",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
        
        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)
            try:
                await self.bot.reply_to(message, "❌ Ошибка обработки сообщения")
            except Exception:
                pass
    
    async def process_message_group(self, group: MessageGroup, processing_msg: Message) -> None:
        """
        Process a complete message group
        
        Args:
            group: Message group to process
            processing_msg: Processing status message
        """
        try:
            # Get user_id from the first message in the group
            if not group.messages:
                self.logger.warning("Empty message group, skipping processing")
                return
            
            user_id = group.messages[0].get('user_id')
            if not user_id:
                self.logger.error("Cannot determine user_id from message group")
                await self.bot.edit_message_text(
                    "❌ Ошибка: не удалось определить пользователя",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Check if user has KB configured
            user_kb = self.user_settings.get_user_kb(user_id)
            
            if not user_kb:
                await self.bot.edit_message_text(
                    "❌ База знаний не настроена\n\n"
                    "Используйте /setkb для настройки базы знаний",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Route to appropriate service based on user mode
            user_mode = self.user_context_manager.get_user_mode(user_id)
            
            if user_mode == "ask":
                await self.question_answering_service.answer_question(
                    group, processing_msg, user_id, user_kb
                )
            else:  # default to "note" mode
                await self.note_creation_service.create_note(
                    group, processing_msg, user_id, user_kb
                )
        
        except Exception as e:
            self.logger.error(f"Error processing message group: {e}", exc_info=True)
            try:
                await self.bot.edit_message_text(
                    f"❌ Ошибка обработки сообщения: {str(e)}",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
            except Exception:
                pass
    
    def _message_to_dict(self, message: Message) -> Dict[str, Any]:
        """
        Convert Telegram message to dictionary
        
        Args:
            message: Telegram message
        
        Returns:
            Message dictionary
        """
        # Base message data
        message_dict = {
            'message_id': message.message_id,
            'chat_id': message.chat.id,
            'user_id': message.from_user.id,
            'text': message.text or '',
            'caption': message.caption or '',
            'content_type': message.content_type,
            'forward_from': message.forward_from,
            'forward_from_chat': message.forward_from_chat,
            'forward_from_message_id': message.forward_from_message_id,
            'forward_sender_name': message.forward_sender_name,
            'forward_date': message.forward_date,
            'date': message.date,
        }
        
        # Add media attachments if present (decoupled from processing logic)
        # This allows us to capture media info without requiring processing support
        if hasattr(message, 'photo') and message.photo:
            message_dict['photo'] = message.photo
        if hasattr(message, 'document') and message.document:
            message_dict['document'] = message.document
        if hasattr(message, 'video') and message.video:
            message_dict['video'] = message.video
        if hasattr(message, 'audio') and message.audio:
            message_dict['audio'] = message.audio
        if hasattr(message, 'voice') and message.voice:
            message_dict['voice'] = message.voice
        if hasattr(message, 'video_note') and message.video_note:
            message_dict['video_note'] = message.video_note
        if hasattr(message, 'animation') and message.animation:
            message_dict['animation'] = message.animation
        if hasattr(message, 'sticker') and message.sticker:
            message_dict['sticker'] = message.sticker
        
        return message_dict
