# Event-Driven Vector Search Reindexing

**Дата:** 2025-10-20  
**Статус:** ✅ Завершено

## Проблема

Изначальная реализация векторного поиска использовала только периодический мониторинг (каждые 5 минут), что означало:
- ⏰ Задержка до 5 минут для индексации изменений
- 💸 Избыточное сканирование даже когда изменений нет
- ❌ Не оптимально для частых изменений

## Решение: Event-Driven Architecture

Реализована event-driven архитектура с паттерном Observer для реактивной реиндексации.

### Принципы SOLID

✅ **Single Responsibility Principle**
- `EventBus` - управление событиями
- `BotVectorSearchManager` - векторный поиск
- Tools - операции с файлами

✅ **Open/Closed Principle**
- Можно добавлять новые подписчики без изменения publisher'ов
- Можно добавлять новые типы событий без изменения существующего кода

✅ **Dependency Inversion Principle**
- Tools зависят от абстракции (EventBus interface)
- Не зависят от конкретной реализации vector search

✅ **Low Coupling**
- Tools не знают о BotVectorSearchManager
- BotVectorSearchManager не знает о Tools
- Связь только через события

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                     Event-Driven Flow                       │
└─────────────────────────────────────────────────────────────┘

1. Agent изменяет файл через Tool
    ↓
2. Tool публикует событие в EventBus
    ↓
3. EventBus уведомляет всех подписчиков
    ↓
4. BotVectorSearchManager получает событие
    ↓
5. Автоматическая реиндексация (с батчингом)
```

### Компоненты

#### 1. Event System (`src/core/events.py`)

**EventBus** - Центральный event bus

```python
class EventBus:
    def subscribe(event_type, handler)         # Sync handler
    def subscribe_async(event_type, handler)   # Async handler
    def publish(event)                         # Sync publishing
    def publish_async(event)                   # Async publishing
```

**EventType** - Типы событий

```python
class EventType(Enum):
    # File events
    KB_FILE_CREATED
    KB_FILE_MODIFIED
    KB_FILE_DELETED

    # Folder events
    KB_FOLDER_CREATED
    KB_FOLDER_DELETED

    # Batch events
    KB_BATCH_CHANGES

    # Git events
    KB_GIT_COMMIT
    KB_GIT_PUSH
    KB_GIT_PULL
```

**Events** - Event classes

```python
@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]
    source: Optional[str]

@dataclass
class KBChangeEvent(Event):
    file_path: Optional[Path]
    files: Optional[List[Path]]
    user_id: Optional[int]
```

#### 2. Event Publisher (`src/agents/tools/_event_publisher.py`)

Утилита для публикации событий из tools:

```python
def publish_kb_file_event(
    event_type: EventType,
    file_path: Path,
    user_id: Optional[int] = None,
    source: str = "agent_tool"
)

def publish_kb_batch_event(
    files: List[Path],
    user_id: Optional[int] = None,
    source: str = "agent_tool"
)

def publish_kb_git_event(
    event_type: EventType,
    user_id: Optional[int] = None,
    source: str = "git_tool",
    **kwargs
)
```

#### 3. Updated Components

**BotVectorSearchManager** - Подписывается на события

```python
def __init__(self, ..., subscribe_to_events: bool = True):
    if subscribe_to_events:
        self._subscribe_to_kb_events()

def _subscribe_to_kb_events():
    event_bus = get_event_bus()
    event_bus.subscribe_async(EventType.KB_FILE_CREATED, self._handle_kb_change_event)
    event_bus.subscribe_async(EventType.KB_FILE_MODIFIED, self._handle_kb_change_event)
    event_bus.subscribe_async(EventType.KB_FILE_DELETED, self._handle_kb_change_event)
    event_bus.subscribe_async(EventType.KB_BATCH_CHANGES, self._handle_kb_change_event)
    event_bus.subscribe_async(EventType.KB_GIT_COMMIT, self._handle_kb_change_event)
    event_bus.subscribe_async(EventType.KB_GIT_PULL, self._handle_kb_change_event)

async def _handle_kb_change_event(event: KBChangeEvent):
    # Batch multiple rapid changes (2 second window)
    self._reindex_pending = True
    await asyncio.sleep(2)

    if self._reindex_pending:
        self._reindex_pending = False
        await self.check_and_reindex_changes()
```

**Agent Tools** - Публикуют события

- `file_create` → `KB_FILE_CREATED`
- `file_edit` → `KB_FILE_MODIFIED`
- `file_delete` → `KB_FILE_DELETED`
- `file_move` → `KB_BATCH_CHANGES` (старый + новый файл)
- `folder_create` → `KB_FOLDER_CREATED`
- `folder_delete` → `KB_FOLDER_DELETED`
- `git commit` → `KB_GIT_COMMIT`
- `git push` → `KB_GIT_PUSH`
- `git pull` → `KB_GIT_PULL`

## Пример использования

### 1. Agent создает файл

```python
# Agent tool execution
await file_create_tool.execute({
    "path": "notes/new-note.md",
    "content": "# New Note\n..."
}, context)

# → Tool публикует событие
publish_kb_file_event(
    EventType.KB_FILE_CREATED,
    file_path=Path("notes/new-note.md"),
    user_id=123,
    source="file_create_tool"
)

# → BotVectorSearchManager получает событие
# → Ждет 2 секунды (батчинг)
# → Автоматически реиндексирует
```

### 2. Agent делает множественные изменения

```python
# Agent редактирует 3 файла подряд
file_edit(..., "file1.md")  # Event 1
file_edit(..., "file2.md")  # Event 2
file_edit(..., "file3.md")  # Event 3

