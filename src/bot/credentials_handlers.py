"""
Credentials Handlers for Telegram Bot
Handles commands for managing Git credentials securely
"""

from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.bot_port import BotPort
from src.knowledge_base.credentials_manager import CredentialsManager


class CredentialsHandlers:
    """Handlers for Git credentials management"""

    def __init__(
        self, bot: BotPort, async_bot: AsyncTeleBot, credentials_manager: CredentialsManager
    ):
        """
        Initialize credentials handlers

        Args:
            bot: Bot messaging interface
            async_bot: Telegram bot instance
            credentials_manager: Credentials manager
        """
        self.bot = bot
        self.async_bot = async_bot
        self.credentials_manager = credentials_manager
        self.logger = logger

        # Temporary storage for multi-step flows
        self._pending_credentials: dict = {}

    async def register_handlers(self):
        """Register all credentials-related handlers"""
        # Command handlers
        self.async_bot.message_handler(commands=["settoken"])(self.handle_settoken)
        self.async_bot.message_handler(commands=["removetoken"])(self.handle_removetoken)
        self.async_bot.message_handler(commands=["listcredentials"])(self.handle_list_credentials)

        # Callback query handlers
        self.async_bot.callback_query_handler(func=lambda call: call.data.startswith("cred:"))(
            self.handle_credentials_callback
        )

        # Message handler for token input
        self.async_bot.message_handler(func=lambda m: self._is_awaiting_token_input(m))(
            self.handle_token_input
        )

        self.logger.info("Credentials handlers registered")

    def _is_awaiting_token_input(self, message: Message) -> bool:
        """Check if user is in token input flow"""
        user_id = message.from_user.id
        if user_id not in self._pending_credentials:
            return False

        pending = self._pending_credentials[user_id]
        return pending.get("state") in ("awaiting_username", "awaiting_token")

    async def handle_settoken(self, message: Message) -> None:
        """
        Handle /settoken command - start token setup flow

        Usage: /settoken
        """
        user_id = message.from_user.id
        self.logger.info(f"[CREDENTIALS] /settoken command from user {user_id}")

        # Show platform selection
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 2
        keyboard.add(
            InlineKeyboardButton("GitHub", callback_data="cred:set:github"),
            InlineKeyboardButton("GitLab", callback_data="cred:set:gitlab"),
        )
        keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cred:cancel"))

        await self.bot.send_message(
            user_id,
            "🔐 *Установка Git Credentials*\n\n"
            "Выберите платформу для которой хотите сохранить токен:\n\n"
            "*⚠️ Безопасность:*\n"
            "• Токены будут зашифрованы перед сохранением\n"
            "• Используется симметричное шифрование (AES-128)\n"
            "• Токены не видны в логах и истории сообщений\n"
            "• Рекомендуется удалить сообщения с токеном после отправки\n\n"
            "_💡 Как получить токен:_\n"
            "• GitHub: Settings → Developer settings → Personal access tokens\n"
            "• GitLab: Settings → Access Tokens\n\n"
            "Требуемые права доступа: `repo` или `write_repository`",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    async def handle_removetoken(self, message: Message) -> None:
        """
        Handle /removetoken command - remove stored credentials

        Usage: /removetoken
        """
        user_id = message.from_user.id
        self.logger.info(f"[CREDENTIALS] /removetoken command from user {user_id}")

        # Get user's credentials
        credentials = self.credentials_manager.list_credentials(user_id)

        if not credentials:
            await self.bot.send_message(
                user_id, "ℹ️ У вас нет сохраненных токенов.", parse_mode="HTML"
            )
            return

        # Show platform selection
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 2

        for platform in credentials.keys():
            platform_emoji = "🐙" if platform == "github" else "🦊"
            keyboard.add(
                InlineKeyboardButton(
                    f"{platform_emoji} {platform.upper()}",
                    callback_data=f"cred:remove:{platform}",
                )
            )

        keyboard.add(
            InlineKeyboardButton("🗑️ Удалить все", callback_data="cred:remove:all"),
            InlineKeyboardButton("❌ Отмена", callback_data="cred:cancel"),
        )

        await self.bot.send_message(
            user_id,
            "🔐 *Удаление Git Credentials*\n\n"
            "Выберите платформу, токен которой нужно удалить:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    async def handle_list_credentials(self, message: Message) -> None:
        """
        Handle /listcredentials command - show stored credentials info

        Usage: /listcredentials
        """
        user_id = message.from_user.id
        self.logger.info(f"[CREDENTIALS] /listcredentials command from user {user_id}")

        # Get user's credentials
        credentials = self.credentials_manager.list_credentials(user_id)

        if not credentials:
            await self.bot.send_message(
                user_id,
                "ℹ️ У вас нет сохраненных токенов.\n\n"
                "Используйте `/settoken` чтобы добавить токен.",
                parse_mode="HTML",
            )
            return

        # Build credentials info message
        lines = ["🔐 *Сохраненные Git Credentials*\n"]

        for platform, info in credentials.items():
            platform_emoji = "🐙" if platform == "github" else "🦊"
            lines.append(f"*{platform_emoji} {platform.upper()}*")
            lines.append(f"  • Username: `{info['username']}`")
            lines.append(
                f"  • Token: {'✅ Установлен' if info['token_set'] else '❌ Не установлен'}"
            )
            if info.get("remote_url"):
                lines.append(f"  • Remote: `{info['remote_url']}`")
            lines.append("")

        lines.append(
            "\n💡 _Токены хранятся в зашифрованном виде и используются "
            "только для Git операций._"
        )

        await self.bot.send_message(user_id, "\n".join(lines), parse_mode="HTML")

    async def handle_credentials_callback(self, call: CallbackQuery) -> None:
        """Handle callback queries for credentials management"""
        user_id = call.from_user.id
        data_parts = call.data.split(":")

        if len(data_parts) < 2:
            await self.async_bot.answer_callback_query(call.id, "❌ Неверная команда")
            return

        action = data_parts[1]

        if action == "set":
            await self._handle_set_callback(call, data_parts)
        elif action == "remove":
            await self._handle_remove_callback(call, data_parts)
        elif action == "cancel":
            await self._handle_cancel_callback(call)
        else:
            await self.async_bot.answer_callback_query(call.id, "❌ Неизвестная команда")

    async def _handle_set_callback(self, call: CallbackQuery, data_parts: list) -> None:
        """Handle set token callback"""
        user_id = call.from_user.id

        if len(data_parts) < 3:
            await self.async_bot.answer_callback_query(call.id, "❌ Неверная команда")
            return

        platform = data_parts[2]

        # Store pending state
        self._pending_credentials[user_id] = {
            "platform": platform,
            "state": "awaiting_username",
        }

        platform_emoji = "🐙" if platform == "github" else "🦊"
        platform_name = platform.upper()

        # Ask for username
        await self.async_bot.edit_message_text(
            f"🔐 *Установка {platform_emoji} {platform_name} токена*\n\n"
            f"Шаг 1/2: Введите ваш *username* на {platform_name}:\n\n"
            f"_Пример: john_doe_",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
        )

        await self.async_bot.answer_callback_query(call.id)

    async def _handle_remove_callback(self, call: CallbackQuery, data_parts: list) -> None:
        """Handle remove token callback"""
        user_id = call.from_user.id

        if len(data_parts) < 3:
            await self.async_bot.answer_callback_query(call.id, "❌ Неверная команда")
            return

        platform = data_parts[2]

        if platform == "all":
            # Remove all credentials
            success = self.credentials_manager.remove_credentials(user_id)
            if success:
                await self.async_bot.edit_message_text(
                    "✅ Все токены успешно удалены",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                )
                self.logger.info(f"Removed all credentials for user {user_id}")
            else:
                await self.async_bot.edit_message_text(
                    "❌ Ошибка при удалении токенов",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                )
        else:
            # Remove specific platform
            success = self.credentials_manager.remove_credentials(user_id, platform)
            platform_emoji = "🐙" if platform == "github" else "🦊"
            platform_name = platform.upper()

            if success:
                await self.async_bot.edit_message_text(
                    f"✅ {platform_emoji} {platform_name} токен успешно удален",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                )
                self.logger.info(f"Removed {platform} credentials for user {user_id}")
            else:
                await self.async_bot.edit_message_text(
                    f"❌ Ошибка при удалении {platform_name} токена",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                )

        await self.async_bot.answer_callback_query(call.id)

    async def _handle_cancel_callback(self, call: CallbackQuery) -> None:
        """Handle cancel callback"""
        user_id = call.from_user.id

        # Clear pending state
        if user_id in self._pending_credentials:
            del self._pending_credentials[user_id]

        await self.async_bot.edit_message_text(
            "❌ Операция отменена",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )
        await self.async_bot.answer_callback_query(call.id)

    async def handle_token_input(self, message: Message) -> None:
        """Handle token/username input from user"""
        user_id = message.from_user.id

        if user_id not in self._pending_credentials:
            return

        pending = self._pending_credentials[user_id]
        state = pending.get("state")
        platform = pending.get("platform")

        if state == "awaiting_username":
            # Store username and ask for token
            username = message.text.strip()
            pending["username"] = username
            pending["state"] = "awaiting_token"

            platform_emoji = "🐙" if platform == "github" else "🦊"
            platform_name = platform.upper()

            # AICODE-NOTE: Delete user's message for security
            try:
                await self.async_bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass

            await self.bot.send_message(
                user_id,
                f"🔐 *Установка {platform_emoji} {platform_name} токена*\n\n"
                f"Username: `{username}` ✅\n\n"
                f"Шаг 2/2: Введите ваш *Personal Access Token*:\n\n"
                f"*⚠️ Важно:*\n"
                f"• Токен будет зашифрован и сохранен безопасно\n"
                f"• После отправки сообщение будет автоматически удалено\n"
                f"• Токен не будет виден в логах\n\n"
                f"_💡 Где получить токен:_\n"
                f"• GitHub: https://github.com/settings/tokens\n"
                f"• GitLab: https://gitlab.com/-/profile/personal_access_tokens",
                parse_mode="HTML",
            )

        elif state == "awaiting_token":
            # Store token
            token = message.text.strip()
            username = pending.get("username")

            # AICODE-NOTE: Immediately delete message with token for security
            try:
                await self.async_bot.delete_message(message.chat.id, message.message_id)
            except Exception as e:
                self.logger.warning(f"Could not delete token message: {e}")

            # Save credentials
            success = self.credentials_manager.set_credentials(
                user_id=user_id, platform=platform, username=username, token=token
            )

            platform_emoji = "🐙" if platform == "github" else "🦊"
            platform_name = platform.upper()

            if success:
                await self.bot.send_message(
                    user_id,
                    f"✅ *{platform_emoji} {platform_name} токен успешно сохранен!*\n\n"
                    f"Username: `{username}`\n"
                    f"Token: ✅ Сохранен и зашифрован\n\n"
                    f"Токен будет автоматически использоваться при работе "
                    f"с Git репозиториями на {platform_name}.",
                    parse_mode="HTML",
                )
                self.logger.info(
                    f"Successfully saved {platform} credentials for user {user_id} "
                    f"(username: {username})"
                )
            else:
                await self.bot.send_message(
                    user_id,
                    f"❌ Ошибка при сохранении {platform_name} токена.\n\n"
                    f"Попробуйте еще раз с помощью команды `/settoken`.",
                    parse_mode="HTML",
                )

            # Clear pending state
            del self._pending_credentials[user_id]
