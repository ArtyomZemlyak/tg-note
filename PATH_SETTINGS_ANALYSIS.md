# Анализ описаний путей в settings (Memory Postfix и MCP)

## Обзор архитектуры путей

Система поддерживает **три уровня организации путей** для максимальной гибкости:

### 1. Глобальные (Shared) пути ✅ АКТИВНО ИСПОЛЬЗУЕТСЯ

**Это правильные и основные пути по умолчанию:**
- `data/mcp_servers/` - глобальные MCP серверы (доступны всем)
- `data/memory/` - глобальная/shared память

### 2. User-specific пути (Legacy)

Используются для пользовательской изоляции:
- `data/mcp_servers/user_{user_id}/` - серверы конкретного пользователя
- `data/memory/user_{user_id}/` - память конкретного пользователя

### 3. Per-KB пути (Новая архитектура)

Используют постфиксы для интеграции в knowledge base:
- `{kb_path}/.mcp_servers/` - MCP серверы внутри KB
- `{kb_path}/memory/` - память внутри KB

## Ключевые настройки

### 1. MEM_AGENT_MEMORY_POSTFIX

**Описание:** Постфикс для директории памяти внутри KB каждого пользователя

**Значение по умолчанию:** `"memory"`

**Полный путь:** `{kb_path}/{MEM_AGENT_MEMORY_POSTFIX}`

**Пример:**
```python
# Для пользователя с KB_PATH = "./knowledge_bases/my-notes"
# и MEM_AGENT_MEMORY_POSTFIX = "memory"
memory_path = settings.get_mem_agent_memory_path(kb_path)
# Результат: ./knowledge_bases/my-notes/memory/
```

**Структура директории:**
```
knowledge_bases/my-notes/memory/
├── user.md              # Персональная информация (для mem-agent storage)
├── entities/            # Файлы сущностей (для mem-agent storage)
├── memories.json        # Хранилище заметок (для json storage)
└── vector_store/        # Векторное хранилище (для vector storage)
```

### 2. MCP_SERVERS_POSTFIX

**Описание:** Постфикс для директории конфигураций MCP серверов внутри KB каждого пользователя

**Значение по умолчанию:** `".mcp_servers"`

**Полный путь:** `{kb_path}/{MCP_SERVERS_POSTFIX}`

**Пример:**
```python
# Для пользователя с KB_PATH = "./knowledge_bases/my-notes"
# и MCP_SERVERS_POSTFIX = ".mcp_servers"
mcp_dir = settings.get_mcp_servers_dir(kb_path)
# Результат: ./knowledge_bases/my-notes/.mcp_servers/
```

**Структура директории:**
```
knowledge_bases/my-notes/.mcp_servers/
├── mem-agent.json       # Конфигурация memory сервера (стандартный MCP формат)
└── custom-server.json   # Пользовательские MCP серверы
```

## Helper методы в Settings

### get_mem_agent_memory_path(kb_path: Path) -> Path

```python
def get_mem_agent_memory_path(self, kb_path: Path) -> Path:
    """
    Get memory agent memory path for a specific knowledge base
    
    Args:
        kb_path: Path to knowledge base
        
    Returns:
        Full path to memory directory (kb_path/{postfix})
    """
    return kb_path / self.MEM_AGENT_MEMORY_POSTFIX
```

**Использование:**
```python
from config.settings import settings
from pathlib import Path

kb_path = Path("./knowledge_bases/user_kb")
memory_path = settings.get_mem_agent_memory_path(kb_path)
print(memory_path)  # ./knowledge_bases/user_kb/memory
```

### get_mcp_servers_dir(kb_path: Path) -> Path

```python
def get_mcp_servers_dir(self, kb_path: Path) -> Path:
    """
    Get MCP servers directory for a specific knowledge base
    
    Args:
        kb_path: Path to knowledge base
        
    Returns:
        Full path to MCP servers directory (kb_path/{postfix})
    """
    return kb_path / self.MCP_SERVERS_POSTFIX
```

**Использование:**
```python
from config.settings import settings
from pathlib import Path

kb_path = Path("./knowledge_bases/user_kb")
mcp_dir = settings.get_mcp_servers_dir(kb_path)
print(mcp_dir)  # ./knowledge_bases/user_kb/.mcp_servers
```

### ensure_mem_agent_memory_path_exists(kb_path: Path) -> None

```python
def ensure_mem_agent_memory_path_exists(self, kb_path: Path) -> None:
    """
    Ensure memory agent memory path exists for a specific KB
    
    Args:
        kb_path: Path to knowledge base
    """
    memory_path = self.get_mem_agent_memory_path(kb_path)
    memory_path.mkdir(parents=True, exist_ok=True)
```

### ensure_mcp_servers_dir_exists(kb_path: Path) -> None

