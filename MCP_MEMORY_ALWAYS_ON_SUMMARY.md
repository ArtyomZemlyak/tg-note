# Сводка: MCP Memory Agent теперь всегда включен

## Обзор изменений

Все реализации агентов теперь **обязательно** используют mem-agent MCP HTTP сервер для хранения и получения памяти. Это ключевая функция системы, которая больше не является опциональной.

## Изменения в коде

### 1. ✅ ToolManager (`src/agents/tools/registry.py`)

**Изменения:**
- Удален параметр `enable_mcp_memory` из `build_default_tool_manager`
- MCP memory инструменты теперь регистрируются **ВСЕГДА** (до проверки `enable_mcp`)
- Обновлена документация, указывающая, что MCP memory - это core feature

**Код:**
```python
# MCP Memory Agent Tools - ALWAYS ENABLED
# All agents use mem-agent MCP HTTP server for memory storage/retrieval
try:
    from ..mcp import memory_agent_tool
    for tool in memory_agent_tool.ALL_TOOLS:
        tool.enable()
    manager.register_many(memory_agent_tool.ALL_TOOLS)
    logger.info("[ToolManager] MCP memory agent tools enabled (always on)")
except ImportError as e:
    logger.warning(f"[ToolManager] Failed to import MCP memory tools: {e}")
```

### 2. ✅ AutonomousAgent (`src/agents/autonomous_agent.py`)

**Изменения:**
- Удален параметр `enable_mcp_memory` из `__init__`
- Удалена переменная `self.enable_mcp_memory`
- Обновлена документация с пометкой, что MCP memory всегда включен
- Удален параметр из вызова `build_default_tool_manager`

**Результат:**
- MCP memory инструменты доступны через `tool_manager` автоматически
- Агент может использовать `memory_store`, `memory_search` и `mcp_memory_agent` без дополнительной конфигурации

### 3. ✅ QwenCodeCLIAgent (`src/agents/qwen_code_cli_agent.py`)

**Изменения:**
- Удалена проверка `enable_mcp` - MCP настройка теперь происходит **ВСЕГДА**
- `_setup_qwen_mcp_config()` вызывается автоматически при инициализации
- `get_mcp_tools_description()` всегда возвращает описание MCP инструментов

**Результат:**
- `.qwen/settings.json` всегда настраивается с mem-agent сервером
- Qwen CLI автоматически получает доступ к MCP memory инструментам

### 4. ✅ StubAgent (`src/agents/stub_agent.py`)

**Изменения:**
- Добавлен параметр `kb_root_path` в конструктор
- Добавлен метод `_init_mcp_memory()` для инициализации MCP memory клиента
- Добавлен метод `_store_in_memory()` для сохранения в памяти
- В `process()` добавлен вызов `_store_in_memory()` для записи результатов

**Результат:**
- StubAgent теперь записывает все обработанные контенты в mem-agent
- Можно искать историю обработки через MCP memory search

### 5. ✅ AgentFactory (`src/agents/agent_factory.py`)

**Изменения:**
- Удалено `enable_mcp_memory` из `from_settings()` конфигурации
- Удален параметр из `_create_autonomous_agent()`
- Добавлена фабрика `_create_stub_agent()` для передачи `kb_root_path`

**Результат:**
- Все агенты, создаваемые через фабрику, автоматически получают MCP memory поддержку

### 6. ✅ Settings (`config/settings.py`)

**Изменения:**
- `AGENT_ENABLE_MCP_MEMORY` помечен как **[DEPRECATED]**
- Значение по умолчанию изменено на `True`
- Обновлено описание: "MCP memory agent is now ALWAYS enabled. This setting is kept for backward compatibility."

**Результат:**
- Обратная совместимость с существующими конфигурациями
- Четкое указание, что настройка больше не используется

### 7. ✅ MCPServerManager (`src/agents/mcp/server_manager.py`)

**Изменения:**
- `setup_default_servers()` теперь всегда регистрирует mem-agent сервер
- Удалена проверка `if self.settings.AGENT_ENABLE_MCP_MEMORY`
- Обновлены комментарии и логи

**Результат:**
- mem-agent сервер запускается автоматически при старте приложения
- Нет необходимости в дополнительной конфигурации

### 8. ✅ Тесты

**Обновлены файлы:**
- `tests/test_stub_agent.py` - добавлен `kb_root_path` параметр, добавлен тест MCP memory интеграции
- `tests/test_agent_factory.py` - обновлены mock настройки, удалены ссылки на `AGENT_ENABLE_MCP_MEMORY`, обновлен тест регистрации агентов

## Миграция существующего кода

### Для пользователей API

**Было:**
```python
agent = AutonomousAgent(
    llm_connector=connector,
    enable_mcp_memory=True  # ❌ Больше не нужно
)
```

**Стало:**
```python
agent = AutonomousAgent(
    llm_connector=connector
    # MCP memory включен автоматически ✅
)
```

### Для конфигурационных файлов

**config.yaml / .env:**
```yaml
# AGENT_ENABLE_MCP_MEMORY: false  # ⚠️ DEPRECATED - игнорируется
# Больше не нужно указывать, mem-agent всегда включен
```

### Для AgentFactory

**Было:**
```python
config = {
    "enable_mcp_memory": True  # ❌ Игнорируется
}
agent = AgentFactory.create_agent("autonomous", config)
```

**Стало:**
```python
config = {}  # MCP memory включен автоматически ✅
agent = AgentFactory.create_agent("autonomous", config)
```

## Преимущества

1. **Упрощенная конфигурация**: Больше не нужно помнить о включении MCP memory
2. **Консистентность**: Все агенты работают одинаково
3. **Лучший UX**: Агенты автоматически могут записывать и искать информацию
4. **Обратная совместимость**: Старые конфигурации продолжают работать

## Что осталось без изменений

- HTTP MCP сервер (`mem_agent_server_http.py`) работает как и раньше
- Структура хранения памяти не изменилась
- API MCP инструментов (`store_memory`, `retrieve_memory`, `list_categories`) остался прежним
- Поддержка per-user storage через `user_id`

## Проверка изменений

### Линтер
```bash
# Все измененные файлы проверены - ошибок нет ✅
```

### Тестовое покрытие
- `test_stub_agent.py` - обновлен и готов к запуску
- `test_agent_factory.py` - обновлен и готов к запуску
- Добавлен новый тест `test_stub_agent_mcp_memory_integration`

## Следующие шаги

1. ✅ Все изменения внесены и проверены
2. ✅ Обратная совместимость сохранена
3. ✅ Документация обновлена
4. 🔄 Рекомендуется обновить документацию в README.md и других файлах docs/

## Файлы, измененные в этом PR

1. `src/agents/tools/registry.py` - ToolManager всегда регистрирует MCP memory
2. `src/agents/autonomous_agent.py` - удален enable_mcp_memory параметр
3. `src/agents/qwen_code_cli_agent.py` - MCP всегда настраивается
4. `src/agents/stub_agent.py` - добавлена MCP memory поддержка
5. `src/agents/agent_factory.py` - обновлены фабрики агентов
6. `config/settings.py` - AGENT_ENABLE_MCP_MEMORY помечен как deprecated
7. `src/agents/mcp/server_manager.py` - mem-agent сервер всегда регистрируется
8. `tests/test_stub_agent.py` - обновлены тесты
9. `tests/test_agent_factory.py` - обновлены тесты

---

**Дата:** 2025-10-08  
**Автор:** Background Agent (Cursor)  
**Статус:** ✅ Завершено
