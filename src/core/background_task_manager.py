"""
Background Task Manager
Централизованный менеджер для управления жизненным циклом фоновых задач
"""

import asyncio
from typing import Any, Callable, Dict, Optional

from loguru import logger


class BackgroundTaskManager:
    """
    Централизованный менеджер жизненного цикла фоновых задач.

    Управляет запуском и остановкой всех фоновых задач (например, MessageAggregator),
    обеспечивая единую точку контроля и прозрачность.
    """

    def __init__(self):
        """Инициализация менеджера фоновых задач"""
        self.logger = logger
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._task_metadata: Dict[str, Dict[str, Any]] = {}
        self.logger.info("BackgroundTaskManager initialized")

    def is_running(self) -> bool:
        """Проверить, запущен ли менеджер"""
        return self._running

    def start(self) -> None:
        """Запустить менеджер фоновых задач"""
        if self._running:
            self.logger.warning("BackgroundTaskManager is already running")
            return

        self._running = True
        self.logger.info("BackgroundTaskManager started")

    async def stop(self) -> None:
        """Остановить менеджер и все задачи"""
        if not self._running:
            self.logger.info("BackgroundTaskManager is already stopped")
            return

        self.logger.info("Stopping BackgroundTaskManager...")
        self._running = False

        # Отменить все задачи
        tasks = list(self._tasks.values())
        for task_id, task in list(self._tasks.items()):
            if not task.done():
                self.logger.debug(f"Cancelling task: {task_id}")
                task.cancel()

        # Дождаться завершения всех задач
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._tasks.clear()
        self._task_metadata.clear()
        self.logger.info("BackgroundTaskManager stopped")

    def register_task(
        self, task_id: str, coroutine: Callable, description: str = "", **metadata
    ) -> None:
        """
        Зарегистрировать и запустить фоновую задачу

        Args:
            task_id: Уникальный идентификатор задачи
            coroutine: Корутина для выполнения
            description: Описание задачи
            **metadata: Дополнительные метаданные
        """
        if not self._running:
            self.logger.warning(f"Cannot register task {task_id}: manager not running")
            return

        if task_id in self._tasks:
            self.logger.warning(f"Task {task_id} is already registered")
            return

        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(coroutine())
            task.add_done_callback(lambda t: self._on_task_done(task_id, t))

            self._tasks[task_id] = task
            self._task_metadata[task_id] = {
                "description": description,
                "started_at": asyncio.get_event_loop().time(),
                **metadata,
            }

            self.logger.info(f"Registered task: {task_id} - {description}")

        except RuntimeError as e:
            self.logger.error(f"Failed to register task {task_id}: {e}")

    async def unregister_task(self, task_id: str) -> None:
        """
        Отменить регистрацию и остановить задачу

        Args:
            task_id: Идентификатор задачи
        """
        if task_id not in self._tasks:
            self.logger.debug(f"Task {task_id} is not registered")
            return

        task = self._tasks[task_id]

        if not task.done():
            self.logger.debug(f"Cancelling task: {task_id}")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        del self._tasks[task_id]
        if task_id in self._task_metadata:
            del self._task_metadata[task_id]

        self.logger.info(f"Unregistered task: {task_id}")

    def _on_task_done(self, task_id: str, task: asyncio.Task) -> None:
        """
        Обработчик завершения задачи

        Args:
            task_id: Идентификатор задачи
            task: Завершенная задача
        """
        try:
            exception = task.exception()
            if exception is not None:
                self.logger.error(
                    f"Task {task_id} failed with exception: {exception}", exc_info=exception
                )
        except asyncio.CancelledError:
            self.logger.debug(f"Task {task_id} was cancelled")
        except Exception as e:
            self.logger.error(f"Error retrieving task exception: {e}", exc_info=True)
        finally:
            # Очистить задачу из реестра
            if task_id in self._tasks:
                del self._tasks[task_id]
            if task_id in self._task_metadata:
                del self._task_metadata[task_id]

    def get_task_status(self, task_id: str) -> Optional[str]:
        """
        Получить статус задачи

        Args:
            task_id: Идентификатор задачи

        Returns:
            Статус задачи или None если задача не найдена
        """
        if task_id not in self._tasks:
            return None

        task = self._tasks[task_id]
        if task.done():
            return "done"
        elif task.cancelled():
            return "cancelled"
        else:
            return "running"

    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Получить список всех задач с метаданными

        Returns:
            Словарь {task_id: metadata}
        """
        result = {}
        for task_id, metadata in self._task_metadata.items():
            status = self.get_task_status(task_id)
            result[task_id] = {**metadata, "status": status}
        return result
