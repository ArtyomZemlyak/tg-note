# Image Prompt Format

How images are now presented to the agent in the prompt.

---

## New Format (Simplified)

### Before (Old, Verbose)

```
Пользователь: Вот диаграммы архитектуры

--- Изображение: image.jpg (сохранено как: ../media/img_1234567890_abc12345_coconut_chain.jpg) ---
Описание: Diagram showing three main components: Frontend (React), API (FastAPI), and Database (PostgreSQL). The frontend communicates with the API via REST endpoints. The API connects to the database using SQLAlchemy ORM. There's also a Redis cache layer between the API and database for performance optimization. The architecture follows microservices pattern with...
Полное описание доступно в: ../media/img_1234567890_abc12345_coconut_chain.md

--- Изображение: image2.jpg (сохранено как: ../media/img_1234567891_def67890_kubernetes.jpg) ---
Описание: Deployment diagram showing Kubernetes cluster with three environments: development, staging, and production. Each environment has separate namespaces. The production namespace contains 5 replicas of the API service, 3 replicas of the worker service, and...
Полное описание доступно в: ../media/img_1234567891_def67890_kubernetes.md
```

**Problems:**
- Very long prompt (hundreds of chars per image)
- Duplicate descriptions (in OCR + in summary)
- Agent might not read .md files

### After (New, Clean)

```
Пользователь: Вот диаграммы архитектуры

Медиафайлы:
лежат в media/
img_1234567890_abc12345_coconut_chain.jpg
img_1234567891_def67890_kubernetes.jpg
```

**Benefits:**
- Minimal prompt size (just filenames!)
- Agent MUST read .md files to understand images
- No duplicates in prompt
- Clean and simple

---

## How Agent Uses Images

### Step 1: See Media List

Agent receives:
```
Медиафайлы:
лежат в media/
img_1234567890_abc12345_coconut_chain.jpg
img_1234567891_def67890_kubernetes.jpg
```

### Step 2: Read Metadata Files

Agent can read descriptions:

```python
# Read first image description
read_file("KB/media/img_1234567890_abc12345_coconut_chain.md")
```

Returns:
```markdown
# Image Description

**File:** img_1234567890_abc12345_coconut_chain.jpg
**Original:** system_architecture.png
**Received:** 1234567890

## Extracted Text (OCR)

Frontend (React)
↓
API Gateway
↓
Microservices:
- Auth Service
- User Service
- Payment Service
↓
PostgreSQL Database
...

## Usage Instructions

When referencing this image in markdown:
1. Use relative path based on file location
2. Add descriptive alt text based on OCR content above
3. Add text description BELOW the image for GitHub rendering

Example:
```markdown
![System architecture diagram](../media/img_1234567890_abc12345_coconut_chain.jpg)

**Описание:** Diagram shows microservices architecture with...
```

### Step 3: Insert in Markdown

Agent creates note:

```markdown
# System Architecture - 2024-01-15

Our new architecture consists of three main layers.

![Microservices architecture with API Gateway and multiple services](../media/img_1234567890_abc12345_coconut_chain.jpg)

**Описание:** The diagram illustrates a microservices architecture where:
- Frontend communicates through API Gateway
- Three core services: Auth, User, and Payment
- PostgreSQL handles persistent storage
- Redis provides caching layer

## Deployment Strategy

The deployment uses Kubernetes for orchestration.

![Kubernetes deployment diagram with three environments](../media/img_1234567891_def67890_kubernetes.jpg)

**Описание:** Deployment structure showing:
- Separate namespaces for dev/staging/prod
- Production runs 5 API replicas
- Automatic scaling based on CPU usage
```

---

## Prompt Size Comparison

### Example: 3 images with OCR text

**Old format:**
```
Image 1: 500 chars description
Image 2: 450 chars description  
Image 3: 600 chars description
Total: ~1550 chars
```

**New format:**
```
Медиафайлы:
лежат в media/
img_001.jpg
img_002.jpg
img_003.jpg
Total: ~60 chars
```

**Savings: 96% reduction in prompt size!**

---

## Agent Instructions

From `template.ru.v2.md`:

```markdown
## Формат списка изображений

