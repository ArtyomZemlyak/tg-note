# Verification for layout_heron_101 Preset

## Your Configuration

```yaml
pipeline:
  layout:
    enabled: true
    preset: layout_heron_101  # ← Your preset
```

## What Will Happen After Fix

### 1. Model Download

Our fix will:
```python
preset = "layout_heron_101"
layout_spec = DOCLING_LAYOUT_HERON_101
repo_id = "docling-models/layout__heron_101"  # From preset
model_repo_folder = "docling-models--layout__heron_101"

# Direct HuggingFace download
download_from_hf(
    repo_id="docling-models/layout__heron_101",
    target_dir="/opt/docling-mcp/models/docling-models--layout__heron_101"
)
```

### 2. Expected Directory Structure

```
/opt/docling-mcp/models/
└── docling-models--layout__heron_101/    ← Correct folder!
    ├── model.safetensors
    ├── config.json
    └── preprocessor_config.json
```

### 3. LayoutModel Path Resolution

```python
artifacts_path = Path("/opt/docling-mcp/models")
model_repo_folder = "docling-models--layout__heron_101"
model_path = ""

# Check: (artifacts_path / model_repo_folder).exists()
# → (/opt/docling-mcp/models/docling-models--layout__heron_101).exists()
# → True ✅

final_path = artifacts_path / model_repo_folder / model_path
# = /opt/docling-mcp/models/docling-models--layout__heron_101

# LayoutPredictor looks for:
# /opt/docling-mcp/models/docling-models--layout__heron_101/model.safetensors ✅
```

## Before vs After

| | **Before (WRONG)** | **After (CORRECT)** |
|---|---|---|
| **Download source** | `docling-project/docling-layout-heron` | `docling-models/layout__heron_101` ✅ |
| **Folder created** | `docling-project--docling-layout-heron` | `docling-models--layout__heron_101` ✅ |
| **LayoutModel looks for** | `docling-models--layout__heron_101` | `docling-models--layout__heron_101` ✅ |
| **Folder exists?** | ❌ No → Error | ✅ Yes → Success |

## Testing Steps

### 1. Clean Old Models (Optional)

```bash
# Remove old/wrong folders
docker-compose exec docling-mcp rm -rf /opt/docling-mcp/models/docling-project--*
```

### 2. Rebuild Container

```bash
docker-compose down
docker-compose build docling-mcp
docker-compose up -d docling-mcp
```

### 3. Check Logs

```bash
docker-compose logs -f docling-mcp | grep -A5 "layout_heron_101"
```

**Expected output**:
```
Downloading Docling layout bundle: preset='layout_heron_101', 
  repo_id='docling-models/layout__heron_101', 
  folder='docling-models--layout__heron_101'
Downloading layout model from docling-models/layout__heron_101 to 
  /opt/docling-mcp/models/docling-models--layout__heron_101
✅ Downloaded bundle layout
```

### 4. Verify Folder

```bash
docker-compose exec docling-mcp ls -la /opt/docling-mcp/models/
```

**Should show**:
```
drwxr-xr-x docling-models--layout__heron_101/    ← ✅ Correct!
```

**Should NOT show**:
```
drwxr-xr-x docling-project--docling-layout-heron/  ← ❌ Old/wrong
```

### 5. Verify Model Files

```bash
docker-compose exec docling-mcp ls /opt/docling-mcp/models/docling-models--layout__heron_101/
```

**Expected**:
```
model.safetensors
config.json
preprocessor_config.json
```

### 6. Test Conversion

Send a PDF to your Telegram bot. Should now work! 🎉

## Troubleshooting

### Still seeing old folder name?

Force re-download:
```bash
docker-compose exec docling-mcp python -m tg_docling.model_sync --force
```

### Network errors during download?

Check if models were downloaded despite the error:
```bash
docker-compose exec docling-mcp find /opt/docling-mcp/models -name "*.safetensors"
```

If files exist, conversion should work (our cache fallback handles network errors).

## Why Your Logs Showed Wrong Folder

From your log:
```
Returning existing local_dir `/opt/docling-mcp/models/docling-project--docling-layout-heron`
```

This happened because:
1. Old code used `download_model_bundles()` 
2. That function uses **Docling's built-in repo_id** (`docling-project/docling-layout-heron`)
3. Ignores your **preset's repo_id** (`docling-models/layout__heron_101`)

**Our fix**: Extract repo_id directly from preset and use HuggingFace download.

## Summary

✅ **Your preset IS supported**: `layout_heron_101` ← in `_LAYOUT_PRESET_MAP`  
✅ **Fix will download to**: `docling-models--layout__heron_101`  
✅ **LayoutModel will find it**: Path construction now matches  
✅ **Network errors handled**: Graceful fallback to cached models  

The fix is **specifically designed** to handle presets like yours correctly! 🎯
