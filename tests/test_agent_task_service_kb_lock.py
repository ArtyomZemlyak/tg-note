"""
Tests for KB locking in Agent Task Service

Verifies that agent mode operations properly use KB locking to prevent
conflicts when multiple users interact with the same knowledge base.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.processor.message_aggregator import MessageGroup
from src.services.agent_task_service import AgentTaskService


class TestAgentTaskServiceKBLock:
    """Test that agent task service uses KB locking"""

    @pytest.fixture
    def temp_kb_path(self):
        """Create temporary KB directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "test_kb"
            kb_path.mkdir(parents=True, exist_ok=True)
            yield str(kb_path)

    @pytest.fixture
    def mock_dependencies(self, temp_kb_path):
        """Create mock dependencies for AgentTaskService"""
        mock_bot = MagicMock()
        mock_bot.edit_message_text = AsyncMock()
        mock_bot.send_message = AsyncMock()

        mock_repo_manager = MagicMock()
        mock_repo_manager.get_kb_path.return_value = Path(temp_kb_path)

        mock_user_context_manager = MagicMock()
        mock_user_context_manager.add_user_message_to_context = MagicMock()
        mock_user_context_manager.add_assistant_message_to_context = MagicMock()
        mock_user_context_manager.get_conversation_context.return_value = None

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.process = AsyncMock(
            return_value={
                "answer": "Test answer",
                "summary": "Test summary",
                "metadata": {
                    "files_created": [],
                    "files_edited": [],
                    "files_deleted": [],
                    "folders_created": [],
                },
            }
        )
        mock_agent.set_working_directory = MagicMock()
        mock_agent.get_instruction = MagicMock(return_value="Test instruction")
        mock_agent.set_instruction = MagicMock()

        mock_user_context_manager.get_or_create_agent.return_value = mock_agent

        mock_settings_manager = MagicMock()
        mock_settings_manager.get_setting.return_value = True

        return {
            "bot": mock_bot,
            "repo_manager": mock_repo_manager,
            "user_context_manager": mock_user_context_manager,
            "settings_manager": mock_settings_manager,
        }

    @pytest.fixture
    def agent_service(self, mock_dependencies):
        """Create AgentTaskService instance"""
        return AgentTaskService(
            bot=mock_dependencies["bot"],
            repo_manager=mock_dependencies["repo_manager"],
            user_context_manager=mock_dependencies["user_context_manager"],
            settings_manager=mock_dependencies["settings_manager"],
        )

    @pytest.mark.asyncio
    async def test_agent_task_uses_kb_lock(self, agent_service, temp_kb_path):
        """Test that agent task execution acquires KB lock"""
        # Create a message group
        group = MessageGroup()
        group.add_message(
            {
                "message_id": 1,
                "date": 1234567890,
                "text": "Test task",
                "chat_id": 123,
            }
        )

        user_kb = {"kb_name": "test_kb", "kb_type": "github"}

        # Track if lock was acquired
        lock_acquired = False
        original_with_kb_lock = None

        # Mock the sync manager to verify lock is acquired
        from src.knowledge_base.sync_manager import get_sync_manager

        sync_manager = get_sync_manager()
        original_with_kb_lock = sync_manager.with_kb_lock

        class MockLockContext:
            def __init__(self, kb_path, operation_name):
                self.kb_path = kb_path
                self.operation_name = operation_name

            async def __aenter__(self):
                nonlocal lock_acquired
                lock_acquired = True
                # Verify that kb_path is correct
                assert str(temp_kb_path) in self.kb_path
                # Verify that operation name includes user_id
                assert "agent_task_user_" in self.operation_name
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        # Replace with_kb_lock with our mock
        sync_manager.with_kb_lock = lambda kb_path, op_name: MockLockContext(kb_path, op_name)

        try:
            # Execute task
            await agent_service.execute_task(
                group=group,
                processing_msg_id=1,
                chat_id=123,
                user_id=456,
                user_kb=user_kb,
            )

            # Verify that lock was acquired
            assert lock_acquired, "KB lock was not acquired for agent task"

        finally:
            # Restore original with_kb_lock
            sync_manager.with_kb_lock = original_with_kb_lock

    @pytest.mark.asyncio
    async def test_agent_tasks_serialized_for_same_kb(self, agent_service, temp_kb_path):
        """Test that multiple agent tasks on same KB are serialized"""
        # Track execution order
        execution_order = []

        # Create two message groups
        group1 = MessageGroup()
        group1.add_message(
            {
                "message_id": 1,
                "date": 1234567890,
                "text": "Task 1",
                "chat_id": 123,
            }
        )

        group2 = MessageGroup()
        group2.add_message(
            {
                "message_id": 2,
                "date": 1234567891,
                "text": "Task 2",
                "chat_id": 124,
            }
        )

        user_kb = {"kb_name": "test_kb", "kb_type": "github"}

        # Patch _execute_task_locked to track execution order
        original_execute_task_locked = agent_service._execute_task_locked

        async def mock_execute_task_locked(
            group, processing_msg_id, chat_id, user_id, user_kb, kb_path
        ):
            execution_order.append(f"start_task_{processing_msg_id}")
            await asyncio.sleep(0.05)  # Simulate work
            execution_order.append(f"end_task_{processing_msg_id}")

        agent_service._execute_task_locked = mock_execute_task_locked

        try:
            # Run two tasks concurrently
            await asyncio.gather(
                agent_service.execute_task(group1, 1, 123, 456, user_kb),
                agent_service.execute_task(group2, 2, 124, 457, user_kb),
            )

            # Check that tasks were serialized (one completed before other started)
            assert len(execution_order) == 4
            assert execution_order == [
                "start_task_1",
                "end_task_1",
                "start_task_2",
                "end_task_2",
            ] or execution_order == [
                "start_task_2",
                "end_task_2",
                "start_task_1",
                "end_task_1",
            ], f"Tasks were not serialized. Execution order: {execution_order}"

        finally:
            # Restore original method
            agent_service._execute_task_locked = original_execute_task_locked

    @pytest.mark.asyncio
    async def test_kb_lock_released_on_exception(self, agent_service, temp_kb_path):
        """Test that KB lock is released even when task fails"""
        # Create a message group
        group = MessageGroup()
        group.add_message(
            {
                "message_id": 1,
                "date": 1234567890,
                "text": "Test task",
                "chat_id": 123,
            }
        )

        user_kb = {"kb_name": "test_kb", "kb_type": "github"}

        # Track lock state
        lock_released = False

        # Mock the sync manager to verify lock is released
        from src.knowledge_base.sync_manager import get_sync_manager

        sync_manager = get_sync_manager()
        original_with_kb_lock = sync_manager.with_kb_lock

        class MockLockContext:
            def __init__(self, kb_path, operation_name):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                nonlocal lock_released
                lock_released = True
                return False

        # Replace with_kb_lock with our mock
        sync_manager.with_kb_lock = lambda kb_path, op_name: MockLockContext(kb_path, op_name)

        # Make _execute_task_locked raise an exception
        async def failing_execute_task_locked(*args, **kwargs):
            raise RuntimeError("Simulated task failure")

        agent_service._execute_task_locked = failing_execute_task_locked

        try:
            # Execute task (should fail but release lock)
            await agent_service.execute_task(
                group=group,
                processing_msg_id=1,
                chat_id=123,
                user_id=456,
                user_kb=user_kb,
            )

            # Verify that lock was released
            assert lock_released, "KB lock was not released after exception"

        finally:
            # Restore original with_kb_lock
            sync_manager.with_kb_lock = original_with_kb_lock
