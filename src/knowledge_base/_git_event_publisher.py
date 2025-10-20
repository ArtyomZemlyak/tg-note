"""
Git Event Publisher Utility

Helper for publishing git-related events from GitOps.
Keeps GitOps clean and decoupled from event system.

AICODE-NOTE: This utility allows GitOps to publish events while maintaining
low coupling. GitOps can still work even if event system is not available.
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from src.core.events import EventType, KBChangeEvent, get_event_bus


def publish_git_commit_event(
    commit_message: str,
    repo_path: Path,
    user_id: Optional[int] = None,
    source: str = "git_ops",
) -> None:
    """
    Publish git commit event
    
    AICODE-NOTE: This is the MAIN trigger point for post-commit actions!
    After a commit succeeds, this event notifies all subscribers (e.g., vector search)
    that changes are finalized and ready for processing.

    Args:
        commit_message: Git commit message
        repo_path: Path to repository
        user_id: Optional user ID
        source: Source component name
    """
    try:
        event = KBChangeEvent(
            event_type=EventType.KB_GIT_COMMIT,
            user_id=user_id,
            source=source,
            commit_message=commit_message,
            repo_path=str(repo_path),
        )
        get_event_bus().publish(event)
        logger.debug(f"[GitEventPublisher] Published KB_GIT_COMMIT: {commit_message[:50]}...")
    except Exception as e:
        # Don't fail git operations if event publishing fails
        logger.warning(f"[GitEventPublisher] Failed to publish commit event: {e}")


def publish_git_pull_event(
    remote: str,
    branch: str,
    repo_path: Path,
    user_id: Optional[int] = None,
    source: str = "git_ops",
) -> None:
    """
    Publish git pull event

    Args:
        remote: Remote name
        branch: Branch name
        repo_path: Path to repository
        user_id: Optional user ID
        source: Source component name
    """
    try:
        event = KBChangeEvent(
            event_type=EventType.KB_GIT_PULL,
            user_id=user_id,
            source=source,
            remote=remote,
            branch=branch,
            repo_path=str(repo_path),
        )
        get_event_bus().publish(event)
        logger.debug(f"[GitEventPublisher] Published KB_GIT_PULL from {remote}/{branch}")
    except Exception as e:
        logger.warning(f"[GitEventPublisher] Failed to publish pull event: {e}")


def publish_git_push_event(
    remote: str,
    branch: str,
    repo_path: Path,
    user_id: Optional[int] = None,
    source: str = "git_ops",
) -> None:
    """
    Publish git push event

    Args:
        remote: Remote name
        branch: Branch name
        repo_path: Path to repository
        user_id: Optional user ID
        source: Source component name
    """
    try:
        event = KBChangeEvent(
            event_type=EventType.KB_GIT_PUSH,
            user_id=user_id,
            source=source,
            remote=remote,
            branch=branch,
            repo_path=str(repo_path),
        )
        get_event_bus().publish(event)
        logger.debug(f"[GitEventPublisher] Published KB_GIT_PUSH to {remote}/{branch}")
    except Exception as e:
        logger.warning(f"[GitEventPublisher] Failed to publish push event: {e}")
