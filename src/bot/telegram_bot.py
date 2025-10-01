"""
Telegram Bot Implementation
Main bot class using pyTelegramBotAPI
"""

import logging
import threading
import time
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
        self._start_stop_lock = threading.Lock()  # Prevent concurrent start/stop operations
    
    def start(self) -> None:
        """Start the bot"""
        with self._start_stop_lock:
            self.logger.info("Starting Telegram bot...")
            
            # Ensure any existing bot is stopped first
            if self.is_running:
                self.logger.warning("Bot is already running, stopping first...")
                self._stop_internal()
            
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
                self.is_running = False
                raise
            except Exception as e:
                self.logger.error(f"Failed to start bot: {e}")
                self.is_running = False
                raise
    
    def stop(self) -> None:
        """Stop the bot"""
        with self._start_stop_lock:
            self._stop_internal()
    
    def _stop_internal(self) -> None:
        """Internal stop method (without lock)"""
        if not self.is_running:
            self.logger.info("Bot is already stopped")
            return
            
        self.logger.info("Stopping Telegram bot...")
        
        self.is_running = False
        
        # Stop the bot's internal polling
        try:
            self.bot.stop_polling()
        except Exception as e:
            self.logger.warning(f"Error stopping bot polling: {e}")
        
        # Wait for polling thread to finish with a longer timeout
        if self.polling_thread and self.polling_thread.is_alive():
            self.logger.info("Waiting for polling thread to finish...")
            self.polling_thread.join(timeout=10)
            if self.polling_thread.is_alive():
                self.logger.warning("Polling thread did not stop gracefully within timeout")
            else:
                self.logger.info("Polling thread stopped successfully")
        
        self.polling_thread = None
        self.logger.info("Telegram bot stopped")
    
    def _polling_loop(self) -> None:
        """Main polling loop"""
        self.logger.info("Starting bot polling loop...")
        
        while self.is_running:
            try:
                # Start polling - this blocks until stopped or error occurs
                self.bot.polling(none_stop=True, timeout=10, long_polling_timeout=10)
                
                # If polling exits without exception, log and retry
                if self.is_running:
                    self.logger.warning("Polling exited unexpectedly, restarting...")
                    time.sleep(5)
                            
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Polling loop error: {e}")
                    # Wait before retrying
                    time.sleep(5)
                    # Continue the loop to retry instead of recursive call
                else:
                    self.logger.info("Polling loop interrupted due to shutdown")
                    break
        
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
        except:
            return False