# Архитектура путей - Исправлено

## Дата: 2025-10-11

## Проблема
Ранее была неправильная архитектура с per-KB путями через постфиксы (`MCP_SERVERS_POSTFIX`, `MEM_AGENT_MEMORY_POSTFIX`), которая позволяла shared memory и нарушала изоляцию пользователей.

## Решение

### ✅ Правильная архитектура путей

#### 1. **Memory (Память)** - СТРОГАЯ изоляция по user_id

**Путь:** `data/memory/user_{user_id}/`

**Правила:**
- ❌ НЕТ shared memory
- ❌ НЕТ per-KB путей 
- ✅ ТОЛЬКО per-user: `data/memory/user_{user_id}/`
- ✅ user_id обязателен для всех операций с памятью

**Причина:** Память - это результат действий пользователя, не должна влиять на других.

#### 2. **MCP Servers** - Shared + User override

**Пути:**
- `data/mcp_servers/` - shared серверы (доступны всем)
- `data/mcp_servers/user_{user_id}/` - user-specific (переопределяют shared)

**Правила:**
- ✅ Shared MCP серверы разрешены (это инструменты, не данные)
- ✅ User-specific серверы переопределяют shared
- ✅ Registry автоматически обнаруживает оба уровня

**Причина:** MCP серверы - это инструменты (как калькулятор), могут быть общими.

## Изменения в коде

### 1. Удалено из `config/settings.py`:

```python
# ❌ УДАЛЕНО
MCP_SERVERS_POSTFIX: str = Field(default=".mcp_servers", ...)
MEM_AGENT_MEMORY_POSTFIX: str = Field(default="memory", ...)

def get_mcp_servers_dir(self, kb_path: Path) -> Path: ...
def get_mem_agent_memory_path(self, kb_path: Path) -> Path: ...
def ensure_mcp_servers_dir_exists(self, kb_path: Path) -> None: ...
def ensure_mem_agent_memory_path_exists(self, kb_path: Path) -> None: ...
```

```python
# ✅ ДОБАВЛЕНО (для работы с user_id)
def get_mem_agent_memory_dir(self, user_id: int) -> Path:
    """Get memory directory: data/memory/user_{user_id}"""
    return Path(f"data/memory/user_{user_id}")

def ensure_mem_agent_memory_dir_exists(self, user_id: int) -> None:
    """Ensure memory directory exists for user"""
    memory_dir = self.get_mem_agent_memory_dir(user_id)
    memory_dir.mkdir(parents=True, exist_ok=True)
```

### 2. Исправлено `src/agents/mcp/memory/memory_server_http.py`:

**Было (НЕПРАВИЛЬНО):**
```python
# Global storage
storage: Optional[MemoryStorage] = None

def init_storage(user_id: Optional[int] = None):
    kb_path = os.getenv("KB_PATH")  # ❌ Per-KB путь
    if kb_path:
        data_dir = Path(kb_path) / memory_postfix
    elif user_id:
        data_dir = Path(f"data/memory/user_{user_id}")
    else:
        data_dir = Path("data/memory/shared")  # ❌ Shared!
```

**Стало (ПРАВИЛЬНО):**
```python
# Per-user storage cache
_storages: Dict[int, MemoryStorage] = {}

def get_storage(user_id: int) -> MemoryStorage:
    """Get or create storage for user (required)"""
    if not user_id:
        raise ValueError("user_id required")  # ✅ Обязателен!
    
    if user_id in _storages:
        return _storages[user_id]
    
    # ✅ ТОЛЬКО user-specific путь
    data_dir = Path(f"data/memory/user_{user_id}")
    # ... create and cache storage ...
    _storages[user_id] = storage
    return storage
```

### 3. Обновлены MCP tools (добавлен user_id):

**Было:**
```python
@mcp.tool()
def store_memory(content: str, category: str = "general") -> dict:
    # Использовал global storage
```

**Стало:**
```python
@mcp.tool()
def store_memory(content: str, user_id: int, category: str = "general") -> dict:
    """user_id обязателен для изоляции"""
    storage = get_storage(user_id)  # ✅ Per-user storage
    # ...
```

### 4. Обновлен `src/agents/mcp/memory/memory_tool.py`:

**Было:**
```python
# Устанавливал KB_PATH в env vars
if hasattr(context, "kb_root_path") and context.kb_root_path:
    updated_env["KB_PATH"] = str(context.kb_root_path)
```

