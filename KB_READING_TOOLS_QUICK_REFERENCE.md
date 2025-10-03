# Knowledge Base Reading Tools - Quick Reference

## Быстрый старт

```python
from src.agents.autonomous_agent import AutonomousAgent
from pathlib import Path

# Создать агента с KB
agent = AutonomousAgent(
    llm_connector=None,  # или ваш LLM connector
    kb_root_path=Path("./my_knowledge_base")
)

# Все 4 тулзы доступны автоматически!
```

---

## 📖 kb_read_file - Чтение файлов

**Что делает:** Читает один или несколько файлов из базы знаний

**Когда использовать:**
- Нужно прочитать существующий контент
- Проверить содержимое перед редактированием
- Получить информацию из нескольких связанных файлов

```python
result = await agent._tool_kb_read_file({
    "paths": ["topics/ai/neural-networks.md", "topics/ai/deep-learning.md"]
})

# result["results"][0]["content"] - содержимое первого файла
# result["results"][0]["size"] - размер в байтах
```

**Возвращает:**
- `success`: boolean
- `files_read`: количество прочитанных файлов  
- `results`: массив с содержимым и метаданными
- `errors`: ошибки по каждому файлу (если есть)

---

## 📁 kb_list_directory - Список содержимого папки

**Что делает:** Перечисляет файлы и папки в директории

**Когда использовать:**
- Исследовать структуру KB
- Получить список файлов для обработки
- Собрать статистику по категориям

```python
# Список файлов в папке (не рекурсивно)
result = await agent._tool_kb_list_directory({
    "path": "topics/ai",
    "recursive": False
})

# Все файлы и подпапки рекурсивно
result = await agent._tool_kb_list_directory({
    "path": "topics",
    "recursive": True
})

# result["files"] - список файлов
# result["directories"] - список папок
```

**Возвращает:**
- `success`: boolean
- `files`: массив файлов с размерами
- `directories`: массив папок
- `file_count`: количество файлов
- `directory_count`: количество папок

---

## 🔍 kb_search_files - Поиск по именам файлов

**Что делает:** Ищет файлы и папки по glob-шаблону

**Когда использовать:**
- Найти все файлы определенного типа
- Искать файлы по части имени
- Фильтровать файлы по расширению

```python
# Все markdown файлы
result = await agent._tool_kb_search_files({
    "pattern": "*.md"
})

# Файлы с "neural" в названии
result = await agent._tool_kb_search_files({
    "pattern": "*neural*",
    "case_sensitive": False
})

# Все .md файлы в topics/ai/ и подпапках
result = await agent._tool_kb_search_files({
    "pattern": "topics/ai/**/*.md"
})
```

**Glob шаблоны:**
- `*` - любые символы
- `?` - один символ
- `**` - любые подпапки
- `[abc]` - один из символов a, b, c

**Возвращает:**
- `success`: boolean
- `files`: найденные файлы
- `directories`: найденные папки
- `file_count`: количество файлов
- `directory_count`: количество папок

---

## 🔎 kb_search_content - Поиск по содержимому

**Что делает:** Ищет текст внутри файлов (full-text search)

**Когда использовать:**
- Найти упоминания концепта/темы
- Проверить наличие информации
- Найти связанные статьи

```python
# Найти все упоминания "machine learning"
result = await agent._tool_kb_search_content({
    "query": "machine learning",
    "case_sensitive": False,
    "file_pattern": "*.md"
})

# Поиск только в AI категории
result = await agent._tool_kb_search_content({
    "query": "neural networks",
    "file_pattern": "topics/ai/**/*.md"
})

# result["matches"][0]["line_number"] - номер строки
# result["matches"][0]["context"] - контекст вокруг найденного
```

**Возвращает:**
- `success`: boolean
- `matches`: массив файлов с совпадениями
  - `path`: путь к файлу
  - `occurrences`: количество вхождений
  - `matches`: до 5 первых совпадений с контекстом
- `files_found`: количество файлов с совпадениями

---

## 🔐 Безопасность

Все инструменты защищены от:
- ✅ Path traversal (`../../../etc/passwd`)
- ✅ Доступа за пределы KB root
- ✅ Чтения системных файлов

```python
# ❌ Заблокировано
result = await agent._tool_kb_read_file({
    "paths": ["../../../etc/passwd"]
})
# result["success"] == False
# result["errors"][0]["error"] - "Path traversal (..) is not allowed"
```

---

## 🎯 Типичные сценарии

### Сценарий 1: Проверка дубликатов

```python
# Перед созданием новой статьи - проверить дубликаты
search = await agent._tool_kb_search_content({
    "query": "neural networks",
    "file_pattern": "topics/ai/*.md"
})

if search["files_found"] > 0:
    # Есть похожие статьи - прочитать их
    files = await agent._tool_kb_read_file({
        "paths": [m["path"] for m in search["matches"]]
    })
    # Дополнить существующее вместо создания нового
```

### Сценарий 2: Анализ структуры KB

```python
# Получить все категории
categories = await agent._tool_kb_list_directory({
    "path": "topics",
    "recursive": False
})

# Для каждой категории - статистика
for cat in categories["directories"]:
    stats = await agent._tool_kb_list_directory({
        "path": cat["path"],
        "recursive": True
    })
    print(f"{cat['name']}: {stats['file_count']} файлов")
```

### Сценарий 3: Поиск связей

```python
# Найти все файлы упоминающие "Python"
refs = await agent._tool_kb_search_content({
    "query": "Python"
})

# Построить граф связей
for match in refs["matches"]:
    print(f"{match['path']}: {match['occurrences']} упоминаний")
```

---

## ⚡ Производительность

**Рекомендации:**

| Инструмент | Рекомендация |
|-----------|-------------|
| `kb_read_file` | Читайте 5-20 файлов за раз, не больше |
| `kb_list_directory` | Используйте `recursive=false` когда возможно |
| `kb_search_files` | Конкретные шаблоны лучше чем `*` |
| `kb_search_content` | Указывайте `file_pattern` для ускорения |

**Ограничения:**
- `kb_search_content` возвращает максимум 5 совпадений на файл
- Все операции синхронные (могут быть медленными на больших KB)

---

## 📝 Примеры в коде

См. `examples/kb_reading_tools_example.py` для полных примеров:
- Чтение файлов
- Листинг директорий  
- Поиск по шаблонам
- Поиск по содержимому
- Комбинированные сценарии
- Обработка ошибок

Запустить:
```bash
python examples/kb_reading_tools_example.py
```

---

## 🧪 Тестирование

```bash
pytest tests/test_kb_reading_tools.py -v
```

Тесты покрывают:
- ✅ Чтение одного и нескольких файлов
- ✅ Рекурсивный и обычный листинг
- ✅ Поиск по glob-шаблонам
- ✅ Полнотекстовый поиск
- ✅ Безопасность (path traversal)
- ✅ Обработка ошибок

---

## 📚 Полная документация

См. `docs_site/agents/kb-reading-tools.md` для:
- Детальное описание параметров
- Примеры JSON ответов
- Интеграция с LLM
- Расширение новыми инструментами
