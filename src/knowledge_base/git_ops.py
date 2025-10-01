"""
Git Operations
Handles git operations for knowledge base
"""

import logging
from pathlib import Path
from typing import Optional

try:
    from git import Repo, InvalidGitRepositoryError

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None  # type: ignore
    InvalidGitRepositoryError = Exception  # type: ignore

logger = logging.getLogger(__name__)


class GitOperations:
    """Manages git operations for knowledge base"""

    def __init__(self, repo_path: str, enabled: bool = True):
        self.repo_path = Path(repo_path)
        self.enabled = enabled and GIT_AVAILABLE
        self.repo: Optional[Repo] = None

        if self.enabled:
            self._initialize_repo()

    def _initialize_repo(self) -> None:
        """Initialize git repository"""
        if not GIT_AVAILABLE:
            logger.warning("GitPython not available, git operations disabled")
            self.enabled = False
            return

        try:
            self.repo = Repo(self.repo_path)
            logger.info(f"Git repository initialized at {self.repo_path}")
        except InvalidGitRepositoryError:
            logger.warning(f"Not a git repository: {self.repo_path}")
            self.enabled = False

    def add(self, file_path: str) -> bool:
        """
        Add file to git staging

        Args:
            file_path: Path to file to add

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.repo:
            return False

        try:
            self.repo.index.add([file_path])
            logger.info(f"Added file to git: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to add file to git: {e}")
            return False

    def commit(self, message: str) -> bool:
        """
        Commit staged changes

        Args:
            message: Commit message

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.repo:
            return False

        try:
            self.repo.index.commit(message)
            logger.info(f"Committed changes: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to commit: {e}")
            return False

    def push(self, remote: str = "origin", branch: str = "main") -> bool:
        """
        Push commits to remote

        Args:
            remote: Remote name
            branch: Branch name

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.repo:
            return False

        try:
            origin = self.repo.remote(remote)
            origin.push(branch)
            logger.info(f"Pushed to {remote}/{branch}")
            return True
        except Exception as e:
            logger.error(f"Failed to push: {e}")
            return False

    def add_commit_push(
        self, file_path: str, message: str, remote: str = "origin", branch: str = "main"
    ) -> bool:
        """
        Add, commit and push in one operation

        Args:
            file_path: Path to file to add
            message: Commit message
            remote: Remote name
            branch: Branch name

        Returns:
            True if all operations successful, False otherwise
        """
        if not self.add(file_path):
            return False

        if not self.commit(message):
            return False

        return self.push(remote, branch)
