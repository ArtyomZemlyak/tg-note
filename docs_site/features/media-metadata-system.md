# Media Metadata System

System for managing media descriptions and preventing duplicates.

---

## Overview

The Media Metadata System solves several problems with image handling:

1. **Large prompts**: OCR text from images was included in full in agent prompts
2. **Duplicates**: Same images were inserted multiple times with different descriptions
3. **GitHub rendering**: Image descriptions in `[alt text]` are not visible in GitHub
4. **Confusion**: Agents sometimes mixed up which image was which

### Solution

For each saved media asset (e.g., `img_1234567890_abc12345_coconut_chain.jpg`), the system creates two companion files:

- `img_1234567890_abc12345_coconut_chain.md` - Human-readable description with OCR text
- `img_1234567890_abc12345_coconut_chain.json` - Machine-readable settings and metadata

---

## How It Works

### 1. Image Saved to KB

When a Telegram image is processed:

```python
# In FileProcessor.download_and_process_telegram_file()
save_path = kb_media_dir / "img_1234567890_abc12345_coconut_chain.jpg"
# Download and save image
# Process with Docling OCR

# Create metadata files
MediaMetadata.create_metadata_files(
    image_path=save_path,
    ocr_text=extracted_text,
    file_id=telegram_file_id,
    timestamp=message_timestamp,
    original_filename="user_image.jpg",
    file_hash=computed_hash
)
```

### 1.1 Filename Structure

Every saved image filename now follows the pattern:

```
img_<timestamp>_<telegram-id>_<ocr-slug>.jpg
```

- `timestamp` — message timestamp (preserves chronological order)
- `telegram-id` — stable `file_unique_id` (or `file_id`/hash fallback) to guarantee uniqueness
- `ocr-slug` — lower-case, underscore-separated keywords extracted from the first OCR sentence

This makes filenames both unique **and** meaningful for agents (e.g., `img_1763208338_agacagia_coconut_vs_reasoning.jpg`).

### 2. Metadata Files Created

**img_1234567890_abc12345_coconut_chain.md:**
```markdown
# Image Description

**File:** img_1234567890_abc12345_coconut_chain.jpg
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

**img_1234567890_abc12345_coconut_chain.json:**
```json
{
  "file_id": "abc12345",
  "timestamp": 1234567890,
  "original_filename": "user_image.jpg",
  "file_hash": "sha256_hash_here",
  "media_filename": "img_1234567890_abc12345_coconut_chain.jpg",
  "ocr_extracted": true,
  "ocr_length": 1234
}
```

### 3. Prompt Generation

When ContentParser builds the prompt for the agent:

**Old approach (problem):**
```
--- Содержимое файла: image.jpg (сохранено как: ../media/img_123_example.jpg) ---
[10KB of OCR text here]
```

**New approach (solution):**
```
--- Изображение: image.jpg (сохранено как: ../media/img_123_example.jpg) ---
Описание: [Brief 500 char summary of OCR]
Полное описание доступно в: ../media/img_123_example.md
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
![Brief description](../media/img_123_example.jpg)

**Описание:** Full detailed description visible in GitHub...
```

### 2. No Duplicates

**Problem:** Same image inserted multiple times with different descriptions.

**Solution:** Insert each unique image path ONLY ONCE:

```markdown
<!-- BAD - duplicate! -->
![Aspect 1](../media/img_123_example.jpg)
![Aspect 2](../media/img_123_example.jpg)

<!-- GOOD - single comprehensive description -->
![Complete description](../media/img_123_example.jpg)

**Описание:** Image shows both:
- Aspect 1: ...
- Aspect 2: ...
```

### 3. No Broken Path Comments

**Problem:** Agent added `<!-- TODO: Broken image path -->` even for valid paths.

**Solution:** Paths are validated before saving. Don't add such comments:

```markdown
<!-- BAD -->
![Diagram](../media/img_123_example.jpg) <!-- TODO: Broken image path -->

<!-- GOOD -->
![Diagram](../media/img_123_example.jpg)
```

### 4. Read Metadata Files

Agent can read `.md` files for full context:

```
Prompt says: "Полное описание доступно в: ../media/img_123_example.md"
Agent can: read_file("KB/media/img_123_example.md")
Result: Full OCR text and usage instructions
```

---

## API Reference

### MediaMetadata Class

#### `create_metadata_files()`

Create `.md` and `.json` companion files for an image.

```python
MediaMetadata.create_metadata_files(
    image_path=Path("media/img_123_example.jpg"),
    ocr_text="Extracted text from image",
    file_id="telegram_file_id",
    timestamp=1234567890,
    original_filename="user_photo.jpg",
    file_hash="sha256_hash"
)
```

**Creates:**
- `media/img_123_example.md` - Description with OCR text
- `media/img_123_example.json` - Settings and metadata

#### `read_metadata()`

Read metadata for an image.

```python
metadata = MediaMetadata.read_metadata("img_123_example.jpg", media_dir)
# Returns: {
#   "description": "...",  # Content of .md file
#   "settings": {...}      # Content of .json file
# }
```

#### `get_media_description_summary()`

Get brief summary for agent prompt (max 500 chars).

```python
summary = MediaMetadata.get_media_description_summary("img_123_example.jpg", media_dir)
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
├── media/
│   ├── img_1234567890_abc12345_coconut_chain.jpg      # Image file
│   ├── img_1234567890_abc12345_coconut_chain.md       # Description (human-readable)
│   ├── img_1234567890_abc12345_coconut_chain.json     # Settings (machine-readable)
│   ├── img_1234567891_def67890_reasoning_map.jpg
│   ├── img_1234567891_def67890_reasoning_map.md
│   └── img_1234567891_def67890_reasoning_map.json
└── topics/
    └── architecture/
        └── system-design.md              # References images
```

**In system-design.md:**
```markdown
# System Design

Our architecture consists of three layers:

![System architecture diagram showing frontend, API, and database layers](../../media/img_1234567890_abc12345_coconut_chain.jpg)

**Описание:** The diagram illustrates:
- Frontend layer with React components
- API layer with FastAPI endpoints
- Database layer with PostgreSQL and Redis
```

---

## Testing

Run tests:

```bash
pytest tests/test_media_metadata.py -v
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
from src.processor.media_metadata import MediaMetadata

    media_dir = Path("knowledge_bases/my-notes/media")
    for img in media_dir.glob("img_*.jpg"):
        if not Path(str(img.with_suffix("")) + ".md").exists():
            # Create metadata with empty OCR
            MediaMetadata.create_metadata_files(
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
- [Qwen CLI Agent](../agents/qwen-code-cli.md) - Agent that uses media metadata
