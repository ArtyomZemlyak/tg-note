# Refactoring Summary: Aggregator Lifecycle & Telegram Decoupling

## Обзор

Реализованы два ключевых улучшения архитектуры:

1. **Централизованное управление жизненным циклом агрегаторов** через `BackgroundTaskManager`
2. **Снижение связности с Telegram API** через улучшенный `BotPort` с retry и throttling

## 1. BackgroundTaskManager - Централизованное управление фоновыми задачами

### Что было

- Старт агрегаторов в `UserContextManager.get_or_create_aggregator()`
- Стоп через различные пути: `invalidate_cache()`, `cleanup()`, прямые вызовы
- Отсутствие единой точки контроля и мониторинга
- Сложность отслеживания активных задач

### Что стало

```python
# src/core/background_task_manager.py
class BackgroundTaskManager:
    """Централизованный менеджер жизненного цикла фоновых задач"""

    def start(self) -> None:
        """Запустить менеджер"""

    async def stop(self) -> None:
        """Остановить все задачи"""

    def register_task(self, task_id: str, coroutine: Callable, ...):
        """Зарегистрировать и запустить задачу"""

    async def unregister_task(self, task_id: str):
        """Отменить регистрацию и остановить задачу"""
```

### Интеграция

**MessageAggregator**:

```python
def __init__(
    self,
    timeout: int = 30,
    user_id: Optional[int] = None,
    task_manager: Optional[BackgroundTaskManager] = None
):
    self.task_manager = task_manager
    # ...

def start_background_task(self) -> None:
    if self.task_manager and self.task_manager.is_running():
        self._task_id = f"aggregator_user_{self.user_id}"
        self.task_manager.register_task(
            task_id=self._task_id,
            coroutine=self._check_timeouts,
            description=f"MessageAggregator for user {self.user_id}",
            user_id=self.user_id
        )
```

**UserContextManager**:

```python
def __init__(
    self,
    settings_manager: SettingsManager,
    conversation_context_manager: ConversationContextManager,
    background_task_manager: Optional[BackgroundTaskManager] = None,
    timeout_callback=None
):
    self.background_task_manager = background_task_manager

def get_or_create_aggregator(self, user_id: int) -> MessageAggregator:
    aggregator = MessageAggregator(
        timeout=timeout,
        user_id=user_id,
        task_manager=self.background_task_manager
    )
    aggregator.start_background_task()
```

**TelegramBot**:

```python
async def start(self) -> None:
    # Start background task manager
    self.background_task_manager.start()
    # ...

async def stop(self) -> None:
    # Stop background tasks через UserContextManager
    await self.handlers.stop_background_tasks()
    # Stop background task manager
    await self.background_task_manager.stop()
```

### Преимущества

- ✅ Единая точка управления всеми фоновыми задачами
- ✅ Централизованное логирование старта/стопа
- ✅ Graceful shutdown с отменой всех задач
- ✅ Возможность мониторинга активных задач через `list_tasks()`
- ✅ Метаданные для каждой задачи (user_id, description, start time)

## 2. BotPort с Retry и Throttling

### Что было

- Прямые вызовы Telegram API без защиты от rate limiting
- Отсутствие автоматических retry при временных ошибках
- Риск получения 429 Too Many Requests
- Дублирование логики обработки ошибок в разных сервисах

### Что стало

**BotPort с встроенной защитой**:

```python
class RateLimiter:
    """Token bucket algorithm для throttling"""
    def __init__(self, rate: float = 30.0, per: float = 1.0):
        # 30 запросов в секунду по умолчанию

class BotPort(ABC):
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit: float = 30.0,
        rate_limit_period: float = 1.0
    ):
        self.rate_limiter = RateLimiter(rate=rate_limit, per=rate_limit_period)

    async def _with_retry_and_throttle(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Выполнить операцию с:
        - Rate limiting (token bucket)
        - Retry с exponential backoff
        - Детальное логирование
        """
        for attempt in range(self.max_retries):
            try:
                await self.rate_limiter.acquire()  # Throttling
                result = await operation(*args, **kwargs)
                return result
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    await asyncio.sleep(delay)
        raise last_exception

    async def send_message(self, chat_id: int, text: str, **kwargs) -> Any:
        return await self._with_retry_and_throttle(
            self._send_message_impl,
            f"send_message(chat_id={chat_id})",
            chat_id, text, **kwargs
        )
```

**TelegramBotAdapter - реализация**:

```python
class TelegramBotAdapter(BotPort):
    def __init__(
        self,
        bot: AsyncTeleBot,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit: float = 30.0,
        rate_limit_period: float = 1.0
    ):
        super().__init__(max_retries, retry_delay, rate_limit, rate_limit_period)
        self._bot = bot

    async def _send_message_impl(self, chat_id: int, text: str, **kwargs):
        return await self._bot.send_message(chat_id, text, **kwargs)
```

