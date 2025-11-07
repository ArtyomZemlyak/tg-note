"""
BotPort Interface
Abstract interface for bot messaging operations (Clean Architecture)
This interface decouples services from the specific transport implementation
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from loguru import logger


class RateLimiter:
    """
    Rate limiter for throttling API requests
    Использует token bucket algorithm
    """

    def __init__(self, rate: float = 30.0, per: float = 1.0):
        """
        Initialize rate limiter

        Args:
            rate: Количество запросов
            per: Временной интервал в секундах
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Дождаться разрешения на выполнение запроса"""
        async with self._lock:
            current = asyncio.get_event_loop().time()
            time_passed = current - self.last_check
            self.last_check = current

            # Пополнить "токены"
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate

            # Если недостаточно токенов, ждать
            if self.allowance < 1.0:
                sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
                await asyncio.sleep(sleep_time)
                self.allowance = 0.0
            else:
                self.allowance -= 1.0


class BotPort(ABC):
    """
    Abstract interface for bot messaging operations

    This interface defines the contract for sending and editing messages,
    allowing services to be independent of the specific transport (Telegram, Slack, etc.)

    Включает встроенные механизмы:
    - Retry logic с экспоненциальным backoff
    - Rate limiting для предотвращения throttling
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        rate_limit: float = 30.0,
        rate_limit_period: float = 1.0,
    ):
        """
        Initialize BotPort with retry and rate limiting

        Args:
            max_retries: Максимальное количество повторов при ошибке
            retry_delay: Начальная задержка между повторами (секунды)
            rate_limit: Количество запросов для rate limiting
            rate_limit_period: Период для rate limiting (секунды)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limiter = RateLimiter(rate=rate_limit, per=rate_limit_period)
        self.logger = logger

    async def _with_retry_and_throttle(
        self, operation: Callable, operation_name: str, *args, **kwargs
    ) -> Any:
        """
        Выполнить операцию с retry и throttling

        Args:
            operation: Асинхронная функция для выполнения
            operation_name: Название операции для логирования
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы

        Returns:
            Результат операции
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                await self.rate_limiter.acquire()

                # Выполнить операцию
                result = await operation(*args, **kwargs)

                if attempt > 0:
                    self.logger.info(f"{operation_name} succeeded on attempt {attempt + 1}")

                return result

            except Exception as e:
                last_exception = e
                self.logger.warning(
                    f"{operation_name} failed on attempt {attempt + 1}/{self.max_retries}: {e}"
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2**attempt)
                    self.logger.debug(f"Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)

        # Все попытки исчерпаны
        self.logger.error(
            f"{operation_name} failed after {self.max_retries} attempts: {last_exception}"
        )
        raise last_exception

    @abstractmethod
    async def _send_message_impl(self, chat_id: int, text: str, **kwargs) -> Any:
        """
        Реализация отправки сообщения (без retry/throttling)
        Должна быть реализована в конкретном адаптере
        """
        pass

    async def send_message(self, chat_id: int, text: str, **kwargs) -> Any:
        """
        Send a message to a chat (с retry и throttling)

        Args:
            chat_id: Chat identifier
            text: Message text
            **kwargs: Additional transport-specific parameters

        Returns:
            Message object (transport-specific)
        """
        return await self._with_retry_and_throttle(
            self._send_message_impl, f"send_message(chat_id={chat_id})", chat_id, text, **kwargs
        )

    @abstractmethod
    async def _reply_to_impl(self, message: Any, text: str, **kwargs) -> Any:
        """
        Реализация ответа на сообщение (без retry/throttling)
        Должна быть реализована в конкретном адаптере
        """
        pass

    async def reply_to(self, message: Any, text: str, **kwargs) -> Any:
        """
        Reply to a message (с retry и throttling)

        Args:
            message: Original message to reply to
            text: Reply text
            **kwargs: Additional transport-specific parameters

        Returns:
            Message object (transport-specific)
        """
        return await self._with_retry_and_throttle(
            self._reply_to_impl, "reply_to", message, text, **kwargs
        )

    @abstractmethod
    async def _edit_message_text_impl(
        self, text: str, chat_id: int, message_id: int, **kwargs
    ) -> Any:
        """
        Реализация редактирования сообщения (без retry/throttling)
        Должна быть реализована в конкретном адаптере
        """
        pass

    async def edit_message_text(self, text: str, chat_id: int, message_id: int, **kwargs) -> Any:
        """
        Edit a message text (с retry и throttling)

        Args:
            text: New message text
            chat_id: Chat identifier
            message_id: Message identifier to edit
            **kwargs: Additional transport-specific parameters

        Returns:
            Updated message object (transport-specific)
        """
        return await self._with_retry_and_throttle(
            self._edit_message_text_impl,
            f"edit_message_text(chat_id={chat_id}, message_id={message_id})",
            text,
            chat_id,
            message_id,
            **kwargs,
        )

    @abstractmethod
    async def download_file(self, file_path: str) -> bytes:
        """
        Download a file by its file path

        Args:
            file_path: File path from the transport service

        Returns:
            File content as bytes
        """
        pass

    @abstractmethod
    async def get_file(self, file_id: str):
        """
        Get file info by file ID

        Args:
            file_id: File identifier

        Returns:
            File object with path information
        """
        pass

    @abstractmethod
    async def get_me(self):
        """
        Get bot information

        Returns:
            Bot information object
        """
        pass
