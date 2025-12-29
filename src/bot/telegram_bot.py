"""
Telegram Bot Implementation
Main bot class using pyTelegramBotAPI with async support
"""

import asyncio
from typing import Optional

from loguru import logger
from telebot.apihelper import ApiTelegramException
from telebot.async_telebot import AsyncTeleBot

from src.bot.bot_port import BotPort
from src.bot.credentials_handlers import CredentialsHandlers
from src.bot.handlers import BotHandlers
from src.bot.kb_handlers import KBHandlers
from src.bot.mcp_handlers import MCPHandlers
from src.bot.scheduled_task_handlers import ScheduledTaskHandlers
from src.bot.settings_handlers import SettingsHandlers
from src.bot.settings_manager import SettingsManager
from src.core.background_task_manager import BackgroundTaskManager
from src.knowledge_base.credentials_manager import CredentialsManager
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.user_settings import UserSettings
from src.mcp.registry.manager import MCPServersManager
from src.services.interfaces import IMessageProcessor, IUserContextManager
from src.services.scheduled_task_service import ScheduledTaskService
from src.services.task_scheduler import TaskScheduler
from src.tracker.processing_tracker import ProcessingTracker


class TelegramBot:
    """Main Telegram bot class with async support"""

    def __init__(
        self,
        bot: AsyncTeleBot,
        bot_adapter: BotPort,
        tracker: ProcessingTracker,
        repo_manager: RepositoryManager,
        user_settings: UserSettings,
        settings_manager: SettingsManager,
        credentials_manager: CredentialsManager,
        user_context_manager: IUserContextManager,
        message_processor: IMessageProcessor,
        background_task_manager: BackgroundTaskManager,
        scheduled_task_service: ScheduledTaskService,
        task_scheduler: TaskScheduler,
    ):
        self.bot = bot
        self.bot_adapter = bot_adapter
        self.tracker = tracker
        self.repo_manager = repo_manager
        self.user_settings = user_settings
        self.settings_manager = settings_manager
        self.credentials_manager = credentials_manager
        self.user_context_manager = user_context_manager
        self.message_processor = message_processor
        self.background_task_manager = background_task_manager
        self.scheduled_task_service = scheduled_task_service
        self.task_scheduler = task_scheduler

        # Initialize handlers (with cross-references for cache invalidation)
        self.handlers = BotHandlers(
            bot=self.bot_adapter,
            async_bot=self.bot,
            tracker=tracker,
            repo_manager=repo_manager,
            user_settings=user_settings,
            settings_manager=settings_manager,
            user_context_manager=user_context_manager,
            message_processor=message_processor,
            settings_handlers=None,
            kb_handlers=None,  # Will be set after KB handlers are created
            mcp_handlers=None,  # Will be set after MCP handlers are created
            scheduled_task_handlers=None,  # Will be set after scheduled task handlers are created
        )
        self.settings_handlers = SettingsHandlers(self.bot, self.handlers)
        # Update the settings_handlers reference in handlers
        self.handlers.settings_handlers = self.settings_handlers

        # Initialize MCP handlers
        self.mcp_manager = MCPServersManager()
        self.mcp_handlers = MCPHandlers(self.bot, self.mcp_manager, self.handlers)
        # Update the mcp_handlers reference in handlers
        self.handlers.mcp_handlers = self.mcp_handlers

        # Initialize KB handlers
        self.kb_handlers = KBHandlers(
            bot=self.bot,
            repo_manager=repo_manager,
            user_settings=user_settings,
            handlers=self.handlers,
        )
        # Update the kb_handlers reference in handlers
        self.handlers.kb_handlers = self.kb_handlers

        # Initialize Credentials handlers
        self.credentials_handlers = CredentialsHandlers(
            bot=self.bot_adapter,
            async_bot=self.bot,
            credentials_manager=self.credentials_manager,
        )

        # Initialize Scheduled Task handlers
        self.scheduled_task_handlers = ScheduledTaskHandlers(
            bot=self.bot,
            task_service=scheduled_task_service,
            user_settings=user_settings,
            handlers=self.handlers,
        )

        # Update cross-references in handlers
        self.handlers.kb_handlers = self.kb_handlers
        self.handlers.mcp_handlers = self.mcp_handlers
        self.handlers.credentials_handlers = self.credentials_handlers
        self.handlers.scheduled_task_handlers = self.scheduled_task_handlers

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
                self.bot.get_me(), timeout=30  # 30 second timeout for initial connection
            )
            logger.info(f"Bot connected: @{bot_info.username} ({bot_info.first_name})")

            # Start background task manager
            self.background_task_manager.start()
            logger.info("Background task manager started")

            # Start background tasks for message aggregator
            self.handlers.start_background_tasks()

            # Register handlers - settings and KB handlers first for proper priority
            await self.settings_handlers.register_handlers_async()
            await self.kb_handlers.register_handlers_async()
            await self.credentials_handlers.register_handlers()
            await self.mcp_handlers.register_handlers_async()
            await self.scheduled_task_handlers.register_handlers_async()
            await self.handlers.register_handlers_async()

            # Load scheduled tasks from config and start scheduler
            await self._initialize_scheduled_tasks()

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
            await self.handlers.stop_background_tasks()
        except Exception as e:
            logger.warning(f"Error stopping background tasks: {e}")

        # Stop background task manager
        try:
            await self.background_task_manager.stop()
            logger.info("Background task manager stopped")
        except Exception as e:
            logger.warning(f"Error stopping background task manager: {e}")

        # Cancel polling task
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

        self._polling_task = None
        # Stop task scheduler
        try:
            await self.task_scheduler.stop()
            logger.info("Task scheduler stopped")
        except Exception as e:
            logger.warning(f"Error stopping task scheduler: {e}")

        logger.info("Telegram bot stopped")

    async def _initialize_scheduled_tasks(self) -> None:
        """Initialize scheduled tasks from config and start scheduler"""
        try:
            from datetime import datetime

            from config import settings

            # Load tasks from config
            if hasattr(settings, "SCHEDULED_TASKS") and settings.SCHEDULED_TASKS:
                config_dict = {"SCHEDULED_TASKS": settings.SCHEDULED_TASKS}
                self.scheduled_task_service.load_tasks_from_config(config_dict)
                logger.info(f"Loaded {len(settings.SCHEDULED_TASKS)} scheduled tasks from config")

                # Calculate and set next_run for all loaded tasks
                now = datetime.now()
                tasks = self.scheduled_task_service.get_all_tasks(enabled_only=True)
                for task in tasks:
                    if task.next_run is None:
                        # Calculate next_run using scheduler's logic
                        next_run = self.task_scheduler._calculate_next_run(task, now)
                        if next_run:
                            task.next_run = next_run
                            self.scheduled_task_service.update_task(task)
                            logger.info(
                                f"Set next_run for task {task.task_id}: {next_run.isoformat()}"
                            )

            # Start scheduler
            self.task_scheduler.start()
            logger.info("Task scheduler started")

        except Exception as e:
            logger.error(f"Failed to initialize scheduled tasks: {e}", exc_info=True)

    async def _polling_loop(self) -> None:
        """Main async polling loop"""
        logger.info("Starting bot polling loop...")

        while self.is_running:
            try:
                # Use async polling with infinity_polling
                await self.bot.infinity_polling(
                    timeout=10, request_timeout=20, logger_level=20  # INFO level
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
            await asyncio.wait_for(self.bot.get_me(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Health check timed out after {timeout}s")
            return False
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
