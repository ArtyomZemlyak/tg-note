# Проверка реальности: Что Docling реально делает

## Критические вопросы

1. **Делает ли Docling извлечение изображений из PDF?**
2. **Как именно Docling предоставляет изображения через MCP API?**
3. **Как извлекаются подписи к изображениям?**

## Что я нашел в коде

### 1. Что возвращает Docling MCP инструмент `convert_document_from_content`

Из `/workspace/docker/docling-mcp/app/tg_docling/tools.py`:

```python
result_dict = {
    "from_cache": False,
    "document_key": cache_key,
}

if export_format:
    if export_format_lower == "markdown":
        markdown_text = document.export_to_markdown()
        result_dict["markdown"] = markdown_text
```

**Вывод:** Docling возвращает только:
- `document_key` - уникальный идентификатор документа
- Опционально `markdown` - если `export_format="markdown"`

**НЕТ resource URIs в ответе!**

### 2. Что делает `export_to_markdown()`

Это метод из библиотеки Docling. Нужно проверить:
- Встраивает ли он изображения как base64 в markdown?
- Или оставляет только плейсхолдеры?
- Или вообще не включает изображения?

### 3. Текущая реализация ищет resource URIs

Из `/workspace/src/processor/file_processor.py`:

```python
elif item_type == "resource":
    resource = item.get("resource") or {}
    uri = resource.get("uri")
    if uri:
        resource_uris.append(uri)
```

**Проблема:** Код ищет resource URIs, но Docling их не возвращает!

### 4. Опции Docling для работы с изображениями

Из `/workspace/docker/docling-mcp/app/tg_docling/converter.py`:

```python
# Генерировать изображения картинок из PDF
pdf_options.generate_picture_images = True/False

# Сохранять изображения в документе
settings.keep_images = True/False

# Генерировать описания картинок через VLM
pdf_options.do_picture_description = True/False
```

**Вопрос:** Что делают эти опции?
- `generate_picture_images` - генерирует ли изображения как бинарные файлы?
- `keep_images` - сохраняет ли изображения в структуре документа?
- `do_picture_description` - генерирует ли описания через VLM?

## Что нужно проверить

### Тест 1: Что возвращает Docling для PDF с изображениями

```python
# Отправить PDF с изображениями
result = await client.call_tool(
    "convert_document_from_content",
    {
        "content": base64_pdf,
        "export_format": "markdown"
    }
)

# Проверить:
# 1. Есть ли в result["markdown"] base64 изображения?
# 2. Есть ли resource URIs в result?
# 3. Что в структуре документа?
```

### Тест 2: Что делает `export_to_markdown()` с `keep_images=True`

```python
# Включить keep_images=True в конфиге
# Проверить, встраивает ли markdown изображения как base64
```

### Тест 3: Есть ли другие инструменты для экспорта ресурсов

```python
# Проверить список доступных инструментов
tools = await client.list_tools()
# Есть ли инструменты для экспорта изображений/таблиц?
```

## Возможные сценарии

### Сценарий 1: Изображения встроены в markdown как base64

Если `keep_images=True` и `export_to_markdown()` встраивает изображения:

```markdown
# Document

![Figure 1](data:image/png;base64,iVBORw0KGgoAAAANS...)
```

**Решение:** Парсить markdown, извлекать base64, декодировать и сохранять.

### Сценарий 2: Docling не предоставляет изображения через MCP

Если Docling не предоставляет изображения через MCP API:

**Решение:** Использовать альтернативный подход:
- PyMuPDF для прямого извлечения из PDF
- pdf2image для конвертации страниц
- Docling только для текста и структуры

### Сценарий 3: Изображения доступны через отдельный инструмент

Если Docling предоставляет отдельный инструмент для экспорта ресурсов:

**Решение:** Вызвать этот инструмент с `document_key` и получить ресурсы.

## Подписи к изображениям

### Что может делать Docling:

1. **Picture Description через VLM:**
   - Требует модель (smolvlm, granitedocling)
   - Генерирует описание изображения
   - Может быть включено в markdown как текст

2. **OCR текста рядом с изображением:**
   - Docling может распознать текст под/над изображением
   - Но это не гарантирует, что это подпись

3. **Метаданные из PDF:**
   - PDF может содержать метаданные об изображениях
   - Но это редко используется

## Вывод

**Текущая реализация - это предположение, которое нужно проверить.**

Нужно:
1. ✅ Проверить, что реально возвращает Docling для PDF с изображениями
2. ⏳ Если изображения в markdown как base64 - парсить markdown
3. ⏳ Если Docling не предоставляет изображения - использовать PyMuPDF
4. ⏳ Если есть отдельный инструмент - использовать его
5. ⏳ Обработать подписи (через VLM или OCR текста рядом)

**Честный ответ пользователю:** Я реализовал код, который предполагает, что Docling предоставляет ресурсы через MCP, но это нужно проверить. Скорее всего, изображения либо встроены в markdown как base64 (если `keep_images=True`), либо вообще не доступны через MCP API.
