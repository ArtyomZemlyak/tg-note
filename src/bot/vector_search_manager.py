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
        return (
            f"KBChange(added={len(self.added)}, "
            f"modified={len(self.modified)}, deleted={len(self.deleted)})"
        )


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
        self._reindex_lock = asyncio.Lock()  # Lock to prevent concurrent reindexing
        self._reindex_task: Optional["asyncio.Task[None]"] = None  # Track ongoing reindex
        self._shutdown = False  # Shutdown flag
        # Subscribe to KB change events for reactive reindexing
        if subscribe_to_events:
            self._subscribe_to_kb_events()

    async def _retry_mcp_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Retry MCP operation with exponential backoff and connectivity checks
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: The async function to retry
            *args, **kwargs: Arguments to pass to the operation function
            
        Returns:
            Result of the operation or None if all retries failed
        """
        max_attempts = settings.MCP_RETRY_ATTEMPTS
        base_delay = settings.MCP_RETRY_DELAY
        
        for attempt in range(max_attempts):
            try:
                # Check connectivity before each attempt (except the first one)
                if attempt > 0:
                    if not await self._check_mcp_hub_connectivity():
                        logger.warning(f"⚠️ MCP Hub connectivity check failed before {operation_name} attempt {attempt + 1}")
                        if attempt < max_attempts - 1:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"⚠️ Retrying {operation_name} in {delay}s...")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ {operation_name} failed - MCP Hub not reachable")
                            return None
                
                result = await operation_func(*args, **kwargs)
                if result is not None:
                    return result
                elif attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"⚠️ {operation_name} attempt {attempt + 1} failed, retrying in {delay}s...")
                    await asyncio.sleep(delay)
            except asyncio.CancelledError:
                logger.warning(f"⚠️ {operation_name} was cancelled on attempt {attempt + 1}")
                raise
            except Exception as e:
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"⚠️ {operation_name} attempt {attempt + 1} failed with error: {e}, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ {operation_name} failed after {max_attempts} attempts: {e}", exc_info=True)
                    raise
        
        logger.error(f"❌ {operation_name} failed after {max_attempts} attempts")
        return None

    async def _check_mcp_hub_connectivity(self) -> bool:
        """
        Check if MCP Hub is reachable and healthy
        
        Returns:
            True if MCP Hub is reachable and healthy
        """
        try:
            health_url = f"{self.mcp_hub_url}/health"
            logger.debug(f"🔍 Checking MCP Hub connectivity at {health_url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.warning(f"⚠️  MCP Hub health check failed with status {resp.status}")
                        return False
                    health_data = await resp.json()
                    logger.debug(f"✅ MCP Hub is healthy: {health_data}")
                    return True
        except Exception as e:
            logger.warning(f"⚠️  MCP Hub connectivity check failed: {e}")
            return False

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
                async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.warning(f"⚠️  MCP Hub health check failed with status {resp.status}")
                        return False

                    data = await resp.json()
                    builtin_tools = data.get("builtin_tools", {})
                    available_tools = builtin_tools.get("names", [])

                    # Check if vector search tools are available
                    required_tools = [
                        "vector_search",
                        "reindex_vector",
                        "add_vector_documents",
                        "delete_vector_documents",
                        "update_vector_documents",
                    ]

                    has_all_tools = all(tool in available_tools for tool in required_tools)

                    if has_all_tools:
                        logger.info(
                            "✅ All vector search tools are available: "
                            f"{', '.join(required_tools)}"
                        )
                        self.vector_search_available = True
                        return True
                    else:
                        missing = [t for t in required_tools if t not in available_tools]
                        available = ", ".join(available_tools) if available_tools else "none"
                        logger.info(
                            f"ℹ️  Vector search tools not fully available. "
                            f"Missing: {', '.join(missing)}. "
                            f"Available tools: {available}"
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

        # Check MCP Hub connectivity before starting indexing
        if not await self._check_mcp_hub_connectivity():
            logger.error("❌ Cannot perform initial indexing: MCP Hub is not reachable")
            return False

        try:
            logger.info("🔄 Starting initial knowledge base indexing (bot-triggered)...")

            # Load current file hashes and scan current state (for change tracking)
            await self._load_file_hashes()
            await self._scan_knowledge_bases()

            # Read all files and prepare documents
            documents = await self._read_all_documents()

            logger.info(f"📚 Prepared {len(documents)} documents for indexing")

            # Trigger reindex via MCP Hub with document data
            ok = await self._call_mcp_reindex(documents=documents, force=force)
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

            # Call MCP Hub for each type of change
            all_ok = True

            # Delete removed files (only document IDs needed)
            if changes.deleted:
                logger.info(f"🗑️  Calling MCP Hub to delete {len(changes.deleted)} documents")
                ok = await self._call_mcp_delete_documents(list(changes.deleted))
                all_ok = all_ok and ok

            # Add new files (read content and send)
            if changes.added:
                logger.info(f"➕ Reading {len(changes.added)} new files...")
                documents = await self._read_documents_by_paths(list(changes.added))
                logger.info(f"➕ Calling MCP Hub to add {len(documents)} documents")
                ok = await self._call_mcp_add_documents(documents)
                all_ok = all_ok and ok

            # Update modified files (read content and send)
            if changes.modified:
                logger.info(f"🔄 Reading {len(changes.modified)} modified files...")
                documents = await self._read_documents_by_paths(list(changes.modified))
                logger.info(f"🔄 Calling MCP Hub to update {len(documents)} documents")
                ok = await self._call_mcp_update_documents(documents)
                all_ok = all_ok and ok

            # Save updated hashes snapshot regardless of MCP outcome
            # to avoid duplicate work next time
            await self._save_file_hashes()

            if all_ok:
                logger.info("✅ Change detection completed, all updates successful")
            else:
                logger.warning("⚠️ Some updates failed; hashes updated, will retry on next event")
            return all_ok

        except Exception as e:
            logger.error(f"❌ Failed to check/reindex changes: {e}", exc_info=True)
            return False

    async def _scan_knowledge_bases(self) -> None:
        """
        Scan all knowledge bases and compute file hashes

        AICODE-NOTE: BOT has file system access, computes hashes for change detection
        """
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

    async def _read_all_documents(self) -> List[Dict[str, Any]]:
        """
        Read all markdown files and prepare documents for MCP HUB

        AICODE-NOTE: SOLID - Single Responsibility Principle
        BOT reads files, MCP HUB processes content
        """
        documents = []

        if not self.kb_root_path.exists():
            logger.warning(f"⚠️  KB root path does not exist: {self.kb_root_path}")
            return documents

        markdown_files = list(self.kb_root_path.rglob("*.md"))

        for file_path in markdown_files:
            try:
                # Compute relative path as document ID
                doc_id = str(file_path.relative_to(self.kb_root_path))

                # Read file content
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Prepare document structure
                doc = {
                    "id": doc_id,
                    "content": content,
                    "metadata": {
                        "file_path": doc_id,
                        "file_name": file_path.name,
                        "file_size": len(content),
                    },
                }

                documents.append(doc)

            except Exception as e:
                logger.error(f"❌ Failed to read file {file_path}: {e}")

        logger.info(f"📖 Read {len(documents)} documents")
        return documents

    async def _read_documents_by_paths(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Read specific files by paths and prepare documents

        Args:
            file_paths: List of relative file paths

        Returns:
            List of document structures
        """
        documents = []

        for rel_path in file_paths:
            try:
                file_path = self.kb_root_path / rel_path

                if not file_path.exists():
                    logger.warning(f"⚠️  File not found: {rel_path}")
                    continue

                # Read file content
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Prepare document structure
                doc = {
                    "id": rel_path,
                    "content": content,
                    "metadata": {
                        "file_path": rel_path,
                        "file_name": file_path.name,
                        "file_size": len(content),
                    },
                }

                documents.append(doc)

            except Exception as e:
                logger.error(f"❌ Failed to read file {rel_path}: {e}")

        return documents

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

    async def _call_mcp_reindex(self, documents: List[Dict[str, Any]], force: bool = False) -> bool:
        """
        Call MCP Hub reindex_vector tool via SSE transport.

        AICODE-NOTE: SOLID - BOT sends document DATA, not file paths
        """
        async def _do_reindex():
            # Ensure SSE URL
            sse_url = self.mcp_hub_url
            if not sse_url.endswith("/sse"):
                sse_url = f"{sse_url}/sse"

            client = MCPClient(MCPServerConfig(transport="sse", url=sse_url), timeout=settings.MCP_TIMEOUT)
            connected = await client.connect()
            if not connected:
                logger.warning("⚠️ Failed to connect to MCP Hub for reindex")
                return False

            try:
                result = await client.call_tool(
                    "reindex_vector", {"documents": documents, "force": bool(force)}
                )
                if result.get("success"):
                    logger.info("✅ MCP reindex_vector completed successfully")
                    return True
                else:
                    logger.warning(f"⚠️ MCP reindex_vector failed: {result.get('error')}")
                    return False
            finally:
                await client.disconnect()
        
        try:
            return await self._retry_mcp_operation("reindex_vector", _do_reindex) or False
        except asyncio.CancelledError:
            logger.warning("⚠️ MCP reindex_vector operation was cancelled")
            return False
        except Exception as e:
            logger.error(f"❌ Exception while calling MCP reindex_vector: {e}", exc_info=True)
            return False

    async def _call_mcp_add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Call MCP Hub add_vector_documents tool to add new documents.

        AICODE-NOTE: SOLID - BOT sends document DATA (content), not file paths
        """
        async def _do_add_documents():
            sse_url = self.mcp_hub_url
            if not sse_url.endswith("/sse"):
                sse_url = f"{sse_url}/sse"

            client = MCPClient(MCPServerConfig(transport="sse", url=sse_url), timeout=settings.MCP_TIMEOUT)
            connected = await client.connect()
            if not connected:
                logger.warning("⚠️ Failed to connect to MCP Hub for add_documents")
                return False

            try:
                result = await client.call_tool("add_vector_documents", {"documents": documents})
                if result.get("success"):
                    logger.info(f"✅ MCP add_vector_documents completed: {result.get('message')}")
                    return True
                else:
                    logger.warning(f"⚠️ MCP add_vector_documents failed: {result.get('error')}")
                    return False
            finally:
                await client.disconnect()
        
        try:
            return await self._retry_mcp_operation("add_vector_documents", _do_add_documents) or False
        except asyncio.CancelledError:
            logger.warning("⚠️ MCP add_vector_documents operation was cancelled")
            return False
        except Exception as e:
            logger.error(f"❌ Exception while calling MCP add_vector_documents: {e}", exc_info=True)
            return False

    async def _call_mcp_delete_documents(self, document_ids: List[str]) -> bool:
        """
        Call MCP Hub delete_vector_documents tool to delete documents.

        AICODE-NOTE: Sends document IDs (not file paths), MCP HUB deletes by ID
        """
        async def _do_delete_documents():
            sse_url = self.mcp_hub_url
            if not sse_url.endswith("/sse"):
                sse_url = f"{sse_url}/sse"

            client = MCPClient(MCPServerConfig(transport="sse", url=sse_url), timeout=settings.MCP_TIMEOUT)
            connected = await client.connect()
            if not connected:
                logger.warning("⚠️ Failed to connect to MCP Hub for delete_documents")
                return False

            try:
                result = await client.call_tool(
                    "delete_vector_documents", {"document_ids": document_ids}
                )
                if result.get("success"):
                    logger.info(
                        f"✅ MCP delete_vector_documents completed: {result.get('message')}"
                    )
                    return True
                else:
                    logger.warning(f"⚠️ MCP delete_vector_documents failed: {result.get('error')}")
                    return False
            finally:
                await client.disconnect()
        
        try:
            return await self._retry_mcp_operation("delete_vector_documents", _do_delete_documents) or False
        except asyncio.CancelledError:
            logger.warning("⚠️ MCP delete_vector_documents operation was cancelled")
            return False
        except Exception as e:
            logger.error(
                f"❌ Exception while calling MCP delete_vector_documents: {e}", exc_info=True
            )
            return False

    async def _call_mcp_update_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Call MCP Hub update_vector_documents tool to update modified documents.

        AICODE-NOTE: SOLID - BOT sends document DATA (content), not file paths
        """
        async def _do_update_documents():
            sse_url = self.mcp_hub_url
            if not sse_url.endswith("/sse"):
                sse_url = f"{sse_url}/sse"

            client = MCPClient(MCPServerConfig(transport="sse", url=sse_url), timeout=settings.MCP_TIMEOUT)
            connected = await client.connect()
            if not connected:
                logger.warning("⚠️ Failed to connect to MCP Hub for update_documents")
                return False

            try:
                result = await client.call_tool("update_vector_documents", {"documents": documents})
                if result.get("success"):
                    logger.info(
                        f"✅ MCP update_vector_documents completed: {result.get('message')}"
                    )
                    return True
                else:
                    logger.warning(f"⚠️ MCP update_vector_documents failed: {result.get('error')}")
                    return False
            finally:
                await client.disconnect()
        
        try:
            return await self._retry_mcp_operation("update_vector_documents", _do_update_documents) or False
        except asyncio.CancelledError:
            logger.warning("⚠️ MCP update_vector_documents operation was cancelled")
            return False
        except Exception as e:
            logger.error(
                f"❌ Exception while calling MCP update_vector_documents: {e}", exc_info=True
            )
            return False

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

        # Cancel any pending reindex task (to batch rapid changes)
        if self._reindex_task and not self._reindex_task.done():
            logger.debug("⏸️  Cancelling pending reindex task to batch changes")
            self._reindex_task.cancel()

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
