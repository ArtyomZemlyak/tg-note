"""
Tests for Bot Vector Search Manager

Tests the bot-side vector search integration that:
- Checks MCP Hub for vector search availability
- Triggers indexing
- Monitors changes for reindexing
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.vector_search_manager import (
    BotVectorSearchManager,
    KnowledgeBaseChange,
    initialize_vector_search_for_bot,
)


@pytest.fixture
def temp_kb():
    """Create a temporary knowledge base for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_path = Path(tmpdir)

        # Create test directory structure
        (kb_path / "user_1" / "topics").mkdir(parents=True)
        (kb_path / "user_2" / "topics").mkdir(parents=True)

        # Create test files
        (kb_path / "user_1" / "topics" / "test.md").write_text("# Test\n\nContent for user 1")
        (kb_path / "user_2" / "topics" / "test.md").write_text("# Test\n\nContent for user 2")

        yield kb_path


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for hashes"""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = Path(tmpdir)
        yield data_path


@pytest.fixture
def manager(temp_kb, temp_data_dir):
    """Create a BotVectorSearchManager instance"""
    mgr = BotVectorSearchManager(
        mcp_hub_url="http://localhost:8765", kb_root_path=temp_kb, subscribe_to_events=False
    )
    # Override hash file path to use temp directory
    mgr._hash_file = temp_data_dir / "hashes.json"
    return mgr


class TestKnowledgeBaseChange:
    """Tests for KnowledgeBaseChange"""

    def test_no_changes(self):
        """Test empty change"""
        change = KnowledgeBaseChange()
        assert not change.has_changes()

    def test_with_changes(self):
        """Test change with modifications"""
        change = KnowledgeBaseChange()
        change.added.add("file1.md")
        change.modified.add("file2.md")
        change.deleted.add("file3.md")

        assert change.has_changes()
        assert len(change.added) == 1
        assert len(change.modified) == 1
        assert len(change.deleted) == 1


class TestBotVectorSearchManager:
    """Tests for BotVectorSearchManager"""

    @pytest.mark.asyncio
    async def test_check_availability_success(self, manager):
        """Test checking vector search availability - success case"""
        # Mock successful health check with all required tools
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "status": "ok",
                "builtin_tools": {
                    "total": 5,
                    "names": [
                        "vector_search",
                        "reindex_vector",
                        "add_vector_documents",
                        "delete_vector_documents",
                        "update_vector_documents",
                    ],
                },
            }
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock session that properly handles async context managers
            mock_session = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(
                return_value={
                    "status": "ok",
                    "builtin_tools": {
                        "total": 5,
                        "names": [
                            "vector_search",
                            "reindex_vector",
                            "add_vector_documents",
                            "delete_vector_documents",
                            "update_vector_documents",
                        ],
                    },
                }
            )

            # Set up the context manager chain
            mock_get = MagicMock()
            mock_get.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_get.__aexit__ = AsyncMock(return_value=None)
            mock_session.get.return_value = mock_get

            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

            available = await manager.check_vector_search_availability()

            assert available is True
            assert manager.vector_search_available is True

    @pytest.mark.asyncio
    async def test_check_availability_not_available(self, manager):
        """Test checking vector search availability - not available"""
        # Mock health check without vector search tools
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "status": "ok",
                "builtin_tools": {
                    "total": 2,
                    "names": ["store_memory", "retrieve_memory"],
                },
            }
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock session that properly handles async context managers
            mock_session = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(
                return_value={
                    "status": "ok",
                    "builtin_tools": {
                        "total": 2,
                        "names": ["store_memory", "retrieve_memory"],
                    },
                }
            )

            # Set up the context manager chain
            mock_get = MagicMock()
            mock_get.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_get.__aexit__ = AsyncMock(return_value=None)
            mock_session.get.return_value = mock_get

            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

            available = await manager.check_vector_search_availability()

            assert available is False
            assert manager.vector_search_available is False

    @pytest.mark.asyncio
    async def test_check_availability_error(self, manager):
        """Test checking vector search availability - error case"""
        # Mock failed health check
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = Exception(
                "Connection error"
            )

            available = await manager.check_vector_search_availability()

            assert available is False
            assert manager.vector_search_available is False

    @pytest.mark.asyncio
    async def test_scan_knowledge_bases(self, manager, temp_kb):
        """Test scanning knowledge bases and computing hashes"""
        await manager._scan_knowledge_bases()

        # Should have found markdown files
        assert len(manager._file_hashes) == 2
        assert "user_1/topics/test.md" in manager._file_hashes
        assert "user_2/topics/test.md" in manager._file_hashes

    @pytest.mark.asyncio
    async def test_detect_changes_new_file(self, manager):
        """Test detecting new files"""
        previous = {"file1.md": "hash1"}
        current = {"file1.md": "hash1", "file2.md": "hash2"}

        changes = manager._detect_changes(previous, current)

        assert changes.has_changes()
        assert "file2.md" in changes.added
        assert len(changes.modified) == 0
        assert len(changes.deleted) == 0

    @pytest.mark.asyncio
    async def test_detect_changes_modified_file(self, manager):
        """Test detecting modified files"""
        previous = {"file1.md": "hash1"}
        current = {"file1.md": "hash2"}

        changes = manager._detect_changes(previous, current)

        assert changes.has_changes()
        assert "file1.md" in changes.modified
        assert len(changes.added) == 0
        assert len(changes.deleted) == 0

    @pytest.mark.asyncio
    async def test_detect_changes_deleted_file(self, manager):
        """Test detecting deleted files"""
        previous = {"file1.md": "hash1", "file2.md": "hash2"}
        current = {"file1.md": "hash1"}

        changes = manager._detect_changes(previous, current)

        assert changes.has_changes()
        assert "file2.md" in changes.deleted
        assert len(changes.added) == 0
        assert len(changes.modified) == 0

    @pytest.mark.asyncio
    async def test_save_and_load_hashes(self, manager):
        """Test saving and loading file hashes"""
        # Set some hashes
        manager._file_hashes = {
            "file1.md": "hash1",
            "file2.md": "hash2",
        }

        # Save
        await manager._save_file_hashes()

        # Clear and reload
        manager._file_hashes = {}
        await manager._load_file_hashes()

        # Verify
        assert len(manager._file_hashes) == 2
        assert manager._file_hashes["file1.md"] == "hash1"
        assert manager._file_hashes["file2.md"] == "hash2"

    @pytest.mark.asyncio
    async def test_perform_initial_indexing_not_available(self, manager):
        """Test initial indexing when vector search is not available"""
        manager.vector_search_available = False

        result = await manager.perform_initial_indexing()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_and_reindex_changes_not_available(self, manager):
        """Test reindexing when vector search is not available"""
        manager.vector_search_available = False

        result = await manager.check_and_reindex_changes()

        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown(self, manager):
        """Test shutdown functionality"""

        # Create a fake reindex task
        async def fake_task():
            await asyncio.sleep(10)

        manager._reindex_task = asyncio.create_task(fake_task())

        # Shutdown should cancel the task
        await manager.shutdown()

        assert manager._shutdown is True
        assert manager._reindex_task.cancelled()

    @pytest.mark.asyncio
    async def test_trigger_reindex_when_shutdown(self, manager):
        """Test that trigger_reindex does nothing when shutdown"""
        manager.vector_search_available = True
        manager._shutdown = True

        result = await manager.trigger_reindex()

        assert result is False


class TestInitializeVectorSearchForBot:
    """Tests for initialize_vector_search_for_bot function"""

    @pytest.mark.asyncio
    async def test_initialize_disabled_in_config(self, temp_kb):
        """Test initialization when vector search is disabled"""
        with patch("src.bot.vector_search_manager.settings") as mock_settings:
            mock_settings.VECTOR_SEARCH_ENABLED = False

            result = await initialize_vector_search_for_bot(
                mcp_hub_url="http://localhost:8765",
                kb_root_path=temp_kb,
                start_monitoring=False,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_initialize_not_available_in_hub(self, temp_kb):
        """Test initialization when vector search is not available in MCP Hub"""
        with patch("src.bot.vector_search_manager.settings") as mock_settings:
            mock_settings.VECTOR_SEARCH_ENABLED = True

            # Mock unavailable response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "status": "ok",
                    "builtin_tools": {
                        "total": 0,
                        "names": [],
                    },
                }
            )

            with patch("aiohttp.ClientSession") as mock_session_class:
                # Create a mock session that properly handles async context managers
                mock_session = MagicMock()
                mock_response_obj = MagicMock()
                mock_response_obj.status = 200
                mock_response_obj.json = AsyncMock(
                    return_value={
                        "status": "ok",
                        "builtin_tools": {
                            "total": 0,
                            "names": [],
                        },
                    }
                )

                # Set up the context manager chain
                mock_get = MagicMock()
                mock_get.__aenter__ = AsyncMock(return_value=mock_response_obj)
                mock_get.__aexit__ = AsyncMock(return_value=None)
                mock_session.get.return_value = mock_get

                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await initialize_vector_search_for_bot(
                    mcp_hub_url="http://localhost:8765",
                    kb_root_path=temp_kb,
                    start_monitoring=False,
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_initialize_success(self, temp_kb):
        """Test successful initialization"""
        with patch("src.bot.vector_search_manager.settings") as mock_settings:
            mock_settings.VECTOR_SEARCH_ENABLED = True

            # Mock available response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "status": "ok",
                    "builtin_tools": {
                        "total": 2,
                        "names": ["vector_search", "reindex_vector"],
                    },
                }
            )

            with patch("aiohttp.ClientSession") as mock_session_class:
                # Create a mock session that properly handles async context managers
                mock_session = MagicMock()
                mock_response_obj = MagicMock()
                mock_response_obj.status = 200
                mock_response_obj.json = AsyncMock(
                    return_value={
                        "status": "ok",
                        "builtin_tools": {
                            "total": 5,
                            "names": [
                                "vector_search",
                                "reindex_vector",
                                "add_vector_documents",
                                "delete_vector_documents",
                                "update_vector_documents",
                            ],
                        },
                    }
                )

                # Set up the context manager chain
                mock_get = MagicMock()
                mock_get.__aenter__ = AsyncMock(return_value=mock_response_obj)
                mock_get.__aexit__ = AsyncMock(return_value=None)
                mock_session.get.return_value = mock_get

                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await initialize_vector_search_for_bot(
                    mcp_hub_url="http://localhost:8765",
                    kb_root_path=temp_kb,
                    start_monitoring=False,
                )

                assert result is not None
                assert isinstance(result, BotVectorSearchManager)
                assert result.vector_search_available is True
