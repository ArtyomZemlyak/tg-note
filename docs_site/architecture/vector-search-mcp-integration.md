# Vector Search MCP Integration

Эта страница описывает архитектуру интеграции векторного поиска с MCP (Model Context Protocol).

## Обзор

Векторный поиск полностью интегрирован с MCP Hub с четким разделением ответственности:

### Разделение ответственности

**MCP HUB** предоставляет функциональность (WHAT):
- **Поиск** - semantic search в базе знаний
- **CRUD операции** - добавление, удаление, обновление документов в векторной БД
- **Полная реиндексация** - при необходимости

**BOT** принимает решения (WHEN):
- **Мониторинг изменений** - отслеживает изменения в базах знаний
- **Принятие решений** - решает когда вызывать MCP Hub для обновления индекса
- **Реактивность** - реагирует на события изменения файлов

### Преимущества архитектуры

1. **Централизованное управление** - Все операции с векторной БД выполняются MCP Hub
2. **Отсутствие дублирования** - BOT не дублирует функциональность MCP Hub
3. **Инкрементальные обновления** - BOT вызывает add/update/delete для конкретных файлов
4. **Унифицированный доступ** - Агенты используют векторный поиск через стандартные MCP тулзы

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      Bot Container                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  main.py (Startup)                                   │  │
│  │  1. Проверка MCP Hub health                          │  │
│  │  2. Инициализация Vector Search Manager              │  │
│  │  3. Запуск мониторинга изменений                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  BotVectorSearchManager                              │  │
│  │  - Проверка доступности тулз через API               │  │
│  │  - Сканирование файлов KB                            │  │
│  │  - Обнаружение изменений (diff)                      │  │
│  │  - Триггер реиндексации через MCP                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           │ HTTP API                        │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     MCP Hub Container                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MCP Hub Server                                      │  │
│  │  /health - Список доступных тулз                     │  │
│  │  /registry/servers - MCP серверы                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Vector Search Tools (MCP)                           │  │
│  │  Search:                                             │  │
│  │  - vector_search(query, top_k)                       │  │
│  │                                                      │  │
│  │  CRUD Operations (called by BOT):                    │  │
│  │  - add_vector_documents(file_paths)                  │  │
│  │  - delete_vector_documents(file_paths)               │  │
│  │  - update_vector_documents(file_paths)               │  │
│  │  - reindex_vector(force) [full reindex]              │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  VectorSearchManager                                 │  │
│  │  - Embeddings (sentence-transformers/openai)         │  │
│  │  - Vector Store (FAISS/Qdrant)                       │  │
│  │  - Chunking (fixed/semantic)                         │  │
│  │  - Index Management                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ MCP Protocol
┌─────────────────────────────────────────────────────────────┐
│                        Agent                                │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tool Manager                                        │  │
│  │  - kb_vector_search                                  │  │
│  │  - (reindex managed by bot only)                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. Bot Container

#### BotVectorSearchManager (`src/bot/vector_search_manager.py`)

**AICODE-NOTE: BOT's responsibility - WHEN to update vector search**

Принимает решения о необходимости обновления векторной БД:

**Ответственности (WHEN - Когда делать):**

- Проверка доступности векторного поиска через MCP Hub API
- Сканирование файлов в базах знаний для обнаружения изменений
- Вычисление хешей файлов для tracking изменений
- **Принятие решений**: когда вызывать MCP Hub для обновления индекса
- Сохранение/загрузка состояния отслеживания (file hashes)

**НЕ выполняет** (это делает MCP Hub):
- Эмбеддинги текстов
- Управление векторной БД
- Индексацию/переиндексацию
- CRUD операции с документами

**Основные методы:**

- `check_vector_search_availability()` - Проверяет доступность MCP Hub tools через `/health`
- `perform_initial_indexing()` - Запускает начальную индексацию через MCP Hub
- `check_and_reindex_changes()` - **Главный метод**: обнаруживает изменения и вызывает MCP Hub
  - Для новых файлов → `add_vector_documents`
  - Для измененных файлов → `update_vector_documents`
  - Для удаленных файлов → `delete_vector_documents`
