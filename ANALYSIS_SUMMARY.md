# Анализ: Взаимодействие Qwen Code CLI с MCP серверами

## Краткий ответ на ваш вопрос

**НЕТ**, вызов MCP серверов из Qwen Code CLI **НЕ БУДЕТ РАБОТАТЬ**, даже если передать описание MCP инструментов в промпт.

## Почему?

### Пайплайн, который вы описали

Вы правильно понимаете текущий пайплайн:

1. ✅ **Промпт с описанием MCP серверов** встраивается и передается в qwen code cli
2. ✅ **qwen code cli запускается** как отдельный Node.js процесс
3. ❌ **MCP tools НЕ МОГУТ быть вызваны**, даже если агент их "захочет" вызвать

### Проблема: Граница процессов

```
┌─────────────────────────────────────┐
│       Python Runtime                │  ← Здесь живут MCP tools
│                                     │
│  QwenCodeCLIAgent.process()        │
│         │                           │
│         │ subprocess.run()          │
│         ▼                           │
│  ════════════════════════════════  │  ← ГРАНИЦА ПРОЦЕССОВ
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    Node.js Process (qwen CLI)       │  ← Отдельный процесс
│                                     │
│  - Получает промпт через stdin      │
│  - Видит описание MCP tools         │
│  - Может "решить" их вызвать        │
│  - НО: не может выполнить Python код│
│                                     │
│  Доступные tools:                   │
│  ✅ web_search (Node.js)            │
│  ✅ git (Node.js)                   │
│  ✅ github (Node.js)                │
│  ❌ mcp_* (Python, недоступен!)    │
└─────────────────────────────────────┘
```

## Что происходит на шаге 2

На шаге 2, когда qwen code cli "что-то делает", происходит следующее:

1. **LLM анализирует промпт** - видит описание MCP tools
2. **Может решить вызвать MCP tool** - например, `mcp_mem_agent_store_memory`
3. **Пытается найти этот tool** - ищет в своей системе инструментов
4. **НЕ НАХОДИТ** - потому что MCP tools не зарегистрированы в Node.js процессе
5. **Получает ошибку** или игнорирует

### Почему qwen CLI не может вызвать MCP tools?

- **qwen CLI** = Node.js процесс
- **MCP tools** = Python объекты в родительском процессе
- **Нет моста** между ними
- **Нет IPC** (межпроцессного взаимодействия) для вызова Python функций

## Что РАБОТАЕТ ✅

### AutonomousAgent с MCP

```
┌─────────────────────────────────────┐
│       Python Runtime                │
│  ┌─────────────────────────────┐   │
│  │  AutonomousAgent            │   │
│  │         │                    │   │
│  │         ▼                    │   │
│  │  ┌─────────────┐            │   │
│  │  │ ToolManager │            │   │
│  │  └──────┬──────┘            │   │
│  │         │                    │   │
│  │         ├─► MCP Tools ✅    │   │  ← Все в одном процессе!
│  │         ├─► FileTools       │   │
│  │         ├─► WebSearch       │   │
│  │         └─► GitTools        │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

**Как это работает:**
1. LLM получает описание MCP tools в system prompt
2. LLM решает вызвать MCP tool
3. AutonomousAgent через ToolManager **выполняет Python код**
4. DynamicMCPTool **вызывает MCPClient**
5. MCPClient **общается с MCP сервером**
6. Результат возвращается обратно

## Решение

### Для работы с MCP используйте AutonomousAgent

```yaml
# config.yaml
AGENT_TYPE: "autonomous"
AGENT_MODEL: "gpt-3.5-turbo"  # или любая OpenAI-совместимая модель
AGENT_ENABLE_MCP: true
```

```bash
# .env
OPENAI_API_KEY=sk-proj-...
OPENAI_BASE_URL=https://api.openai.com/v1  # опционально
```

### Для qwen CLI - используйте БЕЗ MCP

```yaml
# config.yaml
AGENT_TYPE: "qwen_code_cli"
# MCP автоматически отключен
# Доступны встроенные tools: web_search, git, github, shell
```

## Что было сделано

1. ✅ **Добавлена проверка** в `QwenCodeCLIAgent.__init__()`:
   - Если пользователь попытается включить MCP для qwen CLI
   - Будет выдано предупреждение в лог
   - MCP будет автоматически отключен

2. ✅ **Создана документация**:
   - `docs/QWEN_CLI_MCP_ANALYSIS_RU.md` - Подробный анализ (RU)
   - `docs/QWEN_CLI_MCP_ANALYSIS_EN.md` - Detailed analysis (EN)
   - `docs/AGENT_MCP_COMPATIBILITY.md` - Таблица совместимости

3. ✅ **Обновлен README.md**:
   - Добавлена таблица совместимости агентов
   - Ясно указано, что MCP работает только с AutonomousAgent
   - Рекомендации по выбору агента

## Сравнение агентов

| Функция | AutonomousAgent | QwenCodeCLIAgent |
|---------|----------------|------------------|
| **Runtime** | Python | Node.js (subprocess) |
| **MCP Tools** | ✅ Да | ❌ Нет |
| **Built-in Tools** | ✅ Да | ✅ Да |
| **Free Tier** | Зависит от API | 2000/день |
| **Setup** | pip install | npm install |

## Рекомендации

### Когда использовать AutonomousAgent

- ✅ Нужны **MCP tools**
- ✅ Есть OpenAI-compatible API ключ
- ✅ Нужна кастомизация инструментов
- ✅ Нужна Python-нативная интеграция

### Когда использовать QwenCodeCLIAgent

- ✅ Нужен **бесплатный тир** (2000 запросов/день)
- ✅ Нужна поддержка **vision модели**
- ✅ Достаточно встроенных инструментов
- ❌ MCP НЕ НУЖЕН

## Файлы для ознакомления

### Документация
- [`docs/QWEN_CLI_MCP_ANALYSIS_RU.md`](docs/QWEN_CLI_MCP_ANALYSIS_RU.md) - Полный анализ
- [`docs/AGENT_MCP_COMPATIBILITY.md`](docs/AGENT_MCP_COMPATIBILITY.md) - Матрица совместимости
- [`README.md`](README.md) - Обновленный README с таблицей

### Код
- [`src/agents/qwen_code_cli_agent.py`](src/agents/qwen_code_cli_agent.py) - Добавлена проверка MCP
- [`src/agents/autonomous_agent.py`](src/agents/autonomous_agent.py) - Работающая интеграция MCP

## Выводы

1. **Описание MCP tools в промпте** - технически работает (текст передается)
2. **Вызов MCP tools** - НЕ работает (нет доступа к Python runtime)
3. **Для MCP** - используйте **AutonomousAgent**
4. **Для qwen CLI** - используйте **БЕЗ MCP**

## Что дальше?

Если критически нужна поддержка MCP в qwen CLI, возможные (сложные) варианты:

1. **HTTP Bridge** - создать HTTP сервер для MCP tools (сложно, медленно)
2. **MCP в Node.js** - переписать MCP tools в Node.js (много работы)
3. **Contribute в qwen-code** - добавить поддержку external tools (зависимость от третьей стороны)

**Рекомендация**: Использовать **AutonomousAgent** для MCP - это самое простое и надежное решение.