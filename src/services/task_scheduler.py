"""
Task Scheduler
Schedules and executes scheduled agent tasks
"""

import asyncio
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Dict, List, Optional

from croniter import croniter
from loguru import logger

from src.services.scheduled_task import ScheduledTask
from src.services.scheduled_task_service import ScheduledTaskService


class TaskScheduler:
    """
    Scheduler for executing scheduled agent tasks

    Responsibilities:
    - Schedule tasks based on cron expressions or intervals
    - Execute tasks at scheduled times
    - Update task execution timestamps
    - Integrate with agent execution
    """

    def __init__(
        self,
        task_service: ScheduledTaskService,
        execution_callback: Optional[Callable[[ScheduledTask], Awaitable[bool]]] = None,
    ):
        """
        Initialize task scheduler

        Args:
            task_service: Scheduled task service for CRUD operations
            execution_callback: Callback function to execute tasks
                Signature: async def execute_task(task: ScheduledTask) -> bool
        """
        self.task_service = task_service
        self.execution_callback = execution_callback
        self.logger = logger.bind(service="TaskScheduler")
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._execution_tasks: Dict[str, asyncio.Task] = {}

    def start(self) -> None:
        """Start the scheduler"""
        if self._running:
            self.logger.warning("Scheduler is already running")
            return

        self._running = True
        loop = asyncio.get_event_loop()
        self._scheduler_task = loop.create_task(self._scheduler_loop())
        self.logger.info("Task scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler"""
        if not self._running:
            return

        self._running = False

        # Cancel scheduler task
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # Cancel all execution tasks
        for task_id, exec_task in self._execution_tasks.items():
            if not exec_task.done():
                exec_task.cancel()
                try:
                    await exec_task
                except asyncio.CancelledError:
                    pass

        self._execution_tasks.clear()
        self.logger.info("Task scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop - checks for tasks to execute"""
        while self._running:
            try:
                await self._check_and_schedule_tasks()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def _check_and_schedule_tasks(self) -> None:
        """Check for tasks that need to be executed and schedule them"""
        now = datetime.now()
        tasks = self.task_service.get_all_tasks(enabled_only=True)

        for task in tasks:
            # Skip if already executing
            if task.task_id in self._execution_tasks:
                exec_task = self._execution_tasks[task.task_id]
                if not exec_task.done():
                    continue

            # Calculate next run time (or use existing if set)
            if task.next_run is None:
                # First time calculating next_run for this task
                next_run = self._calculate_next_run(task, now)
                if next_run is None:
                    self.logger.warning(f"Could not calculate next_run for task {task.task_id}")
                    continue
                # Save calculated next_run
                task.next_run = next_run
                self.task_service.update_task(task)
                self.logger.debug(
                    f"Calculated next_run for task {task.task_id}: {next_run.isoformat()}"
                )
            else:
                next_run = task.next_run

            # Check if it's time to run
            if next_run <= now:
                # Schedule execution
                self.logger.info(
                    f"Scheduling task {task.task_id} for execution (next_run was {next_run.isoformat()})"
                )
                loop = asyncio.get_event_loop()
                exec_task = loop.create_task(self._execute_task(task))
                self._execution_tasks[task.task_id] = exec_task

                # Calculate and update next_run for future execution
                new_next_run = self._calculate_next_run(task, now)
                if new_next_run:
                    task.next_run = new_next_run
                    self.task_service.update_task(task)
                    self.logger.debug(
                        f"Updated next_run for task {task.task_id}: {new_next_run.isoformat()}"
                    )

    def _calculate_next_run(self, task: ScheduledTask, now: datetime) -> Optional[datetime]:
        """
        Calculate next run time for a task

        Args:
            task: Scheduled task
            now: Current datetime

        Returns:
            Next run datetime or None if schedule is invalid
        """
        try:
            # Check if schedule is a cron expression or interval
            if self._is_cron_expression(task.schedule):
                # Cron expression
                cron = croniter(task.schedule, now)
                next_run = cron.get_next(datetime)
                return next_run
            else:
                # Interval in seconds
                try:
                    interval_seconds = int(task.schedule)
                    if task.last_run:
                        next_run = task.last_run + timedelta(seconds=interval_seconds)
                    else:
                        next_run = now + timedelta(seconds=interval_seconds)

                    # If next_run is in the past, schedule for now
                    if next_run < now:
                        next_run = now

                    return next_run
                except ValueError:
                    self.logger.error(f"Invalid interval format: {task.schedule}")
                    return None

        except Exception as e:
            self.logger.error(f"Failed to calculate next run for task {task.task_id}: {e}")
            return None

    def _is_cron_expression(self, schedule: str) -> bool:
        """
        Check if schedule is a cron expression

        Args:
            schedule: Schedule string

        Returns:
            True if cron expression, False if interval
        """
        # Simple heuristic: cron expressions have spaces or special chars
        # Intervals are just numbers
        try:
            int(schedule)
            return False
        except ValueError:
            return True

    async def _execute_task(self, task: ScheduledTask) -> None:
        """
        Execute a scheduled task

        Args:
            task: Task to execute
        """
        import time

        start_time = time.time()
        self.logger.info(
            f"[TASK_SCHEDULER] Starting execution of scheduled task: {task.task_id} for user {task.user_id}"
        )

        try:
            if self.execution_callback:
                success = await self.execution_callback(task)
                execution_time = time.time() - start_time
                self.logger.info(
                    f"[TASK_SCHEDULER] Task {task.task_id} execution finished (success={success}) in {execution_time:.2f}s"
                )
                self.task_service.mark_task_run(task.task_id, success=success)
            else:
                self.logger.warning(f"No execution callback set for task {task.task_id}")
                self.task_service.mark_task_run(task.task_id, success=False)

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                f"[TASK_SCHEDULER] Error executing task {task.task_id} after {execution_time:.2f}s: {e}",
                exc_info=True,
            )
            self.task_service.mark_task_run(task.task_id, success=False)

        finally:
            # Remove from execution tasks when done
            if task.task_id in self._execution_tasks:
                del self._execution_tasks[task.task_id]
                self.logger.debug(
                    f"[TASK_SCHEDULER] Removed task {task.task_id} from execution tasks"
                )

    def get_next_run_times(self) -> Dict[str, Optional[datetime]]:
        """
        Get next run times for all enabled tasks

        Returns:
            Dictionary mapping task_id to next_run datetime
        """
        now = datetime.now()
        tasks = self.task_service.get_all_tasks(enabled_only=True)
        return {task.task_id: self._calculate_next_run(task, now) for task in tasks}
