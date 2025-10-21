"""
Vector Search Manager for Bot Container

AICODE-NOTE: BOT's responsibility - WHEN to update vector search
This module manages vector search integration in the bot container:
1. Checks availability of vector search tools via MCP Hub API
2. Monitors knowledge base changes (events + periodic checks)
3. Decides WHEN to call MCP Hub for vector DB updates
4. Tracks file changes to determine which documents need updates

The actual vector search operations (SEARCH, ADD, DELETE, UPDATE) are
provided by MCP Hub. BOT only decides when to trigger these operations.

Architecture:
- MCP HUB = provides vector search tools (WHAT)
- BOT = monitors KB and decides when to use MCP Hub tools (WHEN)
"""

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from config import settings
from src.core.events import EventType, KBChangeEvent, get_event_bus

from .file_change_monitor import FileChangeMonitor
from .mcp_hub_client import MCPHubClient, MCPHubError, MCPHubUnavailableError
from .mcp_vector_operations import MCPVectorOperations
from .knowledge_base_change import KnowledgeBaseChange


class BotVectorSearchManager:
    """
    Bot-side Vector Search Manager

    Manages vector search operations from the bot container:
    - Checks MCP Hub for vector search availability
    - Triggers indexing via MCP Hub API
    - Monitors KB changes for reindexing
    """

    def __init__(self, mcp_hub_url: str, kb_root_path: Path, subscribe_to_events: bool = True):
        """
        Initialize bot vector search manager

        Args:
            mcp_hub_url: MCP Hub base URL (e.g., http://mcp-hub:8765)
            kb_root_path: Root path to knowledge bases
            subscribe_to_events: Whether to subscribe to KB change events (default: True)
        """
        self.mcp_hub_url = mcp_hub_url.rstrip("/sse").rstrip("/")  # Remove /sse if present
        self.kb_root_path = Path(kb_root_path)
        self.vector_search_available = False
        self._reindex_lock = asyncio.Lock()  # Lock to prevent concurrent reindexing
        self._reindex_task: Optional["asyncio.Task[None]"] = None  # Track ongoing reindex
        self._shutdown = False  # Shutdown flag

        # Initialize components with separated responsibilities
        self._mcp_client = MCPHubClient(self.mcp_hub_url)
        self._file_monitor = FileChangeMonitor(
            kb_root_path=kb_root_path, hash_file=Path("data/vector_search_hashes.json")
        )
        self._mcp_operations = MCPVectorOperations(self._mcp_client)

        # Subscribe to KB change events for reactive reindexing
        if subscribe_to_events:
            self._subscribe_to_kb_events()

    async def check_vector_search_availability(self) -> bool:
        """
        Check if vector search tools are available via MCP Hub

        Returns:
            True if vector_search and reindex_vector tools are available
        """
        logger.info(f"🔍 Checking vector search availability at {self.mcp_hub_url}")

        # Use MCP operations component for availability check
        self.vector_search_available = await self._mcp_operations.check_availability()

        if self.vector_search_available:
            logger.info("ℹ️  Vector indexing operations available via HTTP API")

        return self.vector_search_available

    async def perform_initial_indexing(self, force: bool = False) -> bool:
        """
        Perform initial indexing of all knowledge bases

        AICODE-NOTE: SOLID - Single Responsibility Principle
        BOT reads files (has file system access) and sends DATA to MCP HUB.
        MCP HUB creates embeddings and manages vector DB.

        Args:
            force: Force reindexing even if index exists

        Returns:
            True if indexing succeeded
        """
        if not self.vector_search_available:
            logger.info("⏭️  Skipping initial indexing: vector search not available")
            return False

        try:
            logger.info("🔄 Starting initial knowledge base indexing (bot-triggered)...")

            # Load current file hashes and scan current state (for change tracking)
            await self._file_monitor.load_file_hashes()
            await self._file_monitor._scan_knowledge_bases()

            # Read all files and prepare documents
            documents = await self._file_monitor.read_all_documents()

            logger.info(f"📚 Prepared {len(documents)} documents for indexing")

            # Trigger reindex via MCP Hub with document data
            ok = await self._mcp_operations.reindex_documents(documents=documents, force=force)
            if not ok:
                return False

            # Persist hash snapshot after successful trigger
            await self._file_monitor.save_file_hashes()
            return True

        except Exception as e:
            logger.error(f"❌ Initial indexing failed: {e}", exc_info=True)
            return False

    async def check_and_reindex_changes(self) -> bool:
        """
        Check for changes in knowledge bases and call MCP Hub for updates

        AICODE-NOTE: BOT's core responsibility - WHEN to update vector search.
        This compares current file hashes with stored hashes to detect:
        - New files (added) -> calls add_vector_documents
        - Modified files (hash changed) -> calls update_vector_documents
        - Deleted files (no longer exist) -> calls delete_vector_documents

        MCP HUB handles the actual indexing/updating operations.

        Returns:
            True if changes were processed successfully
        """
        if not self.vector_search_available or self._shutdown:
            return False

        try:
            # Use file monitor to detect changes
            changes = await self._file_monitor.detect_changes()

            if not changes.has_changes():
                logger.debug("✓ No changes detected in knowledge bases")
                return False

            logger.info(f"📝 Detected changes: {changes}")
            logger.info(
                f"   Added: {len(changes.added)}, "
                f"Modified: {len(changes.modified)}, "
                f"Deleted: {len(changes.deleted)}"
            )

            # Call MCP Hub for each type of change
            all_ok = True

            # Delete removed files (only document IDs needed)
            if changes.deleted:
                logger.info(f"🗑️  Calling MCP Hub to delete {len(changes.deleted)} documents")
                ok = await self._mcp_operations.delete_documents(list(changes.deleted))
                all_ok = all_ok and ok

            # Add new files (read content and send)
            if changes.added:
                logger.info(f"➕ Reading {len(changes.added)} new files...")
                documents = await self._file_monitor.read_documents_by_paths(list(changes.added))
                logger.info(f"➕ Calling MCP Hub to add {len(documents)} documents")
                ok = await self._mcp_operations.add_documents(documents)
                all_ok = all_ok and ok

            # Update modified files (read content and send)
            if changes.modified:
                logger.info(f"🔄 Reading {len(changes.modified)} modified files...")
                documents = await self._file_monitor.read_documents_by_paths(list(changes.modified))
                logger.info(f"🔄 Calling MCP Hub to update {len(documents)} documents")
                ok = await self._mcp_operations.update_documents(documents)
                all_ok = all_ok and ok

            # FIX: Only save hashes if all MCP operations succeeded
            if all_ok:
                await self._file_monitor.save_file_hashes()
                logger.info("✅ All MCP operations succeeded, hashes saved")
            else:
                logger.warning(
                    "⚠️ Some MCP operations failed, hashes not saved to retry on next check"
                )

            if all_ok:
                logger.info("✅ Change detection completed, all updates successful")
            else:
                logger.warning("⚠️ Some updates failed; hashes updated, will retry on next event")
            return all_ok

        except Exception as e:
            logger.error(f"❌ Failed to check/reindex changes: {e}", exc_info=True)
            return False

    def _subscribe_to_kb_events(self) -> None:
        """Subscribe to knowledge base change events for reactive reindexing"""
        event_bus = get_event_bus()

        # Subscribe to file change events
        event_bus.subscribe_async(EventType.KB_FILE_CREATED, self._handle_kb_change_event)
        event_bus.subscribe_async(EventType.KB_FILE_MODIFIED, self._handle_kb_change_event)
        event_bus.subscribe_async(EventType.KB_FILE_DELETED, self._handle_kb_change_event)

        # Subscribe to batch changes (more efficient for multiple files)
        event_bus.subscribe_async(EventType.KB_BATCH_CHANGES, self._handle_kb_change_event)

        # Subscribe to git events (might involve multiple files)
        event_bus.subscribe_async(EventType.KB_GIT_COMMIT, self._handle_kb_change_event)
        event_bus.subscribe_async(EventType.KB_GIT_PULL, self._handle_kb_change_event)

        logger.info("📡 Subscribed to KB change events for reactive reindexing")

    async def _handle_kb_change_event(self, event: KBChangeEvent) -> None:
        """
        Handle KB change event - trigger reindexing

        AICODE-NOTE: This is called automatically when KB files change.
        Uses a lock and task cancellation to batch multiple rapid changes together.
        Only one reindex can run at a time; new events cancel pending reindex tasks.

        Args:
            event: KB change event
        """
        if not self.vector_search_available or self._shutdown:
            return

        logger.debug(f"📬 Received KB change event: {event.type.value}")

        # FIX: Use lock to prevent race conditions
        async with self._reindex_lock:
            # Cancel any pending reindex task (to batch rapid changes)
            if self._reindex_task and not self._reindex_task.done():
                logger.debug("⏸️  Cancelling pending reindex task to batch changes")
                self._reindex_task.cancel()
                try:
                    await self._reindex_task
                except asyncio.CancelledError:
                    pass

            # Schedule new reindex task with a delay to batch rapid changes
            self._reindex_task = asyncio.create_task(self._delayed_reindex(event))

    async def _delayed_reindex(self, event: KBChangeEvent) -> None:
        """
        Perform reindexing after a delay to batch multiple changes

        Args:
            event: KB change event that triggered this reindex
        """
        try:
            # Wait to batch multiple rapid changes
            await asyncio.sleep(2)

            if self._shutdown:
                return

            logger.info(f"🔄 Triggering reactive reindexing due to {event.type.value}")

            await self.check_and_reindex_changes()
            logger.info("✅ Reactive reindexing completed")

        except asyncio.CancelledError:
            logger.debug("⏹️  Reindex task cancelled (batching changes)")
        except Exception as e:
            logger.error(f"❌ Reactive reindexing failed: {e}", exc_info=True)

    async def trigger_reindex(self) -> bool:
        """
        Manually trigger reindexing

        This can be called from anywhere to force a reindex check.
        Useful for external triggers or API endpoints.
        Uses a lock to prevent concurrent reindexing.

        Returns:
            True if reindexing was performed
        """
        if not self.vector_search_available or self._shutdown:
            logger.warning("⚠️  Vector search not available or shutting down, skipping reindex")
            return False

        async with self._reindex_lock:
            logger.info("🔄 Manual reindex triggered")
            return await self.check_and_reindex_changes()

    async def shutdown(self) -> None:
        """
        Shutdown the vector search manager

        Cancels any pending reindex tasks and marks manager as shutdown.
        """
        logger.info("🛑 Shutting down BotVectorSearchManager")
        self._shutdown = True

        # Cancel pending reindex task
        if self._reindex_task and not self._reindex_task.done():
            logger.debug("⏹️  Cancelling pending reindex task")
            self._reindex_task.cancel()
            try:
                await self._reindex_task
            except asyncio.CancelledError:
                pass

        # Close HTTP client
        await self._mcp_client.close()

    async def shutdown(self) -> None:
        """
        Shutdown the vector search manager

        Cancels any pending reindex tasks and marks manager as shutdown.
        """
        logger.info("🛑 Shutting down BotVectorSearchManager")
        self._shutdown = True

        # Cancel pending reindex task
        if self._reindex_task and not self._reindex_task.done():
            logger.debug("⏹️  Cancelling pending reindex task")
            self._reindex_task.cancel()
            try:
                await self._reindex_task
            except asyncio.CancelledError:
                pass

        # Close HTTP client
        await self._mcp_client.close()

        logger.info("✅ BotVectorSearchManager shutdown complete")

    async def start_monitoring(self, check_interval: int = 300) -> None:
        """
        Start periodic monitoring of knowledge bases for changes

        AICODE-NOTE: This is a fallback mechanism for changes that might be missed
        by event system (e.g., external file modifications, NFS mounts, etc.).
        The primary change detection is event-driven via _handle_kb_change_event().

        Args:
            check_interval: Interval in seconds between checks (default: 5 minutes)
        """
        if not self.vector_search_available:
            logger.info("⏭️  Skipping periodic monitoring: vector search not available")
            return

        logger.info(
            f"👁️  Starting periodic KB monitoring (checking every {check_interval}s as fallback)..."
        )
        logger.info("   Primary change detection is event-driven (reactive)")

        while not self._shutdown:
            try:
                await asyncio.sleep(check_interval)
                if not self._shutdown:
                    await self.check_and_reindex_changes()
            except asyncio.CancelledError:
                logger.info("🛑 Periodic KB monitoring stopped")
                break
            except Exception as e:
                logger.error(f"❌ Error in periodic KB monitoring: {e}", exc_info=True)
                # Continue monitoring despite errors