- `start_monitoring()` - Запускает фоновый мониторинг (каждые 5 минут)
- `trigger_reindex()` - Вручную запускает проверку и реиндексацию
- `shutdown()` - Корректно завершает работу менеджера

**Важные особенности:**

- **Событийная система:** Подписывается на события изменения KB (создание, изменение, удаление файлов)
- **Батчинг изменений:** Множественные изменения в течение 2 секунд объединяются в одну операцию
- **Защита от конкурентности:** Использует async lock для предотвращения одновременных операций
- **Инкрементальные обновления:** Вызывает конкретные MCP операции (add/update/delete) вместо полной реиндексации
- **Корректное завершение:** Метод `shutdown()` отменяет pending задачи

#### Инициализация в main.py

```python
# main.py
if settings.VECTOR_SEARCH_ENABLED:
    from src.bot.vector_search_manager import initialize_vector_search_for_bot
    
    vector_search_manager = await initialize_vector_search_for_bot(
        mcp_hub_url=mcp_hub_url,
        kb_root_path=settings.KB_PATH,
        start_monitoring=True,
    )
```

### 2. MCP Hub Container

#### MCP Hub Server (`src/mcp/mcp_hub_server.py`)

Предоставляет векторный поиск как MCP тулзы:

**Доступные тулзы:**

**Для Агентов (Search):**
1. **`vector_search`** - Семантический поиск в базе знаний
   - `query` (string) - Поисковый запрос
   - `top_k` (int) - Количество результатов (default: 5)
   - `user_id` (int, optional) - ID пользователя

**Для BOT (CRUD Operations):**
2. **`add_vector_documents`** - Добавить документы в индекс
   - `file_paths` (list[string]) - Список путей к файлам относительно KB root
   - `user_id` (int, optional) - ID пользователя

3. **`delete_vector_documents`** - Удалить документы из индекса
   - `file_paths` (list[string]) - Список путей к файлам
   - `user_id` (int, optional) - ID пользователя

4. **`update_vector_documents`** - Обновить документы в индексе
   - `file_paths` (list[string]) - Список путей к файлам
   - `user_id` (int, optional) - ID пользователя

5. **`reindex_vector`** - Полная переиндексация (fallback)
   - `force` (bool) - Принудительная переиндексация (default: false)
   - `user_id` (int, optional) - ID пользователя

**Проверка доступности:**

```python
def check_vector_search_availability() -> bool:
    """Проверяет конфигурацию и зависимости"""
    # 1. Проверка VECTOR_SEARCH_ENABLED
    # 2. Проверка embedding provider зависимостей
    # 3. Проверка vector store backend
    return available
```

**Инициализация:**

```python
async def get_vector_search_manager() -> Optional[VectorSearchManager]:
    """Создает и инициализирует VectorSearchManager"""
    # Создание из настроек
    manager = VectorSearchFactory.create_from_settings(...)
    
    # Инициализация (загрузка существующего индекса)
    await manager.initialize()
    
    return manager
```

#### VectorSearchManager (`src/mcp/vector_search/manager.py`)

**AICODE-NOTE: MCP HUB's responsibility - WHAT operations to provide**

Основной менеджер векторного поиска, предоставляющий функциональность:

**Компоненты:**

- **Embedder** - Создание векторных представлений (sentence-transformers/openai/infinity)
- **VectorStore** - Хранение векторов (FAISS/Qdrant)
- **Chunker** - Разбиение документов на чанки
- **Index Metadata** - Отслеживание индексированных файлов и хэшей

**Основные методы:**

**Search:**
- `search(query, top_k)` - Семантический поиск

**Full Indexing:**
- `index_knowledge_base(force)` - Полная (пере)индексация всех файлов
- `initialize()` - Инициализация и загрузка существующего индекса
- `clear_index()` - Очистка индекса

**CRUD Operations (новые):**
- `add_documents_by_paths(file_paths)` - Добавить конкретные документы
- `delete_documents_by_paths(file_paths)` - Удалить конкретные документы
- `update_documents_by_paths(file_paths)` - Обновить конкретные документы (delete + add)

**Metadata Management:**
- `get_stats()` - Статистика индекса
- `_get_file_hash()` - Вычисление хэша файла
- `_save_metadata()` / `_load_metadata()` - Управление метаданными

