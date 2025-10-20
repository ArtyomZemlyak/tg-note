"""
Event System for Application-wide Events

Provides a lightweight event bus for decoupled communication between components.
Follows Observer pattern and SOLID principles.

AICODE-NOTE: This event system allows components to communicate without tight coupling.
Components can publish events without knowing who will handle them.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from loguru import logger


class EventType(Enum):
    """Types of events in the system"""

    # Knowledge Base events
    KB_FILE_CREATED = "kb.file.created"
    KB_FILE_MODIFIED = "kb.file.modified"
    KB_FILE_DELETED = "kb.file.deleted"
    KB_FOLDER_CREATED = "kb.folder.created"
    KB_FOLDER_DELETED = "kb.folder.deleted"
    KB_BATCH_CHANGES = "kb.batch.changes"  # Multiple changes at once

    # Git events
    KB_GIT_COMMIT = "kb.git.commit"
    KB_GIT_PUSH = "kb.git.push"
    KB_GIT_PULL = "kb.git.pull"

    # Agent events (for future use)
    AGENT_TASK_STARTED = "agent.task.started"
    AGENT_TASK_COMPLETED = "agent.task.completed"


@dataclass
class Event:
    """Base event class"""

    type: EventType
    data: Dict[str, Any]
    source: Optional[str] = None  # Component that emitted the event

    def __repr__(self) -> str:
        return f"Event({self.type.value}, source={self.source})"


@dataclass
class KBChangeEvent(Event):
    """Knowledge Base change event"""

    def __init__(
        self,
        event_type: EventType,
        file_path: Optional[Path] = None,
        files: Optional[List[Path]] = None,
        user_id: Optional[int] = None,
        source: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize KB change event

        Args:
            event_type: Type of event
            file_path: Path to changed file (for single file changes)
            files: List of changed files (for batch changes)
            user_id: User who made the change
            source: Component that emitted the event
            **kwargs: Additional event data
        """
        data = {
            "file_path": str(file_path) if file_path else None,
            "files": [str(f) for f in files] if files else None,
            "user_id": user_id,
            **kwargs,
        }
        super().__init__(type=event_type, data=data, source=source)

    @property
    def file_path(self) -> Optional[Path]:
        """Get file path from event data"""
        if self.data.get("file_path"):
            return Path(self.data["file_path"])
        return None

    @property
    def files(self) -> List[Path]:
        """Get list of files from event data"""
        if self.data.get("files"):
            return [Path(f) for f in self.data["files"]]
        return []

    @property
    def user_id(self) -> Optional[int]:
        """Get user ID from event data"""
        return self.data.get("user_id")


# Type alias for event handler
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], asyncio.Task]


class EventBus:
    """
    Lightweight Event Bus for decoupled communication

    Allows components to publish and subscribe to events without knowing about each other.
    Follows Observer pattern and SOLID principles.
    """

    def __init__(self):
        """Initialize event bus"""
        self._sync_handlers: Dict[EventType, List[EventHandler]] = {}
        self._async_handlers: Dict[EventType, List[AsyncEventHandler]] = {}
        self._wildcard_sync_handlers: List[EventHandler] = []  # Handle all events
        self._wildcard_async_handlers: List[AsyncEventHandler] = []

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Subscribe to specific event type (synchronous handler)

        Args:
            event_type: Type of event to subscribe to
            handler: Handler function to call when event is published
        """
        if event_type not in self._sync_handlers:
            self._sync_handlers[event_type] = []

        self._sync_handlers[event_type].append(handler)
        logger.debug(f"[EventBus] Subscribed sync handler to {event_type.value}")

    def subscribe_async(self, event_type: EventType, handler: AsyncEventHandler) -> None:
        """
        Subscribe to specific event type (asynchronous handler)

        Args:
            event_type: Type of event to subscribe to
            handler: Async handler function to call when event is published
        """
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []

        self._async_handlers[event_type].append(handler)
        logger.debug(f"[EventBus] Subscribed async handler to {event_type.value}")

    def subscribe_all(self, handler: EventHandler) -> None:
        """
        Subscribe to all events (wildcard subscription)

        Args:
            handler: Handler function to call for any event
        """
        self._wildcard_sync_handlers.append(handler)
        logger.debug("[EventBus] Subscribed wildcard sync handler")

    def subscribe_all_async(self, handler: AsyncEventHandler) -> None:
        """
        Subscribe to all events (wildcard subscription, async)

        Args:
            handler: Async handler function to call for any event
        """
        self._wildcard_async_handlers.append(handler)
        logger.debug("[EventBus] Subscribed wildcard async handler")

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Unsubscribe from event type

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to remove
        """
        if event_type in self._sync_handlers:
            try:
                self._sync_handlers[event_type].remove(handler)
                logger.debug(f"[EventBus] Unsubscribed sync handler from {event_type.value}")
            except ValueError:
                pass

    def unsubscribe_async(self, event_type: EventType, handler: AsyncEventHandler) -> None:
        """
        Unsubscribe async handler from event type

        Args:
            event_type: Event type to unsubscribe from
            handler: Async handler to remove
        """
        if event_type in self._async_handlers:
            try:
                self._async_handlers[event_type].remove(handler)
                logger.debug(f"[EventBus] Unsubscribed async handler from {event_type.value}")
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        """
        Publish event to all subscribers (synchronous)

        Args:
            event: Event to publish
        """
        logger.debug(f"[EventBus] Publishing {event}")

        # Call specific handlers
        handlers = self._sync_handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    f"[EventBus] Error in sync handler for {event.type.value}: {e}",
                    exc_info=True,
                )

        # Call wildcard handlers
        for handler in self._wildcard_sync_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"[EventBus] Error in wildcard sync handler: {e}", exc_info=True)

    async def publish_async(self, event: Event) -> None:
        """
        Publish event to all subscribers (asynchronous)

        Args:
            event: Event to publish
        """
        logger.debug(f"[EventBus] Publishing async {event}")

        # Call specific async handlers
        handlers = self._async_handlers.get(event.type, [])
        tasks = []

        for handler in handlers:
            try:
                task = asyncio.create_task(handler(event))
                tasks.append(task)
            except Exception as e:
                logger.error(
                    f"[EventBus] Error creating async handler task for {event.type.value}: {e}",
                    exc_info=True,
                )

        # Call wildcard async handlers
        for handler in self._wildcard_async_handlers:
            try:
                task = asyncio.create_task(handler(event))
                tasks.append(task)
            except Exception as e:
                logger.error(
                    f"[EventBus] Error creating wildcard async handler task: {e}", exc_info=True
                )

        # Wait for all async handlers to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"[EventBus] Async handler {i} failed: {result}", exc_info=result
                    )

    def get_subscriber_count(self, event_type: Optional[EventType] = None) -> int:
        """
        Get number of subscribers for event type

        Args:
            event_type: Event type to check (None for all subscribers)

        Returns:
            Number of subscribers
        """
        if event_type is None:
            # Count all subscribers
            total = (
                sum(len(handlers) for handlers in self._sync_handlers.values())
                + sum(len(handlers) for handlers in self._async_handlers.values())
                + len(self._wildcard_sync_handlers)
                + len(self._wildcard_async_handlers)
            )
            return total
        else:
            return len(self._sync_handlers.get(event_type, [])) + len(
                self._async_handlers.get(event_type, [])
            )


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Get global event bus instance

    Returns:
        Global EventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        logger.debug("[EventBus] Created global event bus")
    return _event_bus


def reset_event_bus() -> None:
    """Reset global event bus (for testing)"""
    global _event_bus
    _event_bus = None
    logger.debug("[EventBus] Reset global event bus")
