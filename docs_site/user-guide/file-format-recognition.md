# File format recognition

## Overview

tg-note supports automatic recognition and processing of various file formats using [Docling](https://github.com/DS4SD/docling). When you send a file to the bot, the system automatically extracts text content and integrates it into your knowledge base.

## Supported formats

### Documents
- PDF (`.pdf`)
- Word (`.docx`)
- PowerPoint (`.pptx`)
- Excel (`.xlsx`)

### Text files
- Markdown (`.md`)
- HTML (`.html`)
- Plain Text (`.txt`)

### Images
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- TIFF (`.tiff`)

## How it works

### Automatic processing
1. Send a file to the bot (attachment or forwarded)
2. The bot downloads the file to a temporary directory
3. Docling processes the file and extracts text
4. The content is merged with the message text for analysis
5. The result is saved to the knowledge base

### Example
```
# Just send a file to the bot
# The bot will:
# 1. Detect file format
# 2. Extract content
# 3. Analyze with the AI agent
# 4. Save to the KB with proper structure
```

## Architecture

### Components
1. `FileProcessor` (`src/processor/file_processor.py`)
   - Manages file processing
   - Docling integration
   - Telegram file download
   - Temporary storage

2. `ContentParser` (`src/processor/content_parser.py`)
   - Adds `parse_group_with_files()`
   - Merges file content with message text
   - Async processing

3. `BotHandlers` (`src/bot/handlers.py`)
   - Uses new method to process files
   - Supports documents and photos
   - Automatic temp files cleanup

### Processing flow
```
┌─────────────────┐
│ Telegram Message│
│   with File     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Bot Handlers   │
│ (download file) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ File Processor  │
│   (Docling)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Content Parser  │
│ (merge content) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AI Agent      │
│  (analysis)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Knowledge Base  │
│    (save)       │
└─────────────────┘
```

## Installation

Docling now runs as an MCP server. Docker Compose includes the `docling-mcp` service by default, so
starting the stack is enough to enable document processing.

```bash
# Start Docling MCP together with the hub and bot
docker compose up -d docling-mcp mcp-hub bot
```

The hub registers the Docling MCP server automatically. If you run the server outside of Docker,
set `MEDIA_PROCESSING_DOCLING.mcp.url` to the appropriate endpoint.

The Docling container is built from the repository (`docker/docling-mcp/Dockerfile`) with GPU support.
Model artefacts and configuration are persisted under:

- `data/docling/config` – rendered container configuration (`docling-config.json`)
- `data/docling/models` – downloaded OCR/VLM models
- `data/docling/cache` – HuggingFace / ModelScope caches
- `logs/docling` – container logs

Changing Docling settings via `/settings` regenerates the container configuration and automatically
kicks off model downloads. Progress updates are sent back to the Telegram chat, so no separate command
is required.

Docling settings expose detailed controls under `MEDIA_PROCESSING_DOCLING`:

- `startup_sync`: enable/disable automatic downloads on container start
- `keep_images` / `generate_page_images`: embed page snapshots in the output
- `ocr_config`: choose between `rapidocr`, `easyocr`, `tesseract`, `tesseract_cli`, or `onnxtr`
- `model_cache.downloads`: list of model artefacts fetched from HuggingFace or ModelScope

The default configuration ships with RapidOCR (GPU-enabled via ONNX Runtime). Switch to EasyOCR
or Tesseract by updating `ocr_config.backend` and adjusting backend-specific sections.

### Local fallback (optional)

If you prefer to run Docling inside the bot process, install the Python package manually and set the
backend to `local` in `config.yaml`:

```bash
pip install docling
```

### Verify installation

```python
from src.processor.file_processor import FileProcessor

processor = FileProcessor()
if processor.is_available():
    print("Docling available!")
    print(f"Supported formats: {processor.get_supported_formats()}")
else:
    print("Docling not available")
```

## Examples

### PDF document
```
1. Send a PDF file
2. Bot replies: "🔄 Processing message..."
3. After processing you get details:
   ✅ Saved successfully!
   📁 File: research-paper-2024-10-04.md
   📂 Category: science/research
   🏷 Tags: pdf, research, ai
```

### Image with text
```
1. Send an image (screenshot or document photo)
2. Docling extracts text from the image
3. The text is analyzed and saved to the KB
```

### Multiple files
```
1. Send multiple files in a row
2. Bot groups them (30 seconds)
3. All files are processed and merged into one note
```

## Error handling

### Unsupported format
- The bot still tries to extract text
- Processes the rest of the message content
- Does not abort processing

### File processing error
- Error is logged
- User can be notified (optional)
- Other content is still processed

### Temporary files
- Temporary directories are created
- Files are cleaned up after processing
- Exceptions on cleanup are handled

## Settings

File format recognition works out of the box. You can customize whether it's enabled and which formats are processed:

### Enabling/Disabling media processing

You can completely enable or disable media file processing using the master switch:

```yaml
# config.yaml

# Enable media processing (default)
MEDIA_PROCESSING_ENABLED: true

# Disable all media processing
MEDIA_PROCESSING_ENABLED: false
```

When `MEDIA_PROCESSING_ENABLED` is set to `false`, all file processing is disabled regardless of other settings.

### Docling configuration

Docling behaviour is configured via the `MEDIA_PROCESSING_DOCLING` block in `config.yaml`. Key options:

- `enabled`: Docling master switch (in addition to `MEDIA_PROCESSING_ENABLED`)
- `backend`: `"mcp"` (default) or `"local"` to force the in-process DocumentConverter
- `formats`: list of allowed file extensions (lowercase, no dots)
- `max_file_size_mb`: per-file size limit (set to `0` to disable the limit)
- `prefer_markdown_output`: prefer Markdown export when possible
- `fallback_plain_text`: automatically fallback to text export when preferred export fails
- `image_ocr_enabled`: allow OCR for image formats (`jpg`, `jpeg`, `png`, `tiff`)
- `ocr_languages`: OCR language hints (ISO 639-3 codes such as `eng`, `deu`)
- `mcp`: nested MCP configuration (`server_name`, `url`, `tool_name`, `auto_detect_tool`, etc.)

```yaml
# config.yaml

MEDIA_PROCESSING_DOCLING:
  enabled: true
  backend: mcp
  max_file_size_mb: 25
  prefer_markdown_output: true
  fallback_plain_text: true
  image_ocr_enabled: true
  ocr_languages:
    - eng
  formats:
    - pdf
    - docx
    - pptx
    - xlsx
    - html
    - md
    - txt
    - jpg
    - jpeg
    - png
    - tiff
  mcp:
    server_name: docling
    transport: sse
    url: http://docling-mcp:8077/sse   # Override for custom deployments
    tool_name: convert_document
    auto_detect_tool: true
```

#### Enabling/Disabling specific formats

Customise the `formats` list (and optionally `image_ocr_enabled`) to restrict Docling:

```yaml
# Enable only documents (no images)
MEDIA_PROCESSING_DOCLING:
  enabled: true
  image_ocr_enabled: false
  formats:
    - pdf
    - docx
    - pptx
    - xlsx

# Enable only specific formats
MEDIA_PROCESSING_DOCLING:
  formats:
    - pdf
    - jpg
    - png

# Disable Docling entirely
MEDIA_PROCESSING_DOCLING:
  enabled: false
```

> Legacy note: The older `MEDIA_PROCESSING_DOCLING_FORMATS` list is still supported for backward compatibility, but new deployments should migrate to the richer `MEDIA_PROCESSING_DOCLING` configuration block.

### Message grouping timeout
```yaml
# config.yaml
MESSAGE_GROUP_TIMEOUT: 30  # seconds
```

### Media processing configuration structure

The media processing configuration has a hierarchical structure:

```yaml
# Master switch - controls all media processing
MEDIA_PROCESSING_ENABLED: true

# Per-framework format configuration (new structure)
MEDIA_PROCESSING_DOCLING:
  enabled: true
  formats:
    - pdf
    - jpg
    - ...

# Future frameworks can be added
# MEDIA_PROCESSING_SOME_OTHER_FRAMEWORK_FORMATS:
#   - mp3
#   - mp4
#   - ...

# (Deprecated) Older list-only syntax is still recognised:
# MEDIA_PROCESSING_DOCLING_FORMATS:
#   - pdf
#   - jpg
#   - ...
```

### Configuration examples

```yaml
# Example 1: Completely disable media processing
MEDIA_PROCESSING_ENABLED: false
# When disabled, format lists are ignored

# Example 2: Enable only PDF processing
MEDIA_PROCESSING_ENABLED: true
MEDIA_PROCESSING_DOCLING:
  formats:
    - pdf

# Example 3: Enable documents but not images
MEDIA_PROCESSING_ENABLED: true
MEDIA_PROCESSING_DOCLING:
  image_ocr_enabled: false
  formats:
    - pdf
    - docx
    - pptx
    - xlsx

# Example 4: Enable only images (OCR)
MEDIA_PROCESSING_ENABLED: true
MEDIA_PROCESSING_DOCLING:
  formats:
    - jpg
    - jpeg
    - png
    - tiff
```

## Advanced usage

### Programmatic access
```python
from pathlib import Path
from src.processor.file_processor import FileProcessor

async def process_my_file():
    processor = FileProcessor()

    if not processor.is_available():
        print("Docling not available")
        return

    result = await processor.process_file(Path("my_document.pdf"))

    if result:
        print(f"Extracted {len(result['text'])} chars")
        print(f"Metadata: {result['metadata']}")
        print(f"Text: {result['text'][:100]}...")
```

### Agent integration
```python
# in content_parser.py
content = await self.content_parser.parse_group_with_files(group, bot=self.bot)

# content['text'] contains:
# - Message text
# - Extracted file content
# - File metadata
```

## Performance

### Optimization
- Async IO for file operations
- Temporary files cleaned automatically
- Sequential but efficient handling of multiple files

### Telegram limits
- Max file size: 20 MB (bots)
- Files hosted by Telegram temporarily
- Download speed depends on network

## Debugging

Enable detailed logging:
```yaml
# config.yaml
LOG_LEVEL: DEBUG
```

You will see:
- File download progress
- Docling results
- Errors and warnings
- Cleanup operations

### Check Docling
```python
import logging
logging.basicConfig(level=logging.DEBUG)
from src.processor.file_processor import FileProcessor

processor = FileProcessor()
print(f"Docling available: {processor.is_available()}")
print(f"Supported: {processor.get_supported_formats()}")
```

## Known issues
- Large files (>10 MB) may take longer
- Low-quality images reduce OCR quality
- Complex PDF layout may require extra processing

## Support
- Docs: https://artyomzemlyak.github.io/tg-note/
- Issues: https://github.com/ArtyomZemlyak/tg-note/issues
- Discussions: https://github.com/ArtyomZemlyak/tg-note/discussions

## Roadmap
- ✅ Basic file support
- 🚧 Audio/video files
- 📋 Better table extraction
- 📋 Archive support (.zip, .tar.gz)
- 📋 Batch processing
- 📋 Caching
