"""
Telegram Bot Implementation
Main bot class using pyTelegramBotAPI with async support
"""

import asyncio
from typing import Optional
from telebot.async_telebot import AsyncTeleBot
from telebot.apihelper import ApiTelegramException
from loguru import logger

from src.bot.handlers import BotHandlers
from src.bot.settings_handlers import SettingsHandlers
from src.tracker.processing_tracker import ProcessingTracker
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.user_settings import UserSettings
from src.bot.settings_manager import SettingsManager
from src.services.interfaces import IUserContextManager, IMessageProcessor


class TelegramBot:
    """Main Telegram bot class with async support"""
    
    def __init__(
        self,
        bot: AsyncTeleBot,
        tracker: ProcessingTracker,
        repo_manager: RepositoryManager,
        user_settings: UserSettings,
        settings_manager: SettingsManager,
        user_context_manager: IUserContextManager,
        message_processor: IMessageProcessor,
    ):
        self.bot = bot
        self.tracker = tracker
        self.repo_manager = repo_manager
        self.user_settings = user_settings
        self.settings_manager = settings_manager
        self.user_context_manager = user_context_manager
        self.message_processor = message_processor
        
        # Initialize handlers (with cross-references for cache invalidation)
        self.handlers = BotHandlers(
            bot=self.bot,
            tracker=tracker,
            repo_manager=repo_manager,
            user_settings=user_settings,
            settings_manager=settings_manager,
            user_context_manager=user_context_manager,
            message_processor=message_processor,
            settings_handlers=None,
        )
        self.settings_handlers = SettingsHandlers(self.bot, self.handlers)
        # Update the settings_handlers reference in handlers
        self.handlers.settings_handlers = self.settings_handlers
        
        # Bot state
        self.is_running = False
        self._polling_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the bot (async)"""
        logger.info("Starting Telegram bot...")
        
        # Ensure any existing bot is stopped first
        if self.is_running:
            logger.warning("Bot is already running, stopping first...")
            await self.stop()
        
        try:
            # Test bot connection with timeout
            bot_info = await asyncio.wait_for(
                self.bot.get_me(),
                timeout=30  # 30 second timeout for initial connection
            )
            logger.info(f"Bot connected: @{bot_info.username} ({bot_info.first_name})")
            
            # Start background tasks for message aggregator
            self.handlers.start_background_tasks()
            
            # Register handlers - settings handlers first for proper priority
            await self.settings_handlers.register_handlers_async()
            await self.handlers.register_handlers_async()
            
            # Start polling
            self.is_running = True
            self._polling_task = asyncio.create_task(self._polling_loop())
            
            logger.info("Telegram bot started successfully")
            
        except asyncio.TimeoutError:
            logger.error("Failed to connect to Telegram API: Connection timeout")
            self.is_running = False
            raise
        except ApiTelegramException as e:
            logger.error(f"Failed to connect to Telegram API: {e}")
            self.is_running = False
            raise
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            self.is_running = False
            raise
    
    async def stop(self) -> None:
        """Stop the bot (async)"""
        if not self.is_running:
            logger.info("Bot is already stopped")
            return
            
        logger.info("Stopping Telegram bot...")
        
        self.is_running = False
        
        # Stop background tasks
        try:
            self.handlers.stop_background_tasks()
        except Exception as e:
            logger.warning(f"Error stopping background tasks: {e}")
        
        # Cancel polling task
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        
        self._polling_task = None
        logger.info("Telegram bot stopped")
    
    async def _polling_loop(self) -> None:
        """Main async polling loop"""
        logger.info("Starting bot polling loop...")
        
        while self.is_running:
            try:
                # Use async polling with infinity_polling
                await self.bot.infinity_polling(
                    timeout=10,
                    request_timeout=20,
                    logger_level=20  # INFO level
                )
                
                # If polling exits without exception, log and retry
                if self.is_running:
                    logger.warning("Polling exited unexpectedly, restarting...")
                    await asyncio.sleep(5)
                            
            except asyncio.CancelledError:
                logger.info("Polling loop cancelled")
                break
            except Exception as e:
                if self.is_running:
                    logger.error(f"Polling loop error: {e}")
                    # Wait before retrying
                    await asyncio.sleep(5)
                else:
                    logger.info("Polling loop interrupted due to shutdown")
                    break
        
        logger.info("Bot polling loop ended")
    
    async def send_message(self, chat_id: int, text: str, **kwargs):
        """Send a message to a chat (async)"""
        try:
            return await self.bot.send_message(chat_id, text, **kwargs)
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
    
    async def is_healthy(self, timeout: int = 10) -> bool:
        """Check if bot is healthy (async)
        
        Args:
            timeout: Timeout in seconds for the health check (default: 10s)
            
        Returns:
            True if bot is healthy, False otherwise
        """
        try:
            # Use a shorter timeout for health checks to avoid blocking
            await asyncio.wait_for(
                self.bot.get_me(),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Health check timed out after {timeout}s")
            return False
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