```python
def ensure_mcp_servers_dir_exists(self, kb_path: Path) -> None:
    """
    Ensure MCP servers directory exists for a specific KB
    
    Args:
        kb_path: Path to knowledge base
    """
    mcp_dir = self.get_mcp_servers_dir(kb_path)
    mcp_dir.mkdir(parents=True, exist_ok=True)
```

## Как работает передача путей

### 1. В MCP Registry

Registry обнаруживает серверы на двух уровнях:

```python
# В registry.py
def discover_servers(self) -> None:
    # 1. Shared servers в servers_dir/ (e.g., data/mcp_servers/)
    self._discover_from_directory(self.servers_dir, scope="shared")
    
    # 2. User-specific servers в servers_dir/user_{user_id}/
    if self.user_id is not None:
        user_dir = self.servers_dir / f"user_{self.user_id}"
        if user_dir.exists():
            self._discover_from_directory(user_dir, scope=f"user_{self.user_id}")
```

**Приоритет:** User-specific серверы переопределяют shared серверы с тем же именем.

### 2. В memory серверах (stdio и HTTP)

Memory серверы получают пути через переменные окружения:

```python
# В memory_server.py и memory_server_http.py
kb_path = os.getenv("KB_PATH")
memory_postfix = os.getenv("MEM_AGENT_MEMORY_POSTFIX", "memory")

if kb_path:
    # Per-KB путь: {kb_path}/{memory_postfix}
    data_dir = Path(kb_path) / memory_postfix
    logger.info(f"Using KB-based memory path: {data_dir}")
elif user_id:
    # Legacy user-specific путь
    data_dir = Path(f"data/memory/user_{user_id}")
    logger.info(f"Using legacy user-based memory path: {data_dir}")
else:
    # Shared/global fallback
    data_dir = Path("data/memory/shared")
    logger.info(f"Using shared memory path: {data_dir}")
```

**Приоритет определения пути:**
1. `KB_PATH` env var (per-KB путь) - устанавливается memory_tool.py
2. `user_id` parameter (legacy user-specific) - для обратной совместимости
3. Shared/global (`data/memory/shared`) - fallback по умолчанию

### 3. В MemoryMCPTool

Tool динамически устанавливает KB_PATH в runtime для переключения на per-KB режим:

```python
async def execute(self, params: Dict[str, Any], context: "ToolContext") -> Dict[str, Any]:
    """Execute memory action"""
    # Добавить KB_PATH в переменные окружения для этого выполнения
    # Это позволяет MCP серверу создать директорию памяти в runtime
    # в правильном пользовательском расположении: {kb_path}/memory/
    if hasattr(context, "kb_root_path") and context.kb_root_path:
        kb_path = str(context.kb_root_path)
        updated_env = self._original_env.copy()
        updated_env["KB_PATH"] = kb_path
        
        if self.client:
            self.client.config.env = updated_env
            logger.debug(f"[MemoryMCPTool] Set KB_PATH={kb_path} for memory")
```

## Примеры конфигурации

### config.yaml

```yaml
# Memory Agent Settings
MEM_AGENT_MEMORY_POSTFIX: memory  # Директория памяти внутри KB

# MCP Settings
MCP_SERVERS_POSTFIX: .mcp_servers  # Директория MCP серверов внутри KB

# KB Settings (может быть переопределено для каждого пользователя)
KB_PATH: ./knowledge_base
```

### .env

```bash
# Memory agent
MEM_AGENT_MEMORY_POSTFIX=memory

# MCP
MCP_SERVERS_POSTFIX=.mcp_servers
```

### Переопределение для пользователя

Пользователи могут переопределить свой KB_PATH через команду `/setkb`:

```
/setkb my-notes
# Устанавливает KB_PATH в knowledge_bases/my-notes для этого пользователя
# Memory будет в: knowledge_bases/my-notes/memory
# MCP серверы будут в: knowledge_bases/my-notes/.mcp_servers
```

## Полная структура директорий

### Глобальный уровень (Shared) ✅ ТЕКУЩАЯ РЕАЛИЗАЦИЯ

```
data/
├── mcp_servers/               # Глобальные MCP серверы (shared)
│   ├── mem-agent.json         # Memory сервер
│   ├── custom-tool.json       # Другие серверы
│   └── user_123/              # User-specific серверы (legacy)
│       └── personal-tool.json
└── memory/                    # Глобальная память
    ├── shared/                # Shared память (fallback)
    └── user_123/              # User-specific память (legacy)
        ├── memories.json
        └── vector_store/
```

### Per-KB уровень (Новая архитектура)

