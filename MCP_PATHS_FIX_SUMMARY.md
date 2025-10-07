# MCP Paths and Configuration Fix Summary

## Проблемы, которые были обнаружены

### 1. ❌ Неправильные пути в `.qwen/settings.json`

**Было:**
```json
{
  "mcpServers": {
    "mem-agent": {
      "command": "/Users/hq-g9fg74y03k/Documents/tg-note/venv/bin/python",
      "args": [
        "/Users/hq-g9fg74y03k/Documents/tg-note/src/agents/mcp/mem_agent_server.py",
        "--user-id",
        "858138359"
      ],
      "cwd": "/Users/hq-g9fg74y03k/Documents/tg-note"
    }
  }
}
```

**Проблемы:**
- Абсолютные пути к Python из виртуального окружения пользователя
- Абсолютные пути к скриптам конкретной машины
- Не переносимо между системами

### 2. ❌ Пустая директория `data/mcp_servers/`

**Проблема:**
- Папка `data/mcp_servers/` не существовала
- Конфигурация `mem-agent.json` не была создана
- Python агенты не могли обнаружить MCP сервер

---

## Исправления

### ✅ 1. Создана структура `data/mcp_servers/`

**Что сделано:**
```bash
data/mcp_servers/
├── .gitkeep              # Для сохранения структуры в Git
└── mem-agent.json        # Конфигурация для Python агентов
```

**Конфигурация `mem-agent.json`:**
```json
{
  "name": "mem-agent",
  "description": "Agent's personal note-taking and search system",
  "command": "python",
  "args": ["-m", "src.mem_agent.server"],
  "env": {
    "MEM_AGENT_MEMORY_POSTFIX": "memory"
  },
  "working_dir": "/workspace",
  "enabled": true
}
```

### ✅ 2. Исправлен `qwen_config_generator.py`

**Изменения в файле `src/agents/mcp/qwen_config_generator.py`:**

**Было:**
```python
python_exec = sys.executable  # Абсолютный путь к Python

config = {
    "command": python_exec,  # /Users/.../venv/bin/python
    "args": [str(server_script)],  # /Users/.../mem_agent_server.py
    "cwd": str(self.project_root),
}
```

**Стало:**
```python
config = {
    "command": "python3",  # Из PATH
    "args": [
        str(server_script.relative_to(self.project_root).as_posix())
    ],  # Относительный путь: src/agents/mcp/mem_agent_server.py
    "cwd": str(self.project_root),  # /workspace
}
```

**Преимущества:**
- ✅ Использует `python3` из PATH (универсально)
- ✅ Относительный путь к скрипту (переносимо)
- ✅ Работает на любой системе

### ✅ 3. Исправлен `install_mem_agent.py`

**Изменения в файле `scripts/install_mem_agent.py`:**

**Было:**
```python
config = {
    "command": sys.executable,  # Абсолютный путь
    # ...
}
```

**Стало:**
```python
config = {
    "command": "python3",  # Из PATH
    "working_dir": str(workspace_root.resolve()),  # Абсолютный путь
    # ...
}
```

### ✅ 4. Создана документация

**Новый файл:** `docs/MCP_CONFIGURATION_GUIDE.md`

**Содержание:**
- Объяснение двух видов конфигураций MCP серверов
- Сравнительная таблица
- Примеры правильных и неправильных путей
- Инструкции по исправлению существующих конфигураций
- Частые ошибки и решения

---

## Результат

### ✅ Правильная конфигурация для `.qwen/settings.json`:

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

**Преимущества:**
- ✅ Переносимо между системами
- ✅ Не зависит от виртуального окружения
- ✅ Использует относительные пути
- ✅ Работает на любой машине с `python3` в PATH

### ✅ Правильная конфигурация для `data/mcp_servers/mem-agent.json`:

```json
{
  "name": "mem-agent",
  "description": "Agent's personal note-taking and search system",
  "command": "python",
  "args": ["-m", "src.mem_agent.server"],
  "env": {
    "MEM_AGENT_MEMORY_POSTFIX": "memory"
  },
  "working_dir": "/workspace",
  "enabled": true
}
```

---

## Два вида конфигураций MCP

### 1. `data/mcp_servers/*.json` - для Python агентов
- **Используется в:** AutonomousAgent (DynamicMCP)
- **Формат:** Module-based (`-m src.mem_agent.server`)
- **Загружается через:** MCPServerRegistry

### 2. `.qwen/settings.json` - для Qwen CLI
- **Используется в:** QwenCodeCLIAgent
- **Формат:** File-based (относительный путь к файлу)
- **Генерируется через:** QwenMCPConfigGenerator

---

## Проверка

### Проверить `data/mcp_servers/`:
```bash
ls -la data/mcp_servers/
cat data/mcp_servers/mem-agent.json
```

### Сгенерировать `.qwen/settings.json`:
```python
from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config

setup_qwen_mcp_config(
    user_id=858138359,
    global_config=True
)
```

### Проверить `.qwen/settings.json`:
```bash
cat ~/.qwen/settings.json
```

---

## Изменённые файлы

1. ✅ `data/mcp_servers/.gitkeep` - создан
2. ✅ `data/mcp_servers/mem-agent.json` - создан
3. ✅ `src/agents/mcp/qwen_config_generator.py` - исправлен
4. ✅ `scripts/install_mem_agent.py` - исправлен
5. ✅ `docs/MCP_CONFIGURATION_GUIDE.md` - создан
6. ✅ `.gitignore` - уже корректный

---

## Рекомендации

### Для пользователей с неправильной конфигурацией:

1. **Удалите старые конфигурации:**
   ```bash
   rm -rf ~/.qwen/settings.json
   rm -rf knowledge_base/*/.qwen/settings.json
   ```

2. **Перегенерируйте через Python:**
   ```python
   from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config
   setup_qwen_mcp_config(user_id=YOUR_USER_ID, global_config=True)
   ```

3. **Проверьте `data/mcp_servers/`:**
   ```bash
   python scripts/install_mem_agent.py
   ```

---

## См. также

- [MCP Configuration Guide](docs/MCP_CONFIGURATION_GUIDE.md) - подробная документация
- [Qwen Config Generator](src/agents/mcp/qwen_config_generator.py) - генератор конфигурации
- [Install mem-agent](scripts/install_mem_agent.py) - скрипт установки