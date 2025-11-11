# Docling Model Path and Download Management Fix

## Problem Summary

The Docling MCP container was experiencing issues with model path configuration and model downloads:

1. **Environment Variable Timing**: Docling was initializing before `DOCLING_MODELS_DIR` and `DOCLING_ARTIFACTS_PATH` were set, causing it to look for models in the wrong location
2. **Path Construction Issues**: Models were downloaded to subdirectories (e.g., `/opt/docling-mcp/models/docling-project--docling-layout-heron/`) but Docling was looking directly in the base directory (e.g., `/opt/docling-mcp/models/model.safetensors`)
3. **Network Error Handling**: When HuggingFace Hub connections failed, the system didn't gracefully fall back to cached models
4. **Environment Variable Overwriting**: Using `setdefault()` meant incorrectly set environment variables weren't corrected

## Solutions Implemented

### 1. Early Environment Setup (`env_setup.py`)

**New File**: `/workspace/docker/docling-mcp/app/tg_docling/env_setup.py`

- Creates a module that sets up environment variables **before** any Docling imports
- Ensures directories exist before setting environment variables
- Sets `DOCLING_MODELS_DIR`, `DOCLING_ARTIFACTS_PATH`, `DOCLING_CACHE_DIR`, and `HF_HOME`
- Automatically executed when imported (module-level code)

**Key Feature**: This module is imported at the top of all modules that use Docling components, ensuring environment is configured before Docling initializes.

### 2. Improved Server Initialization (`server.py`)

**Changes**:
- Import `env_setup` before any Docling imports
- Improved `_apply_env_overrides()` function:
  - Uses direct assignment (`os.environ[key] = value`) instead of `setdefault()` to ensure correct values
  - Creates directories before setting environment variables
  - Adds detailed debug logging
  - Ensures `HF_HOME` is set for HuggingFace Hub cache

### 3. Enhanced Model Download Resilience (`model_sync.py`)

**Changes to `_snapshot_download_with_hf_transfer_fallback()`**:
- Added `_check_models_exist()` helper function to verify model files are present
- When network download fails but model files exist locally, use cached version
- Checks for common model file patterns: `*.safetensors`, `*.onnx`, `*.bin`, `*.pt`, `config.json`
- Provides detailed logging when falling back to cached models
- Handles three failure scenarios:
  1. Missing `hf_transfer` package (fallback to standard download)
  2. Network errors during download (use cached if available)
  3. Retry failures (use cached if available)

### 4. Consistent Environment Setup in Tools (`tools.py`)

**Changes to `_load_docling_settings_for_sync()`**:
- Ensures directories exist before setting environment variables
- Sets `HF_HOME` if not already configured
- Uses direct assignment for environment variables
- Improved debug logging with all relevant paths

### 5. Import Order Fixes

Added early environment setup imports to:
- `config.py`
- `model_sync.py`
- `converter.py`
- `tools.py`

This ensures environment variables are always set before Docling components are imported.

## How It Works

### Startup Sequence

```
1. Python imports any tg_docling module
2. That module imports tg_docling.env_setup as first import
3. env_setup sets environment variables immediately (module-level code)
4. Environment is ready before any Docling imports
5. Docling initializes with correct paths
```

### Model Path Resolution

Docling constructs model paths as:
```
artifacts_path / model_repo_folder / model_path
```

Where:
- `artifacts_path` = `DOCLING_MODELS_DIR` (e.g., `/opt/docling-mcp/models`)
- `model_repo_folder` = relative folder name (e.g., `docling-project--docling-layout-heron`)
- `model_path` = usually empty or relative path within folder

The fix ensures:
1. `DOCLING_ARTIFACTS_PATH` and `DOCLING_MODELS_DIR` point to the base directory
2. `model_repo_folder` remains relative (not absolute)
3. Models downloaded to correct subdirectories are properly found

### Network Error Handling

When HuggingFace Hub download fails:
```python
# Old behavior: Raise error immediately
# New behavior:
if _check_models_exist(target_dir):
    logger.warning("Using cached models")
    return str(target_dir)
else:
    raise  # Only raise if models truly missing
```

## Testing the Fix

### 1. Test Environment Variables

Check that environment variables are set correctly:

```python
import os
print(f"DOCLING_MODELS_DIR: {os.environ.get('DOCLING_MODELS_DIR')}")
print(f"DOCLING_ARTIFACTS_PATH: {os.environ.get('DOCLING_ARTIFACTS_PATH')}")
print(f"DOCLING_CACHE_DIR: {os.environ.get('DOCLING_CACHE_DIR')}")
print(f"HF_HOME: {os.environ.get('HF_HOME')}")
```

