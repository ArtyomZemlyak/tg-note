"""
GitOps with Events - Wrapper for GitOps with Event Publishing

This module wraps GitOps methods to automatically publish events after git operations.
This allows any code using GitOps to automatically trigger reindexing without tight coupling.

AICODE-NOTE: This is a decorator/wrapper pattern that adds event publishing to GitOps
without modifying the original class. Follows Open/Closed Principle.

Usage:
    # Instead of using GitOps directly:
    git_ops = GitOps(repo_path)
    
    # Use GitOpsWithEvents:
    git_ops = GitOpsWithEvents(repo_path, user_id=123)
    
    # All git operations will automatically publish events
    git_ops.commit("Update")  # → Publishes KB_GIT_COMMIT event
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from .git_ops import GitOps
from ._git_event_publisher import (
    publish_git_commit_event,
    publish_git_pull_event,
    publish_git_push_event,
)


class GitOpsWithEvents(GitOps):
    """
    GitOps wrapper that publishes events after git operations
    
    This class extends GitOps to add automatic event publishing for:
    - commits
    - pulls
    - pushes
    
    Events trigger automatic reindexing and other post-commit actions.
    """

    def __init__(
        self,
        repo_path: Path,
        user_id: Optional[int] = None,
        enabled: bool = True,
        auto_push: bool = True,
        remote: str = "origin",
        branch: str = "main",
        credentials_manager: Optional["CredentialsManager"] = None,
    ):
        """
        Initialize GitOps with event publishing
        
        Args:
            repo_path: Path to repository
            user_id: User ID for event tracking
            enabled: Enable git operations
            auto_push: Auto-push after commit
            remote: Remote name
            branch: Branch name
            credentials_manager: Optional credentials manager
        """
        super().__init__(
            repo_path=repo_path,
            enabled=enabled,
            auto_push=auto_push,
            remote=remote,
            branch=branch,
            credentials_manager=credentials_manager,
        )
        self.user_id = user_id

    def commit(self, message: str) -> bool:
        """
        Commit staged changes and publish event
        
        AICODE-NOTE: This is the key integration point!
        After commit succeeds, KB_GIT_COMMIT event is published,
        triggering automatic reindexing and other post-commit actions.

        Args:
            message: Commit message

        Returns:
            True if successful, False otherwise
        """
        # Call parent commit
        success = super().commit(message)
        
        if success:
            # Publish commit event
            publish_git_commit_event(
                commit_message=message,
                repo_path=self.repo_path,
                user_id=self.user_id,
                source="git_ops_with_events",
            )
            logger.debug(f"[GitOpsWithEvents] Published commit event for: {message[:50]}...")
        
        return success

    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> tuple[bool, str]:
        """
        Pull latest changes and publish event

        Args:
            remote: Remote name
            branch: Branch name

        Returns:
            Tuple of (success, message)
        """
        # Call parent pull
        success, msg = super().pull(remote, branch)
        
        if success:
            # Publish pull event
            branch_name = branch or self.branch
            publish_git_pull_event(
                remote=remote,
                branch=branch_name,
                repo_path=self.repo_path,
                user_id=self.user_id,
                source="git_ops_with_events",
            )
            logger.debug(f"[GitOpsWithEvents] Published pull event from {remote}/{branch_name}")
        
        return success, msg

    def push(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """
        Push commits and publish event

        Args:
            remote: Remote name
            branch: Branch name

        Returns:
            True if successful, False otherwise
        """
        # Call parent push
        success = super().push(remote, branch)
        
        if success:
            # Publish push event
            branch_name = branch or self.branch
            publish_git_push_event(
                remote=remote,
                branch=branch_name,
                repo_path=self.repo_path,
                user_id=self.user_id,
                source="git_ops_with_events",
            )
            logger.debug(f"[GitOpsWithEvents] Published push event to {remote}/{branch_name}")
        
        return success

    def auto_commit_and_push(
        self,
        message: str = "Auto-commit: Update knowledge base",
        remote: str = "origin",
        branch: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Auto-commit all changes and push
        
        AICODE-NOTE: This is the MAIN integration point for Qwen CLI and other agents!
        This method is called after agent finishes working on KB.
        Events published here trigger automatic reindexing of all changes.

        Args:
            message: Commit message
            remote: Remote name
            branch: Branch name

        Returns:
            Tuple of (success, message)
        """
        # Call parent method
        # It internally calls commit() and push() which will publish events
        return super().auto_commit_and_push(message, remote, branch)


def create_git_ops_for_user(
    repo_path: Path,
    user_id: Optional[int] = None,
    with_events: bool = True,
    **kwargs,
) -> GitOps:
    """
    Factory function to create GitOps instance
    
    Args:
        repo_path: Path to repository
        user_id: User ID for event tracking
        with_events: If True, returns GitOpsWithEvents (default)
        **kwargs: Additional GitOps arguments
    
    Returns:
        GitOps or GitOpsWithEvents instance
    """
    if with_events:
        return GitOpsWithEvents(repo_path=repo_path, user_id=user_id, **kwargs)
    else:
        return GitOps(repo_path=repo_path, **kwargs)
