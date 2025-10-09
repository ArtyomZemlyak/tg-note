"""
Telegram Bot Handlers (Refactored)
Handles all incoming message events from Telegram (fully async)
Follows SOLID principles - uses services for business logic
"""

from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message
from typing import Optional

from src.bot.bot_port import BotPort
from src.bot.message_mapper import MessageMapper
from src.bot.settings_manager import SettingsManager
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.user_settings import UserSettings
from src.processor.message_aggregator import MessageGroup
from src.services.interfaces import IMessageProcessor, IUserContextManager
from src.tracker.processing_tracker import ProcessingTracker


class BotHandlers:
    """
    Telegram bot message handlers (refactored with SOLID principles)

    Responsibilities (reduced to coordination only):
    - Register message handlers with Telegram bot
    - Route commands to appropriate handlers
    - Delegate business logic to services
    """

    def __init__(
        self,
        bot: BotPort,
        async_bot: Optional[AsyncTeleBot] = None,
        tracker: ProcessingTracker = None,
        repo_manager: RepositoryManager = None,
        user_settings: UserSettings = None,
        settings_manager: SettingsManager = None,
        user_context_manager: IUserContextManager = None,
        message_processor: IMessageProcessor = None,
        settings_handlers=None,
    ):
        """
        Initialize bot handlers

        Args:
            bot: Bot messaging interface (transport abstraction)
            async_bot: Telegram bot instance (for handler registration)
            tracker: Processing tracker
            repo_manager: Repository manager
            user_settings: User settings
            settings_manager: Settings manager
            user_context_manager: User context manager service
            message_processor: Message processor service
            settings_handlers: Settings handlers (optional)
        """
        self.bot = bot
        self.async_bot = async_bot
        self.tracker = tracker
        self.repo_manager = repo_manager
        self.user_settings = user_settings
        self.settings_manager = settings_manager
        self.user_context_manager = user_context_manager
        self.message_processor = message_processor
        self.settings_handlers = settings_handlers
        self.logger = logger

        # Set up timeout callback for message processor
        self.user_context_manager.timeout_callback = self._handle_timeout

        self.logger.info("BotHandlers initialized (refactored)")

    async def register_handlers_async(self):
        """Register all bot handlers (async)"""
        if not self.async_bot:
            # Nothing to register if transport bot is not provided (used in unit tests)
            return

        # Command handlers
        self.async_bot.message_handler(commands=["start"])(self.handle_start)
        self.async_bot.message_handler(commands=["help"])(self.handle_help)
        self.async_bot.message_handler(commands=["status"])(self.handle_status)
        self.async_bot.message_handler(commands=["setkb"])(self.handle_setkb)
        self.async_bot.message_handler(commands=["kb"])(self.handle_kb_info)
        self.async_bot.message_handler(commands=["note"])(self.handle_note_mode)
        self.async_bot.message_handler(commands=["ask"])(self.handle_ask_mode)
        self.async_bot.message_handler(commands=["agent"])(self.handle_agent_mode)
        self.async_bot.message_handler(commands=["resetcontext"])(self.handle_reset_context)

        # All supported content types (decoupled from media processing)
        supported_content_types = [
            "text",
            "photo",
            "document",
            "video",
            "audio",
            "voice",
            "video_note",
            "animation",
            "sticker",
        ]

        # Forwarded messages (all content types)
        self.async_bot.message_handler(
            content_types=supported_content_types, func=lambda m: self._is_forwarded_message(m)
        )(self.handle_forwarded_message)

        # Regular messages (all content types, unified handler)
        self.async_bot.message_handler(
            content_types=supported_content_types,
            func=lambda m: not self._is_forwarded_message(m) and not self._is_command_message(m),
        )(self.handle_message)

    def _is_forwarded_message(self, message: Message) -> bool:
        """Check if message is forwarded"""
        if message.forward_date is not None and message.forward_date > 0:
            return True
        return bool(
            message.forward_from
            or message.forward_from_chat
            or (message.forward_sender_name and message.forward_sender_name.strip())
        )

    def _is_command_message(self, message: Message) -> bool:
        """Check if message is a command"""
        return message.text and message.text.startswith("/")

    async def invalidate_user_cache(self, user_id: int) -> None:
        """Invalidate cached user-specific components"""
        await self.user_context_manager.invalidate_cache(user_id)

    def start_background_tasks(self) -> None:
        """Start background tasks"""
        self.logger.info("Starting background tasks")

    def stop_background_tasks(self) -> None:
        """Stop background tasks (synchronous for test friendliness)"""
        self.logger.info("Stopping background tasks")
        try:
            # In tests cleanup can be a regular Mock
            result = self.user_context_manager.cleanup()
            # If coroutine returned, schedule fire-and-forget to avoid await in tests
            import asyncio

            if asyncio.iscoroutine(result):
                asyncio.get_event_loop().create_task(result)
        except Exception as e:
            self.logger.warning(f"Error stopping background tasks: {e}")

    async def _handle_timeout(self, chat_id: int, group: MessageGroup) -> None:
        """Handle timed-out message group"""
        try:
            self.logger.info(
                f"[HANDLER] Processing timed-out group for chat {chat_id} "
                f"with {len(group.messages)} messages"
            )

            processing_msg = await self.bot.send_message(
                chat_id, "🔄 Обрабатываю завершенную группу сообщений..."
            )

            await self.message_processor.process_message_group(
                group, processing_msg.message_id, chat_id
            )

        except Exception as e:
            self.logger.error(
                f"Error handling timed-out group for chat {chat_id}: {e}", exc_info=True
            )

    # Command handlers

    async def handle_start(self, message: Message) -> None:
        """Handle /start command - welcome message"""
        self.logger.info(f"[HANDLER] Start command from user {message.from_user.id}")

        welcome_text = (
            "🤖 Добро пожаловать в tg-note!\n\n"
            "Этот бот автоматически создает заметки в базе знаний из ваших сообщений и репостов.\n\n"
            "Просто отправьте мне:\n"
            "• Текстовые сообщения\n"
            "• Репосты новостей или статей\n"
            "• Фотографии с подписями\n"
            "• Документы\n"
            "• Видео с описанием\n"
            "• Голосовые сообщения\n"
            "• Аудио файлы\n\n"
            "Бот проанализирует контент и сохранит важную информацию в базу знаний.\n\n"
            "Команды:\n"
            "/help - показать справку\n"
            "/status - показать статистику обработки\n\n"
            "Режимы работы:\n"
            "/note - режим создания базы знаний (по умолчанию)\n"
            "/ask - режим вопросов по базе знаний\n"
            "/agent - режим агента (полный доступ)"
        )

        await self.bot.reply_to(message, welcome_text)

    async def handle_help(self, message: Message) -> None:
        """Handle /help command - show help text"""
        self.logger.info(f"[HANDLER] Help command from user {message.from_user.id}")

        help_text = (
            "📚 Справка по tg-note\n\n"
            "Бот автоматически обрабатывает ваши сообщения и создает заметки в базе знаний.\n\n"
            "Поддерживаемые типы контента:\n"
            "• 📝 Текстовые сообщения\n"
            "• 🔄 Репосты (forwarded messages)\n"
            "• 📷 Фотографии с подписями\n"
            "• 📄 Документы (PDF, DOCX, PPTX, XLSX и др.)\n"
            "• 🎥 Видео с описанием (текст извлекается)\n"
            "• 🎵 Аудио файлы (текст извлекается)\n"
            "• 🎤 Голосовые сообщения (текст извлекается)\n\n"
            "Как это работает:\n"
            "1. Отправьте сообщение или репост\n"
            "2. Бот проанализирует контент\n"
            "3. Извлечет ключевую информацию\n"
            "4. Сохранит в базу знаний в формате Markdown\n\n"
            "⚠️ Примечание: Для видео, аудио и голосовых сообщений пока извлекается только текст/подпись. "
            "Полная обработка медиа будет добавлена в будущем.\n\n"
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
            "**MCP серверы:**\n"
            "/addmcpserver - добавить новый MCP сервер\n"
            "/listmcpservers - список всех MCP серверов\n"
            "/mcpstatus - статус MCP серверов\n"
            "/enablemcp <name> - включить MCP сервер\n"
            "/disablemcp <name> - выключить MCP сервер\n"
            "/removemcp <name> - удалить MCP сервер\n\n"
            "**Режимы работы:**\n"
            "/note - режим создания базы знаний (по умолчанию)\n"
            "  В этом режиме бот анализирует ваши сообщения и создает заметки\n\n"
            "/ask - режим вопросов по базе знаний\n"
            "  В этом режиме вы можете задавать вопросы агенту о содержимом базы знаний\n\n"
            "/agent - режим агента (полный доступ)\n"
            "  В этом режиме агент выполняет любые задачи: отвечает на вопросы,\n"
            "  добавляет информацию, переструктурирует базу знаний и т.д.\n\n"
            "**Контекст разговора:**\n"
            "/resetcontext - сбросить контекст разговора\n"
            "  Бот запоминает предыдущие сообщения для более точных ответов.\n"
            "  Используйте эту команду, чтобы начать новый разговор с чистого листа.\n\n"
            "Бот работает для всех пользователей без ограничений!"
        )

        await self.bot.reply_to(message, help_text)

    async def handle_status(self, message: Message) -> None:
        """Handle /status command - show bot status and statistics"""
        self.logger.info(f"[HANDLER] Status command from user {message.from_user.id}")

        try:
            stats = self.tracker.get_stats()
            user_kb = self.user_settings.get_user_kb(message.from_user.id)

            kb_info = "Не настроена (используйте /setkb)"
            if isinstance(user_kb, dict) and user_kb.get("kb_name") and user_kb.get("kb_type"):
                kb_info = f"{user_kb['kb_name']} ({user_kb['kb_type']})"

            kb_git_enabled = self.settings_manager.get_setting(
                message.from_user.id, "KB_GIT_ENABLED"
            )
            current_mode = self.user_context_manager.get_user_mode(message.from_user.id)

            # Determine mode emoji and name
            if current_mode == "note":
                mode_emoji = "📝"
                mode_name = "Создание базы знаний"
            elif current_mode == "ask":
                mode_emoji = "🤔"
                mode_name = "Вопросы по базе знаний"
            else:  # agent mode
                mode_emoji = "🤖"
                mode_name = "Агент (полный доступ)"

            status_text = (
                f"📊 Статистика обработки\n\n"
                f"Всего обработано сообщений: {stats['total_processed']}\n"
                f"Ожидает обработки: {stats['pending_groups']}\n"
                f"Последняя обработка: {stats.get('last_processed', 'Никогда')}\n\n"
                f"База знаний: {kb_info}\n"
                f"Git интеграция: {'Включена' if kb_git_enabled else 'Отключена'}\n\n"
                f"{mode_emoji} Текущий режим: {mode_name}\n"
                f"Переключить: /note | /ask | /agent"
            )
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            status_text = "❌ Ошибка получения статистики"

        await self.bot.reply_to(message, status_text)

    async def handle_setkb(self, message: Message) -> None:
        """Handle /setkb command - configure knowledge base"""
        self.logger.info(f"[HANDLER] Setkb command from user {message.from_user.id}")

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

        if (
            kb_input.startswith("http://")
            or kb_input.startswith("https://")
            or kb_input.startswith("git@")
        ):
            success, msg, kb_path = self.repo_manager.clone_github_kb(kb_input)

            if success:
                kb_name = kb_path.name
                self.user_settings.set_user_kb(
                    message.from_user.id, kb_name, kb_type="github", github_url=kb_input
                )
                await self.bot.reply_to(
                    message, f"✅ {msg}\n\nРепозиторий: {kb_input}\nЛокальный путь: {kb_path}"
                )
            else:
                await self.bot.reply_to(message, f"❌ {msg}")
        else:
            success, msg, kb_path = self.repo_manager.init_local_kb(kb_input)

            if success:
                self.user_settings.set_user_kb(message.from_user.id, kb_input, kb_type="local")
                await self.bot.reply_to(
                    message,
                    f"✅ {msg}\n\nЛокальный путь: {kb_path}\n" f"Инициализирован git репозиторий",
                )
            else:
                await self.bot.reply_to(message, f"❌ {msg}")

    async def handle_kb_info(self, message: Message) -> None:
        """Handle /kb command - show knowledge base information"""
        self.logger.info(f"[HANDLER] KB info command from user {message.from_user.id}")

        user_kb = self.user_settings.get_user_kb(message.from_user.id)

        if not user_kb:
            await self.bot.reply_to(
                message, "❌ База знаний не настроена\n\nИспользуйте /setkb для настройки"
            )
            return

        kb_path = self.repo_manager.get_kb_path(user_kb["kb_name"])

        info_text = (
            f"📚 Информация о базе знаний\n\n"
            f"Название: {user_kb['kb_name']}\n"
            f"Тип: {user_kb['kb_type']}\n"
        )

        if user_kb["kb_type"] == "github":
            info_text += f"GitHub: {user_kb.get('github_url', 'N/A')}\n"

        if kb_path:
            info_text += f"Локальный путь: {kb_path}\n"
        else:
            info_text += "⚠️ Локальная копия не найдена\n"

        await self.bot.reply_to(message, info_text)

    async def handle_note_mode(self, message: Message) -> None:
        """
        Handle /note command - activate note creation mode.

        In this mode, user messages are analyzed and saved to the knowledge base.
        The bot extracts key information and structures it as markdown notes.

        Args:
            message: Telegram message containing the /note command
        """
        self.logger.info(f"[HANDLER] Note mode command from user {message.from_user.id}")

        self.user_context_manager.set_user_mode(message.from_user.id, "note")

        await self.bot.reply_to(
            message,
            "📝 Режим создания базы знаний активирован!\n\n"
            "Теперь ваши сообщения будут анализироваться и сохраняться в базу знаний.\n"
            "Отправьте сообщение, репост или документ для обработки.\n\n"
            "Переключить: /ask | /agent",
        )

    async def handle_ask_mode(self, message: Message) -> None:
        """
        Handle /ask command - activate question answering mode.

        In this mode, the agent searches the knowledge base to answer user questions.
        Requires a configured knowledge base (/setkb).

        Args:
            message: Telegram message containing the /ask command
        """
        self.logger.info(f"[HANDLER] Ask mode command from user {message.from_user.id}")

        user_kb = self.user_settings.get_user_kb(message.from_user.id)

        # Treat non-dict or missing fields as not configured
        if not (isinstance(user_kb, dict) and user_kb.get("kb_name")):
            await self.bot.reply_to(
                message,
                "❌ База знаний не настроена\n\n"
                "Используйте /setkb для настройки базы знаний перед использованием режима вопросов.",
            )
            return

        self.user_context_manager.set_user_mode(message.from_user.id, "ask")

        await self.bot.reply_to(
            message,
            "🤔 Режим вопросов по базе знаний активирован!\n\n"
            "Теперь вы можете задавать вопросы агенту о содержимом вашей базы знаний.\n"
            "Агент будет искать информацию в базе и отвечать на ваши вопросы.\n\n"
            "Переключить: /note | /agent",
        )

    async def handle_agent_mode(self, message: Message) -> None:
        """
        Handle /agent command - activate autonomous agent mode.

        In this mode, the agent has full access to the knowledge base and can:
        - Answer questions
        - Add new information
        - Edit existing notes
        - Restructure the knowledge base
        - Perform any KB-related tasks autonomously

        Requires a configured knowledge base (/setkb).

        Args:
            message: Telegram message containing the /agent command
        """
        self.logger.info(f"[HANDLER] Agent mode command from user {message.from_user.id}")

        user_kb = self.user_settings.get_user_kb(message.from_user.id)

        # Treat non-dict or missing fields as not configured
        if not (isinstance(user_kb, dict) and user_kb.get("kb_name")):
            await self.bot.reply_to(
                message,
                "❌ База знаний не настроена\n\n"
                "Используйте /setkb для настройки базы знаний перед использованием режима агента.",
            )
            return

        self.user_context_manager.set_user_mode(message.from_user.id, "agent")

        await self.bot.reply_to(
            message,
            "🤖 Режим агента активирован!\n\n"
            "Теперь агент может выполнять любые задачи с вашей базой знаний:\n"
            "• Отвечать на вопросы\n"
            "• Добавлять новую информацию\n"
            "• Редактировать существующие заметки\n"
            "• Переструктурировать базу знаний\n"
            "• И многое другое!\n\n"
            "Просто опишите что нужно сделать, и агент выполнит задачу автономно.\n\n"
            "Переключить: /note | /ask",
        )

    async def handle_reset_context(self, message: Message) -> None:
        """Handle /resetcontext command - clear conversation context"""
        self.logger.info(f"[HANDLER] Reset context command from user {message.from_user.id}")

        # Clear conversation context for this user
        self.user_context_manager.clear_conversation_context(message.from_user.id)

        # Set reset point to current message ID
        # Future messages will start a new context from here
        self.user_context_manager.reset_conversation_context(
            message.from_user.id, message.message_id
        )

        await self.bot.reply_to(
            message,
            "🔄 Контекст разговора сброшен!\n\n"
            "Новый контекст будет начинаться со следующего сообщения.\n\n"
            "Настройки контекста:\n"
            "• Используйте /settings для управления настройками контекста\n"
            "• CONTEXT_ENABLED - включить/выключить использование контекста\n"
            "• CONTEXT_MAX_TOKENS - максимальное количество токенов в контексте",
        )

    # Message handlers

    async def handle_message(self, message: Message) -> None:
        """
        Handle all regular messages (unified handler for all content types).

        Routes messages to appropriate service based on current user mode.

        Args:
            message: Telegram message to process
        """
        # Skip if waiting for settings input
        if (
            self.settings_handlers
            and message.from_user.id in self.settings_handlers.waiting_for_input
        ):
            # Only accept text input in settings mode
            if message.content_type != "text":
                await self.bot.reply_to(
                    message,
                    "⚠️ Вы находитесь в режиме настроек. Пожалуйста, отправьте текстовое значение.\n"
                    "Используйте /cancel для отмены.",
                )
                return
            else:
                # Let settings handler process text input
                self.logger.info(
                    f"Skipping text message from user {message.from_user.id} "
                    f"- waiting for settings input"
                )
                return

        # Log message info
        content_type = message.content_type
        log_msg = f"[HANDLER] {content_type.capitalize()} message from user {message.from_user.id}"
        if content_type == "text" and message.text:
            log_msg += f": {message.text[:50]}..."
        self.logger.info(log_msg)

        # For compatibility with existing tests, pass original message object
        await self.message_processor.process_message(message)

    async def handle_forwarded_message(self, message: Message) -> None:
        """
        Handle forwarded messages (all content types).

        Routes forwarded messages to message processor.

        Args:
            message: Forwarded Telegram message to process
        """
        # Skip if waiting for settings input
        if (
            self.settings_handlers
            and message.from_user.id in self.settings_handlers.waiting_for_input
        ):
            await self.bot.reply_to(
                message,
                "⚠️ Вы находитесь в режиме настроек. Пересланные сообщения игнорируются.\n"
                "Отправьте текстовое значение или используйте /cancel для отмены.",
            )
            return

        # Log message info
        content_type = message.content_type
        self.logger.info(
            f"[HANDLER] Forwarded {content_type} message from user {message.from_user.id}"
        )

        # For compatibility with existing tests, pass original message object
        await self.message_processor.process_message(message)
