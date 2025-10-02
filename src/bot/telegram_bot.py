"""
Telegram Bot Implementation
Main bot class using pyTelegramBotAPI with async support
"""

import asyncio
import logging
from typing import Optional
from telebot.async_telebot import AsyncTeleBot
from telebot.apihelper import ApiTelegramException

from config import settings
from src.bot.handlers import BotHandlers
from src.tracker.processing_tracker import ProcessingTracker
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.user_settings import UserSettings


class TelegramBot:
    """Main Telegram bot class with async support"""
    
    def __init__(
        self, 
        tracker: ProcessingTracker,
        repo_manager: RepositoryManager,
        user_settings: UserSettings
    ):
        self.tracker = tracker
        self.repo_manager = repo_manager
        self.user_settings = user_settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize async bot
        self.bot = AsyncTeleBot(settings.TELEGRAM_BOT_TOKEN)
        
        # Initialize handlers
        self.handlers = BotHandlers(self.bot, tracker, repo_manager, user_settings)
        
        # Bot state
        self.is_running = False
        self._polling_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the bot (async)"""
        self.logger.info("Starting Telegram bot...")
        
        # Ensure any existing bot is stopped first
        if self.is_running:
            self.logger.warning("Bot is already running, stopping first...")
            await self.stop()
        
        try:
            # Test bot connection
            bot_info = await self.bot.get_me()
            self.logger.info(f"Bot connected: @{bot_info.username} ({bot_info.first_name})")
            
            # Start background tasks for message aggregator
            self.handlers.start_background_tasks()
            
            # Register handlers
            await self.handlers.register_handlers_async()
            
            # Start polling
            self.is_running = True
            self._polling_task = asyncio.create_task(self._polling_loop())
            
            self.logger.info("Telegram bot started successfully")
            
        except ApiTelegramException as e:
            self.logger.error(f"Failed to connect to Telegram API: {e}")
            self.is_running = False
            raise
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            self.is_running = False
            raise
    
    async def stop(self) -> None:
        """Stop the bot (async)"""
        if not self.is_running:
            self.logger.info("Bot is already stopped")
            return
            
        self.logger.info("Stopping Telegram bot...")
        
        self.is_running = False
        
        # Stop background tasks
        try:
            self.handlers.stop_background_tasks()
        except Exception as e:
            self.logger.warning(f"Error stopping background tasks: {e}")
        
        # Cancel polling task
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        
        self._polling_task = None
        self.logger.info("Telegram bot stopped")
    
    async def _polling_loop(self) -> None:
        """Main async polling loop"""
        self.logger.info("Starting bot polling loop...")
        
        while self.is_running:
            try:
                # Use async polling with infinity_polling
                await self.bot.infinity_polling(
                    timeout=10,
                    request_timeout=20,
                    logger_level=logging.INFO
                )
                
                # If polling exits without exception, log and retry
                if self.is_running:
                    self.logger.warning("Polling exited unexpectedly, restarting...")
                    await asyncio.sleep(5)
                            
            except asyncio.CancelledError:
                self.logger.info("Polling loop cancelled")
                break
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Polling loop error: {e}")
                    # Wait before retrying
                    await asyncio.sleep(5)
                else:
                    self.logger.info("Polling loop interrupted due to shutdown")
                    break
        
        self.logger.info("Bot polling loop ended")
    
    async def send_message(self, chat_id: int, text: str, **kwargs):
        """Send a message to a chat (async)"""
        try:
            return await self.bot.send_message(chat_id, text, **kwargs)
        except Exception as e:
            self.logger.error(f"Failed to send message to {chat_id}: {e}")
    
    async def is_healthy(self) -> bool:
        """Check if bot is healthy (async)"""
        try:
            await self.bot.get_me()
            return True
        except Exception:
            return False
