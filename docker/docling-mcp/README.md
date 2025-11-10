# Docling MCP Container

Docker container for Docling document processing with MCP (Model Context Protocol) server integration.

## Features

- **Multiple OCR Backends**: RapidOCR (default), EasyOCR, Tesseract, OnnxTR
- **VLM Support**: Vision-Language Models for advanced document understanding
- **GPU Acceleration**: CUDA support for faster processing
- **Configurable**: Full control over OCR settings, models, and parameters
- **Model Management**: Automatic model download and caching
- **MCP Integration**: Seamless integration with tg-note via MCP protocol

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docling MCP Container                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐      ┌──────────────────────────┐     │
│  │  MCP Server     │◄─────┤  Document Converter       │     │
│  │  (FastMCP/SSE)  │      │  (docling core)           │     │
│  └────────┬────────┘      └──────────┬───────────────┘     │
│           │                           │                      │
│           │                           ▼                      │
│           │                  ┌────────────────┐             │
│           │                  │  OCR Backends  │             │
│           │                  ├────────────────┤             │
│           │                  │  • RapidOCR    │             │
│           │                  │  • EasyOCR     │             │
│           │                  │  • Tesseract   │             │
│           │                  │  • OnnxTR      │             │
│           │                  └────────────────┘             │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Model Cache & Download Manager             │   │
│  │  (HuggingFace, ModelScope, local cache)              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         ▲                                    ▲
         │ HTTP/SSE                          │ Volume Mounts
         │ (Port 8077)                       │
         │                                   │
    ┌────┴──────┐                     ┌─────┴────────┐
    │  tg-note  │                     │  Host Data   │
    │    Bot    │                     │  Directories │
    └───────────┘                     └──────────────┘
```

## Directory Structure

```
/opt/docling-mcp/
├── config.yaml             # Shared tg-note configuration (mounted read-only)
├── app/                      # Application code
│   └── tg_docling/
│       ├── config.py        # Configuration management
│       ├── converter.py     # Document converter integration
│       ├── model_sync.py    # Model download & sync
│       └── server.py        # MCP server entrypoint
├── models/                  # Model cache (volume)
│   ├── RapidOcr/           # RapidOCR models
│   ├── EasyOcr/            # EasyOCR models
│   └── ...
├── cache/                   # General cache (volume)
│   └── huggingface/        # HuggingFace model cache
└── logs/                    # Log files (volume)
    └── docling-mcp.log
```

## Configuration

The container reads the same `config.yaml` that powers tg-note. Docker Compose mounts the file into
`/opt/docling-mcp/config.yaml`, so Docling and the bot always stay in sync.

### Configuration Structure

```json
{
  "log_level": "INFO",
  "startup_sync": true,
  "mcp": {
    "transport": "sse",
    "host": "0.0.0.0",
    "port": 8077,
    "tools": ["conversion", "generation", "manipulation"]
  },
  "converter": {
    "keep_images": false,
    "prefer_markdown_output": true,
    "fallback_plain_text": true,
    "image_ocr_enabled": true,
    "generate_page_images": false,
    "ocr": {
      "backend": "rapidocr",
      "languages": ["eng"],
      "force_full_page_ocr": false,
      "rapidocr": {
        "enabled": true,
        "backend": "onnxruntime",
        "providers": ["CUDAExecutionProvider", "CPUExecutionProvider"],
        "det_model_path": "RapidOcr/onnx/PP-OCRv4/det/ch_PP-OCRv4_det_infer.onnx",
        "rec_model_path": "RapidOcr/onnx/PP-OCRv4/rec/ch_PP-OCRv4_rec_infer.onnx",
        "cls_model_path": "RapidOcr/onnx/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_infer.onnx",
        "rec_keys_path": "RapidOcr/paddle/PP-OCRv4/rec/ch_PP-OCRv4_rec_infer/ppocr_keys_v1.txt"
      },
      "easyocr": {
        "enabled": false,
        "languages": ["en"],
        "gpu": "auto",
        "model_storage_dir": "EasyOcr"
      },
      "tesseract": {
        "enabled": false,
        "languages": ["eng"]
      },
      "onnxtr": {
        "enabled": false
      }
    }
  },
  "model_cache": {
    "base_dir": "/opt/docling-mcp/models",
    "builtin_models": {
      "layout": true,
      "tableformer": true,
      "code_formula": true,
      "picture_classifier": true,
      "rapidocr": {"enabled": true, "backends": ["onnxruntime"]},
      "easyocr": false,
      "smolvlm": false,
      "granitedocling": false,
      "granitedocling_mlx": false,
      "smoldocling": false,
      "smoldocling_mlx": false,
      "granite_vision": false
    },
    "downloads": []
  }
}
```

## OCR Backends

### RapidOCR (Default)
- **Pros**: Fast, lightweight, good accuracy, GPU support
- **Use case**: General document OCR, Chinese/English documents
- **Models**: PP-OCRv4 (detection/recognition/classification)

### EasyOCR
- **Pros**: Support for 80+ languages, good accuracy
- **Use case**: Multilingual documents
- **Models**: Automatically downloaded based on language selection

### Tesseract
- **Pros**: Mature, stable, wide language support
- **Use case**: Legacy documents, offline processing
- **Models**: Installed via apt packages

### OnnxTR
- **Pros**: ONNX-based, customizable, GPU support
- **Use case**: Custom OCR pipelines
- **Models**: Custom ONNX models

## Model Management

### Automatic Model Download

Models are automatically downloaded on container startup based on configuration. The container first processes `model_cache.builtin_models`, which maps to Docling’s built-in download helpers (layout, tableformer, RapidOCR, EasyOCR, GraniteDocling, etc.). The `sync_docling_models` MCP tool can be called to trigger manual synchronization on demand.

### Model Sources

1. **Docling Bundles** (`model_cache.builtin_models`): Uses `docling.utils.model_downloader` to fetch official models with the expected folder layout.
2. **HuggingFace Hub**: Additional repositories defined in `model_cache.downloads`.
3. **ModelScope**: Optional alternative source for certain OCR artefacts.
4. **Local Cache**: Persistent storage in `/opt/docling-mcp/models`.

### Adding New Models

- Prefer adding bundles to `model_cache.builtin_models` to leverage Docling’s managed downloads and directory structure.
- For bespoke artefacts, add entries to `model_cache.downloads`:

  ```json
  {
    "name": "custom-ocr",
    "type": "huggingface",
    "repo_id": "organization/model-name",
    "local_dir": "custom-ocr",
    "allow_patterns": ["*.onnx", "*.pth"]
  }
  ```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCLING_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DOCLING_MODELS_DIR` | `/opt/docling-mcp/models` | Model cache directory |
