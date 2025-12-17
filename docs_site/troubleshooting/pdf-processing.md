# Troubleshooting PDF Processing

## Overview

This guide helps diagnose and fix issues with PDF document processing in tg-note.

## Symptoms

- ✅ Images from Telegram are processed successfully
- ❌ PDF documents are not being processed
- ❌ No text is extracted from PDF files
- ❌ Documents are silently ignored

## Common Causes and Solutions

### 1. Missing File Extension or MIME Type

**Problem**: Telegram may not provide `file_name` or `mime_type` for documents, especially for forwarded files.

**Solution**: ✅ **Already implemented** (v0.2.0+)

The system now includes robust file type detection that:
- Tries MIME type first (most reliable)
- Falls back to magic bytes detection
- Handles PDFs with leading whitespace/BOM
- Supports fuzzy matching for wrapped PDFs

**Implementation**: `src/processor/file_processor.py::_detect_file_type_from_content()`

**Verification**: Check logs for:
```
[Document Processing] Received document from Telegram: file_id=..., file_name=..., mime_type=...
[File Processing] Extension detected from filename: .pdf
```

or
```
[File Processing] No extension found in filename, will attempt content-based detection
File type detected via content analysis: pdf
```

### 2. Docling Service Not Running

**Problem**: The Docling MCP service is not running or not accessible.

**Diagnosis**:

```bash
# Check if Docling container is running
docker ps | grep docling

# Check Docling logs
docker logs docling-mcp --tail=50

# Test Docling endpoint
curl -v http://localhost:8077/health
```

**Solution**:

```bash
# Start Docling service
docker-compose up -d docling-mcp

# Check status
docker-compose ps
```

**Verification**: Look for in bot logs:
```
[FileProcessor] Docling MCP server 'docling' found in registry
Processing file via Docling MCP: test.pdf (format: pdf, tool: convert_document_from_content)
```

### 3. PDF Format Disabled in Settings

**Problem**: PDF format is disabled in configuration.

**Diagnosis**: Check `config.yaml` or environment variables:

```yaml
MEDIA_PROCESSING_ENABLED: true
MEDIA_PROCESSING_DOCLING:
  enabled: true
  formats: ["pdf", "docx", "pptx", ...]  # <- PDF must be here
```

**Solution**: Add `"pdf"` to the formats list and restart the bot.

**Verification**: Check logs for:
```
[FileProcessor] File processor initialized. Supported formats: pdf, docx, pptx, ...
```

NOT:
```
[File Processing] Skipping file because format 'pdf' is disabled for Docling
```

### 4. File Size Exceeds Limit

**Problem**: PDF file is larger than `max_file_size_mb` setting.

**Default**: 25 MB

**Diagnosis**: Check logs for:
```
[File Processing] Skipping file test.pdf (26214400 bytes) because it exceeds Docling limit of 25 MB
```

**Solution**: Increase the limit in `config.yaml`:

```yaml
MEDIA_PROCESSING_DOCLING:
  max_file_size_mb: 50  # Increase to 50 MB
```

Or set to 0 for unlimited:

```yaml
MEDIA_PROCESSING_DOCLING:
  max_file_size_mb: 0  # No limit
```

**Note**: Larger files require more memory and processing time.

### 5. OCR Disabled for Scanned PDFs

**Problem**: PDFs are processed but return empty text.

**Cause**: Scanned PDFs contain images, not text. OCR must be enabled.

**Diagnosis**: Check `image_ocr_enabled` setting:

```yaml
MEDIA_PROCESSING_DOCLING:
  image_ocr_enabled: false  # <- This disables OCR for scanned PDFs!
```

**Solution**: Enable OCR:

```yaml
MEDIA_PROCESSING_DOCLING:
  image_ocr_enabled: true
```

**Important**: `image_ocr_enabled` affects both:
- Image files (JPG, PNG, etc.)
- Scanned PDFs (PDFs containing images)

If you want to disable image processing but keep PDF OCR, this is currently not supported. Use format exclusion instead:

```yaml
MEDIA_PROCESSING_DOCLING:
  image_ocr_enabled: true
  formats: ["pdf", "docx", "pptx"]  # Exclude jpg, png, etc.
```

### 6. Docling Models Not Downloaded

**Problem**: Docling is running but models are missing.

**Diagnosis**: Check Docling container logs:

```bash
docker logs docling-mcp 2>&1 | grep -i model
```

Look for errors like:
```
ERROR: Failed to load layout model
ERROR: tableformer model not found
```

**Solution**: Sync models via MCP tool:

```python
from src.processor.file_processor import FileProcessor

processor = FileProcessor()
await processor.sync_docling_models(force=True)
```

Or restart Docling container with `startup_sync: true`:

```yaml
MEDIA_PROCESSING_DOCLING:
  startup_sync: true
```

**Configuration**: Models are controlled by `model_cache.builtin_models`:

```yaml
MEDIA_PROCESSING_DOCLING:
  model_cache:
    builtin_models:
      layout: true
      tableformer: true
      code_formula: true
      picture_classifier: true
      rapidocr:
        enabled: true
```

## Diagnostic Checklist

Follow these steps to diagnose PDF processing issues:

### Step 1: Check Logging

Enable detailed logging by sending a test PDF and checking logs:

```bash
# Watch bot logs in real-time
docker-compose logs -f bot

# Or for local development
tail -f logs/bot.log
```

Look for these log entries:

1. **Document received**:
   ```
   [Document Processing] Received document from Telegram: file_id=..., file_name=test.pdf, mime_type=application/pdf
   ```

2. **File processing started**:
   ```
   [File Processing] Starting download and processing: original_filename=test.pdf, mime_type=application/pdf
   ```