async def initialize_vector_search_for_bot(
    mcp_hub_url: str, kb_root_path: Path, start_monitoring: bool = True
) -> Optional[BotVectorSearchManager]:
    """
    Initialize vector search for bot container

    This is the main entry point called from main.py during bot startup.

    Args:
        mcp_hub_url: MCP Hub URL (e.g., http://mcp-hub:8765/sse)
        kb_root_path: Root path to knowledge bases
        start_monitoring: Whether to start background monitoring

    Returns:
        BotVectorSearchManager if vector search is available, None otherwise
    """
    # Check if vector search is enabled in config
    if not settings.VECTOR_SEARCH_ENABLED:
        logger.info("ℹ️  Vector search is disabled in configuration (VECTOR_SEARCH_ENABLED: false)")
        return None

    # Create manager
    manager = BotVectorSearchManager(mcp_hub_url, kb_root_path)

    # Check availability
    available = await manager.check_vector_search_availability()

    if not available:
        logger.info("ℹ️  Vector search tools not available in MCP Hub, skipping initialization")
        return None

    # Perform initial indexing
    logger.info("🚀 Initializing vector search for bot container...")
    await manager.perform_initial_indexing(force=False)

    # Start monitoring in background
    if start_monitoring:
        asyncio.create_task(manager.start_monitoring())
        logger.info("✅ Vector search initialized and monitoring started")
    else:
        logger.info("✅ Vector search initialized (monitoring disabled)")

    return manager