Если во "Входящей информации" есть раздел "Медиафайлы:",
значит к сообщению прикреплены изображения:

Медиафайлы:
лежат в media/
img_1234567890_abc12345_coconut_chain.jpg

**Что делать:**
1. Для каждого изображения (например, `img_123_slug.jpg`)
   существует файл описания `img_123_slug.md` в той же папке `media/`
2. Ты можешь прочитать этот файл чтобы узнать что на изображении
   (там есть OCR текст)
3. Используй изображения в создаваемых markdown файлах
```

---

## Implementation Details

### ContentParser Changes

```python
# Old approach
for file_data in file_contents:
    if "saved_filename" in file_data:
        summary = ImageMetadata.get_image_description_summary(...)
        file_texts.append(f"Описание: {summary}\n...")

# New approach
image_filenames = []
for file_data in file_contents:
    if "saved_filename" in file_data:
        image_filenames.append(file_data["saved_filename"])

# Simple list output
if image_filenames:
    result["text"] += "\n\nМедиафайлы:\nлежат в media/\n"
    result["text"] += "\n".join(image_filenames)
```

### Duplicate Prevention

```python
seen_images = set()
for file_data in file_contents:
    saved_filename = file_data["saved_filename"]

    # Skip duplicates
    if saved_filename in seen_images:
        logger.info(f"Skipping duplicate: {saved_filename}")
        continue

    seen_images.add(saved_filename)
    image_filenames.append(saved_filename)
```

---

## Benefits Summary

| Aspect | Old | New | Improvement |
|--------|-----|-----|-------------|
| Prompt size | ~500 chars/image | ~20 chars/image | 96% smaller |
| Agent action | Passive (reads summary) | Active (must read .md) | Forces engagement |
| Duplicates | Possible in different descriptions | Prevented by `seen_images` | 100% prevented |
| GitHub rendering | Alt-text invisible | Text below image visible | Better UX |
| Maintenance | Descriptions in prompt | Descriptions in files | Easier to update |

---

## Migration Path

1. **No breaking changes**: Existing images without .md files still work
2. **Gradual adoption**: New images get .md files automatically
3. **Backward compatible**: Agent falls back to old format if .md missing

---

## Examples

### Single Image

**Prompt:**
```
Пользователь: Вот скриншот ошибки

Медиафайлы:
лежат в media/
img_1705334567_abc123.jpg
```

**Agent reads:** `../media/img_1705334567_abc123_error_traceback.md`

**Agent creates:**
```markdown
# Production Error - 2024-01-15

![Error traceback showing ConnectionTimeout](../media/img_1705334567_abc123_error_traceback.jpg)

**Описание:** Screenshot shows Redis connection timeout error in production...
```

### Multiple Images

**Prompt:**
```
Пользователь: Три диаграммы для документации

Медиафайлы:
лежат в media/
img_001_overview.jpg
img_002_data_flow.jpg
img_003_deployment.jpg
```

**Agent creates:**
```markdown
# Architecture Documentation

## Overview

![System overview diagram](../media/img_001_overview.jpg)

**Описание:** High-level view of the system...

## Data Flow

![Data flow between components](../media/img_002_data_flow.jpg)

**Описание:** Shows how data moves through the system...

## Deployment

![Kubernetes deployment structure](../media/img_003_deployment.jpg)

**Описание:** Production deployment configuration...
```

---

## See Also

- [Image Metadata System](image-metadata-system.md) - How .md and .json files work
- [Image Embedding](image-embedding.md) - Original image handling system
- [Qwen CLI Agent](../agents/qwen-code-cli.md) - Agent configuration