Expected output:
```
DOCLING_MODELS_DIR: /opt/docling-mcp/models
DOCLING_ARTIFACTS_PATH: /opt/docling-mcp/models
DOCLING_CACHE_DIR: /opt/docling-mcp/cache
HF_HOME: /opt/docling-mcp/hf_cache
```

### 2. Test Model Download

```bash
# From container
python -m tg_docling.model_sync --force
```

Should:
- Create necessary directories
- Download models to correct locations
- Log detailed progress information
- Fallback to cached models if network fails

### 3. Test Document Conversion

```python
from tg_docling.tools import convert_document_from_content
import base64

# Test with a simple PDF
with open("test.pdf", "rb") as f:
    content = base64.b64encode(f.read()).decode()

result = convert_document_from_content(
    content=content,
    filename="test.pdf",
    mime_type="application/pdf"
)
print(f"Conversion successful: {result}")
```

## Troubleshooting

### Issue: Models still not found

**Check**:
1. Directory permissions: `ls -la /opt/docling-mcp/models/`
2. Model files exist: `find /opt/docling-mcp/models/ -name "*.safetensors"`
3. Environment variables: Run test #1 above
4. Docling logs for path construction details

**Fix**:
```bash
# Force re-download
python -m tg_docling.model_sync --force
```

### Issue: Connection errors during download

**Symptoms**: Logs show `RemoteDisconnected` or connection timeout

**Behavior**: System should automatically fall back to cached models if they exist

**Manual Fix**:
```bash
# Verify cached models exist
find /opt/docling-mcp/models/ -name "*.safetensors"

# If models exist, conversion should work despite connection errors
```

### Issue: Circular import errors

**Cause**: Importing modules in wrong order

**Fix**: Ensure `tg_docling.env_setup` is imported **first** in every module that uses Docling:
```python
# GOOD
import tg_docling.env_setup  # First!
from docling.datamodel import ...

# BAD
from docling.datamodel import ...
import tg_docling.env_setup  # Too late!
```

## Environment Variables Reference

| Variable | Purpose | Default | Set By |
|----------|---------|---------|--------|
| `DOCLING_MODELS_DIR` | Base directory for models | `/opt/docling-mcp/models` | `env_setup.py` |
| `DOCLING_ARTIFACTS_PATH` | Docling artifact path (same as MODELS_DIR) | `/opt/docling-mcp/models` | `env_setup.py` |
| `DOCLING_CACHE_DIR` | Docling cache directory | `/opt/docling-mcp/cache` | `env_setup.py` |
| `HF_HOME` | HuggingFace Hub cache | `/opt/docling-mcp/hf_cache` | `env_setup.py` |
| `DOCLING_SETTINGS_PATH` | Path to config YAML | `/opt/docling-mcp/config.yaml` | User/Docker |

## Key Code Changes

### Before
```python
# server.py
os.environ.setdefault("DOCLING_MODELS_DIR", str(models_dir))  # Won't override!

# model_sync.py
return snapshot_download(**kwargs)  # Fails on network error
```

### After
```python
# env_setup.py (NEW FILE)
os.environ["DOCLING_MODELS_DIR"] = str(models_dir)  # Always sets correctly

# model_sync.py
try:
    return snapshot_download(**kwargs)
except Exception as exc:
    if _check_models_exist(target_dir):
        return str(target_dir)  # Use cached
    raise
```

## Related Files Modified

1. `/workspace/docker/docling-mcp/app/tg_docling/env_setup.py` (NEW)
2. `/workspace/docker/docling-mcp/app/tg_docling/server.py`
3. `/workspace/docker/docling-mcp/app/tg_docling/model_sync.py`
4. `/workspace/docker/docling-mcp/app/tg_docling/tools.py`
5. `/workspace/docker/docling-mcp/app/tg_docling/config.py`
6. `/workspace/docker/docling-mcp/app/tg_docling/converter.py`

## Benefits

1. **Reliability**: Environment always configured correctly before Docling initializes
2. **Resilience**: Graceful fallback to cached models when network fails
3. **Clarity**: Detailed logging helps diagnose path issues
4. **Correctness**: Direct environment variable assignment ensures proper values
5. **Consistency**: All modules use same early setup pattern

## Future Improvements

1. Add validation to verify model files are complete (not just present)
2. Implement model integrity checks (checksums)
3. Add retry logic with exponential backoff for network errors
4. Cache model metadata to reduce network requests
5. Add health check endpoint to verify model availability
