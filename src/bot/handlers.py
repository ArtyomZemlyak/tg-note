"""
Telegram Bot Handlers
Handles all incoming message events from Telegram (fully async)
"""

import logging
from typing import Dict, Any
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from config import settings
from src.processor.message_aggregator import MessageAggregator, MessageGroup
from src.processor.content_parser import ContentParser
from src.agents.stub_agent import StubAgent
from src.knowledge_base.manager import KnowledgeBaseManager
from src.tracker.processing_tracker import ProcessingTracker


class BotHandlers:
    """Telegram bot message handlers (fully async)"""
    
    def __init__(self, bot: AsyncTeleBot, tracker: ProcessingTracker, kb_manager: KnowledgeBaseManager):
        self.bot = bot
        self.tracker = tracker
        self.kb_manager = kb_manager
        self.message_aggregator = MessageAggregator(settings.MESSAGE_GROUP_TIMEOUT)
        self.content_parser = ContentParser()
        self.agent = StubAgent()
        self.logger = logging.getLogger(__name__)
        
        # Set up timeout callback for background task
        self.message_aggregator.set_timeout_callback(self._handle_timeout)
    
    async def register_handlers_async(self):
        """Register all bot handlers (async)"""
        # Command handlers
        self.bot.message_handler(commands=['start'])(self.handle_start)
        self.bot.message_handler(commands=['help'])(self.handle_help)
        self.bot.message_handler(commands=['status'])(self.handle_status)
        
        # Forwarded messages - register first to catch all forwarded content
        self.bot.message_handler(func=self._is_forwarded_message)(self.handle_forwarded_message)
        
        # Regular message handlers - only for non-forwarded messages
        self.bot.message_handler(func=lambda message: message.content_type == 'text' and not self._is_forwarded_message(message))(self.handle_text_message)
        self.bot.message_handler(func=lambda message: message.content_type == 'photo' and not self._is_forwarded_message(message))(self.handle_photo_message)
        self.bot.message_handler(func=lambda message: message.content_type == 'document' and not self._is_forwarded_message(message))(self.handle_document_message)
    
    def _is_forwarded_message(self, message: Message) -> bool:
        """Check if message is forwarded from any source"""
        return (
            message.forward_from is not None or  # Forwarded from user
            message.forward_from_chat is not None or  # Forwarded from channel/group
            message.forward_sender_name is not None or  # Forwarded from privacy-enabled user
            message.forward_date is not None  # Forwarded message (any source)
        )
    
    def start_background_tasks(self) -> None:
        """Start background tasks for message processing"""
        self.logger.info("Starting background tasks")
        self.message_aggregator.start_background_task()
    
    def stop_background_tasks(self) -> None:
        """Stop background tasks"""
        self.logger.info("Stopping background tasks")
        self.message_aggregator.stop_background_task()
    
    async def _handle_timeout(self, chat_id: int, group: MessageGroup) -> None:
        """Handle a timed-out message group (async)"""
        try:
            self.logger.info(f"Processing timed-out group for chat {chat_id} with {len(group.messages)} messages")
            
            # Send notification about processing the timed-out group
            processing_msg = await self.bot.send_message(
                chat_id,
                "🔄 Обрабатываю завершенную группу сообщений..."
            )
            
            # Process the group
            await self._process_message_group(group, processing_msg)
            
        except Exception as e:
            self.logger.error(f"Error handling timed-out group for chat {chat_id}: {e}", exc_info=True)
    
    async def handle_start(self, message: Message) -> None:
        """Handle /start command (async)"""
        self.logger.info(f"Start command from user {message.from_user.id}")
        
        welcome_text = (
            "🤖 Добро пожаловать в tg-note!\n\n"
            "Этот бот автоматически создает заметки в базе знаний из ваших сообщений и репостов.\n\n"
            "Просто отправьте мне:\n"
            "• Текстовые сообщения\n"
            "• Репосты новостей или статей\n"
            "• Фотографии с подписями\n"
            "• Документы\n\n"
            "Бот проанализирует контент и сохранит важную информацию в базу знаний.\n\n"
            "Команды:\n"
            "/help - показать справку\n"
            "/status - показать статистику обработки"
        )
        
        await self.bot.reply_to(message, welcome_text)
    
    async def handle_help(self, message: Message) -> None:
        """Handle /help command (async)"""
        self.logger.info(f"Help command from user {message.from_user.id}")
        
        help_text = (
            "📚 Справка по tg-note\n\n"
            "Бот автоматически обрабатывает ваши сообщения и создает заметки в базе знаний.\n\n"
            "Поддерживаемые типы контента:\n"
            "• 📝 Текстовые сообщения\n"
            "• 🔄 Репосты (forwarded messages)\n"
            "• 📷 Фотографии с подписями\n"
            "• 📄 Документы\n\n"
            "Как это работает:\n"
            "1. Отправьте сообщение или репост\n"
            "2. Бот проанализирует контент\n"
            "3. Извлечет ключевую информацию\n"
            "4. Сохранит в базу знаний в формате Markdown\n\n"
            "Команды:\n"
            "/start - начать работу с ботом\n"
            "/status - статистика обработки\n"
            "/help - эта справка\n\n"
            "Бот работает для всех пользователей без ограничений!"
        )
        
        await self.bot.reply_to(message, help_text)
    
    async def handle_status(self, message: Message) -> None:
        """Handle /status command (async)"""
        self.logger.info(f"Status command from user {message.from_user.id}")
        
        try:
            stats = self.tracker.get_stats()
            status_text = (
                f"📊 Статистика обработки\n\n"
                f"Всего обработано сообщений: {stats['total_processed']}\n"
                f"Ожидает обработки: {stats['pending_groups']}\n"
                f"Последняя обработка: {stats.get('last_processed', 'Никогда')}\n\n"
                f"База знаний: {settings.KB_PATH}\n"
                f"Git интеграция: {'Включена' if settings.KB_GIT_ENABLED else 'Отключена'}"
            )
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            status_text = "❌ Ошибка получения статистики"
        
        await self.bot.reply_to(message, status_text)
    
    async def handle_text_message(self, message: Message) -> None:
        """Handle regular text messages (async)"""
        self.logger.info(f"Text message from user {message.from_user.id}: {message.text[:50]}...")
        await self._process_message(message)
    
    async def handle_photo_message(self, message: Message) -> None:
        """Handle photo messages (async)"""
        self.logger.info(f"Photo message from user {message.from_user.id}")
        await self._process_message(message)
    
    async def handle_document_message(self, message: Message) -> None:
        """Handle document messages (async)"""
        self.logger.info(f"Document message from user {message.from_user.id}")
        await self._process_message(message)
    
    async def handle_forwarded_message(self, message: Message) -> None:
        """Handle forwarded messages (async)"""
        self.logger.info(f"Forwarded message from user {message.from_user.id}")
        await self._process_message(message)
    
    async def _process_message(self, message: Message) -> None:
        """Process any type of message (async)"""
        try:
            # Send processing notification
            processing_msg = await self.bot.reply_to(message, "🔄 Обрабатываю сообщение...")
            
            # Convert message to dict for aggregator
            message_dict = self._message_to_dict(message)
            
            # Add message to aggregator (fully async)
            closed_group = await self.message_aggregator.add_message(message.chat.id, message_dict)
            
            if closed_group:
                # Previous group was closed, process it with a separate notification
                prev_processing_msg = await self.bot.send_message(
                    message.chat.id, 
                    "🔄 Обрабатываю предыдущую группу сообщений..."
                )
                await self._process_message_group(closed_group, prev_processing_msg)
                
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
    
    def _message_to_dict(self, message: Message) -> Dict[str, Any]:
        """Convert Telegram message to dictionary"""
        return {
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
            'photo': message.photo,
            'document': message.document
        }
    
    async def _process_message_group(self, group, processing_msg: Message) -> None:
        """Process a complete message group (async)"""
        try:
            # Parse content
            content = self.content_parser.parse_group(group)
            content_hash = self.content_parser.generate_hash(content)
            
            # Check if already processed
            if self.tracker.is_processed(content_hash):
                await self.bot.edit_message_text(
                    "✅ Это сообщение уже было обработано ранее",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Process with agent
            await self.bot.edit_message_text(
                "🤖 Анализирую контент...",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
            
            processed_content = self.agent.process(content)
            
            # Save to knowledge base
            await self.bot.edit_message_text(
                "💾 Сохраняю в базу знаний...",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
            
            kb_file = self.kb_manager.save_content(processed_content, content)
            
            # Mark as processed (use first message from group)
            if not group.messages:
                # Skip tracking for empty groups to avoid invalid entries
                self.logger.warning("Skipping tracker entry for empty message group")
            else:
                first_message = group.messages[0]
                message_ids = [msg.get('message_id') for msg in group.messages if msg.get('message_id')]
                chat_id = first_message.get('chat_id')
                
                if message_ids and chat_id:
                    self.tracker.add_processed(
                        content_hash=content_hash,
                        message_ids=message_ids,
                        chat_id=chat_id,
                        kb_file=str(kb_file),
                        status="completed"
                    )
                else:
                    self.logger.warning(f"Skipping tracker entry due to missing IDs: message_ids={message_ids}, chat_id={chat_id}")
            
            # Success notification
            await self.bot.edit_message_text(
                f"✅ Сообщение успешно обработано и сохранено!\n\n"
                f"📁 Файл: `{kb_file.name}`\n"
                f"🔗 Путь: `{kb_file}`",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.error(f"Error processing message group: {e}")
            try:
                await self.bot.edit_message_text(
                    "❌ Ошибка обработки сообщения",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
            except Exception:
                pass
