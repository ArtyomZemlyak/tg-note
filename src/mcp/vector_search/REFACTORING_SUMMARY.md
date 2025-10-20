# Vector Search Refactoring Summary

## Дата: 2025-10-20

## Цель рефакторинга

Устранить дублирование кода между `src/mcp/vector_search/manager.py` и `src/bot/vector_search_manager.py` и четко разделить ответственность между MCP HUB и BOT.

## Проблема

До рефакторинга:
- Оба менеджера отслеживали хэши файлов
- Оба сканировали knowledge base
- Оба управляли метаданными
- Дублирование функциональности обнаружения изменений

## Решение

Четкое разделение ответственности:

### MCP HUB (WHAT - Что делать)
**Файл:** `src/mcp/vector_search/manager.py`

**Предоставляет функциональность:**
- ✅ **Поиск** - `search(query, top_k)`
- ✅ **Полная индексация** - `index_knowledge_base(force)`
- ✅ **CRUD операции** (новые):
  - `add_documents_by_paths(file_paths)` - добавить документы
  - `delete_documents_by_paths(file_paths)` - удалить документы
  - `update_documents_by_paths(file_paths)` - обновить документы
- ✅ **Управление метаданными** - отслеживание хэшей файлов, config hash
- ✅ **Embeddings & Vector Store** - работа с векторной БД

### BOT (WHEN - Когда делать)
**Файл:** `src/bot/vector_search_manager.py`

**Принимает решения:**
- ✅ Мониторинг изменений в KB (события + периодическая проверка)
- ✅ Обнаружение изменений (added/modified/deleted files)
- ✅ **Принятие решений** когда вызывать MCP Hub:
  - Новые файлы → `add_vector_documents`
  - Измененные файлы → `update_vector_documents`
  - Удаленные файлы → `delete_vector_documents`
- ✅ Tracking file hashes для обнаружения изменений

**НЕ делает:**
- ❌ Эмбеддинги
- ❌ Управление векторной БД
- ❌ Индексацию

## Изменения в коде

### 1. MCP HUB Server (`src/mcp/mcp_hub_server.py`)

**Добавлены новые MCP tools:**
```python
@mcp.tool()
async def add_vector_documents(file_paths: List[str], user_id: int = None) -> dict

@mcp.tool()
async def delete_vector_documents(file_paths: List[str], user_id: int = None) -> dict

@mcp.tool()
async def update_vector_documents(file_paths: List[str], user_id: int = None) -> dict
```

**Обновлен список доступных tools:**
```python
def get_builtin_tools():
    if check_vector_search_availability():
        tools.extend([
            "vector_search",
            "reindex_vector",
            "add_vector_documents",      # НОВЫЙ
            "delete_vector_documents",   # НОВЫЙ
            "update_vector_documents",   # НОВЫЙ
        ])
```

### 2. VectorSearchManager (`src/mcp/vector_search/manager.py`)

**Добавлены CRUD методы:**
```python
async def add_documents_by_paths(self, file_paths: List[str]) -> Dict[str, Any]
async def delete_documents_by_paths(self, file_paths: List[str]) -> Dict[str, Any]
async def update_documents_by_paths(self, file_paths: List[str]) -> Dict[str, Any]
```

### 3. BotVectorSearchManager (`src/bot/vector_search_manager.py`)

**Обновлен метод `check_and_reindex_changes()`:**
- Теперь вызывает конкретные CRUD операции вместо полной реиндексации
- Для новых файлов → `_call_mcp_add_documents()`
- Для измененных → `_call_mcp_update_documents()`
- Для удаленных → `_call_mcp_delete_documents()`

**Добавлены методы вызова MCP Hub:**
```python
async def _call_mcp_add_documents(self, file_paths: List[str]) -> bool
async def _call_mcp_delete_documents(self, file_paths: List[str]) -> bool
async def _call_mcp_update_documents(self, file_paths: List[str]) -> bool
```

**Обновлена проверка доступности:**
```python
async def check_vector_search_availability(self) -> bool:
    # Теперь проверяет все 5 инструментов:
    # - vector_search
    # - reindex_vector
    # - add_vector_documents
    # - delete_vector_documents
    # - update_vector_documents
```

### 4. Документация

Обновлен файл `docs_site/architecture/vector-search-mcp-integration.md`:
- Добавлено описание разделения ответственности
- Обновлены диаграммы
- Описаны новые CRUD операции
- Добавлены примеры использования

### 5. Тесты

Обновлен файл `tests/test_bot_vector_search.py`:
- Проверка наличия всех 5 инструментов
- Обновлены моки для новых операций

## Преимущества

1. **Отсутствие дублирования** - каждая функциональность в одном месте
2. **Четкое разделение ответственности** - понятно кто за что отвечает
3. **Инкрементальные обновления** - быстрее полной реиндексации
4. **Масштабируемость** - легко добавлять новые операции
5. **Тестируемость** - проще тестировать отдельные компоненты

## Совместимость

- ✅ Обратная совместимость сохранена
- ✅ Старые методы (`reindex_vector`) по-прежнему работают
- ✅ Инкрементальные обновления работают для Qdrant
- ✅ Для FAISS fallback на полную реиндексацию

## Миграция

Не требуется никаких действий для существующих установок:
- BOT автоматически обнаружит новые инструменты через `/health`
- MCP Hub автоматически зарегистрирует новые tools
- Существующие индексы совместимы
