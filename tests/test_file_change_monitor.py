"""
Tests for File Change Monitor
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.bot.file_change_monitor import FileChangeMonitor
from src.bot.vector_search_manager import KnowledgeBaseChange


class TestFileChangeMonitor:
    """Test cases for FileChangeMonitor"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def monitor(self, temp_dir):
        """Create a FileChangeMonitor instance for testing"""
        kb_root = temp_dir / "kb"
        kb_root.mkdir()
        hash_file = temp_dir / "hashes.json"
        return FileChangeMonitor(kb_root, hash_file)

    def test_init(self, monitor, temp_dir):
        """Test FileChangeMonitor initialization"""
        assert monitor.kb_root_path == temp_dir / "kb"
        assert monitor.hash_file == temp_dir / "hashes.json"
        assert monitor._file_hashes == {}

    @pytest.mark.asyncio
    async def test_scan_knowledge_bases_empty(self, monitor):
        """Test scanning empty knowledge base"""
        await monitor._scan_knowledge_bases()
        assert monitor._file_hashes == {}

    @pytest.mark.asyncio
    async def test_scan_knowledge_bases_with_files(self, monitor, temp_dir):
        """Test scanning knowledge base with files"""
        # Create test files
        (monitor.kb_root_path / "file1.md").write_text("Content 1")
        (monitor.kb_root_path / "file2.md").write_text("Content 2")
        (monitor.kb_root_path / "subdir").mkdir()
        (monitor.kb_root_path / "subdir" / "file3.md").write_text("Content 3")

        await monitor._scan_knowledge_bases()

        assert len(monitor._file_hashes) == 3
        assert "file1.md" in monitor._file_hashes
        assert "file2.md" in monitor._file_hashes
        assert "subdir/file3.md" in monitor._file_hashes

    @pytest.mark.asyncio
    async def test_detect_changes_no_changes(self, monitor):
        """Test detecting changes when there are no changes"""
        # Set up previous and current state (same)
        monitor._file_hashes = {"file1.md": "hash1", "file2.md": "hash2"}
        previous = monitor._file_hashes.copy()

        changes = monitor._detect_changes(previous, monitor._file_hashes)

        assert not changes.has_changes()
        assert len(changes.added) == 0
        assert len(changes.modified) == 0
        assert len(changes.deleted) == 0

    @pytest.mark.asyncio
    async def test_detect_changes_added_files(self, monitor):
        """Test detecting added files"""
        previous = {"file1.md": "hash1"}
        current = {"file1.md": "hash1", "file2.md": "hash2", "file3.md": "hash3"}

        changes = monitor._detect_changes(previous, current)

        assert changes.has_changes()
        assert changes.added == {"file2.md", "file3.md"}
        assert len(changes.modified) == 0
        assert len(changes.deleted) == 0

    @pytest.mark.asyncio
    async def test_detect_changes_modified_files(self, monitor):
        """Test detecting modified files"""
        previous = {"file1.md": "hash1", "file2.md": "hash2"}
        current = {"file1.md": "hash1_new", "file2.md": "hash2"}

        changes = monitor._detect_changes(previous, current)

        assert changes.has_changes()
        assert changes.modified == {"file1.md"}
        assert len(changes.added) == 0
        assert len(changes.deleted) == 0

    @pytest.mark.asyncio
    async def test_detect_changes_deleted_files(self, monitor):
        """Test detecting deleted files"""
        previous = {"file1.md": "hash1", "file2.md": "hash2", "file3.md": "hash3"}
        current = {"file1.md": "hash1"}

        changes = monitor._detect_changes(previous, current)

        assert changes.has_changes()
        assert changes.deleted == {"file2.md", "file3.md"}
        assert len(changes.added) == 0
        assert len(changes.modified) == 0

    @pytest.mark.asyncio
    async def test_detect_changes_mixed_changes(self, monitor):
        """Test detecting mixed changes (added, modified, deleted)"""
        previous = {"file1.md": "hash1", "file2.md": "hash2", "file3.md": "hash3"}
        current = {"file1.md": "hash1_new", "file2.md": "hash2", "file4.md": "hash4"}

        changes = monitor._detect_changes(previous, current)

        assert changes.has_changes()
        assert changes.added == {"file4.md"}
        assert changes.modified == {"file1.md"}
        assert changes.deleted == {"file3.md"}

    @pytest.mark.asyncio
    async def test_load_file_hashes_file_not_exists(self, monitor):
        """Test loading file hashes when file doesn't exist"""
        await monitor.load_file_hashes()
        assert monitor._file_hashes == {}

    @pytest.mark.asyncio
    async def test_load_file_hashes_file_exists(self, monitor, temp_dir):
        """Test loading file hashes when file exists"""
        # Create hash file
        hash_data = {"file1.md": "hash1", "file2.md": "hash2"}
        with open(monitor.hash_file, "w") as f:
            json.dump(hash_data, f)

        await monitor.load_file_hashes()
        assert monitor._file_hashes == hash_data

    @pytest.mark.asyncio
    async def test_load_file_hashes_invalid_json(self, monitor, temp_dir):
        """Test loading file hashes with invalid JSON"""
        # Create invalid JSON file
        with open(monitor.hash_file, "w") as f:
            f.write("invalid json")

        await monitor.load_file_hashes()
        assert monitor._file_hashes == {}

    @pytest.mark.asyncio
    async def test_save_file_hashes(self, monitor, temp_dir):
        """Test saving file hashes"""
        monitor._file_hashes = {"file1.md": "hash1", "file2.md": "hash2"}

        await monitor.save_file_hashes()

        assert monitor.hash_file.exists()
        with open(monitor.hash_file, "r") as f:
            saved_data = json.load(f)
        assert saved_data == monitor._file_hashes

    @pytest.mark.asyncio
    async def test_read_documents_by_paths(self, monitor, temp_dir):
        """Test reading documents by paths"""
        # Create test files
        (monitor.kb_root_path / "file1.md").write_text("Content 1")
        (monitor.kb_root_path / "file2.md").write_text("Content 2")
        (monitor.kb_root_path / "subdir").mkdir()
        (monitor.kb_root_path / "subdir" / "file3.md").write_text("Content 3")

        documents = await monitor.read_documents_by_paths([
            "file1.md", "file2.md", "subdir/file3.md", "nonexistent.md"
        ])

        assert len(documents) == 3  # nonexistent.md should be skipped
        assert any(doc["id"] == "file1.md" for doc in documents)
        assert any(doc["id"] == "file2.md" for doc in documents)
        assert any(doc["id"] == "subdir/file3.md" for doc in documents)

        # Check document structure
        doc = next(doc for doc in documents if doc["id"] == "file1.md")
        assert doc["content"] == "Content 1"
        assert doc["metadata"]["file_path"] == "file1.md"
        assert doc["metadata"]["file_name"] == "file1.md"
        assert doc["metadata"]["file_size"] == len("Content 1")

    @pytest.mark.asyncio
    async def test_read_all_documents(self, monitor, temp_dir):
        """Test reading all documents"""
        # Create test files
        (monitor.kb_root_path / "file1.md").write_text("Content 1")
        (monitor.kb_root_path / "file2.md").write_text("Content 2")
        (monitor.kb_root_path / "subdir").mkdir()
        (monitor.kb_root_path / "subdir" / "file3.md").write_text("Content 3")

        documents = await monitor.read_all_documents()

        assert len(documents) == 3
        doc_ids = {doc["id"] for doc in documents}
        assert doc_ids == {"file1.md", "file2.md", "subdir/file3.md"}

    @pytest.mark.asyncio
    async def test_detect_changes_integration(self, monitor, temp_dir):
        """Test full integration of change detection"""
        # Create initial files
        (monitor.kb_root_path / "file1.md").write_text("Content 1")
        (monitor.kb_root_path / "file2.md").write_text("Content 2")

        # First scan
        await monitor._scan_knowledge_bases()
        initial_hashes = monitor._file_hashes.copy()

        # Save hashes
        await monitor.save_file_hashes()

        # Modify files
        (monitor.kb_root_path / "file1.md").write_text("Content 1 modified")
        (monitor.kb_root_path / "file3.md").write_text("Content 3")
        (monitor.kb_root_path / "file2.md").unlink()  # Delete file2.md

        # Load previous hashes and detect changes
        await monitor.load_file_hashes()
        changes = await monitor.detect_changes()

        assert changes.has_changes()
        assert changes.added == {"file3.md"}
        assert changes.modified == {"file1.md"}
        assert changes.deleted == {"file2.md"}

    @pytest.mark.asyncio
    async def test_knowledge_base_change_repr(self):
        """Test KnowledgeBaseChange string representation"""
        changes = KnowledgeBaseChange()
        changes.added.add("file1.md")
        changes.modified.add("file2.md")
        changes.deleted.add("file3.md")

        repr_str = repr(changes)
        assert "added=1" in repr_str
        assert "modified=1" in repr_str
        assert "deleted=1" in repr_str

    @pytest.mark.asyncio
    async def test_knowledge_base_change_has_changes(self):
        """Test KnowledgeBaseChange has_changes method"""
        changes = KnowledgeBaseChange()
        assert not changes.has_changes()

        changes.added.add("file1.md")
        assert changes.has_changes()

        changes.added.clear()
        changes.modified.add("file2.md")
        assert changes.has_changes()

        changes.modified.clear()
        changes.deleted.add("file3.md")
        assert changes.has_changes()