# → 3 события опубликованы
# → BotVectorSearchManager батчит их вместе
# → Одна реиндексация для всех изменений
```

### 3. Manual trigger

```python
# Можно вручную триггернуть реиндексацию
await vector_search_manager.trigger_reindex()
```

## Батчинг изменений

Система автоматически батчит множественные изменения:

```python
# В _handle_kb_change_event:
self._reindex_pending = True
await asyncio.sleep(2)  # Ждем 2 секунды

if self._reindex_pending:  # Если еще pending
    self._reindex_pending = False
    await self.check_and_reindex_changes()  # Одна реиндексация
```

**Преимущества:**
- ✅ Множественные изменения → одна реиндексация
- ✅ Меньше нагрузки на систему
- ✅ Более эффективное использование ресурсов

## Fallback механизм

Периодический мониторинг остается как fallback:

```python
# Primary: Event-driven (reactive)
_subscribe_to_kb_events()

# Fallback: Periodic monitoring (каждые 5 минут)
start_monitoring(check_interval=300)
```

**Зачем fallback?**
- Изменения извне (NFS, external tools)
- Пропущенные события
- Гарантия консистентности

## Созданные файлы

1. **`src/core/events.py`** (390 строк)
   - `EventBus` - event bus implementation
   - `EventType` - event types enum
   - `Event` / `KBChangeEvent` - event classes

2. **`src/agents/tools/_event_publisher.py`** (80 строк)
   - Helper functions для публикации событий
   - Минимизирует coupling в tools

## Измененные файлы

1. **`src/bot/vector_search_manager.py`**
   - Added event subscription
   - Added `_handle_kb_change_event()`
   - Added `trigger_reindex()` for manual triggers
   - Updated `start_monitoring()` documentation

2. **`src/agents/tools/file_tools.py`**
   - Added event publishing in `FileCreateTool`
   - Added event publishing in `FileEditTool`
   - Added event publishing in `FileDeleteTool`
   - Added event publishing in `FileMoveTool`

3. **`src/agents/tools/folder_tools.py`**
   - Added event publishing in `FolderCreateTool`
   - Added event publishing in `FolderDeleteTool`

4. **`src/agents/tools/git_tools.py`**
   - Added event publishing for git commit/push/pull

## Производительность

### До (периодический мониторинг)

```
Time    Action
0s      Agent creates file
5s      ... waiting ...
10s     ... waiting ...
15s     ... waiting ...
20s     ... waiting ...
25s     ... waiting ...
30s     Periodic scan → reindex
```

**Задержка:** До 5 минут (300 секунд)

### После (event-driven)

```
Time    Action
0s      Agent creates file → Event published
2s      Reindex triggered (batching window)
```

**Задержка:** ~2 секунды (150x быстрее!)

## Расширяемость

### Добавить новый subscriber

```python
# В любом компоненте
def my_handler(event: KBChangeEvent):
    print(f"KB changed: {event.file_path}")

get_event_bus().subscribe(EventType.KB_FILE_CREATED, my_handler)
```

### Добавить новый publisher

```python
# В любом tool
from src.core.events import EventType, get_event_bus

event = KBChangeEvent(
    event_type=EventType.KB_FILE_CREATED,
    file_path=new_file,
    user_id=123,
    source="my_tool"
)
get_event_bus().publish(event)
```

### Добавить новый тип события

```python
# В events.py
class EventType(Enum):
    ...
    KB_FILE_ARCHIVED = "kb.file.archived"  # Новый тип
```

## Тестирование

Event system легко тестируется благодаря развязке:

```python
# Test tool без запуска vector search
def test_file_create_publishes_event():
    event_received = []

    def handler(event):
        event_received.append(event)

    get_event_bus().subscribe(EventType.KB_FILE_CREATED, handler)

    # Execute tool
    file_create_tool.execute(...)

    # Verify event was published
    assert len(event_received) == 1
    assert event_received[0].type == EventType.KB_FILE_CREATED
```

## Миграция

### Обратная совместимость

✅ **100% обратно совместимо**

- Event system опционален
- Fallback на периодический мониторинг
- Graceful degradation если EventBus недоступен

### Для существующих систем

Ничего не нужно менять! Все работает автоматически:

1. Event system инициализируется автоматически
2. Tools автоматически публикуют события
3. Vector search автоматически подписывается
4. Fallback мониторинг продолжает работать

## Заключение

✅ **Достигнуты цели:**

1. ✅ **Реактивная реиндексация** - сразу при изменениях (задержка ~2 сек вместо 5 мин)
2. ✅ **SOLID принципы** - низкая связность, высокая cohesion
3. ✅ **Расширяемость** - легко добавлять новые события/подписчики
4. ✅ **Производительность** - батчинг множественных изменений
5. ✅ **Надежность** - fallback на периодический мониторинг

**Результат:** 150x быстрее индексация изменений при сохранении архитектурной чистоты! 🎉

## Файлы

### Созданные
- `src/core/events.py` (390 строк)
- `src/agents/tools/_event_publisher.py` (80 строк)
- `VECTOR_SEARCH_EVENT_DRIVEN.md` (этот файл)

### Измененные
- `src/bot/vector_search_manager.py` (+60 строк)
- `src/agents/tools/file_tools.py` (+40 строк)
- `src/agents/tools/folder_tools.py` (+20 строк)
- `src/agents/tools/git_tools.py` (+25 строк)

**Всего:** ~615 строк нового кода
