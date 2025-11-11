# CRITICAL FIX: Model Download Path Mismatch

## 🚨 Critical Problem Discovered

The error `/opt/docling-mcp/models/model.safetensors not found` was caused by **two critical issues**:

### Issue 1: Wrong Model Repository Folder

**Log showed:**
```
Returning existing local_dir `/opt/docling-mcp/models/docling-project--docling-layout-heron`
```

**But we expected:**
```
/opt/docling-mcp/models/docling-models--layout__v2
```

**Root cause**: `download_model_bundles()` from Docling uses its **built-in/outdated** `repo_id`, ignoring our preset configuration!

### Issue 2: LayoutModel Path Logic

From Docling source code:
```python
# In LayoutModel.__init__
if (artifacts_path / model_repo_folder).exists():
    artifacts_path = artifacts_path / model_repo_folder / model_path  # ✅ Correct
elif (artifacts_path / model_path).exists():
    artifacts_path = artifacts_path / model_path  # ❌ Wrong when model_path is empty!
```

**When model folder doesn't exist**:
1. First check fails: `(/opt/docling-mcp/models/docling-models--layout__v2).exists()` → False
2. Second check: `(/opt/docling-mcp/models/).exists()` → True (base dir exists!)
3. Result: `artifacts_path = /opt/docling-mcp/models/`
4. LayoutPredictor looks for: `/opt/docling-mcp/models/model.safetensors` ❌ **WRONG!**

## ✅ Solution Implemented

### Fix 1: Direct HuggingFace Download for Layout Models

Changed `_sync_builtin_model()` in `model_sync.py` to:

1. **Extract correct `repo_id` from preset** (not from Docling defaults)
2. **Use `_snapshot_download_with_hf_transfer_fallback()`** directly
3. **Download to correct folder** (`model_repo_folder` from preset)
4. **Fallback to `download_model_bundles()`** only if direct download fails

**Code:**
```python
if model_name == "layout" and full_settings is not None:
    layout_spec = _LAYOUT_PRESET_MAP.get(layout_preset)
    if layout_spec:
        repo_id = getattr(layout_spec, "repo_id", None)
        model_repo_folder = getattr(layout_spec, "model_repo_folder", None)
        
        # Download directly using correct repo_id
        target_dir = base_dir / model_repo_folder
        local_dir = _snapshot_download_with_hf_transfer_fallback(
            repo_id=repo_id,
            revision=revision,
            target_dir=target_dir,
            ...
        )
```

### Fix 2: Graceful Cache Fallback

Enhanced `_snapshot_download_with_hf_transfer_fallback()` to:
- Check if model files exist before raising network errors
- Use cached models when download fails but files are present
- Check for: `*.safetensors`, `*.onnx`, `*.bin`, `*.pt`, `config.json`

### Fix 3: Early Environment Setup

Created `env_setup.py` that:
- Sets environment variables **before** any Docling imports
- Ensures `DOCLING_MODELS_DIR` = `/opt/docling-mcp/models` (base dir)
- Ensures `DOCLING_ARTIFACTS_PATH` = `/opt/docling-mcp/models` (base dir)
- Creates all directories before configuring paths

## 📊 How Docling Paths Work

### Correct Path Construction

```
Final path = artifacts_path / model_repo_folder / model_path
           = /opt/docling-mcp/models / docling-models--layout__v2 / ""
           = /opt/docling-mcp/models/docling-models--layout__v2
```

Where:
- `artifacts_path` = **Base directory** (`/opt/docling-mcp/models`)
- `model_repo_folder` = **Relative folder** (`docling-models--layout__v2`)
  - Computed as `repo_id.replace("/", "--")`
  - Example: `docling-models/layout__v2` → `docling-models--layout__v2`
- `model_path` = **Usually empty** (`""`)

### What LayoutPredictor Needs

```
artifact_path/
├── model.safetensors         ← Must exist!
├── config.json                ← Must exist!
└── preprocessor_config.json   ← Must exist!
```

So the full path must be:
```
/opt/docling-mcp/models/docling-models--layout__v2/model.safetensors
```

## 🔍 Why The Old Code Failed

### Before Fix:

1. **Download**: `download_model_bundles()` downloads to `docling-project--docling-layout-heron` (wrong folder!)
2. **Converter creation**: LayoutModel looks for `docling-models--layout__v2` (correct folder from preset)
3. **Path check**: `(artifacts_path / model_repo_folder).exists()` → **False** (folder doesn't exist!)
4. **Fallback**: Uses `artifacts_path / model_path` = `/opt/docling-mcp/models/`
5. **Error**: Looks for `/opt/docling-mcp/models/model.safetensors` ❌

### After Fix:

1. **Download**: Direct HuggingFace download to `docling-models--layout__v2` (correct folder!)
2. **Converter creation**: LayoutModel looks for `docling-models--layout__v2`
3. **Path check**: `(artifacts_path / model_repo_folder).exists()` → **True** ✅
4. **Result**: Uses `/opt/docling-mcp/models/docling-models--layout__v2/` ✅
5. **Success**: Finds `/opt/docling-mcp/models/docling-models--layout__v2/model.safetensors` ✅

## 🧪 How to Verify

### 1. Check Model Folder Name

```bash
docker-compose exec docling-mcp ls -la /opt/docling-mcp/models/
```

**Should see:**
```
docling-models--layout__v2/          ← Correct!
```

**Should NOT see:**
```
docling-project--docling-layout-heron/   ← Wrong!
```

### 2. Check Model Files

```bash
docker-compose exec docling-mcp ls -la /opt/docling-mcp/models/docling-models--layout__v2/
```

**Should see:**
```
model.safetensors
config.json
preprocessor_config.json
```

### 3. Check Logs

```bash
docker-compose logs docling-mcp | grep "Downloading Docling layout bundle"
```

**Should see:**
```
Downloading Docling layout bundle: preset='layout_v2', 
  repo_id='docling-models/layout__v2', 
  folder='docling-models--layout__v2'
Downloading layout model from docling-models/layout__v2 to /opt/docling-mcp/models/docling-models--layout__v2
```

## 📝 Key Takeaways

1. ✅ **Always use preset's `repo_id`**, not Docling's built-in defaults
2. ✅ **Download to `model_repo_folder`** from preset, not auto-detected folder
3. ✅ **Ensure folder exists** before LayoutModel initialization
4. ✅ **artifacts_path MUST be base directory**, not model subfolder
5. ✅ **`model_repo_folder` is a @property**, computed from `repo_id`
6. ✅ **Gracefully handle network errors** by checking for cached files

## 🔧 Files Modified

1. **`model_sync.py`**
   - Added direct HuggingFace download for layout models
   - Enhanced cache fallback logic
   - Better logging

2. **`env_setup.py`** (NEW)
   - Early environment variable setup
   - Directory creation before configuration

3. **`server.py`, `tools.py`, `converter.py`, `config.py`**
   - Import `env_setup` before Docling imports
   - Improved path configuration

## 🚀 Next Steps

1. Rebuild Docker container
2. Clear old model cache if needed: `rm -rf /opt/docling-mcp/models/docling-project--*`
3. Let startup sync download to correct location
4. Test document conversion

## ⚠️ Migration Note

If you have old models in `docling-project--docling-layout-heron`, they will be ignored. The new code will download fresh models to `docling-models--layout__v2`.

You can safely delete old folders:
```bash
docker-compose exec docling-mcp find /opt/docling-mcp/models -name "docling-project--*" -type d -exec rm -rf {} +
```
