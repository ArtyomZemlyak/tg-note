"""
Telegram Bot Implementation
Main bot class using pyTelegramBotAPI
"""

import logging
import threading
from typing import Optional
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException

from config import settings
from src.bot.handlers import BotHandlers
from src.tracker.processing_tracker import ProcessingTracker
from src.knowledge_base.manager import KnowledgeBaseManager


class TelegramBot:
    """Main Telegram bot class"""

    def __init__(self, tracker: ProcessingTracker, kb_manager: KnowledgeBaseManager):
        self.tracker = tracker
        self.kb_manager = kb_manager
        self.logger = logging.getLogger(__name__)

        # Initialize bot
        self.bot = TeleBot(settings.TELEGRAM_BOT_TOKEN)

        # Initialize handlers
        self.handlers = BotHandlers(self.bot, tracker, kb_manager)

        # Bot state
        self.is_running = False
        self.polling_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the bot"""
        self.logger.info("Starting Telegram bot...")

        try:
            # Test bot connection
            bot_info = self.bot.get_me()
            self.logger.info(f"Bot connected: @{bot_info.username} ({bot_info.first_name})")

            # Start polling in a separate thread
            self.is_running = True
            self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
            self.polling_thread.start()

            self.logger.info("Telegram bot started successfully")

        except ApiTelegramException as e:
            self.logger.error(f"Failed to connect to Telegram API: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            raise

    def stop(self) -> None:
        """Stop the bot"""
        self.logger.info("Stopping Telegram bot...")

        self.is_running = False

        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)

        self.logger.info("Telegram bot stopped")

    def _polling_loop(self) -> None:
        """Main polling loop"""
        self.logger.info("Starting bot polling loop...")

        try:
            while self.is_running:
                try:
                    self.bot.polling(none_stop=True, timeout=10)
                except Exception as e:
                    if self.is_running:
                        self.logger.error(f"Polling error: {e}")
                        # Wait before retrying
                        import time

                        time.sleep(5)
                    else:
                        break

        except Exception as e:
            self.logger.error(f"Polling loop error: {e}")
        finally:
            self.logger.info("Bot polling loop ended")

    def send_message(self, chat_id: int, text: str, **kwargs) -> None:
        """Send a message to a chat"""
        try:
            self.bot.send_message(chat_id, text, **kwargs)
        except Exception as e:
            self.logger.error(f"Failed to send message to {chat_id}: {e}")

    def is_healthy(self) -> bool:
        """Check if bot is healthy"""
        try:
            self.bot.get_me()
            return True
        except Exception:
            return False
