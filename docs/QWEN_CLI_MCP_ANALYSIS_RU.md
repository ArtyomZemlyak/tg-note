# Анализ: Взаимодействие Qwen Code CLI с MCP серверами

## Краткий ответ

**НЕТ, вызов MCP серверов через Qwen Code CLI в текущей реализации НЕ РАБОТАЕТ.**

Даже если мы передадим описание MCP инструментов в промпт для qwen CLI, они не смогут быть вызваны во время работы агента.

## Почему это так?

### Архитектура Qwen Code CLI Agent

```
┌─────────────┐
│   Python    │
│  Runtime    │
│             │
│ ┌─────────┐ │
│ │  MCP    │ │  ← MCP tools существуют здесь (Python)
│ │ Tools   │ │
│ └─────────┘ │
│             │
│ ┌─────────┐ │
│ │ Qwen    │ │
│ │ CLI     │ ├──┐
│ │ Agent   │ │  │
│ └─────────┘ │  │
└─────────────┘  │
                 │ subprocess.run()
                 │ stdin/stdout
                 ▼
         ┌───────────────┐
         │   Node.js     │
         │   Process     │
         │               │
         │  qwen CLI     │  ← Отдельный процесс, НЕ имеет доступа к Python
         │  (агентная    │
         │   система)    │
         └───────────────┘
              ▲     │
              │     │
         stdin│     │stdout
              │     │
              └─────┘
```

### Проблема

1. **Qwen Code CLI** - это **отдельный Node.js процесс**, который запускается через `subprocess`
2. **MCP tools** - это **Python объекты** в runtime нашего приложения
3. **Нет моста** между Node.js процессом и Python MCP tools

### Что происходит сейчас

#### QwenCodeCLIAgent.process()

```python
# Шаг 1: Подготовка промпта (с описанием MCP tools)
prompt = await self._prepare_prompt_async(content)
# В промпте есть текст:
# """
# # Available MCP Tools
# 
# ## MCP Server: mem-agent
# 
# ### mcp_mem_agent_store_memory
# - **Description**: Store information in memory
# ...
# """

# Шаг 2: Запуск qwen CLI как subprocess
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd=self.working_directory,
    env=env
)

# Шаг 3: Передача промпта в stdin
stdout, stderr = await process.communicate(input=prompt_text.encode('utf-8'))

# Шаг 4: Получение результата из stdout
result = stdout.decode('utf-8').strip()
```

### Что делает qwen CLI внутри

1. Получает промпт через stdin
2. Запускает свою LLM (обычно Qwen модель)
3. LLM видит описание MCP tools в промпте
4. LLM **может решить** вызвать MCP tool (например, `mcp_mem_agent_store_memory`)
5. **НО**: qwen CLI не знает, как вызвать этот tool!
   - У qwen CLI есть свои встроенные tools: `web_search`, `git`, `github`, `shell`
   - Эти tools реализованы в Node.js коде qwen CLI
   - MCP tools **не зарегистрированы** в qwen CLI
   - **Нет механизма** для вызова Python функций из Node.js процесса

### Сравнение: AutonomousAgent vs QwenCodeCLIAgent

#### AutonomousAgent (РАБОТАЕТ ✅)

```
┌────────────────────────────────────────┐
│         Python Runtime                 │
│                                        │
│  ┌──────────────┐                     │
│  │ Autonomous   │                     │
│  │   Agent      │                     │
│  └──────┬───────┘                     │
│         │                              │
│         ▼                              │
│  ┌──────────────┐                     │
│  │ ToolManager  │                     │
│  └──────┬───────┘                     │
│         │                              │
│         ├─────► FileTools             │
│         ├─────► WebSearchTool         │
│         ├─────► GitTools              │
│         ├─────► DynamicMCPTool ✅     │  ← MCP tools доступны!
│         │       │                      │
│         │       └─────► MCPClient     │
│         │               │              │
│         │               └─────► MCP   │
│         │                       Server│
│         │                              │
└─────────┴──────────────────────────────┘
```

**Как это работает:**
1. LLM получает system prompt с описанием MCP tools
2. LLM решает вызвать MCP tool
3. AutonomousAgent через ToolManager выполняет Python код
4. DynamicMCPTool вызывает MCPClient
5. MCPClient общается с MCP сервером
6. Результат возвращается обратно в AutonomousAgent

#### QwenCodeCLIAgent (НЕ РАБОТАЕТ ❌)

```
┌────────────────────────────────────────┐
│         Python Runtime                 │
│                                        │
│  ┌──────────────┐                     │
│  │  Qwen CLI    │                     │
│  │   Agent      │                     │
│  └──────┬───────┘                     │
│         │                              │
│         │ subprocess                   │
│         ▼                              │
│  ═══════════════════════════════════  │  ← Граница процессов
│                                        │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│       Node.js Process (qwen CLI)       │
│                                        │
│  ┌──────────────┐                     │
│  │   Qwen LLM   │                     │
│  └──────┬───────┘                     │
│         │                              │
│         │ "Хочу вызвать                │
│         │  mcp_mem_agent_store_memory" │
│         ▼                              │
│  ┌──────────────┐                     │
│  │ Tool         │                     │
│  │ Executor     │                     │
│  └──────┬───────┘                     │
│         │                              │
│         ├─────► web_search ✅         │
│         ├─────► git ✅                │
│         ├─────► github ✅             │
│         ├─────► shell ✅              │
│         ├─────► mcp_* ❌              │  ← НЕТ ТАКОГО TOOL!
│         │                              │
│         ▼                              │
│     [ERROR]                            │
│                                        │
└────────────────────────────────────────┘

MCP Tools живут в Python, но недоступны ⚠️
┌────────────────┐
│ DynamicMCPTool │
│ MCPClient      │
│ MCP Server     │
└────────────────┘
```

