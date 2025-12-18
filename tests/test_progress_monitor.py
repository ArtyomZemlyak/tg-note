"""
Tests for Progress Monitor

Tests the progress monitoring system that tracks checkbox completion
in agent prompts and updates Telegram messages.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import List

import pytest

from src.services.progress_monitor import CheckboxItem, ProgressMonitor, ProgressSnapshot


@pytest.fixture
def temp_export_dir():
    """Create temporary directory for exported prompts"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_markdown_content():
    """Sample markdown content with checkboxes"""
    return """# Test Prompt

## Шаг 1: Анализ

- [x] Прочитать контент
- [x] Определить тип
- [ ] Проанализировать структуру

## Шаг 2: Обработка

- [ ] Создать файлы
- [ ] Обновить индекс
"""


@pytest.fixture
def completed_markdown_content():
    """Markdown content with all checkboxes completed"""
    return """# Test Prompt

## Шаг 1: Анализ

- [x] Прочитать контент
- [x] Определить тип
- [x] Проанализировать структуру

## Шаг 2: Обработка

- [x] Создать файлы
- [x] Обновить индекс
"""


class TestCheckboxParsing:
    """Tests for checkbox parsing functionality"""

    def test_parse_checkboxes_basic(self, temp_export_dir, sample_markdown_content):
        """Test basic checkbox parsing"""
        # Create test file
        test_file = temp_export_dir / "test.md"
        test_file.write_text(sample_markdown_content)

        # Create monitor (without starting it)
        updates = []

        async def callback(snapshot: ProgressSnapshot):
            updates.append(snapshot)

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        # Parse checkboxes
        checkboxes = monitor._parse_checkboxes_from_file(test_file)

        # Verify
        assert len(checkboxes) == 5
        assert sum(1 for cb in checkboxes if cb.status == "completed") == 2
        assert sum(1 for cb in checkboxes if cb.status == "pending") == 3

        # Check context assignment
        assert checkboxes[0].context == "Шаг 1: Анализ"
        assert checkboxes[3].context == "Шаг 2: Обработка"

    def test_parse_checkboxes_uppercase_x(self, temp_export_dir):
        """Test parsing checkboxes with uppercase X"""
        content = """
- [X] Completed uppercase
- [x] Completed lowercase
- [ ] Pending
"""
        test_file = temp_export_dir / "test.md"
        test_file.write_text(content)

        async def callback(snapshot: ProgressSnapshot):
            pass

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        checkboxes = monitor._parse_checkboxes_from_file(test_file)

        assert len(checkboxes) == 3
        assert checkboxes[0].status == "completed"
        assert checkboxes[1].status == "completed"
        assert checkboxes[2].status == "pending"

    def test_parse_empty_file(self, temp_export_dir):
        """Test parsing file without checkboxes"""
        content = """# No Checkboxes Here

Just some regular content without any checkboxes.
"""
        test_file = temp_export_dir / "test.md"
        test_file.write_text(content)

        async def callback(snapshot: ProgressSnapshot):
            pass

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        checkboxes = monitor._parse_checkboxes_from_file(test_file)
        assert len(checkboxes) == 0


class TestProgressCalculation:
    """Tests for progress calculation"""

    def test_calculate_progress(self, temp_export_dir):
        """Test progress calculation"""
        checkboxes = [
            CheckboxItem(text="Task 1", status="completed", file="test.md", line_number=1),
            CheckboxItem(text="Task 2", status="completed", file="test.md", line_number=2),
            CheckboxItem(text="Task 3", status="pending", file="test.md", line_number=3),
            CheckboxItem(text="Task 4", status="pending", file="test.md", line_number=4),
        ]

        async def callback(snapshot: ProgressSnapshot):
            pass

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        snapshot = monitor._calculate_progress(checkboxes)

        assert snapshot.total == 4
        assert snapshot.completed == 2
        assert snapshot.percentage == 50.0
        assert snapshot.current_task == "Task 3"

    def test_calculate_progress_all_completed(self, temp_export_dir):
        """Test progress when all tasks completed"""
        checkboxes = [
            CheckboxItem(text="Task 1", status="completed", file="test.md", line_number=1),
            CheckboxItem(text="Task 2", status="completed", file="test.md", line_number=2),
        ]

        async def callback(snapshot: ProgressSnapshot):
            pass

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        snapshot = monitor._calculate_progress(checkboxes)

        assert snapshot.total == 2
        assert snapshot.completed == 2
        assert snapshot.percentage == 100.0
        assert snapshot.current_task is None  # No pending tasks

    def test_calculate_progress_empty(self, temp_export_dir):
        """Test progress with no checkboxes"""

        async def callback(snapshot: ProgressSnapshot):
            pass

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        snapshot = monitor._calculate_progress([])

        assert snapshot.total == 0
        assert snapshot.completed == 0
        assert snapshot.percentage == 0.0


