# MCP Quick Start Guide

## Что было добавлено

Добавлена полная поддержка MCP (Model Context Protocol) протокола для автономного агента:

### ✅ Основные компоненты

1. **MCP Client** (`src/agents/mcp/client.py`)
   - Подключение к MCP серверам через stdio
   - JSON-RPC коммуникация
   - Управление lifecycle серверов

2. **Base MCP Tool** (`src/agents/mcp/base_mcp_tool.py`)
   - Базовый класс для MCP инструментов
   - Автоматическое управление соединениями
   - Включение/выключение инструментов

3. **Memory Agent Tool** (`src/agents/mcp/memory_agent_tool.py`)
   - Интеграция с mem-agent-mcp сервером
   - Семантическая память для агента
   - Хранение и поиск контекста между сессиями

### ✅ Встроенные MCP инструменты

**Memory Agent** - управление памятью агента:
- `mcp_memory_agent` - универсальный инструмент (store, search, list)
- `memory_store` - сохранение памяти
- `memory_search` - поиск в памяти

Использует модель: https://huggingface.co/driaforall/mem-agent
Через MCP сервер: https://github.com/firstbatchxyz/mem-agent-mcp

## Быстрый старт

### 1. Установка MCP сервера

```bash
npm install -g @firstbatch/mem-agent-mcp
```

### 2. Настройка конфигурации

В `config.yaml` или переменных окружения:

```yaml
# Включить MCP поддержку
AGENT_ENABLE_MCP: true

# Включить memory agent
AGENT_ENABLE_MCP_MEMORY: true

# Настройки памяти
MCP_MEMORY_PROVIDER: "openai"
MCP_MEMORY_MODEL: "gpt-4"
```

В `.env`:
```bash
OPENAI_API_KEY=your_key_here
```

### 3. Использование в коде

```python
from src.agents.autonomous_agent import AutonomousAgent
from src.agents.llm_connectors import OpenAIConnector

# Создать агента с MCP
agent = AutonomousAgent(
    llm_connector=OpenAIConnector(api_key="..."),
    enable_mcp=True,
    enable_mcp_memory=True
)

# Сохранить память
await agent.tool_manager.execute(
    "memory_store",
    {
        "content": "Пользователь предпочитает Python для бэкенда",
        "tags": ["preferences", "programming"]
    }
)

# Искать в памяти
result = await agent.tool_manager.execute(
    "memory_search",
    {
        "query": "Какие предпочтения по программированию?",
        "limit": 5
    }
)
```

## Примеры

Смотрите полный пример: `examples/mcp_memory_agent_example.py`

```bash
python examples/mcp_memory_agent_example.py
```

## Документация

- **Пользовательская документация**: `docs_site/agents/mcp-tools.md`
- **Техническая документация**: `src/agents/mcp/README.md`
- **Полное описание реализации**: `MCP_IMPLEMENTATION_SUMMARY.md`

## Создание своих MCP инструментов

### Шаг 1: Создать класс инструмента

```python
# src/agents/mcp/my_tool.py

from .base_mcp_tool import BaseMCPTool
from .client import MCPServerConfig

class MyTool(BaseMCPTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Описание инструмента"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    
    @property
    def mcp_server_config(self) -> MCPServerConfig:
        return MCPServerConfig(
            command="npx",
            args=["@your/mcp-server"],
            env=os.environ.copy()
        )
    
    @property
    def mcp_tool_name(self) -> str:
        return "tool_name_in_server"

ALL_TOOLS = [MyTool()]
```

### Шаг 2: Зарегистрировать в registry

В `src/agents/tools/registry.py`:

```python
if enable_mcp and config.get("enable_my_tool", False):
    from ..mcp import my_tool
    for tool in my_tool.ALL_TOOLS:
        tool.enable()
    manager.register_many(my_tool.ALL_TOOLS)
```

### Шаг 3: Добавить настройки

В `config/settings.py`:

```python
AGENT_ENABLE_MY_TOOL: bool = Field(
    default=False,
    description="Enable my custom MCP tool"
)
```

## Архитектура

```
Autonomous Agent
    ↓
Tool Manager
    ↓
BaseMCPTool (можно включать/выключать)
    ↓
MCPClient (JSON-RPC over stdio)
    ↓
MCP Server (Node.js процесс)
    ↓
External APIs (OpenAI, Anthropic, etc.)
```

## Что изменено

### Новые файлы (8):
- `src/agents/mcp/__init__.py`
- `src/agents/mcp/client.py`
- `src/agents/mcp/base_mcp_tool.py`
- `src/agents/mcp/memory_agent_tool.py`
- `src/agents/mcp/README.md`
- `examples/mcp_memory_agent_example.py`
- `docs_site/agents/mcp-tools.md`
- `MCP_IMPLEMENTATION_SUMMARY.md`

### Изменённые файлы (6):
- `config/settings.py` - добавлены MCP настройки
- `config.example.yaml` - добавлена секция MCP
- `src/agents/tools/registry.py` - интеграция MCP
- `src/agents/autonomous_agent.py` - поддержка MCP параметров
- `src/agents/agent_factory.py` - конфигурация MCP
- `pyproject.toml` - опциональные зависимости

## Возможности

✅ **Подключение любых MCP серверов** - гибкая архитектура  
✅ **Встроенные MCP инструменты** - memory agent из коробки  
✅ **Включение/выключение** - как обычные инструменты  
✅ **Семантическая память** - агент помнит контекст между сессиями  
✅ **Расширяемость** - легко добавлять свои MCP инструменты  
✅ **Production-ready** - обработка ошибок, логирование, документация  

## Требования

- Node.js и npm (для MCP серверов)
- MCP сервер (например, mem-agent-mcp)
- API ключ (OpenAI или Anthropic для memory agent)

## Troubleshooting

### Ошибка: "Server process exited immediately"

**Решение:**
1. Проверьте Node.js: `node --version`
2. Проверьте установку: `npm list -g @firstbatch/mem-agent-mcp`
3. Попробуйте запустить вручную: `npx @firstbatch/mem-agent-mcp`

### Ошибка: "API key not found"

**Решение:**
```bash
export OPENAI_API_KEY=your_key_here
```

## Ссылки

- [MCP Protocol](https://modelcontextprotocol.io/)
- [mem-agent Model](https://huggingface.co/driaforall/mem-agent)
- [mem-agent-mcp Server](https://github.com/firstbatchxyz/mem-agent-mcp)

---

**Готово!** 🎉 Теперь у вашего агента есть:
- Поддержка MCP протокола
- Встроенный memory agent инструмент
- Возможность подключать любые MCP тулзы
