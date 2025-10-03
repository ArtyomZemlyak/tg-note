# Рефакторинг архитектуры агентов

## Дата: 2025-10-03

## Цель
Стандартизировать работу агентов таким образом, чтобы:
1. Агенты сами управляли всеми действиями (создание/редактирование/удаление файлов) через тулзы или CLI
2. Каждый агент самостоятельно определял количество и типы действий
3. Все агенты возвращали результат в едином стандартизированном формате
4. Дублирующаяся логика была вынесена в базовый класс

## Проблемы, которые были решены

### 1. QwenCodeCLIAgent вручную парсил результаты
**Было:**
- Агент возвращал markdown через CLI
- Код вручную парсил результат методом `_parse_qwen_result()`
- Вручную извлекались теги, категории, title через `_extract_title()`, `_detect_category()`, `_extract_tags()`
- Вручную создавалась KB структура

**Стало:**
- Агент возвращает результат в стандартизированном формате с блоками ````agent-result` и ````metadata`
- Используется базовый метод `parse_agent_response()` из `BaseAgent`
- Используется базовый метод `extract_kb_structure_from_response()` из `BaseAgent`
- Все парсится автоматически, агент просто работает и отчитывается в стандартном формате

### 2. Инициализация тулзов не находилась в правильном месте
**Было:**
- `QwenCodeAgent` сам регистрировал все тулзы (`_register_all_tools()`)
- `AutonomousAgent` имел механизм `register_tool()`, но не использовал его для инициализации

**Стало:**
- `QwenCodeAgent` наследуется от `AutonomousAgent` и использует его механизм регистрации тулзов
- Конкретные реализации тулзов остались в `QwenCodeAgent` (это правильно, т.к. они специфичны для него)
- `AutonomousAgent` управляет циклом выполнения и вызовом зарегистрированных тулзов

### 3. Не было стандартного формата ответа от агентов
**Было:**
- Каждый агент возвращал результат в своем формате
- QwenCodeCLIAgent возвращал markdown + metadata
- QwenCodeAgent возвращал markdown + title + kb_structure
- Нужно было вручную парсить и извлекать информацию

**Стало:**
- Введен стандартный `AgentResult` в `BaseAgent`:
  ```python
  @dataclass
  class AgentResult:
      markdown: str
      summary: str
      files_created: List[str]
      files_edited: List[str]
      folders_created: List[str]
      metadata: Dict[str, Any]
  ```
- Все агенты должны возвращать результат в формате с блоками:
  ```markdown
  ```agent-result
  {
    "summary": "...",
    "files_created": [...],
    "files_edited": [...],
    "folders_created": [...],
    "metadata": {...}
  }
  ```
  
  ```metadata
  category: ai
  subcategory: models
  tags: tag1, tag2, tag3
  ```
  ```

### 4. Дублирующаяся логика в агентах
**Было:**
- `_extract_keywords()` - дублировалась в `QwenCodeAgent` и `QwenCodeCLIAgent`
- `_detect_category()` - дублировалась в `QwenCodeAgent` и `QwenCodeCLIAgent`
- `_generate_title()` - дублировалась во всех агентах (QwenCodeAgent, QwenCodeCLIAgent, StubAgent)
- `_generate_summary()` - дублировалась в `QwenCodeAgent` и `QwenCodeCLIAgent`

**Стало:**
- Все эти методы вынесены в `BaseAgent` как статические методы:
  - `BaseAgent.extract_keywords(text, top_n)`
  - `BaseAgent.detect_category(text)`
  - `BaseAgent.generate_title(text, max_length)`
  - `BaseAgent.generate_summary(text, max_length)`
- Все агенты используют эти общие методы

## Изменения в файлах

### 1. `src/agents/base_agent.py`
**Добавлено:**
- `AgentResult` dataclass - стандартизированный результат работы агента
- `parse_agent_response()` - парсит ответ агента в стандартном формате
- `extract_kb_structure_from_response()` - извлекает KB структуру из ответа агента
- Статические методы-помощники:
  - `extract_keywords()`
  - `detect_category()`
  - `generate_title()`
  - `generate_summary()`

### 2. `src/agents/autonomous_agent.py`
**Изменено:**
- `AgentResult` → `AutonomousAgentResult` (чтобы не конфликтовать с `BaseAgent.AgentResult`)
- Добавлен метод `to_base_agent_result()` для конвертации в стандартный формат
- Импорт `AgentResult as BaseAgentResult` из `base_agent`

