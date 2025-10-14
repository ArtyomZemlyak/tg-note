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

Docling is installed as a dependency.

```bash
# Poetry
poetry install

# Or pip
pip install -e "."
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

File format recognition works out of the box. You can customize:

### Message grouping timeout
```yaml
# config.yaml
MESSAGE_GROUP_TIMEOUT: 30  # seconds
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
