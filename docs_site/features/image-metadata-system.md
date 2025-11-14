# Image Metadata System

System for managing image descriptions and preventing duplicates.

---

## Overview

The Image Metadata System solves several problems with image handling:

1. **Large prompts**: OCR text from images was included in full in agent prompts
2. **Duplicates**: Same images were inserted multiple times with different descriptions
3. **GitHub rendering**: Image descriptions in `[alt text]` are not visible in GitHub
4. **Confusion**: Agents sometimes mixed up which image was which

### Solution

For each saved image (e.g., `img_1234567890_abc12345.jpg`), the system creates two companion files:

- `img_1234567890_abc12345.md` - Human-readable description with OCR text
- `img_1234567890_abc12345.json` - Machine-readable settings and metadata

---

## How It Works

### 1. Image Saved to KB

When a Telegram image is processed:

```python
# In FileProcessor.download_and_process_telegram_file()
save_path = kb_images_dir / "img_1234567890_abc12345.jpg"
# Download and save image
# Process with Docling OCR

# Create metadata files
ImageMetadata.create_metadata_files(
    image_path=save_path,
    ocr_text=extracted_text,
    file_id=telegram_file_id,
    timestamp=message_timestamp,
    original_filename="user_image.jpg",
    file_hash=computed_hash
)
```

### 2. Metadata Files Created

**img_1234567890_abc12345.md:**
```markdown
# Image Description

**File:** img_1234567890_abc12345.jpg
**Original:** user_image.jpg
**Received:** 1234567890

## Extracted Text (OCR)

[Full OCR text here - can be very long]

## Usage Instructions

When referencing this image in markdown:
1. Use relative path based on file location
2. Add descriptive alt text based on OCR content above
3. Add text description BELOW the image for GitHub rendering
```

**img_1234567890_abc12345.json:**
```json
{
  "file_id": "abc12345",
  "timestamp": 1234567890,
  "original_filename": "user_image.jpg",
  "file_hash": "sha256_hash_here",
  "image_filename": "img_1234567890_abc12345.jpg",
  "ocr_extracted": true,
  "ocr_length": 1234
}
```

### 3. Prompt Generation

When ContentParser builds the prompt for the agent:

**Old approach (problem):**
```
--- Содержимое файла: image.jpg (сохранено как: ../images/img_123.jpg) ---
[10KB of OCR text here]
```

**New approach (solution):**
```
--- Изображение: image.jpg (сохранено как: ../images/img_123.jpg) ---
Описание: [Brief 500 char summary of OCR]
Полное описание доступно в: ../images/img_123.md
```

### 4. Duplicate Detection

ContentParser tracks used images:

```python
seen_images = set()
for file_data in file_contents:
    if saved_filename in seen_images:
        logger.info(f"Skipping duplicate image: {saved_filename}")
        continue
    seen_images.add(saved_filename)
```

---

## Agent Instructions

The agent receives updated instructions in `template.ru.v2.md`:

### 1. Add Descriptions Twice

**Problem:** GitHub doesn't render alt-text `[...]` in markdown images.

**Solution:** Add description both in alt-text AND as text below:

```markdown
![Brief description](../images/img_123.jpg)

**Описание:** Full detailed description visible in GitHub...
```

### 2. No Duplicates

**Problem:** Same image inserted multiple times with different descriptions.

**Solution:** Insert each unique image path ONLY ONCE:

```markdown
<!-- BAD - duplicate! -->
![Aspect 1](../images/img_123.jpg)
![Aspect 2](../images/img_123.jpg)

<!-- GOOD - single comprehensive description -->
![Complete description](../images/img_123.jpg)

**Описание:** Image shows both:
- Aspect 1: ...
- Aspect 2: ...
```

### 3. No Broken Path Comments

**Problem:** Agent added `<!-- TODO: Broken image path -->` even for valid paths.

**Solution:** Paths are validated before saving. Don't add such comments:

