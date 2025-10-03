"""
Git Operations
Handles git operations for knowledge base
"""

from pathlib import Path
from typing import Optional
from loguru import logger

try:
    from git import Repo, InvalidGitRepositoryError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None
    InvalidGitRepositoryError = Exception


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
        
        # Convert to Path and check if file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            logger.warning(
                f"Cannot add file to git - file does not exist: {file_path}"
            )
            return False
        
        try:
            # Convert to relative path from repo root for better git compatibility
            try:
                relative_path = file_path_obj.relative_to(self.repo_path)
                path_to_add = str(relative_path)
            except ValueError:
                # File is outside repo, use absolute path
                path_to_add = str(file_path_obj.absolute())
            
            self.repo.index.add([path_to_add])
            logger.info(f"Added file to git: {path_to_add}")
            return True
        except FileNotFoundError as e:
            logger.error(
                f"File not found when adding to git: {file_path}. "
                f"Error: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to add file to git: {file_path}. "
                f"Error type: {type(e).__name__}, Error: {e}"
            )
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
        self,
        file_path: str,
        message: str,
        remote: str = "origin",
        branch: str = "main"
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