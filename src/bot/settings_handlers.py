"""
Telegram Settings Handlers
Auto-generated command handlers for settings management
"""

from pathlib import Path
from typing import Dict, Optional

from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import settings
from src.bot.settings_manager import SettingsInspector, SettingsManager, UserSettingsStorage
from src.bot.utils import escape_html
from src.mcp.docling_integration import ensure_docling_mcp_spec
from src.processor.docling_runtime import sync_models


class SettingsHandlers:
    """Telegram handlers for settings management"""

    def __init__(self, bot: AsyncTeleBot, handlers=None):
        self.bot = bot
        self.settings_manager = SettingsManager(settings)
        self.inspector = SettingsInspector(type(settings))
        # Track users waiting for input: user_id -> (setting_name, category)
        self.waiting_for_input: Dict[int, tuple[str, str]] = {}
        # Reference to bot handlers for cache invalidation
        self.handlers = handlers

    @staticmethod
    def _is_docling_setting(setting_name: str) -> bool:
        """Return True if the setting impacts Docling configuration."""
        return setting_name.upper().startswith("MEDIA_PROCESSING_DOCLING")

    async def _refresh_docling_after_setting(self, chat_id: int, setting_name: str) -> None:
        """Regenerate Docling configuration and trigger model sync when relevant settings change."""
        if not self._is_docling_setting(setting_name):
            return

        try:
            ensure_docling_mcp_spec(settings.MEDIA_PROCESSING_DOCLING)
        except Exception as exc:
            logger.error(f"Failed to update Docling MCP configuration: {exc}", exc_info=True)
            await self.bot.send_message(
                chat_id,
                "⚠️ Не удалось обновить конфигурацию Docling. Проверьте логи контейнера.",
            )
            return

        progress_msg = await self.bot.send_message(
            chat_id,
            "🔄 Обновляю Docling (загрузка моделей может занять несколько минут)...",
        )

        try:
            result = await sync_models(force=False)
        except Exception as exc:
            logger.error(f"Docling model sync failed: {exc}", exc_info=True)
            await self.bot.edit_message_text(
                "❌ Ошибка: не удалось синхронизировать модели Docling. Подробности в логах контейнера.",
                chat_id,
                progress_msg.message_id,
            )
            return

        if not result:
            await self.bot.edit_message_text(
                "⚠️ Docling MCP недоступен, синхронизация пропущена.",
                chat_id,
                progress_msg.message_id,
            )
            return

        payload = result.get("result") or {}
        items = payload.get("items", [])
        success = result.get("success", True)

        if items:
            lines = [
                f"• {escape_html(item.get('name', item.get('repo_id', 'artefact')))} — "
                f"{escape_html(item.get('status', 'unknown'))}"
                for item in items
            ]
            summary = "\n".join(lines)
        else:
            summary = "Нет изменений (модели уже актуальны)."

        if success:
            text = f"✅ Docling обновлён.\n\n{summary}"
        else:
            text = (
                "⚠️ Синхронизация Docling завершилась с ошибками. "
                "Подробности см. в логах контейнера.\n\n"
                f"{summary}"
            )

        await self.bot.edit_message_text(
            text,
            chat_id,
            progress_msg.message_id,
            parse_mode="HTML",
        )

    def _is_forwarded_message(self, message: Message) -> bool:
        """Check if message is forwarded from any source"""
        # Check forward_date first as it's the most reliable indicator
        # forward_date is an integer timestamp, so we check it's not None and > 0
        if message.forward_date is not None and message.forward_date > 0:
            return True

        # Check other forward fields (objects or strings)
        return bool(
            message.forward_from
            or message.forward_from_chat
            or (message.forward_sender_name and message.forward_sender_name.strip())
        )

    async def register_handlers_async(self):
        """Register all settings handlers"""
        # Main settings commands
        self.bot.message_handler(commands=["settings"])(self.handle_settings_menu)
        self.bot.message_handler(commands=["viewsettings"])(self.handle_view_settings)
        self.bot.message_handler(commands=["resetsetting"])(self.handle_reset_setting)

        # Category-specific commands
        self.bot.message_handler(commands=["kbsettings"])(self.handle_kb_settings)
        self.bot.message_handler(commands=["agentsettings"])(self.handle_agent_settings)

        # Text message handler for setting input (exclude forwarded messages)
        self.bot.message_handler(
            func=lambda m: m.from_user.id in self.waiting_for_input
            and not self._is_forwarded_message(m)
        )(self.handle_setting_input)

        # Callback query handlers for inline keyboards
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("settings:"))(
            self.handle_settings_callback
        )

    async def handle_settings_menu(self, message: Message) -> None:
        """Handle /settings command - show main settings menu"""
        logger.info(f"Settings menu requested by user {message.from_user.id}")

        categories = self.inspector.get_all_categories()

        # Create inline keyboard with categories
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 2

        category_labels = {
            "knowledge_base": "📚 Knowledge Base",
            "agent": "🤖 Agent",
            "processing": "⚙️ Processing",
            "logging": "📝 Logging",
            "security": "🔒 Security",
            "credentials": "🔑 Credentials",
            "telegram": "💬 Telegram",
            "vector_search": "🔍 Vector Search",
            "memory_agent": "🧠 Memory Agent",
            "mcp": "🔌 MCP",
            "media": "📎 Media",
            "context": "💭 Context",
            "rate_limiting": "⏱️ Rate Limiting",
            "health_check": "🏥 Health Check",
            "general": "🔧 General",
        }

        for category in sorted(categories):
            label = category_labels.get(category, category.title())
            keyboard.add(InlineKeyboardButton(label, callback_data=f"settings:category:{category}"))

        menu_text = (
            "⚙️ <b>Settings Menu</b>\n\n"
            "Choose a category to view and modify settings:\n\n"
            "• Settings are stored per-user\n"
            "• You can override global defaults\n"
            "• Click on any setting to change its value\n"
            "• Use /resetsetting -name- to restore default"
        )

        await self.bot.send_message(
            message.chat.id, menu_text, reply_markup=keyboard, parse_mode="HTML"
        )

    async def handle_view_settings(self, message: Message) -> None:
        """Handle /viewsettings command - show all user settings"""
        logger.info(f"View settings requested by user {message.from_user.id}")

        # Parse category from command args
        args = message.text.split(maxsplit=1)
        category = args[1].strip() if len(args) > 1 else None

        # Get settings summary
        settings_dict = self.settings_manager.get_user_settings_summary(
            message.from_user.id, category=category
        )

        if not settings_dict:
            await self.bot.reply_to(message, "❌ No settings found for this category")
            return

        # Format settings display
        lines = []
        if category:
            lines.append(f"⚙️ <b>{category.upper()} Settings</b>\n")
        else:
            lines.append("⚙️ <b>All Settings</b>\n")

        # Group by category
        from collections import defaultdict

        by_category = defaultdict(list)

        for name, value in settings_dict.items():
            info = self.inspector.get_setting_info(name)
            if info:
                by_category[info.category].append((name, value, info))

        for cat in sorted(by_category.keys()):
            lines.append(f"\n<b>{cat.upper()}:</b>")
            for name, value, info in sorted(by_category[cat], key=lambda x: x[0]):
                # Format value
                if info.is_secret:
                    value_str = "<b>*hidden*</b>"
                elif isinstance(value, bool):
                    value_str = "✅ enabled" if value else "❌ disabled"
                else:
                    value_str = escape_html(str(value))

                readonly_marker = " 🔒" if info.is_readonly else ""
                lines.append(f"• `{name}`: {value_str}{readonly_marker}")

        text = "\n".join(lines)

        # Split into multiple messages if too long
        if len(text) > 4000:
            chunks = self._split_message(text, 4000)
            for chunk in chunks:
                await self.bot.send_message(message.chat.id, chunk, parse_mode="HTML")
        else:
            await self.bot.send_message(message.chat.id, text, parse_mode="HTML")

    async def handle_reset_setting(self, message: Message) -> None:
        """Handle /resetsetting command - reset setting to default"""
        logger.info(f"Reset setting requested by user {message.from_user.id}")

        # Parse command arguments
        args = message.text.split(maxsplit=1)

        if len(args) < 2:
            help_text = (
                "⚙️ <b>Reset Setting</b>\n\n"
                "Usage: `/resetsetting -setting_name-`\n\n"
                "This will reset the setting to the global default value.\n\n"
                "Example:\n"
                "```\n"
                "/resetsetting KB_GIT_ENABLED\n"
                "```"
            )
            try:
                await self.bot.reply_to(message, help_text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Error sending help text: {e}", exc_info=True)
            return

        setting_name = args[1].strip().upper()

        # Reset the setting
        try:
            success, msg = self.settings_manager.reset_user_setting(
                message.from_user.id, setting_name
            )
        except Exception as e:
            logger.error(f"Error resetting user setting {setting_name}: {e}", exc_info=True)
            success = False
            msg = f"Ошибка при сбросе настройки: {str(e)}"

        # Always send notification, even if there was an error
        try:
            if success:
                # Invalidate user cache in handlers
                if self.handlers:
                    try:
                        await self.handlers.invalidate_user_cache(message.from_user.id)
                    except Exception as e:
                        logger.warning(f"Error invalidating user cache: {e}", exc_info=True)

                await self.bot.reply_to(message, f"✅ {msg}")
            else:
                await self.bot.reply_to(message, f"❌ {msg}")
        except Exception as e:
            logger.error(f"Error sending setting reset notification: {e}", exc_info=True)
            # Try to send a simple error message
            try:
                await self.bot.reply_to(
                    message,
                    f"❌ Ошибка при отправке уведомления о сбросе настройки {setting_name}",
                )
            except Exception:
                logger.error("Failed to send error notification", exc_info=True)

    async def handle_kb_settings(self, message: Message) -> None:
        """Handle /kbsettings - show KB-specific settings"""
        logger.info(f"KB settings requested by user {message.from_user.id}")

        kb_settings = self.settings_manager.get_user_settings_summary(
            message.from_user.id, category="knowledge_base"
        )

        lines = ["📚 <b>Knowledge Base Settings</b>\n"]

        for name, value in sorted(kb_settings.items()):
            info = self.inspector.get_setting_info(name)
            if info:
                if isinstance(value, bool):
                    value_str = "✅ enabled" if value else "❌ disabled"
                else:
                    value_str = escape_html(str(value))

                lines.append(f"• `{name}`: {value_str}")
                lines.append(f"  _{escape_html(info.description)}_\n")

        # Add quick actions
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("Enable Git", callback_data="settings:set:KB_GIT_ENABLED:true"),
            InlineKeyboardButton("Disable Git", callback_data="settings:set:KB_GIT_ENABLED:false"),
        )
        keyboard.add(
            InlineKeyboardButton(
                "Enable Auto-Push", callback_data="settings:set:KB_GIT_AUTO_PUSH:true"
            ),
            InlineKeyboardButton(
                "Disable Auto-Push", callback_data="settings:set:KB_GIT_AUTO_PUSH:false"
            ),
        )

        text = "\n".join(lines)

        await self.bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="HTML")

    async def handle_agent_settings(self, message: Message) -> None:
        """Handle /agentsettings - show agent-specific settings"""
        logger.info(f"Agent settings requested by user {message.from_user.id}")

        agent_settings = self.settings_manager.get_user_settings_summary(
            message.from_user.id, category="agent"
        )

        lines = ["🤖 <b>Agent Settings</b>\n"]

        for name, value in sorted(agent_settings.items()):
            info = self.inspector.get_setting_info(name)
            if info:
                if isinstance(value, bool):
                    value_str = "✅ enabled" if value else "❌ disabled"
                else:
                    value_str = escape_html(str(value))

                lines.append(f"• `{name}`: {value_str}")
                lines.append(f"  _{escape_html(info.description)}_\n")

        # Add quick actions for common settings
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "Enable Web Search", callback_data="settings:set:AGENT_ENABLE_WEB_SEARCH:true"
            ),
            InlineKeyboardButton(
                "Disable Web Search", callback_data="settings:set:AGENT_ENABLE_WEB_SEARCH:false"
            ),
        )
        keyboard.add(
            InlineKeyboardButton(
                "Set Timeout: 300s", callback_data="settings:set:AGENT_TIMEOUT:300"
            ),
            InlineKeyboardButton(
                "Set Timeout: 600s", callback_data="settings:set:AGENT_TIMEOUT:600"
            ),
        )

        text = "\n".join(lines)

        await self.bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="HTML")

    async def handle_settings_callback(self, call: CallbackQuery) -> None:
        """Handle callback queries from settings inline keyboards"""
        try:
            # Parse callback data
            parts = call.data.split(":", 3)

            if len(parts) < 2:
                await self.bot.answer_callback_query(call.id, "Invalid callback")
                return

            action = parts[1]

            if action == "menu":
                # Show main settings menu
                await self._show_main_menu(call)

            elif action == "category":
                # Show settings for category
                category = parts[2]
                await self._show_category_settings(call, category)

            elif action == "setting":
                # Show individual setting with description
                setting_name = parts[2]
                await self._show_setting_detail(call, setting_name)

            elif action == "set":
                # Set a setting value
                setting_name = parts[2]
                value = parts[3]
                await self._set_setting_callback(call, setting_name, value)

            elif action == "reset":
                # Reset a setting
                setting_name = parts[2]
                await self._reset_setting_callback(call, setting_name)

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
                    await self.bot.send_message(
                        call.message.chat.id, "Main handlers not initialized"
                    )
            else:
                await self.bot.answer_callback_query(call.id, "Unknown action")

        except Exception as e:
            logger.error(f"Error handling settings callback: {e}", exc_info=True)
            # Escape any HTML-like characters in the error message to prevent parsing errors
            error_msg = str(e).replace("&", "&").replace("<", "<").replace(">", ">")
            await self.bot.answer_callback_query(call.id, f"Error: {error_msg}")

    async def _show_main_menu(self, call: CallbackQuery) -> None:
        """Show main settings menu"""
        categories = self.inspector.get_all_categories()

        # Create inline keyboard with categories
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 2

        category_labels = {
            "knowledge_base": "📚 Knowledge Base",
            "agent": "🤖 Agent",
            "processing": "⚙️ Processing",
            "logging": "📝 Logging",
            "security": "🔒 Security",
            "credentials": "🔑 Credentials",
            "telegram": "💬 Telegram",
            "vector_search": "🔍 Vector Search",
            "memory_agent": "🧠 Memory Agent",
            "mcp": "🔌 MCP",
            "media": "📎 Media",
            "context": "💭 Context",
            "rate_limiting": "⏱️ Rate Limiting",
            "health_check": "🏥 Health Check",
            "general": "🔧 General",
        }

        for category in sorted(categories):
            label = category_labels.get(category, category.title())
            keyboard.add(InlineKeyboardButton(label, callback_data=f"settings:category:{category}"))

        menu_text = (
            "⚙️ <b>Settings Menu</b>\n\n"
            "Choose a category to view and modify settings:\n\n"
            "• Settings are stored per-user\n"
            "• You can override global defaults\n"
            "• Click on any setting to change its value\n"
            "• Use /resetsetting -name- to restore default"
        )

        try:
            await self.bot.edit_message_text(
                menu_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception as e:
            # If Markdown parsing fails, send without formatting
            if "can't parse entities" in str(e).lower():
                logger.warning(
                    f"Markdown parsing failed in main menu, sending without formatting: {e}"
                )
                await self.bot.edit_message_text(
                    menu_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode=None,
                )
            else:
                raise

        await self.bot.answer_callback_query(call.id)

    async def _show_category_settings(self, call: CallbackQuery, category: str) -> None:
        """Show settings for a specific category"""
        user_id = call.from_user.id

        settings_dict = self.settings_manager.get_user_settings_summary(user_id, category=category)

        category_labels = {
            "knowledge_base": "📚 Knowledge Base",
            "agent": "🤖 Agent",
            "processing": "⚙️ Processing",
            "logging": "📝 Logging",
            "security": "🔒 Security",
            "credentials": "🔑 Credentials",
            "telegram": "💬 Telegram",
            "vector_search": "🔍 Vector Search",
            "memory_agent": "🧠 Memory Agent",
            "mcp": "🔌 MCP",
            "media": "📎 Media",
            "context": "💭 Context",
            "rate_limiting": "⏱️ Rate Limiting",
            "health_check": "🏥 Health Check",
            "general": "🔧 General",
        }

        label = category_labels.get(category, category.title())
        lines = [f"{label} Settings\n"]
        lines.append("Click on any setting to view details and change its value:\n")

        # Create keyboard with setting buttons
        keyboard = InlineKeyboardMarkup()

        # Add back button
        keyboard.add(InlineKeyboardButton("« Назад", callback_data="settings:back_to_main"))

        for name, value in sorted(settings_dict.items()):
            info = self.inspector.get_setting_info(name)
            if info and not info.is_secret and not info.is_readonly:
                if isinstance(value, bool):
                    value_str = "✅" if value else "❌"
                else:
                    value_str = str(value)[:20]  # Truncate long values

                button_text = f"{name}: {value_str}"
                keyboard.add(
                    InlineKeyboardButton(button_text, callback_data=f"settings:setting:{name}")
                )

        keyboard.add(InlineKeyboardButton("« Back to Menu", callback_data="settings:menu"))

        text = "\n".join(lines)

        try:
            await self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception as e:
            # If Markdown parsing fails, send without formatting
            if "can't parse entities" in str(e).lower():
                logger.warning(
                    f"Markdown parsing failed in category settings, sending without formatting: {e}"
                )
                await self.bot.edit_message_text(
                    text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode=None,
                )
            else:
                raise

        await self.bot.answer_callback_query(call.id)

    async def _set_setting_callback(
        self, call: CallbackQuery, setting_name: str, value: str
    ) -> None:
        """Set a setting from callback"""
        user_id = call.from_user.id

        try:
            success, msg = self.settings_manager.set_user_setting(user_id, setting_name, value)
        except Exception as e:
            logger.error(f"Error setting user setting {setting_name}: {e}", exc_info=True)
            success = False
            msg = f"Ошибка при изменении настройки: {str(e)}"

        try:
            if success:
                if self.handlers:
                    try:
                        await self.handlers.invalidate_user_cache(user_id)
                    except Exception as e:
                        logger.warning(f"Error invalidating user cache: {e}", exc_info=True)

                await self.bot.answer_callback_query(call.id, f"✅ {msg}", show_alert=True)
                try:
                    info = self.inspector.get_setting_info(setting_name)
                    if info:
                        await self._show_category_settings(call, info.category)
                except Exception as e:
                    logger.warning(f"Error refreshing category settings: {e}", exc_info=True)

                await self._refresh_docling_after_setting(call.message.chat.id, setting_name)
            else:
                await self.bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
        except Exception as e:
            logger.error(f"Error sending setting change notification: {e}", exc_info=True)
            try:
                await self.bot.answer_callback_query(
                    call.id,
                    f"❌ Ошибка при изменении настройки {setting_name}",
                    show_alert=True,
                )
            except Exception:
                logger.error("Failed to send error notification", exc_info=True)

    async def _reset_setting_callback(self, call: CallbackQuery, setting_name: str) -> None:
        """Reset a setting from callback"""
        user_id = call.from_user.id

        try:
            success, msg = self.settings_manager.reset_user_setting(user_id, setting_name)
        except Exception as e:
            logger.error(f"Error resetting user setting {setting_name}: {e}", exc_info=True)
            success = False
            msg = f"Ошибка при сбросе настройки: {str(e)}"

        # Always send notification, even if there was an error
        try:
            if success:
                # Invalidate user cache in handlers
                if self.handlers:
                    try:
                        await self.handlers.invalidate_user_cache(user_id)
                    except Exception as e:
                        logger.warning(f"Error invalidating user cache: {e}", exc_info=True)

                await self.bot.answer_callback_query(call.id, f"✅ {msg}", show_alert=True)
                # Refresh the display
                try:
                    info = self.inspector.get_setting_info(setting_name)
                    if info:
                        await self._show_category_settings(call, info.category)
                except Exception as e:
                    logger.warning(f"Error refreshing category settings: {e}", exc_info=True)
            else:
                await self.bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
        except Exception as e:
            logger.error(f"Error sending setting reset notification: {e}", exc_info=True)
            # Try to send a simple error message
            try:
                await self.bot.answer_callback_query(
                    call.id,
                    f"❌ Ошибка при сбросе настройки {setting_name}",
                    show_alert=True,
                )
            except Exception:
                logger.error("Failed to send error notification", exc_info=True)

    async def _show_setting_detail(self, call: CallbackQuery, setting_name: str) -> None:
        """Show detailed information about a setting and prompt for input"""
        user_id = call.from_user.id

        info = self.inspector.get_setting_info(setting_name)
        if not info:
            await self.bot.answer_callback_query(call.id, "Setting not found", show_alert=True)
            return

        # Get current value
        current_value = self.settings_manager.get_setting(user_id, setting_name)

        # Build description text
        lines = [f"⚙️ <b>{setting_name}</b>\n"]
        lines.append(f"📝 {escape_html(info.description)}\n")

        # Add type information
        type_str = self._format_type(info.type)
        lines.append(f"<b>Type:</b> `{escape_html(type_str)}`")

        # Add current value
        if isinstance(current_value, bool):
            value_str = "✅ enabled" if current_value else "❌ disabled"
        else:
            value_str = escape_html(str(current_value))
        lines.append(f"<b>Current value:</b> `{value_str}`")

        # Add default value
        if isinstance(info.default, bool):
            default_str = "✅ enabled" if info.default else "❌ disabled"
        else:
            default_str = escape_html(str(info.default))
        lines.append(f"<b>Default value:</b> `{default_str}`\n")

        # Add allowed values or examples
        if info.type == bool or (
            hasattr(info.type, "__origin__")
            and str(info.type).startswith("typing.Union")
            and bool in str(info.type)
        ):
            lines.append("<b>Allowed values:</b> `true`, `false`")
        elif info.allowed_values:
            allowed_str = ", ".join([f"`{v}`" for v in info.allowed_values])
            lines.append(f"<b>Allowed values:</b> {allowed_str}")
        elif info.min_value is not None or info.max_value is not None:
            if info.min_value is not None and info.max_value is not None:
                lines.append(f"<b>Range:</b> `{info.min_value}` to `{info.max_value}`")
            elif info.min_value is not None:
                lines.append(f"<b>Minimum:</b> `{info.min_value}`")
            elif info.max_value is not None:
                lines.append(f"<b>Maximum:</b> `{info.max_value}`")

        text = "\n".join(lines)

        # Create keyboard
        keyboard = InlineKeyboardMarkup()

        # Add back button
        keyboard.add(InlineKeyboardButton("« Назад", callback_data="settings:back_to_main"))

        # For boolean settings, add toggle buttons
        if info.type == bool or (
            hasattr(info.type, "__origin__")
            and str(info.type).startswith("typing.Union")
            and bool in str(info.type)
        ):
            keyboard.add(
                InlineKeyboardButton(
                    "✅ Enable", callback_data=f"settings:set:{setting_name}:true"
                ),
                InlineKeyboardButton(
                    "❌ Disable", callback_data=f"settings:set:{setting_name}:false"
                ),
            )

        # Add reset and back buttons
        keyboard.add(
            InlineKeyboardButton(
                "🔄 Reset to Default", callback_data=f"settings:reset:{setting_name}"
            )
        )
        keyboard.add(
            InlineKeyboardButton("« Back", callback_data=f"settings:category:{info.category}")
        )

        try:
            await self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception as e:
            # If Markdown parsing fails, send without formatting
            if "can't parse entities" in str(e).lower():
                logger.warning(
                    f"Markdown parsing failed in setting detail, sending without formatting: {e}"
                )
                await self.bot.edit_message_text(
                    text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode=None,
                )
            else:
                raise

        # If not a boolean, prompt for text input
        if info.type != bool and not (
            hasattr(info.type, "__origin__")
            and str(info.type).startswith("typing.Union")
            and bool in str(info.type)
        ):
            # Store that we're waiting for input
            self.waiting_for_input[user_id] = (setting_name, info.category)

            # Send a prompt message
            prompt_text = (
                f"💬 Please send the new value for `{setting_name}`\n\n"
                f"Note: Forwarded messages will be added to knowledge base instead.\n"
                f"Send /cancel to cancel."
            )
            await self.bot.send_message(call.message.chat.id, prompt_text, parse_mode="HTML")

        await self.bot.answer_callback_query(call.id)

    async def handle_setting_input(self, message: Message) -> None:
        """Handle text input for setting values"""
        user_id = message.from_user.id

        # Check if user is waiting for input
        if user_id not in self.waiting_for_input:
            return

        # Check for cancel
        if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
            del self.waiting_for_input[user_id]
            try:
                await self.bot.reply_to(message, "❌ Cancelled")
            except Exception as e:
                logger.error(f"Error sending cancel message: {e}", exc_info=True)
            return

        setting_name, category = self.waiting_for_input[user_id]
        value_str = message.text.strip()

        # Set the setting
        try:
            success, msg = self.settings_manager.set_user_setting(user_id, setting_name, value_str)
        except Exception as e:
            logger.error(f"Error setting user setting {setting_name}: {e}", exc_info=True)
            success = False
            msg = f"Ошибка при изменении настройки: {str(e)}"

        # Clear waiting state
        del self.waiting_for_input[user_id]

        try:
            if success:
                if self.handlers:
                    try:
                        await self.handlers.invalidate_user_cache(user_id)
                    except Exception as e:
                        logger.warning(f"Error invalidating user cache: {e}", exc_info=True)

                await self.bot.reply_to(message, f"✅ {msg}")
                await self._refresh_docling_after_setting(message.chat.id, setting_name)
            else:
                await self.bot.reply_to(message, f"❌ {msg}")
        except Exception as e:
            logger.error(f"Error sending setting change notification: {e}", exc_info=True)
            try:
                await self.bot.reply_to(
                    message,
                    f"❌ Ошибка при отправке уведомления об изменении настройки {setting_name}",
                )
            except Exception:
                logger.error("Failed to send error notification", exc_info=True)

    def _format_type(self, type_annotation) -> str:
        """Format type annotation as a readable string"""
        import typing

        # Handle simple types
        if type_annotation == bool:
            return "boolean"
        elif type_annotation == int:
            return "integer"
        elif type_annotation == float:
            return "float"
        elif type_annotation == str:
            return "string"
        elif type_annotation == Path:
            return "path"

        # Handle Optional types
        origin = getattr(type_annotation, "__origin__", None)
        if origin is typing.Union:
            args = getattr(type_annotation, "__args__", ())
            # Check if it's Optional (Union with None)
            if type(None) in args:
                inner_type = next((arg for arg in args if arg is not type(None)), None)
                if inner_type:
                    return f"optional {self._format_type(inner_type)}"

        # Handle List types
        if origin is list:
            args = getattr(type_annotation, "__args__", ())
            if args:
                return f"list of {self._format_type(args[0])}"
            return "list"

        # Fallback
        return (
            str(type_annotation)
            .replace("typing.", "")
            .replace("<class ", "")
            .replace(">", "")
            .replace("'", "")
        )

    def _split_message(self, text: str, max_length: int = 4000) -> list[str]:
        """Split long message into chunks"""
        chunks = []
        current_chunk = ""

        for line in text.split("\n"):
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += "\n" + line if current_chunk else line

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
