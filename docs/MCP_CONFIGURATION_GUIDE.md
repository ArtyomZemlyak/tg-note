# MCP Configuration Guide

## Две конфигурации MCP серверов

В проекте используется **две разные конфигурации** для MCP серверов, в зависимости от типа агента:

### 1. `data/mcp_servers/*.json` - для Python агентов

**Используется в:**
- `AutonomousAgent` (с DynamicMCP)
- Любые агенты, использующие Python MCP SDK напрямую

**Формат:**
```json
{
  "name": "mem-agent",
  "description": "Agent's personal note-taking and search system",
  "command": "python3",
  "args": [
    "-m",
    "src.mem_agent.server"
  ],
  "env": {
    "MEM_AGENT_MEMORY_POSTFIX": "memory"
  },
  "working_dir": "/workspace",
  "enabled": true
}
```

**Особенности:**
- Используется абсолютный путь в `working_dir` (т.к. Python агенты запускаются из Python кода)
- Конфигурация загружается через `MCPServerRegistry`
- Файлы хранятся в `data/mcp_servers/`
- Поддерживает per-user конфигурации в `data/mcp_servers/user_{user_id}/`

**Создание:**
```bash
# Автоматически через скрипт установки
python scripts/install_mem_agent.py

# Или вручную создать JSON файл в data/mcp_servers/
```

---

### 2. `.qwen/settings.json` - для Qwen CLI

**Используется в:**
- `QwenCodeCLIAgent` (использует встроенный MCP клиент Qwen CLI)

**Формат:**
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

**Особенности:**
- Используется **относительный путь** к скрипту (относительно `cwd`)
- `cwd` указывает рабочую директорию проекта
- Конфигурация генерируется автоматически через `QwenMCPConfigGenerator`
- Может быть глобальной (`~/.qwen/settings.json`) или project-specific (`<kb>/.qwen/settings.json`)

**Создание:**
```python
# Автоматически при инициализации QwenCodeCLIAgent с enable_mcp=True
from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config

# Генерация конфигурации
saved_paths = setup_qwen_mcp_config(
    user_id=858138359,
    kb_path=Path("/path/to/kb"),
    global_config=True
)
```

---

## Сравнение конфигураций

| Параметр | `data/mcp_servers/*.json` | `.qwen/settings.json` |
|----------|---------------------------|------------------------|
| **Для кого** | Python агенты (DynamicMCP) | Qwen CLI |
| **Путь к скрипту** | Module path (`-m src.mem_agent.server`) | Относительный путь к файлу |
| **Working dir** | Абсолютный путь | Абсолютный путь в `cwd` |
| **Генерация** | `install_mem_agent.py` | `QwenMCPConfigGenerator` |
| **Расположение** | `data/mcp_servers/` | `~/.qwen/` или `<kb>/.qwen/` |
| **Формат** | Простой JSON | Qwen-специфичный формат |

---

## Пример правильных путей

### ❌ НЕПРАВИЛЬНО (абсолютные пути пользователя):
```json
{
  "command": "/Users/hq-g9fg74y03k/Documents/tg-note/venv/bin/python",
  "args": [
    "/Users/hq-g9fg74y03k/Documents/tg-note/src/agents/mcp/mem_agent_server.py"
  ],
  "cwd": "/Users/hq-g9fg74y03k/Documents/tg-note"
}
```

**Проблемы:**
- Не работает на других системах
- Привязано к конкретному пользователю
- Использует виртуальное окружение конкретной машины

### ✅ ПРАВИЛЬНО (относительные/универсальные пути):
```json
{
  "command": "python3",
  "args": [
    "src/agents/mcp/mem_agent_server.py"
  ],
  "cwd": "/workspace"
}
```

**Преимущества:**
- Работает на любой системе
- Использует `python3` из PATH
- Относительный путь к скрипту (относительно `cwd`)
- Абсолютный `cwd` указывает на корень проекта

---

## Как исправить существующие конфигурации

### Если у вас есть `.qwen/settings.json` с неправильными путями:

1. **Удалите старую конфигурацию:**
   ```bash
   rm -rf ~/.qwen/settings.json
   rm -rf knowledge_base/*/.qwen/settings.json
   ```

2. **Перегенерируйте через Python:**
   ```python
   from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config
   from pathlib import Path
   
   # Для глобальной конфигурации
   setup_qwen_mcp_config(
       user_id=858138359,
       global_config=True
   )
   
   # Для project-specific конфигурации
   setup_qwen_mcp_config(
       user_id=858138359,
       kb_path=Path("/path/to/kb"),
       global_config=False
   )
   ```

3. **Или запустите QwenCodeCLIAgent с enable_mcp=True** - конфигурация создастся автоматически.

---

## Проверка конфигурации

### Проверить `data/mcp_servers/mem-agent.json`:
```bash
cat data/mcp_servers/mem-agent.json
```

Должно быть:
```json
{
  "name": "mem-agent",
  "description": "Agent's personal note-taking and search system",
  "command": "python3",
  "args": ["-m", "src.mem_agent.server"],
  "working_dir": "/workspace",
  "enabled": true
}
```

### Проверить `.qwen/settings.json`:
```bash
cat ~/.qwen/settings.json
# или
cat /path/to/kb/.qwen/settings.json
```

Должно быть:
```json
{
  "mcpServers": {
    "mem-agent": {
      "command": "python3",
      "args": ["src/agents/mcp/mem_agent_server.py"],
      "cwd": "/workspace",
      "timeout": 10000,
      "trust": true,
      "description": "Memory storage and retrieval agent"
    }
  },
  "allowMCPServers": ["mem-agent"]
}
```

---

## Частые ошибки

### 1. Пустая директория `data/mcp_servers/`

**Проблема:** MCP серверы не обнаруживаются Python агентами.

**Решение:**
```bash
# Запустите скрипт установки
python scripts/install_mem_agent.py
```

### 2. Неправильные пути в `.qwen/settings.json`

**Проблема:** Qwen CLI не может запустить MCP сервер.

**Решение:**
```bash
# Удалите старую конфигурацию
rm ~/.qwen/settings.json

# Перегенерируйте
python -c "from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config; setup_qwen_mcp_config(global_config=True)"
```

### 3. Использование абсолютных путей

**Проблема:** Конфигурация не переносима между системами.

**Решение:** Всегда используйте:
- `python3` вместо абсолютного пути к Python
- Относительные пути к скриптам (относительно `cwd`/`working_dir`)
- Абсолютный `cwd`/`working_dir` только для корня проекта

---

## См. также

- [MCP Server Registry](../src/mcp_registry/README.md)
- [Qwen Config Generator](../src/agents/mcp/qwen_config_generator.py)
- [Install mem-agent script](../scripts/install_mem_agent.py)