**Инкрементальная индексация:**

- Хранит хеши файлов в `metadata.json` в `.vector_index/`
- При индексации проверяет изменения по хэшам
- Индексирует только новые/измененные файлы
- Полная реиндексация при изменении конфигурации (embedder, chunker, vector store)

**Обработка удаленных файлов:**

- **Qdrant (поддерживает удаление):** Удаляет векторы по фильтру `file_path` инкрементально через `delete_by_filter`
- **FAISS (не поддерживает удаление):** Возвращает ошибку из `delete_documents_by_paths`, требуется полная реиндексация
- **Метаданные:** Обновляются только после успешного удаления/индексации для корректного состояния при ошибках

### 3. Agent

#### Tool Registry (`src/agents/tools/registry.py`)

Регистрирует MCP тулзы векторного поиска:

```python
if enable_vector_search:
    from ..mcp.vector_search import vector_search_tool
    
    for tool in vector_search_tool.ALL_TOOLS:
        tool.enable()
    manager.register_many(vector_search_tool.ALL_TOOLS)
```

#### Agent Factory (`src/agents/agent_factory.py`)

Передает флаг векторного поиска из настроек:

```python
config = {
    ...
    "enable_vector_search": settings.VECTOR_SEARCH_ENABLED,
    ...
}

agent = AutonomousAgent(
    ...
    enable_vector_search=config.get("enable_vector_search", False),
    ...
)
```

## Последовательность работы

### Startup Sequence

1. **Bot Container Startup**
   ```
   1. main.py запускается
   2. Запуск MCP Hub Server
   3. Ожидание MCP Hub health check
   4. Проверка доступности векторного поиска
   5. Инициализация BotVectorSearchManager
   6. Сканирование баз знаний
   7. Запуск фонового мониторинга
   ```

2. **MCP Hub Initialization**
   ```
   1. mcp_hub_server.py запускается
   2. Проверка VECTOR_SEARCH_ENABLED
   3. Проверка зависимостей
   4. Регистрация vector search тулз
   5. /health возвращает доступные тулзы
   ```

### Agent Vector Search Flow

1. **Agent вызывает kb_vector_search**
   ```
   Agent → ToolManager → VectorSearchMCPTool → MCP Client → MCP Hub
   ```

2. **MCP Hub обрабатывает запрос**
   ```
   MCP Hub → vector_search tool → VectorSearchManager → Embedder/VectorStore
   ```

3. **Возврат результатов**
   ```
   Results → MCP Hub → MCP Client → VectorSearchMCPTool → Agent
   ```

### Change Detection and Incremental Updates

**AICODE-NOTE: Новая архитектура - BOT решает КОГДА, MCP Hub делает ЧТО**

1. **Событийный мониторинг** (основной механизм - BOT)
   ```
   KB событие (create/modify/delete) 
   → BotVectorSearchManager._handle_kb_change_event()
   → Батчинг изменений (2 секунды)
   → check_and_reindex_changes()
   → Сканирование файлов
   → Вычисление хешей
   → Сравнение с предыдущими хешами
   → Обнаружение: added, modified, deleted
   → Вызов соответствующих MCP Hub операций:
      - Added files → add_vector_documents
      - Modified files → update_vector_documents
      - Deleted files → delete_vector_documents
   ```

2. **Фоновый мониторинг** (fallback, каждые 5 минут - BOT)
   ```
   BotVectorSearchManager.start_monitoring()
   → Периодическая проверка изменений
   → Для случаев, не покрытых событиями (NFS, внешние изменения)
   ```

3. **Обработка CRUD операций в MCP Hub**
   ```
   MCP Hub получает запрос от BOT:
   
   add_vector_documents(file_paths):
   → VectorSearchManager.add_documents_by_paths()
   → Чтение файлов
   → Chunking
   → Embedding
   → Добавление в vector store
   → Обновление metadata
   
   delete_vector_documents(file_paths):
   → VectorSearchManager.delete_documents_by_paths()
   → Если Qdrant: delete_by_filter({"file_path": path})
   → Если FAISS: возврат ошибки (требуется full reindex)
   → Обновление metadata
   
   update_vector_documents(file_paths):
   → VectorSearchManager.update_documents_by_paths()
   → delete_documents_by_paths()
   → add_documents_by_paths()
   → Обновление metadata
   
   reindex_vector(force):
   → VectorSearchManager.index_knowledge_base(force)
   → Полная переиндексация (fallback)
   ```

