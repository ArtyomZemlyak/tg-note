"""
Scheduled Task Model
Data model for scheduled agent tasks
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class ScheduledTask:
    """
    Model for a scheduled agent task

    Attributes:
        task_id: Unique identifier for the task
        user_id: User ID who owns the task
        kb_name: Knowledge base name to run task on
        schedule: Cron expression or interval (e.g., "0 9 * * *" for daily at 9 AM, or "3600" for every hour)
        prompt_path: Path to prompt file (promptic format) or None
        prompt_text: Direct prompt text or None
        enabled: Whether task is enabled
        last_run: Last execution timestamp
        next_run: Next scheduled execution timestamp
        created_at: Task creation timestamp
        updated_at: Last update timestamp
        chat_id: Telegram chat ID for notifications
    """

    task_id: str
    user_id: int
    kb_name: str
    schedule: str  # Cron expression or interval in seconds
    prompt_path: Optional[str] = None  # Path to promptic prompt file
    prompt_text: Optional[str] = None  # Direct prompt text
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    chat_id: Optional[int] = None  # Telegram chat ID for notifications

    def to_dict(self) -> dict:
        """Convert task to dictionary for storage"""
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "kb_name": self.kb_name,
            "schedule": self.schedule,
            "prompt_path": self.prompt_path,
            "prompt_text": self.prompt_text,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "chat_id": self.chat_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledTask":
        """Create task from dictionary"""
        from datetime import datetime

        return cls(
            task_id=data["task_id"],
            user_id=data["user_id"],
            kb_name=data["kb_name"],
            schedule=data["schedule"],
            prompt_path=data.get("prompt_path"),
            prompt_text=data.get("prompt_text"),
            enabled=data.get("enabled", True),
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            next_run=datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None,
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            chat_id=data.get("chat_id"),
        )

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate task configuration

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.task_id:
            return False, "Task ID is required"

        if not self.kb_name:
            return False, "Knowledge base name is required"

        if not self.schedule:
            return False, "Schedule is required"

        if not self.prompt_path and not self.prompt_text:
            return False, "Either prompt_path or prompt_text must be provided"

        if self.prompt_path and self.prompt_text:
            return False, "Cannot specify both prompt_path and prompt_text"

        return True, None
