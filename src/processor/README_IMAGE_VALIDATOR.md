# Image Path Validator for File Processor

Валидация путей к изображениям перед отправкой в Docling для OCR.

## Быстрый старт

### Автоматическая валидация

Валидация запускается автоматически в `FileProcessor` перед отправкой изображений в Docling:

```python
from pathlib import Path
from src.processor.file_processor import FileProcessor

processor = FileProcessor()

# При обработке изображения валидация происходит автоматически
result = await processor.process_file(Path("/path/to/image.jpg"))

# Если валидация не прошла, вернется None и будет залогирована ошибка
if result is None:
    print("Image validation failed - check logs")
```

### Python API

```python
from pathlib import Path
from src.processor.image_path_validator import validate_image_path

# Проверить путь к изображению
img_path = Path("/kb/images/photo.jpg")
kb_images_dir = Path("/kb/images")

is_valid, error_msg = validate_image_path(img_path, kb_images_dir)

if not is_valid:
    print(f"Validation failed: {error_msg}")
else:
    print("✓ Image path is valid")
```

## Что проверяется

- ✅ Существование файла изображения
- ✅ Файл является файлом (не директорией)
- ✅ Расширение файла соответствует изображению
- ✅ Изображение находится внутри KB/images/ директории

## Когда происходит валидация

Валидация запускается в `FileProcessor` в двух местах:

### 1. При обработке файла (`process_file`)

Перед отправкой изображения в Docling:

```python
# file_processor.py - process_file()
if is_image:
    is_valid, error_msg = validate_image_path(file_path, self.images_dir)
    if not is_valid:
        logger.error(f"Image validation failed: {error_msg}")
        return None  # Прекращаем обработку
```

### 2. При скачивании из Telegram (`download_and_process_telegram_file`)

После сохранения изображения в KB/images/:

```python
# file_processor.py - download_and_process_telegram_file()
if save_to_kb and is_image:
    is_valid, error_msg = validate_image_path(save_path, kb_images_dir)
    if not is_valid:
        logger.error(f"Saved image failed validation: {error_msg}")
        logger.warning(f"Image saved but may have path issues")
    else:
        logger.info(f"✓ Image path validated: {save_path}")
```

### Логирование

```
[FileProcessor] ✓ Image path validated: /kb/images/img_1234567890_abc123.jpg
[FileProcessor] Image validation failed: Image is outside KB images directory
[FileProcessor] File path: /tmp/outside.jpg
[FileProcessor] Expected KB images dir: /kb/images
```

## Примеры проблем

### Файл не существует

❌ **Проблема:**
```python
img_path = Path("/kb/images/missing.jpg")
is_valid, error = validate_image_path(img_path)
# Returns: (False, "Image file does not exist: /kb/images/missing.jpg")
```

✅ **Решение:** Убедитесь что файл существует перед валидацией

### Изображение вне KB

❌ **Проблема:**
```python
img_path = Path("/tmp/photo.jpg")  # Вне KB
kb_images_dir = Path("/kb/images")
is_valid, error = validate_image_path(img_path, kb_images_dir)
# Returns: (False, "Image is outside KB images directory...")
```

✅ **Решение:** Сохраните изображение в KB/images/ перед обработкой

### Неправильное расширение

❌ **Проблема:**
```python
txt_file = Path("/kb/images/file.txt")
is_valid, error = validate_image_path(txt_file)
# Returns: (False, "File is not an image (extension: .txt)")
```

✅ **Решение:** Используйте поддерживаемые форматы: jpg, png, gif, tiff, bmp, webp

## Тесты

```bash
# Запустить тесты валидации путей
python3 -m pytest tests/test_file_processor_validation.py -v

# Все тесты должны пройти (10 passed)

# Запустить тесты markdown валидатора (для агентов)
python3 -m pytest tests/test_markdown_image_validator.py -v

# Все тесты должны пройти (13 passed)
```

## Документация

Полная документация: [docs_site/development/image-validation.md](../../docs_site/development/image-validation.md)

## Архитектура

```
src/processor/
├── image_path_validator.py      # Валидация путей к изображениям
│   └── validate_image_path()    # Функция валидации
│
├── file_processor.py             # Обработчик файлов (Docling)
│   ├── process_file()           # Валидация перед обработкой
│   └── download_and_process_telegram_file()  # Валидация после скачивания
│
└── markdown_image_validator.py  # Валидация markdown (для агентов)
    ├── MarkdownImageValidator   # Класс валидатора
    └── validate_* функции       # Удобные обертки

tests/
├── test_file_processor_validation.py     # Тесты (10 tests)
└── test_markdown_image_validator.py      # Тесты markdown (13 tests)
```

## Будущие улучшения

- [ ] Автоматическое исправление путей
- [ ] Проверка размеров изображений
- [ ] Поиск дубликатов изображений
- [ ] Pre-commit hook интеграция
- [ ] Оптимизация изображений

## Лицензия

Часть проекта tg-note
