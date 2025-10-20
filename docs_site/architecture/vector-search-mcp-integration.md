# Vector Search MCP Integration

Эта страница описывает архитектуру интеграции векторного поиска с MCP (Model Context Protocol).

## Обзор

Векторный поиск полностью интегрирован с MCP Hub, что обеспечивает:

1. **Централизованное управление** - Все тулзы векторного поиска доступны через MCP Hub
2. **Автоматическая индексация** - При старте bot контейнера автоматически проверяется доступность и выполняется индексация
3. **Мониторинг изменений** - Автоматическая реиндексация при изменениях в базах знаний
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
│  │  - vector_search(query, top_k)                       │  │
│  │  - reindex_vector(force) [bot-managed]               │  │
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

Управляет векторным поиском со стороны бота:

**Ответственности:**

- Проверка доступности векторного поиска через MCP Hub API
- Сканирование файлов в базах знаний
- Вычисление хешей файлов для обнаружения изменений
- Мониторинг изменений и триггер реиндексации
- Сохранение/загрузка состояния

**Основные методы:**

- `check_vector_search_availability()` - Проверяет доступность тулз через `/health`
- `perform_initial_indexing()` - Запускает начальную индексацию
- `check_and_reindex_changes()` - Проверяет изменения и запускает реиндексацию
- `start_monitoring()` - Запускает фоновый мониторинг (каждые 5 минут)
- `trigger_reindex()` - Вручную запускает проверку и реиндексацию
- `shutdown()` - Корректно завершает работу менеджера

**Важные особенности:**

- **Событийная реиндексация:** Подписывается на события изменения KB (создание, изменение, удаление файлов)
- **Батчинг изменений:** Множественные изменения в течение 2 секунд объединяются в одну реиндексацию
- **Защита от конкурентности:** Использует async lock для предотвращения одновременных реиндексаций
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

1. **`vector_search`** - Семантический поиск в базе знаний
   - `query` (string) - Поисковый запрос
   - `top_k` (int) - Количество результатов (default: 5)
   - `user_id` (int, optional) - ID пользователя

2. Reindex is triggered by the bot container and is not exposed to agents

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

#### VectorSearchManager (`src/vector_search/manager.py`)

Основной менеджер векторного поиска:

**Компоненты:**

- **Embedder** - Создание векторных представлений (sentence-transformers/openai/infinity)
- **VectorStore** - Хранение векторов (FAISS/Qdrant)
- **Chunker** - Разбиение документов на чанки
- **Index Metadata** - Отслеживание индексированных файлов

**Инкрементальная индексация:**

- Хранит хеши файлов в `metadata.json`
- При индексации проверяет изменения
- Индексирует только новые/измененные файлы
- Полная реиндексация при изменении конфигурации

**Обработка удаленных файлов:**

- **Qdrant (поддерживает удаление):** Удаляет векторы по фильтру `file_path` инкрементально
- **FAISS (не поддерживает удаление):** Автоматически переключается на полную реиндексацию при обнаружении удаленных файлов
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

### Change Detection and Reindexing

1. **Событийный мониторинг** (основной механизм)
   ```
   KB событие (create/modify/delete) 
   → BotVectorSearchManager._handle_kb_change_event()
   → Батчинг изменений (2 секунды)
   → check_and_reindex_changes()
   → Сканирование файлов
   → Вычисление хешей
   → Сравнение с предыдущими хешами
   → Обнаружение: added, modified, deleted
   → Вызов MCP reindex_vector
   ```

2. **Фоновый мониторинг** (fallback, каждые 5 минут)
   ```
   BotVectorSearchManager.start_monitoring()
   → Периодическая проверка изменений
   → Для случаев, не покрытых событиями (NFS, внешние изменения)
   ```

3. **Обработка изменений в VectorSearchManager**
   ```
   При обнаружении изменений:
   
   Added/Modified файлы:
   → Индексируются инкрементально
   → Добавляются в vector store
   
   Deleted файлы (Qdrant):
   → delete_by_filter({"file_path": path})
   → Удаляются из metadata
   
   Deleted файлы (FAISS):
   → force=True → full reindex
   → Очистка store → переиндексация всех файлов
   
   → Сохранение новых хешей и metadata
   ```

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
