"""
Tests for Git Operations
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.knowledge_base.git_ops import GitOperations

# Check if GitPython is available
try:
    from git import Repo

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


@pytest.mark.skipif(not GIT_AVAILABLE, reason="GitPython not available")
class TestGitOperations:
    """Test GitOperations functionality"""

    @pytest.fixture
    def temp_repo_path(self):
        """Create temporary git repository"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test_repo"
            repo_path.mkdir(parents=True)
            
            # Initialize git repo
            repo = Repo.init(repo_path)
            
            # Create initial commit
            test_file = repo_path / "README.md"
            test_file.write_text("# Test Repo")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")
            
            yield str(repo_path)

    @pytest.fixture
    def git_ops(self, temp_repo_path):
        """Create GitOperations instance"""
        return GitOperations(temp_repo_path, enabled=True)

    def test_init_with_valid_repo(self, temp_repo_path):
        """Test initialization with valid git repository"""
        git_ops = GitOperations(temp_repo_path, enabled=True)
        assert git_ops.enabled is True
        assert git_ops.repo is not None

    def test_init_with_invalid_repo(self):
        """Test initialization with invalid git repository"""
        with tempfile.TemporaryDirectory() as tmpdir:
            non_repo_path = Path(tmpdir) / "not_a_repo"
            non_repo_path.mkdir(parents=True)
            
            git_ops = GitOperations(str(non_repo_path), enabled=True)
            # Should disable git operations if not a valid repo
            assert git_ops.enabled is False

    def test_add_file(self, git_ops, temp_repo_path):
        """Test adding file to git"""
        # Create a new file
        test_file = Path(temp_repo_path) / "test.txt"
        test_file.write_text("test content")
        
        # Add file
        result = git_ops.add(str(test_file))
        assert result is True

    def test_add_nonexistent_file(self, git_ops, temp_repo_path):
        """Test adding non-existent file"""
        result = git_ops.add(str(Path(temp_repo_path) / "nonexistent.txt"))
        assert result is False

    def test_commit(self, git_ops, temp_repo_path):
        """Test committing changes"""
        # Create and add a file
        test_file = Path(temp_repo_path) / "test.txt"
        test_file.write_text("test content")
        git_ops.add(str(test_file))
        
        # Commit
        result = git_ops.commit("Test commit")
        assert result is True

    def test_pull_no_remote(self, git_ops):
        """Test pull when no remote is configured"""
        success, message = git_ops.pull()
        assert success is False
        assert "not found" in message.lower() or "remote" in message.lower()

    def test_pull_with_uncommitted_changes(self, git_ops, temp_repo_path):
        """Test pull with uncommitted changes"""
        # Create uncommitted change
        test_file = Path(temp_repo_path) / "README.md"
        test_file.write_text("# Modified")
        
        success, message = git_ops.pull()
        assert success is False
        assert "uncommitted" in message.lower()

    @patch("src.knowledge_base.git_ops.Repo")
    def test_pull_successful(self, mock_repo_class, temp_repo_path):
        """Test successful pull operation"""
        # Create mock repo with remote
        mock_repo = MagicMock()
        mock_remote = MagicMock()
        mock_pull_info = MagicMock()
        
        # Configure mocks
        mock_pull_info.flags = 64  # FAST_FORWARD flag
        mock_remote.pull.return_value = [mock_pull_info]
        mock_repo.remote.return_value = mock_remote
        mock_repo.is_dirty.return_value = False
        mock_repo.active_branch.name = "main"
        
        # Mock tracking branch
        mock_tracking = MagicMock()
        mock_tracking.remote_head = "main"
        mock_repo.active_branch.tracking_branch.return_value = mock_tracking
        
        mock_repo_class.return_value = mock_repo
        
        # Create GitOperations with mocked repo
        git_ops = GitOperations(temp_repo_path, enabled=True)
        git_ops.repo = mock_repo
        
        # Test pull
        success, message = git_ops.pull()
        assert success is True
        assert "pulled" in message.lower() or "up to date" in message.lower()

    @patch("src.knowledge_base.git_ops.Repo")
    def test_pull_already_up_to_date(self, mock_repo_class, temp_repo_path):
        """Test pull when already up to date"""
        mock_repo = MagicMock()
        mock_remote = MagicMock()
        mock_pull_info = MagicMock()
        
        # Configure mocks for up-to-date status
        mock_pull_info.flags = 4  # HEAD_UPTODATE flag
        mock_remote.pull.return_value = [mock_pull_info]
        mock_repo.remote.return_value = mock_remote
        mock_repo.is_dirty.return_value = False
        mock_repo.active_branch.name = "main"
        
        mock_tracking = MagicMock()
        mock_tracking.remote_head = "main"
        mock_repo.active_branch.tracking_branch.return_value = mock_tracking
        
        mock_repo_class.return_value = mock_repo
        
        git_ops = GitOperations(temp_repo_path, enabled=True)
        git_ops.repo = mock_repo
        
        success, message = git_ops.pull()
        assert success is True
        assert "up to date" in message.lower()

    def test_pull_disabled(self):
        """Test pull when git operations are disabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_ops = GitOperations(tmpdir, enabled=False)
            success, message = git_ops.pull()
            assert success is False
            assert "disabled" in message.lower()

    def test_add_commit_push(self, git_ops, temp_repo_path):
        """Test combined add, commit, push operation"""
        # Create a new file
        test_file = Path(temp_repo_path) / "test.txt"
        test_file.write_text("test content")
        
        # This will fail because there's no remote, but it tests the flow
        result = git_ops.add_commit_push(str(test_file), "Test commit")
        assert result is False  # No remote configured

    def test_disabled_operations(self):
        """Test that operations return False when disabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_ops = GitOperations(tmpdir, enabled=False)
            
            assert git_ops.add("test.txt") is False
            assert git_ops.commit("test") is False
            assert git_ops.push() is False
            
            success, _ = git_ops.pull()
            assert success is False
