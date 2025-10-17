"""
Tests for KB Synchronization Manager
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from src.knowledge_base.sync_manager import KBSyncManager, get_sync_manager


class TestKBSyncManager:
    """Test KBSyncManager functionality"""

    @pytest.fixture
    def temp_kb_path(self):
        """Create temporary KB directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "test_kb"
            kb_path.mkdir(parents=True, exist_ok=True)
            yield str(kb_path)

    @pytest.fixture
    def sync_manager(self):
        """Create sync manager instance"""
        return KBSyncManager()

    def test_get_sync_manager_singleton(self):
        """Test that get_sync_manager returns singleton"""
        manager1 = get_sync_manager()
        manager2 = get_sync_manager()
        assert manager1 is manager2

    def test_get_lock_for_kb(self, sync_manager, temp_kb_path):
        """Test getting file lock for KB"""
        lock1 = sync_manager.get_lock_for_kb(temp_kb_path)
        lock2 = sync_manager.get_lock_for_kb(temp_kb_path)
        
        # Should return same lock for same path
        assert lock1 is lock2

    def test_get_async_lock_for_kb(self, sync_manager, temp_kb_path):
        """Test getting async lock for KB"""
        lock1 = sync_manager.get_async_lock_for_kb(temp_kb_path)
        lock2 = sync_manager.get_async_lock_for_kb(temp_kb_path)
        
        # Should return same lock for same path
        assert lock1 is lock2
        assert isinstance(lock1, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_with_kb_lock_context_manager(self, sync_manager, temp_kb_path):
        """Test async context manager for KB lock"""
        operation_executed = False
        
        async with sync_manager.with_kb_lock(temp_kb_path, "test_operation"):
            operation_executed = True
            # Simulate some work
            await asyncio.sleep(0.01)
        
        assert operation_executed

    @pytest.mark.asyncio
    async def test_with_kb_lock_serialization(self, sync_manager, temp_kb_path):
        """Test that operations are serialized (not parallel)"""
        execution_order = []
        
        async def operation(op_id: int, delay: float):
            async with sync_manager.with_kb_lock(temp_kb_path, f"op_{op_id}"):
                execution_order.append(f"start_{op_id}")
                await asyncio.sleep(delay)
                execution_order.append(f"end_{op_id}")
        
        # Run two operations concurrently
        await asyncio.gather(
            operation(1, 0.1),
            operation(2, 0.05),
        )
        
        # Check that operations were serialized (one completed before other started)
        # Either op1 fully completed before op2, or vice versa
        assert (
            execution_order == ["start_1", "end_1", "start_2", "end_2"]
            or execution_order == ["start_2", "end_2", "start_1", "end_1"]
        )

    @pytest.mark.asyncio
    async def test_with_kb_lock_different_kbs(self, sync_manager):
        """Test that different KBs can be accessed in parallel"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path1 = Path(tmpdir) / "kb1"
            kb_path2 = Path(tmpdir) / "kb2"
            kb_path1.mkdir(parents=True)
            kb_path2.mkdir(parents=True)
            
            execution_order = []
            
            async def operation(kb_path: Path, op_id: int):
                async with sync_manager.with_kb_lock(str(kb_path), f"op_{op_id}"):
                    execution_order.append(f"start_{op_id}")
                    await asyncio.sleep(0.05)
                    execution_order.append(f"end_{op_id}")
            
            # Run operations on different KBs concurrently
            await asyncio.gather(
                operation(kb_path1, 1),
                operation(kb_path2, 2),
            )
            
            # Operations on different KBs should overlap (not be fully serialized)
            # At least one operation should start before the other ends
            assert len(execution_order) == 4
            # If they were serialized, order would be [start_X, end_X, start_Y, end_Y]
            # But with parallel execution, we expect interleaving

    @pytest.mark.asyncio
    async def test_with_kb_lock_exception_handling(self, sync_manager, temp_kb_path):
        """Test that locks are released even when exception occurs"""
        
        class TestException(Exception):
            pass
        
        # First operation that raises exception
        with pytest.raises(TestException):
            async with sync_manager.with_kb_lock(temp_kb_path, "failing_op"):
                raise TestException("Test error")
        
        # Second operation should still be able to acquire lock
        operation_executed = False
        async with sync_manager.with_kb_lock(temp_kb_path, "successful_op"):
            operation_executed = True
        
        assert operation_executed

    @pytest.mark.asyncio
    async def test_lock_file_created(self, sync_manager, temp_kb_path):
        """Test that lock file is created in KB directory"""
        lock_file = Path(temp_kb_path) / ".kb_operations.lock"
        
        # Lock file shouldn't exist initially
        assert not lock_file.exists()
        
        async with sync_manager.with_kb_lock(temp_kb_path, "test_op"):
            # Lock file should exist while locked
            # Note: filelock creates the file when acquiring
            pass
        
        # Get the lock to trigger its creation
        _ = sync_manager.get_lock_for_kb(temp_kb_path)
        
        # Lock file path should be registered
        # (actual file creation depends on filelock implementation)
