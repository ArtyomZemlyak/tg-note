# Media Metadata System

System for managing media descriptions and preventing duplicates.

---

## Overview

The Media Metadata System solves several issues with image handling:

1. **Large prompts:** OCR text was inlined into prompts
2. **Duplicates:** Same images inserted multiple times with different descriptions
3. **GitHub rendering:** Alt text is invisible; need visible descriptions
4. **Disambiguation:** Agents sometimes mixed up which image was which

### Solution

For each saved media asset (e.g., `img_1234567890_abc12345_coconut_chain.jpg`), two companion files are created:

- `img_1234567890_abc12345_coconut_chain.md` — human-readable description with OCR text
- `img_1234567890_abc12345_coconut_chain.json` — machine-readable settings and metadata

---

## How it works

### 1. Image saved to KB

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

### 1.1 Filename structure

Every saved image filename follows:

```
img_<timestamp>_<telegram-id>_<ocr-slug>.jpg
```

- `timestamp` — message timestamp (chronological order)
- `telegram-id` — stable `file_unique_id` (or `file_id`/hash fallback) to guarantee uniqueness
- `ocr-slug` — lower-case, underscore-separated keywords from the first OCR sentence

This makes filenames both unique **and** meaningful (e.g., `img_1763208338_agacagia_coconut_vs_reasoning.jpg`).

### 2. Metadata files created

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

### 3. Prompt generation

When ContentParser builds the prompt for the agent:

**Old approach (problem):**
```
--- File content: image.jpg (saved as: ../media/img_123_example.jpg) ---
[10KB of OCR text here]
```

**New approach (solution):**
```
--- Image: image.jpg (saved as: ../media/img_123_example.jpg) ---
Description: [Brief 500 char summary of OCR]
Full description available at: ../media/img_123_example.md
```

### 4. Duplicate detection

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

## Agent instructions

The agent receives updated instructions in `template.ru.v2.md`.

### 1. Add descriptions twice

**Problem:** GitHub does not render alt-text `[...]` for images.

**Solution:** Add description both in alt-text **and** as visible text below:

```markdown
![Brief description](../media/img_123_example.jpg)

**Description:** Full detailed description visible in GitHub...
```

### 2. No duplicates

**Problem:** Same image inserted multiple times with different descriptions.

**Solution:** Insert each unique image path **once**:

```markdown
<!-- BAD - duplicate! -->
![Aspect 1](../media/img_123_example.jpg)
![Aspect 2](../media/img_123_example.jpg)

<!-- GOOD - single comprehensive description -->
![Complete description](../media/img_123_example.jpg)

**Description:** Image shows both:
- Aspect 1: ...
- Aspect 2: ...
```

### 3. No "broken path" comments

**Problem:** Agent added `<!-- TODO: Broken image path -->` even for valid paths.

**Solution:** Paths are validated before saving. Do **not** add those comments:

```markdown
<!-- BAD -->
![Diagram](../media/img_123_example.jpg) <!-- TODO: Broken image path -->

<!-- GOOD -->
![Diagram](../media/img_123_example.jpg)
```

### 4. Read metadata files

Agent can read `.md` files for full context:

```
Prompt says: "Full description available at: ../media/img_123_example.md"
Agent can: read_file("KB/media/img_123_example.md")
Result: Full OCR text and usage instructions
```

---

## API reference

### MediaMetadata class

#### `create_metadata_files()`
Create `.md` and `.json` companion files for an image.

```python
MediaMetadata.create_metadata_files(
    image_path=Path("media/img_123_example.jpg"),
    ocr_text="...",
    file_id="abc",
    timestamp=1700000000,
    original_filename="image.jpg",
    file_hash="...",
)
```

#### `get_image_description_summary()`
Generate a short summary (first ~500 chars) from OCR text for the prompt.

#### `load_metadata()` / `save_metadata()`
Read/write `.json` metadata files.

### Prompt integration (ContentParser)

1. Save media files and metadata via MediaMetadata
2. When building prompt:
   - Insert minimal filenames list (see Image Prompt Format doc)
   - Provide link to `.md` with full description
3. Avoid duplicates by tracking seen filenames

---

## Why this matters

- **Smaller prompts:** OCR stays in `.md` files, not inline
- **Better UX on GitHub:** Visible descriptions below images
- **Fewer mistakes:** Clear mapping between filename and description; duplicates avoided
- **Traceability:** `.json` keeps hashes and IDs for troubleshooting

---

## AICODE-NOTE
- Companion files (`.md` + `.json`) are created for every media asset.
- Prompts stay short; agents read metadata when needed.
- Duplicate insertion is prevented via in-memory tracking.
