"""
Telegram Bot Handlers
Handles all incoming message events from Telegram
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
from telebot import TeleBot
from telebot.types import Message

from config import settings
from src.processor.message_aggregator import MessageAggregator
from src.processor.content_parser import ContentParser
from src.agents.stub_agent import StubAgent
from src.knowledge_base.manager import KnowledgeBaseManager
from src.tracker.processing_tracker import ProcessingTracker


class BotHandlers:
    """Telegram bot message handlers"""

    def __init__(self, bot: TeleBot, tracker: ProcessingTracker, kb_manager: KnowledgeBaseManager):
        self.bot = bot
        self.tracker = tracker
        self.kb_manager = kb_manager
        self.message_aggregator = MessageAggregator(settings.MESSAGE_GROUP_TIMEOUT)
        self.content_parser = ContentParser()
        self.agent = StubAgent()
        self.logger = logging.getLogger(__name__)

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register all bot handlers"""
        # Command handlers
        self.bot.message_handler(commands=["start"])(self.handle_start)
        self.bot.message_handler(commands=["help"])(self.handle_help)
        self.bot.message_handler(commands=["status"])(self.handle_status)

        # Message handlers - use func parameter to avoid conflicts
        self.bot.message_handler(
            func=lambda message: message.content_type == "text" and message.forward_from is None
        )(self.handle_text_message)
        self.bot.message_handler(func=lambda message: message.content_type == "photo")(
            self.handle_photo_message
        )
        self.bot.message_handler(func=lambda message: message.content_type == "document")(
            self.handle_document_message
        )

        # Forwarded messages
        self.bot.message_handler(func=lambda message: message.forward_from is not None)(
            self.handle_forwarded_message
        )

    def handle_start(self, message: Message) -> None:
        """Handle /start command"""
        self.logger.info(f"Start command from user {message.from_user.id}")

        welcome_text = (
            "🤖 Добро пожаловать в tg-note!\n\n"
            "Этот бот автоматически создает заметки в базе знаний из ваших "
            "сообщений и репостов.\n\n"
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

        self.bot.reply_to(message, welcome_text)

    def handle_help(self, message: Message) -> None:
        """Handle /help command"""
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

        self.bot.reply_to(message, help_text)

    def handle_status(self, message: Message) -> None:
        """Handle /status command"""
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

        self.bot.reply_to(message, status_text)

    def handle_text_message(self, message: Message) -> None:
        """Handle regular text messages"""
        self.logger.info(f"Text message from user {message.from_user.id}: {message.text[:50]}...")
        self._process_message(message)

    def handle_photo_message(self, message: Message) -> None:
        """Handle photo messages"""
        self.logger.info(f"Photo message from user {message.from_user.id}")
        self._process_message(message)

    def handle_document_message(self, message: Message) -> None:
        """Handle document messages"""
        self.logger.info(f"Document message from user {message.from_user.id}")
        self._process_message(message)

    def handle_forwarded_message(self, message: Message) -> None:
        """Handle forwarded messages"""
        self.logger.info(f"Forwarded message from user {message.from_user.id}")
        self._process_message(message)

    def _process_message(self, message: Message) -> None:
        """Process any type of message"""
        try:
            # Send processing notification
            processing_msg = self.bot.reply_to(message, "🔄 Обрабатываю сообщение...")

            # Convert message to dict for aggregator
            message_dict = self._message_to_dict(message)

            # Add message to aggregator
            closed_group = self.message_aggregator.add_message(message.chat.id, message_dict)

            if closed_group:
                # Previous group was closed, process it
                asyncio.create_task(self._process_message_group(closed_group, processing_msg))
                # Start new group with current message
                self.message_aggregator.add_message(message.chat.id, message_dict)
                self.bot.edit_message_text(
                    "🔄 Добавлено к новой группе сообщений...",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id,
                )
            else:
                # Message added to existing group
                self.bot.edit_message_text(
                    "🔄 Добавлено к группе сообщений, ожидаю завершения...",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id,
                )

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            try:
                self.bot.reply_to(message, "❌ Ошибка обработки сообщения")
            except Exception:
                pass

    def _message_to_dict(self, message: Message) -> Dict[str, Any]:
        """Convert Telegram message to dictionary"""
        return {
            "message_id": message.message_id,
            "chat_id": message.chat.id,
            "user_id": message.from_user.id,
            "text": message.text or "",
            "caption": message.caption or "",
            "content_type": message.content_type,
            "forward_from": message.forward_from,
            "forward_from_message_id": message.forward_from_message_id,
            "date": message.date,
            "photo": message.photo,
            "document": message.document,
        }

    async def _process_message_group(self, group, processing_msg: Message) -> None:
        """Process a complete message group"""
        try:
            # Parse content
            content = self.content_parser.parse_message_group(group.messages)
            content_hash = self.content_parser.generate_content_hash(content["text"])

            # Check if already processed
            if self.tracker.is_processed(content_hash):
                self.bot.edit_message_text(
                    "✅ Это сообщение уже было обработано ранее",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id,
                )
                return

            # Process with agent
            self.bot.edit_message_text(
                "🤖 Анализирую контент...",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
            )

            processed_content = await self.agent.process(content)

            # Save to knowledge base
            self.bot.edit_message_text(
                "💾 Сохраняю в базу знаний...",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
            )

            kb_file = self.kb_manager.create_article(
                content=processed_content["markdown"],
                title=processed_content["title"],
                category=processed_content["category"],
                metadata=processed_content["metadata"]
            )

            # Mark as processed (use first message from group)
            first_message = group.messages[0] if group.messages else {}
            self.tracker.add_processed(
                content_hash=content_hash,
                message_ids=[first_message.get("message_id", 0)],
                chat_id=first_message.get("chat_id", 0),
                kb_file=str(kb_file),
                status="completed"
            )

            # Success notification
            self.bot.edit_message_text(
                f"✅ Сообщение успешно обработано и сохранено!\n\n"
                f"📁 Файл: `{Path(kb_file).name}`\n"
                f"🔗 Путь: `{kb_file}`",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error processing message group: {e}")
            try:
                self.bot.edit_message_text(
                    "❌ Ошибка обработки сообщения",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id,
                )
            except Exception:
                pass
