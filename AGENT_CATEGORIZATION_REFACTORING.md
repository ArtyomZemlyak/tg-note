# Agent Categorization and Refactoring

## Обзор

Агенты были переформатированы на основе двух категорий в соответствии с их архитектурой и способом работы.

## Категории агентов

### Категория 1: Неполноценные автономные агенты (логика на нашей стороне)

**Агенты:**
- `QwenCodeAgent` (qwen_code_agent.py)
- `OpenAIAgent` (openai_agent.py)

**Характеристики:**
- Наследуются от `AutonomousAgent`
- Мы предоставляем им инструменты (tools)
- Мы показываем как работать с базой знаний
- Мы собираем итоговый отчет об изменениях

**Реализованные изменения:**
✅ **Изменения применяются ПО ХОДУ РАБОТЫ агента:**
- Все file/folder tools теперь РЕАЛЬНО создают/изменяют файлы во время выполнения
- `_tool_file_create()` - создает файл немедленно
- `_tool_file_edit()` - редактирует файл немедленно
- `_tool_file_delete()` - удаляет файл немедленно
- `_tool_file_move()` - перемещает файл немедленно
- `_tool_folder_create()` - создает папку немедленно
- `_tool_folder_delete()` - удаляет папку немедленно
- `_tool_folder_move()` - перемещает папку немедленно

✅ **Отчет об изменениях собирается автоматически:**
- В `_generate_final_markdown()` анализируются все выполненные операции
- В итоговый markdown добавляется секция "## Changes Applied"
- Перечисляются все созданные файлы, папки, измененные файлы
- Пример:
  ```markdown
  ## Changes Applied

  **Files Created:**
  - ✓ ai/models/gpt4.md
  - ✓ ai/vision/multimodal.md

  **Folders Created:**
  - ✓ ai/models
  - ✓ ai/vision
  ```

✅ **Множественное создание файлов/папок:**
- Агент может вызывать tools несколько раз в цикле
- Каждая операция выполняется сразу
- Логируется с префиксами `[file_create]`, `[folder_create]` и т.д.

**Доступные инструменты:**
```python
# File management
- file_create(path, content) → создает файл НЕМЕДЛЕННО
- file_edit(path, content) → редактирует файл НЕМЕДЛЕННО
- file_delete(path) → удаляет файл НЕМЕДЛЕННО
- file_move(source, destination) → перемещает файл НЕМЕДЛЕННО

# Folder management
- folder_create(path) → создает папку НЕМЕДЛЕННО
- folder_delete(path) → удаляет папку НЕМЕДЛЕННО
- folder_move(source, destination) → перемещает папку НЕМЕДЛЕННО

# Other tools
- web_search(query)
- git_command(command, cwd)
- github_api(endpoint, method, data)
- shell_command(command, cwd) # disabled by default
- analyze_content(text)
- plan_todo(tasks)
```

### Категория 2: Полноценный автономный агент (вся логика внутри)

**Агент:**
- `QwenCodeCLIAgent` (qwen_code_cli_agent.py)

**Характеристики:**
- Использует внешний CLI инструмент (qwen-code)
- CLI сам реализует всю логику агентности
- CLI сам может изменять файлы В ПРОЦЕССЕ СВОЕЙ РАБОТЫ
- Мы даем задачу, он все сам выполняет

**Реализованные изменения:**
✅ **CLI создает файлы сам во время работы:**
- qwen-code CLI полностью автономен
- Имеет встроенные возможности создания/редактирования файлов
- Prompt инструктирует его создавать несколько файлов и папок
- Мы не контролируем файловые операции - CLI делает это сам

✅ **Парсинг результатов для отчета:**
- Метод `_parse_qwen_result()` извлекает информацию о созданных файлах
- Ищет паттерны: "Created file:", "✓ Created:", "создан файл" и т.д.
- Извлекает пути к файлам из вывода CLI
- Генерирует summary: "Created N file(s), Created M folder(s)"

✅ **Метаданные о выполненных изменениях:**
```python
metadata = {
    "files_created": ["ai/models/gpt4.md", "ai/vision/multimodal.md"],
    "folders_created": ["ai/models", "ai/vision"],
    "files_edited": ["ai/models/gpt4.md"],
    "summary_of_changes": "Created 2 file(s), Created 2 folder(s), Edited 1 file(s)"
}
```

