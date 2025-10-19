"""
Test Knowledge Base Initialization from GitHub
Tests the fix for missing topics directory when cloning from GitHub
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.knowledge_base.repository import RepositoryManager


class TestKBInitializationFromGitHub:
    """Test KB initialization from GitHub with topics directory"""

    @pytest.fixture
    def temp_base_path(self):
        """Create temporary base path for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def repo_manager(self, temp_base_path):
        """Create repository manager with temp path"""
        return RepositoryManager(base_path=str(temp_base_path))

    @patch("src.knowledge_base.repository.Repo")
    def test_clone_github_kb_creates_topics_directory(self, mock_repo, repo_manager, temp_base_path):
        """Test that cloning from GitHub creates topics directory"""
        # Setup mock
        kb_name = "test-kb"
        github_url = "https://github.com/user/test-kb.git"
        kb_path = temp_base_path / kb_name

        # Mock clone_from to create the directory
        def mock_clone_from(url, path):
            Path(path).mkdir(parents=True, exist_ok=True)
            # Create a .git directory to simulate a real clone
            (Path(path) / ".git").mkdir(exist_ok=True)
            return MagicMock()

        mock_repo.clone_from.side_effect = mock_clone_from

        # Clone repository
        success, message, returned_path = repo_manager.clone_github_kb(github_url, kb_name)

        # Verify success
        assert success, f"Clone failed: {message}"
        assert "Successfully cloned" in message
        assert returned_path == kb_path

        # Verify topics directory was created
        topics_path = kb_path / "topics"
        assert topics_path.exists(), "topics directory should exist after clone"
        assert topics_path.is_dir(), "topics should be a directory"

        # Verify basic category directories were created
        for category in ["general", "ai", "tech", "science", "business"]:
            category_path = topics_path / category
            assert category_path.exists(), f"{category} directory should exist"
            assert category_path.is_dir(), f"{category} should be a directory"

    @patch("src.knowledge_base.repository.Repo")
    def test_clone_github_kb_preserves_existing_topics(
        self, mock_repo, repo_manager, temp_base_path
    ):
        """Test that cloning doesn't overwrite existing topics structure"""
        # Setup mock
        kb_name = "test-kb"
        github_url = "https://github.com/user/test-kb.git"
        kb_path = temp_base_path / kb_name

        # Mock clone_from to create the directory with existing topics
        def mock_clone_from(url, path):
            Path(path).mkdir(parents=True, exist_ok=True)
            (Path(path) / ".git").mkdir(exist_ok=True)
            # Create existing topics structure
            topics_path = Path(path) / "topics"
            topics_path.mkdir(exist_ok=True)
            (topics_path / "custom-category").mkdir(exist_ok=True)
            # Create a test file
            test_file = topics_path / "custom-category" / "test.md"
            test_file.write_text("# Test Content")
            return MagicMock()

        mock_repo.clone_from.side_effect = mock_clone_from

        # Clone repository
        success, message, returned_path = repo_manager.clone_github_kb(github_url, kb_name)

        # Verify success
        assert success, f"Clone failed: {message}"

        # Verify existing topics structure is preserved
        topics_path = kb_path / "topics"
        assert topics_path.exists()

        custom_category = topics_path / "custom-category"
        assert custom_category.exists(), "Custom category should be preserved"

        test_file = custom_category / "test.md"
        assert test_file.exists(), "Existing files should be preserved"
        assert test_file.read_text() == "# Test Content"

    @patch("src.knowledge_base.repository.Repo")
    def test_pull_updates_ensures_topics_directory(self, mock_repo, repo_manager, temp_base_path):
        """Test that pulling updates ensures topics directory exists"""
        # Setup
        kb_name = "test-kb"
        kb_path = temp_base_path / kb_name
        kb_path.mkdir(parents=True)
        (kb_path / ".git").mkdir()

        # Create mock repo
        mock_repo_instance = MagicMock()
        mock_repo_instance.is_dirty.return_value = False
        mock_remote = MagicMock()
        mock_remote.pull.return_value = []
        mock_repo_instance.remote.return_value = mock_remote
        mock_repo.return_value = mock_repo_instance

        # Pull updates
        success, message, returned_path = repo_manager.pull_updates(kb_path)

        # Verify success
        assert success, f"Pull failed: {message}"
        assert "Successfully pulled" in message

        # Verify topics directory was created
        topics_path = kb_path / "topics"
        assert topics_path.exists(), "topics directory should exist after pull"
        assert topics_path.is_dir(), "topics should be a directory"

    def test_ensure_kb_structure_creates_minimal_structure(self, repo_manager, temp_base_path):
        """Test that _ensure_kb_structure creates minimal required structure"""
        # Create empty KB directory
        kb_path = temp_base_path / "test-kb"
        kb_path.mkdir(parents=True)

        # Ensure structure
        repo_manager._ensure_kb_structure(kb_path)

        # Verify topics directory exists
        topics_path = kb_path / "topics"
        assert topics_path.exists()
        assert topics_path.is_dir()

        # Verify category directories exist
        for category in ["general", "ai", "tech", "science", "business"]:
            category_path = topics_path / category
            assert category_path.exists()
            assert category_path.is_dir()

        # Verify README exists
        readme_path = kb_path / "README.md"
        assert readme_path.exists()
        assert readme_path.is_file()

        # Verify .gitignore exists
        gitignore_path = kb_path / ".gitignore"
        assert gitignore_path.exists()
        assert gitignore_path.is_file()

    def test_ensure_kb_structure_preserves_existing_files(self, repo_manager, temp_base_path):
        """Test that _ensure_kb_structure doesn't overwrite existing files"""
        # Create KB directory with existing files
        kb_path = temp_base_path / "test-kb"
        kb_path.mkdir(parents=True)

        # Create existing README with custom content
        readme_path = kb_path / "README.md"
        custom_content = "# My Custom README"
        readme_path.write_text(custom_content)

        # Create existing topics structure
        topics_path = kb_path / "topics"
        topics_path.mkdir()
        custom_file = topics_path / "custom.md"
        custom_file.write_text("# Custom File")

        # Ensure structure
        repo_manager._ensure_kb_structure(kb_path)

        # Verify README wasn't overwritten
        assert readme_path.read_text() == custom_content, "README should not be overwritten"

        # Verify custom files are preserved
        assert custom_file.exists(), "Custom files should be preserved"
        assert custom_file.read_text() == "# Custom File"
