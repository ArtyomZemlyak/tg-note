# MCP Configuration via stdio Transport

## Итоговая конфигурация MCP серверов через stdio

Все MCP серверы настроены для работы через **stdio transport** (stdin/stdout).

---

## ✅ Два типа конфигураций

### 1. Для Python агентов (AutonomousAgent + DynamicMCP)

**Файл:** `data/mcp_servers/mem-agent.json`

```json
{
  "name": "mem-agent",
  "description": "Agent's personal note-taking and search system - allows the agent to record and search notes during task execution",
  "command": "python",
  "args": [
    "-m",
    "src.agents.mcp.mem_agent_server"
  ],
  "env": {
    "MEM_AGENT_MEMORY_POSTFIX": "memory"
  },
  "working_dir": "/workspace",
  "enabled": true
}
```

**Как работает:**
- Запускается через `MCPServerManager` в `main.py`
- Использует Python module: `src.agents.mcp.mem_agent_server`
- Общается через stdio (stdin/stdout)
- Автоматически стартует при `AGENT_ENABLE_MCP_MEMORY=true`

---

### 2. Для Qwen CLI (QwenCodeCLIAgent)

**Файл:** `~/.qwen/settings.json` или `<kb-path>/.qwen/settings.json`

```json
{
  "mcpServers": {
    "mem-agent": {
      "command": "python3",
      "args": [
        "src/agents/mcp/mem_agent_server.py"
      ],
      "cwd": "/workspace",
      "timeout": 10000,
      "trust": true,
      "description": "Memory storage and retrieval agent"
    }
  },
  "allowMCPServers": [
    "mem-agent"
  ]
}
```

**Как работает:**
- Генерируется автоматически через `QwenMCPConfigGenerator`
- Использует файл скрипта: `src/agents/mcp/mem_agent_server.py`
- Общается через stdio (stdin/stdout)
- Qwen CLI запускает как subprocess

**Генерация:**
```python
from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config

# Автоматическая генерация
setup_qwen_mcp_config(
    user_id=858138359,
    global_config=True  # Сохранит в ~/.qwen/settings.json
)
```

---

## 🔄 Как это работает

### Архитектура stdio transport

```
┌─────────────────────────┐
│   Agent (Python/Qwen)   │
│                         │
│  - Запускает процесс    │
│  - Отправляет JSON-RPC  │
│    через stdin          │
│  - Читает ответы из     │
│    stdout               │
└────────────┬────────────┘
             │ stdio (pipes)
             │
┌────────────▼────────────┐
│   MCP Server Process    │
│                         │
│  src.agents.mcp.        │
│    mem_agent_server.py  │
│                         │
│  - Читает из stdin      │
│  - Парсит JSON-RPC      │
│  - Выполняет команды    │
│  - Отвечает в stdout    │
└─────────────────────────┘
```

### Процесс коммуникации

1. **Агент запускает процесс:**
   ```bash
   python -m src.agents.mcp.mem_agent_server
   ```

2. **Агент отправляет JSON-RPC запрос в stdin:**
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "method": "tools/call",
     "params": {
       "name": "store_memory",
       "arguments": {
         "content": "Important note"
       }
     }
   }
   ```

3. **Сервер обрабатывает и отвечает в stdout:**
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "result": {
       "content": [
         {
           "type": "text",
           "text": "Memory stored successfully"
         }
       ]
     }
   }
   ```

---

## 📁 Структура файлов

```
/workspace/
├── data/
│   └── mcp_servers/
│       ├── .gitkeep
│       └── mem-agent.json          # Для Python агентов
│
├── src/
│   ├── agents/
│   │   └── mcp/
│   │       ├── mem_agent_server.py  # MCP сервер (stdio)
│   │       ├── qwen_config_generator.py
│   │       └── server_manager.py
│   │
│   └── mem_agent/
│       ├── __init__.py
│       └── storage.py               # Shared storage logic
│
└── scripts/
    └── install_mem_agent.py         # Установка и настройка
```

