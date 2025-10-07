# Резюме: Улучшение обнаружения MCP серверов

## Проблема

До изменений:
- MCP серверы обнаруживались только из глобальной директории `data/mcp_servers/`
- Не было поддержки пользовательских (per-user) MCP серверов
- Агенты не использовали MCPRegistryClient для автоматического обнаружения серверов
- Только жестко закодированный `memory_agent_tool` был доступен

## Решение

Реализована система автоматического обнаружения MCP серверов с поддержкой:
1. **Общих (shared) MCP серверов** - доступны всем пользователям
2. **Пользовательских (per-user) MCP серверов** - доступны только конкретному пользователю
3. **Механизма переопределения** - пользовательские серверы могут переопределять общие
4. **Динамического создания инструментов** - автоматическая регистрация всех инструментов из обнаруженных серверов

## Внесенные изменения

### 1. MCPServerRegistry (`src/mcp_registry/registry.py`)

**Добавлено:**
- Параметр `user_id` в конструктор
- Метод `_discover_from_directory()` для сканирования конкретной директории
- Логика обнаружения сначала общих, затем пользовательских серверов
- Логика переопределения серверов

**Ключевые изменения:**
```python
def __init__(self, servers_dir: Path, user_id: Optional[int] = None)
def discover_servers(self) -> None
    # Сначала обнаруживаем shared серверы
    # Затем обнаруживаем user-specific серверы (если user_id задан)
    # User-specific серверы переопределяют shared
```

### 2. MCPServersManager (`src/mcp_registry/manager.py`)

**Добавлено:**
- Параметр `user_id` в конструктор
- Передача `user_id` в MCPServerRegistry

**Ключевые изменения:**
```python
def __init__(self, servers_dir: Optional[Path] = None, user_id: Optional[int] = None)
    self.user_id = user_id
    self.registry = MCPServerRegistry(servers_dir, user_id=user_id)
```

### 3. MCPRegistryClient (`src/agents/mcp/registry_client.py`)

**Добавлено:**
- Параметр `user_id` для обнаружения пользовательских серверов
- Поддержка пользовательского контекста

**Ключевые изменения:**
```python
def __init__(self, servers_dir: Optional[Path] = None, user_id: Optional[int] = None)
    self.user_id = user_id
    self.manager = MCPServersManager(servers_dir, user_id=user_id)
```

### 4. DynamicMCPTools (НОВЫЙ: `src/agents/mcp/dynamic_mcp_tools.py`)

**Создан новый модуль:**
- `DynamicMCPTool` - класс для обертывания инструментов из MCP серверов
- `discover_and_create_mcp_tools()` - функция автоматического обнаружения и создания инструментов
- `create_mcp_tools_for_user()` - удобная функция для создания инструментов для конкретного пользователя

**Функциональность:**
1. Обнаруживает MCP серверы (shared + per-user)
2. Подключается к включенным серверам
3. Запрашивает у каждого сервера список доступных инструментов
4. Создает `DynamicMCPTool` для каждого инструмента
5. Возвращает список готовых к использованию инструментов

### 5. ToolContext (`src/agents/tools/base_tool.py`)

**Добавлено:**
- Поле `user_id: Optional[int] = None` для передачи пользовательского контекста в инструменты

### 6. ToolManager (`src/agents/tools/registry.py`)

**Добавлено:**
- Параметр `user_id` в `build_default_tool_manager()`
- Передача `user_id` в ToolContext
- Интеграция с динамическим обнаружением MCP инструментов

**Ключевые изменения:**
```python
def build_default_tool_manager(..., user_id: Optional[int] = None):
    ctx = ToolContext(..., user_id=user_id)
    
    # Динамическое обнаружение MCP инструментов
    if enable_mcp:
        mcp_tools = await discover_and_create_mcp_tools(user_id=user_id)
        manager.register_many(mcp_tools)
```

### 7. AutonomousAgent (`src/agents/autonomous_agent.py`)

**Добавлено:**
- Извлечение `user_id` из конфига
- Передача `user_id` в ToolManager

**Ключевые изменения:**
```python
self.user_id = self.config.get("user_id") if self.config else None

self.tool_manager: ToolManager = build_default_tool_manager(
    ...,
    user_id=self.user_id,
)
```

### 8. AgentFactory (`src/agents/agent_factory.py`)

**Добавлено:**
- Параметр `user_id` в `from_settings()`
- Добавление `user_id` в конфиг агента

**Ключевые изменения:**
```python
@classmethod
def from_settings(cls, settings, user_id: Optional[int] = None):
    config = {
        ...,
        "user_id": user_id,
    }
```

### 9. UserContextManager (`src/services/user_context_manager.py`)

**Добавлено:**
- Передача `user_id` при создании агента
- Добавление настроек MCP в конфиг агента

**Ключевые изменения:**
```python
config = {
    ...,
    "enable_mcp": self.settings_manager.get_setting(user_id, "AGENT_ENABLE_MCP"),
    "enable_mcp_memory": self.settings_manager.get_setting(user_id, "AGENT_ENABLE_MCP_MEMORY"),
    "kb_path": self.settings_manager.get_setting(user_id, "KB_PATH"),
    "kb_topics_only": self.settings_manager.get_setting(user_id, "KB_TOPICS_ONLY"),
    "user_id": user_id,
}
```

### 10. Документация

**Создано:**
- `docs/MCP_SERVER_DISCOVERY.md` - подробная документация на английском
- `docs/MCP_SERVER_DISCOVERY_RU.md` - подробная документация на русском

