"""
tg-note: Telegram Bot Entry Point
Main entry point for the Telegram bot application
"""

import asyncio
import os
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
        enable_debug_trace=settings.LOG_LEVEL.upper() == "DEBUG",
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

            # In Docker mode, wait for MCP Hub health and then log available MCP servers
            mcp_hub_url = os.environ.get("MCP_HUB_URL")
            if mcp_hub_url:
                try:
                    await _wait_for_mcp_hub_ready_and_log_servers(mcp_hub_url)
                except Exception as e:
                    logger.warning(f"MCP Hub health check failed: {e}")
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


# Helpers
async def _wait_for_mcp_hub_ready_and_log_servers(mcp_hub_sse_url: str, timeout_seconds: int = 60):
    """Wait until MCP Hub /health is ready, then log available MCP servers.

    Args:
        mcp_hub_sse_url: SSE URL (e.g., http://mcp-hub:8765/sse)
        timeout_seconds: Max time to wait
    """
    from urllib.parse import urlsplit, urlunsplit

    import aiohttp

    parts = urlsplit(mcp_hub_sse_url)
    base = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
    health_url = f"{base}/health"
    list_url = f"{base}/registry/servers"

    logger.info(f"Waiting for MCP Hub health at {health_url} ...")

    deadline = asyncio.get_running_loop().time() + timeout_seconds
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status = data.get("status")
                        ready = data.get("ready", False)
                        if status == "ok" and ready:
                            builtin = data.get("builtin_tools", {})
                            registry = data.get("registry", {})
                            logger.info(
                                f"MCP Hub healthy: builtin_tools={builtin.get('total', 0)}, "
                                f"mcp_servers_total={registry.get('servers_total',0)}, "
                                f"mcp_servers_enabled={registry.get('servers_enabled',0)}"
                            )
                            break
            except Exception:
                pass

            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("Timed out waiting for MCP Hub to become healthy")
            await asyncio.sleep(1)

        # Fetch and log available servers and tools
        try:
            async with session.get(list_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    servers = data.get("servers", [])
                    if not servers:
                        logger.info("No external MCP servers registered in hub.")
                    else:
                        brief = ", ".join(
                            [
                                f"{srv.get('name')}({'on' if srv.get('enabled') else 'off'})"
                                for srv in servers
                            ]
                        )
                        logger.info(f"External MCP servers available: {brief}")
                else:
                    logger.warning(f"Failed to fetch MCP servers list: HTTP {resp.status}")
        except Exception as e:
            logger.warning(f"Error fetching MCP servers list: {e}")

        # Log built-in tools
        try:
            async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    builtin = data.get("builtin_tools", {})
                    tools_count = builtin.get("total", 0)
                    tools_names = builtin.get("names", [])
                    if tools_count > 0:
                        logger.info(
                            f"Built-in tools available ({tools_count}): {', '.join(tools_names)}"
                        )
                    else:
                        logger.warning("No built-in tools available")
        except Exception as e:
            logger.warning(f"Error fetching built-in tools info: {e}")


if __name__ == "__main__":
    cli_main()
