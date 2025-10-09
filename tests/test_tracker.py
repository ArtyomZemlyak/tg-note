"""
Tests for ProcessingTracker
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.tracker.processing_tracker import ProcessingTracker


@pytest.fixture
def temp_storage():
    """Create temporary storage file"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)

    lock_path = temp_path + ".lock"
    if os.path.exists(lock_path):
        os.unlink(lock_path)


def test_tracker_initialization(temp_storage):
    """Test tracker initialization"""
    tracker = ProcessingTracker(temp_storage)
    assert Path(temp_storage).exists()

    stats = tracker.get_stats()
    assert stats["total_processed"] == 0
    assert stats["pending_groups"] == 0


def test_is_processed(temp_storage):
    """Test checking if content is processed"""
    tracker = ProcessingTracker(temp_storage)

    content_hash = "test_hash_123"
    assert not tracker.is_processed(content_hash)

    tracker.add_processed(
        content_hash=content_hash, message_ids=[123], chat_id=456, status="completed"
    )

    assert tracker.is_processed(content_hash)


def test_add_processed(temp_storage):
    """Test adding processed message"""
    tracker = ProcessingTracker(temp_storage)

    tracker.add_processed(
        content_hash="hash1",
        message_ids=[1, 2, 3],
        chat_id=123,
        kb_file="/path/to/file.md",
        status="completed",
    )

    stats = tracker.get_stats()
    assert stats["total_processed"] == 1
    assert stats["completed"] == 1


def test_pending_groups(temp_storage):
    """Test pending groups management"""
    tracker = ProcessingTracker(temp_storage)

    group_id = "group_123"
    message_ids = [1, 2, 3]

    tracker.add_pending_group(group_id, message_ids)

    stats = tracker.get_stats()
    assert stats["pending_groups"] == 1

    tracker.remove_pending_group(group_id)

    stats = tracker.get_stats()
    assert stats["pending_groups"] == 0


def test_concurrent_access(temp_storage):
    """Test file locking for concurrent access"""
    tracker1 = ProcessingTracker(temp_storage)
    tracker2 = ProcessingTracker(temp_storage)

    tracker1.add_processed("hash1", [1], 123, status="completed")
    tracker2.add_processed("hash2", [2], 123, status="completed")

    # Both should be in the file
    assert tracker1.is_processed("hash1")
    assert tracker2.is_processed("hash2")

    stats = tracker1.get_stats()
    assert stats["total_processed"] == 2