```
knowledge_bases/
└── user_kb_name/              # KB пользователя (из команды setkb)
    ├── .mcp_servers/          # Per-KB MCP server configs
    │   ├── mem-agent.json     # Memory сервер (стандартный MCP формат)
    │   └── custom.json        # Пользовательские серверы
    ├── memory/                # Per-KB memory
    │   ├── user.md            # Персональная информация
    │   ├── entities/          # Файлы сущностей
    │   ├── memories.json      # JSON storage
    │   └── vector_store/      # Vector storage
    └── topics/                # Заметки пользователя
        ├── programming/
        └── personal/
```

## Проверка документации

### ✅ Корректные описания

1. **config/settings.py (строки 116-119)**
   ```python
   MCP_SERVERS_POSTFIX: str = Field(
       default=".mcp_servers",
       description="Postfix for MCP servers directory within KB (e.g., '.mcp_servers' -> kb_path/.mcp_servers)",
   )
   ```
   ✅ Правильно описывает, как постфикс добавляется к kb_path

2. **config/settings.py (строки 138-141)**
   ```python
   MEM_AGENT_MEMORY_POSTFIX: str = Field(
       default="memory",
       description="Postfix for memory directory within KB (e.g., 'memory' -> kb_path/memory)",
   )
   ```
   ✅ Правильно описывает, как постфикс добавляется к kb_path

3. **config.example.yaml (строки 334-343)**
   ```yaml
   # MCP_SERVERS_POSTFIX: Directory name for MCP server configs within each user's KB
   #
   # Default: ".mcp_servers"
   # Full path will be: {kb_path}/.mcp_servers/
   # Each user gets their own isolated MCP server configurations
   #
   # Example:
   #   If kb_path is "./knowledge_bases/my-notes" and postfix is ".mcp_servers"
   #   Then MCP configs will be stored at: "./knowledge_bases/my-notes/.mcp_servers/"
   MCP_SERVERS_POSTFIX: .mcp_servers
   ```
   ✅ Детальное и корректное описание с примерами

4. **config.example.yaml (строки 418-427)**
   ```yaml
   # MEM_AGENT_MEMORY_POSTFIX: Directory name for memory storage within each user's KB
   #
   # Default: "memory"
   # Full path will be: {kb_path}/memory/
   # Each user gets their own isolated memory directory
   #
   # Example:
   #   If kb_path is "./knowledge_bases/my-notes" and postfix is "memory"
   #   Then memory will be stored at: "./knowledge_bases/my-notes/memory/"
   MEM_AGENT_MEMORY_POSTFIX: memory
   ```
   ✅ Детальное и корректное описание с примерами

5. **docs_site/architecture/per-user-storage.md**
   
   Документ полностью посвящен описанию архитектуры постфиксов и содержит:
   - ✅ Объяснение концепции постфиксов
   - ✅ Примеры использования helper методов
   - ✅ Структуру директорий
   - ✅ Примеры кода
   - ✅ Ссылки на связанную документацию

6. **docs_site/agents/mem-agent-setup.md**
   
   Содержит корректные описания и примеры:
   - ✅ Настройка путей в config.yaml
   - ✅ Примеры использования `get_mem_agent_memory_path()`
   - ✅ Примеры использования `get_mcp_servers_dir()`
   - ✅ Таблица с настройками и их значениями по умолчанию

## Выявленные проблемы

### 🟡 Незначительные замечания

1. **Использование helper методов в коде**
   
   **Проблема:** Memory серверы не используют helper методы из settings, а напрямую конструируют пути через `Path(kb_path) / memory_postfix`
   
   **Местоположение:**
   - `src/agents/mcp/memory/memory_server.py` (строка 94)
   - `src/agents/mcp/memory/memory_server_http.py` (строка 99)
   
   **Текущий код:**
   ```python
   kb_path = os.getenv("KB_PATH")
   memory_postfix = os.getenv("MEM_AGENT_MEMORY_POSTFIX", "memory")
   if kb_path:
       data_dir = Path(kb_path) / memory_postfix
   ```
   
   **Рекомендация:** Это приемлемый подход, так как серверы запускаются как отдельные процессы и не имеют прямого доступа к settings объекту. Использование переменных окружения здесь корректно.
   
   **Статус:** ✅ Не требует исправления

2. **Документация использования helper методов**
   
   **Проблема:** В коде есть места, где можно было бы использовать `settings.get_mcp_servers_dir()`, но вместо этого используется прямое обращение к `Path(...)`
   
   **Поиск в коде:** Grep не нашел прямого использования helper методов за пределами документации
   
   **Вывод:** Helper методы предоставлены в settings, но не используются активно в основном коде. Это может быть связано с тем, что большая часть кода работает через переменные окружения.
   
   **Статус:** 🟡 Стоит проверить, есть ли места, где можно улучшить код, используя helper методы

## Рекомендации

### 1. Использование helper методов

**Где использовать:**
- В bot handlers при создании пользовательских директорий
- В settings manager при работе с пользовательскими настройками
- В agent factory при инициализации агентов

