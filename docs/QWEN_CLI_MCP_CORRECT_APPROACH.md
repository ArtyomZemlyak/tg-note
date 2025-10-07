# Правильный подход: MCP с Qwen Code CLI

## Важное открытие! 🎯

**Qwen Code CLI ИМЕЕТ встроенную поддержку MCP!**

Предыдущий анализ был **частично неверным**. Проблема не в том, что qwen CLI не поддерживает MCP, а в том, что **подход к интеграции отличается**.

## Два разных подхода к MCP

### Подход 1: Python MCP Tools (текущая реализация)

```
┌─────────────────────────────────────┐
│       Python Runtime                │
│                                     │
│  ┌──────────────────┐               │
│  │ AutonomousAgent  │               │
│  └────────┬─────────┘               │
│           │                         │
│           ▼                         │
│  ┌──────────────────┐               │
│  │  ToolManager     │               │
│  └────────┬─────────┘               │
│           │                         │
│           ├─► DynamicMCPTool       │  ← Python wrapper
│           │   │                     │
│           │   └─► MCPClient        │  ← Python MCP client
│           │       │                 │
│           │       └─► MCP Server   │  ← Subprocess
│           │           (Python)     │
└───────────┴─────────────────────────┘
```

**Характеристики:**
- MCP клиент реализован на Python
- MCP tools обернуты в DynamicMCPTool
- Интеграция через ToolManager
- ✅ Работает с AutonomousAgent
- ❌ НЕ работает с QwenCodeCLIAgent (граница процессов)

---

### Подход 2: Qwen CLI Native MCP (правильный для qwen CLI)

```
┌─────────────────────────────────────┐
│       Python Runtime                │
│                                     │
│  ┌──────────────────┐               │
│  │ QwenCodeCLIAgent │               │
│  └────────┬─────────┘               │
│           │                         │
│           │ subprocess              │
└───────────┼─────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│   Node.js Process (qwen CLI)        │
│                                     │
│  ┌──────────────────┐               │
│  │  Qwen LLM        │               │
│  └────────┬─────────┘               │
│           │                         │
│           ▼                         │
│  ┌──────────────────┐               │
│  │ MCP Client       │  ← Node.js    │
│  │ (built-in)       │     MCP client│
│  └────────┬─────────┘               │
│           │                         │
│           ├─► MCP Server 1 ✅      │  ← Отдельный процесс
│           ├─► MCP Server 2 ✅      │
│           └─► MCP Server 3 ✅      │
└─────────────────────────────────────┘
            ▲
            │ stdio/SSE/HTTP
            │
┌───────────┴─────────────────────────┐
│   MCP Servers (external processes)  │
│                                     │
│  - Python MCP server                │
│  - Node.js MCP server               │
│  - Docker MCP server                │
│  - HTTP/SSE MCP server              │
└─────────────────────────────────────┘
```

**Характеристики:**
- MCP клиент **встроен в qwen CLI** (Node.js)
- MCP серверы запускаются как **внешние процессы**
- Конфигурация через `mcpServers` в qwen settings
- ✅ **РАБОТАЕТ** с QwenCodeCLIAgent!
- ✅ Поддерживает stdio, SSE, HTTP

## Почему предыдущий подход не работал

### Проблема

Мы пытались:
1. Запустить MCP серверы из Python кода
2. Передать **описание** tools через промпт в qwen CLI
3. Ожидать, что qwen CLI вызовет эти Python MCP tools

**Это не работает**, потому что:
- Qwen CLI не знает, как подключиться к уже запущенным Python MCP клиентам
- Описание в промпте ≠ реальное подключение к серверу
- Нет bridge между Python MCP client и Node.js qwen CLI

### Правильное решение

Qwen CLI нужно **настроить на подключение к MCP серверам** через конфигурацию:

```json
{
  "mcpServers": {
    "mem-agent": {
      "command": "python",
      "args": ["-m", "mem_agent.mcp_server"],
      "cwd": "/path/to/mem-agent",
      "timeout": 5000
    }
  }
}
```

Тогда qwen CLI:
1. Сам запустит MCP сервер как subprocess
2. Подключится к нему через stdio
3. Получит список tools
4. Сможет их вызывать

## Как интегрировать MCP с Qwen Code CLI

### Шаг 1: MCP сервер должен быть запускаемым процессом

MCP сервер должен работать как **standalone процесс**, а не как Python библиотека.

**Пример структуры:**

