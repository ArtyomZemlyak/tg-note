# PDF Processing Research: Docling Integration

**Дата**: 2025-11-13  
**Статус**: Research Document  
**Цель**: Исследование возможностей извлечения и использования картинок, таблиц и графиков из PDF через Docling

---

## Содержание

1. [Что умеет Docling](#что-умеет-docling)
2. [Как передавать PDF в Docling](#как-передавать-pdf-в-docling)
3. [Как получать результат от Docling](#как-получать-результат-от-docling)
4. [Как передавать результат агенту](#как-передавать-результат-агенту)
5. [Как хранить PDF и распознанные версии](#как-хранить-pdf-и-распознанные-версии)
6. [План реализации](#план-реализации)

---

## Что умеет Docling

### Официальная документация

**GitHub**: https://github.com/DS4SD/docling  
**Docs**: https://docling-project.github.io/docling/

### Основные возможности

#### 1. **Layout Analysis** (Анализ структуры документа)

Docling использует специализированную AI-модель для распознавания структуры документа:

```python
# Модели Layout Analysis
DOCLING_LAYOUT_V2          # Рекомендуемая (default)
DOCLING_LAYOUT_HERON       # Более точная
DOCLING_LAYOUT_HERON_101   # Еще более точная
DOCLING_LAYOUT_EGRET_*     # Специализированные варианты
```

**Что распознается**:
- Заголовки (H1-H6)
- Параграфы текста
- Списки (numbered, bulleted)
- **Таблицы** (table boundaries)
- **Изображения/Рисунки** (picture boundaries)
- **Формулы** (code/formula blocks)
- Колонтитулы (headers/footers)
- Сноски (footnotes)

**Источник**: `src/processor/docling_runtime.py:338-343`, `docker/docling-mcp/app/tg_docling/converter.py:11-17`

#### 2. **Table Structure Extraction** (Извлечение структуры таблиц)

```yaml
pipeline:
  table_structure:
    enabled: true
    mode: accurate  # или fast
    do_cell_matching: true
```

**Возможности**:
- Распознавание строк и столбцов
- Объединенные ячейки (merged cells)
- Извлечение данных из каждой ячейки
- Экспорт в markdown table format
- Сохранение в JSON с полной структурой

**Модель**: TableFormer (основана на transformer architecture)

**Источник**: `docker/docling-mcp/README.md:144-145`, `docker/docling-mcp/app/tg_docling/converter.py:375-382`

#### 3. **Picture/Image Extraction** (Извлечение изображений)

```yaml
pipeline:
  picture_classifier: true           # Классификация картинок
  picture_description:               # Описание содержимого
    enabled: true
    model: smolvlm                   # или granitedocling, granite_vision
```

**Возможности**:
- **Автоматическое извлечение всех картинок** из PDF
- Классификация типа картинки (photo, diagram, chart, graph, etc.)
- **Генерация текстового описания** картинки (VLM - Vision Language Model)
- Сохранение картинок как отдельных файлов
- Поддержка page images (скриншоты страниц)

**Модели VLM**:
- `smolvlm` - быстрая и легковесная
- `granitedocling` - специализированная для документов
- `granite_vision` - универсальная
- `smoldocling` / `smoldocling_mlx` - оптимизированные версии

**Источник**: `docker/docling-mcp/README.md:147-149`, `docker/docling-mcp/app/tg_docling/converter.py:399-479`

#### 4. **OCR для изображений и сканированных PDF**

```yaml
ocr_config:
  backend: rapidocr  # rapidocr, easyocr, tesseract, onnxtr
  force_full_page_ocr: false
  languages:
    - eng
    - rus
```

**Возможности**:
- Распознавание текста в картинках
- Full-page OCR для сканированных документов
- Поддержка 100+ языков (зависит от backend)
- GPU-ускорение

**Источник**: `docker/docling-mcp/README.md:156-176`, `docker/docling-mcp/app/tg_docling/converter.py:129-245`

#### 5. **Формулы и код**

```yaml
pipeline:
  code_enrichment: false      # LaTeX формулы
  formula_enrichment: false   # Математические формулы
```

**Возможности**:
- Распознавание LaTeX формул
- Извлечение блоков кода
- Сохранение в правильном markdown формате

**Источник**: `docker/docling-mcp/README.md:146-147`, `docker/docling-mcp/app/tg_docling/converter.py:394-395`

#### 6. **Экспорт в различные форматы**

```python
# Доступные методы экспорта
document.export_to_markdown()  # Markdown (рекомендуемый)
document.export_to_json()      # JSON (полная структура)
document.export_to_text()      # Plain text
document.export_to_html()      # HTML (через markdown)
```

**Особенности markdown экспорта**:
- Сохраняет структуру документа
- Таблицы конвертируются в markdown tables
- Формулы в LaTeX блоки
- **Картинки сохраняются с base64 encoding или как ссылки**

**Источник**: `src/processor/file_processor.py:655-701`, `docker/docling-mcp/app/tg_docling/tools.py:318-338`

### Что КРИТИЧЕСКИ важно для нас

✅ **Docling УЖЕ умеет**:
1. Извлекать все картинки из PDF
2. Распознавать таблицы и их структуру
3. Распознавать графики/диаграммы (через picture_classifier)
4. Генерировать текстовые описания для картинок (VLM)
5. Экспортировать в markdown с сохранением структуры

❌ **Что Docling НЕ делает автоматически**:
1. Не сохраняет извлеченные картинки как отдельные файлы в KB
2. Не генерирует уникальные имена для картинок
3. Не обновляет ссылки в markdown на локальные пути

---

## Как передавать PDF в Docling

### Текущая реализация (для любых файлов)

#### 1. **MCP Backend (Docker, рекомендуемый)**

**Инструмент**: `convert_document_from_content`

```python
# FileProcessor._process_with_mcp()
file_bytes = file_path.read_bytes()
base64_content = base64.b64encode(file_bytes).decode("utf-8")

result = await client.call_tool(
    "convert_document_from_content",
    {
        "content": base64_content,           # Base64 PDF
        "filename": file_path.name,          # Имя файла
        "mime_type": "application/pdf",      # MIME тип
        "export_format": "markdown"          # Формат экспорта
    }
)
```

**Преимущества**:
- ✅ Не требует shared filesystem между контейнерами
- ✅ Поддерживает любые размеры файлов (до max_file_size_mb)
- ✅ Кэширование результатов (document_key)
- ✅ Автоматический экспорт в нужный формат

**Недостатки**:
- ❌ Base64 увеличивает размер на ~33%
- ❌ Дополнительный network overhead

**Источник**: `src/processor/file_processor.py:192-251`, `docker/docling-mcp/app/tg_docling/tools.py:246-452`

#### 2. **Local Backend (альтернатива)**

```python
# FileProcessor._process_with_local()
converter = DocumentConverter()
result = converter.convert(str(file_path))
document = result.document
```

**Преимущества**:
- ✅ Прямая работа с файлами
- ✅ Нет network overhead

**Недостатки**:
- ❌ Требует установки docling в bot контейнер
- ❌ Нет кэширования
- ❌ Сложнее управлять зависимостями

**Источник**: `src/processor/file_processor.py:703-753`

### Оптимальный способ для PDF

**Рекомендация**: Использовать **MCP Backend** с base64 transfer

**Почему**:
1. Уже реализовано и протестировано
2. Поддерживает все форматы (PDF, DOCX, images)
3. Автоматическое кэширование
4. Изоляция Docling в отдельный контейнер
5. Легко масштабировать (можно добавить несколько Docling серверов)

**Конфигурация**:
```yaml
MEDIA_PROCESSING_DOCLING:
  backend: mcp
  max_file_size_mb: 50  # Для больших PDF
  mcp:
    tool_name: convert_document_from_content
    auto_detect_tool: true
```

### Chunking (разбивка на куски)

**Вопрос**: Нужно ли передавать PDF по кускам?

**Ответ**: **НЕТ, не нужно**

**Причины**:
1. Docling обрабатывает PDF как единое целое (layout analysis требует полного документа)
2. Передача по кускам усложнит извлечение картинок (они могут быть на разных страницах)
3. Таблицы могут пересекать границы чанков
4. Текущая реализация поддерживает файлы до `max_file_size_mb` (default: 25MB, можно увеличить)

**Когда chunking может понадобиться**:
- Очень большие PDF (>100MB)
- Память Docling контейнера ограничена
- Нужно обрабатывать конкретные страницы

**Альтернатива**: Увеличить `max_file_size_mb` и `shm_size` в docker-compose

**Источник**: `src/processor/file_processor.py:803-811`, `docker-compose.yml` (shm_size параметр)

---

## Как получать результат от Docling

### Структура результата

#### 1. **Через MCP (convert_document_from_content)**

```python
{
    "from_cache": false,                    # Кэширован ли результат
    "document_key": "bytes:sha256:...",     # Ключ для кэша
    "markdown": "# Title\n\n...",           # Markdown экспорт (если запрошен)
    "export_format": "markdown",            # Формат экспорта
}
```

**Если markdown не запрошен сразу, можно экспортировать позже**:
```python
result = await client.call_tool(
    "export_docling_document_to_markdown",
    {"document_key": document_key}
)
```

**Источник**: `docker/docling-mcp/app/tg_docling/tools.py:290-351`, `src/processor/file_processor.py:416-496`

#### 2. **Структура Docling Document**

```python
# docling_core.types.doc.document.Document
document = result.document

# Основные свойства
document.name              # Название документа
document.origin            # Источник (file path/URI)

# Экспорт
document.export_to_markdown()  # → str
document.export_to_json()      # → str (JSON)
document.export_to_text()      # → str

# Внутренняя структура (для продвинутой работы)
document.main_text         # Все текстовые элементы
document.tables            # Все таблицы
document.pictures          # Все картинки
document.pages             # Постраничная разбивка
```

**Источник**: `docling_core` package, используется в `src/processor/file_processor.py:655-701`

### Что содержит markdown результат

```markdown
# Document Title

## Introduction

Regular paragraph text.

### Table Example

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |

### Image Example

![Figure 1: Diagram](data:image/png;base64,iVBORw0KGgoAAAANS...)

### Formula Example

$$
E = mc^2
$$
```

**ВАЖНО**: Картинки в markdown по умолчанию встраиваются как **base64 data URIs**

**Источник**: Наблюдение из кода экспорта в `docker/docling-mcp/app/tg_docling/tools.py:318-338`

### Извлечение отдельных элементов

#### Вариант 1: Использовать JSON экспорт

```python
# Получить JSON с полной структурой
json_result = document.export_to_json()
data = json.loads(json_result)

# Структура JSON
{
    "name": "document.pdf",
    "main-text": [...],
    "tables": [
        {
            "data": [[...], [...]],  # Строки и ячейки
            "num_rows": 5,
            "num_cols": 3,
            ...
        }
    ],
    "pictures": [
        {
            "prov": [...],           # Позиция на странице
            "image": "base64...",    # Картинка в base64
            "caption": "Figure 1",   # Подпись
            ...
        }
    ],
    ...
}
```

**Источник**: `docling_core` JSON schema

#### Вариант 2: Использовать Docling API напрямую

```python
# Если используем local backend
result = converter.convert(pdf_path)
document = result.document

# Перебрать все картинки
for page in document.pages:
    for picture in page.pictures:
        # picture.image - PIL Image или base64
        # picture.bbox - координаты на странице
        # picture.caption - подпись
        pass

# Перебрать все таблицы
for table in document.tables:
    # table.data - 2D массив ячеек
    # table.export_to_markdown() - markdown таблица
    pass
```

**Источник**: `docling` package API (используется если backend='local')

#### Вариант 3: MCP Tools для извлечения (текущая реализация)

```python
# Конвертировать документ
result = await client.call_tool("convert_document_from_content", {...})
document_key = result["document_key"]

# Экспортировать в markdown
markdown = await client.call_tool(
    "export_docling_document_to_markdown",
    {"document_key": document_key}
)

# Экспортировать в JSON
json_result = await client.call_tool(
    "export_docling_document_to_json",
    {"document_key": document_key}
)
```

**Источник**: `src/processor/file_processor.py:416-496`

### Picture Description (VLM)

Если включено `pipeline.picture_description`:

```yaml
pipeline:
  picture_description:
    enabled: true
    model: smolvlm
    prompt: "Describe this image in detail"
```

**Результат**: Каждая картинка будет иметь текстовое описание

```json
{
    "pictures": [
        {
            "image": "base64...",
            "description": "A bar chart showing revenue trends from 2020 to 2023...",
            "caption": "Figure 1",
            ...
        }
    ]
}
```

**Источник**: `docker/docling-mcp/app/tg_docling/converter.py:399-479`

---

## Как передавать результат агенту

### Текущая реализация (для изображений)

#### 1. **Сохранение изображения в KB**

```python
# FileProcessor.download_and_process_telegram_file()

# Генерация уникального имени
timestamp = message_date or int(time.time())
file_suffix = f"_{file_id[:8]}" if file_id else ""
unique_filename = f"img_{timestamp}{file_suffix}{extension}"

# Сохранение в KB
save_path = kb_images_dir / unique_filename
with open(save_path, "wb") as f:
    f.write(downloaded_file)

# Добавление в result
result["saved_path"] = str(save_path)
result["saved_filename"] = unique_filename
```

**Источник**: `src/processor/file_processor.py:945-992`

#### 2. **Передача агенту через ContentParser**

```python
# ContentParser.parse_group_with_files()

# Для каждого файла
file_result = await processor.download_and_process_telegram_file(...)

# Добавить в контент
if file_result and "saved_path" in file_result:
    content_parts.append(
        f"\n\n[Image saved to KB: {file_result['saved_filename']}]\n"
        f"Path: {file_result['saved_path']}\n"
        f"OCR Text: {file_result['text']}\n"
    )
```

**Источник**: `src/processor/content_parser.py` (метод `parse_group_with_files`)

#### 3. **Агент использует путь в markdown**

```markdown
# Agent Output

![Screenshot description](../images/img_1705334567_abcd1234.jpg)

## Analysis

The image shows...
```

**Источник**: Промпты агента в `config/prompts/`, особенно `config/agent_prompts.py`

### Предложенная реализация для PDF

#### Шаг 1: Расширить FileProcessor для PDF

```python
async def extract_pdf_resources(
    self,
    pdf_result: Dict[str, Any],
    kb_images_dir: Path,
    kb_tables_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Извлечь картинки и таблицы из PDF результата Docling.
    
    Returns:
        {
            "images": [
                {
                    "saved_path": "images/pdf_p1_fig1_timestamp.png",
                    "description": "Bar chart showing...",
                    "caption": "Figure 1",
                    "page": 1
                }
            ],
            "tables": [
                {
                    "markdown": "| Header | ... |",
                    "saved_path": "tables/pdf_table1_timestamp.md",  # Optional
                    "caption": "Table 1",
                    "page": 2
                }
            ],
            "text": "Full document text..."
        }
    """
```

**Логика**:
1. Получить JSON экспорт через `export_docling_document_to_json`
2. Извлечь все `pictures` из JSON
3. Декодировать base64 → сохранить в `kb_images_dir`
4. Генерировать уникальные имена: `pdf_p{page}_fig{index}_{timestamp}.{ext}`
5. Сохранить описания VLM (если есть)
6. Извлечь все `tables` → экспортировать в markdown
7. Опционально сохранить таблицы как отдельные `.md` файлы

**Пример имен**:
```
images/pdf_p1_fig1_1705334567.png
images/pdf_p3_chart2_1705334567.jpg
tables/pdf_table1_1705334567.md
```

#### Шаг 2: Обогатить результат для агента

```python
# После извлечения ресурсов
enriched_result = {
    "text": markdown_text,
    "metadata": {
        "source": "document.pdf",
        "pages": 15,
        "images_extracted": 5,
        "tables_extracted": 3,
    },
    "images": [
        {
            "path": "images/pdf_p1_fig1_1705334567.png",
            "description": "A bar chart showing revenue trends...",
            "page": 1,
            "type": "chart"
        }
    ],
    "tables": [
        {
            "markdown": "| Year | Revenue |\n|------|--------|\n...",
            "page": 2
        }
    ]
}
```

#### Шаг 3: Расширить промпт агента

```markdown
# System Prompt Extension

When processing PDF documents:

1. **Images**: All extracted images are saved to `images/` directory with names like:
   - `pdf_p{page}_fig{index}_{timestamp}.{ext}`
   - Example: `images/pdf_p1_fig1_1705334567.png`

2. **Image References**: Always use relative paths in markdown:
   - From root: `![description](images/pdf_p1_fig1_xxx.png)`
   - From topics/: `![description](../images/pdf_p1_fig1_xxx.png)`

3. **VLM Descriptions**: When image has a description from VLM:
   - Use it as alt text: `![Bar chart showing revenue trends](images/...)`
   - Optionally add full description in text

4. **Tables**: Insert tables from PDF directly into markdown:
   ```markdown
   ## Financial Data (from PDF page 2)
   
   | Year | Revenue | Profit |
   |------|---------|--------|
   | 2020 | $100M   | $20M   |
   ```

5. **Charts/Graphs**: Reference them with context:
   ```markdown
   As shown in Figure 1 below, revenue increased by 25% in 2023:
   
   ![Revenue trends 2020-2023](images/pdf_p5_chart1_xxx.png)
   ```
```

**Источник**: Расширение `config/agent_prompts.py` и `config/prompts/*.md`

---

## Как хранить PDF и распознанные версии

### Текущая структура KB

```
knowledge_bases/my-notes/
├── index.md
├── README.md
├── images/                          # Картинки из Telegram
│   ├── img_1705334567_abcd1234.jpg
│   └── img_1705334580_efgh5678.png
└── topics/
    ├── notes.md
    └── research.md
```

**Источник**: `docs_site/user-guide/file-format-recognition.md:550-562`

### Предложенная структура для PDF

```
knowledge_bases/my-notes/
├── index.md
├── README.md
├── images/                          # ВСЕ картинки (Telegram + PDF)
│   ├── img_1705334567_abcd1234.jpg # Telegram фото
│   ├── pdf_p1_fig1_1705334567.png  # Картинка из PDF стр. 1
│   ├── pdf_p3_chart2_1705334567.jpg # График из PDF стр. 3
│   └── ...
├── pdfs/                            # ОПЦИОНАЛЬНО: Исходные PDF
│   ├── arxiv_2023_transformer.pdf
│   ├── research_paper_2024.pdf
│   └── ...
├── processed/                       # РЕКОМЕНДУЕТСЯ: Распознанные версии
│   ├── arxiv_2023_transformer.md    # Markdown из Docling
│   ├── arxiv_2023_transformer.json  # JSON структура
│   └── ...
└── topics/
    ├── ml-papers.md                 # Ссылается на images/ и processed/
    └── research-notes.md
```

### Варианты хранения PDF

#### Вариант 1: Не хранить исходные PDF (рекомендуемый)

**Плюсы**:
- ✅ Экономия места в git repository
- ✅ KB остается текстовым (лучше для git diff)
- ✅ Все нужное уже извлечено (текст, картинки, таблицы)

**Минусы**:
- ❌ Нельзя пересмотреть оригинальный PDF
- ❌ Потеря мета-информации (аннотации, подсветки)

**Реализация**:
```python
# В FileProcessor
# НЕ сохранять PDF в KB, только обрабатывать
temp_pdf = download_to_temp()
result = process_pdf(temp_pdf)
extract_resources(result, kb_dirs)
temp_pdf.unlink()  # Удалить временный файл
```

#### Вариант 2: Хранить PDF в отдельной папке

**Плюсы**:
- ✅ Доступ к оригиналу
- ✅ Можно переобработать с другими настройками

**Минусы**:
- ❌ Размер git repository (PDF - бинарные файлы)
- ❌ Git LFS может потребоваться

**Реализация**:
```python
# Сохранить PDF в KB
kb_pdfs_dir = kb_root / "pdfs"
kb_pdfs_dir.mkdir(parents=True, exist_ok=True)

pdf_filename = f"pdf_{timestamp}_{sanitized_name}.pdf"
pdf_path = kb_pdfs_dir / pdf_filename

with open(pdf_path, "wb") as f:
    f.write(pdf_bytes)
```

**Gitignore** (опционально):
```gitignore
# .gitignore в KB root
pdfs/
```

#### Вариант 3: Ссылка на внешний источник

**Плюсы**:
- ✅ Нет размера в git
- ✅ Оригинал доступен по ссылке

**Минусы**:
- ❌ Ссылка может сломаться
- ❌ Нужен интернет для доступа

**Реализация**:
```markdown
# В generated markdown
Source: [ArXiv Paper](https://arxiv.org/pdf/2301.xxxxx.pdf)

## Abstract

...

## Figures

![Figure 1](../images/pdf_p1_fig1_xxx.png)
```

### Хранение распознанной версии

#### Вариант A: Только markdown (простой)

```python
# После обработки PDF
processed_dir = kb_root / "processed"
processed_dir.mkdir(parents=True, exist_ok=True)

markdown_path = processed_dir / f"{pdf_name}_{timestamp}.md"
markdown_path.write_text(docling_markdown)
```

**Структура markdown**:
```markdown
# Document Title

Source: document.pdf
Processed: 2025-11-13 15:30:00

## Section 1

Text content...

![Figure 1](../images/pdf_p1_fig1_xxx.png)

### Table 1

| Header | ... |
|--------|-----|
| Cell   | ... |
```

#### Вариант B: Markdown + JSON (полный)

```python
# Сохранить оба формата
markdown_path.write_text(docling_markdown)
json_path = processed_dir / f"{pdf_name}_{timestamp}.json"
json_path.write_text(docling_json)
```

**JSON содержит**:
- Полную структуру документа
- Метаданные (автор, дата, и т.д.)
- Координаты всех элементов на страницах
- Сырые данные таблиц

**Польза**:
- Можно пересобрать markdown с другими параметрами
- Легче парсить программно
- Полная информация для ML обработки

#### Вариант C: Только ссылки (минималистичный)

```markdown
# В topics/ml-papers.md

## ArXiv Paper 2023: Transformers

**Processed**: 2025-11-13

### Key Figures

![Architecture Diagram](../images/pdf_p3_fig2_xxx.png)

### Main Ideas

...
```

**Не создавать** `processed/` папку, агент сразу пишет в `topics/`

### Рекомендация

**Для MVP**:
1. ❌ **НЕ хранить** исходные PDF в KB (только в temp)
2. ✅ **Хранить** извлеченные картинки в `images/`
3. ✅ **Хранить** markdown версию в `processed/`
4. ⚠️ **Опционально** хранить JSON для продвинутых случаев

**Для production**:
1. Добавить настройку `KEEP_PROCESSED_PDFS: bool`
2. Если `true` → сохранять в `pdfs/` + добавить в `.gitignore`
3. Добавить настройку `SAVE_DOCLING_JSON: bool`
4. Реализовать переобработку старых PDF с новыми настройками

### Дубликаты PDF (как для картинок)

```python
# FileProcessor._find_existing_pdf_by_hash()
def _find_existing_pdf_by_hash(
    self, file_hash: str, processed_dir: Path
) -> Optional[Path]:
    """Check if PDF already processed (by hash)."""
    for existing_file in processed_dir.glob("pdf_*_*.md"):
        # Проверить hash в метаданных или filename
        if hash_matches(existing_file, file_hash):
            return existing_file
    return None
```

**Источник**: Аналогично `src/processor/file_processor.py:833-862` (для картинок)

---

## План реализации

### Phase 1: Базовая поддержка PDF (MVP)

**Цель**: PDF обрабатываются как документы, текст извлекается

**Задачи**:
1. ✅ **Уже работает**: `FileProcessor.process_file()` поддерживает PDF
2. ✅ **Уже работает**: Markdown экспорт через MCP
3. ⚠️ **Нужно проверить**: Качество извлечения текста из arxiv PDF
4. ⚠️ **Нужно настроить**: Pipeline для научных статей

**Конфигурация**:
```yaml
MEDIA_PROCESSING_DOCLING:
  formats:
    - pdf  # Уже есть
  pipeline:
    layout:
      enabled: true
      preset: layout_v2  # Или layout_heron для научных статей
    table_structure:
      enabled: true
      mode: accurate
```

**Тестирование**:
```python
# Скачать PDF с arxiv
# Отправить боту в Telegram
# Проверить качество извлеченного текста
```

### Phase 2: Извлечение картинок из PDF

**Цель**: Картинки из PDF сохраняются в `images/` и доступны агенту

**Задачи**:

#### 2.1. Включить picture pipeline в Docling
```yaml
pipeline:
  picture_classifier: true
  picture_description:
    enabled: true
    model: smolvlm  # Или granitedocling для документов
```

#### 2.2. Расширить FileProcessor
```python
# Новый метод
async def extract_pdf_images(
    self,
    document_key: str,
    kb_images_dir: Path,
    pdf_filename: str,
    timestamp: int
) -> List[Dict[str, Any]]:
    """
    Извлечь картинки из обработанного PDF.
    
    Returns:
        [
            {
                "saved_path": Path,
                "filename": "pdf_p1_fig1_xxx.png",
                "description": "VLM description",
                "page": 1,
                "index": 1
            }
        ]
    """
    # 1. Получить JSON через export_docling_document_to_json
    json_result = await self._docling_client.call_tool(
        "export_docling_document_to_json",
        {"document_key": document_key}
    )
    
    # 2. Парсить JSON → извлечь pictures[]
    doc_data = json.loads(json_result["structured_content"]["json"])
    
    # 3. Для каждой картинки:
    for idx, picture in enumerate(doc_data.get("pictures", [])):
        # Декодировать base64
        image_data = base64.b64decode(picture["image"])
        
        # Генерировать имя
        page = picture.get("page", 0)
        filename = f"pdf_p{page}_fig{idx+1}_{timestamp}.png"
        
        # Сохранить
        save_path = kb_images_dir / filename
        save_path.write_bytes(image_data)
        
        # Добавить в результат
        images.append({
            "saved_path": save_path,
            "filename": filename,
            "description": picture.get("description"),
            "page": page,
            "index": idx + 1
        })
    
    return images
```

#### 2.3. Интеграция в download_and_process_telegram_file
```python
# В FileProcessor.download_and_process_telegram_file()

# После обработки PDF
if file_format == "pdf" and kb_images_dir:
    # Извлечь картинки
    pdf_images = await self.extract_pdf_images(
        document_key=result.get("document_key"),
        kb_images_dir=kb_images_dir,
        pdf_filename=original_filename,
        timestamp=message_date
    )
    
    # Добавить в result
    result["pdf_images"] = pdf_images
```

#### 2.4. Обогатить ContentParser
```python
# В ContentParser.parse_group_with_files()

if "pdf_images" in file_result:
    content_parts.append("\n\n[PDF Images extracted]:\n")
    for img in file_result["pdf_images"]:
        content_parts.append(
            f"- {img['filename']} (page {img['page']}): {img['description']}\n"
        )
```

#### 2.5. Расширить промпт агента
```markdown
# В config/prompts/qwen_cli_system_prompt.md

## PDF Image References

When processing PDFs with extracted images:
- Images are saved to `images/` with pattern: `pdf_p{page}_fig{index}_{timestamp}.{ext}`
- Use relative paths: `![description](images/pdf_p1_fig1_xxx.png)`
- Include VLM descriptions in alt text
```

**Тестирование**:
1. PDF с картинками/графиками
2. Проверить что картинки сохранились в `images/`
3. Проверить что агент правильно вставил ссылки в markdown

### Phase 3: Извлечение таблиц из PDF

**Цель**: Таблицы из PDF правильно экспортируются в markdown

**Задачи**:

#### 3.1. Включить table structure pipeline
```yaml
pipeline:
  table_structure:
    enabled: true
    mode: accurate
    do_cell_matching: true
```

#### 3.2. Проверить качество экспорта таблиц
```python
# Docling уже экспортирует таблицы в markdown
# Нужно проверить что:
# - Сложные таблицы (merged cells) правильно обрабатываются
# - Формат markdown table корректный
# - Агент правильно вставляет таблицы
```

#### 3.3. Опционально: Извлечь таблицы отдельно
```python
# Если нужно сохранять таблицы как отдельные файлы
async def extract_pdf_tables(
    self,
    document_key: str,
    kb_tables_dir: Path,
    timestamp: int
) -> List[Dict[str, Any]]:
    """Извлечь таблицы из PDF."""
    # Аналогично extract_pdf_images()
    # Сохранять в kb_tables_dir/pdf_table{idx}_{timestamp}.md
```

**Тестирование**:
1. PDF с таблицами (финансовые отчеты, научные данные)
2. Проверить качество распознавания
3. Проверить markdown форматирование

### Phase 4: VLM Descriptions (опционально)

**Цель**: Картинки из PDF имеют автоматические описания

**Задачи**:

#### 4.1. Настроить VLM модель
```yaml
pipeline:
  picture_description:
    enabled: true
    model: granitedocling  # Специально для документов
    prompt: |
      Describe this figure from a scientific paper.
      Focus on:
      - Type of visualization (chart, diagram, photo, etc.)
      - Key data or information shown
      - Main insights or trends
```

#### 4.2. Скачать модель
```yaml
model_cache:
  builtin_models:
    granitedocling: true  # Или smolvlm
```

#### 4.3. Проверить работу
```python
# После обработки PDF с VLM
# Проверить что descriptions есть в результате
# Проверить качество описаний
```

**Тестирование**:
1. PDF с графиками
2. Проверить описания от VLM
3. Настроить prompt для лучших результатов

### Phase 5: Хранение processed версий (опционально)

**Цель**: Markdown версии PDF сохраняются в KB

**Задачи**:

#### 5.1. Создать папку processed
```python
# В FileProcessor
processed_dir = kb_root / "processed"
processed_dir.mkdir(parents=True, exist_ok=True)
```

#### 5.2. Сохранить markdown
```python
# После обработки PDF
markdown_path = processed_dir / f"{sanitized_name}_{timestamp}.md"

# Обогатить markdown метаданными
enriched_markdown = f"""---
source: {original_filename}
processed: {datetime.now().isoformat()}
pages: {num_pages}
images_extracted: {len(pdf_images)}
---

{docling_markdown}
"""

markdown_path.write_text(enriched_markdown)
```

#### 5.3. Опционально: JSON
```python
if settings.SAVE_DOCLING_JSON:
    json_path = processed_dir / f"{sanitized_name}_{timestamp}.json"
    json_path.write_text(docling_json)
```

**Тестирование**:
1. Обработать PDF
2. Проверить что файл в `processed/`
3. Проверить метаданные

### Phase 6: Настройки и оптимизация

**Задачи**:

#### 6.1. Добавить настройки
```yaml
PDF_PROCESSING:
  extract_images: true
  extract_tables: true
  use_vlm_descriptions: false  # Ресурсоемко
  save_processed_markdown: true
  save_docling_json: false
  keep_original_pdf: false
  
  naming:
    image_pattern: "pdf_p{page}_fig{index}_{timestamp}.{ext}"
    table_pattern: "pdf_table{index}_{timestamp}.md"
```

#### 6.2. Оптимизация памяти
```python
# Для больших PDF
# - Обрабатывать постранично
# - Сохранять картинки по мере извлечения
# - Очищать кэш после обработки
```

#### 6.3. Обработка ошибок
```python
# Graceful degradation
try:
    pdf_images = await self.extract_pdf_images(...)
except Exception as e:
    logger.warning(f"Failed to extract images from PDF: {e}")
    pdf_images = []
    # Продолжить с текстом
```

### Итоговая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      Telegram Bot                            │
└───────────────────────┬─────────────────────────────────────┘
                        │ PDF file
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    FileProcessor                             │
│  1. Download PDF to temp                                     │
│  2. Send to Docling MCP (base64)                            │
│  3. Receive markdown + document_key                         │
│  4. Extract images → save to images/                        │
│  5. Extract tables → include in markdown                    │
│  6. Save processed markdown to processed/                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   ContentParser                              │
│  Merge:                                                      │
│  - Full text from markdown                                   │
│  - List of extracted images with descriptions               │
│  - Metadata (pages, tables count, etc.)                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     AI Agent (Qwen)                          │
│  Receives:                                                   │
│  - PDF text content                                          │
│  - Image paths in images/                                    │
│  - Image descriptions (VLM)                                  │
│  - Table data                                                │
│                                                               │
│  Generates:                                                  │
│  - topics/paper-notes.md                                     │
│    - With proper image references                            │
│    - With tables                                             │
│    - With structured content                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Итоговые ответы на вопросы

### 1. Что умеет Docling?

✅ **Docling умеет**:
- Layout analysis (структура документа)
- Table extraction (таблицы с full structure)
- Picture extraction (все картинки из PDF)
- Picture classification (тип картинки: chart, diagram, photo)
- VLM descriptions (текстовые описания картинок)
- OCR (текст в картинках и сканах)
- Formula extraction (LaTeX формулы)
- Export to markdown/JSON/text

**Документация**: https://github.com/DS4SD/docling

### 2. Как передавать PDF в Docling?

✅ **Рекомендуемый способ**: Base64 через MCP

```python
base64_content = base64.b64encode(pdf_bytes).decode("utf-8")
result = await client.call_tool(
    "convert_document_from_content",
    {
        "content": base64_content,
        "filename": "paper.pdf",
        "export_format": "markdown"
    }
)
```

❌ **Chunking НЕ нужен**: Docling обрабатывает PDF целиком

⚠️ **Ограничение**: `max_file_size_mb` (default 25MB, настраивается)

### 3. Как получать результат от Docling?

✅ **Markdown export** (простой):
```python
markdown = result["markdown"]
```

✅ **JSON export** (полный):
```python
json_result = await client.call_tool(
    "export_docling_document_to_json",
    {"document_key": document_key}
)
# Содержит: pictures[], tables[], main-text[], metadata
```

✅ **Структура**:
- `pictures[]` - массив картинок с base64, описаниями, координатами
- `tables[]` - массив таблиц с данными, markdown экспортом
- `main-text[]` - текстовые элементы

### 4. Как передавать результат агенту?

✅ **Текущая схема** (расширить для PDF):

1. Извлечь картинки → сохранить в `images/pdf_p{page}_fig{index}_{timestamp}.{ext}`
2. Создать обогащенный контент:
   ```
   [PDF processed: paper.pdf]
   
   Full text: ...
   
   [Images extracted]:
   - images/pdf_p1_fig1_xxx.png (page 1): "Bar chart showing..."
   - images/pdf_p3_fig2_xxx.png (page 3): "Architecture diagram..."
   
   [Tables extracted]: 3 tables
   ```
3. Агент получает текст + список картинок
4. Агент генерирует markdown с правильными ссылками

✅ **Промпт для агента**:
```markdown
When processing PDFs:
- Use relative paths: `![description](images/pdf_p1_fig1_xxx.png)`
- Include VLM descriptions in alt text
- Insert tables directly in markdown
```

### 5. Как хранить PDF и распознанные версии?

✅ **Рекомендуемая структура**:
```
knowledge_bases/my-notes/
├── images/
│   ├── img_*           # Telegram photos
│   └── pdf_p*_fig*     # PDF images
├── processed/          # Processed PDFs
│   ├── paper_xxx.md
│   └── paper_xxx.json  # Optional
└── topics/
    └── ml-papers.md    # References images + processed
```

❌ **НЕ хранить** исходные PDF в git (только в temp)

✅ **Хранить**:
- Извлеченные картинки в `images/`
- Markdown версию в `processed/`
- JSON (опционально) для продвинутых случаев

⚠️ **Опционально**: Настройка `KEEP_PROCESSED_PDFS` для сохранения оригиналов в `pdfs/` (+ `.gitignore`)

---

## Заключение

**Docling ПОЛНОСТЬЮ поддерживает** нужный функционал для работы с PDF:
- ✅ Извлечение картинок
- ✅ Извлечение таблиц
- ✅ Распознавание графиков
- ✅ VLM описания
- ✅ OCR для сканов

**Текущая реализация** уже поддерживает базовую обработку PDF.

**Требуется**:
1. Включить pipeline картинок/таблиц в конфиге
2. Реализовать `extract_pdf_images()` в FileProcessor
3. Обогатить промпт агента для PDF
4. Настроить хранение в KB

**Оценка трудозатрат**:
- Phase 1 (базовый PDF): ✅ Уже работает
- Phase 2 (картинки): ~4-6 часов
- Phase 3 (таблицы): ~2-3 часа
- Phase 4 (VLM): ~2-3 часа (настройка)
- Phase 5 (хранение): ~2-3 часа
- Phase 6 (оптимизация): ~3-4 часа

**Итого**: ~13-19 часов для полной реализации
