"""
Knowledge Base Handlers for Telegram Bot
Provides button-based interface for managing knowledge bases
"""

from pathlib import Path
from typing import Dict, Optional

from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.utils import escape_markdown
from src.bot.handlers import _escape_html
from src.knowledge_base.mkdocs_configurator import MkDocsConfigurator
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.user_settings import UserSettings


class KBHandlers:
    """Telegram handlers for knowledge base management"""

    def __init__(
        self,
        bot: AsyncTeleBot,
        repo_manager: RepositoryManager,
        user_settings: UserSettings,
    ):
        """
        Initialize KB handlers

        Args:
            bot: Telegram bot instance
            repo_manager: Repository manager for KB operations
            user_settings: User settings manager
        """
        self.bot = bot
        self.repo_manager = repo_manager
        self.user_settings = user_settings
        self.mkdocs_configurator = MkDocsConfigurator()

        # Track users waiting for input: user_id -> waiting_for_type
        self.waiting_for_input: Dict[int, str] = {}

    async def register_handlers_async(self):
        """Register all KB handlers"""
        # KB management commands
        self.bot.message_handler(commands=["kb"])(self.handle_kb_menu)

        # Text message handler for KB name input
        self.bot.message_handler(func=lambda m: m.from_user.id in self.waiting_for_input)(
            self.handle_kb_input
        )

        # Callback query handlers for inline keyboards
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("kb:"))(
            self.handle_kb_callback
        )

    async def handle_kb_menu(self, message: Message) -> None:
        """Handle /kb command - show KB management menu"""
        logger.info(f"KB menu requested by user {message.from_user.id}")

        user_kb = self.user_settings.get_user_kb(message.from_user.id)

        if user_kb:
            # User has a KB - show KB management options
            await self._show_kb_management_menu(message, user_kb)
        else:
            # No KB - show creation menu
            await self._show_kb_creation_menu(message)

    async def _show_kb_creation_menu(self, message: Message) -> None:
        """Show menu for creating a new knowledge base"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 1
 
        # Add back button
        keyboard.add(InlineKeyboardButton("« Назад", callback_data="kb:back_to_main"))
 
        keyboard.add(
            InlineKeyboardButton("📁 Создать локальную БЗ", callback_data="kb:create_local"),
            InlineKeyboardButton(
                "🌐 Подключить GitHub репозиторий", callback_data="kb:create_github"
            ),
        )
 
        menu_text = (
            "📚 **Управление базой знаний**\n\n"
            "У вас пока нет настроенной базы знаний.\n\n"
            "Выберите, что хотите сделать:\n"
            "• **Локальная БЗ** - создается на сервере, можно позже связать с Git\n"
            "• **GitHub репозиторий** - клонируется с GitHub для совместной работы"
        )
 
        await self.bot.send_message(
            message.chat.id, menu_text, reply_markup=keyboard, parse_mode="HTML"
        )

    async def _show_kb_management_menu(self, message: Message, user_kb: Dict) -> None:
        """Show management menu for existing knowledge base"""
        kb_path = self.repo_manager.get_kb_path(user_kb["kb_name"])
 
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 1
 
        # Add back button
        keyboard.add(InlineKeyboardButton("« Назад", callback_data="kb:back_to_main"))
 
        keyboard.add(
            InlineKeyboardButton("ℹ️ Информация о БЗ", callback_data="kb:info"),
            InlineKeyboardButton("🔄 Переключить на другую БЗ", callback_data="kb:switch"),
            InlineKeyboardButton("➕ Создать новую БЗ", callback_data="kb:create_new"),
        )
 
        # Add MkDocs setup button for GitHub repos
        if user_kb["kb_type"] == "github":
            is_mkdocs_configured = False
            if kb_path and self.mkdocs_configurator.is_mkdocs_configured(kb_path):
                is_mkdocs_configured = True
 
            if not is_mkdocs_configured:
                keyboard.add(
                    InlineKeyboardButton(
                        "📖 Настроить документацию (MkDocs)", callback_data="kb:setup_mkdocs"
                    )
                )
 
        # Prepare KB info text
        kb_type_emoji = "🌐" if user_kb["kb_type"] == "github" else "📁"
        kb_type_text = "GitHub репозиторий" if user_kb["kb_type"] == "github" else "Локальная"
 
        menu_text = (
            f"📚 **Текущая база знаний**\n\n"
            f"{kb_type_emoji} **Название:** {_escape_html(user_kb['kb_name'])}\n"
            f"**Тип:** {kb_type_text}\n"
        )
 
        if user_kb["kb_type"] == "github" and user_kb.get("github_url"):
            menu_text += f"**URL:** {_escape_html(user_kb['github_url'])}\n"
 
        if kb_path:
            menu_text += f"**Путь:** `{escape_markdown(str(kb_path))}`\n"
 
        menu_text += "\nВыберите действие:"
 
        await self.bot.send_message(
            message.chat.id, menu_text, reply_markup=keyboard, parse_mode="HTML"
        )

    async def handle_kb_callback(self, call: CallbackQuery) -> None:
        """Handle callback queries from KB inline keyboards"""
        try:
            # Parse callback data
            parts = call.data.split(":", 2)

            if len(parts) < 2:
                await self.bot.answer_callback_query(call.id, "Invalid callback")
                return

            action = parts[1]

            if action == "create_local":
                # Prompt for local KB name
                await self._prompt_for_kb_name(call, "local")

            elif action == "create_github":
                # Prompt for GitHub URL
                await self._prompt_for_github_url(call)

            elif action == "create_new":
                # Show creation menu again
                await self._show_kb_creation_menu_callback(call)

            elif action == "info":
                # Show KB information
                await self._show_kb_info(call)

            elif action == "switch":
                # Show list of available KBs
                await self._show_kb_list(call)

            elif action == "switch_to":
                # Switch to specific KB
                kb_name = parts[2] if len(parts) > 2 else None
                if kb_name:
                    await self._switch_to_kb(call, kb_name)

            elif action == "setup_mkdocs":
                # Setup MkDocs for GitHub repo
                await self._setup_mkdocs(call)

            elif action == "back_to_menu":
                # Go back to main KB menu
                await self._back_to_kb_menu(call)
            elif action == "back_to_main":
                # Return to main menu
                await self.bot.answer_callback_query(call.id)
                # Simulate /start command
                message = call.message
                message.from_user = call.from_user
                message.text = "/start"
                if self.handlers:
                    await self.handlers.handle_start(message)
                else:
                    await self.bot.send_message(call.message.chat.id, "Main handlers not initialized")

            else:
                await self.bot.answer_callback_query(call.id, "Unknown action")

        except Exception as e:
            logger.error(f"Error handling KB callback: {e}", exc_info=True)
            await self.bot.answer_callback_query(call.id, f"Error: {str(e)}")

    async def _prompt_for_kb_name(self, call: CallbackQuery, kb_type: str) -> None:
        """Prompt user to enter KB name"""
        user_id = call.from_user.id
        self.waiting_for_input[user_id] = f"create_{kb_type}"

        prompt_text = (
            "📝 **Создание локальной базы знаний**\n\n"
            "Введите название для новой базы знаний (например: `my-notes`)\n\n"
            "Название может содержать латинские буквы, цифры, дефисы и подчеркивания.\n\n"
            "Отправьте /cancel для отмены."
        )

        await self.bot.send_message(call.message.chat.id, prompt_text, parse_mode="HTML")
        await self.bot.answer_callback_query(call.id)

    async def _prompt_for_github_url(self, call: CallbackQuery) -> None:
        """Prompt user to enter GitHub URL"""
        user_id = call.from_user.id
        self.waiting_for_input[user_id] = "create_github"

        prompt_text = (
            "🌐 **Подключение GitHub репозитория**\n\n"
            "Введите URL GitHub репозитория:\n\n"
            "**Примеры:**\n"
            "```\n"
            "https://github.com/username/repo-name\n"
            "git@github.com:username/repo-name.git\n"
            "```\n\n"
            "Отправьте /cancel для отмены."
        )

        await self.bot.send_message(call.message.chat.id, prompt_text, parse_mode="HTML")
        await self.bot.answer_callback_query(call.id)

    async def handle_kb_input(self, message: Message) -> None:
        """Handle text input for KB operations"""
        user_id = message.from_user.id

        # Check if user is waiting for input
        if user_id not in self.waiting_for_input:
            return

        # Check for cancel
        if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
            del self.waiting_for_input[user_id]
            await self.bot.reply_to(message, "❌ Отменено")
            return

        waiting_for = self.waiting_for_input[user_id]
        input_text = message.text.strip()

        # Clear waiting state
        del self.waiting_for_input[user_id]

        if waiting_for == "create_local":
            await self._create_local_kb(message, input_text)
        elif waiting_for == "create_github":
            await self._create_github_kb(message, input_text)

    async def _create_local_kb(self, message: Message, kb_name: str) -> None:
        """Create a local knowledge base"""
        processing_msg = await self.bot.reply_to(message, "⏳ Создаю локальную базу знаний...")

        try:
            success, msg, kb_path = self.repo_manager.init_local_kb(kb_name)

            # Delete processing message
            try:
                await self.bot.delete_message(message.chat.id, processing_msg.message_id)
            except Exception:
                pass

            if success:
                self.user_settings.set_user_kb(message.from_user.id, kb_name, kb_type="local")

                result_text = (
                    f"✅ {msg}\n\n"
                    f"📁 **Название:** {kb_name}\n"
                    f"📂 **Путь:** `{escape_markdown(str(kb_path))}`\n"
                    f"🔧 **Git:** Инициализирован\n\n"
                    f"Теперь можете отправлять сообщения, и они будут сохраняться в эту базу знаний!"
                )

                await self.bot.reply_to(message, result_text, parse_mode="HTML")
            else:
                await self.bot.reply_to(message, f"❌ {msg}")

        except Exception as e:
            logger.error(f"Error creating local KB: {e}", exc_info=True)
            await self.bot.reply_to(message, f"❌ Ошибка: {str(e)}")

    async def _create_github_kb(self, message: Message, github_url: str) -> None:
        """Create/clone a GitHub knowledge base"""
        processing_msg = await self.bot.reply_to(message, "⏳ Клонирую репозиторий с GitHub...")

        try:
            success, msg, kb_path = self.repo_manager.clone_github_kb(github_url)

            # Delete processing message
            try:
                await self.bot.delete_message(message.chat.id, processing_msg.message_id)
            except Exception:
                pass

            if success:
                kb_name = kb_path.name
                self.user_settings.set_user_kb(
                    message.from_user.id, kb_name, kb_type="github", github_url=github_url
                )

                result_text = (
                    f"✅ {msg}\n\n"
                    f"🌐 **Репозиторий:** {github_url}\n"
                    f"📂 **Локальный путь:** `{escape_markdown(str(kb_path))}`\n\n"
                    f"Теперь можете отправлять сообщения, и они будут сохраняться в этот репозиторий!"
                )

                await self.bot.reply_to(message, result_text, parse_mode="HTML")
            else:
                await self.bot.reply_to(message, f"❌ {msg}")

        except Exception as e:
            logger.error(f"Error creating GitHub KB: {e}", exc_info=True)
            await self.bot.reply_to(message, f"❌ Ошибка: {str(e)}")

    async def _show_kb_info(self, call: CallbackQuery) -> None:
        """Show detailed KB information"""
        user_kb = self.user_settings.get_user_kb(call.from_user.id)

        if not user_kb:
            await self.bot.answer_callback_query(call.id, "❌ БЗ не настроена", show_alert=True)
            return

        kb_path = self.repo_manager.get_kb_path(user_kb["kb_name"])

        kb_type_emoji = "🌐" if user_kb["kb_type"] == "github" else "📁"
        kb_type_text = "GitHub репозиторий" if user_kb["kb_type"] == "github" else "Локальная"

        info_lines = [
            "ℹ️ **Информация о базе знаний**\n",
            f"{kb_type_emoji} **Название:** {_escape_html(user_kb['kb_name'])}",
            f"**Тип:** {kb_type_text}",
        ]

        if user_kb["kb_type"] == "github" and user_kb.get("github_url"):
            info_lines.append(f"**GitHub URL:** {_escape_html(user_kb['github_url'])}")

        if kb_path:
            info_lines.append(f"**Локальный путь:** `{escape_markdown(str(kb_path))}`")

            # Check if MkDocs is configured
            if user_kb["kb_type"] == "github":
                is_mkdocs = self.mkdocs_configurator.is_mkdocs_configured(kb_path)
                mkdocs_status = "✅ Настроен" if is_mkdocs else "❌ Не настроен"
                info_lines.append(f"**MkDocs:** {mkdocs_status}")
        else:
            info_lines.append("⚠️ **Локальная копия не найдена**")

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("« Назад", callback_data="kb:back_to_menu"))

        info_text = "\n".join(info_lines)

        try:
            await self.bot.edit_message_text(
                info_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception:
            # If editing fails, send new message
            await self.bot.send_message(
                call.message.chat.id, info_text, reply_markup=keyboard, parse_mode="HTML"
            )

        await self.bot.answer_callback_query(call.id)

    async def _show_kb_list(self, call: CallbackQuery) -> None:
        """Show list of available knowledge bases"""
        # Get all KBs from the kb_root directory
        kb_root = self.repo_manager.kb_root
        available_kbs = []

        if kb_root.exists():
            for kb_dir in kb_root.iterdir():
                if kb_dir.is_dir() and not kb_dir.name.startswith("."):
                    available_kbs.append(kb_dir.name)

        if not available_kbs:
            await self.bot.answer_callback_query(
                call.id, "❌ Нет доступных баз знаний", show_alert=True
            )
            return

        current_kb = self.user_settings.get_user_kb(call.from_user.id)
        current_kb_name = current_kb["kb_name"] if current_kb else None

        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 1

        text_lines = ["📚 **Доступные базы знаний**\n"]

        for kb_name in sorted(available_kbs):
            if kb_name == current_kb_name:
                text_lines.append(f"✅ **{kb_name}** (текущая)")
            else:
                text_lines.append(f"• {kb_name}")
                keyboard.add(
                    InlineKeyboardButton(
                        f"➡️ Переключиться на {kb_name}", callback_data=f"kb:switch_to:{kb_name}"
                    )
                )

        keyboard.add(InlineKeyboardButton("« Назад", callback_data="kb:back_to_menu"))

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

    async def _switch_to_kb(self, call: CallbackQuery, kb_name: str) -> None:
        """Switch to a different knowledge base"""
        kb_path = self.repo_manager.get_kb_path(kb_name)

        if not kb_path or not kb_path.exists():
            await self.bot.answer_callback_query(
                call.id, f"❌ БЗ {kb_name} не найдена", show_alert=True
            )
            return

        # Determine KB type by checking if it has a remote origin
        kb_type = "local"
        github_url = None

        try:
            from git import Repo

            repo = Repo(kb_path)
            if repo.remotes:
                kb_type = "github"
                github_url = repo.remotes.origin.url
        except Exception:
            pass

        # Update user settings
        self.user_settings.set_user_kb(
            call.from_user.id, kb_name, kb_type=kb_type, github_url=github_url
        )

        await self.bot.answer_callback_query(
            call.id, f"✅ Переключено на БЗ: {kb_name}", show_alert=True
        )

        # Refresh menu
        await self._back_to_kb_menu(call)

    async def _setup_mkdocs(self, call: CallbackQuery) -> None:
        """Setup MkDocs for GitHub knowledge base"""
        user_kb = self.user_settings.get_user_kb(call.from_user.id)

        if not user_kb:
            await self.bot.answer_callback_query(call.id, "❌ БЗ не настроена", show_alert=True)
            return

        if user_kb["kb_type"] != "github":
            await self.bot.answer_callback_query(
                call.id, "❌ MkDocs доступен только для GitHub репозиториев", show_alert=True
            )
            return

        kb_path = self.repo_manager.get_kb_path(user_kb["kb_name"])

        if not kb_path:
            await self.bot.answer_callback_query(
                call.id, "❌ Локальная копия БЗ не найдена", show_alert=True
            )
            return

        # Check if already configured
        if self.mkdocs_configurator.is_mkdocs_configured(kb_path):
            await self.bot.answer_callback_query(call.id, "ℹ️ MkDocs уже настроен", show_alert=True)
            return

        await self.bot.answer_callback_query(call.id)

        # Send processing message
        processing_msg = await self.bot.send_message(
            call.message.chat.id, "⏳ Настраиваю MkDocs для базы знаний..."
        )

        # Configure MkDocs
        success, result_message = self.mkdocs_configurator.configure_mkdocs(
            kb_path=kb_path,
            kb_name=user_kb["kb_name"],
            github_url=user_kb.get("github_url", ""),
        )

        # Delete processing message
        try:
            await self.bot.delete_message(call.message.chat.id, processing_msg.message_id)
        except Exception:
            pass

        # Send result
        await self.bot.send_message(call.message.chat.id, result_message)

    async def _show_kb_creation_menu_callback(self, call: CallbackQuery) -> None:
        """Show KB creation menu in callback"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 1

        keyboard.add(
            InlineKeyboardButton("📁 Создать локальную БЗ", callback_data="kb:create_local"),
            InlineKeyboardButton(
                "🌐 Подключить GitHub репозиторий", callback_data="kb:create_github"
            ),
        )

        menu_text = (
            "📚 **Создание новой базы знаний**\n\n"
            "Выберите тип базы знаний:\n"
            "• **Локальная БЗ** - создается на сервере\n"
            "• **GitHub репозиторий** - для совместной работы"
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

    async def _back_to_kb_menu(self, call: CallbackQuery) -> None:
        """Go back to main KB menu"""
        user_kb = self.user_settings.get_user_kb(call.from_user.id)

        if user_kb:
            kb_path = self.repo_manager.get_kb_path(user_kb["kb_name"])

            keyboard = InlineKeyboardMarkup()
            keyboard.row_width = 1

            keyboard.add(
                InlineKeyboardButton("ℹ️ Информация о БЗ", callback_data="kb:info"),
                InlineKeyboardButton("🔄 Переключить на другую БЗ", callback_data="kb:switch"),
                InlineKeyboardButton("➕ Создать новую БЗ", callback_data="kb:create_new"),
            )

            # Add MkDocs setup button for GitHub repos
            if user_kb["kb_type"] == "github":
                is_mkdocs_configured = False
                if kb_path and self.mkdocs_configurator.is_mkdocs_configured(kb_path):
                    is_mkdocs_configured = True

                if not is_mkdocs_configured:
                    keyboard.add(
                        InlineKeyboardButton(
                            "📖 Настроить документацию (MkDocs)", callback_data="kb:setup_mkdocs"
                        )
                    )

            # Prepare KB info text
            kb_type_emoji = "🌐" if user_kb["kb_type"] == "github" else "📁"
            kb_type_text = "GitHub репозиторий" if user_kb["kb_type"] == "github" else "Локальная"

            menu_text = (
                f"📚 **Текущая база знаний**\n\n"
                f"{kb_type_emoji} **Название:** {_escape_html(user_kb['kb_name'])}\n"
                f"**Тип:** {kb_type_text}\n"
            )

            if user_kb["kb_type"] == "github" and user_kb.get("github_url"):
                menu_text += f"**URL:** {_escape_html(user_kb['github_url'])}\n"

            if kb_path:
                menu_text += f"**Путь:** `{escape_markdown(str(kb_path))}`\n"

            menu_text += "\nВыберите действие:"
        else:
            keyboard = InlineKeyboardMarkup()
            keyboard.row_width = 1

            keyboard.add(
                InlineKeyboardButton("📁 Создать локальную БЗ", callback_data="kb:create_local"),
                InlineKeyboardButton(
                    "🌐 Подключить GitHub репозиторий", callback_data="kb:create_github"
                ),
            )

            menu_text = (
                "📚 **Управление базой знаний**\n\n"
                "У вас пока нет настроенной базы знаний.\n\n"
                "Выберите, что хотите сделать:"
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
