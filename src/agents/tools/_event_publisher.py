"""
Event Publisher Utility for Agent Tools

Helper for publishing KB change events from agent tools.
Provides a simple interface to publish events without tight coupling.

AICODE-NOTE: This utility allows tools to publish events while maintaining
low coupling with the event system. Tools can still work even if event
system is not available.
"""

from pathlib import Path
from typing import List, Optional

from loguru import logger

from src.core.events import EventType, KBChangeEvent, get_event_bus


def publish_kb_file_event(
    event_type: EventType,
    file_path: Path,
    user_id: Optional[int] = None,
    source: str = "agent_tool",
) -> None:
    """
    Publish a single file change event

    Args:
        event_type: Type of event (KB_FILE_CREATED, KB_FILE_MODIFIED, KB_FILE_DELETED)
        file_path: Path to the changed file
        user_id: Optional user ID
        source: Source component name
    """
    try:
        event = KBChangeEvent(
            event_type=event_type, file_path=file_path, user_id=user_id, source=source
        )
        get_event_bus().publish(event)
        logger.debug(f"[EventPublisher] Published {event_type.value} for {file_path.name}")
    except Exception as e:
        # Don't fail tool execution if event publishing fails
        logger.warning(f"[EventPublisher] Failed to publish event: {e}")


def publish_kb_batch_event(
    files: List[Path], user_id: Optional[int] = None, source: str = "agent_tool"
) -> None:
    """
    Publish a batch change event for multiple files

    Args:
        files: List of changed files
        user_id: Optional user ID
        source: Source component name
    """
    try:
        event = KBChangeEvent(
            event_type=EventType.KB_BATCH_CHANGES, files=files, user_id=user_id, source=source
        )
        get_event_bus().publish(event)
        logger.debug(f"[EventPublisher] Published batch event for {len(files)} files")
    except Exception as e:
        logger.warning(f"[EventPublisher] Failed to publish batch event: {e}")


def publish_kb_git_event(
    event_type: EventType, user_id: Optional[int] = None, source: str = "git_tool", **kwargs
) -> None:
    """
    Publish a git-related event

    Args:
        event_type: Type of git event (KB_GIT_COMMIT, KB_GIT_PUSH, KB_GIT_PULL)
        user_id: Optional user ID
        source: Source component name
        **kwargs: Additional event data
    """
    try:
        event = KBChangeEvent(event_type=event_type, user_id=user_id, source=source, **kwargs)
        get_event_bus().publish(event)
        logger.debug(f"[EventPublisher] Published {event_type.value}")
    except Exception as e:
        logger.warning(f"[EventPublisher] Failed to publish git event: {e}")
