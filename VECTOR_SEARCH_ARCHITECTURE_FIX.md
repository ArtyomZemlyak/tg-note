# Vector Search Architecture Fix - SOLID Principles

## ✅ РЕАЛИЗОВАНО

Архитектура полностью переработана согласно принципам SOLID.

## Проблема (до исправления)

**Текущая (неправильная) архитектура:**
```
MCP HUB контейнер:
- ❌ НЕТ доступа к knowledge_base (volume не проброшен)
- ❌ Пытается читать файлы через file_paths
- ❌ Нарушает SOLID принципы

BOT контейнер:
- ✅ Имеет доступ к knowledge_base
- ❌ Отправляет только пути к файлам в MCP HUB
```

## SOLID Принципы

### 1. Single Responsibility Principle (SRP)
- **BOT** - отвечает за работу с файловой системой (чтение, мониторинг)
- **MCP HUB** - отвечает за векторные операции (embeddings, vector DB)

### 2. Dependency Inversion Principle (DIP)
- MCP HUB не должен зависеть от файловой системы
- MCP HUB работает с абстракциями (документы как данные)

### 3. Interface Segregation Principle (ISP)
- Четкий контракт данных между BOT и MCP HUB
- BOT отправляет структурированные данные, не пути

## Правильная архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      BOT Container                          │
│  (имеет доступ к knowledge_base volume)                     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  BotVectorSearchManager                              │  │
│  │                                                      │  │
│  │  Responsibilities (FILE I/O):                        │  │
│  │  1. Мониторинг файлов KB                            │  │
│  │  2. ЧТЕНИЕ файлов                                   │  │
│  │  3. Извлечение контента                             │  │
│  │  4. Подготовка структуры данных                     │  │
│  │  5. Отправка ДАННЫХ в MCP HUB                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           │ HTTP/MCP                        │
│                           │ Отправляет ДАННЫЕ:              │
│                           │ {                               │
│                           │   "documents": [                │
│                           │     {                           │
│                           │       "id": "path/to/file.md",  │
│                           │       "content": "...",         │
│                           │       "metadata": {...}         │
│                           │     }                           │
│                           │   ]                             │
│                           │ }                               │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     MCP HUB Container                       │
│  (НЕТ доступа к knowledge_base)                             │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  VectorSearchManager                                 │  │
│  │                                                      │  │
│  │  Responsibilities (VECTOR OPERATIONS):               │  │
│  │  1. Получение ДАННЫХ (не путей!)                    │  │
│  │  2. Chunking контента                               │  │
│  │  3. Creating embeddings                             │  │
│  │  4. Управление Vector DB                            │  │
│  │  5. Поиск по векторам                               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Новый контракт данных

### Document Structure (отправляется из BOT в MCP HUB)

```python
from typing import TypedDict, List, Optional, Dict, Any

class DocumentData(TypedDict):
    """
    Структура документа для передачи из BOT в MCP HUB

    AICODE-NOTE: BOT читает файлы и отправляет контент,
    MCP HUB работает только с данными
    """
    id: str                    # Уникальный ID (например, относительный путь)
    content: str               # Содержимое документа (текст)
    metadata: Dict[str, Any]   # Метаданные (file_name, file_path, etc.)

class VectorDocumentsBatch(TypedDict):
    """Пакет документов для batch операций"""
    documents: List[DocumentData]
```

## Новые MCP Tools Signatures

### 1. add_vector_documents

```python
@mcp.tool()
async def add_vector_documents(documents: List[Dict[str, Any]]) -> dict:
    """
    Add documents to vector index

    Args:
        documents: List of documents with structure:
            - id (str): Unique document ID
            - content (str): Document text content
            - metadata (dict): Additional metadata

    Returns:
        Operation statistics
    """
```

### 2. delete_vector_documents

```python
@mcp.tool()
async def delete_vector_documents(document_ids: List[str]) -> dict:
    """
    Delete documents from vector index

    Args:
        document_ids: List of document IDs to delete

    Returns:
        Operation statistics
    """
```

### 3. update_vector_documents

```python
@mcp.tool()
async def update_vector_documents(documents: List[Dict[str, Any]]) -> dict:
    """
    Update documents in vector index

    Args:
        documents: List of documents (same structure as add)

    Returns:
        Operation statistics
    """
```

## Implementation Changes

### MCP HUB Changes

**VectorSearchManager:**
```python
class VectorSearchManager:
    # УДАЛИТЬ зависимость от kb_root_path!
    def __init__(
        self,
        embedder: BaseEmbedder,
        vector_store: BaseVectorStore,
        chunker: DocumentChunker,
        index_path: Optional[Path] = None,  # Только для индекса
    ):
        # БЕЗ kb_root_path!

    # НОВЫЕ методы - принимают ДАННЫЕ, не пути
    async def add_documents(
        self,
        documents: List[DocumentData]
    ) -> Dict[str, Any]:
        """Принимает готовые данные, не читает файлы"""

    async def delete_documents(
        self,
        document_ids: List[str]
    ) -> Dict[str, Any]:
        """Удаляет по ID, не по путям"""

    async def update_documents(
        self,
        documents: List[DocumentData]
    ) -> Dict[str, Any]:
        """Обновляет из данных"""
```

### BOT Changes

**BotVectorSearchManager:**
```python
class BotVectorSearchManager:
    async def check_and_reindex_changes(self) -> bool:
        """
        1. Обнаружить изменения (added/modified/deleted)
        2. ПРОЧИТАТЬ файлы
        3. Подготовить DocumentData
        4. Отправить в MCP HUB
        """
        changes = self._detect_changes(previous, current)

        # Для новых файлов
        if changes.added:
            documents = []
            for file_path in changes.added:
                # ЧИТАЕМ файл
                content = self._read_file(file_path)
                # Создаем структуру данных
                doc = DocumentData(
                    id=file_path,
                    content=content,
                    metadata={"file_path": file_path, ...}
                )
                documents.append(doc)

            # Отправляем ДАННЫЕ, не пути
            await self._call_mcp_add_documents(documents)

        # Аналогично для modified и deleted
```

## Преимущества

### 1. SOLID Compliance ✅

- **SRP**: Каждый компонент отвечает за свою область
- **DIP**: MCP HUB не зависит от файловой системы
- **ISP**: Четкий интерфейс передачи данных

### 2. Масштабируемость ✅

- MCP HUB может работать с любыми источниками данных
- Не только файлы, но и API, БД, и т.д.

### 3. Тестируемость ✅

- MCP HUB легко тестировать с моками данных
- Не нужны файлы для тестов

### 4. Deployment Flexibility ✅

- MCP HUB не требует volume для KB
- Можно разделить на разные серверы

## Migration Path

1. ✅ Создать новые типы данных (DocumentData, etc.)
2. ✅ Обновить VectorSearchManager - убрать kb_root_path
3. ✅ Обновить MCP tools - принимать данные вместо путей
4. ✅ Обновить BOT - читать файлы и отправлять данные
5. ✅ Обновить тесты
6. ✅ Обновить документацию
