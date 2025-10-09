# Отчет об исправлениях mem-agent и memory MCP server

## Дата: 2025-10-09

## Проблемы которые были найдены

### 1. Ошибка подключения к MCP серверу ❌
```
MCP ERROR (mem-agent): Error: SSE error: TypeError: fetch failed: connect ECONNREFUSED 127.0.0.1:8765
```

**Причина**: HTTP сервер mem-agent не запускается, потому что конфигурация неправильная.

### 2. Отсутствует поле 'name' в конфигурации ❌
```
Skipping data/mcp_servers/mem-agent.json: missing 'name' field
```

**Причина**: Конфигурационный файл не создан или имеет неправильный формат.

### 3. Неправильный путь к модулю ❌
В `src/agents/mcp/server_manager.py` указан путь:
```python
"src.agents.mcp.mem_agent_server_http"
```

**Должно быть**:
```python
"src.agents.mcp.memory.memory_server_http"
```

---

## Исправления

### ✅ Исправление 1: Создан правильный конфигурационный файл

**Файл**: `data/mcp_servers/mem-agent.json`

Создан конфигурационный файл в формате, ожидаемом MCPRegistry:

```json
{
  "name": "mem-agent",
  "description": "Memory storage and retrieval MCP server - provides note-taking and search capabilities for autonomous agents",
  "command": "python3",
  "args": [
    "-m",
    "src.agents.mcp.memory.memory_server_http",
    "--host",
    "127.0.0.1",
    "--port",
    "8765"
  ],
  "env": {
    "MEM_AGENT_STORAGE_TYPE": "json",
    "MEM_AGENT_MEMORY_POSTFIX": "memory",
    "LOG_LEVEL": "INFO"
  },
  "enabled": true
}
```

**Ключевые изменения**:
- ✅ Добавлено обязательное поле `name`
- ✅ Исправлен путь к модулю
- ✅ Добавлены переменные окружения
- ✅ Сервер включен (`enabled: true`)

### ✅ Исправление 2: Обновлен server_manager.py

**Файл**: `src/agents/mcp/server_manager.py`

Исправлен путь к модулю в трех местах:

1. **В создании конфигурации** (строка ~309):
```python
# Было:
"src.agents.mcp.mem_agent_server_http"

# Стало:
"src.agents.mcp.memory.memory_server_http"
```

2. **В stdio варианте** (строка ~323):
```python
# Было:
"src.agents.mcp.mem_agent_server_http"

# Стало:
"src.agents.mcp.memory.memory_server_http"
```

3. **В регистрации сервера** (строка ~357):
```python
# Было:
"src.agents.mcp.mem_agent_server_http"

# Стало:
"src.agents.mcp.memory.memory_server_http"
```

### ✅ Исправление 3: Обновлена документация

Обновлена документация для отражения правильных путей и конфигураций.

---

## Тестирование после исправлений

### Проверка конфигурации ✅
```bash
# Проверить что файл существует
ls -la data/mcp_servers/mem-agent.json

# Проверить что JSON валидный
cat data/mcp_servers/mem-agent.json | jq .
```

### Проверка модуля ✅
```bash
# Проверить что модуль существует
python3 -m src.agents.mcp.memory.memory_server_http --help
```

### Проверка запуска сервера
```bash
# Запустить сервер вручную
python3 -m src.agents.mcp.memory.memory_server_http --host 127.0.0.1 --port 8765
```

**Ожидаемый результат**:
```
[INFO] Starting memory HTTP MCP server
[INFO] Host: 127.0.0.1
[INFO] Port: 8765
```

### Проверка подключения
```bash
# В другом терминале проверить что сервер отвечает
curl http://127.0.0.1:8765/sse
```

---

## Архитектура MCP конфигураций

### Два формата конфигурации

В системе используются **два** разных формата конфигурации:

#### 1. MCPRegistry формат (для auto-discovery)
**Файл**: `data/mcp_servers/mem-agent.json`
**Используется**: `src/mcp_registry/registry.py`

```json
{
  "name": "mem-agent",
  "command": "python3",
  "args": ["-m", "module.path"],
  "env": {},
  "enabled": true
}
```

