# Knowledge Base Reading Tools

Автономный агент теперь имеет набор инструментов для чтения и поиска в базе знаний. Эти инструменты позволяют агенту взаимодействовать с существующими данными в KB перед созданием нового контента.

## Доступные инструменты

### 1. `kb_read_file` - Чтение файлов

Читает один или несколько файлов из базы знаний.

**Параметры:**
- `paths` (array of strings, обязательный) - Список относительных путей к файлам

**Пример использования:**
```json
{
  "paths": ["topics/ai/neural-networks.md", "topics/tech/python.md"]
}
```

**Возвращает:**
```json
{
  "success": true,
  "files_read": 2,
  "results": [
    {
      "path": "topics/ai/neural-networks.md",
      "full_path": "/path/to/kb/topics/ai/neural-networks.md",
      "content": "# Neural Networks\n\n...",
      "size": 1234
    }
  ],
  "errors": null
}
```

**Особенности:**
- Поддерживает чтение нескольких файлов за один вызов
- Валидация путей для предотвращения path traversal атак
- Возвращает содержимое и метаданные каждого файла
- Обрабатывает ошибки отдельно для каждого файла

---

### 2. `kb_list_directory` - Перечисление содержимого папки

Перечисляет файлы и папки в указанной директории.

**Параметры:**
- `path` (string, обязательный) - Относительный путь к папке. Пустая строка для корня.
- `recursive` (boolean, опциональный) - Рекурсивно перечислить все подпапки (по умолчанию `false`)

**Пример использования:**
```json
{
  "path": "topics/ai",
  "recursive": false
}
```

**Возвращает:**
```json
{
  "success": true,
  "path": "topics/ai",
  "recursive": false,
  "files": [
    {
      "path": "topics/ai/neural-networks.md",
      "name": "neural-networks.md",
      "size": 1234
    }
  ],
  "directories": [
    {
      "path": "topics/ai/machine-learning",
      "name": "machine-learning"
    }
  ],
  "file_count": 1,
  "directory_count": 1
}
```

**Особенности:**
- Может работать рекурсивно для получения всего дерева файлов
- Возвращает отдельно файлы и папки
- Включает размер файлов
- Безопасная валидация путей

---

### 3. `kb_search_files` - Поиск файлов по названию

Ищет файлы и папки по названию или glob-шаблону.

**Параметры:**
- `pattern` (string, обязательный) - Шаблон поиска (поддерживает glob: `*`, `?`, `[]`)
- `case_sensitive` (boolean, опциональный) - Регистрозависимый поиск (по умолчанию `false`)

**Примеры шаблонов:**
- `*.md` - все markdown файлы
- `ai/**/*.md` - все markdown файлы в папке ai и подпапках
- `*neural*` - файлы содержащие "neural" в названии

**Пример использования:**
```json
{
  "pattern": "*neural*.md",
  "case_sensitive": false
}
```

**Возвращает:**
```json
{
  "success": true,
  "pattern": "*neural*.md",
  "case_sensitive": false,
  "files": [
    {
      "path": "topics/ai/neural-networks.md",
      "name": "neural-networks.md",
      "size": 1234
    }
  ],
  "directories": [],
  "file_count": 1,
  "directory_count": 0
}
```

**Особенности:**
- Поддержка glob-шаблонов
- Поиск как по полному пути, так и только по имени файла
- Регистронезависимый поиск по умолчанию
- Возвращает и файлы, и директории

---

### 4. `kb_search_content` - Поиск по содержимому

Ищет текст внутри файлов в базе знаний.

**Параметры:**
- `query` (string, обязательный) - Текст для поиска
- `case_sensitive` (boolean, опциональный) - Регистрозависимый поиск (по умолчанию `false`)
- `file_pattern` (string, опциональный) - Glob шаблон для фильтрации файлов (по умолчанию `*.md`)

**Пример использования:**
```json
{
  "query": "machine learning",
  "case_sensitive": false,
  "file_pattern": "*.md"
}
```