**Содержание:**
- Обзор системы обнаружения MCP серверов
- Процесс обнаружения и архитектура
- Формат конфигурационных файлов
- Примеры конфигураций (shared, per-user, override)
- Использование через Telegram бот и программно
- Интеграция с агентами
- Лучшие практики
- Troubleshooting
- API reference

### 11. Тесты

**Создано:**
- `tests/test_mcp_user_discovery.py` - тесты для проверки функциональности

**Покрытие:**
- Обнаружение shared серверов
- Обнаружение per-user серверов
- Переопределение shared серверов пользовательскими
- Работа MCPServersManager с user_id
- Изоляция между пользователями
- Обработка отключенных серверов

## Структура директорий

### До изменений
```
data/mcp_servers/
├── mem-agent.json
└── other-server.json
```

### После изменений
```
data/mcp_servers/
├── mem-agent.json              # Общий сервер (доступен всем)
├── filesystem.json             # Еще один общий сервер
├── user_123456/                # Серверы для пользователя 123456
│   ├── mem-agent.json          # Переопределяет общий mem-agent
│   └── custom-tool.json        # Пользовательский инструмент
└── user_789012/                # Серверы для пользователя 789012
    └── private-api.json        # Приватное API
```

## Как это работает

### 1. Создание агента для пользователя

```python
# UserContextManager создает агент с user_id
config = {
    "user_id": 123456,
    "enable_mcp": True,
    ...
}
agent = AgentFactory.create_agent("autonomous", config)
```

### 2. Инициализация ToolManager

```python
# AutonomousAgent создает ToolManager с user_id
self.tool_manager = build_default_tool_manager(
    user_id=self.user_id,
    enable_mcp=True,
    ...
)
```

### 3. Обнаружение MCP серверов

```python
# build_default_tool_manager вызывает
mcp_tools = await discover_and_create_mcp_tools(user_id=user_id)

# discover_and_create_mcp_tools:
# 1. Создает MCPRegistryClient с user_id
registry_client = MCPRegistryClient(user_id=user_id)

# 2. Обнаруживает серверы
registry_client.initialize()  # Обнаруживает shared + user-specific

# 3. Подключается к серверам
connected_clients = await registry_client.connect_all_enabled()

# 4. Запрашивает инструменты у каждого сервера
for server_name, client in connected_clients.items():
    available_tools = await client.list_tools()
    
    # 5. Создает DynamicMCPTool для каждого инструмента
    for tool_schema in available_tools:
        mcp_tool = DynamicMCPTool(
            tool_name=tool_schema["name"],
            server_name=server_name,
            mcp_client=client,
            tool_schema=tool_schema
        )
        tools.append(mcp_tool)
```

### 4. Регистрация инструментов

```python
# build_default_tool_manager регистрирует все обнаруженные инструменты
manager.register_many(mcp_tools)
```

### 5. Использование инструментов агентом

```python
# Агент видит все инструменты как обычные tools
# Имена: mcp_{server_name}_{tool_name}

# Пример: mem-agent сервер с инструментом store_memory
# Становится: mcp_mem_agent_store_memory

await agent.tool_manager.execute("mcp_mem_agent_store_memory", {
    "content": "Important information"
})
```

## Преимущества

✅ **Автоматическое обнаружение** - не нужно жестко кодировать инструменты  
✅ **Per-user изоляция** - каждый пользователь может иметь свои серверы  
✅ **Переопределение** - пользователи могут кастомизировать общие серверы  
✅ **Динамическая регистрация** - новые серверы автоматически доступны  
✅ **Безопасность** - изоляция пользовательских данных  
✅ **Гибкость** - простое добавление новых серверов через JSON  
✅ **Telegram интеграция** - управление через бот команды  

## Использование

### Для пользователей (через Telegram)

```
/listmcpservers          - показать все серверы
/addmcpserver           - добавить новый сервер (вставить JSON)
/enablemcp server-name  - включить сервер
/disablemcp server-name - отключить сервер
/removemcp server-name  - удалить сервер
```

### Для разработчиков

```python
# Создать менеджер для пользователя
manager = MCPServersManager(user_id=123456)
manager.initialize()

# Получить серверы
all_servers = manager.get_all_servers()  # shared + user-specific
enabled_servers = manager.get_enabled_servers()

# Управление серверами
manager.enable_server("my-server")
manager.disable_server("my-server")
manager.add_server_from_json(json_content)
```

## Совместимость

- ✅ Обратная совместимость с существующим кодом
- ✅ Старый `AGENT_ENABLE_MCP_MEMORY` продолжает работать
- ✅ Можно постепенно мигрировать на новую систему
- ✅ Оба подхода могут сосуществовать

## Тестирование

Запустить тесты:
```bash
pytest tests/test_mcp_user_discovery.py -v
```

Тесты проверяют:
- Обнаружение shared серверов
- Обнаружение per-user серверов  
- Переопределение серверов
- Изоляцию между пользователями
- Работу с отключенными серверами

## Следующие шаги

Рекомендации для дальнейшего развития:

1. **Валидация** - добавить валидацию JSON конфигов перед сохранением
2. **Кэширование** - кэшировать результаты обнаружения для производительности
3. **Мониторинг** - добавить метрики использования MCP серверов
4. **UI** - создать веб-интерфейс для управления серверами
5. **Шаблоны** - предоставить готовые шаблоны для популярных MCP серверов
6. **Безопасность** - добавить sandboxing для user-uploaded серверов

## Заключение

Реализована полноценная система обнаружения MCP серверов с поддержкой:
- Общих и пользовательских серверов
- Автоматического обнаружения и регистрации инструментов
- Безопасной изоляции между пользователями
- Простого управления через Telegram бот
- Гибкой конфигурации через JSON файлы

Система готова к использованию и хорошо документирована.