| `DOCLING_CACHE_DIR` | `/opt/docling-mcp/cache` | General cache directory |
| `DOCLING_LOG_DIR` | `/opt/docling-mcp/logs` | Log files directory |
| `HF_HOME` | `/opt/docling-mcp/cache/huggingface` | HuggingFace cache location |
| `HF_HUB_ENABLE_HF_TRANSFER` | `1` | Enable fast HF transfers (auto-disables when `hf_transfer` is missing) |
| `CUDA_VISIBLE_DEVICES` | `all` | GPU device selection |
| `DOCLING_OCR_BACKEND` | `rapidocr` | Default OCR backend |

## Usage

### Starting the Container

```bash
docker-compose up -d docling-mcp
```

### Viewing Logs

```bash
docker-compose logs -f docling-mcp
```

### Manual Model Sync

Via MCP tool (from tg-note):
```python
from src.processor.docling_runtime import sync_models

result = await sync_models(force=True)
```

Via Docker exec:
```bash
docker exec tg-note-docling python -m tg_docling.model_sync --force
```

### Testing OCR

```bash
# Convert a PDF
docker exec tg-note-docling python -c "
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
result = converter.convert('/path/to/document.pdf')
print(result.document.export_to_markdown())
"
```

## GPU Support

### Requirements

- NVIDIA GPU with CUDA support
- nvidia-docker2 installed
- CUDA 12.1 or compatible version

### Verifying GPU Access

```bash
docker exec tg-note-docling nvidia-smi
```

### GPU Memory Management

- Default GPU memory utilization: 80%
- Can be adjusted via CUDA runtime environment variables
- Multiple containers can share GPUs

## Troubleshooting

### Container Fails to Start

1. Check logs: `docker-compose logs docling-mcp`
2. Verify GPU access: `docker exec tg-note-docling nvidia-smi`
3. Check disk space for model downloads
4. Verify configuration file is valid JSON

### Model Download Fails

1. Check HuggingFace connectivity
2. Verify HF_TOKEN if using private models
3. Check disk space in models directory
4. Review logs for specific error messages
5. If you see an `hf_transfer` import error, the container will automatically fall back to standard downloads after logging a warning.

### OCR Not Working

1. Verify OCR backend is enabled in configuration
2. Check that required models are downloaded
3. Verify GPU access (for CUDA providers)
4. Try fallback to CPU provider

### Performance Issues

1. Check GPU utilization: `nvidia-smi`
2. Verify CUDA providers are being used
3. Consider using lighter OCR models
4. Increase container memory if needed

## Development

### Building Locally

```bash
docker build -t tg-note-docling-mcp:local \
  -f docker/docling-mcp/Dockerfile \
  .
```

The Dockerfile uses the official PyTorch base image (`pytorch/pytorch:2.8.0-cuda12.6-cudnn9-runtime`) which includes PyTorch, torchvision, and torchaudio with CUDA 12.6 support pre-installed. This ensures reliable CUDA builds without dependency conflicts and provides improved GPU performance.

### Running Tests

```bash
docker exec tg-note-docling pytest /opt/docling-mcp/tests/
```

### Adding New OCR Backend

1. Update `requirements.txt` with dependencies
2. Add configuration class to `config.py`
3. Implement OCR options builder in `converter.py`
4. Update documentation

## Integration with tg-note

The container is automatically integrated with tg-note through:

1. **MCP Protocol**: SSE transport on port 8077
2. **Configuration Sync**: Settings automatically update container config
3. **Model Management**: Models sync when settings change
4. **Notifications**: Progress updates sent to Telegram (when callback is set)

### Changing Settings via Telegram

1. Use `/settings` command
2. Navigate to Media Processing → Docling
3. Change OCR backend, languages, or models
4. Models automatically download if needed
5. Progress notifications sent to chat

## License

Follows tg-note project license (MIT).

## References

- [Docling Documentation](https://docling-project.github.io/docling/)
- [Docling MCP GitHub](https://github.com/docling-project/docling-mcp)
- [RapidOCR](https://github.com/RapidAI/RapidOCR)
- [EasyOCR](https://github.com/JaidedAI/EasyOCR)
- [Tesseract](https://github.com/tesseract-ocr/tesseract)
