"""
Git Operations
Handles git operations for knowledge base
"""

from pathlib import Path
from typing import Optional

from loguru import logger

try:
    from git import GitCommandError, InvalidGitRepositoryError, Repo

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None
    InvalidGitRepositoryError = Exception
    GitCommandError = Exception


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
            logger.warning(f"Cannot add file to git - file does not exist: {file_path}")
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
            logger.error(f"File not found when adding to git: {file_path}. " f"Error: {e}")
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

    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> tuple[bool, str]:
        """
        Pull latest changes from remote repository

        Args:
            remote: Remote name
            branch: Branch name to pull from. If None/"auto", pulls current branch tracking branch.

        Returns:
            Tuple of (success, message)
        """
        if not self.enabled or not self.repo:
            return False, "Git operations disabled"

        # Check if there are uncommitted changes
        if self.repo.is_dirty(untracked_files=False):
            logger.warning("Repository has uncommitted changes, cannot pull")
            return False, "Repository has uncommitted changes. Commit or stash them first."

        # Validate remote
        try:
            remote_obj = self.repo.remote(remote)
        except ValueError:
            available = ", ".join(r.name for r in self.repo.remotes) or "<none>"
            error_msg = (
                f"Remote '{remote}' not found. Available remotes: {available}. "
                f"To set a remote, run: git remote add origin <url>"
            )
            logger.error(f"Failed to pull: {error_msg}")
            return False, error_msg

        # Determine current branch
        active_branch_name: Optional[str] = None
        try:
            active_branch_name = self.repo.active_branch.name  # type: ignore[attr-defined]
        except Exception:
            # Detached HEAD or no branch
            logger.warning("Not on any branch (detached HEAD), cannot pull")
            return False, "Not on any branch (detached HEAD state)"

        # Determine which branch to pull from
        target_branch = branch if branch not in (None, "", "auto", "current", "HEAD") else None
        if target_branch is None:
            # Try to get tracking branch
            try:
                tracking = self.repo.active_branch.tracking_branch()  # type: ignore[attr-defined]
                if tracking:
                    target_branch = tracking.remote_head
                else:
                    # No tracking branch set, assume same name as local branch
                    target_branch = active_branch_name
            except Exception:
                target_branch = active_branch_name

        # Perform pull
        try:
            pull_info = remote_obj.pull(target_branch)
            
            # Check if there were any changes
            if pull_info and len(pull_info) > 0:
                flags = pull_info[0].flags
                if flags & 4:  # HEAD_UPTODATE flag
                    logger.info(f"Already up to date with {remote}/{target_branch}")
                    return True, "Already up to date"
                elif flags & 64:  # FAST_FORWARD flag
                    logger.info(f"Successfully pulled (fast-forward) from {remote}/{target_branch}")
                    return True, "Successfully pulled (fast-forward)"
                else:
                    logger.info(f"Successfully pulled from {remote}/{target_branch}")
                    return True, "Successfully pulled"
            else:
                logger.info(f"Pull completed from {remote}/{target_branch}")
                return True, "Pull completed"
                
        except GitCommandError as gce:  # type: ignore[misc]
            error_msg = str(gce)
            # Check for merge conflicts
            if "conflict" in error_msg.lower() or "merge" in error_msg.lower():
                logger.error(f"Merge conflict during pull: {gce}")
                return False, f"Merge conflict during pull. Please resolve manually."
            else:
                logger.error(f"Failed to pull (git): {gce}")
                return False, f"Git error during pull: {error_msg}"
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(
                f"Failed to pull from {remote}/{target_branch}: {error_msg}"
            )
            return False, f"Error during pull: {error_msg}"

    def push(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """
        Push commits to remote

        Args:
            remote: Remote name
            branch: Branch name to push to on remote. If None/"auto", pushes current branch.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.repo:
            return False

        # Validate remote
        try:
            remote_obj = self.repo.remote(remote)
        except ValueError:
            available = ", ".join(r.name for r in self.repo.remotes) or "<none>"
            logger.error(
                f"Failed to push: Remote '{remote}' not found. Available remotes: {available}. "
                f"To set a remote, run: git remote add origin <url>"
            )
            return False

        # Determine local ref (current branch or HEAD)
        active_branch_name: Optional[str] = None
        try:
            active_branch_name = self.repo.active_branch.name  # type: ignore[attr-defined]
        except Exception:
            # Detached HEAD or no branch
            active_branch_name = None

        # Determine target branch on remote
        target_branch = branch if branch not in (None, "", "auto", "current", "HEAD") else None
        if target_branch is None:
            target_branch = active_branch_name or "main"

        # Determine local refspec (what to push)
        local_ref = active_branch_name or "HEAD"

        # Check tracking configuration
        has_tracking = False
        if active_branch_name:
            try:
                tracking = self.repo.active_branch.tracking_branch()  # type: ignore[attr-defined]
                has_tracking = bool(
                    tracking
                    and tracking.remote_name == remote
                    and tracking.remote_head == target_branch
                )
            except Exception:
                has_tracking = False

        # Perform push
        try:
            if has_tracking:
                # Tracking set correctly, simple push
                self.repo.git.push(remote)
            else:
                # First push or remote/branch mismatch: set upstream while pushing
                self.repo.git.push("--set-upstream", remote, f"{local_ref}:{target_branch}")

            logger.info(f"Pushed to {remote}/{target_branch}")
            return True
        except GitCommandError as gce:  # type: ignore[misc]
            logger.error(f"Failed to push (git): {gce}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to push: {type(e).__name__}: {e}. "
                f"Tried pushing {local_ref} -> {remote}/{target_branch}."
            )
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
