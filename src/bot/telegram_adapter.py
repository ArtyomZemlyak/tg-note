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
    for bot operations, following the Adapter pattern
    """
    
    def __init__(self, bot: AsyncTeleBot):
        """
        Initialize Telegram bot adapter
        
        Args:
            bot: AsyncTeleBot instance
        """
        self._bot = bot
    
    @property
    def bot(self) -> AsyncTeleBot:
        """
        Get underlying Telegram bot instance
        
        Returns:
            AsyncTeleBot instance
        """
        return self._bot
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        **kwargs
    ) -> Message:
        """
        Send a message to a chat
        
        Args:
            chat_id: Chat identifier
            text: Message text
            **kwargs: Additional Telegram-specific parameters
            
        Returns:
            Telegram Message object
        """
        return await self._bot.send_message(chat_id, text, **kwargs)
    
    async def reply_to(
        self,
        message: Message,
        text: str,
        **kwargs
    ) -> Message:
        """
        Reply to a message
        
        Args:
            message: Original Telegram message to reply to
            text: Reply text
            **kwargs: Additional Telegram-specific parameters
            
        Returns:
            Telegram Message object
        """
        return await self._bot.reply_to(message, text, **kwargs)
    
    async def edit_message_text(
        self,
        text: str,
        chat_id: int,
        message_id: int,
        **kwargs
    ) -> Any:
        """
        Edit a message text
        
        Args:
            text: New message text
            chat_id: Chat identifier
            message_id: Message identifier to edit
            **kwargs: Additional Telegram-specific parameters
            
        Returns:
            Updated Telegram Message object
        """
        return await self._bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            **kwargs
        )
    
    async def download_file(
        self,
        file_path: str
    ) -> bytes:
        """
        Download a file by its file path
        
        Args:
            file_path: File path from Telegram
            
        Returns:
            File content as bytes
        """
        return await self._bot.download_file(file_path)
    
    async def get_file(
        self,
        file_id: str
    ):
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