**Возвращает:**
```json
{
  "success": true,
  "query": "machine learning",
  "case_sensitive": false,
  "file_pattern": "*.md",
  "matches": [
    {
      "path": "topics/ai/neural-networks.md",
      "name": "neural-networks.md",
      "occurrences": 3,
      "matches": [
        {
          "line_number": 5,
          "line": "Machine learning is a subset of AI",
          "context": "# Introduction\n\nMachine learning is a subset of AI\nthat focuses on..."
        }
      ]
    }
  ],
  "files_found": 1
}
```

**Особенности:**
- Полнотекстовый поиск по содержимому файлов
- Возвращает номера строк и контекст вокруг найденного текста
- Ограничение: первые 5 совпадений на файл
- Фильтрация по типу файлов через glob-шаблон
- Эффективный поиск только в нужных файлах

---

## Безопасность

Все инструменты включают валидацию путей для предотвращения:
- Path traversal атак (`../../../etc/passwd`)
- Доступа за пределы корня базы знаний
- Чтения системных файлов

Все пути должны быть относительными и находиться внутри `kb_root_path`.

---

## Примеры использования

### Сценарий 1: Проверка существующего контента перед созданием

```python
# Агент сначала ищет существующие файлы о нейронных сетях
result = await agent._execute_tool({
    "tool_name": "kb_search_files",
    "tool_params": {"pattern": "*neural*.md"}
})

# Если находит, читает их
if result["file_count"] > 0:
    read_result = await agent._execute_tool({
        "tool_name": "kb_read_file",
        "tool_params": {"paths": [f["path"] for f in result["files"]]}
    })
    # Анализирует контент и дополняет, а не дублирует
```

### Сценарий 2: Структурированное исследование базы знаний

```python
# Список всех категорий
categories = await agent._execute_tool({
    "tool_name": "kb_list_directory",
    "tool_params": {"path": "topics", "recursive": False}
})

# Для каждой категории получить статистику
for category in categories["directories"]:
    files = await agent._execute_tool({
        "tool_name": "kb_list_directory",
        "tool_params": {"path": category["path"], "recursive": True}
    })
```

### Сценарий 3: Поиск связанных тем

```python
# Ищет все упоминания "Python" в базе
python_refs = await agent._execute_tool({
    "tool_name": "kb_search_content",
    "tool_params": {
        "query": "Python",
        "file_pattern": "*.md"
    }
})

# Создает карту связей между темами
```

---

## Интеграция с агентским циклом

Эти инструменты автоматически доступны в агентском цикле и могут быть вызваны LLM через function calling:

```python
agent = AutonomousAgent(
    llm_connector=openai_connector,
    kb_root_path=Path("./my_knowledge_base")
)

# LLM может решить использовать любой из этих инструментов
# на основе задачи и контекста
result = await agent.process({
    "text": "Find and summarize all articles about machine learning"
})
```

LLM сам решает:
1. Какие инструменты использовать
2. В каком порядке их вызывать
3. Как объединить результаты

---

## Производительность

**Рекомендации:**

1. **kb_read_file**: Читайте несколько файлов за раз, но не более 10-20 одновременно
2. **kb_list_directory**: Используйте `recursive=false` когда возможно
3. **kb_search_files**: Используйте специфичные шаблоны вместо `*`
4. **kb_search_content**: Указывайте `file_pattern` для ограничения области поиска

**Ограничения:**

- `kb_search_content` возвращает максимум 5 совпадений на файл
- Все операции выполняются синхронно (в будущем могут быть оптимизированы)
- Рекурсивный listing может быть медленным на больших базах

---

## Расширение

Для добавления новых инструментов чтения KB:

1. Создайте метод `_tool_kb_your_tool` в `AutonomousAgent`
2. Зарегистрируйте в `_register_all_tools()`
3. Добавьте схему в `_build_tools_schema()`
4. Добавьте тесты в `tests/test_kb_reading_tools.py`

Пример:
```python
async def _tool_kb_get_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Get statistics about knowledge base"""
    # Implementation
    pass
```