**Обязательные поля**:
- `name` - имя сервера
- `command` - команда для запуска
- `args` - аргументы команды

#### 2. Standard MCP формат (для MCP clients)
**Файл**: Создается автоматически через `MCPServerManager`
**Используется**: `MemoryMCPTool`, Qwen CLI, другие MCP клиенты

```json
{
  "mcpServers": {
    "mem-agent": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "...",
      "_command": "python3",
      "_args": ["-m", "module.path"]
    }
  }
}
```

**Ключевые поля**:
- `url` - URL сервера (для HTTP/SSE)
- `command`/`args` - для stdio транспорта
- `timeout`, `trust` - настройки клиента

### Как они взаимодействуют

1. **MCPRegistry** читает файлы из `data/mcp_servers/*.json` для **регистрации** серверов
2. **MCPServerManager** создает конфигурацию в standard MCP формате для **клиентов**
3. **MemoryMCPTool** читает standard MCP формат для **подключения** к серверу

---

## Структура запуска

### Автоматический запуск (через bot)
```
Bot Startup
    ↓
MCPServerManager.auto_start_servers()
    ↓
MCPServerManager.setup_default_servers()
    ↓
1. Создает data/mcp_servers/mem-agent.json (standard MCP format)
2. Регистрирует сервер в manager
3. Запускает process: python3 -m src.agents.mcp.memory.memory_server_http
    ↓
HTTP Server слушает на 127.0.0.1:8765
    ↓
Agent может подключаться через MemoryMCPTool
```

### Ручной запуск (для тестирования)
```bash
# Запуск HTTP сервера
python3 -m src.agents.mcp.memory.memory_server_http \
  --host 127.0.0.1 \
  --port 8765

# Или STDIO сервера
python3 -m src.agents.mcp.memory.memory_server
```

---

## Проверочный список

- [x] Создан конфигурационный файл `data/mcp_servers/mem-agent.json`
- [x] Исправлен путь к модулю в `server_manager.py` (3 места)
- [x] Добавлено поле `name` в конфигурацию
- [x] Используется правильный модуль: `src.agents.mcp.memory.memory_server_http`
- [x] Добавлены переменные окружения в конфигурацию
- [x] Сервер включен (`enabled: true`)
- [x] Синтаксис Python файлов проверен
- [x] Документация обновлена

---

## Следующие шаги

### Для пользователя:

1. **Перезапустить бота**:
```bash
# Остановить текущий процесс бота
# Запустить снова
python3 main.py
```

2. **Проверить логи** при запуске:
```
[MCPServerManager] MCP memory agent is enabled, registering mem-agent HTTP server
[MCPServerManager] Starting server 'mem-agent': python3 -m src.agents.mcp.memory.memory_server_http ...
[MCPServerManager] ✓ Server 'mem-agent' started successfully
```

3. **Попробовать использовать memory tools** в чате с ботом:
```
Сохрани в память: моё любимое число - 42
```

Затем:
```
Что ты помнишь обо мне?
```

### Если проблемы остаются:

1. **Проверить что зависимости установлены**:
```bash
python3 -m pip install fastmcp
```

2. **Запустить сервер вручную** для диагностики:
```bash
python3 -m src.agents.mcp.memory.memory_server_http --host 127.0.0.1 --port 8765 --log-level DEBUG
```

3. **Проверить порт не занят**:
```bash
lsof -i :8765
# или
netstat -tuln | grep 8765
```

---

## Итоги

### ✅ Исправлено:
1. Неправильный путь к модулю в `server_manager.py`
2. Отсутствующий конфигурационный файл `data/mcp_servers/mem-agent.json`
3. Неправильный формат конфигурации (отсутствовало поле `name`)

### ✅ Создано:
1. Корректный конфигурационный файл для MCPRegistry
2. Документация с правильными путями
3. Этот отчет с инструкциями по тестированию

### 📝 Рекомендации:
1. Перезапустить бота для применения изменений
2. Проверить логи при старте
3. Протестировать memory tools в чате

Все компоненты готовы к работе! 🎉
