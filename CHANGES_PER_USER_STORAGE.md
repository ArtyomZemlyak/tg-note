# Per-User Storage Refactoring

## Краткое описание

Переделана архитектура хранения данных с глобальных путей на **per-user postfix подход** для изоляции данных пользователей.

## Что изменилось

### 1. Настройки (config/settings.py)

**Было:**
```python
MCP_SERVERS_DIR: Path = Field(default=Path("./data/mcp_servers"))
MEM_AGENT_MEMORY_PATH: Path = Field(default=Path("./data/memory"))
```

**Стало:**
```python
MCP_SERVERS_POSTFIX: str = Field(default=".mcp_servers")
MEM_AGENT_MEMORY_POSTFIX: str = Field(default="memory")
```

### 2. Новые helper методы в Settings

```python
def get_mcp_servers_dir(self, kb_path: Path) -> Path:
    """Возвращает {kb_path}/{MCP_SERVERS_POSTFIX}"""
    
def get_mem_agent_memory_path(self, kb_path: Path) -> Path:
    """Возвращает {kb_path}/{MEM_AGENT_MEMORY_POSTFIX}"""
    
def ensure_mcp_servers_dir_exists(self, kb_path: Path) -> None:
    """Создает директорию MCP серверов если не существует"""
    
def ensure_mem_agent_memory_path_exists(self, kb_path: Path) -> None:
    """Создает директорию памяти если не существует"""
```

### 3. Структура директорий

**Было (глобально):**
```
data/
├── mcp_servers/      # Общие для всех
│   └── mem-agent.json
└── memory/           # Общая для всех
    ├── user.md
    └── entities/
```

**Стало (per-user):**
```
knowledge_bases/
└── {user_kb_name}/   # Каждый пользователь имеет свою KB
    ├── .mcp_servers/ # MCP серверы пользователя
    │   └── mem-agent.json
    ├── memory/       # Память пользователя
    │   ├── user.md
    │   └── entities/
    └── topics/       # Заметки пользователя
```

## Преимущества

1. ✅ **Изоляция пользователей** - каждый пользователь имеет свою память и MCP конфигурацию
2. ✅ **Чистая конфигурация** - postfix'ы проще, чем полные пути
3. ✅ **Гибкость** - легко изменить структуру, изменив postfix
4. ✅ **Интеграция с KB** - всё в рамках knowledge base пользователя
5. ✅ **Консистентность** - единый подход для всех per-user данных

## Как использовать

### Получение путей для пользователя

```python
from config.settings import settings
from pathlib import Path

# Получить KB path пользователя (из setkb)
kb_path = Path("./knowledge_bases/user_kb")

# Сконструировать полные пути
memory_path = settings.get_mem_agent_memory_path(kb_path)
# Результат: knowledge_bases/user_kb/memory

mcp_dir = settings.get_mcp_servers_dir(kb_path)
# Результат: knowledge_bases/user_kb/.mcp_servers
```

### Создание MCP Manager для пользователя

```python
from src.mcp_registry import MCPServersManager

# Получить KB path пользователя
kb_path = get_user_kb_path(user_id)

# Создать per-user MCP manager
mcp_dir = settings.get_mcp_servers_dir(kb_path)
manager = MCPServersManager(servers_dir=mcp_dir)
```

## Обновленные файлы

### Код
- ✅ `config/settings.py` - Добавлены postfix'ы и helper методы
- ✅ `scripts/install_mem_agent.py` - Использует новую структуру
- ✅ `src/mem_agent/__init__.py` - Удалена ссылка на settings.py

### Документация
- ✅ `docs_site/agents/mem-agent-setup.md` - Обновлены примеры
- ✅ `docs_site/agents/mcp-server-registry.md` - Обновлены примеры
- ✅ `docs_site/architecture/per-user-storage.md` - Новый гайд
- ✅ `README_MEM_AGENT.md` - Обновлена структура
- ✅ `MIGRATION_SUMMARY.md` - Обновлены примеры

## Конфигурация

### config.yaml

```yaml
# Postfix'ы для per-user директорий
MEM_AGENT_MEMORY_POSTFIX: memory
MCP_SERVERS_POSTFIX: .mcp_servers

# Глобальный KB path (можно переопределить per-user)
KB_PATH: ./knowledge_bases/default
```

### Per-User настройки

Пользователи могут установить свою KB через `/setkb`:

```
/setkb my-notes
# Устанавливает KB_PATH в knowledge_bases/my-notes для этого пользователя
# Память будет в: knowledge_bases/my-notes/memory
# MCP серверы будут в: knowledge_bases/my-notes/.mcp_servers
```

## Обратная совместимость

⚠️ **Breaking Change**: Старые глобальные пути `MCP_SERVERS_DIR` и `MEM_AGENT_MEMORY_PATH` больше не поддерживаются.

**Миграция:**
1. Переместите существующие MCP конфигурации в KB пользователя
2. Переместите существующую память в KB пользователя
3. Обновите конфигурацию на использование postfix'ов

## См. также

- [Per-User Storage Architecture](docs_site/architecture/per-user-storage.md) - Подробная архитектура
- [Memory Agent Setup](docs_site/agents/mem-agent-setup.md) - Настройка memory agent
- [MCP Server Registry](docs_site/agents/mcp-server-registry.md) - Управление MCP серверами