✅ **Множественное создание файлов/папок:**
- CLI инструктируется создавать несколько файлов из одного источника
- Prompt явно указывает: "разбивай информацию по темам"
- Пример из промпта:
  ```
  Источник: "Статья о GPT-4 с vision"
  → ai/models/gpt4.md
  → ai/vision/multimodal-models.md
  → applications/medical/ai-diagnostics.md
  ```

**Инструкция для CLI (из config/agent_prompts.py):**
- Шаг 4: Структурирование по темам - "ОДИН источник может содержать РАЗНЫЕ темы"
- Шаг 5: Создание структуры - создавать папки и файлы
- Шаг 6: Наполнение КАЖДОГО файла
- Шаг 8: Создание связей между файлами

### Особый случай: StubAgent

**Агент:**
- `StubAgent` (stub_agent.py)

**Характеристики:**
- Самый простой агент без ИИ
- Просто форматирует текст в markdown
- Не создает файлы напрямую (это делает система БЗ)

**Статус:**
- ✅ Остается простым, как и задумано
- ✅ Возвращает markdown и KB structure для сохранения системой
- Создание одного файла (системой БЗ, а не самим агентом)

## Архитектура изменений

### Категория 1: QwenCodeAgent & OpenAIAgent

```
User Input
    ↓
Agent Loop (AutonomousAgent)
    ↓
_make_decision() → выбирает следующее действие
    ↓
_execute_tool() → вызывает tool
    ↓
_tool_file_create() → ✅ СОЗДАЕТ ФАЙЛ СРАЗУ!
_tool_folder_create() → ✅ СОЗДАЕТ ПАПКУ СРАЗУ!
    ↓
ToolExecution сохраняется в context
    ↓
(loop continues...)
    ↓
_generate_final_markdown() → собирает отчет
    ↓
Returns: markdown + metadata + kb_structure
```

**Ключевое изменение:** Инструменты теперь возвращают `Dict[str, Any]` вместо `ToolResult`, и РЕАЛЬНО создают файлы во время выполнения.

### Категория 2: QwenCodeCLIAgent

```
User Input
    ↓
_prepare_prompt() → формирует задачу для CLI
    ↓
_execute_qwen_cli() → запускает qwen-code CLI
    ↓
[CLI работает автономно]
    ├─ web_search
    ├─ folder_create (CLI САМ создает!) ✅
    ├─ file_create (CLI САМ создает!) ✅
    ├─ file_edit (CLI САМ редактирует!) ✅
    └─ возвращает результат
    ↓
_parse_qwen_result() → парсит что CLI сделал
    ↓
Returns: markdown + metadata (с отчетом об изменениях)
```

**Ключевое изменение:** CLI сам создает файлы, мы только парсим результат и включаем информацию о созданных файлах в metadata.

## Функциональность

### Все агенты теперь могут:

| Агент | Создать несколько файлов | Создать несколько папок | Изменения по ходу работы | Отчет об изменениях |
|-------|-------------------------|------------------------|-------------------------|-------------------|
| **QwenCodeAgent** | ✅ Да | ✅ Да | ✅ Да | ✅ Да (в markdown) |
| **OpenAIAgent** | ✅ Да | ✅ Да | ✅ Да | ✅ Да (в markdown) |
| **QwenCodeCLIAgent** | ✅ Да (CLI) | ✅ Да (CLI) | ✅ Да (CLI сам) | ✅ Да (в metadata) |
| **StubAgent** | ➖ Один файл | ➖ Нет | ➖ Нет | ➖ Нет (простейший) |

## Примеры использования

### Категория 1: QwenCodeAgent

```python
agent = QwenCodeAgent(
    enable_file_management=True,
    enable_folder_management=True,
    kb_root_path=Path("./knowledge_base")
)

result = await agent.process({
    "text": "Article about GPT-4 Vision..."
})

# Во время process():
# 1. Agent планирует: folder_create("ai/models")
# 2. Agent выполняет: ✅ ПАПКА СОЗДАЕТСЯ СРАЗУ
# 3. Agent планирует: file_create("ai/models/gpt4.md", content)
# 4. Agent выполняет: ✅ ФАЙЛ СОЗДАЕТСЯ СРАЗУ
# 5. Agent планирует: folder_create("ai/vision")
# 6. Agent выполняет: ✅ ПАПКА СОЗДАЕТСЯ СРАЗУ
# 7. Agent планирует: file_create("ai/vision/multimodal.md", content)
# 8. Agent выполняет: ✅ ФАЙЛ СОЗДАЕТСЯ СРАЗУ
# ...

# result["markdown"] содержит:
# ## Changes Applied
# **Files Created:**
# - ✓ ai/models/gpt4.md
# - ✓ ai/vision/multimodal.md
# **Folders Created:**
# - ✓ ai/models
# - ✓ ai/vision
```

