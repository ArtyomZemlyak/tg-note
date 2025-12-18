"""
Progress Monitor - отслеживание прогресса выполнения задач агентом через чекбоксы

AICODE-NOTE: Этот модуль мониторит изменения в файлах промптов (data/prompts/)
где агент закрывает чекбоксы во время работы, и обновляет telegram сообщения
с прогрессом выполнения.

Использует watchdog для асинхронного мониторинга файловой системы.
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


@dataclass
class CheckboxItem:
    """Элемент чекбокса из markdown файла"""

    text: str  # Текст задачи
    status: str  # "pending" | "completed"
    file: str  # Путь к файлу
    line_number: int  # Номер строки
    context: Optional[str] = None  # Контекст (родительский заголовок)


@dataclass
class ProgressSnapshot:
    """Снимок прогресса выполнения"""

    total: int  # Общее количество чекбоксов
    completed: int  # Количество выполненных
    percentage: float  # Процент выполнения
    current_task: Optional[str] = None  # Текущая задача (первый pending)
    checkboxes: List[CheckboxItem] = field(default_factory=list)  # Все чекбоксы

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            "total": self.total,
            "completed": self.completed,
            "percentage": self.percentage,
            "current_task": self.current_task,
            "checkboxes": [
                {
                    "text": cb.text,
                    "status": cb.status,
                    "file": cb.file,
                    "line_number": cb.line_number,
                    "context": cb.context,
                }
                for cb in self.checkboxes
            ],
        }


class PromptFileEventHandler(FileSystemEventHandler):
    """Обработчик событий изменения файлов промптов"""

    def __init__(self, callback: Callable[[Path], None]):
        """
        Инициализация обработчика

        Args:
            callback: Функция для вызова при изменении файла
        """
        super().__init__()
        self.callback = callback
        self.logger = logger.bind(handler="PromptFileEventHandler")

    def on_modified(self, event: FileSystemEvent):
        """Обработка события изменения файла"""
        if event.is_directory:
            return

        # Отслеживаем только .md файлы
        if not event.src_path.endswith(".md"):
            return

        self.logger.debug(f"File modified: {event.src_path}")
        self.callback(Path(event.src_path))


class ProgressMonitor:
    """
    Монитор прогресса выполнения задач агентом

    Отслеживает изменения в файлах промптов где агент закрывает чекбоксы,
    парсит их и вызывает callback для обновления UI (telegram сообщения).

    Features:
    - Асинхронный мониторинг файловой системы (watchdog)
    - Парсинг чекбоксов с контекстом (родительские заголовки)
    - Throttling обновлений (не чаще раз в N секунд)
    - Graceful error handling
    """

    def __init__(
        self,
        export_dir: Path,
        update_callback: Callable[[ProgressSnapshot], Any],
        throttle_interval: float = 2.0,
    ):
        """
        Инициализация монитора прогресса

        Args:
            export_dir: Директория с экспортированными промптами (data/prompts/*)
            update_callback: Async функция для обновления UI с прогрессом
            throttle_interval: Минимальный интервал между обновлениями (секунды)
        """
        self.export_dir = export_dir
        self.update_callback = update_callback
        self.throttle_interval = throttle_interval

        self.observer: Optional[Observer] = None
        self.is_monitoring = False
        self.last_update_time = 0.0
        self.current_snapshot: Optional[ProgressSnapshot] = None

        # Для debounce: накапливаем изменения и обрабатываем батчем
        self._pending_updates: List[Path] = []
        self._update_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self.logger = logger.bind(service="ProgressMonitor")

    async def start_monitoring(self) -> None:
        """
        Запустить мониторинг файлов

        Raises:
            RuntimeError: Если мониторинг уже запущен
        """
        if self.is_monitoring:
            raise RuntimeError("Monitoring already started")

        self.logger.info(f"Starting progress monitoring in: {self.export_dir}")

        # Сохраняем ссылку на текущий event loop
        self._loop = asyncio.get_running_loop()

        # Проверяем что директория существует
        if not self.export_dir.exists():
            self.logger.warning(
                f"Export directory does not exist yet: {self.export_dir}. "
                f"Will monitor after it's created."
            )
            self.export_dir.mkdir(parents=True, exist_ok=True)

        # Создаем observer и event handler
        event_handler = PromptFileEventHandler(callback=self._on_file_changed)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.export_dir), recursive=True)
        self.observer.start()

        self.is_monitoring = True

        # Делаем первоначальный парсинг для установки baseline
        await self._parse_and_update()

        self.logger.info("Progress monitoring started successfully")

    async def stop_monitoring(self) -> None:
        """Остановить мониторинг файлов"""
        if not self.is_monitoring:
            return

        self.logger.info("Stopping progress monitoring...")

        # Останавливаем observer
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5.0)
            self.observer = None

        # Отменяем pending task если есть
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        self.is_monitoring = False
        self.logger.info("Progress monitoring stopped")

    def _on_file_changed(self, file_path: Path) -> None:
        """
        Callback для watchdog при изменении файла

        AICODE-NOTE: Этот метод вызывается из отдельного потока watchdog,
        поэтому используем run_coroutine_threadsafe для запуска в основном event loop.

        Args:
            file_path: Путь к измененному файлу
        """
        # Добавляем в очередь и планируем обновление с debounce
        self._pending_updates.append(file_path)

        # Создаем task для обработки если его еще нет
        if self._loop and (self._update_task is None or self._update_task.done()):
            # Используем run_coroutine_threadsafe для запуска из другого потока
            future = asyncio.run_coroutine_threadsafe(self._debounced_update(), self._loop)
            # Оборачиваем Future в Task для совместимости
            # (не обязательно, но сохраняет совместимость с существующим кодом)
            try:
                self._update_task = asyncio.wrap_future(future, loop=self._loop)
            except Exception as e:
                self.logger.error(f"Failed to schedule debounced update: {e}")

    async def _debounced_update(self) -> None:
        """
        Обработка изменений с debounce

        Ждет короткий интервал чтобы собрать batch изменений,
        затем парсит и обновляет прогресс.
        """
        # Ждем немного чтобы собрать batch изменений
        await asyncio.sleep(0.5)

        async with self._lock:
            if not self._pending_updates:
                return

            # Очищаем очередь
            changed_files = list(set(self._pending_updates))
            self._pending_updates.clear()

            self.logger.debug(f"Processing {len(changed_files)} changed file(s)")

            # Парсим и обновляем с throttling
            await self._parse_and_update()

    async def _parse_and_update(self) -> None:
        """
        Парсинг чекбоксов и обновление прогресса

        С throttling: не обновляет чаще чем throttle_interval.
        """
        try:
            # Проверяем throttling
            current_time = time.time()
            time_since_last_update = current_time - self.last_update_time

            if time_since_last_update < self.throttle_interval:
                self.logger.debug(
                    f"Throttling: {time_since_last_update:.1f}s since last update "
                    f"(min: {self.throttle_interval}s)"
                )
                return

            # Парсим все файлы
            all_checkboxes = self._parse_all_checkboxes()

            if not all_checkboxes:
                self.logger.debug("No checkboxes found in prompt files")
                return

            # Создаем snapshot
            snapshot = self._calculate_progress(all_checkboxes)

            # Проверяем изменился ли прогресс
            if self.current_snapshot and self._snapshots_equal(self.current_snapshot, snapshot):
                self.logger.debug("Progress unchanged, skipping update")
                return

            self.current_snapshot = snapshot
            self.last_update_time = current_time

            # Вызываем callback для обновления UI
            self.logger.info(
                f"Progress updated: {snapshot.completed}/{snapshot.total} "
                f"({snapshot.percentage:.1f}%)"
            )

            # Вызываем async callback
            if asyncio.iscoroutinefunction(self.update_callback):
                await self.update_callback(snapshot)
            else:
                self.update_callback(snapshot)

        except Exception as e:
            # Graceful error handling - не роняем мониторинг
            self.logger.error(f"Error parsing and updating progress: {e}", exc_info=True)

    def _parse_all_checkboxes(self) -> List[CheckboxItem]:
        """
        Парсинг всех чекбоксов из всех .md файлов в export_dir

        Returns:
            Список всех найденных чекбоксов
        """
        all_checkboxes: List[CheckboxItem] = []

        # Рекурсивно находим все .md файлы
        if not self.export_dir.exists():
            return all_checkboxes

        md_files = list(self.export_dir.rglob("*.md"))

        for md_file in md_files:
            try:
                checkboxes = self._parse_checkboxes_from_file(md_file)
                all_checkboxes.extend(checkboxes)
            except Exception as e:
                self.logger.warning(f"Failed to parse {md_file}: {e}")

        return all_checkboxes

    def _parse_checkboxes_from_file(self, file_path: Path) -> List[CheckboxItem]:
        """
        Парсинг чекбоксов из одного файла с контекстом

        Парсит markdown файл и извлекает:
        - Чекбоксы (- [ ] и - [x])
        - Контекст (родительский заголовок ## или ###)
        - Номер строки

        Args:
            file_path: Путь к markdown файлу

        Returns:
            Список чекбоксов из файла
        """
        checkboxes: List[CheckboxItem] = []

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            current_context = None  # Текущий заголовок раздела

            # Регулярные выражения
            # Заголовки: ## Шаг 1: Анализ
            header_pattern = re.compile(r"^(#{2,})\s+(.+)$")
            # Чекбоксы: - [ ] Task или - [x] Task или - [X] Task
            checkbox_pattern = re.compile(r"^-\s*\[([ xX])\]\s+(.+)$")

            for line_num, line in enumerate(lines, start=1):
                line_stripped = line.strip()

                # Обновляем контекст при встрече заголовка
                header_match = header_pattern.match(line_stripped)
                if header_match:
                    header_level = len(header_match.group(1))  # Количество #
                    header_text = header_match.group(2).strip()
                    # Используем только заголовки уровня 2-3 (## и ###)
                    if header_level in [2, 3]:
                        current_context = header_text
                    continue

                # Парсим чекбоксы
                checkbox_match = checkbox_pattern.match(line_stripped)
                if checkbox_match:
                    checkbox_mark = checkbox_match.group(1)
                    task_text = checkbox_match.group(2).strip()

                    # Определяем статус
                    if checkbox_mark in ["x", "X"]:
                        status = "completed"
                    else:
                        status = "pending"

                    checkbox = CheckboxItem(
                        text=task_text,
                        status=status,
                        file=str(file_path.relative_to(self.export_dir)),
                        line_number=line_num,
                        context=current_context,
                    )
                    checkboxes.append(checkbox)

        except Exception as e:
            self.logger.error(f"Failed to parse checkboxes from {file_path}: {e}")

        return checkboxes

    def _calculate_progress(self, checkboxes: List[CheckboxItem]) -> ProgressSnapshot:
        """
        Расчет прогресса на основе чекбоксов

        Args:
            checkboxes: Список всех чекбоксов

        Returns:
            Snapshot с прогрессом выполнения
        """
        total = len(checkboxes)
        completed = sum(1 for cb in checkboxes if cb.status == "completed")
        percentage = (completed / total * 100) if total > 0 else 0.0

        # Находим первую pending задачу (текущая задача)
        current_task = None
        for cb in checkboxes:
            if cb.status == "pending":
                current_task = cb.text
                break

        return ProgressSnapshot(
            total=total,
            completed=completed,
            percentage=percentage,
            current_task=current_task,
            checkboxes=checkboxes,
        )

    def _snapshots_equal(self, s1: ProgressSnapshot, s2: ProgressSnapshot) -> bool:
        """
        Проверка равенства двух snapshots

        Сравниваем только ключевые поля (completed/total),
        не сравниваем сами checkboxes для производительности.

        Args:
            s1: Первый snapshot
            s2: Второй snapshot

        Returns:
            True если snapshots одинаковые
        """
        return s1.total == s2.total and s1.completed == s2.completed

    def get_current_progress(self) -> Optional[ProgressSnapshot]:
        """
        Получить текущий snapshot прогресса

        Returns:
            Текущий snapshot или None если еще не парсили
        """
        return self.current_snapshot


# AICODE-NOTE: Экспортируем основные классы для удобного импорта
__all__ = ["ProgressMonitor", "ProgressSnapshot", "CheckboxItem"]