**Стало:**
```python
# Получает user_id из context и передает в MCP вызовы
user_id = getattr(context, "user_id", None)
if not user_id:
    return {"success": False, "error": "user_id required"}

mcp_params = {
    "content": content,
    "user_id": user_id,  # ✅ Передаем в каждом вызове
    # ...
}
```

### 5. Упрощен HTTP сервер:

**Удалено:**
- `--user-id` параметр командной строки (не нужен)
- Global storage initialization

**Изменено:**
- Сервер работает в multi-user режиме
- Storage создается on-demand для каждого user_id
- Кеширование storage по user_id

### 6. Обновлен `config.example.yaml`:

**Удалено:**
```yaml
# ❌ УДАЛЕНО
MCP_SERVERS_POSTFIX: .mcp_servers
MEM_AGENT_MEMORY_POSTFIX: memory
```

**Обновлено:**
```yaml
# ✅ ПРАВИЛЬНОЕ описание
# Memory storage:
#   Each user's memory is stored at: data/memory/user_{user_id}/
#   This ensures strict per-user isolation and privacy
#
# MCP servers:
#   Shared servers: data/mcp_servers/ (available to all users)
#   User-specific: data/mcp_servers/user_{user_id}/ (override shared)
```

## Структура директорий

### ✅ ПРАВИЛЬНАЯ структура

```
data/
├── mcp_servers/              # Shared MCP серверы (инструменты)
│   ├── mem-agent.json        # Memory HTTP server config
│   ├── custom-tool.json      # Другие серверы
│   └── user_123/             # User-specific серверы
│       └── personal-tool.json
└── memory/                   # User memory (результаты действий)
    ├── user_123/             # Память пользователя 123
    │   ├── memories.json     # JSON storage
    │   └── vector_store/     # Vector storage
    └── user_456/             # Память пользователя 456
        └── memories.json

knowledge_bases/              # Knowledge bases (заметки, KB)
└── my-notes/                 # KB пользователя
    ├── topics/               # Топики и заметки
    └── index.md
```

### ❌ УДАЛЕНО (неправильно)

```
# ❌ БОЛЬШЕ НЕТ per-KB путей
knowledge_bases/user_kb/
├── .mcp_servers/  # ❌ Удалено
└── memory/        # ❌ Удалено

# ❌ БОЛЬШЕ НЕТ shared memory
data/memory/shared/  # ❌ Удалено
```

## MCP Registry - Приоритеты

```python
# В registry.py
def discover_servers(self) -> None:
    # 1. Shared servers (data/mcp_servers/)
    self._discover_from_directory(self.servers_dir, scope="shared")
    
    # 2. User-specific servers (data/mcp_servers/user_{user_id}/)
    if self.user_id is not None:
        user_dir = self.servers_dir / f"user_{self.user_id}"
        if user_dir.exists():
            self._discover_from_directory(user_dir, scope=f"user_{user_id}")
    
    # User-specific переопределяют shared с тем же именем
```

## Проверка

### Что проверено:

1. ✅ `config/settings.py` - удалены постфиксы и helper методы
2. ✅ `config.example.yaml` - обновлены описания
3. ✅ `src/agents/mcp/memory/memory_server_http.py` - multi-user, user_id обязателен
4. ✅ `src/agents/mcp/memory/memory_server.py` - user_id обязателен
5. ✅ `src/agents/mcp/memory/memory_tool.py` - передает user_id в MCP вызовах
6. ✅ `scripts/install_mem_agent.py` - обновлено описание

### Что нужно обновить:

- [ ] Документация в `docs_site/` - удалить упоминания per-KB архитектуры
- [ ] Примеры в `examples/` - обновить под новую архитектуру

## Преимущества новой архитектуры

1. ✅ **Строгая изоляция пользователей** - нет shared memory
2. ✅ **Простота** - нет постфиксов, фиксированные пути
3. ✅ **Безопасность** - user_id обязателен, нельзя получить чужую память
4. ✅ **Гибкость MCP** - shared инструменты + user override
5. ✅ **Multi-user сервер** - один HTTP сервер для всех пользователей
6. ✅ **Кеширование** - storage кешируется по user_id

## Итог

**ВСЕ ИСПРАВЛЕНО! ✅**

- ❌ Удалена per-KB архитектура (не должно быть)
- ❌ Удалена shared memory (не должно быть)
- ✅ Память строго per-user: `data/memory/user_{user_id}/`
- ✅ MCP shared + user: `data/mcp_servers/` + `data/mcp_servers/user_{user_id}/`
- ✅ user_id обязателен для всех memory операций
- ✅ Multi-user HTTP сервер с кешированием

**Архитектура правильная и безопасная!**