```
mem_agent/
├── __init__.py
├── mcp_server.py       ← Точка входа для запуска
└── tools/
    ├── store_memory.py
    └── retrieve_memory.py
```

**mcp_server.py:**
```python
#!/usr/bin/env python3
"""
MCP Server for mem-agent
Runs as standalone process, communicates via stdio
"""
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

async def main():
    server = Server("mem-agent")
    
    @server.tool()
    async def store_memory(content: str, category: str = "general"):
        """Store information in memory"""
        # Implementation
        return {"success": True, "stored": content}
    
    @server.tool()
    async def retrieve_memory(query: str):
        """Retrieve information from memory"""
        # Implementation
        return {"success": True, "results": [...]}
    
    # Run server via stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())
```

### Шаг 2: Конфигурация Qwen CLI

**Файл**: `~/.config/qwen/settings.json` или project `.qwen/settings.json`

```json
{
  "mcpServers": {
    "mem-agent": {
      "command": "python",
      "args": ["-m", "mem_agent.mcp_server"],
      "cwd": "/path/to/mem-agent",
      "timeout": 5000,
      "trust": true,
      "description": "Memory agent for storing and retrieving information"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
      "description": "Filesystem operations"
    }
  },
  "allowMCPServers": ["mem-agent", "filesystem"]
}
```

### Шаг 3: Запуск Qwen CLI

Qwen CLI автоматически:
1. Подключится к MCP серверам из конфигурации
2. Получит список tools
3. Сделает их доступными для LLM

```bash
# Просто запускаем qwen CLI
qwen

# Или через наш Python код
agent = QwenCodeCLIAgent(
    working_directory="/path/to/kb",
    enable_web_search=True
)
result = await agent.process(content)
```

## Преимущества встроенной поддержки MCP в qwen CLI

✅ **Нативная интеграция** - MCP встроен в qwen CLI  
✅ **Автоматическое обнаружение** - tools автоматически доступны  
✅ **Множественные серверы** - можно подключить много MCP серверов  
✅ **Разные транспорты** - stdio, SSE, HTTP  
✅ **Конфликтов нет** - автоматический prefixing имен  
✅ **Безопасность** - `trust`, `includeTools`, `excludeTools`  

## Обновленное сравнение подходов

### AutonomousAgent + Python MCP

```yaml
AGENT_TYPE: "autonomous"
AGENT_ENABLE_MCP: true
```

**Как работает:**
- Python код запускает и управляет MCP серверами
- MCP tools обернуты в DynamicMCPTool
- Все в одном Python процессе

**Плюсы:**
- ✅ Полный контроль из Python
- ✅ Динамическая регистрация tools
- ✅ Легко дебажить

**Минусы:**
- ❌ Только для AutonomousAgent
- ❌ Требует Python MCP client
- ❌ Не работает с qwen CLI

---

### QwenCodeCLIAgent + Qwen Native MCP

```json
// .qwen/settings.json
{
  "mcpServers": {
    "mem-agent": {
      "command": "python",
      "args": ["-m", "mem_agent.mcp_server"]
    }
  }
}
```

**Как работает:**
- Qwen CLI подключается к MCP серверам
- MCP серверы - standalone процессы
- Конфигурация через qwen settings

**Плюсы:**
- ✅ Работает с qwen CLI
- ✅ Нативная поддержка
- ✅ Множественные транспорты
- ✅ Продакшен-ready

**Минусы:**
- ❌ Требует standalone MCP серверы
- ❌ Конфигурация вне Python кода
- ❌ Меньше контроля из Python

## Что нужно сделать для интеграции

### 1. Создать standalone MCP серверы

Превратить текущие Python MCP tools в запускаемые процессы:

```
data/mcp_servers/
├── user_123/
│   └── mem-agent/
│       ├── __init__.py
│       ├── mcp_server.py      ← Точка входа
│       └── config.json         ← Настройки сервера
└── shared/
    └── filesystem/
        ├── mcp_server.py
        └── config.json
```

### 2. Генерировать qwen settings

Создать функцию для генерации `.qwen/settings.json`:

