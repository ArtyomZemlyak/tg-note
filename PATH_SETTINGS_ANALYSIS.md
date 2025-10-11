# Анализ описаний путей в settings (Memory Postfix и MCP)

## Обзор архитектуры путей

Система использует **подход на основе постфиксов** для создания пользовательских путей внутри knowledge bases. Вместо жестко заданных глобальных путей, настройки определяют постфиксы, которые добавляются к пути KB каждого пользователя.

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

### 1. В memory серверах (stdio и HTTP)

Memory серверы получают пути через переменные окружения:

```python
# В memory_server.py и memory_server_http.py
kb_path = os.getenv("KB_PATH")
memory_postfix = os.getenv("MEM_AGENT_MEMORY_POSTFIX", "memory")

if kb_path:
    # Использовать KB-based путь: {kb_path}/{memory_postfix}
    data_dir = Path(kb_path) / memory_postfix
    logger.info(f"Using KB-based memory path: {data_dir}")
```

**Приоритет определения пути:**
1. `KB_PATH` env var (устанавливается memory_tool.py для специфичного пользователя)
2. Legacy user_id-based путь (для обратной совместимости)
3. Shared memory (fallback)

### 2. В MemoryMCPTool

Tool динамически устанавливает KB_PATH в runtime для каждого пользователя:

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

## Структура директорий для пользователя

```
knowledge_bases/
└── user_kb_name/              # KB пользователя (из команды setkb)
    ├── .mcp_servers/          # Per-user MCP server configs
    │   ├── mem-agent.json     # Memory сервер (стандартный MCP формат)
    │   └── custom.json        # Пользовательские серверы
    ├── memory/                # Per-user memory
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

## Итоги проверки

### ✅ Что работает правильно

1. **Определение постфиксов в settings.py:** Правильные значения по умолчанию и описания
2. **Helper методы:** Корректно реализованы и следуют single responsibility principle
3. **Документация:** Подробная и точная в config.example.yaml
4. **Архитектурная документация:** Отличное описание в per-user-storage.md
5. **Передача через ENV vars:** Корректный подход для изоляции процессов
6. **Динамическая установка KB_PATH:** MemoryMCPTool правильно устанавливает путь в runtime

### 🟡 Что можно улучшить

1. **Активное использование helper методов:** Можно найти места в коде, где прямое конструирование путей можно заменить на helper методы
2. **Примеры в коде:** Добавить больше примеров использования в docstrings

### ❌ Критические проблемы

**НЕ ОБНАРУЖЕНО**

## Заключение

Архитектура путей для memory (постфикс `memory`) и MCP (постфикс `.mcp_servers`) реализована **корректно и следует best practices**:

1. ✅ Использование постфиксов вместо жестко заданных путей
2. ✅ Per-user изоляция через KB path
3. ✅ Helper методы для безопасного конструирования путей
4. ✅ Корректная передача через переменные окружения
5. ✅ Подробная и точная документация
6. ✅ Консистентная структура для всех пользовательских данных

**Система работает правильно и не требует исправлений.**

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