4. **Преимущества инкрементальных обновлений:**
   - Быстрее полной реиндексации (обрабатываются только измененные файлы)
   - Меньше нагрузка на embedder
   - Меньше использование памяти
   - Лучшая отзывчивость системы

## Конфигурация

### Environment Variables

```bash
# Vector Search Enable
VECTOR_SEARCH_ENABLED=true

# Embedding Provider
VECTOR_EMBEDDING_PROVIDER=sentence_transformers
VECTOR_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Vector Store
VECTOR_STORE_PROVIDER=faiss

# Chunking
VECTOR_CHUNKING_STRATEGY=fixed_size_overlap
VECTOR_CHUNK_SIZE=512
VECTOR_CHUNK_OVERLAP=50

# Search
VECTOR_SEARCH_TOP_K=5
```

### config.yaml

```yaml
# Vector Search Configuration
vector_search:
  enabled: true
  
  # Embedding configuration
  embedding:
    provider: sentence_transformers  # sentence_transformers, openai, infinity
    model: all-MiniLM-L6-v2
  
  # Vector store configuration
  vector_store:
    provider: faiss  # faiss, qdrant
  
  # Chunking configuration
  chunking:
    strategy: fixed_size_overlap  # fixed_size, fixed_size_overlap, semantic
    chunk_size: 512
    chunk_overlap: 50
    respect_headers: true
  
  # Search configuration
  search:
    top_k: 5
```

## Зависимости

### Required

- `loguru` - Логирование
- `aiohttp` - HTTP клиент для bot ↔ MCP Hub
- `pathlib` - Работа с путями

### Optional (для векторного поиска)

- `sentence-transformers` - Для sentence_transformers provider
- `faiss-cpu` - Для FAISS vector store
- `qdrant-client` - Для Qdrant vector store
- `openai` - Для OpenAI embeddings

## Мониторинг и Логирование

### Bot Container

```
🔍 Checking vector search availability at http://mcp-hub:8765/health
✅ Vector search tools are available: vector_search
🔄 Starting initial knowledge base indexing...
📊 Scanned 150 markdown files
👁️ Starting KB change monitoring (checking every 300s)...
📝 Detected changes: KBChange(added=2, modified=3, deleted=1)
🔄 Triggering reindexing due to changes...
✅ Change detection completed, hashes updated
```

### MCP Hub

```
🔍 Vector search is available and properly configured
🚀 INITIALIZING VECTOR SEARCH MANAGER
📁 KB Root: /app/knowledge_base
🔄 Initializing vector search manager...
✅ Vector search manager initialized successfully
🔍 VECTOR_SEARCH called
  Query: neural networks architecture
  Top K: 5
✅ Vector search successful: found 5 results
```

## Troubleshooting

### Vector Search Not Available

**Проблема:** MCP Hub не предоставляет vector search тулзы

**Решение:**
1. Проверьте `VECTOR_SEARCH_ENABLED=true`
2. Проверьте зависимости:
   ```bash
   pip install sentence-transformers faiss-cpu
   ```
3. Проверьте логи MCP Hub на ошибки инициализации

### No Changes Detected

**Проблема:** Изменения в KB не обнаруживаются

**Решение:**
1. Проверьте права доступа к `data/vector_search_hashes.json`
2. Проверьте логи мониторинга
3. Вручную удалите файл хешей для полной переиндексации

### Indexing Slow

**Проблема:** Индексация занимает много времени

**Решение:**
1. Уменьшите `VECTOR_CHUNK_SIZE`
2. Используйте менее ресурсоемкую модель embeddings
3. Проверьте количество файлов в KB

## См. также

- [Vector Search Quickstart](../../VECTOR_SEARCH_QUICKSTART.md)
- [MCP Architecture](./mcp-architecture.md)
- [Agent Architecture](./agent-architecture.md)
- [Deployment Guide](../deployment/overview.md)