class TestProgressMonitoring:
    """Tests for progress monitoring functionality"""

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, temp_export_dir):
        """Test starting and stopping monitoring"""
        updates = []

        async def callback(snapshot: ProgressSnapshot):
            updates.append(snapshot)

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        # Start monitoring
        await monitor.start_monitoring()
        assert monitor.is_monitoring

        # Stop monitoring
        await monitor.stop_monitoring()
        assert not monitor.is_monitoring

    @pytest.mark.asyncio
    async def test_monitor_file_changes(self, temp_export_dir, sample_markdown_content):
        """Test monitoring detects file changes"""
        updates: List[ProgressSnapshot] = []

        async def callback(snapshot: ProgressSnapshot):
            updates.append(snapshot)

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.5
        )

        # Create initial file
        test_file = temp_export_dir / "test.md"
        test_file.write_text(sample_markdown_content)

        # Start monitoring
        await monitor.start_monitoring()

        # Wait for initial parse
        await asyncio.sleep(0.3)

        # Verify initial state
        assert len(updates) >= 1
        initial_snapshot = updates[-1]
        assert initial_snapshot.total == 5
        assert initial_snapshot.completed == 2

        # Update file (complete one more checkbox)
        updated_content = sample_markdown_content.replace(
            "- [ ] Проанализировать структуру", "- [x] Проанализировать структуру"
        )
        test_file.write_text(updated_content)

        # Wait for update to be detected
        await asyncio.sleep(1.0)

        # Verify update was detected
        assert len(updates) >= 2
        final_snapshot = updates[-1]
        assert final_snapshot.completed == 3

        # Stop monitoring
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_throttling(self, temp_export_dir, sample_markdown_content):
        """Test that updates are throttled"""
        updates: List[ProgressSnapshot] = []
        update_times: List[float] = []

        import time

        async def callback(snapshot: ProgressSnapshot):
            updates.append(snapshot)
            update_times.append(time.time())

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=1.0
        )

        test_file = temp_export_dir / "test.md"
        test_file.write_text(sample_markdown_content)

        await monitor.start_monitoring()

        # Wait for initial update
        await asyncio.sleep(0.3)

        # Make multiple rapid changes
        for i in range(3):
            content = sample_markdown_content + f"\n<!-- Change {i} -->"
            test_file.write_text(content)
            await asyncio.sleep(0.1)

        # Wait for throttling
        await asyncio.sleep(2.0)

        await monitor.stop_monitoring()

        # Verify throttling worked (should have fewer updates than changes)
        assert len(updates) >= 1
        if len(update_times) >= 2:
            # Check that updates are at least throttle_interval apart
            time_diffs = [
                update_times[i + 1] - update_times[i] for i in range(len(update_times) - 1)
            ]
            assert all(diff >= 0.9 for diff in time_diffs)  # Allow small margin

    @pytest.mark.asyncio
    async def test_multiple_files(self, temp_export_dir):
        """Test monitoring multiple files"""
        updates = []

        async def callback(snapshot: ProgressSnapshot):
            updates.append(snapshot)

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        # Create multiple files
        file1 = temp_export_dir / "file1.md"
        file1.write_text("- [x] Task 1\n- [ ] Task 2")

        file2 = temp_export_dir / "file2.md"
        file2.write_text("- [x] Task 3\n- [x] Task 4")

        await monitor.start_monitoring()
        await asyncio.sleep(0.3)

        # Verify all checkboxes found
        assert len(updates) >= 1
        snapshot = updates[-1]
        assert snapshot.total == 4
        assert snapshot.completed == 3

        await monitor.stop_monitoring()


class TestSnapshotComparison:
    """Tests for snapshot comparison"""

    def test_snapshots_equal(self, temp_export_dir):
        """Test snapshot equality check"""

        async def callback(snapshot: ProgressSnapshot):
            pass

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        s1 = ProgressSnapshot(total=5, completed=2, percentage=40.0)
        s2 = ProgressSnapshot(total=5, completed=2, percentage=40.0)
        s3 = ProgressSnapshot(total=5, completed=3, percentage=60.0)

        assert monitor._snapshots_equal(s1, s2)
        assert not monitor._snapshots_equal(s1, s3)


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_nonexistent_directory(self):
        """Test monitoring nonexistent directory"""
        nonexistent = Path("/tmp/nonexistent_test_dir_progress_monitor")

        updates = []

        async def callback(snapshot: ProgressSnapshot):
            updates.append(snapshot)

        monitor = ProgressMonitor(
            export_dir=nonexistent, update_callback=callback, throttle_interval=0.1
        )

        # Should create directory and start without error
        await monitor.start_monitoring()
        assert nonexistent.exists()

        await monitor.stop_monitoring()

        # Cleanup
        if nonexistent.exists():
            nonexistent.rmdir()

    @pytest.mark.asyncio
    async def test_malformed_markdown(self, temp_export_dir):
        """Test handling malformed markdown"""
        malformed = """
# Broken Markdown
- [x Incomplete checkbox
- [] Empty checkbox
- [x] Valid checkbox
"""
        test_file = temp_export_dir / "malformed.md"
        test_file.write_text(malformed)

        updates = []

        async def callback(snapshot: ProgressSnapshot):
            updates.append(snapshot)

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        # Should handle gracefully
        checkboxes = monitor._parse_checkboxes_from_file(test_file)

        # Should only parse valid checkbox
        assert len(checkboxes) == 1
        assert checkboxes[0].status == "completed"

    def test_get_current_progress(self, temp_export_dir):
        """Test getting current progress"""

        async def callback(snapshot: ProgressSnapshot):
            pass

        monitor = ProgressMonitor(
            export_dir=temp_export_dir, update_callback=callback, throttle_interval=0.1
        )

        # Initially should be None
        assert monitor.get_current_progress() is None

        # After setting snapshot
        test_snapshot = ProgressSnapshot(total=5, completed=2, percentage=40.0)
        monitor.current_snapshot = test_snapshot

        assert monitor.get_current_progress() == test_snapshot


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
