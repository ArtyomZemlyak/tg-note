"""
Telegram Bot Adapter
Adapter implementation of BotPort for Telegram (AsyncTeleBot)
This adapter decouples the application from the Telegram SDK
"""

from typing import Any

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from src.bot.bot_port import BotPort


class TelegramBotAdapter(BotPort):
    """
    Telegram implementation of BotPort interface

    This adapter wraps AsyncTeleBot and provides a clean interface
    for bot operations, following the Adapter pattern.
    Includes retry and throttling mechanisms via BotPort base class.
    """

    def __init__(
        self,
        bot: AsyncTeleBot,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit: float = 30.0,
        rate_limit_period: float = 1.0,
    ):
        """
        Initialize Telegram bot adapter

        Args:
            bot: AsyncTeleBot instance
            max_retries: Максимальное количество повторов при ошибке
            retry_delay: Начальная задержка между повторами (секунды)
            rate_limit: Количество запросов для rate limiting
            rate_limit_period: Период для rate limiting (секунды)
        """
        super().__init__(
            max_retries=max_retries,
            retry_delay=retry_delay,
            rate_limit=rate_limit,
            rate_limit_period=rate_limit_period,
        )
        self._bot = bot

    @property
    def bot(self) -> AsyncTeleBot:
        """
        Get underlying Telegram bot instance

        Returns:
            AsyncTeleBot instance
        """
        return self._bot

    async def _send_message_impl(self, chat_id: int, text: str, **kwargs) -> Message:
        """
        Реализация отправки сообщения (без retry/throttling)

        Args:
            chat_id: Chat identifier
            text: Message text
            **kwargs: Additional Telegram-specific parameters

        Returns:
            Telegram Message object
        """
        return await self._bot.send_message(chat_id, text, **kwargs)

    async def _reply_to_impl(self, message: Message, text: str, **kwargs) -> Message:
        """
        Реализация ответа на сообщение (без retry/throttling)

        Args:
            message: Original Telegram message to reply to
            text: Reply text
            **kwargs: Additional Telegram-specific parameters

        Returns:
            Telegram Message object
        """
        return await self._bot.reply_to(message, text, **kwargs)

    async def _edit_message_text_impl(
        self, text: str, chat_id: int, message_id: int, **kwargs
    ) -> Any:
        """
        Реализация редактирования сообщения (без retry/throttling)

        Args:
            text: New message text
            chat_id: Chat identifier
            message_id: Message identifier to edit
            **kwargs: Additional Telegram-specific parameters

        Returns:
            Updated Telegram Message object
        """
        return await self._bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id, **kwargs
        )

    async def download_file(self, file_path: str) -> bytes:
        """
        Download a file by its file path

        Args:
            file_path: File path from Telegram

        Returns:
            File content as bytes
        """
        return await self._bot.download_file(file_path)

    async def get_file(self, file_id: str):
        """
        Get file info by file ID

        Args:
            file_id: File identifier

        Returns:
            Telegram File object with path information
        """
        return await self._bot.get_file(file_id)

    async def get_me(self):
        """
        Get bot information

        Returns:
            Telegram User object representing the bot
        """
        return await self._bot.get_me()

    async def answer_callback_query(self, callback_query_id: str, text: str = None, show_alert: bool = False, url: str = None, cache_time: int = None):
        """
        Answer a callback query

        Args:
            callback_query_id: Callback query identifier
            text: Text to display to the user (optional)
            show_alert: If True, show an alert instead of a toast notification (optional)
            url: URL to redirect the user to (optional)
            cache_time: Maximum time in seconds for caching the result (optional)

        Returns:
            True on success
        """
        return await self._bot.answer_callback_query(
            callback_query_id, text=text, show_alert=show_alert, url=url, cache_time=cache_time
        )
