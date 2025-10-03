# Руководство по автономному агенту

## Обзор

Автономный агент - это система, которая **сама** принимает решения о том, какие действия выполнять для достижения цели.

### Ключевые отличия от предыдущей реализации

#### ❌ Было (QwenCodeAgent - жёсткий план)

```python
# План жёстко закодирован
plan.add_task("Analyze content", priority=1)
plan.add_task("Search web", priority=2)  # Всегда выполняется
plan.add_task("Extract metadata", priority=3)

# Агент НЕ может изменить план
# Агент НЕ решает какие тулзы использовать
```

#### ✅ Стало (AutonomousAgent - динамический план)

```python
# Агент САМ решает что делать на каждом шаге

Iteration 1: LLM → "Нужно создать план" → plan_todo([...])
Iteration 2: LLM → "Нужно проанализировать текст" → analyze_content(text)
Iteration 3: LLM → "Нужен контекст из интернета" → web_search(query)
Iteration 4: LLM → "Достаточно, создаю файл" → file_create(path, content)
Iteration 5: LLM → "Задача выполнена" → END
```

## Архитектура

### Агентский цикл

```
┌─────────────────────────────────────────────────────────────┐
│                      AGENT LOOP                              │
└─────────────────────────────────────────────────────────────┘

START
  │
  ├─► LLM Decision
  │     ↓
  │   ┌─────────────┐
  │   │ Tool Call?  │
  │   └─────────────┘
  │     │         │
  │     │         └─► END → Return Result
  │     ↓
  │   Execute Tool
  │     ↓
  │   Update Context
  │     ↓
  └───┤ Back to LLM
      │
      ├─► Max iterations? → END
      │
      └─► Continue Loop
```

### Компоненты

#### 1. AutonomousAgent (Базовый класс)

```python
class AutonomousAgent(BaseAgent):
    """
    Абстрактный базовый класс
    
    Реализует:
    - Агентский цикл (_agent_loop)
    - Выполнение тулзов (_execute_tool)
    - Управление контекстом
    - Финализацию результата
    
    НЕ реализует:
    - _make_decision() - должна реализовать каждая реализация
    """
```

#### 2. OpenAIAgent (Конкретная реализация)

```python
class OpenAIAgent(AutonomousAgent):
    """
    Агент с OpenAI-compatible API
    
    Использует:
    - Function calling для автоматического вызова тулзов
    - Chat Completions API
    - JSON schema для описания тулзов
    
    Совместим с:
    - OpenAI API
    - Qwen API (dashscope)
    - OpenRouter
    - Любой OpenAI-compatible API
    """
```

#### 3. AgentContext (Контекст выполнения)

```python
@dataclass
class AgentContext:
    """
    Хранит:
    - Задачу
    - Историю выполнения тулзов
    - Ошибки
    
    Используется для:
    - Передачи истории в LLM
    - Логирования
    - Отладки
    """
```

#### 4. AgentDecision (Решение LLM)

```python
@dataclass
class AgentDecision:
    """
    Решение LLM о следующем действии:
    
    - action: TOOL_CALL или END
    - tool_name: какой тулз вызвать
    - tool_params: параметры тулза
    - reasoning: объяснение решения
    - final_result: итоговый результат (если END)
    """
```

## Использование

### Быстрый старт

```python
from src.agents.openai_agent import OpenAIAgent

# 1. Создать агента
agent = OpenAIAgent(
    api_key="your-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    model="qwen-max",
    max_iterations=10
)

# 2. Зарегистрировать тулзы
agent.register_tool("web_search", web_search_handler)
agent.register_tool("file_create", file_create_handler)

# 3. Запустить агента
result = await agent.process({
    "text": "Статья о машинном обучении...",
    "urls": ["https://example.com"]
})

# 4. Получить результат
print(result['markdown'])
print(result['metadata']['tools_used'])
```

### Реализация тулзов

Тулз - это async функция, которая принимает параметры и возвращает результат:

```python
async def web_search_tool(params: dict) -> dict:
    """
    Тулз для поиска в интернете
    
    Args:
        params: {"query": "поисковый запрос"}
    
    Returns:
        {"success": True, "results": [...]}
    """
    query = params.get("query", "")
    
    # Ваша логика поиска
    results = await search_api.search(query)
    
    return {
        "success": True,
        "query": query,
        "results": results
    }
```

**Важные правила:**

1. ✅ Функция должна быть `async`
2. ✅ Принимает `dict` с параметрами
3. ✅ Возвращает `dict` с результатом
4. ✅ Обрабатывает ошибки внутри
5. ✅ Всегда возвращает `success: bool`