## Детальный анализ кода

### 1. Как MCP tools добавляются в промпт

**Файл: `src/agents/qwen_code_cli_agent.py`**

```python
async def _prepare_prompt_async(self, content: Dict) -> str:
    # ...
    base_prompt = CONTENT_PROCESSING_PROMPT_TEMPLATE.format(...)
    
    # Добавляем описание MCP tools
    mcp_description = await self.get_mcp_tools_description()
    if mcp_description:
        return f"{base_prompt}{mcp_description}"
    
    return base_prompt
```

**Файл: `src/agents/mcp/tools_description.py`**

```python
async def get_mcp_tools_description(user_id: Optional[int] = None) -> str:
    """
    Генерирует описание MCP tools для промпта
    """
    # Подключается к MCP серверам
    registry_client = MCPRegistryClient(servers_dir=servers_dir, user_id=user_id)
    registry_client.initialize()
    connected_clients = await registry_client.connect_all_enabled()
    
    # Получает список tools
    for server_name, client in connected_clients.items():
        available_tools = await client.list_tools()
        # Форматирует описание
        # ...
    
    return description  # Текстовое описание для промпта
```

### 2. Как qwen CLI получает промпт

**Файл: `src/agents/qwen_code_cli_agent.py`**

```python
async def _execute_qwen_cli(self, prompt: str) -> str:
    """
    Выполняет qwen CLI через subprocess
    """
    # Запуск Node.js процесса
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=self.working_directory,
        env=env
    )
    
    # Передача промпта
    stdout, stderr = await process.communicate(
        input=prompt_text.encode('utf-8')
    )
    
    # Получение результата
    result = stdout.decode('utf-8').strip()
    return result
```

### 3. Что делает AutonomousAgent (для сравнения)

**Файл: `src/agents/autonomous_agent.py`**

```python
async def _execute_tool(self, decision: AgentDecision) -> ToolExecution:
    """
    Выполняет tool ВНУТРИ Python runtime
    """
    tool_name = decision.tool_name  # например, "mcp_mem_agent_store_memory"
    params = decision.tool_params
    
    # ToolManager знает о всех tools, включая MCP
    if not self.tool_manager.has(tool_name):
        return ToolExecution(success=False, error="Tool not found")
    
    # ВЫЗОВ Python функции
    result = await self.tool_manager.execute(tool_name, params)
    
    return ToolExecution(
        tool_name=tool_name,
        params=params,
        result=result,
        success=True
    )
```

**Файл: `src/agents/mcp/dynamic_mcp_tools.py`**

```python
class DynamicMCPTool(BaseTool):
    """
    MCP tool, зарегистрированный в ToolManager
    """
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """
        ВЫЗОВ MCP сервера через Python
        """
        # Вызов MCP сервера
        result = await self._mcp_client.call_tool(self._original_tool_name, params)
        
        return {
            "success": True,
            "result": result.get("result")
        }
```

## Почему это критическая проблема

### Для пользователя

1. **Ожидание**: "Я включил MCP, qwen CLI должен использовать MCP tools"
2. **Реальность**: qwen CLI не может вызывать MCP tools
3. **Результат**: Функциональность не работает, но нет явной ошибки

### Технически

1. **Описание есть** - MCP tools описаны в промпте
2. **LLM видит** - модель может "решить" использовать MCP tool
3. **Выполнения нет** - tool call невозможен из-за границы процессов
4. **Без fallback** - нет механизма для проксирования вызовов обратно в Python

## Возможные решения

### Решение 1: Запретить MCP для QwenCodeCLIAgent ✅ (Простое)

**Изменить инициализацию:**

```python
class QwenCodeCLIAgent(BaseAgent):
    def __init__(self, ...):
        # ...
        
        # MCP НЕ поддерживается для qwen CLI
        if config and config.get("enable_mcp"):
            logger.warning(
                "[QwenCodeCLIAgent] MCP tools are not supported with Qwen CLI. "
                "Use AutonomousAgent for MCP support. Disabling MCP."
            )
            self.enable_mcp = False
        else:
            self.enable_mcp = False
```

**Плюсы:**
- Честно по отношению к пользователю
- Предотвращает ложные ожидания
- Не ломает существующий код

**Минусы:**
- Функциональность недоступна для qwen CLI

### Решение 2: MCP Server Bridge (Сложное) ⚠️