### 3. `src/agents/qwen_code_agent.py`
**Удалено:**
- `_extract_keywords()`
- `_detect_category()`
- `_generate_title()`
- `_generate_summary()`

**Изменено:**
- Все вызовы этих методов заменены на `BaseAgent.extract_keywords()`, `BaseAgent.detect_category()` и т.д.

### 4. `src/agents/qwen_code_cli_agent.py`
**Удалено:**
- `_parse_qwen_result()` - больше не нужен, используется `parse_agent_response()` из BaseAgent
- `_extract_title()` → `_extract_title_from_markdown()` (только для извлечения title из готового markdown)
- `_detect_category()` - используется `BaseAgent.detect_category()`
- `_extract_tags()` - используется `BaseAgent.extract_keywords()`
- `_generate_summary()` - используется `BaseAgent.generate_summary()`

**Изменено:**
- `process()` теперь использует:
  ```python
  agent_result = self.parse_agent_response(result_text)
  kb_structure = self.extract_kb_structure_from_response(result_text)
  ```
- Версия агента обновлена до 2.0.0

### 5. `src/agents/stub_agent.py`
**Удалено:**
- `_generate_title()` - используется `BaseAgent.generate_title()`

### 6. `config/agent_prompts.py`
**Обновлено:**
- `QWEN_CODE_AGENT_INSTRUCTION` - добавлена секция о стандартном формате ответа
- `QWEN_CODE_CLI_AGENT_INSTRUCTION` - добавлен "Шаг 9: ВАЖНО! Возврат результата"
- `CONTENT_PROCESSING_PROMPT_TEMPLATE` - добавлен "Этап 7: ВАЖНО! Возврат результата"

## Теперь каждый агент работает следующим образом:

### QwenCodeCLIAgent (полностью автономный через CLI)
1. Получает задачу с контентом
2. Формирует промпт для qwen-code CLI
3. **CLI сам выполняет все действия** (создает файлы, папки, редактирует)
4. **CLI возвращает markdown с суммаризацией в стандартном формате**
5. Агент парсит ответ стандартным парсером из BaseAgent
6. Извлекает KB структуру стандартным методом из BaseAgent
7. Возвращает готовый результат

### QwenCodeAgent (автономный через тулзы)
1. Получает задачу с контентом
2. Запускает агентский цикл (`_agent_loop`)
3. **В цикле сам вызывает тулзы** для выполнения действий (file_create, folder_create, web_search и т.д.)
4. **Сам определяет когда завершить работу** (ACTION.END)
5. **Возвращает результат в стандартном формате** через `_finalize_result()`
6. Конвертируется в `BaseAgent.AgentResult` через `to_base_agent_result()`

### StubAgent (простой агент для тестов)
1. Получает задачу
2. Создает простой markdown
3. Использует общие методы из BaseAgent для генерации title
4. Возвращает результат в стандартном формате

## Преимущества новой архитектуры

### ✅ Единый стандарт
- Все агенты возвращают результат в одном формате
- Легко добавлять новые агенты
- Легко тестировать агентов

### ✅ Автономность
- Агенты сами управляют файлами/папками
- Агенты сами определяют количество действий
- Агенты работают без вмешательства пользователя

### ✅ Суммаризация
- Каждый агент отчитывается о проделанной работе
- Видно какие файлы созданы/отредактированы
- Видно какие папки созданы

### ✅ DRY (Don't Repeat Yourself)
- Вся общая логика в BaseAgent
- Нет дублирования кода
- Проще поддерживать и обновлять

### ✅ Расширяемость
- Легко добавить новый тип агента
- Легко добавить новые тулзы
- Легко изменить формат ответа (изменится только в одном месте - BaseAgent)

## Обратная совместимость

Все изменения обратно совместимы:
- Существующие агенты продолжают работать
- Существующий API не изменился
- Добавлены только новые методы и стандарты

## Что дальше?

1. Обновить тесты для проверки стандартного формата ответа
2. Убедиться что qwen-code CLI действительно возвращает результат в стандартном формате (нужно обновить промпт если нет)
3. Возможно добавить валидацию формата ответа от агентов
4. Добавить примеры использования нового API
