"""
KB Synchronization Manager
Handles synchronization and serialization of knowledge base operations
to prevent conflicts when multiple users work with the same KB
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional

from filelock import FileLock
from loguru import logger


class KBSyncManager:
    """
    Manages synchronization for knowledge base operations.
    
    Ensures that operations on the same KB are serialized (executed one after another)
    to prevent git conflicts when multiple users work with the same knowledge base.
    
    Uses file-based locks to ensure cross-process synchronization.
    """

    def __init__(self):
        """Initialize KB sync manager"""
        self._locks: Dict[str, FileLock] = {}
        self._async_locks: Dict[str, asyncio.Lock] = {}

    def get_lock_for_kb(self, kb_path: str) -> FileLock:
        """
        Get or create a file lock for the given knowledge base
        
        Args:
            kb_path: Path to knowledge base
            
        Returns:
            FileLock instance for the KB
        """
        kb_path_normalized = str(Path(kb_path).resolve())
        
        if kb_path_normalized not in self._locks:
            # Create lock file in the KB directory
            lock_file = Path(kb_path) / ".kb_operations.lock"
            self._locks[kb_path_normalized] = FileLock(str(lock_file), timeout=300)
            logger.debug(f"Created file lock for KB: {kb_path_normalized}")
        
        return self._locks[kb_path_normalized]

    def get_async_lock_for_kb(self, kb_path: str) -> asyncio.Lock:
        """
        Get or create an async lock for the given knowledge base
        
        This is used in addition to file locks for in-process synchronization.
        
        Args:
            kb_path: Path to knowledge base
            
        Returns:
            asyncio.Lock instance for the KB
        """
        kb_path_normalized = str(Path(kb_path).resolve())
        
        if kb_path_normalized not in self._async_locks:
            self._async_locks[kb_path_normalized] = asyncio.Lock()
            logger.debug(f"Created async lock for KB: {kb_path_normalized}")
        
        return self._async_locks[kb_path_normalized]

    async def with_kb_lock(self, kb_path: str, operation_name: str = "operation"):
        """
        Async context manager for KB operations with both file and async locks
        
        Usage:
            async with sync_manager.with_kb_lock(kb_path, "create_note"):
                # Your KB operations here
                ...
        
        Args:
            kb_path: Path to knowledge base
            operation_name: Name of the operation (for logging)
            
        Returns:
            Async context manager
        """
        return _KBLockContext(self, kb_path, operation_name)


class _KBLockContext:
    """Async context manager for KB lock operations"""
    
    def __init__(self, manager: KBSyncManager, kb_path: str, operation_name: str):
        self.manager = manager
        self.kb_path = kb_path
        self.operation_name = operation_name
        self.file_lock: Optional[FileLock] = None
        self.async_lock: Optional[asyncio.Lock] = None

    async def __aenter__(self):
        """Acquire both async and file locks"""
        kb_path_normalized = str(Path(self.kb_path).resolve())
        
        # First acquire async lock (for in-process synchronization)
        self.async_lock = self.manager.get_async_lock_for_kb(self.kb_path)
        await self.async_lock.acquire()
        logger.info(f"[{self.operation_name}] Acquired async lock for KB: {kb_path_normalized}")
        
        # Then acquire file lock (for cross-process synchronization)
        try:
            self.file_lock = self.manager.get_lock_for_kb(self.kb_path)
            await asyncio.get_event_loop().run_in_executor(
                None, self.file_lock.acquire
            )
            logger.info(f"[{self.operation_name}] Acquired file lock for KB: {kb_path_normalized}")
        except Exception as e:
            # If file lock fails, release async lock
            if self.async_lock and self.async_lock.locked():
                self.async_lock.release()
            logger.error(f"[{self.operation_name}] Failed to acquire file lock: {e}")
            raise
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release both locks in reverse order"""
        kb_path_normalized = str(Path(self.kb_path).resolve())
        
        # Release file lock first
        if self.file_lock and self.file_lock.is_locked:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.file_lock.release
                )
                logger.info(f"[{self.operation_name}] Released file lock for KB: {kb_path_normalized}")
            except Exception as e:
                logger.error(f"[{self.operation_name}] Error releasing file lock: {e}")
        
        # Then release async lock
        if self.async_lock and self.async_lock.locked():
            self.async_lock.release()
            logger.info(f"[{self.operation_name}] Released async lock for KB: {kb_path_normalized}")
        
        return False  # Don't suppress exceptions


# Global singleton instance
_global_sync_manager: Optional[KBSyncManager] = None


def get_sync_manager() -> KBSyncManager:
    """
    Get global KB sync manager instance (singleton)
    
    Returns:
        Global KBSyncManager instance
    """
    global _global_sync_manager
    if _global_sync_manager is None:
        _global_sync_manager = KBSyncManager()
        logger.info("Initialized global KB sync manager")
    return _global_sync_manager