---

## 🚀 Использование

### Для Python агентов (AutonomousAgent)

**1. Установите mem-agent:**
```bash
python scripts/install_mem_agent.py
```

**2. Включите в конфигурации:**
```yaml
# config.yaml
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true
```

**3. Сервер запустится автоматически** при старте бота в `main.py`:
```python
# main.py автоматически:
mcp_server_manager = container.get("mcp_server_manager")
await mcp_server_manager.auto_start_servers()
```

---

### Для Qwen CLI (QwenCodeCLIAgent)

**1. Сгенерируйте конфигурацию:**
```python
from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config

setup_qwen_mcp_config(
    user_id=858138359,
    kb_path=Path("/path/to/knowledge_base"),  # Опционально
    global_config=True
)
```

**2. Или автоматически при создании агента:**
```python
agent = QwenCodeCLIAgent(
    kb_path="/path/to/kb",
    config={
        "enable_mcp": True,
        "user_id": 858138359
    }
)
# Конфигурация создастся автоматически в __init__
```

**3. Проверьте конфигурацию:**
```bash
cat ~/.qwen/settings.json
```

---

## ✅ Проверка работоспособности

### Проверить конфигурацию для Python агентов:
```bash
# Проверить файл
cat data/mcp_servers/mem-agent.json

# Проверить, что модуль существует
python -c "import src.agents.mcp.mem_agent_server; print('✓ OK')"
```

### Проверить конфигурацию для Qwen CLI:
```bash
# Глобальная конфигурация
cat ~/.qwen/settings.json

# Project-specific конфигурация
cat /path/to/kb/.qwen/settings.json
```

### Проверить работу MCP сервера:
```bash
# Запустить вручную
python -m src.agents.mcp.mem_agent_server

# Сервер должен ждать ввода в stdin
# Можно отправить JSON-RPC запрос для теста
```

---

## 🔧 Troubleshooting

### Проблема: ModuleNotFoundError: No module named 'src.mem_agent.server'

**Причина:** Старая конфигурация с неправильным путём к модулю.

**Решение:**
```bash
# Обновите конфигурацию
python scripts/install_mem_agent.py
```

Проверьте, что в `data/mcp_servers/mem-agent.json`:
```json
{
  "args": ["-m", "src.agents.mcp.mem_agent_server"]  // ✓ ПРАВИЛЬНО
}
```

А НЕ:
```json
{
  "args": ["-m", "src.mem_agent.server"]  // ✗ НЕПРАВИЛЬНО
}
```

---

### Проблема: Пустая директория data/mcp_servers/

**Причина:** Конфигурация не была создана.

**Решение:**
```bash
python scripts/install_mem_agent.py
```

---

### Проблема: Неправильные пути в .qwen/settings.json

**Причина:** Старая конфигурация с абсолютными путями.

**Решение:**
```bash
# Удалите старую
rm ~/.qwen/settings.json

# Создайте новую
python -c "from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config; setup_qwen_mcp_config(global_config=True)"
```

---

## 📊 Сравнение конфигураций

| Параметр | Python агенты | Qwen CLI |
|----------|---------------|----------|
| **Файл конфига** | `data/mcp_servers/mem-agent.json` | `~/.qwen/settings.json` |
| **Формат запуска** | Module (`-m src.agents.mcp.mem_agent_server`) | Script (`src/agents/mcp/mem_agent_server.py`) |
| **Command** | `python` | `python3` |
| **Transport** | stdio | stdio |
| **Запуск** | `MCPServerManager` в `main.py` | Qwen CLI subprocess |
| **Автостарт** | При `AGENT_ENABLE_MCP_MEMORY=true` | При запуске Qwen CLI |

---

## 📝 См. также

- [MCP Server Implementation](src/agents/mcp/mem_agent_server.py)
- [Qwen Config Generator](src/agents/mcp/qwen_config_generator.py)
- [Installation Script](scripts/install_mem_agent.py)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)