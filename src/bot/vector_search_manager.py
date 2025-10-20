"""
Vector Search Manager for Bot Container

This module manages vector search integration in the bot container:
1. Checks availability of vector search tools via MCP Hub API
2. Performs initial indexing of all knowledge bases on startup
3. Monitors knowledge base changes and reindexes when needed
4. Provides incremental reindexing based on file diffs

AICODE-NOTE: This is the bot-side manager that coordinates with MCP Hub.
The actual vector search implementation is in src/mcp/mcp_hub_server.py
and src/vector_search/.
"""

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

import aiohttp
from loguru import logger

from config import settings
from src.core.events import EventType, KBChangeEvent, get_event_bus
from src.mcp.client import MCPClient, MCPServerConfig


class KnowledgeBaseChange:
    """Represents a change in knowledge base files"""

    def __init__(self):
        self.added: Set[str] = set()
        self.modified: Set[str] = set()
        self.deleted: Set[str] = set()

    def has_changes(self) -> bool:
        """Check if there are any changes"""
        return bool(self.added or self.modified or self.deleted)

    def __repr__(self) -> str:
        return f"KBChange(added={len(self.added)}, modified={len(self.modified)}, deleted={len(self.deleted)})"


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
        self._file_hashes: Dict[str, str] = {}  # file_path -> hash
        self._hash_file = Path("data/vector_search_hashes.json")
        self._reindex_pending = False  # Flag to batch multiple changes
        
        # Subscribe to KB change events for reactive reindexing
        if subscribe_to_events:
            self._subscribe_to_kb_events()

    async def check_vector_search_availability(self) -> bool:
        """
        Check if vector search tools are available via MCP Hub

        Returns:
            True if vector_search and reindex_vector tools are available
        """
        try:
            health_url = f"{self.mcp_hub_url}/health"
            logger.info(f"🔍 Checking vector search availability at {health_url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    health_url, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"⚠️  MCP Hub health check failed with status {resp.status}"
                        )
                        return False

                    data = await resp.json()
                    builtin_tools = data.get("builtin_tools", {})
                    available_tools = builtin_tools.get("names", [])

                    # Check if both vector search tools are available
                    has_search = "vector_search" in available_tools
                    has_reindex = "reindex_vector" in available_tools

                    if has_search and has_reindex:
                        logger.info(
                            "✅ Vector search tools are available: vector_search, reindex_vector"
                        )
                        self.vector_search_available = True
                        return True
                    else:
                        logger.info(
                            f"ℹ️  Vector search tools not available. "
                            f"Available tools: {', '.join(available_tools) if available_tools else 'none'}"
                        )
                        self.vector_search_available = False
                        return False

        except Exception as e:
            logger.warning(f"⚠️  Failed to check vector search availability: {e}")
            self.vector_search_available = False
            return False

    async def perform_initial_indexing(self, force: bool = False) -> bool:
        """
        Perform initial indexing of all knowledge bases

        This calls the MCP Hub reindex_vector tool to index all KBs.

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

            # Load current file hashes and scan current state (for change tracking only)
            await self._load_file_hashes()
            await self._scan_knowledge_bases()

            # Trigger reindex via MCP Hub
            ok = await self._call_mcp_reindex(force=force)
            if not ok:
                return False

            # Persist hash snapshot after successful trigger
            await self._save_file_hashes()
            return True

        except Exception as e:
            logger.error(f"❌ Initial indexing failed: {e}", exc_info=True)
            return False

    async def check_and_reindex_changes(self) -> bool:
        """
        Check for changes in knowledge bases and reindex if needed

        This compares current file hashes with stored hashes to detect:
        - New files (added)
        - Modified files (hash changed)
        - Deleted files (no longer exist)

        Returns:
            True if reindexing was performed
        """
        if not self.vector_search_available:
            return False

        try:
            # Load previous hashes
            previous_hashes = self._file_hashes.copy()

            # Scan current state
            await self._scan_knowledge_bases()
            current_hashes = self._file_hashes

            # Detect changes
            changes = self._detect_changes(previous_hashes, current_hashes)

            if not changes.has_changes():
                logger.debug("✓ No changes detected in knowledge bases")
                return False

            logger.info(f"📝 Detected changes: {changes}")
            logger.info(
                f"   Added: {len(changes.added)}, "
                f"Modified: {len(changes.modified)}, "
                f"Deleted: {len(changes.deleted)}"
            )

            # Trigger reindexing (incremental by default; manager will full-rebuild if needed)
            logger.info("🔄 Triggering MCP reindex due to detected changes...")
            ok = await self._call_mcp_reindex(force=False)

            # Save updated hashes snapshot regardless of MCP outcome to avoid duplicate work next time
            await self._save_file_hashes()

            if ok:
                logger.info("✅ Change detection completed, reindex triggered and hashes updated")
            else:
                logger.warning("⚠️ Reindex trigger failed; hashes updated, will retry on next event")
            return ok

        except Exception as e:
            logger.error(f"❌ Failed to check/reindex changes: {e}", exc_info=True)
            return False

    async def _scan_knowledge_bases(self) -> None:
        """Scan all knowledge bases and compute file hashes"""
        self._file_hashes.clear()

        if not self.kb_root_path.exists():
            logger.warning(f"⚠️  KB root path does not exist: {self.kb_root_path}")
            return

        # Find all markdown files in all KBs
        # Each user KB is at kb_root_path/user_{user_id}/
        markdown_files = list(self.kb_root_path.rglob("*.md"))

        for file_path in markdown_files:
            try:
                # Compute relative path for consistent tracking
                rel_path = str(file_path.relative_to(self.kb_root_path))

                # Compute file hash
                content = file_path.read_bytes()
                file_hash = hashlib.md5(content).hexdigest()

                self._file_hashes[rel_path] = file_hash

            except Exception as e:
                logger.warning(f"⚠️  Failed to hash file {file_path}: {e}")

        logger.debug(f"📊 Scanned {len(self._file_hashes)} markdown files")

    def _detect_changes(
        self, previous: Dict[str, str], current: Dict[str, str]
    ) -> KnowledgeBaseChange:
        """
        Detect changes between previous and current file states

        Args:
            previous: Previous file hashes
            current: Current file hashes

        Returns:
            KnowledgeBaseChange with detected changes
        """
        changes = KnowledgeBaseChange()

        # Find new and modified files
        for file_path, current_hash in current.items():
            if file_path not in previous:
                changes.added.add(file_path)
            elif previous[file_path] != current_hash:
                changes.modified.add(file_path)

        # Find deleted files
        for file_path in previous:
            if file_path not in current:
                changes.deleted.add(file_path)

        return changes

    async def _load_file_hashes(self) -> None:
        """Load file hashes from storage"""
        try:
            if self._hash_file.exists():
                with open(self._hash_file, "r") as f:
                    self._file_hashes = json.load(f)
                logger.debug(f"📥 Loaded {len(self._file_hashes)} file hashes")
            else:
                self._file_hashes = {}
                logger.debug("📝 No previous file hashes found")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load file hashes: {e}")
            self._file_hashes = {}

    async def _save_file_hashes(self) -> None:
        """Save file hashes to storage"""
        try:
            self._hash_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._hash_file, "w") as f:
                json.dump(self._file_hashes, f, indent=2)
            logger.debug(f"💾 Saved {len(self._file_hashes)} file hashes")
        except Exception as e:
            logger.error(f"❌ Failed to save file hashes: {e}", exc_info=True)

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

    async def _call_mcp_reindex(self, force: bool = False) -> bool:
        """Call MCP Hub reindex_vector tool via SSE transport."""
        try:
            # Ensure SSE URL
            sse_url = self.mcp_hub_url
            if not sse_url.endswith("/sse"):
                sse_url = f"{sse_url}/sse"

            client = MCPClient(MCPServerConfig(transport="sse", url=sse_url))
            connected = await client.connect()
            if not connected:
                logger.warning("⚠️ Failed to connect to MCP Hub for reindex")
                return False

            try:
                result = await client.call_tool("reindex_vector", {"force": bool(force)})
                if result.get("success"):
                    logger.info("✅ MCP reindex_vector completed successfully")
                    return True
                else:
                    logger.warning(f"⚠️ MCP reindex_vector failed: {result.get('error')}")
                    return False
            finally:
                await client.disconnect()
        except Exception as e:
            logger.error(f"❌ Exception while calling MCP reindex_vector: {e}", exc_info=True)
            return False

    async def _handle_kb_change_event(self, event: KBChangeEvent) -> None:
        """
        Handle KB change event - trigger reindexing

        AICODE-NOTE: This is called automatically when KB files change.
        Uses a flag to batch multiple rapid changes together.
        
        Args:
            event: KB change event
        """
        if not self.vector_search_available:
            return
        
        logger.debug(f"📬 Received KB change event: {event.type.value}")
        
        # Mark reindex as pending
        self._reindex_pending = True
        
        # Wait a bit to batch multiple rapid changes
        await asyncio.sleep(2)
        
        # If still pending, perform reindex
        if self._reindex_pending:
            self._reindex_pending = False
            logger.info(f"🔄 Triggering reactive reindexing due to {event.type.value}")
            
            try:
                await self.check_and_reindex_changes()
                logger.info("✅ Reactive reindexing completed")
            except Exception as e:
                logger.error(f"❌ Reactive reindexing failed: {e}", exc_info=True)

    async def trigger_reindex(self) -> bool:
        """
        Manually trigger reindexing
        
        This can be called from anywhere to force a reindex check.
        Useful for external triggers or API endpoints.
        
        Returns:
            True if reindexing was performed
        """
        if not self.vector_search_available:
            logger.warning("⚠️  Vector search not available, skipping reindex")
            return False
        
        logger.info("🔄 Manual reindex triggered")
        return await self.check_and_reindex_changes()

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

        while True:
            try:
                await asyncio.sleep(check_interval)
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
        logger.info(
            "ℹ️  Vector search tools not available in MCP Hub, skipping initialization"
        )
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
