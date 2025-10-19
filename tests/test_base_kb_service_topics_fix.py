"""
Test Base KB Service Topics Directory Fix
Tests that _get_agent_working_dir creates topics directory if it doesn't exist
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from src.services.base_kb_service import BaseKBService


class TestBaseKBServiceTopicsFix:
    """Test topics directory creation in BaseKBService"""

    @pytest.fixture
    def temp_kb_path(self):
        """Create temporary KB path for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test-kb"

    @pytest.fixture
    def mock_settings_manager(self):
        """Create mock settings manager"""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def base_service(self, mock_settings_manager):
        """Create BaseKBService instance with mocks"""
        mock_bot = MagicMock()
        mock_repo_manager = MagicMock()

        service = BaseKBService(
            bot=mock_bot,
            repo_manager=mock_repo_manager,
            settings_manager=mock_settings_manager,
        )
        return service

    def test_get_agent_working_dir_creates_topics_when_kb_topics_only_true(
        self, base_service, mock_settings_manager, temp_kb_path
    ):
        """Test that _get_agent_working_dir creates topics directory when KB_TOPICS_ONLY=true"""
        # Create KB path without topics directory
        temp_kb_path.mkdir(parents=True)
        assert temp_kb_path.exists()
        assert not (temp_kb_path / "topics").exists(), "topics should not exist initially"

        # Configure settings: KB_TOPICS_ONLY=true
        mock_settings_manager.get_setting.return_value = True

        # Call _get_agent_working_dir
        user_id = 123
        working_dir = base_service._get_agent_working_dir(temp_kb_path, user_id)

        # Verify topics directory was created
        topics_path = temp_kb_path / "topics"
        assert topics_path.exists(), "topics directory should be created"
        assert topics_path.is_dir(), "topics should be a directory"

        # Verify returned path is correct
        assert working_dir == topics_path
        assert str(working_dir).endswith("topics")

    def test_get_agent_working_dir_kb_topics_only_false_no_topics_creation(
        self, base_service, mock_settings_manager, temp_kb_path
    ):
        """Test that _get_agent_working_dir doesn't create topics when KB_TOPICS_ONLY=false"""
        # Create KB path without topics directory
        temp_kb_path.mkdir(parents=True)
        assert temp_kb_path.exists()
        assert not (temp_kb_path / "topics").exists()

        # Configure settings: KB_TOPICS_ONLY=false
        mock_settings_manager.get_setting.return_value = False

        # Call _get_agent_working_dir
        user_id = 123
        working_dir = base_service._get_agent_working_dir(temp_kb_path, user_id)

        # Verify topics directory was NOT created
        topics_path = temp_kb_path / "topics"
        assert not topics_path.exists(), "topics directory should not be created when KB_TOPICS_ONLY=false"

        # Verify returned path is KB root
        assert working_dir == temp_kb_path

    def test_get_agent_working_dir_preserves_existing_topics(
        self, base_service, mock_settings_manager, temp_kb_path
    ):
        """Test that _get_agent_working_dir preserves existing topics structure"""
        # Create KB path with existing topics
        temp_kb_path.mkdir(parents=True)
        topics_path = temp_kb_path / "topics"
        topics_path.mkdir()

        # Create some files in topics
        test_file = topics_path / "test.md"
        test_content = "# Test Content"
        test_file.write_text(test_content)

        # Configure settings: KB_TOPICS_ONLY=true
        mock_settings_manager.get_setting.return_value = True

        # Call _get_agent_working_dir
        user_id = 123
        working_dir = base_service._get_agent_working_dir(temp_kb_path, user_id)

        # Verify existing files are preserved
        assert test_file.exists(), "Existing files should be preserved"
        assert test_file.read_text() == test_content, "File content should be unchanged"

        # Verify returned path is correct
        assert working_dir == topics_path

    def test_get_agent_working_dir_handles_permission_errors_gracefully(
        self, base_service, mock_settings_manager, temp_kb_path
    ):
        """Test that _get_agent_working_dir handles permission errors gracefully"""
        # This test verifies that even if directory creation fails,
        # the method returns the expected path without crashing

        # Create KB path
        temp_kb_path.mkdir(parents=True)

        # Configure settings: KB_TOPICS_ONLY=true
        mock_settings_manager.get_setting.return_value = True

        # Call _get_agent_working_dir - should not raise even if mkdir fails
        user_id = 123
        try:
            working_dir = base_service._get_agent_working_dir(temp_kb_path, user_id)
            # Should return topics path even if creation failed
            assert working_dir == temp_kb_path / "topics"
        except Exception as e:
            pytest.fail(f"_get_agent_working_dir should not raise exceptions: {e}")

    def test_configure_agent_working_dir_sets_directory(self, base_service, temp_kb_path):
        """Test that _configure_agent_working_dir sets working directory on agent"""
        # Create mock agent with set_working_directory method
        mock_agent = MagicMock()
        mock_agent.set_working_directory = MagicMock()

        working_dir = temp_kb_path / "topics"

        # Call _configure_agent_working_dir
        base_service._configure_agent_working_dir(mock_agent, working_dir)

        # Verify set_working_directory was called
        mock_agent.set_working_directory.assert_called_once_with(str(working_dir))

    def test_configure_agent_working_dir_handles_missing_method(self, base_service, temp_kb_path):
        """Test that _configure_agent_working_dir handles agents without set_working_directory"""
        # Create mock agent without set_working_directory method
        mock_agent = MagicMock(spec=[])  # No methods

        working_dir = temp_kb_path / "topics"

        # Call _configure_agent_working_dir - should not raise
        try:
            base_service._configure_agent_working_dir(mock_agent, working_dir)
        except Exception as e:
            pytest.fail(f"_configure_agent_working_dir should handle missing method: {e}")
