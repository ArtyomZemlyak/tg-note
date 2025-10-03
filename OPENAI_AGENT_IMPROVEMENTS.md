# OpenAI Agent Improvements

## Обзор изменений

OpenAI Agent был доработан для правильного использования автономного агента, базового агента и формата ответа, а также для выполнения всех изменений базы знаний в рамках своей работы.

## Ключевые улучшения

### 1. Встроенные тулзы для работы с базой знаний

OpenAI Agent теперь автоматически регистрирует встроенные тулзы при инициализации:

- **file_create** - создание файла в базе знаний
- **file_edit** - редактирование существующего файла
- **folder_create** - создание папки для организации файлов
- **plan_todo** - создание плана действий

Эти тулзы работают непосредственно с файловой системой и автоматически управляют изменениями в базе знаний.

#### Пример использования:

```python
from pathlib import Path
from src.agents.openai_agent import OpenAIAgent

# Создать агента с указанием пути к базе знаний
agent = OpenAIAgent(
    api_key="your-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    model="qwen-max",
    max_iterations=10,
    kb_root_path=Path("./knowledge_base")  # Агент будет создавать файлы здесь
)

# Тулзы file_create, file_edit, folder_create уже зарегистрированы!
# Агент может сразу начинать работу с базой знаний
```

### 2. Автоматическое управление файлами

Агент теперь полностью управляет всеми изменениями базы знаний через свои тулзы:

**Ранее:**
- Агент возвращал только markdown контент
- Файлы создавались вручную после получения ответа
- Не было контроля над структурой файлов

**Сейчас:**
- Агент сам создает файлы через `file_create`
- Агент организует структуру папок через `folder_create`
- Агент может редактировать существующие файлы через `file_edit`
- Все операции логируются и отслеживаются в контексте

### 3. Улучшенный формат ответа

Агент теперь правильно возвращает результаты в формате `AgentResult` с полной информацией о KB структуре.

#### Структура ответа:

```python
{
    "markdown": "Финальный markdown контент",
    "title": "Заголовок статьи",
    "kb_structure": KBStructure(
        category="ai",
        subcategory="machine-learning",
        tags=["neural-networks", "deep-learning"]
    ),
    "metadata": {
        "agent": "AutonomousAgent",
        "iterations": 5,
        "tools_used": ["plan_todo", "file_create"],
        # ... дополнительные метаданные
    }
}
```

### 4. Автоматическое определение KB структуры

Агент теперь интеллектуально определяет структуру базы знаний:

1. **Из метаданных агента** - если агент явно указал category/tags в формате agent-result
2. **Из созданных файлов** - извлекает категорию из путей созданных файлов
3. **Автоопределение** - анализирует контент для определения категории

#### Пример автоопределения:

```python
# Агент создал файл: topics/ai/neural-networks/article.md
# Автоматически определяется:
kb_structure = KBStructure(
    category="ai",
    subcategory="neural-networks",
    tags=[]
)
```

### 5. Обновленная инструкция агента

Инструкция агента переработана с акцентом на работу с базой знаний:

**Ключевые моменты:**
- Агент ОБЯЗАН использовать тулзы для создания файлов
- Агент НЕ должен возвращать просто markdown - он должен сохранить его через file_create
- Агент должен вернуть финальный результат с информацией о созданных файлах
- Все изменения базы знаний делаются ТОЛЬКО через тулзы

### 6. Интеграция с bot handlers

Bot handlers обновлены для передачи пути к базе знаний при создании агента:

```python
def _get_or_create_user_agent(self, user_id: int):
    # Get user KB path
    user_kb = self.user_settings.get_user_kb(user_id)
    kb_path = None
    if user_kb:
        kb_path = self.repo_manager.get_kb_path(user_kb['kb_name'])
    
    config = {
        # ... другие настройки
        "kb_path": str(kb_path) if kb_path else None,
    }
    
    agent = AgentFactory.create_agent(agent_type=agent_type, config=config)
```

## Технические детали

### Изменения в файлах

#### `src/agents/openai_agent.py`

