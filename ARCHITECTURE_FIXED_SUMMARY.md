# Архитектура путей исправлена ✅

## Дата: 2025-10-11

## Что было неправильно

❌ **Per-KB архитектура с постфиксами:**
- `{kb_path}/.mcp_servers/` через `MCP_SERVERS_POSTFIX`
- `{kb_path}/memory/` через `MEM_AGENT_MEMORY_POSTFIX`
- Shared memory в `data/memory/shared/`
- Возможность действий, влияющих на всех пользователей

## Что исправлено

### ✅ Memory (Память пользователя)

**Путь:** `data/memory/user_{user_id}/`

**Правила:**
- ✅ Строгая изоляция по `user_id`
- ❌ НЕТ shared memory
- ❌ НЕТ per-KB путей
- ✅ `user_id` обязателен для всех операций

```bash
data/memory/
├── user_123/
│   ├── memories.json
│   └── vector_store/
└── user_456/
    └── memories.json
```

### ✅ MCP Servers (Инструменты)

**Пути:**
- `data/mcp_servers/` - shared (доступны всем)
- `data/mcp_servers/user_{user_id}/` - user-specific (переопределяют shared)

**Правила:**
- ✅ Shared MCP разрешены (это инструменты, не данные)
- ✅ User-specific переопределяют shared
- ✅ Registry автоматически находит оба уровня

```bash
data/mcp_servers/
├── mem-agent.json       # Shared memory server
└── user_123/            # User overrides
    └── custom-tool.json
```

## Изменения в коде

### 1. `config/settings.py`

**Удалено:**
- `MCP_SERVERS_POSTFIX`
- `MEM_AGENT_MEMORY_POSTFIX`
- `get_mcp_servers_dir(kb_path)`
- `get_mem_agent_memory_path(kb_path)`
- `ensure_mcp_servers_dir_exists(kb_path)`
- `ensure_mem_agent_memory_path_exists(kb_path)`

**Добавлено:**
```python
def get_mem_agent_memory_dir(self, user_id: int) -> Path:
    return Path(f"data/memory/user_{user_id}")

def ensure_mem_agent_memory_dir_exists(self, user_id: int) -> None:
    memory_dir = self.get_mem_agent_memory_dir(user_id)
    memory_dir.mkdir(parents=True, exist_ok=True)
```

### 2. `memory_server_http.py`

**Было:**
```python
storage = None  # Global

def init_storage(user_id: Optional[int] = None):
    if kb_path:  # ❌ Per-KB
        data_dir = kb_path / postfix
    elif user_id:
        data_dir = f"data/memory/user_{user_id}"
    else:
        data_dir = "data/memory/shared"  # ❌ Shared!
```

**Стало:**
```python
_storages: Dict[int, MemoryStorage] = {}  # Per-user cache

def get_storage(user_id: int) -> MemoryStorage:
    if not user_id:
        raise ValueError("user_id required")  # ✅ Обязателен!
    
    if user_id in _storages:
        return _storages[user_id]
    
    data_dir = Path(f"data/memory/user_{user_id}")  # ✅ Только per-user
    # ... create and cache ...
```

### 3. MCP Tools

**Было:**
```python
@mcp.tool()
def store_memory(content: str) -> dict:
    # Global storage
```

**Стало:**
```python
@mcp.tool()
def store_memory(content: str, user_id: int) -> dict:
    storage = get_storage(user_id)  # ✅ Per-user
    # ...
```

### 4. `memory_tool.py`

**Было:**
```python
# Устанавливал KB_PATH в env
updated_env["KB_PATH"] = str(context.kb_root_path)
```

**Стало:**
```python
# Получает user_id из context
user_id = getattr(context, "user_id", None)
if not user_id:
    return {"error": "user_id required"}

mcp_params = {"content": content, "user_id": user_id}
```

### 5. `config.example.yaml`

**Удалено:**
```yaml
MCP_SERVERS_POSTFIX: .mcp_servers
MEM_AGENT_MEMORY_POSTFIX: memory
```

**Обновлено:**
```yaml
# Memory storage:
#   Each user's memory is stored at: data/memory/user_{user_id}/
#
# MCP servers:
#   Shared: data/mcp_servers/
#   User-specific: data/mcp_servers/user_{user_id}/
```

### 6. HTTP Server

**Удалено:**
- `--user-id` параметр
- Global storage initialization

**Изменено:**
- Multi-user режим
- Storage on-demand
- Кеширование по user_id

## Документация

### Обновлено:
- ✅ `PATHS_ARCHITECTURE_FIXED.md` - полное описание новой архитектуры
- ✅ `docs_site/architecture/storage-paths.md` - новая документация путей
- ✅ `config.example.yaml` - обновлены описания
- ✅ `scripts/install_mem_agent.py` - обновлено описание

### Удалено:
- ❌ `docs_site/architecture/per-user-storage.md` - описывало неправильную архитектуру

### Требует обновления:
- [ ] `docs_site/agents/mem-agent-setup.md` - убрать упоминания постфиксов
- [ ] `docs_site/agents/mcp-server-registry.md` - убрать упоминания per-KB
- [ ] Другие документы в `docs_site/`

## Проверка

```bash
# Проверить, что все работает
python -m src.agents.mcp.memory.memory_server_http

# Проверить registry
python -c "from src.mcp_registry import MCPServersManager; m = MCPServersManager(); m.initialize(); print(m.get_all_servers())"

# Проверить settings
python -c "from config.settings import settings; print(settings.get_mem_agent_memory_dir(123))"
```

## Итог

✅ **ВСЕ ИСПРАВЛЕНО!**

1. ✅ Память строго per-user: `data/memory/user_{user_id}/`
2. ✅ MCP shared + user override: `data/mcp_servers/` + `data/mcp_servers/user_{user_id}/`
3. ✅ user_id обязателен для memory
4. ✅ Нет shared memory
5. ✅ Нет per-KB путей
6. ✅ Multi-user HTTP сервер
7. ✅ Кеширование storage

**Архитектура правильная и безопасная! Пользователи изолированы.**
