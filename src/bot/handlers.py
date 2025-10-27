"""
Telegram Bot Handlers (Refactored)
Handles all incoming message events from Telegram (fully async)
Follows SOLID principles - uses services for business logic
"""

from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.bot_port import BotPort
from src.bot.message_mapper import MessageMapper
from src.bot.settings_manager import SettingsManager
from src.knowledge_base.mkdocs_configurator import MkDocsConfigurator
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.user_settings import UserSettings
from src.processor.message_aggregator import MessageGroup
from src.services.interfaces import IMessageProcessor, IUserContextManager
from src.tracker.processing_tracker import ProcessingTracker


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parsing mode"""
    if not text:
        return text
    
    # Replace HTML special characters
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#x27;")
    return text


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
        async_bot: AsyncTeleBot,
        tracker: ProcessingTracker,
        repo_manager: RepositoryManager,
        user_settings: UserSettings,
        settings_manager: SettingsManager,
        user_context_manager: IUserContextManager,
        message_processor: IMessageProcessor,
        settings_handlers=None,
        kb_handlers=None,
        mcp_handlers=None,
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
            kb_handlers: Knowledge base handlers (optional)
            mcp_handlers: MCP handlers (optional)
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
        self.kb_handlers = kb_handlers
        self.mcp_handlers = mcp_handlers
        self.logger = logger

        # Initialize MkDocs configurator
        self.mkdocs_configurator = MkDocsConfigurator()

        # Set up timeout callback for message processor
        self.user_context_manager.timeout_callback = self._handle_timeout

        self.logger.info("BotHandlers initialized (refactored)")

    async def register_handlers_async(self):
        """Register all bot handlers (async)"""
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
        self.async_bot.message_handler(commands=["setupmkdocs"])(self.handle_setup_mkdocs)

        # Callback query handler for start menu
        self.async_bot.callback_query_handler(func=lambda call: call.data.startswith("start:"))(
            self.handle_start_callback
        )

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

    async def stop_background_tasks(self) -> None:
        """Stop background tasks"""
        self.logger.info("Stopping background tasks")
        # Support both async and sync implementations of cleanup for test doubles
        cleanup = getattr(self.user_context_manager, "cleanup", None)
        if cleanup is None:
            return
        try:
            result = cleanup()
            # If result is awaitable, await it; otherwise it's a sync mock/func
            if hasattr(result, "__await__"):
                await result
        except TypeError:
            # Some mocks may not be awaitable; ignore in that case
            pass

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
        """Handle /start command - show main menu"""
        self.logger.info(f"[HANDLER] Start command from user {message.from_user.id}")

        user_kb = self.user_settings.get_user_kb(message.from_user.id)

        # Create inline keyboard with main menu
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 2

        # First row - KB and Mode
        if user_kb:
            keyboard.add(
                InlineKeyboardButton("📚 База знаний", callback_data="start:kb"),
                InlineKeyboardButton("🔄 Режим работы", callback_data="start:mode"),
            )
        else:
            keyboard.add(
                InlineKeyboardButton("➕ Создать БЗ", callback_data="start:create_kb"),
                InlineKeyboardButton("🔄 Режим работы", callback_data="start:mode"),
            )

        # Second row - Settings and MCP
        keyboard.add(
            InlineKeyboardButton("⚙️ Настройки", callback_data="start:settings"),
            InlineKeyboardButton("🔧 MCP серверы", callback_data="start:mcp"),
        )

        # Third row - Context and Help
        keyboard.add(
            InlineKeyboardButton("💬 Контекст", callback_data="start:context"),
            InlineKeyboardButton("❓ Помощь", callback_data="start:help"),
        )

        welcome_text = (
            "🤖 **Добро пожаловать в tg-note!**\n\n"
            "Этот бот автоматически создает заметки в базе знаний из ваших сообщений и репостов.\n\n"
        )

        if user_kb:
            kb_type_emoji = "🌐" if user_kb["kb_type"] == "github" else "📁"
            welcome_text += f"{kb_type_emoji} **Текущая БЗ:** {_escape_html(user_kb['kb_name'])}\n"
        else:
            welcome_text += "⚠️ **База знаний не настроена**\n" "Начните с создания базы знаний!\n\n"

        current_mode = self.user_context_manager.get_user_mode(message.from_user.id)
        mode_emoji = {"note": "📝", "ask": "🤔", "agent": "🤖"}.get(current_mode, "📝")
        mode_name = {"note": "Создание БЗ", "ask": "Вопросы", "agent": "Агент"}.get(
            current_mode, "Создание БЗ"
        )

        welcome_text += f"{mode_emoji} **Режим:** {mode_name}\n\n"
        welcome_text += "Выберите действие из меню ниже:"
 
        # Store the main menu message ID for future edits
        self._main_menu_message_id = message.message_id
        self._main_menu_chat_id = message.chat.id
 
        try:
            await self.bot.edit_message_text(
                welcome_text,
                message.chat.id,
                message.message_id,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception:
            # If editing fails (e.g., message not found), send a new message
            sent_message = await self.bot.send_message(
                message.chat.id, welcome_text, reply_markup=keyboard, parse_mode="HTML"
            )
            # Update stored message ID for future edits
            self._main_menu_message_id = sent_message.message_id
            self._main_menu_chat_id = sent_message.chat.id

    async def handle_start_callback(self, call: CallbackQuery) -> None:
        """Handle callback queries from start menu"""
        try:
            # Parse callback data
            parts = call.data.split(":", 2)

            if len(parts) < 2:
                await self.bot.answer_callback_query(call.id, "Invalid callback")
                return

            action = parts[1]

            if action == "kb":
                # Open KB menu (delegate to kb_handlers)
                await self.bot.answer_callback_query(call.id)
                # Simulate /kb command
                message = call.message
                message.from_user = call.from_user
                message.text = "/kb"
                if self.kb_handlers:
                    await self.kb_handlers.handle_kb_menu(message)
                else:
                    await self.bot.send_message(call.message.chat.id, "KB handlers not initialized")

            elif action == "create_kb":
                # Create KB (delegate to kb_handlers)
                await self.bot.answer_callback_query(call.id)
                message = call.message
                message.from_user = call.from_user
                message.text = "/kb"
                if self.kb_handlers:
                    await self.kb_handlers.handle_kb_menu(message)
                else:
                    await self.bot.send_message(call.message.chat.id, "KB handlers not initialized")

            elif action == "mode":
                # Show mode selection menu
                await self._show_mode_menu(call)

            elif action == "set_mode":
                # Set mode
                mode = parts[2] if len(parts) > 2 else "note"
                await self._set_mode(call, mode)

            elif action == "settings":
                # Open settings menu (delegate to settings_handlers)
                await self.bot.answer_callback_query(call.id)
                message = call.message
                message.from_user = call.from_user
                message.text = "/settings"
                message.chat = call.message.chat
                if self.settings_handlers:
                    await self.settings_handlers.handle_settings_menu(message)

            elif action == "mcp":
                # Open MCP menu (delegate to mcp_handlers)
                await self.bot.answer_callback_query(call.id)
                message = call.message
                message.from_user = call.from_user
                message.text = "/listmcpservers"
                message.chat = call.message.chat
                if self.mcp_handlers:
                    await self.mcp_handlers.handle_list_mcp_servers(message)
                else:
                    await self.bot.send_message(call.message.chat.id, "MCP handlers not initialized")

            elif action == "context":
                # Show context management menu
                await self._show_context_menu(call)

            elif action == "reset_context":
                # Reset context
                await self._reset_context(call)

            elif action == "help":
                # Show help
                await self.bot.answer_callback_query(call.id)
                message = call.message
                message.from_user = call.from_user
                message.text = "/help"
                await self.handle_help(message)
            elif action == "back_to_main":
                # Return to main menu
                await self.bot.answer_callback_query(call.id)
                await self.handle_start(call.message)

            else:
                await self.bot.answer_callback_query(call.id, "Unknown action")

        except Exception as e:
            self.logger.error(f"Error handling start callback: {e}", exc_info=True)
            await self.bot.answer_callback_query(call.id, f"Error: {str(e)}")

    async def _show_mode_menu(self, call: CallbackQuery) -> None:
        """Show mode selection menu"""
        current_mode = self.user_context_manager.get_user_mode(call.from_user.id)
 
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 1
 
        # Add back button
        keyboard.add(InlineKeyboardButton("« Назад", callback_data="start:back_to_main"))
 
        modes = [
            ("note", "📝 Создание базы знаний", "Сообщения анализируются и сохраняются в БЗ"),
            ("ask", "🤔 Вопросы по БЗ", "Задавайте вопросы о содержимом БЗ"),
            ("agent", "🤖 Агент (полный доступ)", "Агент может выполнять любые задачи с БЗ"),
        ]
 
        text_lines = ["🔄 **Выбор режима работы**\n"]
 
        for mode_id, mode_name, mode_desc in modes:
            if mode_id == current_mode:
                text_lines.append(f"✅ **{mode_name}** (текущий)")
                text_lines.append(f"   _{mode_desc}_\n")
            else:
                text_lines.append(f"• {mode_name}")
                text_lines.append(f"   _{mode_desc}_")
                keyboard.add(
                    InlineKeyboardButton(
                        f"➡️ {mode_name}", callback_data=f"start:set_mode:{mode_id}"
                    )
                )
 
        text = "\n".join(text_lines)
 
        try:
            await self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception:
            await self.bot.send_message(
                call.message.chat.id, text, reply_markup=keyboard, parse_mode="HTML"
            )
 
        await self.bot.answer_callback_query(call.id)

    async def _set_mode(self, call: CallbackQuery, mode: str) -> None:
        """Set user mode"""
        user_kb = self.user_settings.get_user_kb(call.from_user.id)

        # Check if KB is required for this mode
        if mode in ["ask", "agent"] and not user_kb:
            await self.bot.answer_callback_query(
                call.id, "❌ Для этого режима требуется настроенная БЗ", show_alert=True
            )
            return

        self.user_context_manager.set_user_mode(call.from_user.id, mode)

        mode_names = {
            "note": "📝 Создание базы знаний",
            "ask": "🤔 Вопросы по БЗ",
            "agent": "🤖 Агент (полный доступ)",
        }

        await self.bot.answer_callback_query(
            call.id, f"✅ Режим изменен на: {mode_names.get(mode, mode)}", show_alert=True
        )

        # Refresh mode menu
        await self._show_mode_menu(call)

    async def _show_context_menu(self, call: CallbackQuery) -> None:
        """Show context management menu"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 1
 
        # Add back button
        keyboard.add(InlineKeyboardButton("« Назад", callback_data="start:back_to_main"))
 
        keyboard.add(
            InlineKeyboardButton("🔄 Сбросить контекст", callback_data="start:reset_context"),
        )
 
        menu_text = (
            "💬 **Управление контекстом**\n\n"
            "Бот запоминает предыдущие сообщения для более точных ответов.\n\n"
            "**Сброс контекста** очищает историю разговора и начинает новый диалог с чистого листа.\n\n"
            "Настройки контекста доступны в разделе ⚙️ Настройки."
        )
 
        try:
            await self.bot.edit_message_text(
                menu_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception:
            await self.bot.send_message(
                call.message.chat.id, menu_text, reply_markup=keyboard, parse_mode="HTML"
            )
 
        await self.bot.answer_callback_query(call.id)

    async def _reset_context(self, call: CallbackQuery) -> None:
        """Reset conversation context"""
        # Clear conversation context for this user
        self.user_context_manager.clear_conversation_context(call.from_user.id)

        # Set reset point to current message ID
        self.user_context_manager.reset_conversation_context(
            call.from_user.id, call.message.message_id
        )

        await self.bot.answer_callback_query(
            call.id, "🔄 Контекст разговора сброшен!", show_alert=True
        )

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
            "/kb - информация о базе знаний\n"
            "/setupmkdocs - настроить MkDocs для GitHub репозитория\n\n"
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
            if user_kb:
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

        if not user_kb:
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

        if not user_kb:
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

    async def handle_setup_mkdocs(self, message: Message) -> None:
        """
        Handle /setupmkdocs command - configure MkDocs for GitHub knowledge base.

        This command checks if the current knowledge base is GitHub-based and,
        if so, configures MkDocs with all necessary files for building and
        deploying static documentation to GitHub Pages.

        Args:
            message: Telegram message containing the /setupmkdocs command
        """
        self.logger.info(f"[HANDLER] Setup MkDocs command from user {message.from_user.id}")

        # Get user's knowledge base settings
        user_kb = self.user_settings.get_user_kb(message.from_user.id)

        if not user_kb:
            await self.bot.reply_to(
                message,
                "❌ База знаний не настроена\n\n"
                "Используйте /setkb для настройки базы знаний перед настройкой MkDocs.",
            )
            return

        # Check if KB is GitHub-based
        if user_kb["kb_type"] != "github":
            await self.bot.reply_to(
                message,
                "❌ Эта команда работает только с GitHub-репозиториями\n\n"
                f"Ваша текущая база знаний '{user_kb['kb_name']}' имеет тип: {user_kb['kb_type']}\n\n"
                "Используйте /setkb <github_url> для настройки GitHub репозитория.",
            )
            return

        # Get KB path
        kb_path = self.repo_manager.get_kb_path(user_kb["kb_name"])
        if not kb_path:
            await self.bot.reply_to(
                message,
                "❌ Локальная копия базы знаний не найдена\n\n"
                "Попробуйте заново настроить базу знаний с помощью /setkb",
            )
            return

        # Check if MkDocs is already configured
        if self.mkdocs_configurator.is_mkdocs_configured(kb_path):
            await self.bot.reply_to(
                message,
                "ℹ️ MkDocs уже настроен для этой базы знаний\n\n"
                f"Найден файл: {kb_path / 'mkdocs.yml'}\n\n"
                "Если вы хотите перенастроить MkDocs, удалите файл mkdocs.yml и запустите команду снова.",
            )
            return

        # Send processing message
        processing_msg = await self.bot.reply_to(message, "⏳ Настраиваю MkDocs для базы знаний...")

        # Configure MkDocs
        success, result_message = self.mkdocs_configurator.configure_mkdocs(
            kb_path=kb_path,
            kb_name=user_kb["kb_name"],
            github_url=user_kb.get("github_url", ""),
        )

        # Delete processing message
        try:
            await self.bot.delete_message(message.chat.id, processing_msg.message_id)
        except Exception:
            pass

        # Send result
        await self.bot.reply_to(message, result_message)

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

        # Convert Telegram message to DTO
        message_dto = MessageMapper.from_telegram_message(message)

        # Process message regardless of content type
        await self.message_processor.process_message(message_dto)

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

        # Convert Telegram message to DTO
        message_dto = MessageMapper.from_telegram_message(message)

        # Process message regardless of content type
        await self.message_processor.process_message(message_dto)
