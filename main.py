"""
tg-note: Telegram Bot Entry Point
Main entry point for the Telegram bot application
"""

import asyncio
import logging
import sys
from pathlib import Path

from config import settings
from src.tracker.processing_tracker import ProcessingTracker
from src.knowledge_base.manager import KnowledgeBaseManager
from src.knowledge_base.git_ops import GitOperations
from src.bot.telegram_bot import TelegramBot

# Configure logging
def setup_logging():
    """Setup logging configuration"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Add file handler if log file is configured
    if settings.LOG_FILE:
        settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(settings.LOG_FILE))
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )


def validate_configuration():
    """Validate application configuration"""
    logger = logging.getLogger(__name__)
    
    errors = settings.validate()
    
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    logger.info("Configuration validated successfully")
    logger.info(f"Settings: {settings}")
    return True


async def main():
    """Main application entry point"""
    logger = logging.getLogger(__name__)
    
    # Setup logging
    setup_logging()
    logger.info("Starting tg-note bot...")
    
    # Validate configuration
    if not validate_configuration():
        logger.error("Exiting due to configuration errors")
        sys.exit(1)
    
    # Initialize components
    logger.info("Initializing components...")
    
    telegram_bot = None
    try:
        # Initialize Processing Tracker
        tracker = ProcessingTracker(str(settings.PROCESSED_LOG_PATH))
        logger.info(f"Processing tracker initialized: {settings.PROCESSED_LOG_PATH}")
        
        # Initialize Knowledge Base Manager
        kb_manager = KnowledgeBaseManager(str(settings.KB_PATH))
        logger.info(f"Knowledge base manager initialized: {settings.KB_PATH}")
        
        # Initialize Git Operations
        git_ops = GitOperations(
            str(settings.KB_PATH),
            enabled=settings.KB_GIT_ENABLED
        )
        logger.info(f"Git operations initialized (enabled: {settings.KB_GIT_ENABLED})")
        
        # Get initial stats
        stats = tracker.get_stats()
        logger.info(f"Processing stats: {stats}")
        
        # Initialize Telegram Bot
        telegram_bot = TelegramBot(tracker, kb_manager)
        telegram_bot.start()
        logger.info("Telegram bot started successfully")
        
        logger.info("Bot initialization completed")
        logger.info("Press Ctrl+C to stop")
        
        # Keep running until interrupted
        try:
            health_check_interval = 30  # Check health every 30 seconds instead of every second
            last_health_check = asyncio.get_running_loop().time()  # Initialize to current time
            
            while True:
                await asyncio.sleep(1)
                
                # Check bot health periodically (every 30 seconds)
                current_time = asyncio.get_running_loop().time()
                if current_time - last_health_check >= health_check_interval:
                    last_health_check = current_time
                    
                    if not telegram_bot.is_healthy():
                        logger.warning("Bot health check failed, attempting restart...")
                        await asyncio.to_thread(telegram_bot.stop)
                        await asyncio.sleep(5)  # Wait for complete shutdown
                        await asyncio.to_thread(telegram_bot.start)
                        logger.info("Bot restarted successfully")
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            if telegram_bot:
                telegram_bot.stop()
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal during initialization, shutting down...")
        if telegram_bot:
            telegram_bot.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        if telegram_bot:
            telegram_bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
        sys.exit(0)