# Quick Start: Docling Model Path Fix

## What Was Fixed

Fixed critical issues with Docling model path configuration and downloads:

1. ✅ **Environment variables now set BEFORE Docling imports** - prevents path misconfiguration
2. ✅ **Network errors handled gracefully** - falls back to cached models when HuggingFace Hub is unreachable
3. ✅ **Directory creation ensured** - all paths created before use
4. ✅ **Proper path resolution** - models downloaded to correct subdirectories are now found
5. ✅ **Better logging** - detailed debug information for troubleshooting

## Key Changes

### New File
- `app/tg_docling/env_setup.py` - Sets environment variables early in startup

### Modified Files
- `app/tg_docling/server.py` - Improved environment setup
- `app/tg_docling/model_sync.py` - Enhanced download resilience
- `app/tg_docling/tools.py` - Better path configuration
- `app/tg_docling/config.py` - Early env setup
- `app/tg_docling/converter.py` - Early env setup

## How to Test

### 1. Rebuild Docker Container

```bash
# From workspace root
docker-compose down
docker-compose build docling-mcp
docker-compose up -d docling-mcp
```

### 2. Check Logs

```bash
docker-compose logs -f docling-mcp
```

**Look for**:
- ✅ Environment configuration messages
- ✅ Model synchronization progress
- ✅ Successful model downloads or "using cached" messages
- ❌ NO "model.safetensors not found" errors

### 3. Test Document Conversion

From your bot application:
```python
# Send a PDF to the Telegram bot
# It should now convert successfully even if HuggingFace Hub has connection issues
```

## Expected Behavior

### First Run (Models Not Cached)
```
[INFO] Docling environment configured: DOCLING_MODELS_DIR=/opt/docling-mcp/models
[INFO] Starting model synchronization...
[INFO] Downloading layout bundle: preset='layout_v2'...
[INFO] ✅ Downloaded bundle layout
```

### Subsequent Runs (Models Cached)
```
[INFO] Docling environment configured: DOCLING_MODELS_DIR=/opt/docling-mcp/models
[INFO] Skipping model sync (already cached)
[INFO] Starting Docling MCP server...
```

### Network Error (With Cached Models)
```
[WARNING] Download verification failed, but cached models exist. Using cached version.
[INFO] ✅ Model sync completed successfully
```

## Troubleshooting

### Still seeing "model.safetensors" errors?

1. **Force model re-download:**
   ```bash
   docker-compose exec docling-mcp python -m tg_docling.model_sync --force
   ```

2. **Check model files exist:**
   ```bash
   docker-compose exec docling-mcp find /opt/docling-mcp/models -name "*.safetensors"
   ```

3. **Check environment variables:**
   ```bash
   docker-compose exec docling-mcp env | grep DOCLING
   ```

### Container won't start?

Check logs for import errors:
```bash
docker-compose logs docling-mcp | grep -i error
```

## What's Next

After verifying everything works:

1. Commit the changes
2. Update your deployment
3. Monitor logs for any issues
4. Check the detailed documentation in `DOCLING_MODEL_PATH_FIX.md`

## Questions?

See `DOCLING_MODEL_PATH_FIX.md` for:
- Detailed technical explanation
- Architecture diagrams
- Advanced troubleshooting
- Environment variable reference