3. **Extension detected**:
   ```
   [File Processing] Extension detected from filename: .pdf
   ```
   or
   ```
   [File Processing] No extension found, will attempt content-based detection
   File type detected via content analysis: pdf
   ```

4. **Docling processing**:
   ```
   Processing file via Docling MCP: test.pdf (format: pdf, tool: convert_document_from_content)
   ```

5. **Success**:
   ```
   Successfully processed document: test.pdf
   ```

### Step 2: Verify Settings

Check your configuration:

```bash
# View current config
cat config.yaml

# Check environment overrides
docker-compose config
```

Verify:
- [ ] `MEDIA_PROCESSING_ENABLED: true`
- [ ] `MEDIA_PROCESSING_DOCLING.enabled: true`
- [ ] `"pdf"` in `MEDIA_PROCESSING_DOCLING.formats`
- [ ] `max_file_size_mb` is sufficient (default: 25)
- [ ] `image_ocr_enabled: true` for scanned PDFs

### Step 3: Test Docling Service

```bash
# Check container status
docker ps | grep docling

# Check Docling health
curl http://localhost:8077/health

# Check available tools
# (requires MCP client - see src/mcp/client.py)
```

### Step 4: Test with Simple PDF

Create a minimal test PDF:

```bash
# Create simple text PDF
echo "Test PDF content" | ps2pdf - test.pdf

# Send to your bot and check logs
```

This PDF should:
- Be small (< 1 KB)
- Have clear `application/pdf` MIME type
- Start with `%PDF` magic bytes

If this fails, the issue is with Docling configuration, not file detection.

### Step 5: Test without Extension

To verify robust file detection works:

1. Create PDF without extension:
   ```bash
   cp test.pdf telegram_document
   ```

2. Simulate Telegram document with no file_name:
   - The system should detect PDF via magic bytes
   - Check logs for: `File type detected via content analysis: pdf`

## Advanced Debugging

### Enable Debug Logging

Add to `config.yaml`:

```yaml
logging:
  level: DEBUG
```

Or set environment variable:

```bash
export LOG_LEVEL=DEBUG
```

### Inspect Downloaded File

To see exactly what Telegram sends:

1. Temporarily modify `file_processor.py`:
   ```python
   # After: downloaded_file = await bot.download_file(...)

   import tempfile
   debug_path = f"/tmp/telegram_debug_{file_id}.bin"
   with open(debug_path, "wb") as f:
       f.write(downloaded_file)
   self.logger.info(f"DEBUG: Saved file to {debug_path}")
   self.logger.info(f"DEBUG: First 100 bytes (hex): {downloaded_file[:100].hex()}")
   ```

2. Check the saved file:
   ```bash
   file /tmp/telegram_debug_*.bin
   hexdump -C /tmp/telegram_debug_*.bin | head -20
   ```

### Check Docling Directly

Test Docling independently:

```bash
# Enter Docling container
docker exec -it docling-mcp bash

# Test document conversion
python3 -c "
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
result = converter.convert('/path/to/test.pdf')
print(result.document.export_to_markdown())
"
```

## Known Issues

### Issue: Forwarded PDFs Have No Extension

**Status**: ✅ Fixed in v0.2.0

**Description**: When users forward PDF files from other chats, Telegram may not provide `file_name` or `mime_type`.

**Solution**: Implemented robust content-based file type detection using magic bytes.

### Issue: PDFs with Encryption

**Status**: ⚠️ Partial support

**Description**: Encrypted/password-protected PDFs cannot be processed.

**Workaround**: Ask user to send unencrypted version.

### Issue: Very Large PDFs (>100 MB)

**Status**: ⚠️ Limited support

**Description**: Large PDFs may cause memory issues or timeouts.

**Recommendation**:
- Set reasonable `max_file_size_mb` limit (25-50 MB)
- Consider splitting large PDFs into smaller chunks

### Issue: Malformed PDFs

**Status**: ⚠️ Depends on Docling

**Description**: Some PDFs may have structural issues that Docling cannot handle.

**Diagnosis**: Check Docling logs for conversion errors.

**Workaround**: Try converting PDF to a different format first.

## Configuration Examples

### Minimal Configuration (PDF Only)

```yaml
MEDIA_PROCESSING_ENABLED: true
MEDIA_PROCESSING_DOCLING:
  enabled: true
  backend: mcp
  formats: ["pdf"]
  image_ocr_enabled: true
  max_file_size_mb: 25
```

### Full Configuration (All Formats)

```yaml
MEDIA_PROCESSING_ENABLED: true
MEDIA_PROCESSING_DOCLING:
  enabled: true
  backend: mcp
  formats: ["pdf", "docx", "pptx", "xlsx", "html", "md", "txt", "jpg", "png"]
  image_ocr_enabled: true
  max_file_size_mb: 50
  prefer_markdown_output: true
  fallback_plain_text: true

  mcp:
    server_name: docling
    transport: sse
    url: http://docling-mcp:8077/sse

  model_cache:
    builtin_models:
      layout: true
      tableformer: true
      code_formula: true
      picture_classifier: true
      rapidocr:
        enabled: true
```

## Getting Help

If you're still experiencing issues:

1. **Collect logs**: Save bot and Docling logs covering the problematic operation
2. **Prepare test case**: Use a simple, shareable PDF if possible
3. **Check configuration**: Share relevant parts of `config.yaml` (remove sensitive data)
4. **Open issue**: Create GitHub issue with:
   - Symptom description
   - Relevant log excerpts
   - Configuration (sanitized)
   - Steps to reproduce

## See Also

- [Architecture: File Processing](../architecture/file-processing.md)
- [Development: Testing](../development/testing.md)
- [Configuration: Media Processing](../configuration/media-processing.md)