```markdown
<!-- BAD -->
![Diagram](../images/img_123.jpg) <!-- TODO: Broken image path -->

<!-- GOOD -->
![Diagram](../images/img_123.jpg)
```

### 4. Read Metadata Files

Agent can read `.md` files for full context:

```
Prompt says: "Полное описание доступно в: ../images/img_123.md"
Agent can: read_file("KB/images/img_123.md")
Result: Full OCR text and usage instructions
```

---

## API Reference

### ImageMetadata Class

#### `create_metadata_files()`

Create `.md` and `.json` companion files for an image.

```python
ImageMetadata.create_metadata_files(
    image_path=Path("images/img_123.jpg"),
    ocr_text="Extracted text from image",
    file_id="telegram_file_id",
    timestamp=1234567890,
    original_filename="user_photo.jpg",
    file_hash="sha256_hash"
)
```

**Creates:**
- `images/img_123.md` - Description with OCR text
- `images/img_123.json` - Settings and metadata

#### `read_metadata()`

Read metadata for an image.

```python
metadata = ImageMetadata.read_metadata("img_123.jpg", images_dir)
# Returns: {
#   "description": "...",  # Content of .md file
#   "settings": {...}      # Content of .json file
# }
```

#### `get_image_description_summary()`

Get brief summary for agent prompt (max 500 chars).

```python
summary = ImageMetadata.get_image_description_summary("img_123.jpg", images_dir)
# Returns: "Brief OCR text..." (truncated to 500 chars)
```

---

## Benefits

### 1. Shorter Prompts

**Before:** 50KB prompt with full OCR text
**After:** 5KB prompt with brief summaries

### 2. No Duplicates

ContentParser tracks and skips duplicate images automatically.

### 3. Better GitHub Rendering

Text descriptions below images are visible in GitHub.

### 4. Agent Context

Agent can read full `.md` files when needed for detailed context.

### 5. Traceability

`.json` files store metadata for debugging:
- When image was received
- Original filename
- Telegram file_id
- File hash (for deduplication)

---

## File Structure Example

```
knowledge_bases/my-notes/
├── images/
│   ├── img_1234567890_abc12345.jpg      # Image file
│   ├── img_1234567890_abc12345.md       # Description (human-readable)
│   ├── img_1234567890_abc12345.json     # Settings (machine-readable)
│   ├── img_1234567891_def67890.jpg
│   ├── img_1234567891_def67890.md
│   └── img_1234567891_def67890.json
└── topics/
    └── architecture/
        └── system-design.md              # References images
```

**In system-design.md:**
```markdown
# System Design

Our architecture consists of three layers:

![System architecture diagram showing frontend, API, and database layers](../../images/img_1234567890_abc12345.jpg)

**Описание:** The diagram illustrates:
- Frontend layer with React components
- API layer with FastAPI endpoints
- Database layer with PostgreSQL and Redis
```

---

## Testing

Run tests:

```bash
pytest tests/test_image_metadata.py -v
```

**Test coverage:**
- Metadata file creation
- Reading metadata
- Summary generation
- Multiple images
- Missing OCR handling

---

## Migration

Existing images without metadata files will continue to work:
- ContentParser falls back to old format
- No breaking changes

To add metadata to existing images:

```python
from pathlib import Path
from src.processor.image_metadata import ImageMetadata

images_dir = Path("knowledge_bases/my-notes/images")
for img in images_dir.glob("img_*.jpg"):
    if not Path(str(img.with_suffix("")) + ".md").exists():
        # Create metadata with empty OCR
        ImageMetadata.create_metadata_files(
            image_path=img,
            ocr_text="",
            file_id="",
            timestamp=0,
            original_filename=img.name,
            file_hash=""
        )
```

---

## See Also

- [Image Embedding](image-embedding.md) - Original image handling system
- [File Format Recognition](../user-guide/file-format-recognition.md) - Docling OCR integration
- [Qwen CLI Agent](../agents/qwen-code-cli.md) - Agent that uses image metadata