### Регистрация тулзов

```python
# Регистрация одного тулза
agent.register_tool("tool_name", tool_handler)

# Регистрация множества тулзов
tools = {
    "web_search": web_search_tool,
    "file_create": file_create_tool,
    "folder_create": folder_create_tool,
    "analyze_content": analyze_content_tool
}

for name, handler in tools.items():
    agent.register_tool(name, handler)
```

### Кастомная инструкция

```python
custom_instruction = """
Ты специализированный агент для анализа научных статей.

Твоя задача:
1. ОБЯЗАТЕЛЬНО создай план (plan_todo)
2. Проанализируй статью
3. Извлеки ключевую информацию
4. Сохрани в структурированном виде

Доступные тулзы:
- plan_todo: Создать план
- analyze_content: Анализ текста
- web_search: Поиск информации
- file_create: Создание файла

Работай автономно и систематично.
"""

agent = OpenAIAgent(
    api_key="...",
    base_url="...",
    instruction=custom_instruction
)
```

## Примеры использования

### Пример 1: Базовая обработка статьи

```python
async def process_article():
    agent = OpenAIAgent(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model="qwen-max"
    )
    
    # Регистрируем тулзы
    agent.register_tool("web_search", web_search_tool)
    agent.register_tool("file_create", file_create_tool)
    agent.register_tool("analyze_content", analyze_content_tool)
    
    # Задача
    content = {
        "text": "Статья о нейронных сетях...",
        "urls": ["https://example.com/article"]
    }
    
    # Агент САМ решит:
    # 1. Создать план
    # 2. Проанализировать текст
    # 3. Может быть сделать web_search по URL
    # 4. Создать файл с результатом
    result = await agent.process(content)
    
    return result
```

### Пример 2: Обработка с файловыми операциями

```python
from pathlib import Path

async def file_create_tool(params: dict) -> dict:
    """Тулз для создания файлов в KB"""
    path = params["path"]
    content = params["content"]
    
    # Валидация пути
    kb_root = Path("/path/to/kb")
    full_path = (kb_root / path).resolve()
    
    # Проверка безопасности
    if not str(full_path).startswith(str(kb_root)):
        return {
            "success": False,
            "error": "Path traversal detected"
        }
    
    # Создание файла
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    
    return {
        "success": True,
        "path": path,
        "message": f"File created: {path}"
    }

# Использование
agent = OpenAIAgent(...)
agent.register_tool("file_create", file_create_tool)

result = await agent.process({
    "text": "Информация для сохранения..."
})

# Агент может сам решить создать несколько файлов:
# - ai/concepts/neural-networks.md
# - ai/concepts/transformers.md
# - ai/README.md
```

### Пример 3: Интеграция с существующей системой

```python
from src.knowledge_base.manager import KnowledgeBaseManager

async def integrate_with_kb():
    """Интеграция агента с Knowledge Base"""
    
    kb_manager = KnowledgeBaseManager(...)
    
    # Создать тулз для сохранения в KB
    async def save_to_kb_tool(params: dict) -> dict:
        content = params["content"]
        category = params.get("category", "general")
        
        # Использовать существующий KB manager
        article_id = await kb_manager.save_article(
            content=content,
            metadata={"category": category}
        )
        
        return {
            "success": True,
            "article_id": article_id
        }
    
    # Создать агента
    agent = OpenAIAgent(...)
    agent.register_tool("save_to_kb", save_to_kb_tool)
    
    # Агент теперь может сохранять в KB
    result = await agent.process({
        "text": "Статья..."
    })
```

## Конфигурация

### Через config.yaml

```yaml
# Тип агента
AGENT_TYPE: "openai"  # Использовать OpenAI Agent

# OpenAI API настройки
AGENT_MODEL: "qwen-max"
AGENT_MAX_ITERATIONS: 10

# Инструкция (опционально)
AGENT_INSTRUCTION: |
  Ты автономный агент...
  Твоя задача...
```

### Через .env

```bash
# API ключи
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Или для других провайдеров
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

### Программная конфигурация

```python
from src.agents.agent_factory import AgentFactory

# Через фабрику
agent = AgentFactory.create_agent(
    agent_type="openai",
    config={
        "api_key": "your-key",
        "base_url": "https://...",
        "model": "qwen-max",
        "max_iterations": 10,
        "instruction": "Custom instruction..."
    }
)

# Или напрямую
from src.agents.openai_agent import OpenAIAgent

