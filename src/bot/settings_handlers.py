"""
Telegram Settings Handlers
Auto-generated command handlers for settings management
"""

import logging
from typing import Optional
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import settings
from src.bot.settings_manager import SettingsManager, SettingsInspector, UserSettingsStorage

logger = logging.getLogger(__name__)


class SettingsHandlers:
    """Telegram handlers for settings management"""
    
    def __init__(self, bot: AsyncTeleBot):
        self.bot = bot
        self.settings_manager = SettingsManager(settings)
        self.inspector = SettingsInspector(type(settings))
    
    async def register_handlers_async(self):
        """Register all settings handlers"""
        # Main settings commands
        self.bot.message_handler(commands=['settings'])(self.handle_settings_menu)
        self.bot.message_handler(commands=['viewsettings'])(self.handle_view_settings)
        self.bot.message_handler(commands=['setsetting'])(self.handle_set_setting)
        self.bot.message_handler(commands=['resetsetting'])(self.handle_reset_setting)
        
        # Category-specific commands
        self.bot.message_handler(commands=['kbsettings'])(self.handle_kb_settings)
        self.bot.message_handler(commands=['agentsettings'])(self.handle_agent_settings)
        
        # Callback query handlers for inline keyboards
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('settings:'))(
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
            "general": "🔧 General"
        }
        
        for category in sorted(categories):
            label = category_labels.get(category, category.title())
            keyboard.add(
                InlineKeyboardButton(
                    label,
                    callback_data=f"settings:category:{category}"
                )
            )
        
        menu_text = (
            "⚙️ **Settings Menu**\n\n"
            "Choose a category to view and modify settings:\n\n"
            "• Settings are stored per-user\n"
            "• You can override global defaults\n"
            "• Use /viewsettings to see all settings\n"
            "• Use /setsetting <name> <value> to change a setting\n"
            "• Use /resetsetting <name> to restore default"
        )
        
        await self.bot.send_message(
            message.chat.id,
            menu_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    async def handle_view_settings(self, message: Message) -> None:
        """Handle /viewsettings command - show all user settings"""
        logger.info(f"View settings requested by user {message.from_user.id}")
        
        # Parse category from command args
        args = message.text.split(maxsplit=1)
        category = args[1].strip() if len(args) > 1 else None
        
        # Get settings summary
        settings_dict = self.settings_manager.get_user_settings_summary(
            message.from_user.id,
            category=category
        )
        
        if not settings_dict:
            await self.bot.reply_to(
                message,
                "❌ No settings found for this category"
            )
            return
        
        # Format settings display
        lines = []
        if category:
            lines.append(f"⚙️ **{category.upper()} Settings**\n")
        else:
            lines.append("⚙️ **All Settings**\n")
        
        # Group by category
        from collections import defaultdict
        by_category = defaultdict(list)
        
        for name, value in settings_dict.items():
            info = self.inspector.get_setting_info(name)
            if info:
                by_category[info.category].append((name, value, info))
        
        for cat in sorted(by_category.keys()):
            lines.append(f"\n**{cat.upper()}:**")
            for name, value, info in sorted(by_category[cat], key=lambda x: x[0]):
                # Format value
                if info.is_secret:
                    value_str = "***hidden***"
                elif isinstance(value, bool):
                    value_str = "✅ enabled" if value else "❌ disabled"
                else:
                    value_str = str(value)
                
                readonly_marker = " 🔒" if info.is_readonly else ""
                lines.append(f"• `{name}`: {value_str}{readonly_marker}")
        
        text = "\n".join(lines)
        
        # Split into multiple messages if too long
        if len(text) > 4000:
            chunks = self._split_message(text, 4000)
            for chunk in chunks:
                await self.bot.send_message(
                    message.chat.id,
                    chunk,
                    parse_mode='Markdown'
                )
        else:
            await self.bot.send_message(
                message.chat.id,
                text,
                parse_mode='Markdown'
            )
    
    async def handle_set_setting(self, message: Message) -> None:
        """Handle /setsetting command - set a specific setting"""
        logger.info(f"Set setting requested by user {message.from_user.id}")
        
        # Parse command arguments
        args = message.text.split(maxsplit=2)
        
        if len(args) < 3:
            help_text = (
                "⚙️ **Set Setting**\n\n"
                "Usage: `/setsetting <setting_name> <value>`\n\n"
                "Examples:\n"
                "```\n"
                "/setsetting KB_GIT_ENABLED true\n"
                "/setsetting AGENT_TIMEOUT 600\n"
                "/setsetting MESSAGE_GROUP_TIMEOUT 60\n"
                "```\n\n"
                "Use /viewsettings to see available settings"
            )
            await self.bot.reply_to(message, help_text, parse_mode='Markdown')
            return
        
        setting_name = args[1].strip().upper()
        value_str = args[2].strip()
        
        # Set the setting
        success, msg = self.settings_manager.set_user_setting(
            message.from_user.id,
            setting_name,
            value_str
        )
        
        if success:
            await self.bot.reply_to(message, f"✅ {msg}")
        else:
            await self.bot.reply_to(message, f"❌ {msg}")
    
    async def handle_reset_setting(self, message: Message) -> None:
        """Handle /resetsetting command - reset setting to default"""
        logger.info(f"Reset setting requested by user {message.from_user.id}")
        
        # Parse command arguments
        args = message.text.split(maxsplit=1)
        
        if len(args) < 2:
            help_text = (
                "⚙️ **Reset Setting**\n\n"
                "Usage: `/resetsetting <setting_name>`\n\n"
                "This will reset the setting to the global default value.\n\n"
                "Example:\n"
                "```\n"
                "/resetsetting KB_GIT_ENABLED\n"
                "```"
            )
            await self.bot.reply_to(message, help_text, parse_mode='Markdown')
            return
        
        setting_name = args[1].strip().upper()
        
        # Reset the setting
        success, msg = self.settings_manager.reset_user_setting(
            message.from_user.id,
            setting_name
        )
        
        if success:
            await self.bot.reply_to(message, f"✅ {msg}")
        else:
            await self.bot.reply_to(message, f"❌ {msg}")
    
    async def handle_kb_settings(self, message: Message) -> None:
        """Handle /kbsettings - show KB-specific settings"""
        logger.info(f"KB settings requested by user {message.from_user.id}")
        
        kb_settings = self.settings_manager.get_user_settings_summary(
            message.from_user.id,
            category="knowledge_base"
        )
        
        lines = ["📚 **Knowledge Base Settings**\n"]
        
        for name, value in sorted(kb_settings.items()):
            info = self.inspector.get_setting_info(name)
            if info:
                if isinstance(value, bool):
                    value_str = "✅ enabled" if value else "❌ disabled"
                else:
                    value_str = str(value)
                
                lines.append(f"• `{name}`: {value_str}")
                lines.append(f"  _{info.description}_\n")
        
        # Add quick actions
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "Enable Git",
                callback_data="settings:set:KB_GIT_ENABLED:true"
            ),
            InlineKeyboardButton(
                "Disable Git",
                callback_data="settings:set:KB_GIT_ENABLED:false"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Enable Auto-Push",
                callback_data="settings:set:KB_GIT_AUTO_PUSH:true"
            ),
            InlineKeyboardButton(
                "Disable Auto-Push",
                callback_data="settings:set:KB_GIT_AUTO_PUSH:false"
            )
        )
        
        text = "\n".join(lines)
        
        await self.bot.send_message(
            message.chat.id,
            text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    async def handle_agent_settings(self, message: Message) -> None:
        """Handle /agentsettings - show agent-specific settings"""
        logger.info(f"Agent settings requested by user {message.from_user.id}")
        
        agent_settings = self.settings_manager.get_user_settings_summary(
            message.from_user.id,
            category="agent"
        )
        
        lines = ["🤖 **Agent Settings**\n"]
        
        for name, value in sorted(agent_settings.items()):
            info = self.inspector.get_setting_info(name)
            if info:
                if isinstance(value, bool):
                    value_str = "✅ enabled" if value else "❌ disabled"
                else:
                    value_str = str(value)
                
                lines.append(f"• `{name}`: {value_str}")
                lines.append(f"  _{info.description}_\n")
        
        # Add quick actions for common settings
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "Enable Web Search",
                callback_data="settings:set:AGENT_ENABLE_WEB_SEARCH:true"
            ),
            InlineKeyboardButton(
                "Disable Web Search",
                callback_data="settings:set:AGENT_ENABLE_WEB_SEARCH:false"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Set Timeout: 300s",
                callback_data="settings:set:AGENT_TIMEOUT:300"
            ),
            InlineKeyboardButton(
                "Set Timeout: 600s",
                callback_data="settings:set:AGENT_TIMEOUT:600"
            )
        )
        
        text = "\n".join(lines)
        
        await self.bot.send_message(
            message.chat.id,
            text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    async def handle_settings_callback(self, call: CallbackQuery) -> None:
        """Handle callback queries from settings inline keyboards"""
        try:
            # Parse callback data
            parts = call.data.split(':', 3)
            
            if len(parts) < 2:
                await self.bot.answer_callback_query(call.id, "Invalid callback")
                return
            
            action = parts[1]
            
            if action == "category":
                # Show settings for category
                category = parts[2]
                await self._show_category_settings(call, category)
            
            elif action == "set":
                # Set a setting value
                setting_name = parts[2]
                value = parts[3]
                await self._set_setting_callback(call, setting_name, value)
            
            elif action == "reset":
                # Reset a setting
                setting_name = parts[2]
                await self._reset_setting_callback(call, setting_name)
            
            else:
                await self.bot.answer_callback_query(call.id, "Unknown action")
        
        except Exception as e:
            logger.error(f"Error handling settings callback: {e}", exc_info=True)
            await self.bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    async def _show_category_settings(self, call: CallbackQuery, category: str) -> None:
        """Show settings for a specific category"""
        user_id = call.from_user.id
        
        settings_dict = self.settings_manager.get_user_settings_summary(user_id, category=category)
        
        lines = [f"⚙️ **{category.upper()} Settings**\n"]
        
        for name, value in sorted(settings_dict.items()):
            info = self.inspector.get_setting_info(name)
            if info and not info.is_secret and not info.is_readonly:
                if isinstance(value, bool):
                    value_str = "✅" if value else "❌"
                else:
                    value_str = str(value)
                
                lines.append(f"• `{name}`: {value_str}")
        
        text = "\n".join(lines)
        
        # Create keyboard with setting toggles
        keyboard = InlineKeyboardMarkup()
        
        for name, value in sorted(settings_dict.items()):
            info = self.inspector.get_setting_info(name)
            if info and not info.is_secret and not info.is_readonly:
                if isinstance(value, bool):
                    # Toggle button
                    new_value = "false" if value else "true"
                    button_text = f"{'✅' if value else '❌'} {name}"
                    keyboard.add(
                        InlineKeyboardButton(
                            button_text,
                            callback_data=f"settings:set:{name}:{new_value}"
                        )
                    )
        
        keyboard.add(
            InlineKeyboardButton("« Back to Menu", callback_data="settings:menu")
        )
        
        await self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        await self.bot.answer_callback_query(call.id)
    
    async def _set_setting_callback(self, call: CallbackQuery, setting_name: str, value: str) -> None:
        """Set a setting from callback"""
        user_id = call.from_user.id
        
        success, msg = self.settings_manager.set_user_setting(user_id, setting_name, value)
        
        if success:
            await self.bot.answer_callback_query(call.id, f"✅ {msg}", show_alert=True)
            # Refresh the display
            info = self.inspector.get_setting_info(setting_name)
            if info:
                await self._show_category_settings(call, info.category)
        else:
            await self.bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
    
    async def _reset_setting_callback(self, call: CallbackQuery, setting_name: str) -> None:
        """Reset a setting from callback"""
        user_id = call.from_user.id
        
        success, msg = self.settings_manager.reset_user_setting(user_id, setting_name)
        
        if success:
            await self.bot.answer_callback_query(call.id, f"✅ {msg}", show_alert=True)
            # Refresh the display
            info = self.inspector.get_setting_info(setting_name)
            if info:
                await self._show_category_settings(call, info.category)
        else:
            await self.bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
    
    def _split_message(self, text: str, max_length: int = 4000) -> list[str]:
        """Split long message into chunks"""
        chunks = []
        current_chunk = ""
        
        for line in text.split('\n'):
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += '\n' + line if current_chunk else line
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
