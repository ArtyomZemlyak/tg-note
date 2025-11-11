# Markdown Image Path Validator

Автоматическая валидация путей к изображениям в markdown файлах, созданных агентами.

## Быстрый старт

### Автоматическая валидация

При создании/редактировании markdown файлов через агента валидация запускается автоматически:

```python
# Агент создает файл с изображением
result = await file_create_tool.execute({
    "path": "topics/guide.md",
    "content": "# Guide\n\n![Chart](../images/chart.jpg)"
})

# Результат содержит информацию о валидации
if result.get("validation_passed") is False:
    print("Обнаружены проблемы с путями к изображениям!")
    print(result.get("validation_warnings"))
```

### Ручная валидация

Проверка всей базы знаний:

```bash
# Простая проверка
python scripts/validate_kb_images.py /path/to/kb

# Детальный отчет
python scripts/validate_kb_images.py /path/to/kb --verbose
```

### Python API

```python
from pathlib import Path
from src.processor.markdown_image_validator import (
    validate_agent_generated_markdown,
    validate_kb_images,
    MarkdownImageValidator
)

# Проверить конкретный файл
kb_root = Path("/path/to/kb")
md_file = kb_root / "topics" / "example.md"
passed = validate_agent_generated_markdown(md_file, kb_root)

# Проверить всю базу знаний
error_count = validate_kb_images(kb_root, verbose=True)

# Расширенное использование
validator = MarkdownImageValidator(kb_root)
refs, issues = validator.validate_markdown_file(md_file)
unreferenced = validator.find_unreferenced_images()
```

## Что проверяется

- ✅ Существование файлов изображений
- ✅ Корректность относительных путей
- ✅ Расположение изображений внутри KB
- ✅ Качество alt-текста (описания)

## Уровни проблем

| Уровень | Описание | Пример |
|---------|----------|--------|
| **ERROR** | Файл не найден | `![](images/missing.jpg)` |
| **WARNING** | Изображение вне KB | `![](../../external.jpg)` |
| **INFO** | Некачественный alt-текст | `![image](photo.jpg)` |

## Интеграция

### File Tools

Валидация автоматически запускается в:
- `FileCreateTool` - при создании markdown файлов
- `FileEditTool` - при редактировании markdown файлов

### Логирование

```
[file_create] ✓ Created file: topics/guide.md (1234 bytes)
[file_create] Image validation error: Image file not found: images/chart.jpg
```

## Примеры проблем

### Неправильный относительный путь

❌ **Проблема:**
```markdown
<!-- Файл: topics/guide.md -->
![Chart](images/chart.jpg)
```

✅ **Решение:**
```markdown
<!-- Файл: topics/guide.md -->
![Chart](../images/chart.jpg)
```

### Отсутствующее изображение

❌ **Проблема:**
```markdown
![Screenshot](../images/missing.jpg)
```

✅ **Решение:**
1. Сохранить изображение в `KB/images/`
2. Обновить путь в markdown

### Плохой alt-текст

❌ **Проблема:**
```markdown
![image](../images/chart.jpg)
```

✅ **Решение:**
```markdown
![График роста выручки за Q4 2024: +45%](../images/chart.jpg)
```

## Тесты

```bash
# Запустить тесты
python3 -m pytest tests/test_markdown_image_validator.py -v

# Все тесты должны пройти (13 passed)
```

## Документация

Полная документация: [docs_site/development/image-validation.md](../../docs_site/development/image-validation.md)

## Архитектура

```
src/processor/
├── markdown_image_validator.py  # Основной модуль
│   ├── MarkdownImageValidator   # Класс валидатора
│   ├── ImageReference           # Ссылка на изображение
│   ├── ValidationIssue          # Проблема валидации
│   └── validate_* функции       # Удобные обертки
│
scripts/
└── validate_kb_images.py        # CLI инструмент

src/agents/tools/
└── file_tools.py                # Интеграция в file_create/file_edit

tests/
└── test_markdown_image_validator.py  # Тесты (13 tests)
```

## Будущие улучшения

- [ ] Автоматическое исправление путей
- [ ] Проверка размеров изображений
- [ ] Поиск дубликатов изображений
- [ ] Pre-commit hook интеграция
- [ ] Оптимизация изображений

## Лицензия

Часть проекта tg-note
