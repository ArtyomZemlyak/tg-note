"""
Telegram Settings Handlers
Auto-generated command handlers for settings management
"""

from loguru import logger
from pathlib import Path
from typing import Dict, Optional
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import settings
from src.bot.settings_manager import SettingsManager, SettingsInspector, UserSettingsStorage



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
    
    def _is_forwarded_message(self, message: Message) -> bool:
        """Check if message is forwarded from any source"""
        return (
            message.forward_from is not None or  # Forwarded from user
            message.forward_from_chat is not None or  # Forwarded from channel/group
            message.forward_sender_name is not None or  # Forwarded from privacy-enabled user
            message.forward_date is not None  # Forwarded message (any source)
        )
    
    async def register_handlers_async(self):
        """Register all settings handlers"""
        # Main settings commands
        self.bot.message_handler(commands=['settings'])(self.handle_settings_menu)
        self.bot.message_handler(commands=['viewsettings'])(self.handle_view_settings)
        self.bot.message_handler(commands=['resetsetting'])(self.handle_reset_setting)
        
        # Category-specific commands
        self.bot.message_handler(commands=['kbsettings'])(self.handle_kb_settings)
        self.bot.message_handler(commands=['agentsettings'])(self.handle_agent_settings)
        
        # Text message handler for setting input (exclude forwarded messages)
        self.bot.message_handler(func=lambda m: m.from_user.id in self.waiting_for_input and not self._is_forwarded_message(m))(
            self.handle_setting_input
        )
        
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
            "• Click on any setting to change its value\n"
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
            # Invalidate user cache in handlers
            if self.handlers:
                self.handlers.invalidate_user_cache(message.from_user.id)
            
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
            
            else:
                await self.bot.answer_callback_query(call.id, "Unknown action")
        
        except Exception as e:
            logger.error(f"Error handling settings callback: {e}", exc_info=True)
            await self.bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
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
            "• Click on any setting to change its value\n"
            "• Use /resetsetting <name> to restore default"
        )
        
        await self.bot.edit_message_text(
            menu_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
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
            "general": "🔧 General"
        }
        
        label = category_labels.get(category, category.title())
        lines = [f"{label} Settings\n"]
        lines.append("Click on any setting to view details and change its value:\n")
        
        # Create keyboard with setting buttons
        keyboard = InlineKeyboardMarkup()
        
        for name, value in sorted(settings_dict.items()):
            info = self.inspector.get_setting_info(name)
            if info and not info.is_secret and not info.is_readonly:
                if isinstance(value, bool):
                    value_str = "✅" if value else "❌"
                else:
                    value_str = str(value)[:20]  # Truncate long values
                
                button_text = f"{name}: {value_str}"
                keyboard.add(
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"settings:setting:{name}"
                    )
                )
        
        keyboard.add(
            InlineKeyboardButton("« Back to Menu", callback_data="settings:menu")
        )
        
        text = "\n".join(lines)
        
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
            # Invalidate user cache in handlers
            if self.handlers:
                self.handlers.invalidate_user_cache(user_id)
            
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
            # Invalidate user cache in handlers
            if self.handlers:
                self.handlers.invalidate_user_cache(user_id)
            
            await self.bot.answer_callback_query(call.id, f"✅ {msg}", show_alert=True)
            # Refresh the display
            info = self.inspector.get_setting_info(setting_name)
            if info:
                await self._show_category_settings(call, info.category)
        else:
            await self.bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
    
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
        lines = [f"⚙️ **{setting_name}**\n"]
        lines.append(f"📝 {info.description}\n")
        
        # Add type information
        type_str = self._format_type(info.type)
        lines.append(f"**Type:** `{type_str}`")
        
        # Add current value
        if isinstance(current_value, bool):
            value_str = "✅ enabled" if current_value else "❌ disabled"
        else:
            value_str = str(current_value)
        lines.append(f"**Current value:** `{value_str}`")
        
        # Add default value
        if isinstance(info.default, bool):
            default_str = "✅ enabled" if info.default else "❌ disabled"
        else:
            default_str = str(info.default)
        lines.append(f"**Default value:** `{default_str}`\n")
        
        # Add allowed values or examples
        if info.type == bool or (hasattr(info.type, '__origin__') and str(info.type).startswith('typing.Union') and bool in str(info.type)):
            lines.append("**Allowed values:** `true`, `false`")
        elif info.allowed_values:
            allowed_str = ", ".join([f"`{v}`" for v in info.allowed_values])
            lines.append(f"**Allowed values:** {allowed_str}")
        elif info.min_value is not None or info.max_value is not None:
            if info.min_value is not None and info.max_value is not None:
                lines.append(f"**Range:** `{info.min_value}` to `{info.max_value}`")
            elif info.min_value is not None:
                lines.append(f"**Minimum:** `{info.min_value}`")
            elif info.max_value is not None:
                lines.append(f"**Maximum:** `{info.max_value}`")
        
        text = "\n".join(lines)
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup()
        
        # For boolean settings, add toggle buttons
        if info.type == bool or (hasattr(info.type, '__origin__') and str(info.type).startswith('typing.Union') and bool in str(info.type)):
            keyboard.add(
                InlineKeyboardButton("✅ Enable", callback_data=f"settings:set:{setting_name}:true"),
                InlineKeyboardButton("❌ Disable", callback_data=f"settings:set:{setting_name}:false")
            )
        
        # Add reset and back buttons
        keyboard.add(
            InlineKeyboardButton("🔄 Reset to Default", callback_data=f"settings:reset:{setting_name}")
        )
        keyboard.add(
            InlineKeyboardButton("« Back", callback_data=f"settings:category:{info.category}")
        )
        
        await self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        # If not a boolean, prompt for text input
        if info.type != bool and not (hasattr(info.type, '__origin__') and str(info.type).startswith('typing.Union') and bool in str(info.type)):
            # Store that we're waiting for input
            self.waiting_for_input[user_id] = (setting_name, info.category)
            
            # Send a prompt message
            prompt_text = (
                f"💬 Please send the new value for `{setting_name}`\n\n"
                f"Note: Forwarded messages will be added to knowledge base instead.\n"
                f"Send /cancel to cancel."
            )
            await self.bot.send_message(call.message.chat.id, prompt_text, parse_mode='Markdown')
        
        await self.bot.answer_callback_query(call.id)
    
    async def handle_setting_input(self, message: Message) -> None:
        """Handle text input for setting values"""
        user_id = message.from_user.id
        
        # Check if user is waiting for input
        if user_id not in self.waiting_for_input:
            return
        
        # Check for cancel
        if message.text and message.text.strip().lower() in ['/cancel', 'cancel']:
            del self.waiting_for_input[user_id]
            await self.bot.reply_to(message, "❌ Cancelled")
            return
        
        setting_name, category = self.waiting_for_input[user_id]
        value_str = message.text.strip()
        
        # Set the setting
        success, msg = self.settings_manager.set_user_setting(user_id, setting_name, value_str)
        
        # Clear waiting state
        del self.waiting_for_input[user_id]
        
        if success:
            # Invalidate user cache in handlers
            if self.handlers:
                self.handlers.invalidate_user_cache(user_id)
            
            await self.bot.reply_to(message, f"✅ {msg}")
        else:
            await self.bot.reply_to(message, f"❌ {msg}")
    
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
        origin = getattr(type_annotation, '__origin__', None)
        if origin is typing.Union:
            args = getattr(type_annotation, '__args__', ())
            # Check if it's Optional (Union with None)
            if type(None) in args:
                inner_type = next((arg for arg in args if arg is not type(None)), None)
                if inner_type:
                    return f"optional {self._format_type(inner_type)}"
        
        # Handle List types
        if origin is list:
            args = getattr(type_annotation, '__args__', ())
            if args:
                return f"list of {self._format_type(args[0])}"
            return "list"
        
        # Fallback
        return str(type_annotation).replace('typing.', '').replace('<class ', '').replace('>', '').replace("'", '')
    
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