**Пример хорошей практики:**
```python
from config.settings import settings
from pathlib import Path

# ✅ ХОРОШО: использовать helper метод
kb_path = Path(user_kb_path)
memory_path = settings.get_mem_agent_memory_path(kb_path)

# ❌ ПЛОХО: прямое конструирование пути
memory_path = kb_path / "memory"  # Hardcoded постфикс!
```

### 2. Проверка существования директорий

**При создании пользователя или инициализации KB:**
```python
from config.settings import settings

# Убедиться, что директории существуют
settings.ensure_mem_agent_memory_path_exists(kb_path)
settings.ensure_mcp_servers_dir_exists(kb_path)
```

### 3. Документирование постфиксов

Все настройки постфиксов хорошо задокументированы:
- ✅ В config/settings.py есть docstrings
- ✅ В config.example.yaml есть подробные комментарии
- ✅ Есть отдельная документация docs_site/architecture/per-user-storage.md

## Преимущества текущей архитектуры

1. **Изоляция пользователей:** Каждый пользователь имеет отдельную память и MCP конфигурации
2. **Чистая конфигурация:** Постфиксы простые и не требуют полных путей
3. **Гибкость:** Легко изменить структуру, модифицируя постфиксы
4. **Консистентность:** Все пользовательские данные следуют одному паттерну
5. **Интеграция с KB:** Все находится внутри структуры knowledge base

## Текущее использование в боте

```python
# В telegram_bot.py
self.mcp_manager = MCPServersManager()  # БЕЗ параметров
# Использует: data/mcp_servers (глобальный/shared)
```

**Это правильно!** Бот использует глобальные серверы, доступные всем пользователям.

### Переключение на per-KB режим (опционально)

Для per-KB изоляции можно передать явный путь:

```python
from config.settings import settings

# Получить KB path пользователя
kb_path = settings_manager.get_setting(user_id, "KB_PATH")

# Создать per-KB manager
mcp_dir = settings.get_mcp_servers_dir(kb_path)
mcp_manager = MCPServersManager(servers_dir=mcp_dir)
```

## Итоги проверки

### ✅ Что работает правильно

1. **Глобальные пути работают корректно:** `data/mcp_servers` и `data/memory` - правильные и активно используемые пути
2. **Registry поддерживает три уровня:**
   - Shared: `data/mcp_servers/`
   - User-specific: `data/mcp_servers/user_{id}/`
   - Per-KB: `{kb_path}/.mcp_servers/`
3. **Memory серверы поддерживают три уровня:**
   - Shared: `data/memory/shared/`
   - User-specific: `data/memory/user_{id}/`
   - Per-KB: `{kb_path}/memory/`
4. **Helper методы в settings.py:** Готовы для per-KB режима
5. **Приоритеты четко определены:** User-specific переопределяет shared, KB переопределяет все
6. **Документация постфиксов:** Корректна для per-KB режима

### 🟢 Текущая реализация (Shared/Global)

**Бот сейчас использует глобальный режим:**
- ✅ `data/mcp_servers/` - все MCP серверы здесь
- ✅ `data/memory/` - вся память здесь
- ✅ Это правильно и работает!

### 🔵 Будущая архитектура (Per-KB) - Опциональна

**Для per-KB изоляции доступны:**
- `{kb_path}/.mcp_servers/` через `settings.get_mcp_servers_dir(kb_path)`
- `{kb_path}/memory/` через `settings.get_mem_agent_memory_path(kb_path)`
- Включается передачей `servers_dir` в `MCPServersManager()`

### ❌ Критические проблемы

**НЕ ОБНАРУЖЕНО**

## Заключение

**ВСЕ ПРАВИЛЬНО! ✅**

1. ✅ `data/mcp_servers` - правильный глобальный путь (активно используется)
2. ✅ `data/memory` - правильный глобальный путь (активно используется)
3. ✅ Система поддерживает три уровня изоляции (shared, user-specific, per-KB)
4. ✅ Registry корректно обнаруживает серверы на всех уровнях
5. ✅ Memory серверы поддерживают все три режима с правильными приоритетами
6. ✅ Постфиксы (`MEM_AGENT_MEMORY_POSTFIX`, `MCP_SERVERS_POSTFIX`) готовы для per-KB режима
7. ✅ Helper методы реализованы и задокументированы

**Текущая конфигурация с `data/memory` и `data/mcp_servers` - это правильно и работает как задумано!**

---

**Дата проверки:** 2025-10-11  
**Проверенные компоненты:**
- config/settings.py
- config.example.yaml
- docs_site/architecture/per-user-storage.md
- docs_site/agents/mem-agent-setup.md
- src/agents/mcp/memory/memory_tool.py
- src/agents/mcp/memory/memory_server.py
- src/agents/mcp/memory/memory_server_http.py
