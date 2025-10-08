"""
Message Processor Service
Handles message processing and routing
Follows Single Responsibility Principle
"""

from typing import Any, Dict
from loguru import logger

from src.bot.bot_port import BotPort
from src.bot.dto import IncomingMessageDTO
from src.bot.message_mapper import MessageMapper
from src.services.interfaces import (
    IMessageProcessor,
    IUserContextManager,
    INoteCreationService,
    IQuestionAnsweringService,
    IAgentTaskService
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
        bot: BotPort,
        user_context_manager: IUserContextManager,
        user_settings: UserSettings,
        note_creation_service: INoteCreationService,
        question_answering_service: IQuestionAnsweringService,
        agent_task_service: IAgentTaskService
    ):
        """
        Initialize message processor
        
        Args:
            bot: Bot messaging interface (transport abstraction)
            user_context_manager: User context manager
            user_settings: User settings
            note_creation_service: Note creation service
            question_answering_service: Question answering service
            agent_task_service: Agent task service
        """
        self.bot = bot
        self.user_context_manager = user_context_manager
        self.user_settings = user_settings
        self.note_creation_service = note_creation_service
        self.question_answering_service = question_answering_service
        self.agent_task_service = agent_task_service
        self.logger = logger
    
    async def process_message(self, message: IncomingMessageDTO) -> None:
        """
        Process an incoming message
        
        Args:
            message: Incoming message DTO
        """
        try:
            # Send processing notification
            processing_msg = await self.bot.send_message(message.chat_id, "🔄 Обрабатываю сообщение...")
            
            # Convert DTO to dict format for aggregator
            message_dict = MessageMapper.to_dict(message)
            
            # Get user-specific aggregator
            user_aggregator = self.user_context_manager.get_or_create_aggregator(message.user_id)
            
            # Add message to aggregator
            closed_group = await user_aggregator.add_message(message.chat_id, message_dict)
            
            if closed_group:
                # Previous group was closed, process it
                prev_processing_msg = await self.bot.send_message(
                    message.chat_id,
                    "🔄 Обрабатываю предыдущую группу сообщений..."
                )
                await self.process_message_group(
                    closed_group, 
                    prev_processing_msg.message_id,
                    message.chat_id
                )
                
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
                await self.bot.send_message(message.chat_id, "❌ Ошибка обработки сообщения")
            except Exception:
                pass
    
    async def process_message_group(self, group: MessageGroup, processing_msg_id: int, chat_id: int) -> None:
        """
        Process a complete message group
        
        Args:
            group: Message group to process
            processing_msg_id: ID of the processing status message
            chat_id: Chat ID where message group was sent
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
                    chat_id=chat_id,
                    message_id=processing_msg_id
                )
                return
            
            # Check if user has KB configured
            user_kb = self.user_settings.get_user_kb(user_id)
            
            if not user_kb:
                await self.bot.edit_message_text(
                    "❌ База знаний не настроена\n\n"
                    "Используйте /setkb для настройки базы знаний",
                    chat_id=chat_id,
                    message_id=processing_msg_id
                )
                return
            
            # Route to appropriate service based on user mode
            user_mode = self.user_context_manager.get_user_mode(user_id)
            
            if user_mode == "ask":
                await self.question_answering_service.answer_question(
                    group, processing_msg_id, chat_id, user_id, user_kb
                )
            elif user_mode == "agent":
                await self.agent_task_service.execute_task(
                    group, processing_msg_id, chat_id, user_id, user_kb
                )
            else:  # default to "note" mode
                await self.note_creation_service.create_note(
                    group, processing_msg_id, chat_id, user_id, user_kb
                )
        
        except Exception as e:
            self.logger.error(f"Error processing message group: {e}", exc_info=True)
            try:
                await self.bot.edit_message_text(
                    f"❌ Ошибка обработки сообщения: {str(e)}",
                    chat_id=chat_id,
                    message_id=processing_msg_id
                )
            except Exception:
                pass
    