Создать HTTP/WebSocket сервер, который:
1. Запускается в Python runtime
2. Предоставляет MCP tools через HTTP API
3. qwen CLI вызывает этот API как внешний сервис

**Архитектура:**

```
┌─────────────────────────────────────────┐
│          Python Runtime                 │
│                                         │
│  ┌──────────────┐    ┌──────────────┐  │
│  │ Qwen CLI     │    │ MCP Bridge   │  │
│  │ Agent        │    │ HTTP Server  │  │
│  └──────┬───────┘    │ (FastAPI)    │  │
│         │            └───────┬──────┘  │
│         │                    │          │
│         │ subprocess         │          │
│         ▼                    │          │
│  ═══════════════════════════│══════════│
│                              │          │
└──────────────────────────────┼──────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌───────────────┐
│   Node.js       │   │ MCP Tools     │
│  qwen CLI       │   │ Registry      │
│                 │   │               │
│  HTTP Client ───┼──►│ DynamicMCP    │
│  calls          │   │ Tools         │
│  localhost:8000 │   │               │
└─────────────────┘   └───────┬───────┘
                              │
                              ▼
                      ┌───────────────┐
                      │  MCP Servers  │
                      └───────────────┘
```

**Плюсы:**
- MCP tools доступны для qwen CLI
- Работает через стандартный HTTP

**Минусы:**
- Сложная реализация
- Требует запуск дополнительного сервера
- Проблемы с безопасностью (localhost доступ)
- Дополнительная задержка (HTTP overhead)

### Решение 3: Использовать AutonomousAgent ✅ (Рекомендуется)

**Для MCP использовать AutonomousAgent:**

```yaml
# config.yaml

# Для работы с MCP
AGENT_TYPE: "autonomous"
AGENT_ENABLE_MCP: true

# Или для работы без MCP
AGENT_TYPE: "qwen_code_cli"
```

**Плюсы:**
- Работает из коробки
- Полная поддержка MCP
- Нативная интеграция
- Нет дополнительной сложности

**Минусы:**
- Нельзя использовать qwen CLI с MCP

## Рекомендации

### Для разработчиков

1. **Документировать** ограничение в README и документации
2. **Добавить warning** при попытке включить MCP для qwen CLI
3. **Рекомендовать** AutonomousAgent для MCP use cases

### Для пользователей

**Если нужен MCP:**
```yaml
AGENT_TYPE: "autonomous"
AGENT_MODEL: "gpt-3.5-turbo"  # или любая OpenAI-совместимая модель
AGENT_ENABLE_MCP: true
```

**Если нужен qwen CLI:**
```yaml
AGENT_TYPE: "qwen_code_cli"
# MCP автоматически отключен
# Доступны встроенные tools: web_search, git, github, shell
```

## Выводы

### Текущее состояние

| Агент | MCP Support | Причина |
|-------|-------------|---------|
| **AutonomousAgent** | ✅ Да | Все в Python runtime, нативная интеграция |
| **QwenCodeCLIAgent** | ❌ Нет | Отдельный Node.js процесс, нет доступа к Python MCP tools |
| **StubAgent** | ❌ Нет | Тестовый агент без AI |

### Почему не работает для qwen CLI

1. **Граница процессов**: qwen CLI = Node.js, MCP tools = Python
2. **Нет моста**: Нет механизма для вызова Python из Node.js subprocess
3. **Описание ≠ Реализация**: Описание в промпте не делает tool доступным для вызова

### Правильный подход

- **Для MCP**: Использовать **AutonomousAgent**
- **Для qwen CLI**: Использовать встроенные tools, **без MCP**
- **Документация**: Четко указать совместимость агентов и функций

## Дальнейшие шаги

### Краткосрочные (рекомендуется)

1. ✅ Добавить проверку и warning при попытке использовать MCP с qwen CLI
2. ✅ Обновить документацию с таблицей совместимости
3. ✅ Добавить примеры для обоих сценариев

### Долгосрочные (опционально)

1. ⚠️ Рассмотреть MCP Bridge через HTTP (если критически нужно)
2. ⚠️ Изучить альтернативы: MCP серверы в Node.js?
3. ⚠️ Вклад в qwen-code для поддержки external tools?

## Файлы для изменения

1. **src/agents/qwen_code_cli_agent.py**
   - Добавить проверку enable_mcp с warning
   - Форсировать enable_mcp = False

2. **docs/QWEN_CLI_MCP_COMPATIBILITY.md** (новый)
   - Документация совместимости
   - Примеры использования

3. **README.md**
   - Таблица совместимости агентов
   - Рекомендации по выбору агента

4. **docs_site/agents/qwen-code-cli.md**
   - Секция "MCP Support"
   - Ссылка на AutonomousAgent для MCP

## Заключение

Передача описания MCP tools в промпт qwen CLI **технически работает**, но **практически бесполезна**, потому что:

1. ❌ qwen CLI не может вызвать эти tools (они в другом процессе)
2. ❌ Нет механизма для проксирования вызовов
3. ❌ LLM может "попытаться" вызвать, но получит ошибку

**Решение**: Использовать **AutonomousAgent** для работы с MCP, а **QwenCodeCLIAgent** - для работы со встроенными tools.