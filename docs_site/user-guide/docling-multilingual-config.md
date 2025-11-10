# Docling Multilingual Configuration

Guide for configuring Docling to support multiple languages (English and Russian).

---

## Overview

Docling supports multiple OCR backends, each with different language code formats:

- **Tesseract**: Uses ISO 639-3 codes (`eng`, `rus`)
- **EasyOCR**: Uses ISO 639-1 codes (`en`, `ru`)
- **RapidOCR**: Uses ISO 639-3 codes (`eng`, `rus`) or language names
- **OnnxTR**: Uses ISO 639-3 codes (`eng`, `rus`)

---

## Recommended Configuration

For English and Russian support, use the following configuration:

```yaml
MEDIA_PROCESSING_DOCLING:
  enabled: true
  ocr_languages:
    - eng  # English (ISO 639-3)
    - rus  # Russian (ISO 639-3)
  ocr_config:
    backend: rapidocr  # or tesseract, easyocr
    languages: []  # Empty = use ocr_languages as fallback
    rapidocr:
      enabled: true
      providers:
        - CUDAExecutionProvider
        - CPUExecutionProvider
    easyocr:
      enabled: false
      languages:
        - en  # ISO 639-1
        - ru  # ISO 639-1
    tesseract:
      enabled: false
      languages:
        - eng  # ISO 639-3
        - rus  # ISO 639-3
```

---

## Language Code Reference

### ISO 639-3 (Tesseract, RapidOCR, OnnxTR)

| Language | Code |
|----------|------|
| English  | `eng` |
| Russian  | `rus` |

### ISO 639-1 (EasyOCR)

| Language | Code |
|----------|------|
| English  | `en` |
| Russian  | `ru` |

---

## Backend-Specific Configuration

### RapidOCR (Default, Recommended)

RapidOCR is the default backend and supports multiple languages:

```yaml
ocr_config:
  backend: rapidocr
  languages: []  # Uses ocr_languages when empty
  rapidocr:
    enabled: true
    providers:
      - CUDAExecutionProvider
      - CPUExecutionProvider
```

**Language codes**: ISO 639-3 (`eng`, `rus`)

### Tesseract

Tesseract requires language packs to be installed in the Docker container:

```yaml
ocr_config:
  backend: tesseract
  languages: []  # Uses ocr_languages when empty
  tesseract:
    enabled: true
    languages:
      - eng
      - rus
```

**Language codes**: ISO 639-3 (`eng`, `rus`)

**Note**: The Dockerfile already includes `tesseract-ocr-eng` and `tesseract-ocr-rus` packages.

### EasyOCR

EasyOCR supports many languages out of the box:

```yaml
ocr_config:
  backend: easyocr
  languages: []  # Uses ocr_languages when empty
  easyocr:
    enabled: true
    languages:
      - en  # ISO 639-1
      - ru  # ISO 639-1
    gpu: auto
```

**Language codes**: ISO 639-1 (`en`, `ru`)

**Note**: EasyOCR downloads models automatically on first use.

---

## Complete Example Configuration

```yaml
MEDIA_PROCESSING_DOCLING:
  enabled: true
  max_file_size_mb: 25
  prefer_markdown_output: true
  fallback_plain_text: true
  image_ocr_enabled: true
  keep_images: false
  generate_page_images: false
  startup_sync: true
  
  # Main OCR languages (ISO 639-3)
  # Used as fallback when ocr_config.languages is empty
  ocr_languages:
    - eng
    - rus
  
  ocr_config:
    backend: rapidocr  # rapidocr | tesseract | easyocr | onnxtr
    languages: []  # Empty = use ocr_languages above
    
    rapidocr:
      enabled: true
      providers:
        - CUDAExecutionProvider
        - CPUExecutionProvider
    
    easyocr:
      enabled: false
      languages:
        - en
        - ru
      gpu: auto
    
    tesseract:
      enabled: false
      languages:
        - eng
        - rus
    
    onnxtr:
      enabled: false
  
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
  
  model_cache:
    base_dir: /opt/docling-mcp/models
    groups:
      - name: layout
      - name: tableformer
      - name: code_formula
      - name: picture_classifier
      - name: rapidocr
        backends:
          - onnxruntime
```

---

## How Language Selection Works

1. **Primary source**: `ocr_config.languages` (if not empty)
2. **Fallback**: `ocr_languages` (if `ocr_config.languages` is empty)
3. **Backend override**: Each backend can have its own `languages` list

**Priority order**:
```
ocr_config.<backend>.languages 
  → ocr_config.languages 
    → ocr_languages
```

---

## Testing Multilingual OCR

After configuration, test with documents containing both languages:

1. **English document**: Should recognize English text correctly
2. **Russian document**: Should recognize Cyrillic text correctly
3. **Mixed document**: Should handle both languages in the same document

---

## Troubleshooting

### Tesseract: Language pack not found

**Error**: `Error opening data file /usr/share/tesseract-ocr/5/tessdata/rus.traineddata`

**Solution**: Ensure Docker container includes language packs:
```dockerfile
tesseract-ocr-eng
tesseract-ocr-rus
```

The Dockerfile already includes these packages.

### EasyOCR: Model download fails

**Error**: `Failed to download EasyOCR model`

**Solution**: 
- Check internet connection
- Set `download_enabled: true` in EasyOCR config
- Models are cached in `DOCLING_CACHE_DIR`

### RapidOCR: Language not supported

**Error**: `Unsupported language code`

**Solution**: Use ISO 639-3 codes (`eng`, `rus`) instead of ISO 639-1 (`en`, `ru`)

---

## See Also

- [File Format Recognition](file-format-recognition.md)
- [Configuration Reference](../reference/configuration.md)
- [Docling Documentation](https://github.com/DS4SD/docling)