1. Добавлен параметр `kb_root_path` в конструктор
2. Добавлен метод `_register_kb_tools()` для автоматической регистрации тулзов
3. Реализованы методы-обработчики:
   - `_handle_file_create()`
   - `_handle_file_edit()`
   - `_handle_folder_create()`
4. Переопределен метод `_determine_kb_structure()` для интеллектуального определения структуры

#### `src/agents/agent_factory.py`

1. Обновлен метод `_create_openai_agent()` для передачи `kb_root_path`
2. Добавлена поддержка параметра `kb_path` из конфигурации

#### `src/bot/handlers.py`

1. Обновлен метод `_get_or_create_user_agent()` для получения и передачи пути к KB пользователя

### Формат финального ответа агента

Агент должен возвращать ответ в следующем формате:

```markdown
# Результат обработки

Здесь описание выполненной работы...

```agent-result
{
  "summary": "Краткое описание выполненных действий",
  "files_created": ["topics/ai/article.md"],
  "files_edited": [],
  "folders_created": ["topics/ai"],
  "metadata": {
    "category": "ai",
    "subcategory": "machine-learning",
    "tags": ["neural-networks", "transformers"]
  }
}
```
```

## Примеры использования

### Базовый пример

```python
from pathlib import Path
from src.agents.openai_agent import OpenAIAgent

# Инициализация агента
agent = OpenAIAgent(
    api_key="your-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    model="qwen-max",
    kb_root_path=Path("./my_knowledge_base")
)

# Обработка контента
content = {
    "text": "Подробная статья о нейронных сетях..."
}

result = await agent.process(content)

# Результат содержит:
# - result['markdown'] - финальный markdown
# - result['title'] - заголовок
# - result['kb_structure'] - структура KB
# - result['metadata'] - метаданные с информацией о созданных файлах
```

### Пример с кастомной инструкцией

```python
custom_instruction = """
Ты специализированный агент для обработки научных статей.

Твоя задача:
1. Создай план через plan_todo
2. Проанализируй статью
3. Определи категорию (science/physics, science/biology и т.д.)
4. Создай папку если нужно через folder_create
5. Сохрани статью через file_create в соответствующую категорию
"""

agent = OpenAIAgent(
    api_key="your-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    model="qwen-max",
    instruction=custom_instruction,
    kb_root_path=Path("./my_knowledge_base")
)
```

## Преимущества

1. **Автономность** - агент полностью управляет базой знаний самостоятельно
2. **Прозрачность** - все операции логируются и отслеживаются
3. **Гибкость** - можно легко добавлять новые тулзы
4. **Надежность** - встроенная обработка ошибок и валидация
5. **Интеграция** - правильная работа с базовым агентом и форматами ответа

## Миграция

Если вы использовали старую версию OpenAI Agent:

### Было:
```python
agent = OpenAIAgent(api_key="key", base_url="url", model="model")
agent.register_tool("file_create", my_file_create_handler)
agent.register_tool("folder_create", my_folder_create_handler)
```

### Стало:
```python
agent = OpenAIAgent(
    api_key="key",
    base_url="url",
    model="model",
    kb_root_path=Path("./kb")  # Добавьте путь к KB
)
# file_create, folder_create уже встроены!
# Регистрируйте только дополнительные тулзы
```

## Тестирование

Для тестирования обновленного агента:

```bash
# Запустить пример
python examples/autonomous_agent_example.py

# Или использовать в боте
# Агент автоматически получит правильный kb_path от bot handlers
```

## Дальнейшее развитие

Возможные улучшения:

1. Добавить тулз `file_delete` для удаления файлов
2. Добавить тулз `file_list` для просмотра содержимого KB
3. Реализовать версионирование файлов
4. Добавить поддержку шаблонов для разных типов контента
5. Интегрировать с vector database для семантического поиска

## Заключение

OpenAI Agent теперь полноценный автономный агент для работы с базой знаний, который:
- Правильно наследуется от AutonomousAgent
- Использует стандартный формат ответа BaseAgent
- Полностью управляет изменениями базы знаний
- Автоматически определяет структуру KB
- Интегрирован с остальной системой

Все изменения совместимы с существующей архитектурой и следуют принципам SOLID.
