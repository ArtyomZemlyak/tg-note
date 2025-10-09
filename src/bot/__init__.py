"""
Telegram Bot Layer
Handles incoming messages and forwards them to processing

Clean Architecture:
- BotPort: Abstract interface for bot messaging operations
- TelegramBotAdapter: Telegram implementation of BotPort
"""

from src.bot.bot_port import BotPort
from src.bot.telegram_adapter import TelegramBotAdapter

__all__ = ["BotPort", "TelegramBotAdapter"]
