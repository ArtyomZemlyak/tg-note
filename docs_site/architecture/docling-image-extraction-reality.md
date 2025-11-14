# Реальность: Как Docling извлекает изображения из PDF

## Важные вопросы

1. **Делает ли Docling извлечение изображений?** 
   - ✅ **ДА**, но с ограничениями

2. **Как именно Docling это делает?**
   - Docling может генерировать изображения из PDF через опцию `generate_picture_images`
   - Но **не предоставляет их напрямую через MCP API**

3. **Как извлекаются подписи?**
   - Docling может генерировать описания через VLM (`picture_description`)
   - Но это требует дополнительной настройки и моделей

## Что реально делает Docling

### 1. Обработка PDF

Docling обрабатывает PDF и создает структурированный документ (`Document` объект), который содержит:
- Текст (извлеченный и распознанный через OCR)
- Структуру документа (заголовки, параграфы, таблицы)
- Метаданные о изображениях (позиция, размер, тип)
- **НО НЕ САМИ ИЗОБРАЖЕНИЯ КАК БИНАРНЫЕ ФАЙЛЫ**

### 2. Экспорт в Markdown

Когда вызывается `document.export_to_markdown()`, Docling:
- Конвертирует структуру документа в markdown
- **Может встроить изображения как base64** в markdown (если `keep_images=True`)
- Или может оставить только ссылки/плейсхолдеры

### 3. Опции Docling для работы с изображениями

Из кода `converter.py`:

```python
# Генерировать изображения картинок из PDF
pdf_options.generate_picture_images = True/False

# Сохранять изображения в документе
settings.keep_images = True/False

# Генерировать описания картинок через VLM
pdf_options.do_picture_description = True/False
```

## Проблема текущей реализации

### Что я предположил (неправильно):

1. ❌ Docling возвращает resource URIs для изображений через MCP
2. ❌ Можно вызвать `read_resource(uri)` и получить изображение
3. ❌ Таблицы доступны как отдельные JSON ресурсы

### Что реально происходит:

1. ✅ Docling обрабатывает PDF и создает структурированный документ
2. ✅ Docling может экспортировать в markdown
3. ❓ **Изображения могут быть встроены в markdown как base64** (если `keep_images=True`)
4. ❓ **Или изображения могут быть недоступны через MCP API**

## Как это должно работать на самом деле

### Вариант 1: Изображения в markdown как base64

Если Docling встраивает изображения в markdown:

```markdown
# Document

![Figure 1](data:image/png;base64,iVBORw0KGgoAAAANS...)
```

Тогда нужно:
1. Парсить markdown
2. Извлекать base64 изображения
3. Декодировать и сохранять в `images/`
4. Заменять в markdown на относительные пути

### Вариант 2: Docling не предоставляет изображения через MCP

Если Docling не предоставляет изображения через MCP API, то:
1. Нужно использовать локальный DocumentConverter (не через MCP)
2. Или использовать другой инструмент для извлечения изображений из PDF

### Вариант 3: Использовать PyMuPDF или pdf2image

Альтернативный подход:
1. Использовать PyMuPDF (`fitz`) для извлечения изображений напрямую из PDF
2. Использовать pdf2image для конвертации страниц в изображения
3. Сохранять изображения в KB
4. Docling используется только для текста и структуры

## Подписи к изображениям

### Что может делать Docling:

1. **Picture Description через VLM:**
   - Требует модель (smolvlm, granitedocling)
   - Генерирует описание изображения через Vision-Language Model
   - Может быть включено в markdown как текст под изображением

2. **OCR текста рядом с изображением:**
   - Docling может распознать текст под/над изображением
   - Но это не гарантирует, что это именно подпись

3. **Метаданные из PDF:**
   - PDF может содержать метаданные об изображениях
   - Но это редко используется

## Что нужно сделать

### Шаг 1: Проверить, что реально возвращает Docling

```python
# Добавить логирование
result = await client.call_tool("convert_document_from_content", {...})
markdown = result.get("markdown")

# Проверить:
# 1. Есть ли в markdown base64 изображения?
# 2. Есть ли resource URIs?
# 3. Что в структуре документа?
```

### Шаг 2: Если изображения в markdown как base64

Реализовать парсинг:

```python
import re
import base64

def extract_images_from_markdown(markdown: str) -> List[Dict]:
    pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
    images = []
    
    for match in re.finditer(pattern, markdown):
        alt_text = match.group(1)  # Подпись!
        image_type = match.group(2)  # png, jpeg
        base64_data = match.group(3)
        
        image_bytes = base64.b64decode(base64_data)
        # Сохранить в images/
        # Вернуть метаданные с alt_text
```

### Шаг 3: Если Docling не предоставляет изображения

Использовать альтернативный подход:

```python
import fitz  # PyMuPDF

def extract_images_from_pdf(pdf_path: Path) -> List[Dict]:
    doc = fitz.open(pdf_path)
    images = []
    
    for page_num, page in enumerate(doc):
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            # Сохранить изображение
            # Попытаться найти подпись (текст под/над изображением)
            # Вернуть метаданные
```

## Вывод

**Текущая реализация - это основа, но она неполная.**

Нужно:
1. ✅ Проверить, что реально возвращает Docling
2. ⏳ Реализовать парсинг markdown для base64 изображений (если они там)
3. ⏳ Или использовать PyMuPDF для прямого извлечения из PDF
4. ⏳ Обработать подписи (через VLM или OCR текста рядом)

**Честный ответ:** Я реализовал код, который предполагает, что Docling предоставляет ресурсы через MCP, но это нужно проверить. Скорее всего, изображения встроены в markdown как base64, и их нужно парсить оттуда.