```python
def generate_qwen_mcp_config(user_id: int, kb_path: str) -> dict:
    """Generate qwen CLI MCP configuration"""
    
    # Обнаружить MCP серверы пользователя
    mcp_servers_dir = Path(f"data/mcp_servers/user_{user_id}")
    
    config = {"mcpServers": {}}
    
    # Для каждого MCP сервера
    for server_dir in mcp_servers_dir.iterdir():
        if server_dir.is_dir():
            server_name = server_dir.name
            
            config["mcpServers"][server_name] = {
                "command": "python",
                "args": ["-m", f"{server_dir}/mcp_server"],
                "cwd": str(server_dir),
                "timeout": 5000,
                "trust": True
            }
    
    # Сохранить в .qwen/settings.json в KB
    qwen_config_path = Path(kb_path) / ".qwen" / "settings.json"
    qwen_config_path.parent.mkdir(exist_ok=True)
    qwen_config_path.write_text(json.dumps(config, indent=2))
    
    return config
```

### 3. Обновить QwenCodeCLIAgent

```python
class QwenCodeCLIAgent(BaseAgent):
    def __init__(self, ...):
        # ...
        
        # Генерировать qwen MCP config если MCP включен
        if self.enable_mcp and self.user_id:
            self._setup_qwen_mcp_config()
    
    def _setup_qwen_mcp_config(self):
        """Setup qwen CLI MCP configuration"""
        config = generate_qwen_mcp_config(
            user_id=self.user_id,
            kb_path=self.working_directory
        )
        logger.info(f"Generated qwen MCP config: {len(config['mcpServers'])} servers")
```

## Пример: mem-agent как MCP сервер для qwen CLI

### Структура

```
mem_agent/
├── __init__.py
├── mcp_server.py       ← Standalone server
├── storage.py          ← Storage backend
└── requirements.txt
```

### mcp_server.py

```python
#!/usr/bin/env python3
"""
Mem-agent MCP Server
Provides memory storage and retrieval tools
"""
import asyncio
import json
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .storage import MemoryStorage

async def main():
    # Initialize storage
    storage = MemoryStorage(data_dir="./data/memory")
    
    # Create MCP server
    server = Server("mem-agent")
    
    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="store_memory",
                description="Store information in memory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Content to store"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category for organization",
                            "default": "general"
                        }
                    },
                    "required": ["content"]
                }
            ),
            Tool(
                name="retrieve_memory",
                description="Retrieve information from memory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "store_memory":
            result = await storage.store(
                content=arguments["content"],
                category=arguments.get("category", "general")
            )
            return [TextContent(type="text", text=json.dumps(result))]
        
        elif name == "retrieve_memory":
            results = await storage.retrieve(
                query=arguments["query"]
            )
            return [TextContent(type="text", text=json.dumps(results))]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
```

### Qwen конфигурация

```json
{
  "mcpServers": {
    "mem-agent": {
      "command": "python",
      "args": ["-m", "mem_agent.mcp_server"],
      "cwd": "/path/to/mem-agent",
      "timeout": 5000,
      "trust": true,
      "description": "Memory storage and retrieval"
    }
  }
}
```

## Обновленные рекомендации

### Для AutonomousAgent

**Использовать Python MCP approach:**
```yaml
AGENT_TYPE: "autonomous"
AGENT_ENABLE_MCP: true
```

**Почему:**
- Полный контроль из Python
- Динамическая регистрация
- Все в одном процессе

---

### Для QwenCodeCLIAgent

**Использовать Qwen native MCP:**
```json
// .qwen/settings.json
{
  "mcpServers": {
    "mem-agent": {...},
    "filesystem": {...}
  }
}
```

**Почему:**
- ✅ **РАБОТАЕТ** с qwen CLI
- Нативная поддержка
- Продакшен-ready

## Выводы

### Исправление предыдущего анализа

**Было неверно:**
> "MCP не работает с qwen CLI из-за границы процессов"

**Верно:**
> "Python MCP client не работает с qwen CLI, но **qwen CLI имеет свой встроенный MCP client** и может подключаться к MCP серверам через конфигурацию"

### Два валидных подхода

| Подход | Агент | Реализация |
|--------|-------|------------|
| **Python MCP** | AutonomousAgent | Python MCP client + DynamicMCPTool |
| **Qwen Native MCP** | QwenCodeCLIAgent | Qwen встроенный MCP client |

**Оба работают!** Но для разных агентов и с разными архитектурами.

## Следующие шаги

1. ✅ Обновить документацию с правильной информацией
2. ⏭️ Реализовать standalone MCP серверы
3. ⏭️ Добавить генерацию qwen settings.json
4. ⏭️ Обновить QwenCodeCLIAgent для поддержки MCP
5. ⏭️ Протестировать интеграцию

## Ссылки

- [Qwen Code CLI Configuration](https://github.com/QwenLM/qwen-code/blob/main/docs/cli/configuration.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)