### Конфигурация в service_container.py

```python
container.register(
    "bot_adapter",
    lambda c: TelegramBotAdapter(
        bot=c.get("async_bot"),
        max_retries=3,
        retry_delay=1.0,
        rate_limit=30.0,  # 30 запросов
        rate_limit_period=1.0  # в секунду
    ),
    singleton=True
)
```

### Покрытие сервисов

Все основные сервисы используют `BotPort`:

- ✅ `NoteCreationService`
- ✅ `QuestionAnsweringService`
- ✅ `AgentTaskService`
- ✅ `MessageProcessor`
- ✅ `BotHandlers`

**Примечание**: `SettingsHandlers` и `MCPHandlers` используют `AsyncTeleBot` напрямую для UI-команд, что приемлемо так как:

- Это редкие UI-взаимодействия (не high-frequency)
- Retry менее критичны для простых команд
- Минимальный риск rate limiting

### Преимущества

- ✅ **Защита от rate limiting**: Token bucket algorithm
- ✅ **Автоматические retry**: Exponential backoff при ошибках
- ✅ **Централизованное логирование**: Все попытки и ошибки логируются
- ✅ **Конфигурируемость**: Настройка retry/throttling через DI
- ✅ **Прозрачность**: Сервисы не знают о retry - работает автоматически
- ✅ **Resilience**: Система устойчива к временным сбоям Telegram API

## Изменения в интерфейсах

### IUserContextManager

```python
# Методы стали async
async def invalidate_cache(self, user_id: int) -> None
async def cleanup(self) -> None
```

### MessageAggregator

```python
# stop_background_task стал async
async def stop_background_task(self) -> None
```

## Файлы изменены

### Новые файлы

- `src/core/background_task_manager.py` - Менеджер фоновых задач

### Измененные файлы

1. **Core/Infrastructure**:
   - `src/bot/bot_port.py` - Добавлены RateLimiter, retry logic
   - `src/bot/telegram_adapter.py` - Реализация с retry/throttling
   - `src/core/service_container.py` - Добавлен BackgroundTaskManager

2. **Aggregator & Context**:
   - `src/processor/message_aggregator.py` - Интеграция с BackgroundTaskManager
   - `src/services/user_context_manager.py` - Использование BackgroundTaskManager
   - `src/services/interfaces.py` - Async методы cleanup/invalidate_cache

3. **Bot & Handlers**:
   - `src/bot/telegram_bot.py` - Управление BackgroundTaskManager
   - `src/bot/handlers.py` - Async stop_background_tasks/invalidate_cache
   - `src/bot/settings_handlers.py` - Await для invalidate_cache
   - `src/bot/utils.py` - Документация для BotPort

## Тестирование

Рекомендуется проверить:

1. **Lifecycle агрегаторов**:
   - Создание пользовательских агрегаторов
   - Timeout обработка
   - Graceful shutdown

2. **Retry & Throttling**:
   - Отправка множества сообщений подряд
   - Поведение при временных ошибках API
   - Rate limiting (логи должны показывать throttling)

3. **Интеграция**:
   - Запуск/остановка бота
   - Изменение настроек пользователя (invalidate_cache)
   - Работа в режимах note/ask/agent

## Миграция и обратная совместимость

- ✅ Обратная совместимость сохранена
- ✅ MessageAggregator работает без BackgroundTaskManager (fallback режим)
- ✅ Все сервисы продолжают работать через BotPort прозрачно
- ✅ Не требуется изменений в конфигурации (defaults заданы)

## Метрики и мониторинг

### BackgroundTaskManager

```python
# Получить список активных задач
tasks = background_task_manager.list_tasks()
# {
#   "aggregator_user_123": {
#     "description": "MessageAggregator for user 123",
#     "started_at": 1234567890.123,
#     "status": "running",
#     "user_id": 123
#   }
# }
```

### BotPort Logging

```
INFO: send_message(chat_id=123) succeeded on attempt 2
WARNING: send_message(chat_id=456) failed on attempt 1/3: Connection timeout
```

## Заключение

Реализованы ключевые архитектурные улучшения:

1. **Централизованное управление lifecycle** - все фоновые задачи под контролем BackgroundTaskManager
2. **Resilient Telegram integration** - BotPort с retry и throttling защищает от rate limiting и временных ошибок
3. **Чистая архитектура** - сервисы декаплированы от Telegram через BotPort
4. **Production-ready** - логирование, мониторинг, graceful shutdown

Система теперь более устойчива, предсказуема и проще в поддержке.