agent = OpenAIAgent(
    api_key="your-key",
    base_url="https://...",
    model="qwen-max",
    max_iterations=10
)
```

## Логирование и отладка

### Включение DEBUG логов

```python
import logging

# Для всех агентов
logging.getLogger("src.agents").setLevel(logging.DEBUG)

# Только для OpenAI агента
logging.getLogger("src.agents.openai_agent").setLevel(logging.DEBUG)
```

### Анализ выполнения

```python
result = await agent.process(content)

# Метаданные выполнения
metadata = result['metadata']

print(f"Итераций: {metadata['iterations']}")
print(f"Тулзы: {metadata['tools_used']}")

# Детали каждого вызова тулза
for execution in metadata['executions']:
    print(f"Tool: {execution['tool_name']}")
    print(f"Success: {execution['success']}")
    print(f"Result: {execution['result']}")
    if not execution['success']:
        print(f"Error: {execution['error']}")
```

### Контекст выполнения

```python
# Доступ к контексту
context = result['metadata']['context']

print(f"Задача: {context['task']}")
print(f"Выполнено тулзов: {len(context['executions'])}")
print(f"Ошибки: {context['errors']}")
```

## Ограничения и лучшие практики

### Ограничения

1. **Max iterations**: По умолчанию 10 итераций
   - Защита от бесконечных циклов
   - Настраивается через `max_iterations`

2. **API rate limits**: Зависит от провайдера
   - Qwen: 60 req/min, 2000 req/day
   - OpenAI: зависит от тарифа

3. **Context window**: Ограничен размером контекста модели
   - При длинной истории выполнения может закончиться контекст

### Лучшие практики

#### 1. Валидация тулзов

```python
async def safe_file_tool(params: dict) -> dict:
    # ✅ Валидация параметров
    if "path" not in params:
        return {"success": False, "error": "Missing path"}
    
    # ✅ Валидация путей
    if ".." in params["path"]:
        return {"success": False, "error": "Path traversal"}
    
    # ✅ Обработка ошибок
    try:
        # Ваша логика
        result = create_file(params["path"], params["content"])
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

#### 2. Инструкции

```python
# ✅ Хорошая инструкция
instruction = """
1. ОБЯЗАТЕЛЬНО создай план (plan_todo)
2. Используй тулзы в правильном порядке
3. Всегда возвращай результат в markdown

Доступные тулзы:
- plan_todo: Создать план
- analyze: Анализ
- save: Сохранение
"""

# ❌ Плохая инструкция
instruction = "Обработай контент"
```

#### 3. Обработка ошибок

```python
# Агент автоматически обрабатывает ошибки тулзов
# и продолжает работу

result = await agent.process(content)

# Проверка на ошибки
if result['metadata']['errors']:
    print("Были ошибки:", result['metadata']['errors'])
    
# Агент всё равно вернёт результат (fallback)
```

## FAQ

### Q: Как агент принимает решения?

A: Через OpenAI function calling. LLM видит доступные тулзы и их описания, анализирует текущую ситуацию и решает какой тулз вызвать.

### Q: Можно ли использовать с другими LLM?

A: Да, любые OpenAI-compatible API:
- Qwen (dashscope)
- OpenRouter
- Together AI
- Локальные модели через vLLM/ollama с OpenAI endpoint

### Q: Как ограничить количество итераций?

A: Через параметр `max_iterations`:

```python
agent = OpenAIAgent(max_iterations=5)  # Макс 5 итераций
```

### Q: Что если агент не вызывает тулзы?

A: Проверьте:
1. Инструкция указывает использовать тулзы?
2. Тулзы зарегистрированы?
3. Описания тулзов понятны LLM?

### Q: Как добавить свой тулз?

A: Создайте async функцию и зарегистрируйте:

```python
async def my_tool(params: dict) -> dict:
    # Ваша логика
    return {"success": True, "result": "..."}

agent.register_tool("my_tool", my_tool)
```

## Roadmap

- [ ] Поддержка streaming результатов
- [ ] Поддержка vision моделей для изображений
- [ ] Автоматический retry при ошибках API
- [ ] Кэширование промптов
- [ ] Parallel tool execution
- [ ] Tool композиция (один тулз вызывает другие)
- [ ] Metrics и мониторинг
- [ ] Web UI для отладки

## См. также

- [AGENT_ARCHITECTURE.md](./AGENT_ARCHITECTURE.md) - Подробная архитектура
- [examples/autonomous_agent_example.py](../examples/autonomous_agent_example.py) - Примеры кода
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling) - Документация OpenAI