### Категория 2: QwenCodeCLIAgent

```python
agent = QwenCodeCLIAgent(
    instruction=QWEN_CODE_CLI_AGENT_INSTRUCTION,
    working_directory="./knowledge_base"
)

result = await agent.process({
    "text": "Article about GPT-4 Vision..."
})

# Во время process():
# CLI работает автономно:
# 1. ✅ CLI САМ создает ai/models/
# 2. ✅ CLI САМ создает ai/models/gpt4.md
# 3. ✅ CLI САМ создает ai/vision/
# 4. ✅ CLI САМ создает ai/vision/multimodal.md
# ...

# result["metadata"] содержит:
{
    "files_created": ["ai/models/gpt4.md", "ai/vision/multimodal.md"],
    "folders_created": ["ai/models", "ai/vision"],
    "summary_of_changes": "Created 2 file(s), Created 2 folder(s)"
}
```

## Логирование

### Категория 1 - подробные логи каждой операции:
```
[QwenCodeAgent] Iteration 1/10
[QwenCodeAgent] Decision: action=TOOL_CALL, tool=folder_create
[folder_create] ✓ Created folder: ai/models
[QwenCodeAgent] Iteration 2/10
[QwenCodeAgent] Decision: action=TOOL_CALL, tool=file_create
[file_create] ✓ Created file: ai/models/gpt4.md (1234 bytes)
...
[QwenCodeAgent] All tasks completed, generating final result
[QwenCodeAgent] Completed in 5 iterations
```

### Категория 2 - CLI выполняет, мы парсим:
```
[QwenCodeCLIAgent] Starting autonomous content processing with qwen-code CLI...
[QwenCodeCLIAgent._execute_qwen_cli] Executing qwen-code CLI...
[QwenCodeCLIAgent._execute_qwen_cli] Process completed with return code: 0
[QwenCodeCLIAgent] Changes detected: Created 2 file(s), Created 2 folder(s)
[QwenCodeCLIAgent] Successfully processed content: title='GPT-4', category='ai'
```

## Безопасность

### Категория 1: Валидация путей
- Все пути валидируются через `_validate_safe_path()`
- Запрещены абсолютные пути
- Запрещен path traversal (`..`)
- Все операции ограничены `kb_root_path`

### Категория 2: CLI работает в working_directory
- CLI ограничен своей рабочей директорией
- Prompt инструктирует использовать только относительные пути
- Опасные команды shell заблокированы в safe list

## Тестирование

Для проверки функционала:

```python
# Test Category 1
from src.agents.qwen_code_agent import QwenCodeAgent

agent = QwenCodeAgent(
    enable_file_management=True,
    enable_folder_management=True,
    kb_root_path=Path("./test_kb")
)

result = await agent.process({
    "text": "Test content about AI and biology"
})

# Проверить созданные файлы в test_kb/

# Test Category 2
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

agent = QwenCodeCLIAgent(
    working_directory="./test_kb"
)

result = await agent.process({
    "text": "Test content about AI and biology"
})

# Проверить metadata["files_created"]
# Проверить созданные файлы в test_kb/
```

## Заключение

### Достигнутые цели:

✅ **Категория 1 (QwenCodeAgent, OpenAIAgent):**
- Изменения применяются ПО ХОДУ РАБОТЫ агента (не разово в конце)
- Собирается итоговый отчет об изменениях
- Могут создавать несколько файлов и папок

✅ **Категория 2 (QwenCodeCLIAgent):**
- CLI сам изменяет файлы В ПРОЦЕССЕ СВОЕЙ РАБОТЫ
- Возвращает описание того, что сделал
- Может создавать несколько файлов и папок

✅ **StubAgent:**
- Остается простым без ИИ
- Создает один файл (через систему БЗ)

### Архитектурные улучшения:

1. **Четкое разделение на категории** - понятно какой агент за что отвечает
2. **Изменения в процессе работы** - не откладываются на потом
3. **Детальное логирование** - видно что происходит
4. **Отчетность** - понятно что было сделано
5. **Безопасность** - валидация путей и ограничения
6. **Множественные файлы** - все агенты (кроме stub) могут создавать несколько файлов/папок

### Следующие шаги:

- Тестирование на реальных данных
- Оптимизация промптов для лучшего разбиения на темы
- Мониторинг созданных файлов и структуры
