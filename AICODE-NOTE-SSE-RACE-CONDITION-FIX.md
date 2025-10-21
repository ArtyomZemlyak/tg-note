# AICODE-NOTE: SSE Connection Race Condition Fix

## Проблема

В методе `_connect_sse` происходила race condition между инициализацией SSE соединения и началом чтения ответов:

1. Устанавливалось SSE соединение и получался `session_id`
2. Сохранялся `_sse_response` для чтения SSE потока
3. Запускался `_sse_reader_task` для чтения ответов
4. **Сразу же** вызывался `_initialize()`, который отправлял initialize запрос
5. `_initialize()` вызывал `_send_request`, который ждал ответа через SSE

**Проблема**: `_initialize()` вызывался ДО того, как `_sse_reader_task` успевал прочитать ответ!

## Решение

Добавлен механизм синхронизации с использованием `asyncio.Event`:

1. **Добавлено событие `_sse_reader_ready`** в конструктор `MCPClient`
2. **В `_sse_reader`** добавлен сигнал готовности в начале метода
3. **В `_connect_sse`** добавлено ожидание готовности перед вызовом `_initialize()`
4. **В `disconnect` и `reconnect`** добавлен сброс события

## Изменения в коде

### 1. Добавлено событие в конструктор
```python
# AICODE-NOTE: Event to signal when SSE reader is ready to process responses
self._sse_reader_ready = asyncio.Event()
```

### 2. Сигнал готовности в _sse_reader
```python
async def _sse_reader(self) -> None:
    # ... existing code ...

    # Signal that SSE reader is ready to process responses
    if self._sse_reader_ready:
        self._sse_reader_ready.set()
        logger.debug("[MCPClient] SSE reader ready signal sent")

    # ... rest of the method ...
```

### 3. Ожидание готовности в _connect_sse
```python
# Store SSE response and start background task to read from stream
self._sse_response = response
self._sse_reader_task = asyncio.create_task(self._sse_reader())
logger.debug("[MCPClient] Started SSE reader task")

# Wait for SSE reader to be ready before initializing
logger.debug("[MCPClient] Waiting for SSE reader to be ready...")
await self._sse_reader_ready.wait()
logger.debug("[MCPClient] SSE reader is ready, proceeding with initialization")
```

### 4. Сброс события при отключении/переподключении
```python
# In disconnect()
if self._sse_reader_ready:
    self._sse_reader_ready.clear()

# In reconnect()
if self._sse_reader_ready:
    self._sse_reader_ready.clear()
```

## Тестирование

Создан тест `test_mcp_client_sse_race_condition.py` который проверяет:

1. **Порядок операций**: SSE reader сигнализирует о готовности ДО вызова initialize
2. **Инициализация события**: событие правильно инициализируется
3. **Сброс при отключении**: событие сбрасывается при disconnect
4. **Сброс при переподключении**: событие сбрасывается при reconnect

## Результат

Теперь `_initialize()` вызывается только после того, как `_sse_reader_task` готов к обработке ответов, что устраняет race condition и обеспечивает корректную работу SSE соединения.

## Файлы изменены

- `src/mcp/client.py` - основное исправление
- `tests/test_mcp_client_sse_race_condition.py` - тесты для проверки исправления
