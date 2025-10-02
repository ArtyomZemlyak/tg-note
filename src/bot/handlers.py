"""
Telegram Bot Handlers
Handles all incoming message events from Telegram (fully async)
"""

import logging
from typing import Dict, Any, Optional
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from config import settings
from src.processor.message_aggregator import MessageAggregator, MessageGroup
from src.processor.content_parser import ContentParser
from src.agents.agent_factory import AgentFactory
from src.knowledge_base.manager import KnowledgeBaseManager
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.user_settings import UserSettings
from src.knowledge_base.git_ops import GitOperations
from src.tracker.processing_tracker import ProcessingTracker


class BotHandlers:
    """Telegram bot message handlers (fully async)"""
    
    def __init__(
        self, 
        bot: AsyncTeleBot, 
        tracker: ProcessingTracker,
        repo_manager: RepositoryManager,
        user_settings: UserSettings
    ):
        self.bot = bot
        self.tracker = tracker
        self.repo_manager = repo_manager
        self.user_settings = user_settings
        self.message_aggregator = MessageAggregator(settings.MESSAGE_GROUP_TIMEOUT)
        self.content_parser = ContentParser()
        
        # Initialize agent using factory based on settings
        self.agent = AgentFactory.from_settings(settings)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Initialized agent: {type(self.agent).__name__}")
        
        # Set up timeout callback for background task
        self.message_aggregator.set_timeout_callback(self._handle_timeout)
    
    async def register_handlers_async(self):
        """Register all bot handlers (async)"""
        # Command handlers
        self.bot.message_handler(commands=['start'])(self.handle_start)
        self.bot.message_handler(commands=['help'])(self.handle_help)
        self.bot.message_handler(commands=['status'])(self.handle_status)
        self.bot.message_handler(commands=['setkb'])(self.handle_setkb)
        self.bot.message_handler(commands=['kb'])(self.handle_kb_info)
        
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
            "**Основные команды:**\n"
            "/start - начать работу с ботом\n"
            "/status - статистика обработки\n"
            "/help - эта справка\n\n"
            "**База знаний:**\n"
            "/setkb <name|url> - настроить базу знаний\n"
            "/kb - информация о базе знаний\n\n"
            "**Настройки:**\n"
            "/settings - меню настроек\n"
            "/viewsettings - просмотр всех настроек\n"
            "/kbsettings - настройки базы знаний\n"
            "/agentsettings - настройки агента\n\n"
            "Бот работает для всех пользователей без ограничений!"
        )
        
        await self.bot.reply_to(message, help_text)
    
    async def handle_status(self, message: Message) -> None:
        """Handle /status command (async)"""
        self.logger.info(f"Status command from user {message.from_user.id}")
        
        try:
            stats = self.tracker.get_stats()
            user_kb = self.user_settings.get_user_kb(message.from_user.id)
            
            kb_info = "Не настроена (используйте /setkb)"
            if user_kb:
                kb_info = f"{user_kb['kb_name']} ({user_kb['kb_type']})"
            
            status_text = (
                f"📊 Статистика обработки\n\n"
                f"Всего обработано сообщений: {stats['total_processed']}\n"
                f"Ожидает обработки: {stats['pending_groups']}\n"
                f"Последняя обработка: {stats.get('last_processed', 'Никогда')}\n\n"
                f"База знаний: {kb_info}\n"
                f"Git интеграция: {'Включена' if settings.KB_GIT_ENABLED else 'Отключена'}"
            )
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            status_text = "❌ Ошибка получения статистики"
        
        await self.bot.reply_to(message, status_text)
    
    async def handle_setkb(self, message: Message) -> None:
        """Handle /setkb command - set up knowledge base (async)"""
        self.logger.info(f"Setkb command from user {message.from_user.id}")
        
        # Parse command arguments
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            help_text = (
                "📚 Настройка базы знаний\n\n"
                "Использование:\n"
                "/setkb <название> - создать локальную базу знаний\n"
                "/setkb <github_url> - использовать GitHub репозиторий\n\n"
                "Примеры:\n"
                "/setkb my-notes\n"
                "/setkb https://github.com/user/knowledge-base\n"
            )
            await self.bot.reply_to(message, help_text)
            return
        
        kb_input = args[1].strip()
        
        # Determine if it's a GitHub URL or local name
        if kb_input.startswith('http://') or kb_input.startswith('https://') or kb_input.startswith('git@'):
            # GitHub repository
            success, msg, kb_path = self.repo_manager.clone_github_kb(kb_input)
            
            if success:
                kb_name = kb_path.name
                self.user_settings.set_user_kb(
                    message.from_user.id,
                    kb_name,
                    kb_type="github",
                    github_url=kb_input
                )
                await self.bot.reply_to(
                    message,
                    f"✅ {msg}\n\n"
                    f"Репозиторий: {kb_input}\n"
                    f"Локальный путь: {kb_path}"
                )
            else:
                await self.bot.reply_to(message, f"❌ {msg}")
        else:
            # Local knowledge base
            success, msg, kb_path = self.repo_manager.init_local_kb(kb_input)
            
            if success:
                self.user_settings.set_user_kb(
                    message.from_user.id,
                    kb_input,
                    kb_type="local"
                )
                await self.bot.reply_to(
                    message,
                    f"✅ {msg}\n\n"
                    f"Локальный путь: {kb_path}\n"
                    f"Инициализирован git репозиторий"
                )
            else:
                await self.bot.reply_to(message, f"❌ {msg}")
    
    async def handle_kb_info(self, message: Message) -> None:
        """Handle /kb command - show KB info (async)"""
        self.logger.info(f"KB info command from user {message.from_user.id}")
        
        user_kb = self.user_settings.get_user_kb(message.from_user.id)
        
        if not user_kb:
            await self.bot.reply_to(
                message,
                "❌ База знаний не настроена\n\n"
                "Используйте /setkb для настройки"
            )
            return
        
        kb_path = self.repo_manager.get_kb_path(user_kb['kb_name'])
        
        info_text = (
            f"📚 Информация о базе знаний\n\n"
            f"Название: {user_kb['kb_name']}\n"
            f"Тип: {user_kb['kb_type']}\n"
        )
        
        if user_kb['kb_type'] == 'github':
            info_text += f"GitHub: {user_kb.get('github_url', 'N/A')}\n"
        
        if kb_path:
            info_text += f"Локальный путь: {kb_path}\n"
        else:
            info_text += "⚠️ Локальная копия не найдена\n"
        
        await self.bot.reply_to(message, info_text)
    
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
            # Get user_id from the first message in the group (original user message, not bot's processing_msg)
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
            
            # Get KB path
            kb_path = self.repo_manager.get_kb_path(user_kb['kb_name'])
            if not kb_path:
                await self.bot.edit_message_text(
                    "❌ Локальная копия базы знаний не найдена\n\n"
                    "Попробуйте настроить базу знаний заново: /setkb",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Create KB manager for user's KB
            kb_manager = KnowledgeBaseManager(str(kb_path))
            git_ops = GitOperations(str(kb_path), enabled=settings.KB_GIT_ENABLED)
            
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
            
            try:
                processed_content = await self.agent.process(content)
            except Exception as agent_error:
                self.logger.error(f"Agent processing failed: {agent_error}", exc_info=True)
                await self.bot.edit_message_text(
                    f"❌ Ошибка обработки контента агентом:\n{str(agent_error)}\n\n"
                    f"Проверьте, что Qwen CLI правильно настроен и инициализирован.",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Save to knowledge base
            await self.bot.edit_message_text(
                "💾 Сохраняю в базу знаний...",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
            
            # Extract KB structure from processed content
            kb_structure = processed_content.get('kb_structure')
            title = processed_content.get('title')
            markdown = processed_content.get('markdown')
            metadata = processed_content.get('metadata')
            
            # Validate required fields
            if not kb_structure:
                self.logger.error("Agent did not return kb_structure")
                raise ValueError("Agent processing incomplete: missing kb_structure")
            
            if not title:
                self.logger.warning("Agent did not return title, using default")
                title = "Untitled Note"
            
            if not markdown:
                self.logger.error("Agent did not return markdown content")
                raise ValueError("Agent processing incomplete: missing markdown content")
            
            # Create article using KB structure from agent
            try:
                kb_file = kb_manager.create_article(
                    content=markdown,
                    title=title,
                    kb_structure=kb_structure,
                    metadata=metadata
                )
            except Exception as kb_error:
                self.logger.error(f"Failed to create KB article: {kb_error}", exc_info=True)
                await self.bot.edit_message_text(
                    f"❌ Ошибка сохранения в базу знаний:\n{str(kb_error)}",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Update index
            kb_manager.update_index(kb_file, title, kb_structure)
            
            # Git operations
            if settings.KB_GIT_ENABLED and git_ops.enabled:
                git_ops.add(str(kb_file))
                git_ops.add(str(kb_path / "index.md"))
                git_ops.commit(f"Add article: {title}")
                
                if settings.KB_GIT_AUTO_PUSH:
                    git_ops.push(settings.KB_GIT_REMOTE, settings.KB_GIT_BRANCH)
            
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
            
            # Success notification with category info
            category_str = kb_structure.category
            if kb_structure.subcategory:
                category_str += f"/{kb_structure.subcategory}"
            
            await self.bot.edit_message_text(
                f"✅ Сообщение успешно обработано и сохранено!\n\n"
                f"📁 Файл: `{kb_file.name}`\n"
                f"📂 Категория: `{category_str}`\n"
                f"🏷 Теги: {', '.join(kb_structure.tags) if kb_structure.tags else 'нет'}\n"
                f"🔗 Путь: `{kb_file.relative_to(kb_path)}`",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                parse_mode='Markdown'
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
