"""
Scheduled Task Service
Manages scheduled agent tasks (CRUD operations and execution)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from filelock import FileLock
from loguru import logger

from src.services.scheduled_task import ScheduledTask


class ScheduledTaskService:
    """
    Service for managing scheduled agent tasks

    Responsibilities:
    - CRUD operations for scheduled tasks
    - Task storage (JSON file)
    - Task validation
    - Loading tasks from config
    """

    def __init__(self, storage_file: Optional[Path] = None):
        """
        Initialize scheduled task service

        Args:
            storage_file: Path to JSON file for task storage (default: data/scheduled_tasks.json)
        """
        if storage_file is None:
            storage_file = Path(__file__).parent.parent.parent / "data" / "scheduled_tasks.json"

        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file = Path(str(storage_file) + ".lock")
        self.logger = logger.bind(service="ScheduledTaskService")

        # Load tasks on init
        self._tasks: Dict[str, ScheduledTask] = {}
        self._load_tasks()

    def _load_tasks(self) -> None:
        """Load tasks from storage file"""
        if not self.storage_file.exists():
            self.logger.info(
                f"Storage file does not exist, starting with empty task list: {self.storage_file}"
            )
            return

        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._tasks = {}
            for task_data in data.get("tasks", []):
                try:
                    task = ScheduledTask.from_dict(task_data)
                    is_valid, error = task.validate()
                    if is_valid:
                        self._tasks[task.task_id] = task
                    else:
                        self.logger.warning(f"Skipping invalid task {task.task_id}: {error}")
                except Exception as e:
                    self.logger.error(f"Failed to load task: {e}", exc_info=True)

            self.logger.info(f"Loaded {len(self._tasks)} scheduled tasks from {self.storage_file}")

        except Exception as e:
            self.logger.error(f"Failed to load tasks from {self.storage_file}: {e}", exc_info=True)
            self._tasks = {}

    def _save_tasks(self) -> None:
        """Save tasks to storage file (with file lock)"""
        lock = FileLock(str(self.lock_file), timeout=10)
        try:
            with lock:
                data = {"tasks": [task.to_dict() for task in self._tasks.values()]}
                with open(self.storage_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                self.logger.debug(f"Saved {len(self._tasks)} tasks to {self.storage_file}")
        except Exception as e:
            self.logger.error(f"Failed to save tasks: {e}", exc_info=True)
            raise

    def create_task(self, task: ScheduledTask) -> bool:
        """
        Create a new scheduled task

        Args:
            task: Task to create

        Returns:
            True if created successfully, False otherwise
        """
        is_valid, error = task.validate()
        if not is_valid:
            self.logger.error(f"Cannot create invalid task: {error}")
            return False

        if task.task_id in self._tasks:
            self.logger.warning(f"Task {task.task_id} already exists, use update_task instead")
            return False

        task.created_at = datetime.now()
        task.updated_at = datetime.now()
        self._tasks[task.task_id] = task
        self._save_tasks()

        self.logger.info(f"Created scheduled task: {task.task_id} for user {task.user_id}")
        return True

    def update_task(self, task: ScheduledTask) -> bool:
        """
        Update an existing scheduled task

        Args:
            task: Task to update

        Returns:
            True if updated successfully, False otherwise
        """
        is_valid, error = task.validate()
        if not is_valid:
            self.logger.error(f"Cannot update invalid task: {error}")
            return False

        if task.task_id not in self._tasks:
            self.logger.warning(f"Task {task.task_id} does not exist, use create_task instead")
            return False

        task.updated_at = datetime.now()
        self._tasks[task.task_id] = task
        self._save_tasks()

        self.logger.info(f"Updated scheduled task: {task.task_id}")
        return True

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a scheduled task

        Args:
            task_id: Task ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        if task_id not in self._tasks:
            self.logger.warning(f"Task {task_id} does not exist")
            return False

        del self._tasks[task_id]
        self._save_tasks()

        self.logger.info(f"Deleted scheduled task: {task_id}")
        return True

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """
        Get a task by ID

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        return self._tasks.get(task_id)

    def get_tasks_for_user(self, user_id: int) -> List[ScheduledTask]:
        """
        Get all tasks for a user

        Args:
            user_id: User ID

        Returns:
            List of tasks for the user
        """
        return [task for task in self._tasks.values() if task.user_id == user_id]

    def get_all_tasks(self, enabled_only: bool = False) -> List[ScheduledTask]:
        """
        Get all tasks

        Args:
            enabled_only: If True, return only enabled tasks

        Returns:
            List of all tasks
        """
        tasks = list(self._tasks.values())
        if enabled_only:
            tasks = [task for task in tasks if task.enabled]
        return tasks

    def get_tasks_for_kb(self, kb_name: str, enabled_only: bool = True) -> List[ScheduledTask]:
        """
        Get all tasks for a knowledge base

        Args:
            kb_name: Knowledge base name
            enabled_only: If True, return only enabled tasks

        Returns:
            List of tasks for the KB
        """
        tasks = [task for task in self._tasks.values() if task.kb_name == kb_name]
        if enabled_only:
            tasks = [task for task in tasks if task.enabled]
        return tasks

    def mark_task_run(self, task_id: str, success: bool = True) -> None:
        """
        Mark a task as executed

        Args:
            task_id: Task ID
            success: Whether execution was successful
        """
        if task_id not in self._tasks:
            return

        task = self._tasks[task_id]
        task.last_run = datetime.now()
        task.updated_at = datetime.now()
        self._save_tasks()

        self.logger.debug(f"Marked task {task_id} as run (success={success})")

    def load_tasks_from_config(self, config: dict) -> None:
        """
        Load tasks from configuration (config.yaml)

        AICODE-NOTE: Before loading, removes all existing tasks that were loaded from config
        (identified by task_id starting with "config_") to prevent duplicates on restart.

        Args:
            config: Configuration dictionary with SCHEDULED_TASKS key
        """
        scheduled_tasks = config.get("SCHEDULED_TASKS", [])
        if not scheduled_tasks:
            self.logger.debug("No scheduled tasks in config")
            # Remove all config tasks if config is empty
            self._remove_config_tasks()
            return

        # Remove all existing tasks that were loaded from config (to prevent duplicates on restart)
        self._remove_config_tasks()

        for index, task_config in enumerate(scheduled_tasks):
            try:
                # Generate task_id from config if not provided
                task_id = task_config.get("task_id")
                if not task_id:
                    # Generate from user_id and kb_name with index to ensure uniqueness
                    user_id = task_config.get("user_id", 0)
                    kb_name = task_config.get("kb_name", "default")
                    task_id = f"config_{user_id}_{kb_name}_{index}"

                # Check if task already exists (skip if exists)
                if task_id in self._tasks:
                    self.logger.debug(f"Task {task_id} already exists, skipping config load")
                    continue

                task = ScheduledTask(
                    task_id=task_id,
                    user_id=task_config.get("user_id", 0),
                    kb_name=task_config["kb_name"],
                    schedule=task_config["schedule"],
                    prompt_path=task_config.get("prompt_path"),
                    prompt_text=task_config.get("prompt_text"),
                    enabled=task_config.get("enabled", True),
                    chat_id=task_config.get("chat_id"),
                )

                is_valid, error = task.validate()
                if is_valid:
                    self.create_task(task)
                    self.logger.info(f"Loaded task from config: {task_id}")
                else:
                    self.logger.warning(f"Skipping invalid task from config {task_id}: {error}")

            except Exception as e:
                self.logger.error(f"Failed to load task from config: {e}", exc_info=True)

    def _remove_config_tasks(self) -> None:
        """
        Remove all tasks that were loaded from config (identified by task_id starting with "config_")

        AICODE-NOTE: This prevents duplicate tasks when bot is restarted and config is reloaded.
        """
        config_task_ids = [
            task_id for task_id in self._tasks.keys() if task_id.startswith("config_")
        ]
        if config_task_ids:
            self.logger.info(
                f"Removing {len(config_task_ids)} existing config tasks before reload: {config_task_ids}"
            )
            for task_id in config_task_ids:
                del self._tasks[task_id]
            self._save_tasks()
