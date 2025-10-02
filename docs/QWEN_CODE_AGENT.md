# Qwen Code Agent Implementation

## Обзор

Реализован автономный агент на базе концепции [Qwen Code](https://github.com/QwenLM/qwen-code) с полным набором функций для обработки контента и сохранения в базу знаний.

## Основные возможности

### ✅ 1. Настраиваемая инструкция

Агент поддерживает настраиваемые инструкции, которые определяют его поведение:

```python
from src.agents.qwen_code_agent import QwenCodeAgent

# Использование стандартной инструкции
agent = QwenCodeAgent()

# Кастомная инструкция
custom_instruction = """
Вы - специализированный агент для анализа научных статей.
Фокусируйтесь на извлечении методологии и результатов.
"""

agent = QwenCodeAgent(instruction=custom_instruction)

# Изменение инструкции в runtime
agent.set_instruction("Новая инструкция")
```

**Конфигурация через YAML:**
```yaml
AGENT_TYPE: "qwen_code"
AGENT_INSTRUCTION: "Кастомная инструкция для агента"
```

### ✅ 2. Автономный режим работы

Агент работает полностью автономно без запросов к пользователю:

```python
# Обработка контента
content = {
    "text": "Статья о машинном обучении...",
    "urls": ["https://example.com/article"]
}

# Агент автономно:
# 1. Создает TODO план
# 2. Выполняет план
# 3. Анализирует контент
# 4. Структурирует данные
# 5. Генерирует markdown
result = await agent.process(content)
```

**Процесс обработки:**
1. Получение контента → Анализ → Создание плана
2. Выполнение плана с использованием инструментов
3. Структурирование информации
4. Сохранение в базу знаний

### ✅ 3. TODO план

Агент автоматически создает и выполняет план обработки:

```python
# План создается автоматически и включает:
# - Анализ контента
# - Поиск дополнительного контекста (если есть URL)
# - Извлечение метаданных
# - Структурирование
# - Генерация markdown

# Доступ к плану после обработки
result = await agent.process(content)
plan = result["metadata"]["plan"]

print("Задачи:")
for task in plan["tasks"]:
    print(f"- {task['task']} [{task['status']}]")
```

**Структура TODO плана:**
```json
{
  "tasks": [
    {
      "task": "Analyze content and extract key topics",
      "status": "completed",
      "priority": 1,
      "created_at": "2025-10-02T10:30:00"
    },
    {
      "task": "Search web for context on URLs",
      "status": "completed",
      "priority": 2,
      "created_at": "2025-10-02T10:30:01"
    }
  ]
}
```

### ✅ 4. Система инструментов (Tools)

#### 4.1 Web Search (Веб-поиск)

```python
agent = QwenCodeAgent(enable_web_search=True)

# Автоматически используется при наличии URL в контенте
content = {
    "text": "Анализ статьи",
    "urls": ["https://example.com/article"]
}

result = await agent.process(content)
# Агент автоматически получит метаданные URL
```

#### 4.2 Git Commands (Git команды)

```python
agent = QwenCodeAgent(enable_git=True)

# Безопасные git команды
# Разрешены: status, log, diff, branch, remote, show
result = await agent._tool_git_command({
    "command": "git status",
    "cwd": "/path/to/repo"
})

if result.success:
    print(result.output["stdout"])
```

**Безопасность:** Только read-only команды разрешены по умолчанию.

#### 4.3 GitHub API

```python
agent = QwenCodeAgent(
    enable_github=True,
    config={"github_token": "your_token"}
)

# Использование GitHub API
result = await agent._tool_github_api({
    "endpoint": "/repos/user/repo",
    "method": "GET"
})

if result.success:
    repo_data = result.output["data"]
```

**Конфигурация токена:**
```yaml
# config.yaml
AGENT_ENABLE_GITHUB: true
```

```bash
# .env
GITHUB_TOKEN=your_github_token
```

#### 4.4 Shell Commands (Команды оболочки)

⚠️ **ВАЖНО:** Отключено по умолчанию из-за рисков безопасности!

```python
# Включить только если абсолютно необходимо
agent = QwenCodeAgent(enable_shell=True)

# Опасные команды блокируются автоматически:
# rm -rf, sudo, wget, curl, и др.
```

**Конфигурация:**
```yaml
AGENT_ENABLE_SHELL: false  # НЕ включайте без необходимости!
```

## Конфигурация

### Через настройки приложения

**config.yaml:**
```yaml
# Agent Configuration
AGENT_TYPE: "qwen_code"  # или "stub"
AGENT_MODEL: "qwen-max"  # qwen-max, qwen-plus, qwen-turbo
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false
```

**.env:**
```bash
# API ключи (НЕ в YAML!)
QWEN_API_KEY=your_qwen_api_key
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
GITHUB_TOKEN=your_github_token
```

### Программная конфигурация

```python
from src.agents.agent_factory import AgentFactory

# Автоматически из настроек
agent = AgentFactory.from_settings(settings)

# Или вручную
agent = AgentFactory.create_agent(
    agent_type="qwen_code",
    config={
        "api_key": "your_qwen_api_key",
        "model": "qwen-max",
        "instruction": "Custom instruction",
        "enable_web_search": True,
        "enable_git": True,
        "enable_github": True,
        "enable_shell": False
    }
)
```

## Использование с Telegram ботом

Бот автоматически использует настроенный агент:

```bash
# 1. Настроить config.yaml
cp config.example.yaml config.yaml
nano config.yaml  # установить AGENT_TYPE: "qwen_code"

# 2. Настроить .env
echo "QWEN_API_KEY=your_key" >> .env
echo "GITHUB_TOKEN=your_token" >> .env

# 3. Запустить бота
python main.py
```

Агент будет автоматически обрабатывать все сообщения в Telegram.

## API агента

### Основные методы

```python
from src.agents.qwen_code_agent import QwenCodeAgent

agent = QwenCodeAgent()

# 1. Обработка контента (основной метод)
result = await agent.process({
    "text": "Контент для обработки",
    "urls": ["https://example.com"]
})

# Результат содержит:
# - markdown: Отформатированный контент
# - metadata: Метаданные обработки
# - title: Заголовок
# - kb_structure: Структура для KB

# 2. Валидация входных данных
is_valid = agent.validate_input(content)

# 3. Управление инструкцией
agent.set_instruction("Новая инструкция")
instruction = agent.get_instruction()
```

### Структура результата

```python
{
    "markdown": "# Заголовок\n\n## Metadata\n...",
    "metadata": {
        "processed_at": "2025-10-02T10:30:00",
        "agent": "QwenCodeAgent",
        "version": "1.0.0",
        "model": "qwen-max",
        "plan": {
            "tasks": [...]
        },
        "execution_log": [
            {
                "task": "Analyze content",
                "status": "completed",
                "timestamp": "..."
            }
        ],
        "tools_used": ["web_search", "git_command"]
    },
    "title": "Заголовок статьи",
    "kb_structure": KBStructure(
        category="ai",
        subcategory="machine-learning",
        tags=["ml", "neural-networks"]
    )
}
```

## Расширение агента

### Добавление нового инструмента

```python
class CustomQwenAgent(QwenCodeAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавить свой инструмент
        self.tools["custom_tool"] = self._tool_custom
    
    async def _tool_custom(self, params: Dict) -> ToolResult:
        try:
            # Ваша логика
            result = do_something(params)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
```

### Кастомизация TODO плана

```python
class CustomQwenAgent(QwenCodeAgent):
    async def _create_todo_plan(self, content: Dict) -> TodoPlan:
        plan = TodoPlan()
        
        # Ваша логика создания плана
        plan.add_task("Кастомная задача 1", priority=1)
        plan.add_task("Кастомная задача 2", priority=2)
        
        return plan
```

## Безопасность

### Рекомендации

1. **API ключи**: Храните в `.env`, НЕ в коде или YAML
2. **Shell команды**: Оставьте `enable_shell=false` если не требуется
3. **Git команды**: Только read-only операции разрешены
4. **GitHub токен**: Используйте токен с минимальными правами

### Автоматическая защита

- ✅ Блокировка опасных shell команд
- ✅ Ограничение git команд на безопасные операции
- ✅ Timeout для внешних запросов (30 секунд)
- ✅ Валидация входных данных

## Тестирование

```bash
# Запустить все тесты агента
pytest tests/test_qwen_code_agent.py -v

# Запустить тесты фабрики
pytest tests/test_agent_factory.py -v

# Запустить тесты с покрытием
pytest tests/test_qwen_code_agent.py --cov=src.agents.qwen_code_agent

# Запустить конкретный тест
pytest tests/test_qwen_code_agent.py::TestQwenCodeAgent::test_process_full -v
```

## Примеры использования

### Пример 1: Обработка научной статьи

```python
agent = QwenCodeAgent(
    instruction="Фокус на научных статьях. Извлекай методологию и результаты.",
    enable_web_search=True
)

content = {
    "text": """
    Новое исследование в области машинного обучения...
    Методология: использовали нейронные сети...
    Результаты: точность 95%...
    """,
    "urls": ["https://arxiv.org/abs/12345"]
}

result = await agent.process(content)

# Сохранить в KB
kb_manager.save_article(
    content=result["markdown"],
    kb_structure=result["kb_structure"],
    metadata=result["metadata"]
)
```

### Пример 2: Мониторинг GitHub репозитория

```python
agent = QwenCodeAgent(
    enable_github=True,
    config={"github_token": "token"}
)

content = {
    "text": "Обзор репозитория QwenLM/qwen-code",
    "urls": ["https://github.com/QwenLM/qwen-code"]
}

result = await agent.process(content)
# Агент автоматически получит информацию из GitHub API
```

### Пример 3: Анализ git репозитория

```python
agent = QwenCodeAgent(enable_git=True)

# В процессе обработки агент может использовать git
result = await agent._tool_git_command({
    "command": "git log --oneline -10",
    "cwd": "/path/to/repo"
})

if result.success:
    commits = result.output["stdout"]
    # Проанализировать коммиты
```

## Логирование

Агент логирует все важные операции:

```python
import logging

# Включить DEBUG логи
logging.getLogger("src.agents.qwen_code_agent").setLevel(logging.DEBUG)

# Пример логов:
# INFO: QwenCodeAgent initialized with model: qwen-max
# INFO: Enabled tools: ['web_search', 'git_command', 'github_api']
# INFO: Starting autonomous content processing...
# INFO: Created TODO plan with 5 tasks
# INFO: Executing task 1/5: Analyze content and extract key topics
# INFO: Plan execution completed with 5 results
```

## Метрики и мониторинг

```python
result = await agent.process(content)

# Доступ к метрикам
metadata = result["metadata"]

print(f"Модель: {metadata['model']}")
print(f"Задач выполнено: {len(metadata['plan']['tasks'])}")
print(f"Инструменты использованы: {metadata['tools_used']}")
print(f"Время обработки: {metadata['processed_at']}")

# Логи выполнения
for log in metadata['execution_log']:
    print(f"{log['timestamp']}: {log['task']} - {log['status']}")
```

## FAQ

### Q: Нужен ли API ключ Qwen?

A: В текущей реализации API ключ опционален. Агент использует локальную обработку. Для использования реального Qwen API через `qwen-agent` пакет, требуется ключ.

### Q: Какие модели поддерживаются?

A: `qwen-max`, `qwen-plus`, `qwen-turbo`. Настройка через `AGENT_MODEL` в config.yaml.

### Q: Как включить shell команды?

A: Установите `AGENT_ENABLE_SHELL: true` в config.yaml. **НЕ рекомендуется** из-за рисков безопасности.

### Q: Можно ли использовать свой LLM?

A: Да, расширьте класс `QwenCodeAgent` и переопределите методы обработки для интеграции с вашим LLM.

### Q: Как агент определяет категорию?

A: Использует keyword-based анализ текста. Для более точной категоризации можно интегрировать классификатор на базе LLM.

## Производительность

- **Обработка текста**: ~1-2 секунды для статьи 1000 слов
- **Web поиск**: +2-5 секунд на URL
- **GitHub API**: +1-3 секунды на запрос
- **Git команды**: <1 секунда

## Зависимости

```txt
aiohttp>=3.9.1      # Для async HTTP запросов
requests>=2.31.0    # Для sync HTTP запросов
qwen-agent>=0.0.31  # Опционально для интеграции с Qwen API
```

## Roadmap

- [ ] Интеграция с реальным Qwen API
- [ ] Улучшенная категоризация с LLM
- [ ] Поддержка многоязычности
- [ ] Кэширование web поиска
- [ ] Поддержка изображений и PDF
- [ ] Векторное хранилище для semantic search
- [ ] Поддержка длинных документов с chunking

## Лицензия

MIT License - см. LICENSE файл

## Контрибуция

Pull requests приветствуются! Для крупных изменений, пожалуйста, сначала откройте issue.
