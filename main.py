"""
tg-note: Telegram Bot Entry Point
Main entry point for the Telegram bot application
"""

import asyncio
import sys

from loguru import logger

from config import settings
from config.logging_config import setup_logging
from src.core.service_container import create_service_container


def validate_configuration():
    """Validate application configuration"""
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
    """Main application entry point (fully async)"""
    # Setup logging with loguru
    setup_logging(
        log_level=settings.LOG_LEVEL.upper(),
        log_file=settings.LOG_FILE,
        enable_debug_trace=settings.LOG_LEVEL.upper() == "DEBUG"
    )
    logger.info("Starting tg-note bot...")
    
    # Validate configuration
    if not validate_configuration():
        logger.error("Exiting due to configuration errors")
        sys.exit(1)
    
    # Initialize components
    logger.info("Initializing components...")
    
    telegram_bot = None
    mcp_server_manager = None
    try:
        # Create and configure service container
        container = create_service_container()
        logger.info("Service container created and configured")
        
        # Get services from container
        telegram_bot = container.get("telegram_bot")
        tracker = container.get("tracker")
        mcp_server_manager = container.get("mcp_server_manager")
        
        # Auto-start MCP servers if enabled
        if settings.AGENT_ENABLE_MCP or settings.AGENT_ENABLE_MCP_MEMORY:
            logger.info("MCP is enabled, auto-starting MCP servers...")
            await mcp_server_manager.auto_start_servers()
        else:
            logger.debug("MCP is disabled, skipping MCP server startup")
        
        # Get initial stats
        stats = tracker.get_stats()
        logger.info(f"Processing stats: {stats}")
        
        # Start Telegram Bot (async)
        await telegram_bot.start()
        logger.info("Telegram bot started successfully")
        
        logger.info("Bot initialization completed")
        logger.info("Press Ctrl+C to stop")
        
        # Keep running until interrupted
        health_check_interval = 30  # Check health every 30 seconds
        last_health_check = asyncio.get_running_loop().time()
        consecutive_failures = 0
        max_consecutive_failures = 5  # Stop trying after 5 consecutive failures
        base_backoff = 5  # Start with 5 second backoff
        max_backoff = 300  # Max 5 minute backoff
        
        while True:
            await asyncio.sleep(1)
            
            # Check bot health periodically (every 30 seconds)
            current_time = asyncio.get_running_loop().time()
            if current_time - last_health_check >= health_check_interval:
                last_health_check = current_time
                
                # Use shorter timeout for health checks (10s instead of 300s)
                if not await telegram_bot.is_healthy(timeout=10):
                    consecutive_failures += 1
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(
                            f"Bot has failed {consecutive_failures} consecutive health checks. "
                            f"Stopping automatic restart attempts. Manual intervention required."
                        )
                        logger.error(
                            "Possible causes: network issues, Telegram API unavailable, "
                            "invalid bot token, or firewall blocking connection."
                        )
                        # Continue running but stop trying to restart
                        continue
                    
                    # Calculate exponential backoff
                    backoff = min(base_backoff * (2 ** (consecutive_failures - 1)), max_backoff)
                    
                    logger.warning(
                        f"Bot health check failed (attempt {consecutive_failures}/{max_consecutive_failures}), "
                        f"attempting restart after {backoff}s backoff..."
                    )
                    
                    try:
                        await telegram_bot.stop()
                    except Exception as e:
                        logger.error(f"Error during bot stop in health check: {e}", exc_info=True)
                    
                    await asyncio.sleep(backoff)  # Wait with exponential backoff
                    
                    try:
                        await telegram_bot.start()
                        logger.info("Bot restarted successfully")
                        consecutive_failures = 0  # Reset counter on success
                    except Exception as e:
                        logger.error(f"Error during bot start in health check: {e}", exc_info=True)
                        logger.error(
                            f"Failed to restart bot (attempt {consecutive_failures}/{max_consecutive_failures}), "
                            f"will retry after next health check"
                        )
                else:
                    # Reset failure counter on successful health check
                    if consecutive_failures > 0:
                        logger.info("Bot health restored, resetting failure counter")
                        consecutive_failures = 0
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        if mcp_server_manager:
            await mcp_server_manager.cleanup()
        if telegram_bot:
            await telegram_bot.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        if mcp_server_manager:
            await mcp_server_manager.cleanup()
        if telegram_bot:
            await telegram_bot.stop()
        sys.exit(1)


def cli_main():
    """
    Console script entry point for tg-note command
    This is a synchronous wrapper for the async main function
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()
